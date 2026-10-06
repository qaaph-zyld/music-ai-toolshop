"""Wikisource public-domain folk-lyric adapter (lyrics-sources wave A, I3).

SPEC §2.1/§3.2/§9 + R2 §1-§3. Serves BOTH wikis under the merged
``wikisource_pd`` registry row / ``lyrics/wikisource_pd/`` corpus:

* sr.wikisource.org — ~10k+ ``Народне песме`` poem pages. Category layout is
  frozen to the six slugs ``zenske | epske | lirske | vuk-zbirke | erlangen |
  ostalo``; branch assignment is resolved dynamically during a bounded
  depth-first walk of ``Категорија:Народне песме`` (pages sit in several
  overlapping cycles, so membership is discovered, not hard-coded; R2 §1 warns
  ~1.6k poem pages are categorized under the broad root but NOT under their
  specific book category — hence the DFS from the root, not per-book cats).
  The Vuk collection tree (14 book categories, ~1.6k pages) and
  ``Ерлангенски рукопис`` (~216 pages) are separate entry points.
* en.wikisource.org — the six pre-1930 categories froze in the SPEC:
  folk-songs / ballads / traditional-ballads / song-books / hymns /
  poetry-collections. Secondary arm (~300-500 pages). Child-ballad pages are
  ``{{migrate to}}`` placeholders (R2 §2) and are dropped by the
  empty/link-heavy guards, not emitted.

Network contract (R2 §3 — violating this triggers an IP block):
serial requests ONLY via :func:`_common.polite_get`; >=1.5 s between hits;
descriptive contact User-Agent; ``maxlag=5`` honored server-side; no
parallel fetch bursts anywhere in this module. Wikitext is fetched via
``action=parse&prop=wikitext`` (NOT prop=extracts, SPEC §9).

Per-page license gate (SPEC §9): every page's wikitext is scanned for
license-name templates BEFORE an item is emitted. ``{{PD-*}}`` /
``{{Јавно власништво}}`` / absence of any license template -> PD ``yes``.
``CC-BY-SA``-style templates -> item emitted with ``conditional`` tier
(bilateral-review bucket). Non-PD / NC / fair-use / GFDL templates ->
``DropItem``, never written.

Serbian normalization (frozen): ``raw_lyrics`` keeps the original Cyrillic
byte-for-byte; ``clean_lyrics`` = ``cyrtranslit.to_latin(.., 'sr')`` +
diacritic fold matching ``lyricsdb.normalize_text`` (c/c, c/c, s/s,
z/z, dj/dj); ``script: "cyrillic-original"`` marks pages that arrived in
Cyrillic. ``Narodna pesma`` fills artist (songs.primary_artist NOT NULL);
en pages get ``Traditional``.

Stanzas -> ``sections[{label: "Strofa N", content}]`` — the canonical
non-English label that ``lyricsdb._parse_section_label`` folds to
``{kind: "strofa"}``.

sys.path shim so it imports both as part of ``sources.*`` and when the
extractor folder itself is on sys.path (SPEC §7). No ``import toolshop``.
"""

from __future__ import annotations

import re
import unicodedata
from html import unescape
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import quote

try:  # hard dep in the project venv; kept optional for fixture-less imports
    import cyrtranslit
    _HAS_CYRTRANSLIT = True
except ImportError:  # pragma: no cover - venv guarantees it
    cyrtranslit = None
    _HAS_CYRTRANSLIT = False

try:
    from . import registry
    from ._common import (
        CatalogEntry,
        DropItem,
        LicenseInfo,
        detect_script,
        polite_get,
    )
except ImportError:  # pragma: no cover - direct sys.path import
    import registry  # type: ignore
    from _common import (  # type: ignore
        CatalogEntry,
        DropItem,
        LicenseInfo,
        detect_script,
        polite_get,
    )

SOURCE_ID = "wikisource_pd"
WIKI_SR = "sr"
WIKI_EN = "en"

APIS = {
    WIKI_SR: "https://sr.wikisource.org/w/api.php",
    WIKI_EN: "https://en.wikisource.org/w/api.php",
}
PAGE_URL = {
    WIKI_SR: "https://sr.wikisource.org/wiki/{title}",
    WIKI_EN: "https://en.wikisource.org/wiki/{title}",
}
DEFAULT_MAXLAG = 5
MAX_DEPTH = 8
MIN_VERSE_LINES = 4
PD_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
CC_BY_SA_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

