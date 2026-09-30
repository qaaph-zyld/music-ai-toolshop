"""sacred-texts.com adapter — Child's *English and Scottish Popular Ballads*
mirror (SPEC §9, R2 §6).

Pilot findings (2026-09-30, live-verified this wave):
- The old static archive has been re-platformed into a SvelteKit app, but the
  classic URLs still serve 200 with the chapter body **server-rendered into
  the page data** as ``chapterContent:{…, contentHtml:"<js-escaped>",
  contentText:"<plain>"}`` — parseable without running JS.
- File↔ballad mapping is 1:1: ``/neu/eng/child/chNNN.htm`` ↔ Child ballad N
  (verified ``ch001``→"1A: Riddles Wisely Expounded", ``ch039``→"39A: Tam
  Lin", ``ch250``→"250A: Henry Martyn", ``ch305``→"305A: The Outlaw Murray";
  ``ch306`` → 404, so the corpus is exactly 1–305).
- ``robots.txt``: ``User-agent: *`` ``Allow: /`` — fully permitted.
- The embedded ``contentHtml`` carries the transcription **with its upstream
  mojibake** (UTF-8 curly punctuation double-encoded as cp1252 bytes —
  ``ladieâ€™s`` for ``ladie's``); ``_fix_mojibake`` repairs it.
- Ballad text model: version headings ``<h*>NN<L>: Title</h*>`` (also arrives
  as escaped legacy ``&lt;H3&gt;`` markup), stanza numbers ``NN<L>.M``
  inline in ``<p>`` blobs or at ``<pre>`` line starts, ``Refrain:`` paras,
  and ``* * * * *`` asterism breaks (dropped — typographic).

Catalog stage fetches nothing: ballad numbers are deterministic, so
``iter_catalog`` emits 305 entries instantly (title placeholder replaced by
the real title at fetch). License is uniform: the book (Houghton Mifflin,
1882–98) is pre-1931 PD and the site asserts "This text is in the public
domain" — ``license_tier='pd'``, ``release_ok='yes'``, site notice recorded
verbatim in ``copyright_notice``.
"""

from __future__ import annotations

import html as _html_mod
import json
import re
from typing import Any, Dict, Iterator, List, Optional

try:  # package import (sources.sacred_texts) or flat sys.path (tests)
    from . import _common as _c
except ImportError:  # pragma: no cover
    import _common as _c  # type: ignore

CatalogEntry = _c.CatalogEntry
LicenseInfo = _c.LicenseInfo
DropItem = _c.DropItem

SOURCE_ID = "sacred_texts"
BASE_URL = "https://sacred-texts.com"
CATEGORY = "child-ballads"  # SPEC §3.2 frozen slug

PAGE_TEMPLATE = BASE_URL + "/neu/eng/child/ch{n:03d}.htm"
FIRST_BALLAD = 1
LAST_BALLAD = 305  # ch306 verified 404 (2026-09-30)

BOOK_TITLE = "The English and Scottish Popular Ballads"
BOOK_YEARS = "1882-98"
EDITOR = "Francis James Child"

#: The site's own PD assertion on the title page — recorded verbatim per the
#: TASL/notice convention (SPEC §1.3), it is the transcription-layer grant.
SITE_NOTICE = (
    "Ballads originally transcribed by Cathy Lynn Preston. HTML Formatting "
    "at sacred-texts.com. This text is in the public domain. These files may "
    "be used for any non-commercial purpose, provided this notice of "
    "attribution is left intact."
)

PD_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"

#: Injectable seams — tests monkeypatch these (FakeSession / no-wait limiter).
_SESSION = None
_LIMITER = None


def _get(url: str, **kw):
    return _c.polite_get(
        url,
        SOURCE_ID,
        session=_SESSION,
        limiter=_LIMITER,
        **kw,
    )


# ---------------------------------------------------------------------------
# iter_catalog — deterministic enumeration, zero network
# ---------------------------------------------------------------------------


