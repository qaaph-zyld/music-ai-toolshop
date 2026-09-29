"""Shared infrastructure for license-tiered lyric-source adapters (SPEC §6).

Self-contained on purpose: **never ``import toolshop`` here** — the package
``__init__`` eagerly loads heavy deps (~70 s cold, megaplan F-B1). The
``RobotsPolicy`` below is *vendored* from ``toolshop/genius_adapter.py:43-117``
and generalised to accept ``robots_url`` or ``base_url``.

Provided (SPEC §6.2):
- ``RobotsPolicy``, ``RobotsDisallowedError`` — vendored robots.txt gate
- ``RateLimiter``, ``polite_get`` — paced requests wrapper (registry
  ``politeness`` block: ``min_interval_s``, descriptive contact UA, gzip,
  429/``Retry-After`` + MediaWiki ``maxlag``/``ratelimited`` backoff)
- ``CatalogEntry`` / ``LicenseInfo`` dataclasses (+ dict round-trip helpers)
- ``LICENSE_URL_MAP`` / ``license_from_url`` / ``LICENSE_TOKEN_INFO`` /
  ``license_policy_for`` — Openverse URL-fragment -> SPDX-token normalisation
- ``tasl_credit`` — computed credit line (attribution is computed, not stored)
- ``load_catalog`` / ``save_catalog`` — low-level ``_catalog.json`` IO
- ``write_song_json`` / ``song_base_name`` — song JSON v2 + .txt writer
- ``build_index`` / ``write_index`` — per-corpus ``_index.json`` from disk
- ``slugify`` / ``detect_script`` / ``norm_key``
- resumable-batch helpers (``pending_slice`` etc.) matching
  ``toolshop/batch.py`` semantics without importing it
- exceptions: ``DropItem``, ``EnvGateError``
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import urlparse

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:  # pragma: no cover - exercised only without the [lyrics] extra
    requests = None  # type: ignore
    _HAS_REQUESTS = False


__version__ = "1.0"

#: Registry-politeness default pacing (SPEC §6.1: ">=1.5s delay between requests").
DEFAULT_MIN_INTERVAL_S = 1.5
DEFAULT_TIMEOUT_S = 30.0
#: ``{contact}`` is substituted from the ``TOOLSHOP_CONTACT`` env var; Wikimedia
#: IP-blocks bot traffic without a descriptive contact UA (R2 §3).
DEFAULT_UA_TEMPLATE = "toolshop-lyrics/{version} (+contact: {contact})"
ENV_UA_OVERRIDE = "TOOLSHOP_LYRICS_UA"
ENV_CONTACT = "TOOLSHOP_CONTACT"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RobotsDisallowedError(RuntimeError):
    """Raised by polite_get when robots.txt disallows the requested path."""


class DropItem(Exception):
    """Adapters raise this (from license_of/fetch_lyrics) to drop an item.

    The runner records ``status='dropped'`` + ``drop_reason`` in _catalog.json —
    e.g. a copyright-flagged mudcat entry or a ccMixter upload with no lyric
    block. Dropped items never reach disk.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EnvGateError(RuntimeError):
    """Raised when an env-gated source is used without its key (jamendo)."""

    def __init__(self, env_var: str, source_id: str = "") -> None:
        self.env_var = env_var
        self.source_id = source_id
        super().__init__(
            f"source '{source_id}' is env-gated: set {env_var} to enable it "
            f"(adapter ships inert until keyed, SPEC §6.3)"
        )


def _check_requests() -> None:
    if not _HAS_REQUESTS:
        raise RuntimeError(
            "requests is required for lyric-source fetching. "
            "Install with: pip install -e \".[lyrics]\""
        )


# ---------------------------------------------------------------------------
# RobotsPolicy — vendored from toolshop/genius_adapter.py:43-117, generalised
# ---------------------------------------------------------------------------


