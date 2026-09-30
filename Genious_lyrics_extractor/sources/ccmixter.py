"""ccMixter acappella adapter (SPEC §6.3, §9; R1 research handoff).

Queries the ccHost Query API — ``GET https://ccmixter.org/api/query``,
keyless, ``f=json&dataview=default`` — for ``tags=acappella`` pells, resolves
each item's license from its ``license_url`` (LICENSE_URL_MAP, never free-text
names), and extracts lyric text out of ``upload_description_plain`` via
header detection + verse-run analysis (R1 §2: ~45-60% of pells carry usable
lyric text under informal headers like ``Lyric:`` / ``WORDS`` /
``LYRICS/SPOKEN WORD:`` — or as bare verse stanzas after/before the prose).

POLICY — robots/API conflict (GATE R, binding):
    ``ccmixter.org/robots.txt`` carries ``Disallow: /api/`` for
    ``User-agent: *`` AND a full ``MLBot`` ban, while the site's own about
    page (http://t.ccmixter.org/about) explicitly declares the Query API "an
    open, publicly available interface … for public use, especially by 3rd
    party" services. GATE R (user decision, recorded in the megaplan + SPEC
    roster) resolved this conflict as **polite auto-fetch**: we call the API
    with the robots gate deliberately OFF (``polite_get(robots=None)`` — do
    NOT pass ``robots="auto"`` here, it would block the sanctioned API path),
    at the registry pace of ≥1.5 s between requests, with the descriptive
    contact User-Agent from the registry ``politeness`` block. ``MLBot`` is
    never spoofed. If the site revokes the open-API statement, downgrade to
    ``catalog-only`` per R1 §4.

QUIRK — ``X-JSON`` response header:
    ccHost echoes the *entire* JSON payload in an ``X-JSON`` HTTP header.
    For ``dataview=default`` pages this single header line exceeds Python's
    ``http.client._MAXLINE`` (65536) and kills every request with
    ``LineTooLong``. ``_raise_http_header_limit()`` lifts that constant —
    module-local necessity, applied before each API call.

Lyric extraction (R1 §2 + live probe of 104 items, 2026-09-30):
    1. Header strategy — a standalone marker line (``Lyrics:``, ``WORDS``,
       ``LYRICS/SPOKEN WORD:``, ``Vox:``, ``Poem:`` …) opens the lyric block;
       the longest verse-like block run *after* it is the lyric text.
    2. Verse-run strategy — when no header exists, the longest run of
       verse-like blocks (several short lines, few sentence-final periods)
       anywhere in the description is taken; bare-stanza pells and
       lyrics-then-prose descriptions are both covered.
    Items failing the lyric gates raise ``DropItem('no-lyric-text')`` — the
    runner records ``status='dropped'`` (SPEC §9).

Lanes: ``lic=by`` + ``lic=pd`` are the default release-safe lane (~1,507
candidates per R1 §2); ``nc``/``sa``/``byncsa``/``splus`` are opt-in study
tiers via ``CCMIXTER_LANES`` env (comma list) or the ``lanes`` kwarg.
"""

from __future__ import annotations

import http.client
import os
import re
from collections import deque
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlencode

try:
    from ._common import (
        CatalogEntry,
        DropItem,
        LicenseInfo,
        license_from_url,
        license_policy_for,
        polite_get,
        slugify,
    )
except ImportError:  # sources/ dir directly on sys.path
    from _common import (  # type: ignore
        CatalogEntry,
        DropItem,
        LicenseInfo,
        license_from_url,
        license_policy_for,
        polite_get,
        slugify,
    )

SOURCE_ID = "ccmixter"
API_URL = "https://ccmixter.org/api/query"

#: Query-format limit cap is admin-set ~100-200 (R1 §1); 100 keeps the
#: ``X-JSON`` header quirk manageable under the raised header limit.
PAGE_SIZE = 100

#: Release-safe default lane (SPEC §9); study tiers are opt-in.
DEFAULT_LANES: Tuple[str, ...] = ("by", "pd")
STUDY_LANES: Tuple[str, ...] = ("nc", "sa", "byncsa", "splus", "ncsplus")
KNOWN_LANES = DEFAULT_LANES + STUDY_LANES
ENV_LANES = "CCMIXTER_LANES"

