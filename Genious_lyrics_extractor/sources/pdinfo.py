"""PDInfo title-index adapter — ``fetch_policy='catalog-only'`` (SPEC §6.3/§9).

Harvests PDInfo's public-domain song **TITLE lists** into the ``pdinfo``
corpus catalog. Song titles are uncopyrightable facts (US Copyright Office
Circular 33, R2 §5) so catalog harvest is auto-OK; the site hosts **no
lyric text** — each emitted row is a lookup seed for a future
wikisource/gutenberg fetch (``meta.fetch_hint='resolve-via-wikisource'``).

Hard facts this adapter encodes:

- Every row's PD claim means *"a pre-1930 sheet-music publication exists
  somewhere"* (PDInfo's own methodology) — **NOT** documentation →
  ``meta.pd_claim='unverified'`` (SPEC §9). PD status is only proven when a
  wikisource/gutenberg copy is actually fetched downstream.
- Lyric snippets on the list pages (``V - ``/``C - ``/``N - ``/``P - ``
  blocks) are **never parsed or stored** — this is a title index, not a
  text source.
- Fetch-once, cache-forever: list-page HTML is cached under
  ``<data>/lyrics/pdinfo/_cache/pages/`` (data/ boundary, never
  committed); a second run replays from cache with zero requests.

Contract (SPEC §6.3): ships ``iter_catalog`` + ``license_of``;
``fetch_lyrics`` must not exist — there is no lyric to fetch.
"""

from __future__ import annotations

import html as _html
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from ._common import (
        CatalogEntry,
        LicenseInfo,
        RateLimiter,
        polite_get,
        slugify,
    )
    from . import registry as _registry
except ImportError:  # sources/ dir directly on sys.path
    from _common import (  # type: ignore
        CatalogEntry,
        LicenseInfo,
        RateLimiter,
        polite_get,
        slugify,
    )
    import registry as _registry  # type: ignore

SOURCE_ID = "pdinfo"
BASE_URL = "https://www.pdinfo.com"
PD_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
FETCH_HINT = "resolve-via-wikisource"
PD_CLAIM = "unverified"

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_GENRE_PAGES = (
    "hymns", "spirituals", "christmas-songs",
    "children-songs", "patriotic-songs", "popular-songs",
)
_YEAR_RANGE = range(1923, 1930)  # 1923-1929 per R2 §5


# ---------------------------------------------------------------------------
# Page map
# ---------------------------------------------------------------------------


def default_pages() -> List[Tuple[str, str, str]]:
    """The frozen list-page set (R2 §5): ``(url_path, list_kind, label)``.

    - ``pd-song-list/pd-song-list-best-<a-z>.php`` — "Best Known" A-Z
    - ``pd-song-list/pd-song-list-less-<a-z>.php`` — "Less Known" A-Z
      (some letters legitimately absent → 404 is tolerated as empty)
    - ``pd-music-genres/pd-<genre>.php`` — genre lists
    - ``pd-music-genres/pd-popular-songs-<year>.php`` — per-year lists
    """
    pages: List[Tuple[str, str, str]] = []
    for letter in _LETTERS:
        pages.append((
            f"pd-song-list/pd-song-list-best-{letter}.php",
            "best-known", f"best-{letter}",
        ))
    for letter in _LETTERS:
        pages.append((
            f"pd-song-list/pd-song-list-less-{letter}.php",
            "less-known", f"less-{letter}",
        ))
    for genre in _GENRE_PAGES:
        pages.append((
            f"pd-music-genres/pd-{genre}.php",
            "genre", f"genre-{genre}",
        ))
    for year in _YEAR_RANGE:
        pages.append((
            f"pd-music-genres/pd-popular-songs-{year}.php",
            "year", f"year-{year}",
        ))
    return pages


def _corpus_root(data_dir: Optional[Path] = None) -> Path:
    """``<data>/lyrics/pdinfo`` via the registry corpus resolution."""
    row = _registry.get(SOURCE_ID)
    root = _registry.corpus_root(row, data_dir)
    assert root is not None, "pdinfo row must carry corpus_tag"
    return root


def _cache_dir(data_dir: Optional[Path], cache_dir: Optional[Path]) -> Path:
    if cache_dir is not None:
        return Path(cache_dir)
    return _corpus_root(data_dir) / "_cache" / "pages"


# ---------------------------------------------------------------------------
# Page fetch (fetch-once + disk cache)
# ---------------------------------------------------------------------------


def _cache_name(url_path: str) -> str:
    return url_path.replace("/", "__") + ".html"