class RobotsPolicy:
    """Check a site's robots.txt before fetching pages.

    Generalised vendor of ``toolshop.genius_adapter.RobotsPolicy``: pass either
    ``robots_url`` directly or ``base_url`` (``<base>/robots.txt`` is derived).
    Only ``User-agent: *`` (or a group matching our UA) rules apply; rules
    targeting specific AI bots (ChatGPT, ClaudeBot, MLBot…) are ignored.
    """

    def __init__(
        self,
        robots_url: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        user_agent: Optional[str] = None,
    ) -> None:
        _check_requests()
        if robots_url is None:
            if not base_url:
                raise ValueError("RobotsPolicy needs robots_url or base_url")
            robots_url = base_url.rstrip("/") + "/robots.txt"
        self._robots_url = robots_url
        self._timeout = timeout
        self._user_agent = user_agent
        self._disallowed: list[str] = []
        self._loaded = False

    def _load(self) -> None:
        """Fetch and parse robots.txt once.

        Only applies disallow rules from the ``User-agent: *`` section
        (or a section matching our user-agent). Rules targeting specific
        AI bots (ChatGPT, ClaudeBot, etc.) are ignored.
        """
        try:
            headers = {"User-Agent": self._user_agent} if self._user_agent else {}
            resp = requests.get(self._robots_url, timeout=self._timeout, headers=headers)
            resp.raise_for_status()
        except Exception:
            # If robots.txt is unreachable, be conservative and allow
            self._loaded = True
            return

        # Parse robots.txt into per-user-agent groups
        current_agents: list[str] = []
        applies_to_us = False

        for line in resp.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            lower = line.lower()

            if lower.startswith("user-agent:"):
                agent = line[len("user-agent:"):].strip().lower()
                if current_agents and current_agents[-1] != agent:
                    # New group — reset
                    current_agents = []
                    applies_to_us = False
                current_agents.append(agent)
                if agent == "*" or "toolshop" in agent:
                    applies_to_us = True
                continue

            if lower.startswith("disallow:"):
                if applies_to_us:
                    path = line[len("disallow:"):].strip()
                    if path:
                        self._disallowed.append(path)

        self._loaded = True

    def can_fetch(self, path: str) -> bool:
        """Check if a URL path is allowed by robots.txt.

        Args:
            path: URL path (e.g. /wiki/Some_Page).

        Returns:
            True if fetching is allowed, False if disallowed.
        """
        if not self._loaded:
            self._load()

        for disallowed in self._disallowed:
            if path.startswith(disallowed):
                return False
        return True


# ---------------------------------------------------------------------------
# Rate limiting + polite_get
# ---------------------------------------------------------------------------


class RateLimiter:
    """Enforces a minimum interval between requests.

    ``sleep``/``now`` are injectable so tests can verify pacing without real
    waits. State (last request time) lives on the instance — share one limiter
    per source to pace a whole run.
    """

    def __init__(
        self,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        *,
        sleep=None,
        now=None,
    ) -> None:
        self.min_interval_s = float(min_interval_s)
        self._sleep = sleep or time.sleep
        self._now = now or time.monotonic
        self._last: Optional[float] = None
        self.slept: List[float] = []  # observed sleeps — tests assert on this

    def wait(self) -> None:
        now = self._now()
        if self._last is not None:
            delta = self.min_interval_s - (now - self._last)
            if delta > 0:
                self.slept.append(delta)
                self._sleep(delta)
        self._last = self._now()


# Per-source shared limiters so pacing survives across calls in one process.
_LIMITERS: Dict[str, RateLimiter] = {}
_ROBOTS_CACHE: Dict[str, RobotsPolicy] = {}


def default_user_agent(source_id: Optional[str] = None, template: Optional[str] = None) -> str:
    """Descriptive UA for a source. ``TOOLSHOP_LYRICS_UA`` overrides entirely;
    ``TOOLSHOP_CONTACT`` fills the ``{contact}`` template placeholder."""
    ua = os.environ.get(ENV_UA_OVERRIDE)
    if ua:
        return ua
    contact = os.environ.get(ENV_CONTACT, "unconfigured-local-research")
    tpl = template or DEFAULT_UA_TEMPLATE
    try:
        return tpl.format(contact=contact, version=__version__)
    except (KeyError, IndexError):
        return tpl  # template without placeholders — use verbatim