#: Frozen category slugs (SPEC §3.2) — license-classed so the disk layout is
#: itself release-auditable.
CATEGORY_BY = "acappella-by"
CATEGORY_PD = "acappella-pd"
CATEGORY_NC = "acappella-nc"
CATEGORY_SA = "acappella-sa"

#: PD-dedication mark URL stamped on ccMixter ``lic=pd`` items. ccMixter's
#: public-domain lane is a dedication-by-declaration that PREDATES CC0 — the
#: site has no true CC0 (SPEC §1.3 / R1 §3), yet its API reports
#: ``publicdomain/zero/1.0`` on those uploads. Mapping them to ``CC0-1.0``
#: would mis-record the legal state, so ``_resolve_license`` remaps the
#: resolved token to ``LicenseRef-public-domain`` and rewrites the deed URL
#: to this mark URL.
CCMIXTER_PD_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"

#: Resolved license_tier -> frozen category slug.
TIER_CATEGORY = {
    "cc-by": CATEGORY_BY,
    "pd": CATEGORY_PD,
    "cc0": CATEGORY_PD,
    "cc-by-nc": CATEGORY_NC,
    "cc-by-sa": CATEGORY_SA,
}

#: Lane -> category fallback when the item's license URL is unresolvable
#: (unknown / study-only tokens keep the lane they were discovered under).
LANE_CATEGORY = {
    "by": CATEGORY_BY,
    "pd": CATEGORY_PD,
    "nc": CATEGORY_NC,
    "byncsa": CATEGORY_NC,
    "byncnd": CATEGORY_NC,
    "ncsplus": CATEGORY_NC,
    "sa": CATEGORY_SA,
    "s": CATEGORY_SA,
    "splus": CATEGORY_SA,
    "nod": CATEGORY_SA,
}

_HTTP_MAXLINE_RAISED = False


def _raise_http_header_limit() -> None:
    """Lift ``http.client._MAXLINE`` — ccHost echoes the whole JSON payload
    in an ``X-JSON`` header line which exceeds the 64 KiB default and aborts
    every ``dataview=default`` response with ``LineTooLong``."""
    global _HTTP_MAXLINE_RAISED
    if not _HTTP_MAXLINE_RAISED:
        http.client._MAXLINE = 1 << 20  # 1 MiB — payload echo can be ~40 KiB+
        _HTTP_MAXLINE_RAISED = True


# ---------------------------------------------------------------------------
# license resolution (SPEC §1.3, §6.3 downgrade-only rule)
# ---------------------------------------------------------------------------

#: release_ok restrictiveness rank — license_of may only ever *increase*
#: this number relative to the registry default (never upgrade).
_RELEASE_RANK = {"yes": 0, "conditional": 1, "no": 2}