def _fetch_page(
    url_path: str,
    *,
    session: Any = None,
    cache_dir: Optional[Path] = None,
    limiter: Optional[RateLimiter] = None,
    timeout: float = 30.0,
) -> str:
    """Return a list page's HTML — disk cache first, ``polite_get`` on miss.

    Cache hits need no session at all (offline replay). A 404 is cached as
    an empty document (absent less-known letters are normal); other HTTP
    errors raise after polite_get's own retry/backoff so an aborted run can
    simply be re-run — cached pages are never re-fetched.
    """
    cache_dir = Path(cache_dir) if cache_dir else None
    cache_path = cache_dir / _cache_name(url_path) if cache_dir else None
    if cache_path is not None and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    url = f"{BASE_URL}/{url_path}"
    try:
        resp = polite_get(url, SOURCE_ID, session=session,
                          timeout=timeout, limiter=limiter)
    except Exception as exc:
        # polite_get raises for non-2xx before we see the response — a 404
        # (absent less-known letters are normal) is an empty page, not an
        # error; other failures abort so a re-run resumes from the cache.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 404 or "404" in str(exc):
            text = ""
        else:
            raise
    else:
        text = resp.text
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# List-page parser — machine-generated table markup, regex is sufficient
# ---------------------------------------------------------------------------

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TITLE_TD_RE = re.compile(
    r'<td\s+class="songTitle"[^>]*>(.*?)</td>', re.S | re.I)
_TD_RE = re.compile(r'<td\b[^>]*>(.*?)</td>', re.S | re.I)
_CAT_RE = re.compile(r'<span\s+class="cat"[^>]*>(.*?)</span>', re.S | re.I)
_YEAR_RE = re.compile(
    r'(?:<b>|<span\s+class="b">)\s*(\d{4})\s*(?:</b>|</span>)', re.I)
_SNIPPET_RE = re.compile(
    r'(?:<b>|<span\s+class="b">)\s*[VCNP]\s*-', re.I)
