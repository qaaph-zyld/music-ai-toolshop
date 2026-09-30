"""LRCLIB adapter — study-only synced/plain lyrics lookup (SPEC §6.3, §9).

Keyless API (R3 §4 — verified live): ``/api/search`` (≤20 results, no
paging), ``/api/get`` (exact signature + ±2 s duration tolerance, external
fallback on miss), ``/api/get-cached`` (internal DB only, deterministic —
preferred first hop). No key, no registration; ~20 req/s ceiling with
``429``+``Retry-After`` — we still pace at the shared **≥1.5 s** floor
(wave-B constraint; registry notes advertise 200-500 ms but the shared
polite interval is deliberately more conservative).

LRCLIB is a *lookup* API, not a browsable corpus → ``iter_catalog`` reads a
local **seed file** (SPEC §9): ``_seed.json`` (list of
``{artist,title,album?,duration?}``) or ``_seed.csv`` (header row) under the
corpus dir ``data/toolshop/lyrics/lrclib/``; ``LRCLIB_SEED`` env var or the
``seed_path`` kwarg override the location.

License posture — **study-only FOREVER**: lyric text remains ©
songwriters/publishers (LRCLIB is a service license, not a content license;
R3 §4). Every catalog row and every song JSON hard-codes
``license='proprietary', license_tier='study-only', release_ok='no'`` —
a ``release_ok='yes'`` lrclib row is a release blocker (invariant test).

Capture per SPEC §3.3: ``plainLyrics`` → raw/clean, ``syncedLyrics`` →
``synced_lyrics`` (LRC), ``lyricsfile`` → ``lyricsfile`` (YAML per-line ms
timings — whisperX weak-label fuel for the alignment lane).

NEVER ``import toolshop`` (megaplan F-B1).
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlencode

try:
    from ._common import (
        CatalogEntry,
        DropItem,
        LicenseInfo,
        polite_get,
        slugify,
    )
except ImportError:  # pragma: no cover - sources/ dir directly on sys.path
    from _common import (  # type: ignore
        CatalogEntry,
        DropItem,
        LicenseInfo,
        polite_get,
        slugify,
    )

SOURCE_ID = "lrclib"
API_BASE = "https://lrclib.net"
DEFAULT_CATEGORY = "tracks"          # frozen single category (SPEC §3.2)

#: Shared politeness floor — the API would tolerate ~20 req/s (50 ms) and the
#: registry row advertises 0.5 s, but wave-B pins us to the shared ≥1.5 s
#: pacing used by every auto source. polite_get's per-source limiter is
#: keyed on source_id, so this is shared across all lrclib calls.
MIN_INTERVAL_S = 1.5

SEED_ENV = "LRCLIB_SEED"
SEED_CANDIDATES = ("_seed.json", "_seed.csv")

#: Hard-locked license block — study-only forever, non-negotiable.
LOCKED_LICENSE = {
    "license": "proprietary",
    "license_tier": "study-only",
    "release_ok": "no",
}


# ---------------------------------------------------------------------------
# seed file (iter_catalog is a local-file reader — SPEC §9)
# ---------------------------------------------------------------------------


def _corpus_root() -> Path:
    """``<data>/lyrics/lrclib`` via the registry (lazy import — keeps module
    import cheap and avoids a sources.registry ↔ _common cycle)."""
    try:
        try:
            from . import registry
        except ImportError:
            import registry  # type: ignore
        root = registry.corpus_root(registry.get(SOURCE_ID))
        if root is not None:
            return root
    except Exception:
        pass
    # defensive fallback — mirrors registry.lyrics_root semantics
    return Path(os.environ.get("TOOLSHOP_DATA_DIR",
            Path(__file__).resolve().parents[2] / "data" / "toolshop")) \
        / "lyrics" / "lrclib"


def seed_path(seed: Optional[Path] = None) -> Optional[Path]:
    """Resolve the seed file: explicit arg > ``LRCLIB_SEED`` env >
    ``<corpus>/_seed.json|_seed.csv``. None when nothing exists."""
    if seed is not None:
        return Path(seed)
    env = os.environ.get(SEED_ENV)
    if env:
        return Path(env)
    root = _corpus_root()
    for name in SEED_CANDIDATES:
        p = root / name
        if p.exists():
            return p
    return None


def _load_seed(path: Path) -> List[Dict[str, Any]]:
    """Parse the seed file into ``{artist,title,album,duration}`` dicts."""
    path = Path(path)
    if not path.exists():
        return []
    if path.suffix.lower() == ".csv":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(_norm_seed_row(row))
        return rows
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("entries") if isinstance(doc, dict) else doc
    if not isinstance(raw, list):
        return []
    return [_norm_seed_row(r) for r in raw if isinstance(r, dict)]


def _norm_seed_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Accept friendly aliases (artist_name/track_name/album_name/duration_s)."""
    def pick(*keys: str):
        for k in keys:
            v = row.get(k)
            if v not in (None, ""):
                return v
        return None

    dur = pick("duration", "duration_s")
    try:
        dur = float(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur = None
    return {
        "artist": pick("artist", "artist_name") or "",
        "title": pick("title", "track_name", "name") or "",
        "album": pick("album", "album_name"),
        "duration": dur,
    }


def _seed_fid(row: Dict[str, Any]) -> str:
    """Stable catalog identity for a seed row — deliberately NOT the LRCLIB
    numeric id (unknown until fetch); relisting the same seed must reproduce
    the same key so ``Catalog.upsert`` never duplicates rows."""
    parts = [
        slugify(row.get("artist") or "?"),
        slugify(row.get("title") or "?"),
        slugify(str(row.get("album") or "")),
        str(int(row["duration"])) if row.get("duration") else "",
    ]
    return "seed:" + ":".join(parts).rstrip(":")


def iter_catalog(
    limit: Optional[int] = None,
    offset: int = 0,
    *,
    seed: Optional[Path] = None,
) -> Iterator[CatalogEntry]:
    """Yield CatalogEntries from the local seed file. No network — LRCLIB is
    a lookup API; the *seed* is the work queue input (SPEC §9). A missing
    seed file yields nothing (empty catalog, exit 0 — never an error)."""
    sp = seed_path(seed)
    rows = _load_seed(sp) if sp else []
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]
    for r in rows:
        yield CatalogEntry(
            source_id=SOURCE_ID,
            foreign_identifier=_seed_fid(r),
            title=r["title"],
            url="",
            artist=r["artist"] or None,
            creator="",                     # lyric contributor unknown (R3 §4)
            category=DEFAULT_CATEGORY,
            meta={"album": r.get("album"), "duration": r.get("duration")},
            **LOCKED_LICENSE,
        )