def _resolve_license(
    license_url: Optional[str],
    license_name: Optional[str] = None,
) -> LicenseInfo:
    """Resolve one item's license from its deed URL.

    ``license_url`` routes through ``license_from_url`` (LICENSE_URL_MAP) per
    SPEC §6.2 — free-text ``license_name`` is never trusted. Unresolvable
    URLs downgrade to ``unknown``/``study-only``/``no`` — an item whose
    license we cannot verify is never release-cleared.
    """
    if not isinstance(license_url, str):
        license_url = None
    token = license_from_url(license_url)
    # SPEC §1.3 / R1 §3: ccMixter ``lic=pd`` items are PD dedications — the
    # site has no CC0, its ``publicdomain/zero/1.0`` report is their PD mark.
    # Remap to LicenseRef-public-domain + the PD mark URL (never CC0-1.0).
    if token == "CC0-1.0":
        token = "LicenseRef-public-domain"
        license_url = CCMIXTER_PD_MARK_URL
    if token is None:
        return LicenseInfo(
            license="unknown",
            license_url=license_url,
            license_tier="study-only",
            release_ok="no",
            copyright_notice=None,
        )
    tier, release = license_policy_for(token)
    if tier is None:  # token without a policy row — safe side
        tier, release = "study-only", "no"
    return LicenseInfo(
        license=token,
        license_url=license_url,
        license_tier=tier,
        release_ok=release,
    )


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Per-item license resolution (SPEC §6.3).

    Resolves ``entry.license_url`` and additionally honours the ccMixter
    ``ccplus`` flag — the CC tier stands but the separately-purchasable
    commercial license is recorded in ``copyright_notice``. Never upgrades a
    catalog entry: an entry already marked more restrictive keeps the safer
    ``release_ok``.
    """
    info = _resolve_license(entry.license_url, entry.meta.get("license_name"))
    meta = entry.meta or {}
    extra = meta.get("upload_extra") or {}
    if (meta.get("ccplus") or extra.get("ccplus")
            or "ccplus" in (extra.get("ccud") or meta.get("ccud") or "")):
        info.copyright_notice = (
            "ccPlus commercial license also available via ccMixter/tunetrack"
        )
    # downgrade-only: never return a release_ok less restrictive than what
    # the catalog row already carries.
    prev = entry.release_ok
    if prev in _RELEASE_RANK and info.release_ok in _RELEASE_RANK:
        if _RELEASE_RANK[info.release_ok] < _RELEASE_RANK[prev]:
            info.release_ok = prev
            if info.license_tier in ("cc-by", "pd", "cc0") and prev != "yes":
                info.license_tier = entry.license_tier or info.license_tier
    return info


def _category_for(tier: Optional[str], lane: str) -> str:
    return TIER_CATEGORY.get(tier or "", LANE_CATEGORY.get(lane, CATEGORY_SA))


# ---------------------------------------------------------------------------
# API access
# ---------------------------------------------------------------------------


def _api_query(
    params: Dict[str, Any],
    *,
    session=None,
    limiter=None,
):
    """One polite GET against the Query API. Returns the parsed JSON list.

    ``robots`` is intentionally NOT passed — GATE R waived robots-strict for
    the openly-documented Query API (see module docstring)."""
    _raise_http_header_limit()
    resp = polite_get(
        API_URL,
        source_id=SOURCE_ID,
        params=params,
        session=session,
        limiter=limiter,
    )
    data = resp.json()
    if isinstance(data, dict):
        # ccHost can wrap: find the first list value.
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    if not isinstance(data, list):
        return []
    return data


def _lane_entries(
    lane: str,
    *,
    session=None,
    limiter=None,
) -> Iterator[CatalogEntry]:
    """Lazily page one ``lic=<lane>`` slice of ``tags=acappella``."""
    api_offset = 0
    while True:
        items = _api_query(
            {
                "f": "json",
                "dataview": "default",
                "tags": "acappella",
                "lic": lane,
                "limit": PAGE_SIZE,
                "offset": api_offset,
            },
            session=session,
            limiter=limiter,
        )
        if not items:
            return
        for item in items:
            entry = _item_to_entry(item, lane)
            if entry is not None:
                yield entry
        if len(items) < PAGE_SIZE:
            return
        api_offset += len(items)


def _item_to_entry(item: Dict[str, Any], lane: str) -> Optional[CatalogEntry]:
    """Map one ``dataview=default`` upload object to a CatalogEntry."""
    fid = item.get("upload_id")
    if fid is None:
        return None
    info = _resolve_license(item.get("license_url"), item.get("license_name"))
    extra = item.get("upload_extra") or {}
    desc_plain = item.get("upload_description_plain")
    desc_html = item.get("upload_description_html")
    if not isinstance(desc_plain, str):
        desc_plain = ""
    if not isinstance(desc_html, str):
        desc_html = ""
    meta: Dict[str, Any] = {
        "license_name": item.get("license_name"),
        "upload_tags": item.get("upload_tags"),
        "usertags": extra.get("usertags"),
        "ccud": extra.get("ccud"),
        "systags": extra.get("systags"),
        "bpm": extra.get("bpm"),
        "ccplus": bool(extra.get("ccplus")),
        "nsfw": bool(extra.get("nsfw")),
        "num_scores": item.get("upload_num_scores"),
        "upload_date": item.get("upload_date_format"),
        "lane": lane,
        "upload_extra": {"ccplus": bool(extra.get("ccplus")),
                          "ccud": extra.get("ccud")},
        # lyric source text rides the catalog — one item fetch saved per pell
        # (politeness budget halves; R1 §2 fields).
        "description_plain": desc_plain,
    }
    if not desc_plain and desc_html:
        meta["description_html"] = desc_html
    if extra.get("ccplus"):
        info.copyright_notice = (
            "ccPlus commercial license also available via ccMixter/tunetrack"
        )
    file_page = item.get("file_page_url") or ""
    title = _fix_mojibake(str(item.get("upload_name") or "")) \
        or f"ccmixter-{fid}"
    creator = _fix_mojibake(
        str(item.get("user_real_name") or item.get("user_name") or ""))
    return CatalogEntry(
        source_id=SOURCE_ID,
        foreign_identifier=str(fid),
        title=title,
        url=file_page,
        artist=creator,
        creator=creator,
        creator_url=item.get("artist_page_url"),
        source_url=file_page or None,
        license=info.license,
        license_url=info.license_url,
        license_tier=info.license_tier,
        release_ok=info.release_ok,
        copyright_notice=info.copyright_notice,
        category=_category_for(info.license_tier, lane),
        meta=meta,
    )


def _resolve_lanes(lanes: Optional[List[str]]) -> List[str]:
    """Lane order: explicit kwarg > ``CCMIXTER_LANES`` env > release-safe
    default ``(by, pd)`` (SPEC §9)."""
    if lanes is None:
        env = os.environ.get(ENV_LANES)
        if env:
            lanes = [x.strip() for x in env.split(",") if x.strip()]
    if lanes is None:
        return list(DEFAULT_LANES)
    bad = [x for x in lanes if x not in LANE_CATEGORY]
    if bad:
        raise ValueError(
            f"unknown ccmixter lic lane(s) {bad} — known: {sorted(LANE_CATEGORY)}"
        )
    return list(lanes)


def _round_robin(iterators: List[Iterator[CatalogEntry]]) -> Iterator[CatalogEntry]:
    """Interleave lane streams so a bounded slice sees every license class."""
    q = deque(iterators)
    while q:
        it = q.popleft()
        try:
            yield next(it)
            q.append(it)
        except StopIteration:
            pass


def iter_catalog(
    limit: Optional[int] = None,
    offset: int = 0,
    *,
    lanes: Optional[List[str]] = None,
    session=None,
    limiter=None,
) -> Iterator[CatalogEntry]:
    """Emit one ``CatalogEntry`` per acappella pell (SPEC §6.3).

    Default lane: ``lic=by`` + ``lic=pd`` (release-safe, ~1,507 items per R1);
    study tiers opt in via ``lanes``/``CCMIXTER_LANES``. Lanes are round-robin
    interleaved so ``--limit N`` pilots cover every license class; ``offset``
    then ``limit`` slice the merged stream.
    """
    lane_list = _resolve_lanes(lanes)
    streams = [
        _lane_entries(lane, session=session, limiter=limiter)
        for lane in lane_list
    ]
    merged = _round_robin(streams) if len(streams) > 1 else streams[0]
    skipped = 0
    yielded = 0
    for entry in merged:
        if skipped < offset:
            skipped += 1
            continue
        if limit is not None and yielded >= limit:
            return
        yield entry
        yielded += 1


# ---------------------------------------------------------------------------
# Lyric extraction (SPEC §9: header detection + verse-run fallback)
# ---------------------------------------------------------------------------

#: A line that *is* a lyric marker — the whole line is the label, optionally
#: wrapped in brackets and optionally terminated by : ; - – — .
_HEADER_LINE_RE = re.compile(
    r"""^\s*[\(\[\{<*_=\-~]*\s*
        (lyrics?|lyric|words?|wordz|vocals?|vox|spoken\s+words?|poem|poetry|
         song\s*text|lyrics?\s*[/\\&\-+]\s*(?:spoken\s*)?words?|
         words?\s*[/\\&\-+]\s*lyrics?|the\s+lyrics?|text)
        \s*[\)\]\}>*_=\-~]*\s*[:;\-–—.]?\s*$""",
    re.IGNORECASE | re.VERBOSE,
)

#: Marker word followed by a terminator AND inline lyric content on the same
#: line (``Lyrics: la la la``).
_HEADER_INLINE_RE = re.compile(
    r"""^\s*[\(\[\{<*_]*\s*
        (lyrics?|lyric|words?|vocals?|vox|spoken\s+words?|poem|
         lyrics?\s*[/\\&\-+]\s*(?:spoken\s*)?words?)
        \s*[\)\]\}>*_]*\s*[:;\-–—]\s*(.+)$""",
    re.IGNORECASE | re.VERBOSE,
)

#: Pure separator / decorative lines.
_SEP_RE = re.compile(r"^\s*[*_=\-~#—–·•]{3,}\s*$")

#: Trailing attribution/license footer lines to strip from the lyric tail.
_FOOTER_RE = re.compile(
    r"^\s*[\(\[]?\s*(©|\(c\)|copyright|copyleft|all\s+rights\s+reserved|"
    r"license[ds]?\b.*|licensed\s+under.*|creative\s+commons.*|"
    r"words?\s*(?:&|and|by)\b.*|music\s+by\b.*|written\s+by\b.*|"
    r"lyrics?\s+by\b.*|vocals?\s+by\b.*|"
    r"download|http[s]?://\S+|www\.\S+)\s*[\)\]]?\s*$",
    re.IGNORECASE,
)

#: Stanza-label first lines — [Chorus], Verse 1:, (Hook), BRIDGE…
_LABEL_RE = re.compile(
    r"""^\s*[\(\[]?\s*
        (verse|refrain|chorus|hook|bridge|intro|outro|pre[-\s]?chorus|
         post[-\s]?chorus|instrumental|interlude|coda|tag|vamp|break|
         spoken|stanza|strofa|refren|couplet|refrain|chant|reprise)
        \b[^\n\]\)]{0,30}[\)\]:.\-–—]?\s*$""",
    re.IGNORECASE | re.VERBOSE,
)

#: A trailing single-line "Name 2011" signature block.
_SIGNATURE_RE = re.compile(
    r"^[A-ZÀ-Þ][\w.'-]*(?:\s+[A-ZÀ-Þ.]?[\w.'-]*){0,3}\s+(?:\(c\)\s*)?"
    r"(?:19|20)\d{2}\.?\s*$"
)

#: UTF-8-as-Latin-1 mojibake detector: a UTF-8 lead byte seen as Latin-1
#: (Â=0xC2, Ã=0xC3, â=0xE2, ð=0xF0) followed by a C1 control / continuation
#: byte as Latin-1, plus the already-visible forms (â€™, â€œ, ðŸ).
_MOJIBAKE_RE = re.compile(
    r"(?:â[\x80-\x9f€™œž\"«»]|Ã[\x80-\xbf]|Â[\x80-\xbf]|ð[\x80-\x9fŸ])"
)


def _fix_mojibake(text: str) -> str:
    """Repair UTF-8-misdecoded-as-Latin-1/CP1252 mojibake (``Iâ€™ve`` ->
    ``I've``, ``â\x80\x93`` -> ``–``).

    All-or-nothing per text: attempted only when tell-tale markers exist.
    latin-1 covers C1-control remnants (``â\\x80\\x93``); cp1252 covers the
    ``€™œ`` visible-punctuation form. Real non-Latin-1 text (Cyrillic, CJK)
    aborts the fix and is left untouched.
    """
    if not isinstance(text, str) or not _MOJIBAKE_RE.search(text):
        return text
    before = len(_MOJIBAKE_RE.findall(text))
    for enc in ("latin-1", "cp1252"):
        try:
            fixed = text.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        after = len(_MOJIBAKE_RE.findall(fixed))
        if after < before:
            return fixed
    return text


def _scrub_broken_chars(text: str) -> str:
    """Clean irrecoverable sequences left by upstream transcoding: U+FFFD
    plus trailing C1 bytes between letters are almost always a lost
    apostrophe; stray C1 controls and leftover U+FFFD otherwise. raw_lyrics
    keeps the verbatim bytes — this runs on clean_lyrics only."""
    # Iâ€™ve-through-the-wringer: U+FFFD + \x80\x99 between letters
    text = re.sub(r"(?<=[A-Za-zÀ-ÿ])[\ufffd][\x80-\x9f]{0,2}(?=[A-Za-zÀ-ÿ])",
                  "'", text)
    text = re.sub(r"(?<=[A-Za-zÀ-ÿ])[\ufffd][\x80-\x9f]{0,2}\s*$", "…", text)
    text = re.sub(r"[\x80-\x9f]+", "", text)          # C1 remnants
    text = re.sub(r"\ufffd+", "…", text)              # remaining unknowns
    return text


def _split_blocks(text: str) -> List[str]:
    """Paragraph blocks separated by blank lines (indentation normalised)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip("\n") for b in blocks if b.strip()]


