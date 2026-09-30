"""Jamendo adapter — env-gated CC-music lyric source (SPEC §6.3, §9).

GATE R / wave-B contract: the adapter **ships inert**. Without
``JAMENDO_CLIENT_ID`` it must make **ZERO network calls**:

- module import is side-effect-free except a pure-file ``.env`` read
  (``bootstrap_env`` — no HTTP);
- ``iter_catalog`` / ``fetch_lyrics`` raise :class:`EnvGateError` (or yield
  nothing under ``allow_inert=True``, the SPEC §6.3 runner-flag option);
- ``python sources/jamendo.py`` reports ``inert — register at
  devportal.jamendo.com`` and exits 0.

The dispatcher's ``check_env_gate`` (W1) also refuses unkeyed runs with exit 2
**before** any adapter code executes — either way, no request is ever made.

When keyed (R1 §5 — v3 API, https://developer.jamendo.com/v3.0/tracks):

- ``tracks`` endpoint, ``include=lyrics`` returns a per-track ``lyrics`` field;
- ``license_ccurl`` per track → SPDX via ``_common.LICENSE_URL_MAP``
  (``license_of`` routes through it, never free-text names — SPEC §6.2);
- ``limit`` ≤ 200 + ``offset`` paging; ~35k req/month non-commercial quota;
- Jamendo error **code 6** (HTTP 200 body) = rate-limit → local backoff.

NEVER ``import toolshop`` (megaplan F-B1).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

try:  # package import (sources.jamendo) and flat sys.path both supported
    from ._common import (
        CatalogEntry,
        DropItem,
        EnvGateError,
        LicenseInfo,
        license_from_url,
        license_policy_for,
        polite_get,
    )
except ImportError:  # pragma: no cover - sources/ dir directly on sys.path
    from _common import (  # type: ignore
        CatalogEntry,
        DropItem,
        EnvGateError,
        LicenseInfo,
        license_from_url,
        license_policy_for,
        polite_get,
    )

SOURCE_ID = "jamendo"
ENV_VAR = "JAMENDO_CLIENT_ID"
API_BASE = "https://api.jamendo.com/v3.0"
PAGE_SIZE = 200          # Jamendo v3 hard cap (R1 §5)
RATE_LIMIT_CODE = 6      # headers.code == 6 → rate-limit → backoff (R1 §5)
RATE_LIMIT_RETRIES = 3

#: Devportal key registration note — the exact inert report string.
INERT_MESSAGE = (
    "jamendo: inert — register at devportal.jamendo.com for a free "
    "JAMENDO_CLIENT_ID; the adapter ships disabled until keyed (GATE R)."
)

#: ``.env`` lives beside the extractor scripts (same file that carries
#: ``Genious_API``). Injectable for tests.
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"


# ---------------------------------------------------------------------------
# env gate — reads JAMENDO_CLIENT_ID from the process env OR the .env file
# ---------------------------------------------------------------------------


def _read_dotenv(path: Optional[Path] = None) -> Dict[str, str]:
    """Parse ``KEY=value`` lines from a .env file. Pure file IO — no network.
    Missing/unreadable files return an empty mapping (never raises)."""
    path = Path(path) if path else DOTENV_PATH
    out: Dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            out[key] = val
    return out


def bootstrap_env(dotenv_path: Optional[Path] = None) -> bool:
    """If ``JAMENDO_CLIENT_ID`` is absent from os.environ, lift it from .env
    via ``os.environ.setdefault``. Import-time safe: pure file read, zero
    network. Makes the env-or-.env gate work end-to-end through the W1
    dispatcher, whose ``check_env_gate`` inspects ``os.environ`` only
    (``resolve_adapter`` imports this module *before* the gate runs)."""
    if os.environ.get(ENV_VAR):
        return True
    val = _read_dotenv(dotenv_path).get(ENV_VAR)
    if val:
        os.environ.setdefault(ENV_VAR, val)
        return True
    return False


def get_client_id(dotenv_path: Optional[Path] = None) -> Optional[str]:
    """Resolve the client id: real env var wins, .env fallback. None = inert."""
    return os.environ.get(ENV_VAR) or _read_dotenv(dotenv_path).get(ENV_VAR)


def require_client_id(dotenv_path: Optional[Path] = None) -> str:
    """Return the client id or raise :class:`EnvGateError`. No network."""
    cid = get_client_id(dotenv_path)
    if not cid:
        raise EnvGateError(ENV_VAR, source_id=SOURCE_ID)
    return cid


def is_keyed(dotenv_path: Optional[Path] = None) -> bool:
    return bool(get_client_id(dotenv_path))


def status(dotenv_path: Optional[Path] = None) -> Dict[str, Any]:
    """Machine-readable gate status for tooling/handoffs."""
    keyed = is_keyed(dotenv_path)
    return {
        "source": SOURCE_ID,
        "keyed": keyed,
        "env_var": ENV_VAR,
        "state": "keyed" if keyed else "inert",
        "message": (f"jamendo: keyed ({ENV_VAR} present) — quota ~35k req/month"
                    if keyed else INERT_MESSAGE),
    }


# ---------------------------------------------------------------------------
# license mapping — license_ccurl → SPDX token → tier/release_ok (SPEC §1)
# ---------------------------------------------------------------------------

#: SPDX token → registry category slug (frozen list: by, cc0, by-sa, by-nc,
#: by-nd, other — SPEC §3.2). License-classed dirs make the disk layout itself
#: release-auditable.
def category_for_license(token: Optional[str]) -> str:
    if not token:
        return "other"
    t = token.upper()
    if t.startswith("CC0"):
        return "cc0"
    if t.startswith("CC-BY-SA"):
        return "by-sa"
    if t.startswith("CC-BY-NC"):      # covers BY-NC, BY-NC-SA, BY-NC-ND
        return "by-nc"
    if t.startswith("CC-BY-ND"):
        return "by-nd"
    if t.startswith("CC-BY"):
        return "by"
    return "other"


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Resolve per-item license from ``license_ccurl`` via ``LICENSE_URL_MAP``.

    May only *downgrade* the registry default (cc-by/yes): an unresolvable
    URL degrades to ``unknown``/``study-only``/``no`` — never an upgrade,
    never a guess (SPEC §6.3).
    """
    token = license_from_url(entry.license_url)
    tier, rel = license_policy_for(token)
    if token is None or tier is None:
        return LicenseInfo(
            license="unknown",
            license_url=entry.license_url,
            license_tier="study-only",
            release_ok="no",
        )
    return LicenseInfo(
        license=token,
        license_url=entry.license_url,
        license_tier=tier,
        release_ok=rel,
    )