_CART_RE = re.compile(r"addCart\('([A-Za-z]+\d+)[RD]?'\)", re.I)
_ALTTITLE_RE = re.compile(
    r'<td\s+class="altTitle"[^>]*>(.*?)</td>\s*'
    r'<td[^>]*>\s*See\s+<span\s+class="alt"[^>]*>(.*?)</span>',
    re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# role markers inside attribution text: "w.m.", "w.", "m.", <i>music</i>…
# (lookahead, not \b, after the group — "w.m." ends in '.' where a word
# boundary does not exist before a space)
_ROLE_TOKEN_RE = re.compile(
    r"\b(?:w\.m\.|m\.w\.|w\.|m\.|music|words|text|tune)(?=\W|$)", re.I)


def _clean(fragment: str) -> str:
    """Strip tags, unescape entities, collapse whitespace."""
    txt = _TAG_RE.sub("", fragment)
    return _WS_RE.sub(" ", _html.unescape(txt)).strip()


def _clean_creator(attribution: str) -> str:
    """Remove words/music role tokens from an attribution string.

    'w.m. Arthur Fields, Walter Donaldson' -> 'Arthur Fields, Walter
    Donaldson'; 'Lyte, Henry F. music, W.H. Monk words' -> 'Lyte, Henry F.,
    W.H. Monk'; 'Traditional' stays 'Traditional'."""
    txt = _ROLE_TOKEN_RE.sub("", attribution)
    txt = re.sub(r"[,\s]*,[,\s]*", ", ", txt)  # collapse stray commas
    return txt.strip(" ,;-").strip()


def _parse_row(row_html: str) -> Optional[Dict[str, Any]]:
    """Parse one <tr> into a raw row dict, or None for non-song rows."""
    m = _ALTTITLE_RE.search(row_html)
    if m:
        return {
            "row_kind": "see-also",
            "title": _clean(m.group(1)),
            "canonical_title": _clean(m.group(2)),
            "genre": "", "year": None, "attribution": "", "product_id": "",
        }

    tm = _TITLE_TD_RE.search(row_html)
    if not tm:
        return None
    inner = tm.group(1)
    genre = ""
    gm = _CAT_RE.search(inner)
    if gm:
        genre = _clean(gm.group(1))
        inner = inner[:gm.start()]
    title = _clean(inner)
    if not title:
        return None

    # Attribution cell = the <td> after the songTitle td, truncated at the
    # first V/C/N/P marker — lyric-snippet dbk blocks are NEVER harvested.
    # (dbk spans nest <span class="b"> so they can't be regex-extracted
    # individually; bounding by the <td> is safe — tds never nest here.)
    after = row_html[tm.end():]
    cm = _TD_RE.search(after)
    cell = cm.group(1) if cm else ""
    sm = _SNIPPET_RE.search(cell)
    region = cell[:sm.start()] if sm else cell
    ym = _YEAR_RE.search(region)
    year = int(ym.group(1)) if ym else None
    attribution = _clean(_YEAR_RE.sub("", region, count=1)).lstrip("-").strip()

    pm = _CART_RE.search(row_html)
    return {
        "row_kind": "song",
        "title": title,
        "canonical_title": "",
        "genre": genre,
        "year": year,
        "attribution": attribution,
        "product_id": pm.group(1) if pm else "",
    }


def parse_list_page(
    html_text: str,
    *,
    list_kind: str,
    list_label: str,
    page_url: str = "",
) -> List[Dict[str, Any]]:
    """Parse a PDInfo list page into raw row dicts (titles + facts only)."""
    rows: List[Dict[str, Any]] = []
    if not html_text:
        return rows
    for row_html in _ROW_RE.findall(html_text):
        row = _parse_row(row_html)
        if row is None:
            continue
        row["list_kind"] = list_kind
        row["list_label"] = list_label
        row["page_url"] = page_url
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


def _entry_from_raw(raw: Dict[str, Any]) -> CatalogEntry:
    """Build a CatalogEntry from a parsed row — title facts only."""
    if raw["row_kind"] == "see-also":
        fid = f"pdinfo-xref-{raw['list_label']}-{slugify(raw['title'])}"
    elif raw["product_id"]:
        fid = f"pdinfo-{raw['product_id']}"
    else:
        fid = f"pdinfo-{raw['list_label']}-{slugify(raw['title'])}"

    creator = _clean_creator(raw["attribution"]) if raw["attribution"] else ""
    meta: Dict[str, Any] = {
        "lists": [raw["list_label"]],
        "list_kind": raw["list_kind"],
        "genre": raw["genre"],
        "year": raw["year"],
        "attribution": raw["attribution"],
        "pd_claim": PD_CLAIM,
        "fetch_hint": FETCH_HINT,
        "row_kind": raw["row_kind"],
    }
    if raw["row_kind"] == "see-also":
        meta["canonical_title"] = raw["canonical_title"]

    return CatalogEntry(
        source_id=SOURCE_ID,
        foreign_identifier=fid,
        title=raw["title"],
        artist=creator or None,
        creator=creator,
        url=raw["page_url"],
        source_url=raw["page_url"],
        license="LicenseRef-public-domain",
        license_url=PD_MARK_URL,
        license_tier="pd",
        release_ok="yes",
        category="",  # pdinfo emits catalog rows only — no song dirs (§3.2)
        status="pending",
        meta=meta,
    )


def _merge(existing: CatalogEntry, new: CatalogEntry) -> None:
    """Merge a duplicate (same song on a second list): union list
    provenance, fill empty attribution/genre/year fields."""
    seen = existing.meta.setdefault("lists", [])
    for label in new.meta.get("lists", []):
        if label not in seen:
            seen.append(label)
    for key in ("genre", "year", "attribution"):
        if not existing.meta.get(key) and new.meta.get(key):
            existing.meta[key] = new.meta[key]
    if not existing.creator and new.creator:
        existing.creator = new.creator
        existing.artist = new.artist


def iter_catalog(
    limit: Optional[int] = None,
    offset: int = 0,
    *,
    session: Any = None,
    cache_dir: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    pages: Optional[List[Tuple[str, str, str]]] = None,
    limiter: Optional[RateLimiter] = None,
) -> Iterator[CatalogEntry]:
    """Emit one CatalogEntry per PD title on the PDInfo list pages.

    ``limit``/``offset`` slice the merged entry stream (SPEC §6.3).
    ``pages`` may subset the default ~64-page map (tests/pilots). Pages are
    fetched once into ``cache_dir`` and replayed offline afterwards.
    """
    cache = _cache_dir(data_dir, cache_dir)
    merged: Dict[str, CatalogEntry] = {}
    order: List[str] = []

    for url_path, kind, label in (pages if pages is not None else default_pages()):
        text = _fetch_page(
            url_path, session=session, cache_dir=cache, limiter=limiter,
        )
        page_url = f"{BASE_URL}/{url_path}"
        for raw in parse_list_page(
            text, list_kind=kind, list_label=label, page_url=page_url
        ):
            entry = _entry_from_raw(raw)
            if entry.foreign_identifier in merged:
                _merge(merged[entry.foreign_identifier], entry)
            else:
                merged[entry.foreign_identifier] = entry
                order.append(entry.foreign_identifier)

    entries = [merged[k] for k in order]
    if offset:
        entries = entries[offset:]
    if limit is not None:
        entries = entries[:limit]
    yield from entries


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """PD title facts — the catalog row itself is release-safe
    (``pd``/``LicenseRef-public-domain``/``yes``); the underlying song's PD
    *claim* stays ``meta.pd_claim='unverified'`` until a wikisource/
    gutenberg copy is fetched downstream (SPEC §9)."""
    return LicenseInfo(
        license="LicenseRef-public-domain",
        license_url=PD_MARK_URL,
        license_tier="pd",
        release_ok="yes",
    )


# NOTE: no fetch_lyrics() here — pdinfo is a title index; there are no
# lyrics on the site to fetch (SPEC §1.2 catalog-only contract, §9).