def _block_lines(block: str) -> List[str]:
    return [l.strip() for l in block.split("\n") if l.strip()]


def _is_separator(block: str) -> bool:
    return bool(_SEP_RE.match(block)) and len(_block_lines(block)) == 1


def _is_verse_block(block: str) -> bool:
    """Verse-like: several mostly-short lines of modest mean length.

    Prose paragraphs are 1-3 long lines; verse stanzas are many short lines.
    Sentence-final periods do NOT disqualify a stanza — real pell lyrics end
    lines with '.' often (verified on fixture items 31321/22762)."""
    if _is_separator(block):
        return False
    lines = _block_lines(block)
    n = len(lines)
    if n < 2:
        return False
    short = sum(1 for l in lines if len(l) <= 80)
    mean = sum(len(l) for l in lines) / n
    if n == 2:
        # couplets are ambiguous — require clearly verse-like shape
        return short == 2 and mean <= 50
    return short / n >= 0.66 and mean <= 70


def _is_neutral_line_block(block: str) -> bool:
    """A single short line that doesn't end a verse run — refrains, one-line
    hooks, ``Chorus!`` shouts. Sentence-ending single lines (``For the
    children.``) read as prose and DO bound the run."""
    lines = _block_lines(block)
    return (len(lines) == 1 and len(lines[0]) <= 60
            and not lines[0].endswith(".")
            and not _is_separator(block))