def _source_politeness(source_id: Optional[str]) -> Dict[str, Any]:
    """Pull the registry ``politeness`` block for ``source_id`` (lazy import —
    keeps module import cheap and avoids a cycle with sources.registry)."""
    if not source_id:
        return {}
    try:
        try:
            from . import registry  # package import (sources._common)
        except ImportError:
            import registry  # sources/ dir directly on sys.path
        row = registry.get(source_id)
    except Exception:
        return {}
    return row.get("politeness") or {}


def _limiter_for(source_id: str, min_interval_s: float) -> RateLimiter:
    limiter = _LIMITERS.get(source_id)
    if limiter is None:
        limiter = RateLimiter(min_interval_s)
        _LIMITERS[source_id] = limiter
    return limiter


def polite_get(
    url: str,
    source_id: Optional[str] = None,
    *,
    session=None,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT_S,
    min_interval_s: Optional[float] = None,
    user_agent: Optional[str] = None,
    robots=None,
    max_retries: int = 3,
    limiter: Optional[RateLimiter] = None,
    sleep=None,
) -> "requests.Response":
    """GET ``url`` with registry politeness: pacing, descriptive UA, robots
    check, gzip, and retry/backoff on 429 (+``Retry-After``), 5xx, and
    MediaWiki ``maxlag``/``ratelimited`` JSON errors.

    Args:
        url: request URL.
        source_id: registry id — pulls the ``politeness`` block (min_interval_s,
            user_agent template) and keys the shared per-source limiter.
        session: ``requests.Session``-like (defaults to module requests).
        robots: ``None`` (no check), a ``RobotsPolicy``, or ``"auto"`` to build
            one from the URL's origin (cached per origin).
        limiter: ``RateLimiter`` override (tests inject a fake clock here).
        sleep: sleep callable override for retry backoff (tests).
        max_retries: retries on 429/5xx/maxlag before raising.

    Raises:
        RobotsDisallowedError: when robots.txt disallows the path.
        requests.HTTPError / RequestException: on persistent failure.
    """
    _check_requests()
    pol = _source_politeness(source_id)
    interval = (
        float(min_interval_s)
        if min_interval_s is not None
        else float(pol.get("min_interval_s", DEFAULT_MIN_INTERVAL_S))
    )
    ua = user_agent or default_user_agent(source_id, pol.get("user_agent"))
    req_headers = {
        "User-Agent": ua,
        "Accept-Encoding": "gzip",
    }
    if headers:
        req_headers.update(headers)

    getter = session if session is not None else requests
    real_sleep = sleep or time.sleep

    # --- robots gate -------------------------------------------------------
    if robots == "auto":
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots = _ROBOTS_CACHE.get(origin)
        if robots is None:
            robots = RobotsPolicy(base_url=origin, user_agent=ua)
            _ROBOTS_CACHE[origin] = robots
    if robots is not None:
        path = urlparse(url).path or "/"
        if not robots.can_fetch(path):
            raise RobotsDisallowedError(
                f"robots.txt disallows fetching {url} — aborting to respect "
                f"crawl rules (source={source_id})"
            )

    if limiter is None:
        limiter = _limiter_for(source_id or "_default", interval)

    retryable_http = {429, 500, 502, 503, 504}
    maxlag_s = float(pol.get("maxlag", 5))

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        limiter.wait()
        try:
            resp = getter.get(
                url, params=params, headers=req_headers, timeout=timeout
            )
        except Exception as exc:  # connection error etc. — retry w/ backoff
            last_exc = exc
            if attempt < max_retries:
                real_sleep(min(2 ** attempt, 30))
                continue
            raise

        if resp.status_code in retryable_http:
            retry_after = resp.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(2 ** attempt, 30)
            if attempt < max_retries:
                real_sleep(delay)
                continue
            resp.raise_for_status()

        resp.raise_for_status()

        # MediaWiki maxlag / ratelimited arrive as HTTP 200 with a JSON error.
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "json" in ctype:
            try:
                code = (resp.json().get("error") or {}).get("code", "")
            except Exception:
                code = ""
            if code in {"maxlag", "ratelimited"} and attempt < max_retries:
                retry_after = resp.headers.get("Retry-After")
                real_sleep(float(retry_after) if retry_after else maxlag_s)
                continue

        return resp

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"polite_get exhausted retries for {url}")


