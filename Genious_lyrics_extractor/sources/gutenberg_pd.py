"""Project Gutenberg public-domain song-collection adapter (lyrics-sources
wave A, I3).

SPEC §2.1/§9 + R2 §4 + `gutenberg.org/policy/robot_access.html`:

* **Catalog-first.** The adapter ships a curated `WORKS` table (PD song /
  ballad collections) instead of crawling gutenberg.org. An optional
  offline catalog dump can be dropped at
  ``lyrics/gutenberg_pd/_src/pg_catalog.json`` and is merged in — no
  human-facing ebook or files page is ever scraped.
* **Sanctioned retrieval only.** Plain texts come from the robot-sanctioned
  mirror host ``aleph.gutenberg.org`` directory listings
  (``https://aleph.gutenberg.org/<digits>/<ebook>/``), which R2 confirmed is
  the official harvest target (``robot/harvest?filetypes[]=txt`` emits the
  same hosts). The file is cached under ``_src/pg<n>.txt`` for resume.
* Corporate TLS interception breaks hostname verification on aleph's
  certificate in this environment — ``_session(verify=False)`` is used ONLY
  for the aleph host and is documented in the handoff; nothing else in this
  module weakens TLS.

Song splitting: each work is a *collection*, so ``iter_catalog`` emits one
CatalogEntry per discovered song (``pg<ebook>:<idx>``), never one giant book.
Per-work ``kind`` selects the splitter:

* ``sotw``  — Songs of the West style: ``No. N TITLE`` headings, stanza
              numbers restart per song; [Music]/[Illustration]/arranger
              initials skipped.
* ``child`` — Child ballad volumes: bare arabic ballad number then CAPS
              title then lettered variants (``A``, ``B``...); each variant
              becomes its own song ``Title [A]``; stanza numbers printed.
              Vols II–V start numbering at 54/114/189/266, so the first
              ballad may be any number <=305 (subsequent ones must stay
              within +40 of the last — the CAPS-title lookahead is the real
              guard). ``=X.=``/``#X.#`` markers open a variant only when a
              bare stanza ``1`` follows (otherwise they are notes-section
              heads). Mid-volume ``APPENDIX`` and
              ``ADDITIONS AND CORRECTIONS`` heads switch to a supplement
              mode where CAPS headings are pieces in their own right
              (Child prints full extra versions there) instead of ending
              the lyric region.
* ``caps``  — generic CAPS-heading collections (Elizabethan, Yorkshire,
              misc): a >=5-char all-caps heading followed by >=2 indented
              verse lines opens a song; stanzas split on blank lines.
              Optional per-work flags: ``flush_left_heads`` requires
              headings at column 0 (indented CAPS refrain lines stay verse)
              and ``caps_paren`` also accepts a trailing parenthetical
              qualifier like ``(the later version.)``.

Body boundaries: text is cut to ``*** START/END OF ... GUTENBERG EBOOK ***``
then per-work END_HEADS (``NOTES ON THE SONGS``, ``GLOSSARY``, ``APPENDIX``,
``LIST OF SONG-BOOKS``, ``TRANSCRIBER'S NOTE``) stop the lyric region before
back-matter contaminates stanzas. END_HEADS only cut once the song region
has actually begun — tables of contents list the same headings verbatim
(e.g. a ``GLOSSARY`` or ``NOTES ON THE SONGS`` row before song 1), which
must not truncate the work.

``license_tier`` is frozen ``pd``/``release_ok=yes`` (all listed works are
pre-1930 PD); ``license_of`` returns the registry default.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from . import registry
    from ._common import (
        CatalogEntry,
        DropItem,
        LicenseInfo,
        polite_get,
    )
except ImportError:  # pragma: no cover - direct sys.path import
    import registry  # type: ignore
    from _common import (  # type: ignore
        CatalogEntry,
        DropItem,
        LicenseInfo,
        polite_get,
    )

SOURCE_ID = "gutenberg_pd"
ALEPH = "https://aleph.gutenberg.org"
GUTENBERG_EBOOK_URL = "https://www.gutenberg.org/ebooks/{n}"
PD_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"

# ---------------------------------------------------------------------------
# Curated PD song-collection catalog (R2 §4 ids verified against live mirror)
# ---------------------------------------------------------------------------

WORKS: Tuple[Dict[str, Any], ...] = (
    {"ebook": 44969, "key": "child-vol1",
     "title": "The English and Scottish Popular Ballads, Vol. I",
     "category": "child-ballads", "kind": "child",
     "editor": "Francis James Child"},
    {"ebook": 47692, "key": "child-vol2",
     "title": "The English and Scottish Popular Ballads, Vol. II",
     "category": "child-ballads", "kind": "child",
     "editor": "Francis James Child"},
    {"ebook": 62474, "key": "child-vol3",
     "title": "The English and Scottish Popular Ballads, Vol. III",
     "category": "child-ballads", "kind": "child",
     "editor": "Francis James Child"},
    {"ebook": 63116, "key": "child-vol4",
     "title": "The English and Scottish Popular Ballads, Vol. IV",
     "category": "child-ballads", "kind": "child",
     "editor": "Francis James Child"},
    {"ebook": 71104, "key": "child-vol5",
     "title": "The English and Scottish Popular Ballads, Vol. V",
     "category": "child-ballads", "kind": "child",
     "editor": "Francis James Child"},
    {"ebook": 56625, "key": "songs-of-the-west",
     "title": "Songs of the West",
     "category": "songs-of-the-west", "kind": "sotw",
     "editor": "Sabine Baring-Gould"},
    {"ebook": 27129, "key": "elizabethan",
     "title": "Lyrics from the Song-Books of the Elizabethan Age",
     "category": "elizabethan", "kind": "caps",
     "editor": "A. H. Bullen"},
    {"ebook": 47607, "key": "yorkshire",
     "title": "The Ballads and Songs of Yorkshire",
     "category": "yorkshire", "kind": "caps",
     "editor": "C. J. Davison Ingledew"},
    {"ebook": 7535, "key": "old-ballads",
     "title": "Old Ballads",
     "category": "misc", "kind": "caps"},
    {"ebook": 2831, "key": "bundle-of-ballads",
     "title": "A Bundle of Ballads",
     "category": "misc", "kind": "caps",
     # headings sit at column 0 (indented CAPS lines are verse refrains);
     # 'CHEVY CHASE (the later version.)' carries a lowercase qualifier
     "flush_left_heads": True, "caps_paren": True},
)

_WORK_BY_EBOOK = {w["ebook"]: w for w in WORKS}

#: back-matter headings (CAPS) that stop the lyric region per kind
_END_HEADS = {
    "GLOSSARY", "APPENDIX", "APPENDIX.", "INDEX", "LIST OF SONG-BOOKS",
    "NOTES ON THE SONGS", "NOTES", "TRANSCRIBER'S NOTE", "TRANSCRIBER'S NOTES",
    "TRANSCRIBERS NOTES", "LIST OF ILLUSTRATIONS", "ERRATA", "BIBLIOGRAPHY",
}
_SECTION_HEADS = {
    "CONTENTS", "INTRODUCTION", "FOREWORD", "PREFACE", "PREFACE.", "PROEM",
    "LIST OF COLOUR PLATES", "LIST OF PLATES", "EDITOR'S NOTE", "DEDICATION",
    "TO ", "CHRONOLOGICAL TABLE",
}
_CAPS_RE = re.compile(r"^\s*([A-Z][A-Z0-9 ,.'\-:&;\(\)\"!?]{4,})\s*$")
#: CAPS heading with an optional trailing '(any case)' qualifier —
#: 'CHEVY CHASE (the later version.)' in pg2831 (work flag caps_paren)
_CAPS_PAREN_RE = re.compile(
    r"^\s*([A-Z][A-Z0-9 ,.'\-:&;\(\)\"!?]{4,}?)\s*(\([^)]*\))?\s*$")
_BARE_NUM = re.compile(r"^\s*(\d{1,3})\s*\.?\s*$")
_BARE_LETTER = re.compile(r"^\s*([A-HJ-Z])\s*\.?\s*$")
#: decorated variant markers used by Child vols III–V: '=A.=', '#A.#', '#B#'
_VARIANT_MARK = re.compile(r"^\s*[#=]\s*([A-HJ-Z])\s*\.?\s*[#=]?\s*$")
_PAGE_NUM = re.compile(r"^\s*\[?\d{1,4}\s*[a-z]?\.?\]?\s*$")
_DIVIDER_RE = re.compile(r"^\*+(?:\s+\*+)*\s*$")
#: sentinel kept in the line stream for the child splitter — Child prints
#: a '* * *' rule between commentary and the ballad text(s); it is the
#: signal that a bare stanza '1' opens an unlettered text rather than a
#: quotation inside the apparatus
_DIVIDER = "\x00"

#: Child supplement heads that do NOT end the lyric region — each volume
#: interleaves 'APPENDIX' sections (extra full versions) after ballads and
#: closes with 'ADDITIONS AND CORRECTIONS' (which also prints complete
#: texts, e.g. the two 'Giles Collins' versions in vol. III).
_CHILD_SUPPLEMENT_HEADS = {"APPENDIX", "ADDITIONS AND CORRECTIONS"}
_END_HEADS_CLEAN = {h.rstrip(".") for h in _END_HEADS}
#: inside supplements, CAPS lines that are bibliographic citations,
#: initials signatures, or volume/page refs are NOT piece titles:
#: 'II, 28.', 'VOL. II.', 'P. 174.', 'I, 691.', 'G. L. K.', 'IX, 437.'
_SUPP_HEAD_BAD_RES = (
    re.compile(r"^(?:P|VOL|VOLS|NO|NOS)\.?\s"),
    re.compile(r"^[IVXLC]+[,\).]"),
    re.compile(r"^(?:[A-Z]\.\s*)+[A-Z]?\.?$"),
)
#: division heads inside a supplement piece ('FYTT II', 'SECOND FYTTE.',
#: 'PART THE SECOND.') do not open a new piece — they continue the current
#: one, keeping the following stanzas under the same title
_SUPP_PART_RE = re.compile(
    r"^(?:THE\s+)?(?:FIRST|SECOND|SECONDE|THIRD|THYRDE|THIRDE|FOURTH|"
    r"FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|PART|PARTE|BOOK|"
    r"FYTT?E?S?|FITT?E?S?|FYFTE?|FIT)\b")


def _supplement_head_ok(head: str) -> bool:
    """A supplement CAPS line is a real piece title only if it is not a
    citation head: no digits, not 'P. <n>'/'VOL. <n>', not a roman-numeral
    ref 'II, 28.', not initials 'G. L. K.'."""
    if re.search(r"\d", head):
        return False
    return not any(r.match(head) for r in _SUPP_HEAD_BAD_RES)


def _squeeze_interline_blanks(lines: List[str]) -> List[str]:
    """Many PG texts are 'double-spaced': every content line is followed by
    one blank, while real stanza/section breaks use runs of 2+. When blanks
    exceed ~45% of lines, drop single blanks between content lines and
    collapse longer runs to one separator — restoring the contiguous-verse
    topology the splitters were written for."""
    if not lines:
        return lines
    blank = sum(1 for l in lines if not l.strip())
    if blank / len(lines) <= 0.45:
        return lines
    out: List[str] = []
    run = 0
    for l in lines:
        if l.strip():
            if run >= 2:
                out.append("")
            run = 0
            out.append(l)
        else:
            run += 1
    return out


def _corpus_root() -> Path:
    return registry.corpus_root(registry.get(SOURCE_ID))


def _session():
    """requests.Session for the sanctioned aleph mirror. Corporate TLS
    interception breaks hostname verification on aleph in this environment,
    so certificate verification is disabled ONLY on this host session —
    documented in the I3 handoff."""
    import requests  # local: keep module import light for fixture tests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    s = requests.Session()
    s.verify = False
    return s


def _aleph_dir(ebook: int) -> str:
    d = "/".join(str(ebook)[:-1]) or "0"
    return f"{ALEPH}/{d}/{ebook}/"


def _txt_candidates(html: str, ebook: int) -> List[str]:
    names = re.findall(r'href="([^"]+\.txt)"', html, flags=re.I)
    names = [n.rsplit("/", 1)[-1] for n in names]
    pref = [n for n in names if re.fullmatch(rf"{ebook}-8\.txt", n)]
    mid = [n for n in names if re.fullmatch(rf"{ebook}-\d+\.txt", n)
           and n not in pref]
    plain = [n for n in names if n == f"{ebook}.txt"]
    old = [n for n in names
           if n not in pref + mid + plain and n.rsplit("/", 1)[-1]
           .startswith(str(ebook))]
    return pref + mid + plain + old


def _ensure_text(ebook: int, session=None, limiter=None) -> Path:
    """Resolve the plain-text file via the aleph directory listing and cache
    under ``_src/pg<n>.txt``. Any cache hit returns without network."""
    root = _corpus_root() / "_src"
    root.mkdir(parents=True, exist_ok=True)
    cache = root / f"pg{ebook}.txt"
    if cache.exists() and cache.stat().st_size > 0:
        return cache
    if session is None:
        session = _session()
    listing = polite_get(_aleph_dir(ebook), source_id=SOURCE_ID,
                         session=session, limiter=limiter)
    cands = _txt_candidates(listing.text or "", ebook)
    if not cands:
        raise DropItem(f"pg{ebook}:no-txt-in-mirror-listing")
    resp = polite_get(_aleph_dir(ebook) + cands[0], source_id=SOURCE_ID,
                      session=session, limiter=limiter)
    raw = resp.content if isinstance(resp.content, bytes) else b""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    cache.write_text(text, encoding="utf-8")
    return cache


def _load_offline_catalog() -> List[Dict[str, Any]]:
    p = _corpus_root() / "_src" / "pg_catalog.json"
    if not p.exists():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return doc.get("works", []) if isinstance(doc, dict) else []


def _work_for(ebook: int) -> Dict[str, Any]:
    if ebook in _WORK_BY_EBOOK:
        return _WORK_BY_EBOOK[ebook]
    for w in _load_offline_catalog():
        if int(w.get("ebook", -1)) == ebook:
            merged = dict(w)
            merged.setdefault("kind", "caps")
            merged.setdefault("category", "misc")
            return merged
    raise DropItem(f"pg{ebook}:not-in-catalog")


# ---------------------------------------------------------------------------
# Body region + splitters
# ---------------------------------------------------------------------------


def _slice_region(text: str) -> str:
    """Cut PG header (up to *** START ***) and footer (*** END *** /
    trailing license marker)."""
    lines = text.split("\n")
    start = 0
    end = len(lines)
    for i, l in enumerate(lines[:200]):
        if l.startswith("*** START OF") or "*** START OF THIS PROJECT" in l:
            start = i + 1
            break
    for i in range(len(lines) - 1, max(len(lines) - 8000, 0), -1):
        l = lines[i].strip()
        if l.startswith("*** END OF") or l.startswith("End of the Project")\
                or l.startswith("End of Project Gutenberg"):
            end = i
            break
    return "\n".join(lines[start:end])


def _cut_at_end_head(lines: List[str], i: int) -> bool:
    caps = _CAPS_RE.match(lines[i])
    if caps:
        head = caps.group(1).strip().rstrip(".")
        if head in {h.rstrip(".") for h in _END_HEADS}:
            return True
    return False


def _title_clean(raw: str) -> str:
    t = re.sub(r"\s+", " ", raw).strip().rstrip(".")
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        t = t.title()
    return t


def _stanzas(blocks: List[List[str]],
             printed_numbers: bool) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for blk in blocks:
        first = blk[0].strip()
        m = _BARE_NUM.match(first)
        label = f"Strofa {m.group(1)}" if (printed_numbers and m) else \
            f"Strofa {len(out) + 1}"
        content_lines = blk[1:] if (printed_numbers and m) else blk
        content = "\n".join(l.rstrip() for l in content_lines).strip()
        if content:
            out.append({"label": label, "content": content})
    return out


def _split_sotw(lines: List[str]) -> List[Tuple[str, List[List[str]]]]:
    """Songs of the West: 'No. N TITLE' headings; stanzas open ONLY on a
    printed stanza number — [Music]/arranger/singer lines between the
    heading and stanza 1 are apparatus and stay out."""
    songs: List[Tuple[str, List[List[str]]]] = []
    cur_title: Optional[str] = None
    cur: Optional[List[str]] = None
    blocks: List[List[str]] = []

    def flush():
        nonlocal blocks, cur
        if cur:
            blocks.append(cur)
            cur = None
        if cur_title is not None and blocks:
            songs.append((cur_title, blocks))
        blocks = []

    i = 0
    while i < len(lines):
        l = lines[i]
        # END_HEADS cut only after the song region has begun — the
        # CONTENTS page lists 'NOTES ON THE SONGS.' verbatim (pg56625)
        # and must not truncate the work before song 1.
        if _cut_at_end_head(lines, i) and cur_title is not None:
            break
        m = re.match(r"^\s*No\.?\s*(\d+)\s*[.,]?\s+(.+)$", l)
        if m:
            flush()
            cur_title = _title_clean(m.group(2))
            i += 1
            continue
        if cur_title is None:
            i += 1
            continue
        s = l.strip()
        if not s:
            # a lone stanza number survives the blank that separates it
            # from its verse (the squeeze maps '1' + 2+ blanks + verse to
            # '1', '', verse — flushing here would orphan the number and
            # drop the verse as apparatus, leaving every song empty)
            if cur and not (len(cur) == 1 and _BARE_NUM.match(cur[0])):
                blocks.append(cur)
                cur = None
            i += 1
            continue
        # bare digits = printed stanza numbers (must precede the page-num
        # skip — a bare '97' satisfies _PAGE_NUM too)
        if _BARE_NUM.match(s):
            if cur:
                blocks.append(cur)
            cur = [s]
            i += 1
            continue
        if (s.startswith("[") or _PAGE_NUM.match(s)
                or re.fullmatch(r"[A-Z]\. ?[A-Z]\.? ?[A-Z]?\.?", s)
                or s.startswith("Sung by") or s.startswith("Taken down")):
            i += 1
            continue
        if cur is None:
            i += 1  # apparatus before stanza 1
            continue
        cur.append(s)
        i += 1
    flush()
    return songs


def _unlettered_opens(lines: List[str], i: int) -> bool:
    """A bare stanza ``1`` opens an unlettered ballad text. Quotations of a
    single stanza inside the commentary are always followed soon by the
    real variant head (``A``, ``=A.=``, ``#A.#``) or a CAPS/supplement
    heading or a ``* * *`` rule — if any appears within the next 40 lines,
    this ``1`` is a quote, not a text start."""
    for j in range(i + 1, min(i + 40, len(lines))):
        l2 = lines[j]
        if l2 == _DIVIDER:
            return False
        s2 = l2.strip()
        if not s2:
            continue
        if (_BARE_LETTER.match(s2) or _VARIANT_MARK.match(s2)
                or _CAPS_RE.match(l2)):
            return False
    return True


def _mark_is_variant(lines: List[str], i: int) -> bool:
    """A ``=X.=``/``#X.#`` line is a *variant start* only when the next bare
    stanza number is ``1``. Child vols III–V also use these marks for
    notes-section heads listing variant readings (``5^1.``, ``8^1,`` … —
    never bare), where a False verdict keeps the notes out of stanza
    blocks. Scan stops at any other variant/letter/CAPS mark."""
    for j in range(i + 1, min(i + 60, len(lines))):
        s2 = lines[j].strip()
        if not s2:
            continue
        m = _BARE_NUM.match(s2)
        if m:
            return m.group(1) == "1"
        if (_CAPS_RE.match(lines[j]) or _VARIANT_MARK.match(lines[j])
                or _BARE_LETTER.match(s2)):
            return False
    return False


def _split_child(lines: List[str]) -> List[Tuple[str, List[List[str]]]]:
    """Child ballad volumes: ballad = bare number + CAPS title line;
    lettered variants (A/B/...) become separate songs; apparatus prose
    between the letter and stanza 1 is dropped; `#...#` citation lines and
    `[x]` footnote lines dropped.

    Vols II–V continue the numbering (54…305), so the first detected
    ballad may be any number <=305; later ones must stay within +40 of the
    previous ballad. ``=X.=``/``#X.#`` marks count as variant heads only
    when stanza 1 follows (``_mark_is_variant``) — elsewhere they head
    notes sections. ``APPENDIX``/``ADDITIONS AND CORRECTIONS`` heads do not
    end the work: they open a supplement mode in which CAPS headings are
    pieces of their own (Child prints full extra versions there); the next
    numbered ballad heading leaves supplement mode."""
    songs: List[Tuple[str, List[List[str]]]] = []
    ballad_title: Optional[str] = None
    variant: Optional[str] = None  # '' marks a supplement piece
    cur: Optional[List[str]] = None
    blocks: List[List[str]] = []
    last_ballad_no = 0
    supplement = False
    seen_star = False  # '* * *' rule since the current ballad heading

    def flush_variant():
        nonlocal blocks, cur
        if cur:
            blocks.append(cur)
            cur = None
        if ballad_title and variant is not None and blocks:
            label = (f"{ballad_title} [{variant}]" if variant
                     else ballad_title)
            songs.append((label, blocks))
        blocks = []

    i = 0
    while i < len(lines):
        l = lines[i]
        if l == _DIVIDER:
            seen_star = True
            if cur:
                blocks.append(cur)
                cur = None
            i += 1
            continue
        s = l.strip()
        caps = _CAPS_RE.match(l)
        if caps:
            head = caps.group(1).strip().rstrip(".")
            if head in _CHILD_SUPPLEMENT_HEADS:
                # only meaningful after the ballad region has begun —
                # a TOC 'APPENDIX' row is skipped like any other line
                if ballad_title is not None or supplement:
                    flush_variant()
                    ballad_title = None
                    variant = None
                    supplement = True
                i += 1
                continue
            if head in _END_HEADS_CLEAN:
                if ballad_title is not None or supplement:
                    break
                i += 1
                continue
            if supplement:
                if _SUPP_PART_RE.match(head):
                    i += 1  # 'SECOND FYTTE'/'PART ...' continue a piece
                    continue
                # CAPS heading inside a supplement: either a piece of its
                # own or a bibliographic citation head — in both cases the
                # previous piece is over
                ok = _supplement_head_ok(head)
                flush_variant()
                ballad_title = _title_clean(head) if ok else None
                variant = "" if ok else None
                i += 1
                continue
        # ballad heading: bare ballad number + CAPS title on the next
        # non-blank line (PG 44969 prints "1." then the title). The first
        # ballad of a volume may be any Child number <=305 (vol. II starts
        # at 54, III at 114, IV at 189, V at 266).
        nm = _BARE_NUM.match(s)
        if (nm and int(nm.group(1)) > last_ballad_no
                and int(nm.group(1))
                <= (last_ballad_no + 40 if last_ballad_no else 305)):
            j = i + 1
            while j < len(lines) and j <= i + 3 and not lines[j].strip():
                j += 1
            ncaps = _CAPS_RE.match(lines[j]) if j < len(lines) else None
            if ncaps:
                nhead = ncaps.group(1).strip().rstrip(".")
                if (nhead not in _END_HEADS_CLEAN
                        and nhead not in _CHILD_SUPPLEMENT_HEADS):
                    flush_variant()
                    last_ballad_no = int(nm.group(1))
                    ballad_title = _title_clean(nhead)
                    variant = None
                    supplement = False
                    seen_star = False
                    i = j + 1
                    continue
        if ballad_title is None:
            i += 1
            continue
        bl = _BARE_LETTER.match(s)
        if bl:
            flush_variant()
            variant = bl.group(1)
            i += 1
            continue
        vm = _VARIANT_MARK.match(s)
        if vm and _mark_is_variant(lines, i):
            flush_variant()
            variant = vm.group(1)
            i += 1
            continue
        if variant is None:
            # unlettered single-text ballad: no variant letter is printed
            # (e.g. 'HOBIE NOBLE', 'JAMIE TELFER' in vol. IV, 'CAPTAIN
            # WARD' in vol. V). The text proper begins after the '* * *'
            # rule that closes the commentary; where no rule is printed,
            # the lookahead distinguishes a real stanza '1' from a quoted
            # stanza inside the apparatus
            if (_BARE_NUM.match(s) and s.rstrip(".") == "1"
                    and (seen_star or _unlettered_opens(lines, i))):
                variant = ""
                cur = ["1"]
            i += 1
            continue
        if not s:
            # same lone-stanza-number rule as _split_sotw: a number
            # separated from its verse by 2+ blanks must not orphan
            if cur and not (len(cur) == 1 and _BARE_NUM.match(cur[0])):
                blocks.append(cur)
                cur = None
            i += 1
            continue
        if _BARE_NUM.match(s):
            if cur:
                blocks.append(cur)
            cur = [s]
            i += 1
            continue
        if ("#" in s
                and re.search(r"#\s*\d|\d\s*#|[a-z]\d|#[A-Za-z]", s)) \
                or _PAGE_NUM.match(s):
            i += 1
            continue
        if cur is None:
            i += 1  # apparatus prose before stanza 1
            continue
        if len(s) > 95:
            i += 1  # wrapped apparatus leaked mid-stanza
            continue
        cur.append(s)
        i += 1
    flush_variant()
    return songs


def _caps_head_title(m: "re.Match[str]") -> str:
    """Title for a CAPS heading match. With the ``caps_paren`` pattern a
    trailing '(qualifier)' is kept so e.g. the two Chevy Chase versions do
    not collapse to one title."""
    base = _title_clean(m.group(1))
    if m.re is _CAPS_PAREN_RE and m.lastindex and m.lastindex >= 2 \
            and m.group(2):
        inner = m.group(2).strip().lstrip("(").rstrip(")").strip() \
            .rstrip(".")
        if inner:
            base = f"{base} ({inner.title()})"
    return base


def _split_caps(lines: List[str], work: Optional[Dict[str, Any]] = None
                ) -> List[Tuple[str, List[List[str]]]]:
    """Generic CAPS-heading collection. A heading opens a song only when at
    least 2 indented verse lines (>=2 leading spaces) appear within the next
    8 lines — CONTENTS/back-matter lists fail that probe and are skipped.
    Section heads (PREFACE, INTRODUCTION...) are passed through; END_HEADS
    terminate once the song region has begun (a TOC row for the same
    heading must not cut early — pg2831 lists 'GLOSSARY').

    Work flags: ``flush_left_heads`` accepts only column-0 headings
    (indented CAPS lines are refrain verse, e.g. pg2831's 'UNWORTHY
    BARBARA ALLEN.'); ``caps_paren`` also accepts a trailing lowercase
    parenthetical qualifier ('CHEVY CHASE (the later version.)')."""
    work = work or {}
    flush_left = bool(work.get("flush_left_heads"))
    head_re = _CAPS_PAREN_RE if work.get("caps_paren") else _CAPS_RE
    songs: List[Tuple[str, List[List[str]]]] = []
    cur_title: Optional[str] = None
    cur: List[str] = []
    blocks: List[List[str]] = []

    def flush():
        nonlocal blocks, cur
        if cur:
            blocks.append(cur)
            cur = []
        if cur_title is not None and blocks:
            songs.append((cur_title, blocks))
        blocks = []

    def verse_probe(start: int) -> bool:
        hits = 0
        for j in range(start, min(start + 9, len(lines))):
            s = lines[j].strip()
            if _BARE_NUM.match(s) or (lines[j][:1] == " " and s
                                      and len(s) <= 95
                                      and not _CAPS_RE.match(lines[j])):
                hits += 1
                if hits >= 2:
                    return True
        return False

    i = 0
    while i < len(lines):
        l = lines[i]
        if _cut_at_end_head(lines, i) and cur_title is not None:
            break
        caps = head_re.match(l)
        if caps and (not flush_left or l[:1] not in (" ", "\t")):
            head = caps.group(1).strip().rstrip(".")
            if cur_title is not None and _SUPP_PART_RE.match(head):
                # 'SECOND FYTTE.'/'PART THE SECOND.' divide one long
                # ballad (Adam Bell, The Nut-Brown Maid, The Heir of
                # Linne) — keep its verse under the parent title instead
                # of cataloguing an anonymous fragment
                if cur:
                    blocks.append(cur)
                    cur = []
                i += 1
                continue
            if any(head.startswith(s.rstrip(".")) for s in _SECTION_HEADS):
                if cur_title is None:
                    i += 1
                    continue
            if verse_probe(i + 1):
                flush()
                cur_title = _caps_head_title(caps)
                i += 1
                continue
        if cur_title is None:
            i += 1
            continue
        s = l.strip()
        if not s:
            if cur:
                blocks.append(cur)
                cur = []
            i += 1
            continue
        # stanza numbers in caps works must be indented; flush-left bare
        # digits are page numbers
        if _BARE_NUM.match(s) and l[:1] in (" ", "\t"):
            if cur:
                blocks.append(cur)
            cur = [s]
            i += 1
            continue
        if _PAGE_NUM.match(s):
            i += 1
            continue
        # an *indented* part-head ('  FIRST PART.', pg2831 AULD ROBIN
        # GRAY) passes the flush-left check as verse — it is a division
        # label like its flush-left siblings, not a lyric line
        if _CAPS_RE.match(l) and _SUPP_PART_RE.match(s.rstrip(".")):
            if cur:
                blocks.append(cur)
                cur = []
            i += 1
            continue
        if (l[:1] == " " or l[:1] == "\t") and len(s) <= 95 and \
                not s.startswith("["):
            cur.append(s)
        i += 1
    flush()
    return songs


def split_songs(text: str, work: Dict[str, Any]) -> List[Tuple[str, List[List[str]]]]:
    body = _slice_region(text)
    lines = _squeeze_interline_blanks(body.split("\n"))
    kind = work.get("kind", "caps")
    if kind == "child":
        # keep '* * *' rules as sentinels: they mark the commentary/text
        # boundary the child splitter needs for unlettered texts
        lines = [_DIVIDER if _DIVIDER_RE.match(l.strip()) else l
                 for l in lines]
    else:
        lines = [l for l in lines if not _DIVIDER_RE.match(l.strip())]
    if kind == "sotw":
        return _split_sotw(lines)
    if kind == "child":
        return _split_child(lines)
    return _split_caps(lines, work)


# ---------------------------------------------------------------------------
# SPEC §6.3 contract
# ---------------------------------------------------------------------------


def iter_catalog(limit: Optional[int] = None, offset: int = 0,
                 session=None, limiter=None) -> Iterator[CatalogEntry]:
    """One CatalogEntry per discovered song across the curated WORKS table.
    ``offset``/`limit`` address the WORKS list (a work = a slice unit), not
    individual songs — the pilot's --limit 25 covers the whole table."""
    works = list(WORKS)
    works.extend(w for w in _load_offline_catalog()
                 if int(w.get("ebook", -1)) not in _WORK_BY_EBOOK)
    if offset:
        works = works[offset:]
    if limit is not None:
        works = works[:limit]
    for w in works:
        ebook = int(w["ebook"])
        path = _ensure_text(ebook, session=session, limiter=limiter)
        text = path.read_text(encoding="utf-8")
        songs = split_songs(text, w)
        if not songs:
            continue
        for idx, (title, _blocks) in enumerate(songs):
            url = GUTENBERG_EBOOK_URL.format(n=ebook)
            yield CatalogEntry(
                source_id=SOURCE_ID,
                foreign_identifier=f"pg{ebook}:{idx}",
                title=title,
                url=url,
                artist="Traditional",
                creator="Traditional",
                source_url=url,
                license="LicenseRef-public-domain",
                license_url=PD_LICENSE_URL,
                license_tier="pd",
                release_ok="yes",
                category=str(w.get("category", "misc")),
                meta={
                    "ebook": ebook,
                    "work_key": w.get("key"),
                    "work_title": w.get("title"),
                    "song_idx": idx,
                    "editor": w.get("editor"),
                },
            )


def license_of(entry: CatalogEntry) -> LicenseInfo:
    return LicenseInfo(
        license="LicenseRef-public-domain",
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
    )


def fetch_lyrics(entry: CatalogEntry, session=None, limiter=None) -> Dict[str, Any]:
    meta = dict(entry.meta or {})
    ebook = int(meta.get("ebook")
                or str(entry.foreign_identifier)[2:].split(":")[0])
    song_idx = int(meta.get("song_idx")
                   or str(entry.foreign_identifier).rsplit(":", 1)[-1])
    w = _work_for(ebook)
    path = _ensure_text(ebook, session=session, limiter=limiter)
    text = path.read_text(encoding="utf-8")
    songs = split_songs(text, w)
    if not (0 <= song_idx < len(songs)):
        raise DropItem(f"pg{ebook}:{song_idx}:song-index-out-of-range")
    title, blocks = songs[song_idx]
    printed = w.get("kind") in ("sotw", "child")
    sections = _stanzas(blocks, printed_numbers=printed)
    body = "\n\n".join(b["content"] for b in sections).strip()
    if len(body.split("\n")) < 4:
        raise DropItem(f"pg{ebook}:{song_idx}:too-short")

    url = str(entry.source_url or entry.url
              or GUTENBERG_EBOOK_URL.format(n=ebook))
    song: Dict[str, Any] = {
        "title": title,
        "artist": "Traditional",
        "primary_artist": "Traditional",
        "featured_artists": [],
        "category": str(entry.category or w.get("category", "misc")),
        "url": url,
        "language": "en",
        "raw_lyrics": body,
        "clean_lyrics": unescape(body),
        "sections": sections,
        "corpus": "gutenberg_pd",
        "source": SOURCE_ID,
        "foreign_identifier": str(entry.foreign_identifier),
        "source_url": url,
        "creator": "Traditional",
        "creator_url": None,
        "copyright_notice": None,
        "modified_note": None,
        "license": "LicenseRef-public-domain",
        "license_url": PD_LICENSE_URL,
        "license_tier": "pd",
        "release_ok": "yes",
        "derived_from": None,
        "script": "latin",
        "meta": {
            "ebook": ebook,
            "work_key": w.get("key"),
            "work_title": w.get("title"),
            "work_editor": w.get("editor"),
            "song_idx": song_idx,
            "mirror": _aleph_dir(ebook),
            "text_cache": str(path),
            "stanzas_printed_numbers": printed,
        },
    }
    return song