def _longest_verse_run(blocks: List[str]) -> Optional[Tuple[int, int]]:
    """Return ``(start, end)`` block indices of the longest run of verse-like
    blocks, or None. Neutral single-line blocks are glue *inside* a run (a
    run must start and end on a verse block); separators, prose blocks, and
    prose-ish single lines bound it — so trailing signatures and ``____``
    dividers naturally cut the lyric region."""
    best: Optional[Tuple[int, int]] = None
    best_len = 0
    i = 0
    n = len(blocks)
    while i < n:
        if not _is_verse_block(blocks[i]):
            i += 1
            continue
        j = i
        n_lines = 0
        while j < n:
            if _is_verse_block(blocks[j]):
                n_lines += len(_block_lines(blocks[j]))
                j += 1
                continue
            # neutral glue only when verse resumes immediately after
            if (j + 1 < n and _is_neutral_line_block(blocks[j])
                    and _is_verse_block(blocks[j + 1])):
                n_lines += 1
                j += 1
                continue
            break
        if n_lines > best_len:
            best, best_len = (i, j), n_lines
        i = j
    return best


def _lyric_gate(text: str, min_lines: int = 4, min_chars: int = 120) -> bool:
    lines = [l for l in text.split("\n") if l.strip()]
    return len(lines) >= min_lines and len(text.strip()) >= min_chars