# ---------------------------------------------------------------------------
# Category roots (frozen set, SPEC §3.2 / task §4)
# ---------------------------------------------------------------------------

#: (category title, forced branch slug | None -> resolved by name)
SR_ENTRY_POINTS: Tuple[Tuple[str, Optional[str]], ...] = (
    ("Категорија:Збирке Вука Стефановића Караџића", "vuk-zbirke"),
    ("Категорија:Ерлангенски рукопис", "erlangen"),
    ("Категорија:Народне песме", None),  # broadest LAST (DFS, dedup-first-wins)
)

EN_CATEGORIES: Tuple[Tuple[str, str], ...] = (
    ("Category:Folk songs", "folk-songs"),
    ("Category:Ballads", "ballads"),
    ("Category:Traditional ballads", "traditional-ballads"),
    ("Category:Song books", "song-books"),
    ("Category:Hymns", "hymns"),
    ("Category:Collections of poetry", "poetry-collections"),
)

_FOLD_TABLE = str.maketrans({
    "š": "s", "Š": "S", "č": "c", "Č": "C", "ć": "c", "Ć": "C",
    "ž": "z", "Ž": "Z", "đ": "dj", "Đ": "Dj",
})


def _latin(text: str) -> str:
    """Cyrillic -> Serbian Latin via cyrtranslit, then SPEC diacritic fold
    (identical mapping to lyricsdb.normalize_text). Latin input passes
    through the fold unchanged. Case preserved (clean_lyrics convention)."""
    if not text:
        return text
    if _HAS_CYRTRANSLIT and detect_script(text) == "cyrillic":
        text = cyrtranslit.to_latin(text, "sr")
    text = unicodedata.normalize("NFC", text)
    return text.translate(_FOLD_TABLE)


# ---------------------------------------------------------------------------
# MediaWiki API — serial, polite_get-paced, maxlag=5
# ---------------------------------------------------------------------------


def _api_get(wiki: str, params: Dict[str, Any], session=None,
             limiter=None) -> Dict[str, Any]:
    q: Dict[str, Any] = {"format": "json", "formatversion": "2",
                         "maxlag": str(DEFAULT_MAXLAG)}
    q.update(params)
    resp = polite_get(APIS[wiki], source_id=SOURCE_ID, params=q,
                      session=session, limiter=limiter)
    try:
        return resp.json()
    except Exception as exc:  # pragma: no cover - network failure
        raise DropItem(f"api-json-parse:{exc}") from exc


def _cm(wiki: str, cat: str, cmtype: str, session,
        limiter=None) -> Iterator[Dict[str, Any]]:
    """Yield categorymembers pages/subcats, serial through continuation."""
    cont: Dict[str, Any] = {}
    while True:
        p: Dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmtype": cmtype,
            "cmlimit": "500",
        }
        if cmtype == "page":
            p["cmnamespace"] = "0"  # ns-0 poem pages only (skip files/authors)
        p.update(cont)
        data = _api_get(wiki, p, session=session, limiter=limiter)
        for m in data.get("query", {}).get("categorymembers", []):
            yield m
        nxt = data.get("continue", {})
        if not nxt:
            break
        cont = {"cmcontinue": nxt.get("cmcontinue")}


def _catnorm(cat: str) -> str:
    return _latin(cat.split(":", 1)[-1]).lower().replace("_", " ").strip()


def _branch_for_cat(cat_title: str, inherited: str) -> str:
    """Map an sr subcategory name to one of the 6 frozen slugs."""
    name = _catnorm(cat_title)
    # all 14 book cats contain "Вук"; "Караџићев циклус" is a theme cycle
    # about Karadžić (ostalo), NOT a zbirka — so key on "vuk" only.
    if "vuk" in name:
        return "vuk-zbirke"
    if "erlangen" in name:
        return "erlangen"
    if "zenske narodne" in name:
        return "zenske"
    if "srpske epske narodne" in name:
        return "epske"
    if "srpske lirske narodne" in name:
        return "lirske"
    return inherited