# ---------------------------------------------------------------------------
# License model (SPEC §1) — Openverse-style URL->token normalisation
# ---------------------------------------------------------------------------

#: URL-fragment -> SPDX-style token (Openverse constants.py pattern, R4 §1.1).
#: ``license_of()`` implementations MUST route through this rather than trust
#: free-text license names. Matched case-insensitively, longest fragment first.
LICENSE_URL_MAP: Dict[str, str] = {
    "licenses/by-nc-nd/4.0": "CC-BY-NC-ND-4.0",
    "licenses/by-nc-nd/3.0": "CC-BY-NC-ND-3.0",
    "licenses/by-nc-sa/4.0": "CC-BY-NC-SA-4.0",
    "licenses/by-nc-sa/3.0": "CC-BY-NC-SA-3.0",
    "licenses/by-nc-sa/2.5": "CC-BY-NC-SA-2.5",
    "licenses/by-nc/4.0": "CC-BY-NC-4.0",
    "licenses/by-nc/3.0": "CC-BY-NC-3.0",
    "licenses/by-nc/2.5": "CC-BY-NC-2.5",
    "licenses/by-nd/4.0": "CC-BY-ND-4.0",
    "licenses/by-nd/3.0": "CC-BY-ND-3.0",
    "licenses/by-sa/4.0": "CC-BY-SA-4.0",
    "licenses/by-sa/3.0": "CC-BY-SA-3.0",
    "licenses/by-sa/2.5": "CC-BY-SA-2.5",
    "licenses/by/4.0": "CC-BY-4.0",
    "licenses/by/3.0": "CC-BY-3.0",
    "licenses/by/2.5": "CC-BY-2.5",
    "licenses/sampling+/1.0": "LicenseRef-sampling-plus-1.0",
    "licenses/sampling/1.0": "LicenseRef-sampling-1.0",
    "publicdomain/zero/1.0": "CC0-1.0",
    "publicdomain/mark/1.0": "LicenseRef-public-domain",
    "publicdomain": "LicenseRef-public-domain",
}

#: SPDX token -> (license_tier, release_ok) policy pair (SPEC §1.1/§1.3).
#: ND-family licenses have no dedicated tier in the frozen enum; verbatim
#: redistribution is legal under ND but we conservatively class them
#: ``study-only``/``no`` pending a user decision (adapters may record context
#: in ``copyright_notice``).
LICENSE_TOKEN_INFO: Dict[str, tuple] = {
    "CC0-1.0": ("cc0", "yes"),
    "LicenseRef-public-domain": ("pd", "yes"),
    "CC-BY-4.0": ("cc-by", "yes"),
    "CC-BY-3.0": ("cc-by", "yes"),
    "CC-BY-2.5": ("cc-by", "yes"),
    "CC-BY-SA-4.0": ("cc-by-sa", "conditional"),
    "CC-BY-SA-3.0": ("cc-by-sa", "conditional"),
    "CC-BY-SA-2.5": ("cc-by-sa", "conditional"),
    "CC-BY-NC-4.0": ("cc-by-nc", "no"),
    "CC-BY-NC-3.0": ("cc-by-nc", "no"),
    "CC-BY-NC-2.5": ("cc-by-nc", "no"),
    "CC-BY-NC-SA-4.0": ("cc-by-nc", "no"),
    "CC-BY-NC-SA-3.0": ("cc-by-nc", "no"),
    "CC-BY-NC-SA-2.5": ("cc-by-nc", "no"),
    "CC-BY-ND-4.0": ("study-only", "no"),
    "CC-BY-ND-3.0": ("study-only", "no"),
    "CC-BY-NC-ND-4.0": ("cc-by-nc", "no"),
    "CC-BY-NC-ND-3.0": ("cc-by-nc", "no"),
    "LicenseRef-sampling-plus-1.0": ("study-only", "no"),
    "LicenseRef-sampling-1.0": ("study-only", "no"),
    "proprietary": ("study-only", "no"),
    "unknown": ("study-only", "no"),
}