# ---------------------------------------------------------------------------
# API access (only ever reached when keyed)
# ---------------------------------------------------------------------------


def _api_tracks(
    client_id: str,
    *,
    offset: int = 0,
    limit: int = PAGE_SIZE,
    params_extra: Optional[Dict[str, Any]] = None,
    session=None,
    sleep=None,
) -> Dict[str, Any]:
    """One ``/v3.0/tracks`` page. Jamendo reports failures as HTTP 200 +
    ``headers.code != 0``; code 6 = rate-limit → local exponential backoff
    (R1 §5). Transport pacing/UA/backoff still go through ``polite_get``."""
    real_sleep = sleep or time.sleep
    params: Dict[str, Any] = {
        "client_id": client_id,
        "format": "json",
        "limit": min(int(limit), PAGE_SIZE),
        "offset": int(offset),
        "include": "lyrics",
    }
    if params_extra:
        params.update(params_extra)

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        resp = polite_get(
            f"{API_BASE}/tracks/",
            SOURCE_ID,
            params=params,
            session=session,
            sleep=sleep,
        )
        data = resp.json()
        headers = data.get("headers") or {}
        code = headers.get("code", 0)
        if code == RATE_LIMIT_CODE:
            if attempt < RATE_LIMIT_RETRIES:
                real_sleep(min(2 ** attempt * 5, 60))
                continue
            raise RuntimeError(
                f"jamendo rate-limit (code {RATE_LIMIT_CODE}) persisted past "
                f"{RATE_LIMIT_RETRIES} retries"
            )
        if code not in (0, None):
            raise RuntimeError(
                f"jamendo API error code={code}: "
                f"{headers.get('error_message') or headers.get('status')}"
            )
        return data
    raise RuntimeError(f"jamendo API unreachable for {params}")  # unreachable


def _entry_from_track(track: Dict[str, Any]) -> CatalogEntry:
    """v3 track JSON → CatalogEntry (TASL fields populated, SPEC §1.3)."""
    fid = str(track.get("id", ""))
    artist = track.get("artist_name") or ""
    share = track.get("shareurl") or f"https://www.jamendo.com/track/{fid}"
    lic_url = track.get("license_ccurl") or None
    token = license_from_url(lic_url)
    tier, rel = license_policy_for(token)
    artist_id = track.get("artist_id")
    lyrics = track.get("lyrics") or ""
    return CatalogEntry(
        source_id=SOURCE_ID,
        foreign_identifier=fid,
        title=track.get("name") or "",
        url=share,
        artist=artist or None,
        creator=artist,                       # TASL Author (task contract)
        creator_url=(f"https://www.jamendo.com/artist/{artist_id}"
                     if artist_id else None),
        source_url=share,                     # TASL Source — the track page
        license=token,
        license_url=lic_url,
        license_tier=tier,
        release_ok=rel,
        category=category_for_license(token),
        meta={
            "album_name": track.get("album_name"),
            "album_id": track.get("album_id"),
            "duration": track.get("duration"),
            "releasedate": track.get("releasedate"),
            "lang": track.get("lang"),
            "position": track.get("position"),
            "lyrics_present": bool(lyrics.strip()),
        },
    )