def _artist(wiki: str) -> str:
    return "Narodna pesma" if wiki == WIKI_SR else "Traditional"


def _mk_entry(wiki: str, member: Dict[str, Any], slug: str) -> CatalogEntry:
    pid = str(member.get("pageid"))
    title = str(member.get("title", ""))
    url = PAGE_URL[wiki].format(title=quote(title.replace(" ", "_")))
    artist = _artist(wiki)
    return CatalogEntry(
        source_id=SOURCE_ID,
        foreign_identifier=f"{wiki}:{pid}",
        title=title,
        url=url,
        artist=artist,
        creator=artist,
        source_url=url,
        license="LicenseRef-public-domain",
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
        category=slug,
        meta={"wiki": wiki, "pageid": pid, "page_title": title},
    )


def _walk_sr(session, seen_pages: Set[str], limiter=None) -> Iterator[CatalogEntry]:
    """Lazy DFS over the frozen sr entry points. Pages stream out as they
    are found so a --limit pilot never walks the whole 10k tree."""
    seen_cats: Set[str] = set()
    stack: List[Tuple[str, str, int]] = [
        (cat, forced if forced else "ostalo", 0)
        for cat, forced in SR_ENTRY_POINTS
    ]
    while stack:
        cat, branch, depth = stack.pop()
        key = _catnorm(cat)
        if key in seen_cats or depth > MAX_DEPTH:
            continue
        seen_cats.add(key)
        for m in _cm(WIKI_SR, cat, "page", session, limiter=limiter):
            pid = str(m.get("pageid"))
            if pid in seen_pages:
                continue
            seen_pages.add(pid)
            yield _mk_entry(WIKI_SR, m, branch)
        for sc in _cm(WIKI_SR, cat, "subcat", session, limiter=limiter):
            t = str(sc.get("title", ""))
            if not t:
                continue
            stack.append((t, _branch_for_cat(t, branch), depth + 1))


def _walk_en(session, seen_pages: Set[str], limiter=None) -> Iterator[CatalogEntry]:
    """Lazy walk of the six frozen en categories (depth<=2)."""
    for cat, slug in EN_CATEGORIES:
        stack: List[Tuple[str, int]] = [(cat, 0)]
        seen_cats: Set[str] = set()
        while stack:
            c, depth = stack.pop()
            k = _catnorm(c)
            if k in seen_cats or depth > 2:
                continue
            seen_cats.add(k)
            for m in _cm(WIKI_EN, c, "page", session, limiter=limiter):
                pid = str(m.get("pageid"))
                if pid in seen_pages:
                    continue
                seen_pages.add(pid)
                yield _mk_entry(WIKI_EN, m, slug)
            for sc in _cm(WIKI_EN, c, "subcat", session, limiter=limiter):
                t = str(sc.get("title", ""))
                if t:
                    stack.append((t, depth + 1))


def iter_catalog(limit: Optional[int] = None, offset: int = 0,
                 session=None, limiter=None) -> Iterator[CatalogEntry]:
    """Serial lazy catalog: sr arm first (dedup-first-wins across the
    overlapping cycles), then the six frozen en categories. `session`
    exists for fixture tests; the live pilot drives this with no kwargs.
    """
    seen_pages: Set[str] = set()

    def _gen() -> Iterator[CatalogEntry]:
        yield from _walk_sr(session, seen_pages, limiter=limiter)
        yield from _walk_en(session, seen_pages, limiter=limiter)

    emitted = skipped = 0
    for e in _gen():
        if skipped < offset:
            skipped += 1
            continue
        yield e
        emitted += 1
        if limit is not None and emitted >= limit:
            return


# ---------------------------------------------------------------------------
# License-template scan (SPEC §9)
# ---------------------------------------------------------------------------

#: template-name fragments that mark the candidate set as license-ish
_LIC_TOKENS = (
    "pd", "public domain", "javno", "jв", "cc", "creative commons",
    "gfdl", "fair", "copyright", "licen", "license", "free", "domain",
)
_NON_PD_TOKENS = (
    "noncommercial", "non-commercial", "non free", "non-free", "nonfree",
    "nc-", "-nc", "fairuse", "fair-use", "fair use", "copyrighted",
    "all rights", "allrights", "gfdl", "do not move", "not-pd", "nonpd",
    "permission",
)
_CONDITIONAL_TOKENS = ("by-sa", "share-alike", "sharealike")