def license_from_url(url: Optional[str]) -> Optional[str]:
    """Normalise a license deed URL to an SPDX-style token via
    ``LICENSE_URL_MAP`` (longest fragment match wins). Returns None when no
    fragment matches — callers then fall back to ``license_ref_default``."""
    if not url:
        return None
    low = url.lower()
    for frag in sorted(LICENSE_URL_MAP, key=len, reverse=True):
        if frag in low:
            return LICENSE_URL_MAP[frag]
    return None


def license_policy_for(token: Optional[str]) -> tuple:
    """``(license_tier, release_ok)`` for an SPDX token; ``(None, None)`` when
    the token is unknown so callers fall back to registry defaults."""
    if not token:
        return (None, None)
    return LICENSE_TOKEN_INFO.get(token, (None, None))


@dataclass
class LicenseInfo:
    """Per-item license resolution returned by ``license_of()`` (SPEC §6.2).

    May only *downgrade* the registry tier default — upgrades are recorded
    user decisions on items (``modified_note``), not adapter logic.
    """

    license: Optional[str] = None            # SPDX token / LicenseRef-*
    license_url: Optional[str] = None        # deed/legal URL
    license_tier: Optional[str] = None       # resolved tier (else registry default)
    release_ok: Optional[str] = None         # yes | conditional | no
    copyright_notice: Optional[str] = None   # licensor-supplied notice

    def apply_to(self, d: dict) -> dict:
        """Stamp resolved fields onto a catalog entry / song dict."""
        for k in ("license", "license_url", "license_tier", "release_ok",
                  "copyright_notice"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d


# ---------------------------------------------------------------------------
# CatalogEntry — the _catalog.json row (SPEC §6.2 + W1 task fields)
# ---------------------------------------------------------------------------

#: Terminal catalog statuses are never reprocessed by the fetch loop.
TERMINAL_STATUSES = {"fetched", "skipped", "dropped"}
#: Active statuses: ``pending`` is new work; ``failed`` is retried on resume
#: (mirrors toolshop/batch.py: completed/skipped_long skipped, failed retried).
ACTIVE_STATUSES = {"pending", "failed"}
ALL_STATUSES = TERMINAL_STATUSES | ACTIVE_STATUSES


@dataclass
class CatalogEntry:
    """One work-queue row in ``_catalog.json``.

    Serialised dicts carry the union of SPEC §6.2 fields and the megaplan W1
    task fields: ``source``/``external_id``/``artist``/``license_ref`` are
    emitted as aliases of ``source_id``/``foreign_identifier``/
    ``creator``-fallback/``license``, and ``fetched`` mirrors
    ``status == 'fetched'`` (read-side ignores it; ``status`` is canonical).
    """

    source_id: str
    foreign_identifier: str = ""
    title: str = ""
    url: str = ""                                # fetch/page URL
    artist: Optional[str] = None                 # display artist (defaults to creator)
    creator: str = ""                            # TASL Author
    creator_url: Optional[str] = None
    source_url: Optional[str] = None             # TASL Source landing page
    license: Optional[str] = None                # SPDX token / LicenseRef-*
    license_url: Optional[str] = None
    license_tier: Optional[str] = None
    release_ok: Optional[str] = None             # yes | conditional | no
    copyright_notice: Optional[str] = None
    category: str = ""                           # corpus subdir slug
    status: str = "pending"                      # pending|fetched|skipped|failed|dropped
    drop_reason: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        """Dedup identity inside a catalog: upstream id, else (title,url)."""
        if self.foreign_identifier:
            return f"fid:{self.foreign_identifier}"
        return f"tu:{norm_key(self.title, self.artist or self.creator)}:{self.url}"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            # task-named fields
            "source": self.source_id,
            "external_id": self.foreign_identifier,
            "title": self.title,
            "artist": self.artist if self.artist is not None else (self.creator or None),
            "url": self.url,
            "license_tier": self.license_tier,
            "license_ref": self.license,
            "release_ok": self.release_ok,
            "fetched": self.status == "fetched",
            # spec §6.2 fields
            "foreign_identifier": self.foreign_identifier,
            "creator": self.creator,
            "creator_url": self.creator_url,
            "source_url": self.source_url,
            "license": self.license,
            "license_url": self.license_url,
            "copyright_notice": self.copyright_notice,
            "category": self.category,
            "status": self.status,
            "drop_reason": self.drop_reason,
            "meta": self.meta,
        }
        return d