def _clean_lyric_block(text: str) -> str:
    """Normalise extracted lyric text: drop separators/footers, fix
    mojibake, un-indent, collapse blank runs."""
    lines = [l.strip() for l in text.replace("\r\n", "\n").replace("\r", "\n")
             .split("\n")]
    # drop pure separator lines
    lines = [l for l in lines if not _SEP_RE.match(l)]
    # strip trailing footers (license lines, 'words & music by', urls, sigs)
    while lines and (not lines[-1]
                     or _FOOTER_RE.match(lines[-1])
                     or _SIGNATURE_RE.match(lines[-1])):
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    text = "\n".join(lines)
    text = _fix_mojibake(text)
    text = _scrub_broken_chars(text)
    # collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sections(clean: str) -> List[Dict[str, Any]]:
    """Blank-line stanzas -> sections[{label, content}]; a first line matching
    the label pattern (``[Chorus]``, ``Verse 1:``) becomes ``label``."""
    out: List[Dict[str, Any]] = []
    for block in _split_blocks(clean):
        lines = _block_lines(block)
        if not lines:
            continue
        label = None
        m = _LABEL_RE.match(lines[0])
        if m:
            label = m.group(0).strip().strip("[]():.-–—") or None
            lines = lines[1:]
        content = "\n".join(lines).strip()
        if content:
            out.append({"label": label, "content": content})
    return out