def iter_catalog(
    limit: Optional[int] = None,
    offset: int = 0,
    *,
    session=None,
    client_id: Optional[str] = None,
    allow_inert: bool = False,
    sleep=None,
    params_extra: Optional[Dict[str, Any]] = None,
) -> Iterator[CatalogEntry]:
    """Yield CatalogEntries from ``/v3.0/tracks`` (paged ≤200, R1 §5).

    Env gate (GATE R): unkeyed raises :class:`EnvGateError` on first
    iteration — or yields nothing when the runner passes
    ``allow_inert=True`` (SPEC §6.3 runner-flag option). Either way: ZERO
    network calls while unkeyed.
    """
    try:
        cid = client_id or require_client_id()
    except EnvGateError:
        if allow_inert:
            return
        raise

    emitted = 0
    page_offset = offset
    while limit is None or emitted < limit:
        want = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - emitted)
        data = _api_tracks(
            cid,
            offset=page_offset,
            limit=want,
            params_extra=params_extra,
            session=session,
            sleep=sleep,
        )
        results = data.get("results") or []
        if not results:
            break
        for track in results:
            if limit is not None and emitted >= limit:
                break
            yield _entry_from_track(track)
            emitted += 1
        page_offset += len(results)
        # A page whose size differs from what was requested is the last page
        # (short = exhausted; over-long = upstream ignored `limit` — stop so a
        # pathological response can never loop forever).
        if len(results) != want:
            break


def fetch_lyrics(
    entry: CatalogEntry,
    *,
    session=None,
    client_id: Optional[str] = None,
    sleep=None,
) -> Dict[str, Any]:
    """Fetch one track's lyrics → song JSON v2 (SPEC §3.3).

    Re-queries ``/v3.0/tracks?id=<fid>&include=lyrics`` so the catalog queue
    stays a metadata file. Tracks with an empty ``lyrics`` payload are
    dropped (``no-lyric-text``) — the fill-rate caveat is a known unknown
    (R1 §5 / GATE 0 Q2).
    """
    cid = client_id or require_client_id()
    fid = entry.foreign_identifier
    data = _api_tracks(
        cid,
        offset=0,
        limit=1,
        params_extra={"id": fid},
        session=session,
        sleep=sleep,
    )
    results = data.get("results") or []
    if not results:
        raise DropItem("not-found")
    track = results[0]

    lyrics = (track.get("lyrics") or "").strip()
    if not lyrics:
        raise DropItem("no-lyric-text")

    info = license_of(entry)
    share = track.get("shareurl") or entry.source_url or entry.url
    artist = track.get("artist_name") or entry.artist or entry.creator or "Unknown"
    stanzas = [s.strip() for s in lyrics.split("\n\n") if s.strip()]
    song: Dict[str, Any] = {
        "title": track.get("name") or entry.title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "category": entry.category or category_for_license(info.license),
        "url": share,
        "language": track.get("lang") or entry.meta.get("lang"),
        "raw_lyrics": lyrics,
        "clean_lyrics": lyrics,
        "sections": [{"label": None, "content": s} for s in stanzas],
        # license/provenance block (song JSON v2)
        "corpus": "jamendo",
        "source": SOURCE_ID,
        "foreign_identifier": str(track.get("id", fid)),
        "source_url": share,
        "creator": artist,
        "creator_url": entry.creator_url,
        "copyright_notice": None,
        "modified_note": None,
        "license": info.license,
        "license_url": info.license_url or entry.license_url,
        "license_tier": info.license_tier,
        "release_ok": info.release_ok,
        "derived_from": None,
        "meta": {
            "album_name": track.get("album_name") or entry.meta.get("album_name"),
            "duration": track.get("duration") or entry.meta.get("duration"),
            "releasedate": track.get("releasedate"),
            "audio_stream": track.get("audio") or track.get("audiodownload"),
        },
    }
    return song


# ---------------------------------------------------------------------------
# standalone entry — the inert report (GATE R: reports inert, exits 0)
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None) -> int:
    """``python sources/jamendo.py`` → gate status. Unkeyed prints the inert
    report and returns 0 — and performs NO network access in either branch."""
    # UTF-8 console on Windows (AGENTS.md hard rule)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    st = status()
    print(st["message"])
    if not st["keyed"]:
        return 0
    print(f"jamendo: run a pilot via fetch_lyrics_source.py --source jamendo "
          f"[--catalog-only] [--limit N]")
    return 0


# Import-time .env bridge — pure file IO (zero network): lets the dispatcher's
# os.environ-only env gate see a key that lives only in .env. resolve_adapter
# runs before check_env_gate, so this is the single integration point.
try:
    bootstrap_env()
except Exception:  # pragma: no cover - never block module import
    pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