def entry_from_dict(d: Dict[str, Any], source_id: str = "") -> CatalogEntry:
    """Rebuild a CatalogEntry from a stored dict, tolerating alias-only rows."""
    return CatalogEntry(
        source_id=d.get("source_id") or d.get("source") or source_id,
        foreign_identifier=str(d.get("foreign_identifier") or d.get("external_id") or ""),
        title=d.get("title") or "",
        url=d.get("url") or "",
        artist=d.get("artist"),
        creator=d.get("creator") or d.get("artist") or "",
        creator_url=d.get("creator_url"),
        source_url=d.get("source_url"),
        license=d.get("license") or d.get("license_ref"),
        license_url=d.get("license_url"),
        license_tier=d.get("license_tier"),
        release_ok=d.get("release_ok"),
        copyright_notice=d.get("copyright_notice"),
        category=d.get("category") or "",
        status=d.get("status") or "pending",
        drop_reason=d.get("drop_reason"),
        meta=d.get("meta") or {},
    )


# ---------------------------------------------------------------------------
# TASL credit line — computed at export, never stored (SPEC §1.3)
# ---------------------------------------------------------------------------


def tasl_credit(item: Dict[str, Any]) -> str:
    """Render a TASL credit line from a stored song/catalog dict.

    Format: ``"<title>" by <creator> — source: <url> — license: <token> (<url>)``
    plus optional copyright notice / modification note. Attribution is
    *computed* per the Openverse pattern (R4 §3); missing fields surface as
    ``unknown`` so gaps are visible in a CREDITS.md audit.
    """
    get = item.get if hasattr(item, "get") else lambda k, d=None: getattr(item, k, d)
    title = get("title") or "untitled"
    creator = get("creator") or get("primary_artist") or get("artist") or "unknown"
    source_url = get("source_url") or get("url") or ""
    license_tok = get("license") or get("license_ref") or "unknown"
    license_url = get("license_url")

    parts = [f'"{title}" by {creator}']
    if source_url:
        parts.append(f"source: {source_url}")
    lic = license_tok + (f" ({license_url})" if license_url else "")
    parts.append(f"license: {lic}")
    if get("copyright_notice"):
        parts.append(str(get("copyright_notice")))
    if get("modified_note"):
        parts.append(f"note: {get('modified_note')}")
    return " — ".join(parts)


# ---------------------------------------------------------------------------
# Text/path helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Filesystem-safe slug (extract_artists.py:63-66 pattern, kept verbatim)."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "unknown"


def norm_key(title: str, artist: str) -> tuple:
    """Normalised (title, primary_artist) dedup key (extract_artists.py:69-74)."""
    return (
        re.sub(r"[^\w\s]", "", (title or "").lower()).strip(),
        re.sub(r"[^\w\s]", "", (artist or "").lower()).strip(),
    )


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def detect_script(text: Optional[str]) -> Optional[str]:
    """``'cyrillic'`` when the text contains Cyrillic letters, ``'latin'`` when
    only Latin letters, else ``None``. Equivalent to lyricsdb ``_has_cyrillic``
    semantics (sr corpora keep the original script in ``raw_lyrics``)."""
    if not text:
        return None
    if _CYRILLIC_RE.search(text):
        return "cyrillic"
    if re.search(r"[A-Za-zÀ-ɏ]", text):
        return "latin"
    return None


def song_base_name(song: Dict[str, Any]) -> str:
    """``<artist-slug>-<title-slug>`` filename base (existing convention)."""
    artist = song.get("primary_artist") or song.get("artist") or "unknown"
    title = song.get("title") or "unknown"
    return f"{slugify(str(artist))}-{slugify(str(title))}"


# ---------------------------------------------------------------------------
# Song JSON v2 writer (SPEC §3.3)
# ---------------------------------------------------------------------------