def extract_lyrics(
    description: Optional[str],
) -> Optional[Tuple[str, str, List[Dict[str, Any]], str]]:
    """Extract lyric text from a pell description.

    Returns ``(raw_block, clean_lyrics, sections, how)`` where ``how`` is
    ``'header'`` or ``'verse-run'``; ``None`` when no lyric block is present
    (caller raises ``DropItem('no-lyric-text')``).
    """
    if not isinstance(description, str) or not description.strip():
        return None
    text = description.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # -- strategy A: a marker header line opens the lyric block ------------
    header_at = -1
    inline_first = ""
    for i, line in enumerate(lines):
        if _HEADER_LINE_RE.match(line):
            header_at = i
            break
        m = _HEADER_INLINE_RE.match(line)
        if m:
            header_at = i
            inline_first = m.group(2).strip()
            break
    if header_at >= 0:
        region_lines = lines[header_at + 1:]
        if inline_first:
            region_lines = [inline_first] + region_lines
        region = "\n".join(region_lines)
        blocks = _split_blocks(region)
        run = _longest_verse_run(blocks)
        if run is None:
            return None  # header promised lyrics; never emit prose
        raw = "\n\n".join(blocks[run[0]:run[1]])
        clean = _clean_lyric_block(raw)
        if not _lyric_gate(clean):
            return None
        return (raw, clean, _sections(clean), "header")

    # -- strategy B: longest verse-run anywhere in the description ---------
    blocks = _split_blocks(text)
    run = _longest_verse_run(blocks)
    if run is None:
        return None
    raw = "\n\n".join(blocks[run[0]:run[1]])
    clean = _clean_lyric_block(raw)
    # stricter gate for headerless extraction — a lone couplet amid prose is
    # not a lyric sheet (R1: yield ~45-60%, precision matters more).
    if not _lyric_gate(clean, min_lines=4, min_chars=140):
        return None
    return (raw, clean, _sections(clean), "verse-run")


# ---------------------------------------------------------------------------
# language heuristic — langdetect is NOT in the [lyrics] extra and pip
# installs are disallowed; a tiny stopword vote covers the corpus's dominant
# languages. Field is advisory; None when no signal.
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "en": {"the", "and", "you", "i", "to", "of", "in", "my", "me", "is",
           "it", "that", "we", "your", "on", "are", "be", "so", "not", "all"},
    "es": {"el", "la", "los", "las", "de", "que", "en", "y", "un", "una",
           "mi", "tu", "es", "por", "con", "no", "se", "te", "me", "lo"},
    "fr": {"le", "la", "les", "de", "des", "et", "un", "une", "je", "tu",
           "est", "dans", "que", "ne", "pas", "pour", "sur", "avec", "mon",
           "ma"},
    "de": {"der", "die", "das", "und", "ich", "du", "ist", "nicht", "ein",
           "eine", "zu", "den", "mit", "auf", "sich", "es", "im", "dem"},
    "pt": {"o", "a", "os", "as", "de", "que", "e", "um", "uma", "meu", "seu",
           "em", "não", "com", "por", "te", "me", "se", "para", "do", "da"},
    "la": {"et", "in", "est", "non", "ad", "qui", "cum", "de", "meum",
           "vita", "homine", "dominus", "per", "sed", "quod", "nos"},
    "sr": {"i", "u", "je", "na", "se", "da", "ne", "za", "mi", "ti", "od",
           "po", "sam", "si", "iz", "kao", "će", "mu", "ga", "to"},
}