# ---------------------------------------------------------------------------
# license — locked study-only (the forever invariant)
# ---------------------------------------------------------------------------


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Always ``proprietary``/``study-only``/``no`` — LRCLIB text is ©
    songwriters regardless of what a seed row or upstream record says."""
    return LicenseInfo(
        license="proprietary",
        license_url=None,
        license_tier="study-only",
        release_ok="no",
    )


# ---------------------------------------------------------------------------
# API access
# ---------------------------------------------------------------------------


def _is_not_found(exc: Exception) -> bool:
    resp = getattr(exc, "response", None)
    if resp is not None and getattr(resp, "status_code", None) == 404:
        return True
    return "404" in str(exc)


def _get_json(path: str, params: Dict[str, Any], *, session=None) -> Optional[dict]:
    """polite_get wrapper: returns parsed JSON, ``None`` on 404-miss,
    propagates other errors. Paced at MIN_INTERVAL_S (≥1.5 s shared floor)."""
    try:
        resp = polite_get(
            f"{API_BASE}{path}",
            SOURCE_ID,
            params=params,
            session=session,
            min_interval_s=MIN_INTERVAL_S,
        )
    except Exception as exc:
        if _is_not_found(exc):
            return None
        raise
    return resp.json()


def _signature_params(entry: CatalogEntry) -> Dict[str, Any]:
    """``/api/get`` exact-signature params from a catalog entry."""
    p: Dict[str, Any] = {
        "track_name": entry.title,
        "artist_name": entry.artist or entry.creator or "",
    }
    album = entry.meta.get("album")
    dur = entry.meta.get("duration")
    if album:
        p["album_name"] = album
    if dur:
        p["duration"] = int(float(dur))
    return p


def _search_params(entry: CatalogEntry) -> Dict[str, Any]:
    p: Dict[str, Any] = {
        "track_name": entry.title,
        "artist_name": entry.artist or entry.creator or "",
    }
    if entry.meta.get("album"):
        p["album_name"] = entry.meta["album"]
    return p


def _pick_search_hit(results: List[Dict[str, Any]], entry: CatalogEntry) -> Optional[Dict[str, Any]]:
    """Best hit from ``/api/search``: prefer exact (title,artist) match,
    else the first result with any lyric payload."""
    if not results:
        return None
    want_t = (entry.title or "").strip().lower()
    want_a = (entry.artist or entry.creator or "").strip().lower()
    for r in results:
        if ((r.get("trackName") or "").strip().lower() == want_t
                and (r.get("artistName") or "").strip().lower() == want_a):
            return r
    for r in results:
        if (r.get("plainLyrics") or "").strip() or (r.get("syncedLyrics") or "").strip():
            return r
    return results[0]


def _lookup(entry: CatalogEntry, *, session=None) -> tuple:
    """Resolve one seed row → (record, lookup_url, matched_via).

    Order per SPEC §9: ``/api/get-cached`` (deterministic) → ``/api/get``
    (±2 s tolerance, external fallback) when the full signature is known;
    ``/api/search`` when album/duration are missing. ``None`` record = miss.
    """
    params = _signature_params(entry)
    full_sig = bool(params.get("album_name") and params.get("duration"))
    base = f"{API_BASE}/api/get"
    lookup_url = f"{base}?{urlencode(params)}"

    if full_sig:
        rec = _get_json("/api/get-cached", params, session=session)
        if rec:
            return rec, lookup_url.replace("/api/get", "/api/get-cached"), "get-cached"
        rec = _get_json("/api/get", params, session=session)
        if rec:
            return rec, lookup_url, "get"
        return None, lookup_url, "miss"

    results = _get_json("/api/search", _search_params(entry), session=session)
    if isinstance(results, dict):   # tolerate a bare record instead of a list
        results = [results]
    hit = _pick_search_hit(results or [], entry) if results else None
    search_url = f"{API_BASE}/api/search?{urlencode(_search_params(entry))}"
    return hit, search_url, "search" if hit else "miss"


_LRC_TAG_RE = re.compile(r"\[[^\]]*\]")


def _lrc_to_plain(lrc: str) -> str:
    """Strip ``[mm:ss.xx]``/tag lines from LRC → plain lyric text."""
    lines = []
    for line in (lrc or "").splitlines():
        text = _LRC_TAG_RE.sub("", line).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def fetch_lyrics(
    entry: CatalogEntry,
    *,
    session=None,
) -> Dict[str, Any]:
    """Resolve one seed row against LRCLIB → song JSON v2 (SPEC §3.3).

    Drops: ``not-found`` (no cached/get/search hit), ``instrumental``
    (``instrumental: true`` — no lyrics exist), ``no-lyrics`` (record
    carries neither plain nor synced text).
    """
    rec, lookup_url, via = _lookup(entry, session=session)
    if rec is None:
        raise DropItem("not-found")

    if rec.get("instrumental"):
        raise DropItem("instrumental")

    plain = (rec.get("plainLyrics") or "").strip()
    synced = (rec.get("syncedLyrics") or "").strip()
    lyricsfile = rec.get("lyricsfile")
    if isinstance(lyricsfile, str):
        lyricsfile = lyricsfile.strip() or None
    else:
        lyricsfile = None

    if not plain and not synced:
        raise DropItem("no-lyrics")

    text = plain or _lrc_to_plain(synced)
    stanzas = [s.strip() for s in text.split("\n\n") if s.strip()]

    artist = rec.get("artistName") or entry.artist or entry.creator or "Unknown"
    title = rec.get("trackName") or rec.get("name") or entry.title
    fid = str(rec.get("id") or entry.foreign_identifier)

    # stamp the resolved id/URL back on the work-queue entry (meta only —
    # foreign_identifier stays the stable seed key so relists never dupe)
    entry.meta["lrclib_id"] = rec.get("id")
    entry.meta["matched_via"] = via
    entry.url = lookup_url

    song: Dict[str, Any] = {
        "title": title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "category": entry.category or DEFAULT_CATEGORY,
        "url": lookup_url,
        "language": None,
        "raw_lyrics": plain or text,
        "clean_lyrics": text,
        "sections": [{"label": None, "content": s} for s in stanzas],
        # license/provenance block — LOCKED (study-only forever)
        "corpus": "lrclib",
        "source": SOURCE_ID,
        "foreign_identifier": fid,          # LRCLIB numeric id (SPEC §1.3)
        "source_url": lookup_url,           # canonical API request URL
        "creator": "",                      # lyric contributor unknown
        "creator_url": None,
        "copyright_notice": None,
        "modified_note": None,
        "license": "proprietary",
        "license_url": None,
        "license_tier": "study-only",
        "release_ok": "no",
        "derived_from": None,
        # lrclib-specific capture (SPEC §3.3)
        "synced_lyrics": synced or None,    # LRC [mm:ss.xx]
        "lyricsfile": lyricsfile,           # YAML per-line start_ms/end_ms
        "meta": {
            "lrclib_id": rec.get("id"),
            "album_name": rec.get("albumName") or entry.meta.get("album"),
            "duration": rec.get("duration") or entry.meta.get("duration"),
            "hasWordSync": rec.get("hasWordSync"),
            "matched_via": via,
        },
    }
    return song


# ---------------------------------------------------------------------------
# standalone entry — status only, no network
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = seed_path()
    rows = _load_seed(p) if p else []
    if p is None:
        print("lrclib: no seed file — expected "
              "data/toolshop/lyrics/lrclib/_seed.json|_seed.csv "
              "(rows: artist,title,album?,duration?; or set LRCLIB_SEED)")
    else:
        print(f"lrclib: seed {p} — {len(rows)} rows "
              f"(study-only corpus; release_ok='no' forever)")
    print("lrclib: run via fetch_lyrics_source.py --source lrclib "
          "[--catalog-only] [--limit N]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