#: License/provenance block fields (song JSON v2, SPEC §3.3). ``license`` maps
#: to the DB column ``license_ref`` downstream (SPEC §4.1).
SONG_LICENSE_FIELDS = (
    "corpus", "source", "foreign_identifier", "source_url",
    "creator", "creator_url", "copyright_notice", "modified_note",
    "license", "license_url", "license_tier", "release_ok", "derived_from",
    "script", "synced_lyrics", "lyricsfile", "meta",
)

#: Safe defaults (SPEC §4.1): never auto-release what an adapter forgot to tag.
SONG_LICENSE_DEFAULTS = {
    "license_tier": "study-only",
    "release_ok": "no",
}


def normalise_song(song: Dict[str, Any]) -> Dict[str, Any]:
    """Fill song JSON v2 defaults in place: artist aliases, featured list,
    license block defaults (``study-only``/``no`` — safe side)."""
    if not song.get("primary_artist"):
        song["primary_artist"] = song.get("artist") or "Unknown"
    if not song.get("artist"):
        song["artist"] = song["primary_artist"]
    song.setdefault("featured_artists", [])
    song.setdefault("language", None)
    song.setdefault("sections", [])
    for f in SONG_LICENSE_FIELDS:
        if f in SONG_LICENSE_DEFAULTS:
            song.setdefault(f, SONG_LICENSE_DEFAULTS[f])
        else:
            song.setdefault(f, None)
    if song.get("script") is None:
        song["script"] = detect_script(song.get("raw_lyrics") or song.get("clean_lyrics"))
    return song


def write_song_json(
    song: Dict[str, Any],
    corpus_root: Path,
    category: str,
    *,
    write_txt: bool = True,
) -> Path:
    """Write a song JSON v2 + optional clean-lyrics .txt under
    ``<corpus_root>/<category>/``. UTF-8, ``ensure_ascii=False``.

    Filename: ``<artist-slug>-<title-slug>.json``; on collision with a
    *different* upstream item the foreign identifier is appended so a title
    edit upstream can never silently overwrite a stored song.
    """
    normalise_song(song)
    cat_dir = Path(corpus_root) / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    base = song_base_name(song)
    json_path = cat_dir / f"{base}.json"
    fid = song.get("foreign_identifier")
    if json_path.exists() and fid:
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            if existing.get("foreign_identifier") not in (None, fid):
                json_path = cat_dir / f"{base}-{slugify(str(fid))}.json"
        except Exception:
            json_path = cat_dir / f"{base}-{slugify(str(fid))}.json"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(song, f, indent=2, ensure_ascii=False)

    if write_txt:
        txt_path = json_path.with_suffix(".txt")
        with txt_path.open("w", encoding="utf-8") as f:
            f.write(song.get("clean_lyrics") or "")

    return json_path


# ---------------------------------------------------------------------------
# Per-corpus _index.json writer (license fields ride the index — SPEC §3.3/F8)
# ---------------------------------------------------------------------------

#: License fields copied into every index entry so lyricsdb ``_insert_song``
#: picks them up when joining _index.json by basename (SPEC §3.3).
INDEX_LICENSE_FIELDS = (
    "corpus", "source", "foreign_identifier", "source_url",
    "creator", "creator_url", "copyright_notice", "modified_note",
    "license", "license_url", "license_tier", "release_ok", "derived_from",
    "script", "language",
)