def _guess_language(text: str) -> Optional[str]:
    tokens = re.findall(r"[a-zà-ÿšđžćč']+", (text or "").lower())
    if len(tokens) < 8:
        return None
    best, best_hits = "en", 0
    for lang, stops in _STOPWORDS.items():
        hits = sum(1 for t in tokens if t in stops)
        if hits > best_hits:
            best, best_hits = lang, hits
    return best if best_hits >= 3 else "en"


# ---------------------------------------------------------------------------
# fetch_lyrics — description -> song JSON v2 (SPEC §3.3/§9)
# ---------------------------------------------------------------------------


def _html_to_text(html: str) -> str:
    """upload_description_html -> plain text (bs4 in the [lyrics] extra)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return re.sub(r"<[^>]+>", "\n", html)
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.append("\n")
    return soup.get_text()


def _fetch_upload(
    foreign_identifier: str,
    *,
    session=None,
    limiter=None,
) -> Dict[str, Any]:
    """Refetch a single upload by id — fallback when the catalog row carries
    no stored description (hand-built catalogs, older queues)."""
    items = _api_query(
        {"f": "json", "dataview": "default", "ids": str(foreign_identifier)},
        session=session,
        limiter=limiter,
    )
    if not items:
        raise DropItem("upstream-item-missing")
    return items[0]


def fetch_lyrics(
    entry: CatalogEntry,
    *,
    session=None,
    limiter=None,
) -> Dict[str, Any]:
    """Build a song JSON v2 (SPEC §3.3) from one catalog entry.

    Lyric source = ``meta.description_plain`` stored at catalog time (or the
    HTML variant / a single polite ``ids=`` refetch). Pells without a lyric
    block raise ``DropItem('no-lyric-text')`` — R1 measured ~45-60% yield, so
    dropping is the normal path, not an error.
    """
    meta = entry.meta or {}
    desc_plain = meta.get("description_plain")
    desc_html = meta.get("description_html")
    if not desc_plain and not desc_html and entry.foreign_identifier:
        item = _fetch_upload(entry.foreign_identifier,
                             session=session, limiter=limiter)
        desc_plain = item.get("upload_description_plain")
        desc_html = item.get("upload_description_html")
        if not entry.title:
            entry.title = item.get("upload_name") or entry.title

    text = desc_plain or (_html_to_text(desc_html) if desc_html else "")
    result = extract_lyrics(text)
    if result is None:
        raise DropItem("no-lyric-text")
    raw, clean, sections, how = result

    info = license_of(entry)
    title = entry.title or f"ccmixter-{entry.foreign_identifier}"
    creator = entry.creator or entry.artist or "ccMixter contributor"

    song: Dict[str, Any] = {
        "title": title,
        "artist": creator,
        "primary_artist": creator,   # NOT NULL downstream (SPEC §3.3)
        "featured_artists": [],
        "category": entry.category,
        "url": entry.url or entry.source_url or "",
        "language": _guess_language(clean),
        "raw_lyrics": raw,
        "clean_lyrics": clean,
        "sections": sections,
        "corpus": "ccmixter",
        "source": SOURCE_ID,
        "foreign_identifier": entry.foreign_identifier,
        "source_url": entry.source_url or entry.url,
        "creator": creator,
        "creator_url": entry.creator_url,
        "copyright_notice": info.copyright_notice,
        "modified_note": None,
        "license": info.license,
        "license_url": info.license_url,
        "license_tier": info.license_tier,
        "release_ok": info.release_ok,
        "derived_from": None,
        "meta": {
            "lane": meta.get("lane"),
            "extraction": how,
            "license_name": meta.get("license_name"),
            "upload_tags": meta.get("upload_tags"),
            "usertags": meta.get("usertags"),
            "bpm": meta.get("bpm"),
            "ccplus": meta.get("ccplus"),
            "nsfw": meta.get("nsfw"),
            "num_scores": meta.get("num_scores"),
            "upload_date": meta.get("upload_date"),
        },
    }
    return song


__all__ = [
    "SOURCE_ID",
    "iter_catalog",
    "license_of",
    "fetch_lyrics",
    "extract_lyrics",
]