def scan_license_templates(wikitext: str) -> Tuple[str, List[str], Optional[str]]:
    """Return (verdict, license_template_names, offending_name).

    verdict: 'ok' | 'conditional' | 'non-pd'. Only template NAMES are
    inspected — a ``{{Поезија}}`` body template is never a license signal.
    """
    names = [m.group(1).strip()
             for m in re.finditer(r"\{\{\s*([^{}|]+)", wikitext)]
    candidates: List[str] = []
    verdict = "ok"
    offending: Optional[str] = None
    for n in names:
        low = _latin(n).lower().replace("_", " ")
        if not any(tok in low for tok in _LIC_TOKENS):
            continue
        candidates.append(n)
        if any(tok in low for tok in _NON_PD_TOKENS):
            return "non-pd", candidates, n
        if (any(tok in low for tok in _CONDITIONAL_TOKENS)
                or re.search(r"\bsa[- ]?\d", low)):
            verdict = "conditional"
            offending = n
    return verdict, candidates, offending


# ---------------------------------------------------------------------------
# Wikitext -> verse text
# ---------------------------------------------------------------------------

#: container templates whose BODY is the lyric text (never strip)
_KEEP_BODY_TEMPLATES = {
    "поезија", "poezija", "poem", "poetry", "стихи", "стихотворение",
    "verse", "quote", "blockquote", "цитат", "цитата", "center", "оквир",
}
#: headings (folded, lower) that END lyric content
_CUT_HEADINGS = {
    "vidi jos", "види још", "vidi takode", "види такође", "napomene",
    "напомене", "reference", "референце", "references", "izvor", "извор",
    "spoljasne veze", "спољашње везе", "see also", "external links",
    "further reading", "sources", "bibliography", "notes", "galerija",
}
_LINK_LIST_LINE = re.compile(r"^\s*(?:[*:#]+\s*)?\[\[")
_LANG_PREFIXES = {
    "en", "de", "fr", "ru", "sl", "hr", "bg", "mk", "uk", "be", "es", "it",
    "slika", "file", "image", "category", "категорија", "слика", "категориа",
}
_SKIP_LINE_TOKENS = ("_toc_",)