def build_index(corpus_root: Path) -> Dict[str, Any]:
    """Scan ``<corpus_root>/<category>/*.json`` and build index + dedup log.

    Corpus-scoped dedup (SPEC §4.3): a song is skipped when its normalised
    (title, primary_artist) key OR its ``foreign_identifier`` was already seen
    *within this corpus*; skipped items land in the dedup log. Cross-corpus
    duplicates are correct (F9) and unaffected.
    """
    corpus_root = Path(corpus_root)
    index: List[Dict[str, Any]] = []
    dedup_log: List[Dict[str, Any]] = []
    seen_keys = set()
    seen_fids = set()

    for json_path in sorted(corpus_root.glob("*/*.json")):
        if json_path.name.startswith("_"):
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        title = data.get("title", "Unknown")
        primary = data.get("primary_artist") or data.get("artist") or "Unknown"
        key = norm_key(title, primary)
        fid = data.get("foreign_identifier")
        if key in seen_keys or (fid is not None and fid in seen_fids):
            dedup_log.append({
                "title": title,
                "primary_artist": primary,
                "foreign_identifier": fid,
                "json_path": str(json_path.relative_to(corpus_root)),
            })
            continue
        seen_keys.add(key)
        if fid is not None:
            seen_fids.add(fid)

        category = data.get("category") or json_path.parent.name
        txt_path = json_path.with_suffix(".txt")
        entry = {
            "title": title,
            "primary_artist": primary,
            "featured_artists": data.get("featured_artists", []),
            "category": category,
            "url": data.get("url", ""),
            "status": "completed",
            "json_path": str(json_path.relative_to(corpus_root)).replace("\\", "/"),
            "txt_path": str(txt_path.relative_to(corpus_root)).replace("\\", "/")
            if txt_path.exists() else None,
        }
        if data.get("genius_song_id") is not None:
            entry["genius_song_id"] = data.get("genius_song_id")
        for f in INDEX_LICENSE_FIELDS:
            entry[f] = data.get(f)
        index.append(entry)

    return {"index": index, "dedup_log": dedup_log}


def write_index(corpus_root: Path) -> Dict[str, Any]:
    """Rebuild and write ``_index.json`` + ``_dedup_log.json`` for a corpus."""
    corpus_root = Path(corpus_root)
    result = build_index(corpus_root)
    index_path = corpus_root / "_index.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(result["index"], f, indent=2, ensure_ascii=False)
    dedup_path = corpus_root / "_dedup_log.json"
    with dedup_path.open("w", encoding="utf-8") as f:
        json.dump(result["dedup_log"], f, indent=2, ensure_ascii=False)
    return result


# ---------------------------------------------------------------------------
# _catalog.json low-level IO (SPEC §6.2) + resumable-batch helpers
# ---------------------------------------------------------------------------

CATALOG_VERSION = 1


def load_catalog(path: Path) -> Dict[str, Any]:
    """Load a ``_catalog.json`` doc; returns an empty doc skeleton when the
    file is absent or unreadable (never raises on a missing queue)."""
    path = Path(path)
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(doc, list):  # tolerate a bare entry list
                doc = {"entries": doc}
            doc.setdefault("entries", [])
            return doc
        except Exception:
            pass
    return {
        "version": CATALOG_VERSION,
        "source": None,
        "corpus": None,
        "created": None,
        "updated": None,
        "entries": [],
    }


def save_catalog(doc: Dict[str, Any], path: Path) -> None:
    """Flush the catalog doc — called after every item status change so the
    queue is a resumable status file (SPEC §3.1, AGENTS.md batch pattern)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc["updated"] = datetime.now().isoformat()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def load_status(path: Path) -> Dict[str, Any]:
    """Generic status-JSON load (batch.py ``load_or_create_status`` analogue)."""
    path = Path(path)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_status(status: Dict[str, Any], path: Path) -> None:
    """Flush a status JSON per item (UTF-8, ensure_ascii=False)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")


def is_terminal(status: Optional[str]) -> bool:
    return status in TERMINAL_STATUSES


def pending_slice(
    entries: Iterable[Dict[str, Any]],
    *,
    resume: bool = True,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Select work-queue entries for the fetch loop.

    ``resume=True`` processes ``pending`` + ``failed`` and skips the terminal
    statuses (``fetched``/``skipped``/``dropped``) — the skip-completed rule.
    ``resume=False`` reprocesses everything except ``skipped``/``dropped``
    (deliberate adapter decisions are never silently re-queued). ``offset``
    applies to the *eligible* list, then ``limit`` — the same slicing order as
    ``toolshop.batch.discover_files``.
    """
    eligible: List[Dict[str, Any]] = []
    for e in entries:
        st = e.get("status") or "pending"
        if st in ("skipped", "dropped"):
            continue
        if resume and st == "fetched":
            continue
        if category and e.get("category") != category:
            continue
        eligible.append(e)
    if offset:
        eligible = eligible[offset:]
    if limit is not None and limit >= 0:
        eligible = eligible[:limit]
    return eligible