def iter_catalog(limit: Optional[int] = None, offset: int = 0) -> Iterator[CatalogEntry]:
    """Emit one CatalogEntry per Child ballad number (1–305). The real title
    is only known after fetching the page — ``fetch_lyrics`` fills it and the
    runner syncs it back into the catalog row."""
    nums = list(range(FIRST_BALLAD, LAST_BALLAD + 1))
    if offset:
        nums = nums[offset:]
    if limit is not None:
        nums = nums[:limit]
    for n in nums:
        yield CatalogEntry(
            source_id=SOURCE_ID,
            foreign_identifier=f"child-{n:03d}",
            title=f"Child ballad {n}",
            url=PAGE_TEMPLATE.format(n=n),
            creator="Traditional",
            category=CATEGORY,
            license="LicenseRef-public-domain",
            license_url=PD_LICENSE_URL,
            license_tier="pd",
            release_ok="yes",
            meta={"child_number": n},
        )


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Uniform PD: the book is 1882–98 (pre-1931) and the site asserts PD on
    its transcription; the notice line is carried verbatim for audit."""
    return LicenseInfo(
        license="LicenseRef-public-domain",
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
        copyright_notice=SITE_NOTICE,
    )


# ---------------------------------------------------------------------------
# Page data extraction — SvelteKit ``chapterContent`` block
# ---------------------------------------------------------------------------

_CONTENT_HTML_RE = re.compile(r'contentHtml\s*:\s*"((?:\\.|[^"\\])*)"')
_CONTENT_TEXT_RE = re.compile(r'contentText\s*:\s*"((?:\\.|[^"\\])*)"')


def _decode_js_string(body: str) -> str:
    """Decode a JS-string literal body (``\\u003C`` escapes, ``\\'``, ``\\/``).
    JSON-compatible escapes go through ``json.loads``; a manual pass covers
    JS-only escapes if needed."""
    try:
        return json.loads('"' + body + '"')
    except Exception:
        out = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda m: chr(int(m.group(1), 16)), body)
        return (out.replace("\\'", "'").replace('\\"', '"')
                   .replace("\\/", "/").replace("\\n", "\n")
                   .replace("\\t", "\t").replace("\\\\", "\\"))


def extract_chapter(page_html: str) -> Optional[Dict[str, str]]:
    """Pull ``chapterContent``'s ``contentHtml``/``contentText`` out of the
    Svelte page; ``None`` when the page has none."""
    if "contentHtml" not in page_html:
        return None
    m = _CONTENT_HTML_RE.search(page_html)
    if not m:
        return None
    out = {"content_html": _decode_js_string(m.group(1))}
    mt = _CONTENT_TEXT_RE.search(page_html)
    if mt:
        out["content_text"] = _decode_js_string(mt.group(1))
    return out


# ---------------------------------------------------------------------------
# Mojibake repair (cp1252→UTF-8 double-encoding baked into the transcription)
# ---------------------------------------------------------------------------

#: The transcription was UTF-8 mis-decoded through **latin-1** (verified
#: live: ``a'`` arrives as ``a`` + ``â`` + U+0080 + U+0099 — bytes
#: E2 80 99 decoded as latin-1, leaving C1 controls). Some content may
#: carry the cp1252 variant (``â€™``) instead. Repair encodes each
#: suspicious run back to bytes — latin-1 first (it covers C1 controls
#: cp1252 cannot encode), cp1252 second — and re-decodes UTF-8; a run
#: that fails the round-trip (e.g. a legit lone ``’``) is kept verbatim,
#: so repair only fires on real damage. C1 controls U+0080–U+009F are
#: never legitimate text: a certain marker, with ``â``/``Ã``/``€``/``™``.
_MOJI_MARK_RE = re.compile("[\u0080-\u009f]|[âÃ]|\u20ac|\u2122")
_LATIN1_RUN = re.compile(
    "[\u0080-\u00ff"
    "\u0192\u02c6\u02dc"
    "\u0160\u0161\u0152\u0153\u0178\u017d\u017e"
    "\u2013\u2014\u2018\u2019\u201a\u201c\u201d\u201e"
    "\u2020\u2021\u2022\u2026\u2030\u2039\u203a\u20ac\u2122]+"
)


def _recode_run(run: str) -> str:
    for enc in ("latin-1", "cp1252"):
        try:
            return run.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return run


def _fix_mojibake(text: str) -> str:
    if not _MOJI_MARK_RE.search(text):
        return text
    for enc in ("latin-1", "cp1252"):
        try:
            return text.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return _LATIN1_RUN.sub(lambda m: _recode_run(m.group(0)), text)


# ---------------------------------------------------------------------------
# Ballad HTML → version/stanza model (section→stanza mapping)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_RE = re.compile(r"<(h[1-6]|p|pre|blockquote)\b[^>]*>(.*?)</\1>",
                       re.S | re.I)
_VERSION_HEAD_RE = re.compile(r"^\s*(\d+)([A-Z]+)\s*[:.)]\s*(.*)$")
_VERSE_REF_RE = re.compile(r"(\d+)([A-Z]+)\.(\d+)")
_REFRAIN_RE = re.compile(r"^\s*(?:refrain|chorus)\b[:\s-]*", re.I)
_ASTERISM_RE = re.compile(r"^[\s*•·_]+$")


def _block_lines(kind: str, inner: str) -> List[str]:
    """Block → text lines; ``<pre>`` keeps line breaks, ``<p>`` converts
    ``<br>`` then runs as prose."""
    if kind == "pre":
        txt = _TAG_RE.sub("", _html_mod.unescape(inner))
        return [ln for ln in txt.splitlines()]
    txt = re.sub(r"<br\s*/?>", "\n", inner, flags=re.I)
    return _TAG_RE.sub("", _html_mod.unescape(txt)).splitlines()


def parse_ballad_html(content_html: str) -> Dict[str, Any]:
    """Parse a ballad ``contentHtml`` into versions × stanza units.

    Two passes: (1) blocks → a token stream of ``version`` headings /
    ``ref`` verse-number tokens / ``text`` runs — verse refs like ``39A.8``
    open a new stanza wherever they occur (refs arrive mid-paragraph in
    prose-wrapped versions); (2) the token stream is folded into ordered
    units ``[{ref, kind: 'stanza'|'refrain', text}]``. ``Refrain:`` runs become
    refrain units; asterism breaks (``* * * * *``) are dropped; prose before
    the first version lands in ``notes``.
    """
    # legacy markup arrives escaped inside contentHtml (<H3>/<PRE>)
    content_html = _fix_mojibake(_html_mod.unescape(content_html))

    tokens: List[tuple] = []
    for m in _BLOCK_RE.finditer(content_html):
        kind, inner = m.group(1).lower(), m.group(2)
        lines = _block_lines(kind, inner)
        chunk = " ".join(ln.strip() for ln in lines if ln.strip())
        if not chunk:
            continue
        if kind.startswith("h"):
            vm = _VERSION_HEAD_RE.match(chunk)
            if vm:
                tokens.append(("version",
                               f"{vm.group(1)}{vm.group(2)}",
                               vm.group(3).strip()))
            else:
                tokens.append(("text", chunk))
            continue
        pos = 0
        for vm in _VERSE_REF_RE.finditer(chunk):
            if vm.start() > pos:
                tokens.append(("text", chunk[pos:vm.start()]))
            tokens.append(("ref",
                           f"{vm.group(1)}{vm.group(2)}.{vm.group(3)}"))
            pos = vm.end()
        if pos < len(chunk):
            tokens.append(("text", chunk[pos:]))

    units: List[Dict[str, str]] = []
    notes: List[str] = []
    title = None
    version = None  # e.g. "39A"
    refrain_idx = 0
    for tok in tokens:
        if tok[0] == "version":
            version, refrain_idx = tok[1], 0
            if title is None and tok[2]:
                title = tok[2]
            continue
        if tok[0] == "ref":
            version = tok[1].split(".")[0]
            units.append({"ref": tok[1], "kind": "stanza", "text": ""})
            continue
        s = re.sub(r"(?:\s*\*\s*){2,}", " ", tok[1]).strip()
        if not s or _ASTERISM_RE.match(s):
            continue
        rm = _REFRAIN_RE.match(s)
        if rm and version:
            refrain_idx += 1
            units.append({"ref": f"{version} Refrain {refrain_idx}",
                          "kind": "refrain",
                          "text": s[rm.end():].strip()})
        elif units:
            units[-1]["text"] = (
                (units[-1]["text"] + " " + s).strip()
                if units[-1].get("text") else s)
        else:
            notes.append(s)

    ballad_refs = sorted({u["ref"].split(".")[0] for u in units
                          if u["kind"] == "stanza"})
    return {
        "title": title,
        "ballad_refs": ballad_refs,
        "units": units,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# fetch_lyrics
# ---------------------------------------------------------------------------


def fetch_lyrics(entry: CatalogEntry) -> dict:
    """Fetch the ``chNNN.htm`` page, extract ``contentHtml``, map versions →
    stanza units → ``sections`` (one section per stanza; refrains labelled
    ``<ref> Refrain k``).

    Drops: ``page-missing`` (404 — lacuna in the etext), ``no-chapter-content``
    (page served but no chapterContent block), ``no-ballad-text`` (no stanza
    units parsed)."""
    try:
        resp = _get(entry.url)
    except Exception as e:
        # polite_get raises requests.HTTPError on 4xx — a 404 is a lacuna in
        # the transcription (documented: the etext "has some lacunae"), which
        # is a drop, not a retryable failure.
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 404 or "404" in str(e):
            raise DropItem("page-missing")
        raise

    chapter = extract_chapter(resp.text)
    if chapter is None:
        raise DropItem("no-chapter-content")

    parsed = parse_ballad_html(chapter["content_html"])
    stanza_units = [u for u in parsed["units"] if u["kind"] == "stanza"]
    if not stanza_units:
        raise DropItem("no-ballad-text")

    n = (entry.meta or {}).get("child_number")
    title = parsed["title"] or entry.title
    if n:
        title = re.sub(r"^\s*%d[A-Z]*\s*[:.)]\s*" % n, "", title) or title
    entry.title = title  # syncs back into the catalog row

    sections = [{"label": u["ref"], "content": u["text"]}
                for u in parsed["units"] if u["text"]]
    clean = "\n\n".join(u["text"] for u in parsed["units"] if u["text"])
    raw = "\n".join(f"{u['ref']} {u['text']}" for u in parsed["units"]
                    if u["text"])

    return {
        "title": title,
        "primary_artist": "Traditional",
        "artist": "Traditional",
        "category": entry.category or CATEGORY,
        "url": entry.url,
        "language": "en",
        "raw_lyrics": raw,
        "clean_lyrics": clean,
        "sections": sections,
        "corpus": "sacred-texts",
        "source": SOURCE_ID,
        "foreign_identifier": entry.foreign_identifier,
        "source_url": entry.url,
        "creator": "Traditional",
        "creator_url": None,
        "copyright_notice": SITE_NOTICE,
        "modified_note": None,
        "license": "LicenseRef-public-domain",
        "license_url": PD_LICENSE_URL,
        "license_tier": "pd",
        "release_ok": "yes",
        "meta": {
            "child_number": n,
            "book": BOOK_TITLE,
            "book_years": BOOK_YEARS,
            "editor": EDITOR,
            "version_refs": parsed["ballad_refs"],  # e.g. ["39A", "39B"]
            "stanza_count": len(stanza_units),
            "unit_count": len(parsed["units"]),
            "notes": parsed["notes"][:5],
            "line_structure": "stanza-blobs",
            "reader_format": "svelte-chapterContent",
        },
    }