def _find_template_end(wt: str, start: int) -> int:
    """Index after the matching '}}' for the '{{' at `start`; -1 if open."""
    depth, i, n = 0, start, len(wt)
    while i < n - 1:
        pair = wt[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return i
            continue
        i += 1
    return -1


def _first_top_pipe(body: str) -> int:
    """Position of the first '|' outside nested {{..}} in template body."""
    depth = 0
    i = 0
    while i < len(body) - 1:
        pair = body[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            return i
        i += 1
    return -1


def _strip_templates(wt: str, max_passes: int = 8) -> str:
    """Remove templates; container templates ({{Поезија|...}} etc.) keep
    their body, everything else ({{стих|5}}, font color, {{header}}...) is
    dropped whole. Left-associative text inside the body survives."""
    for _ in range(max_passes):
        start = wt.find("{{")
        if start < 0:
            return wt
        end = _find_template_end(wt, start)
        if end < 0:
            return wt[:start]
        body = wt[start + 2:end - 2]
        pipe = _first_top_pipe(body)
        name = _latin(body[:pipe if pipe >= 0 else len(body)]
                      ).strip().lower().replace("_", " ")
        if name in _KEEP_BODY_TEMPLATES and pipe >= 0:
            repl = body[pipe + 1:]
        else:
            repl = ""
        wt = wt[:start] + repl + wt[end:]
    return wt


_TAG_DROP_SPAN = re.compile(
    r"<\s*(gallery|timeline|math|syntaxhighlight|source|score|imagemap"
    r"|graph|hiero)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.S | re.I)
_TAG_DROP_LINE = re.compile(
    r"<\s*(pages|gallery|nowiki|noinclude|includeonly|onlyinclude|references)"
    r"\b[^>]*/?\s*>", re.I)
_TAG_KEEP_SPAN = re.compile(
    r"<\s*/?\s*(poem|center|div|span|big|small|blockquote|font|u|s|sup|sub|br|i|b|p|dd|dl|dt|table|tr|td|th|ul|ol|li)\b[^>]*>",
    re.I)


def _is_link_line(raw_line: str) -> bool:
    return bool(_LINK_LIST_LINE.match(raw_line))


def wikitext_to_verse(wt: str) -> str:
    """Clean a wikitext page down to lyric lines. Preserves {{Поезија}} /
    <poem> bodies; drops nav, refs, categories, images, TOC lists of links.
    Trailing sections (Види још / Референце / Извор / See also / Notes)
    cut the text. Returns '' -> caller drops."""
    if not wt:
        return ""
    txt = re.sub(r"<!--.*?-->", "", wt, flags=re.S)
    txt = re.sub(r"<\s*ref\b[^>]*/\s*>", "", txt, flags=re.I)
    txt = re.sub(r"<\s*ref\b[^>]*>.*?<\s*/\s*ref\s*>", "", txt, flags=re.S | re.I)
    txt = _TAG_DROP_SPAN.sub("", txt)
    txt = _strip_templates(txt)
    txt = _TAG_DROP_LINE.sub("", txt)
    txt = re.sub(r"<\s*br\b[^>]*/?\s*>", "\n", txt, flags=re.I)
    txt = _TAG_KEEP_SPAN.sub("", txt)

    out: List[str] = []
    for raw_line in txt.split("\n"):
        line = raw_line.strip()
        if not line:
            out.append("")
            continue
        if any(tok in line.lower() for tok in _SKIP_LINE_TOKENS):
            continue
        # headings
        hm = re.match(r"^(=+)\s*(.*?)\s*\1\s*$", line)
        if hm:
            head = _latin(hm.group(2)).lower().replace("_", " ").strip()
            head = re.sub(r"[.\s]+$", "", head)
            if head in _CUT_HEADINGS:
                break
            continue
        # full-line category/file/interwiki links
        lm = re.match(r"^\[\[([^|\]]+)(?:\|[^\]]*)?\]\]\s*$", line)
        if lm:
            prefix = lm.group(1).split(":", 1)[0].strip().lower()
            if prefix in _LANG_PREFIXES or len(prefix) == 2:
                continue
        # inline links [[a|b]] -> b ; [[a]] -> a ; drop cat/file inline
        def _sub(m: re.Match) -> str:
            target, _, label = m.group(1).partition("|")
            pref = target.split(":", 1)[0].strip().lower()
            if pref in _LANG_PREFIXES or len(pref) == 2:
                return ""
            return label or target
        line = re.sub(r"\[\[([^\]]+)\]\]", _sub, line)
        line = line.replace("'''", "").replace("''", "")
        line = re.sub(r"^[:#*]+", "", line)  # indent/list markers
        line = unescape(line).replace("\xa0", " ")
        out.append(line.rstrip())
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


def _link_heavy(wt: str, clean: str) -> bool:
    """Page was mostly a list of links (book TOC / disambig): raw lines
    that are `[[..]]`/`*[[..]]` dominate AND little verse survived."""
    raw_lines = [l for l in wt.split("\n") if l.strip()]
    if not raw_lines:
        return False
    link_lines = sum(1 for l in raw_lines if _is_link_line(l))
    verse = sum(1 for l in clean.split("\n") if l.strip())
    return link_lines >= 4 and link_lines >= len(raw_lines) * 0.5 and verse < 12


def _stanzas_to_sections(text: str, fold: bool) -> List[Dict[str, str]]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    sections: List[Dict[str, str]] = []
    for i, b in enumerate(blocks, 1):
        content = _latin(b) if fold else b
        if content:
            sections.append({"label": f"Strofa {i}", "content": content})
    return sections


# ---------------------------------------------------------------------------
# license_of + fetch_lyrics (SPEC §6.3 contract)
# ---------------------------------------------------------------------------


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Registry default is PD; license_of may only downgrade (SPEC §6.3).
    The actual per-page template verdict lands in fetch_lyrics — a catalog
    row carries no wikitext yet."""
    return LicenseInfo(
        license="LicenseRef-public-domain",
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
    )


def _song_from_wikitext(entry: CatalogEntry, wt: str,
                        parsed_title: Optional[str] = None) -> Dict[str, Any]:
    """Shared wikitext -> song-dict pipeline (license gate, verse cleaning,
    normalization, schema). Both ``fetch_lyrics`` (API ``action=parse`` path)
    and the P2 XML-dump ingestor land here so the verdict logic can never
    drift between the two — dump passes ``parsed_title=None`` (the page title
    already rides ``entry.meta['page_title']``).

    Raises ``DropItem`` for empty wikitext, non-PD license templates,
    too-short pages, TOC/index pages, and empty-after-normalization.
    """
    meta = dict(entry.meta or {})
    wiki = str(meta.get("wiki") or WIKI_SR)
    pid = str(meta.get("pageid")
                or str(entry.foreign_identifier).rsplit(":", 1)[-1])
    if not wt.strip():
        raise DropItem("empty-wikitext")

    verdict, lic_templates, offender = scan_license_templates(wt)
    if verdict == "non-pd":
        raise DropItem(f"non-pd-license-template:{offender}")

    clean = wikitext_to_verse(wt)
    verse_lines = [l for l in clean.split("\n") if l.strip()]
    if len(verse_lines) < MIN_VERSE_LINES:
        raise DropItem(f"too-short:{len(verse_lines)}-verse-lines")
    if _link_heavy(wt, clean):
        raise DropItem("toc-or-index-page")

    script = "cyrillic-original" if detect_script(clean) == "cyrillic" \
        else "latin"
    fold = wiki == WIKI_SR
    sections = _stanzas_to_sections(clean, fold=fold)
    clean_lyrics = _latin(clean) if fold else clean
    if not clean_lyrics.strip():
        raise DropItem("empty-after-normalization")

    title = str(entry.title or meta.get("page_title") or "")
    artist = _artist(wiki)
    url = str(entry.source_url or entry.url
              or PAGE_URL[wiki].format(
                  title=quote(str(meta.get("page_title", "")).replace(" ", "_"))))

    lic = "LicenseRef-public-domain"
    lic_url = PD_LICENSE_URL
    tier = "pd"
    rel = "yes"
    if verdict == "conditional":
        lic = "CC-BY-SA-4.0"
        lic_url = CC_BY_SA_URL
        tier = "cc-by-sa"
        rel = "conditional"

    song: Dict[str, Any] = {
        "title": title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "category": str(entry.category or "ostalo"),
        "url": url,
        "language": "sr" if wiki == WIKI_SR else "en",
        "raw_lyrics": clean,
        "clean_lyrics": clean_lyrics,
        "sections": sections,
        "corpus": "wikisource_pd",
        "source": SOURCE_ID,
        "foreign_identifier": str(entry.foreign_identifier),
        "source_url": url,
        "creator": artist,
        "creator_url": None,
        "copyright_notice": None,
        "modified_note": None,
        "license": lic,
        "license_url": lic_url,
        "license_tier": tier,
        "release_ok": rel,
        "derived_from": None,
        "script": script,
        "meta": {
            "wiki": wiki,
            "pageid": pid,
            "page_title": parsed_title or meta.get("page_title"),
            "license_templates": lic_templates,
            "license_verdict": verdict,
            "wikitext_bytes": len(wt),
            "normalization": ("cyrtranslit.to_latin(sr) + diacritic fold "
                              "(SPEC/lyricsdb parity); raw_lyrics keeps "
                              "the original script")
            if script == "cyrillic-original" else "latin-source",
        },
    }
    return song


def fetch_lyrics(entry: CatalogEntry, session=None, limiter=None) -> Dict[str, Any]:
    meta = dict(entry.meta or {})
    wiki = str(meta.get("wiki") or WIKI_SR)
    pid = str(meta.get("pageid")
                or str(entry.foreign_identifier).rsplit(":", 1)[-1])
    data = _api_get(wiki, {"action": "parse", "prop": "wikitext",
                           "pageid": pid}, session=session, limiter=limiter)
    parsed = data.get("parse") or {}
    return _song_from_wikitext(
        entry, parsed.get("wikitext") or "",
        parsed_title=parsed.get("title"))
