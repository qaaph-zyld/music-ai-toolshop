"""mudcat.org Digital Tradition adapter — one-shot DigiTrad archive (SPEC §9).

The Digital Tradition folk-song database ships as a single MSDOS zip off
``https://mudcat.org/download.cfm`` (~7.7 MB, ~8.9k records, Spring 2002
snapshot). Per SPEC §9 and R2 §6:

- Fetch the zip ONCE into ``<corpus_root>/_src/``, unpack there, parse
  offline — **no per-song-page crawling** (robots ``Crawl-delay: 10`` and
  AI-bot UAs are hard-blocked on mudcat.org; the one-shot archive is the
  sanctioned lane).
- ``Z02.ASK`` is an askSam flat database: binary header + UI script +
  records whose fields are separated by ``\\x1c`` (ASCII FS). Each song
  record ends with a ``filename[ <SongID>`` marker; provenance fields
  (transcriber initials, date, ``play.exe`` tune key, author credit) sit in a
  short trailer after the marker.
- **Drop at catalog stage any entry carrying an explicit copyright marker**
  (``copyright`` / ``©`` / ``(c)`` + year or name / ``(p)`` + year /
  ``all rights reserved`` / permission-grant phrases). Dropped items never
  reach disk — they land in ``_catalog.json`` as ``status='dropped'`` with
  ``drop_reason='copyright-flagged:<marker>'`` only.
- Unflagged records are traditional/PD material under the DigiTrad
  not-for-profit charter → ``pd`` / ``LicenseRef-public-domain`` /
  ``release_ok='yes'``; the charter context is recorded in ``modified_note``
  (the manifest note required by GATE 0 Q4).

Title recovery is deliberately conservative: the askSam record carries no
explicit title field, so the parser reconstructs it positionally (the
caps-shout header line that precedes the lyric body). Records whose title
cannot be resolved to a plausible header are dropped ``title-unresolved``
rather than emitting a lyric-line or binary-junk "title".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:  # package import (sources.mudcat_digitrad) or flat sys.path (tests)
    from . import _common as _c
    from . import registry as _registry
except ImportError:  # pragma: no cover
    import _common as _c  # type: ignore
    import registry as _registry  # type: ignore

CatalogEntry = _c.CatalogEntry
LicenseInfo = _c.LicenseInfo
DropItem = _c.DropItem

SOURCE_ID = "mudcat_digitrad"
BASE_URL = "https://mudcat.org"
DOWNLOAD_URL = f"{BASE_URL}/download/DTSpring2002MSDOS.zip"
SOURCE_URL = f"{BASE_URL}/download.cfm"
CATEGORY = "dt"  # flat single bucket (SPEC §3.2); per-song @tags ride meta

ASK_FILENAME = "Z02.ASK"
TITLES_FILENAME = "TITLES"
ZIP_FILENAME = "DTSpring2002MSDOS.zip"
FETCH_STATE_FILENAME = "_fetch_state.json"

#: PD convention (SPEC §1.3): LicenseRef-public-domain + PDM deed URL.
LICENSE_TOKEN = "LicenseRef-public-domain"
PD_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"

#: Manifest note required for every emitted item (GATE 0 Q4 / SPEC §9): the
#: charter is not-for-profit so unflagged records are corpus/internal release
#: material. Stored in ``modified_note`` on song JSON and ``meta`` on catalog.
CHARTER_NOTE = (
    "Digital Tradition not-for-profit charter item; no copyright/© marker "
    "found in the source record (Spring 2002 askSam snapshot)."
)

#: Env var letting tests/ops point the adapter at a pre-staged _src dir.
ENV_SRC_DIR = "MUDCAT_DIGITRAD_SRC"

# ---------------------------------------------------------------------------
# Injectable seams (tests monkeypatch these; production leaves them None)
# ---------------------------------------------------------------------------

_SRC_DIR: Optional[Path] = None          # override for _src resolution
_SESSION = None                          # requests.Session-like for polite_get
_LIMITER = None                          # RateLimiter override


def _get(url: str, **kw):
    return _c.polite_get(url, SOURCE_ID, session=_SESSION, limiter=_LIMITER,
                         **kw)


def src_dir() -> Path:
    """``<corpus_root>/_src`` — overridable via ``_SRC_DIR`` or
    ``MUDCAT_DIGITRAD_SRC``; default resolves through the registry row so it
    tracks ``TOOLSHOP_DATA_DIR`` exactly like the dispatcher's corpus root."""
    if _SRC_DIR is not None:
        return Path(_SRC_DIR)
    env = os.environ.get(ENV_SRC_DIR)
    if env:
        return Path(env).expanduser().resolve()
    row = _registry.get(SOURCE_ID)
    root = _registry.corpus_root(row)
    assert root is not None  # mudcat row always has corpus_tag
    return Path(root) / "_src"


# ---------------------------------------------------------------------------
# askSam decoding
# ---------------------------------------------------------------------------

#: askSam uses \x1c as its field separator; other low control bytes show up
#: inside record bodies as embedded field marks — normalise them all to \x1c
#: BEFORE splitting so UI script text and binary runs collapse into skippable
#: fields instead of gluing onto lyric/title text.
_CTRL_MAP = {c: 0x1C for c in range(0x00, 0x1C)}


def ask_to_text(raw: bytes) -> str:
    """Decode an askSam blob: cp1252 → str, low control bytes → \x1c.

    ``errors='replace'`` keeps binary runs lossy-but-harmless; the field
    grammar below never treats replacement chars as content."""
    return raw.decode("cp1252", errors="replace").translate(_CTRL_MAP)


# ---------------------------------------------------------------------------
# Field grammar — record structure of the Spring 2002 MSDOS export
# ---------------------------------------------------------------------------

#: ``filename[ <SongID>`` terminates every song record. The id is the legacy
#: DOS filename (≤8+3 era) — letters/digits/_!$&'.- — followed by \x1c or EOF.
_FN_RE = re.compile(
    r"filename\s*\[\s*\x1c?\s*([A-Za-z0-9_!$'&.-]{2,16})(?=\x1c|$)", re.I)

_DATE_RE = re.compile(
    r"(?i)^\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*"
    r"\d{1,4}\s*$"
    r"|^\s*\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\s*$|^\s*\d{4}\s*$"
    r"|^\s*\d{1,2}(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"\d{2,4}\s*$")
_INIT_RE = re.compile(r"^[A-Z]{1,4}[a-z]{0,2}$")           # transcriber initials
_RULE_RE = re.compile(r"^\s*[-_*=.]{8,}\s*$")              # --- separator rules
_TAG_RE = re.compile(r"(?<!\S)@[A-Za-z][A-Za-z0-9_-]*")
_TAGLINE_RE = re.compile(r"^(?:\s*@[A-Za-z][A-Za-z0-9_-]*)+\s*$")
_META_RE = re.compile(r"(?i)^\s*(dt|child)\s*#")
_PAREN_RE = re.compile(r"^\(.{1,90}\)$")                   # (Author) subtitle
_DTNUM_RE = re.compile(r"(?i)\bdt\s*#\s*(\d+)")
_CHILD_RE = re.compile(r"(?i)\bchild\s*#?\s*(\d+[a-z]?)")
_TUNE_RE = re.compile(r"(?i)play\.exe.([A-Za-z0-9_]+)")
_HOW_RE = re.compile(r"(?i)\bhow\s+(?:the\s+)?song\s+came\b")

#: askSam embedded UI/script text — a field that is clearly program text, not
#: song content. Used both for trailer-walk and as a lookahead *reject*.
_SCRIPT_RE = re.compile(
    r'(?i)^\s*[{":]|^\s*(mes|free|disk|rem|screen|index|opt|col|row|enter|if|'
    r"else|return|quick|full|context|hint\d?|forget|soundex|exact)\b|[{}]")

#: UI banner strings that satisfy the caps heuristic but are never titles.
_STOP_TITLES = {
    "the digital tradition", "digital tradition", "asksam", "helpful hints",
    "enter search spec. here", "return", "quick list", "disk list",
    "disk show", "full search", "context", "hint", "hint2", "hint3", "hint4",
}

#: Note/apparatus line starters — anything at/after these is source metadata,
#: not lyric text (SPEC §9: source line + @tags → meta).
_NOTE_START_RE = re.compile(
    r"(?i)^(note:|notes:|source:|sources:|collected|recorded|published|"
    r"printed|transcribed|sung by|written by|words and music|words by|"
    r"music by|lyrics by|arr\.|arranged|tune:|see also|cf\.|also found|"
    r"version [a-d]\b|author|from the singing|from a |from the [a-z-]+ "
    r"(collection|manuscript|ms\.?|songbook|journal))")

#: Title-position fields that are actually junk — comma-joined transcriber
#: initials, inline chord charts, HTML drips, chorus markers, truncated
#: first-lines. A title matching one of these → record is dropped
#: ``title-unresolved``.
_INITIALS_JOINED_RE = re.compile(
    r"^[A-Z]{1,4}[a-z]?(\s*,\s*[A-Z]{1,4}[a-z]?)+\.?$")
_CHORD_TOKEN_RE = re.compile(
    r"^[A-G][#b]?(m|min|maj|dim|aug|sus|add)?[0-9]*(/[A-G][#b]?)?[0-9]*$",
    re.I)
_HTML_RE = re.compile(r"</?[a-zA-Z][^>]*>")


def _is_chord_chart(s: str) -> bool:
    toks = [t for t in re.split(r"[\s/|]+", s) if t]
    return len(toks) >= 3 and all(_CHORD_TOKEN_RE.match(t) for t in toks)


def _is_junk_title(s: str) -> bool:
    c = s.strip()
    if not c:
        return True
    if len(c) <= 2 and c.isupper():
        return True                                    # bare initials
    if _INITIALS_JOINED_RE.match(c):
        return True                                    # 'RG, RPf, GG' bleed
    if _is_chord_chart(c):
        return True                                    # 'F G C Em Am ...'
    if re.match(r"(?i)^(cho|chorus|refrain|verse)\s*\d*\s*[:.)]", c):
        return True                                    # 'CHORUS:' header junk
    if _HTML_RE.search(c):
        return True                                    # '</TD></TR>' drips
    if c.endswith((",", ";")):
        return True                                    # truncated lyric line
    if re.match(r"^\d[A-Z]", c):
        return True                                    # mojibake '6O FALSE..'
    if c[0].isdigit() and not any(ch.islower() for ch in c) and " " not in c:
        return True                                    # pure code fragments
    return False


def _alett(s: str) -> List[str]:
    return [ch for ch in s if ("a" <= ch <= "z") or ("A" <= ch <= "Z")]


def _is_titleish(f: str) -> bool:
    """Caps-shout heuristic: DigiTrad record titles are uppercase headers."""
    c = f.strip()
    if not c or len(c) > 95 or len(c) < 2:
        return False
    low = c.lower()
    if low in _STOP_TITLES:
        return False
    if c[0] in '{":' or c.startswith("@"):
        return False
    if low.startswith(("filename", "play.exe", "dt #", "child #",
                      "keywords", "note:", "notes:")):
        return False
    if _DATE_RE.match(c) or _RULE_RE.match(c) or _SCRIPT_RE.match(c):
        return False
    letters = _alett(c)
    if len(letters) < 2:
        return False
    return sum(ch.isupper() for ch in letters) / len(letters) > 0.6


def _is_trailer_field(f: str) -> bool:
    """Provenance-tail grammar: fields found between ``filename[ <id>`` and
    the next record's title — initials, dates, ``play.exe`` tune keys,
    ``(Author)`` credits, junk bytes, tag/meta tails, UI script leftovers."""
    c = f.strip()
    if not c:
        return True
    low = c.lower()
    if "play.exe" in low:
        return True
    if _DATE_RE.match(c):
        return True
    if _INIT_RE.match(c) and len(c) <= 4:
        return True
    if _PAREN_RE.match(c) and len(c) <= 90:
        return True
    if low in ("asksam", "sof", "eof", "dt", "the digital tradition"):
        return True
    if len(c) <= 4:
        letters = _alett(c)
        if len(letters) <= 1 or not c.isascii() or \
                not all(ch.isalpha() for ch in letters):
            return True
    if len(c) <= 3 and not _is_titleish(c):
        return True
    if c[0].isdigit() and len(c) <= 8:
        return True
    if _TAGLINE_RE.match(c) or _META_RE.match(c) or _RULE_RE.match(c):
        return True
    if c[0] in '{":' or _SCRIPT_RE.match(c):
        return True
    if _NOTE_START_RE.match(c):
        return True
    return False


#: Copyright markers — explicit only (the charter flags © where noted; a
#: bare 'by <name>' attribution is NOT a copyright flag). Order = audit order.
COPYRIGHT_PATTERNS: Tuple[Tuple[str, "re.Pattern"], ...] = (
    ("copyright-word", re.compile(r"(?i)copy\s*-?\s*right|copyright")),
    ("copyright-sign", re.compile("©")),
    ("c-paren-year", re.compile(r"\([Cc]\)\s*\(?\s*(19|20)\d{2}")),
    ("c-paren-name", re.compile(r"\([Cc]\)\s*[A-Z][a-z]+\s+[A-Z]")),
    ("p-paren-year", re.compile(r"\([Pp]\)\s*(19|20)\d{2}")),
    ("all-rights-reserved", re.compile(r"(?i)all\s+rights\s+reserved")),
    ("permission-grant", re.compile(
        r"(?i)(?:reproduced|reprinted|printed|used|appears|used here|"
        r"included).{0,50}permission|"
        r"(?:by|with(?:\s+the)?)\s+permission\s+of|"
        r"permission\s+(?:is\s+)?granted")),
)


def copyright_flag(text: str) -> Optional[Tuple[str, str]]:
    """``(marker_name, snippet)`` when ``text`` carries an explicit copyright
    marker, else ``None``. Snippet is bounded for catalog audit."""
    for name, pat in COPYRIGHT_PATTERNS:
        m = pat.search(text)
        if m:
            start = max(0, m.start() - 60)
            snippet = " ".join(text[start:m.end() + 40].split())[:160]
            return name, snippet
    return None


# ---------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------

#: How far past a ``filename[`` marker the provenance tail may extend before
#: we give up (bounded slice — never slice the whole remaining tail: O(n²)).
_TAIL_WINDOW = 900

_TITLE_FIELDS = (
    "filename", "title", "subtitle", "creator", "lyric_fields",
    "notes_fields", "tags", "dt_num", "child_num", "tune", "transcriber",
    "dt_date", "trailer_fields", "suspect_title", "copyright",
    "copyright_marker", "copyright_snippet",
)


def _find_title(fields: List[str]) -> Optional[int]:
    """Index of the record's title field inside the region split.

    The header title is the FIRST caps-shout field that (a) follows an
    empty/trailer/script boundary and (b) is followed by real content
    (skipping trailer-grammar fields, rejecting when a script field comes
    first — that means the candidate is itself UI text).
    """
    for i, f in enumerate(fields):
        if not _is_titleish(f):
            continue
        prev_ok = (i == 0 or not fields[i - 1].strip()
                   or _is_trailer_field(fields[i - 1])
                   or _SCRIPT_RE.match(fields[i - 1].strip()))
        if not prev_ok:
            continue
        next_ok: Optional[bool] = None
        for j in range(i + 1, min(len(fields), i + 7)):
            nf = fields[j].strip()
            if not nf:
                continue
            if _SCRIPT_RE.match(nf):
                next_ok = False
                break
            if _is_trailer_field(fields[j]):
                continue
            next_ok = True
            break
        if next_ok:
            return i
    return None


def _record_from_region(filename: str, region: str, trailer_text: str,
                        flag_tail_text: str,
                        prev_tail_flagged: bool) -> Dict[str, Any]:
    fields = region.split("\x1c")
    tidx = _find_title(fields)
    suspect = False
    if tidx is None:
        # controlled fallback: first non-trailer field
        for i, f in enumerate(fields):
            if not _is_trailer_field(f):
                tidx = i
                break
    if tidx is None:
        title, body = "", []
        suspect = True
    else:
        title = fields[tidx].strip()
        body = fields[tidx + 1:]
        suspect = not _is_titleish(title)

    # optional subtitle/credit — the first non-empty field directly after the
    # title (within a small lead window) when it is a (paren) credit or a bare
    # Trad./Anonymous marker.
    subtitle = None
    body = list(body)
    lead_i = None
    for i, f in enumerate(body[:4]):
        if f.strip():
            lead_i = i
            break
    if lead_i is not None:
        f0 = body[lead_i].strip()
        if f0.startswith("(") and len(f0) < 140 and ")" in f0:
            subtitle = f0.strip("() ")
            body.pop(lead_i)
        elif re.match(
                r"(?i)^(trad\.?|traditional|anonymous|anon\.?|author unknown)"
                r"[.!]?\s*$", f0):
            subtitle = "Traditional"
            body.pop(lead_i)

    trailer_fields = [t for t in trailer_text.split("\x1c") if t.strip()]
    # author credit may live in the trailer tail as a (paren) field
    if subtitle is None:
        for t in trailer_fields:
            tt = t.strip()
            if _PAREN_RE.match(tt) and len(tt) > 4:
                subtitle = tt.strip("() ")
                break

    tags: List[str] = []
    notes: List[str] = []
    lyric: List[str] = []
    dt_num = child_num = tune = transcriber = dt_date = None
    seen_sep = False
    for f in body:
        c = f.strip()
        if _TAGLINE_RE.match(c):
            tags.extend(t[1:] for t in _TAG_RE.findall(c))
            seen_sep = True
            continue
        dm = _DTNUM_RE.search(c)
        if dm:
            dt_num = dm.group(1)
            continue
        cm = _CHILD_RE.search(c)
        if cm:
            child_num = cm.group(1)
            notes.append(c)
            continue
        if _RULE_RE.match(c):
            seen_sep = True
            continue
        if _NOTE_START_RE.match(c):
            seen_sep = True
            notes.append(c)
            continue
        (notes if seen_sep else lyric).append(c)

    # provenance tail: tune key / initials / date
    for t in trailer_fields:
        tm = _TUNE_RE.search(t)
        if tm and tune is None:
            tune = tm.group(1)
            continue
        if transcriber is None and _INIT_RE.match(t.strip()) \
                and len(t.strip()) <= 4:
            transcriber = t.strip()
            continue
        if dt_date is None and _DATE_RE.match(t.strip()):
            dt_date = t.strip()

    # copyright flag: scan the WHOLE region (lead junk included — a © notice
    # in the previous record's trailer leaks into this region's lead fields
    # when it doesn't match the trailer grammar, and flagging on it is the
    # correct conservative call) plus the pre-title tail window after this
    # record's filename marker — the zone where post-record © annotations
    # live even when they don't match the trailer grammar.
    # askSam UI script fields are excluded — program text is not a notice.
    # ``prev_tail_flagged`` additionally propagates markers seen in the
    # consumed trailer tail so a notice flags the record on BOTH sides of it.
    scan_fields = [f for f in fields
                   if f.strip() and not _SCRIPT_RE.match(f.strip())]
    blob = "\x1c".join(scan_fields) + "\x1c" + flag_tail_text
    hit = copyright_flag(blob)
    marker = snippet = None
    if hit:
        marker, snippet = hit
    elif prev_tail_flagged:
        marker, snippet = "prev-record-trailer", ""

    creator = subtitle or "Traditional"
    return {
        "filename": filename,
        "title": title,
        "subtitle": subtitle,
        "creator": creator,
        "lyric_fields": lyric,
        "notes_fields": notes,
        "tags": tags,
        "dt_num": dt_num,
        "child_num": child_num,
        "tune": tune,
        "transcriber": transcriber,
        "dt_date": dt_date,
        "trailer_fields": trailer_fields,
        "suspect_title": suspect,
        "copyright": bool(hit) or bool(prev_tail_flagged),
        "copyright_marker": marker,
        "copyright_snippet": snippet,
    }


def parse_records(text: str) -> List[Dict[str, Any]]:
    """Split a decoded askSam blob into song record dicts.

    ``filename[ <id>`` markers are the record boundaries; each marker ends
    its own record and is followed by a bounded provenance tail (initials /
    date / tune key) that the next record's region must not swallow.
    """
    records: List[Dict[str, Any]] = []
    cursor = 0
    prev_tail_flagged = False
    for m in _FN_RE.finditer(text):
        region = text[cursor:m.start()]
        # consume the provenance tail after this marker
        tail_start = m.end()
        buf = text[tail_start:tail_start + _TAIL_WINDOW]
        tail_fields: List[str] = []
        off = 0
        seen_date = False
        for f in buf.split("\x1c"):
            c = f.strip()
            # once a date is seen, a caps field is almost certainly the NEXT
            # record's title — stop, don't eat it as initials.
            if seen_date and _is_titleish(f):
                break
            if _is_trailer_field(f):
                tail_fields.append(c)
                off += len(f) + 1
                if _DATE_RE.match(c):
                    seen_date = True
            else:
                break
        tail_text = "\x1c".join(tail_fields)
        # flag window: every field from filename-end up to the next real
        # title — a title is titleish AND outside the trailer grammar (bare
        # initials like 'RG' are both, so grammar must win or we'd stop at
        # the transcriber initials before reaching a © notice deeper in
        # the tail). Bounded at 60 fields for safety.
        flag_fields: List[str] = []
        for f in buf.split("\x1c")[:60]:
            if _is_titleish(f) and not _is_trailer_field(f):
                break
            flag_fields.append(f)
        flag_tail_text = "\x1c".join(flag_fields)
        cursor = tail_start + off
        rec = _record_from_region(
            m.group(1), region, tail_text, flag_tail_text, prev_tail_flagged)
        # propagate: this record's own trailer flag marks the next record too
        prev_tail_flagged = bool(copyright_flag(flag_tail_text))
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Archive acquisition — one-shot download + unpack, then fully offline
# ---------------------------------------------------------------------------

def _extract_zip(zip_path: Path, dest: Path) -> None:
    """Unpack the DigiTrad zip (sanitised member names; skips the executables
    we don't need but keeps them harmless on disk)."""
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name  # strip any directory traversal
            if not name:
                continue
            target = dest / name
            with zf.open(info) as src, target.open("wb") as out:
                out.write(src.read())


def _write_fetch_state(src: Path, url: str, data: bytes) -> None:
    state = {
        "url": url,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "downloaded": True,
    }
    (src / FETCH_STATE_FILENAME).write_text(
        json.dumps(state, indent=2), encoding="utf-8")


def ensure_ask(src: Optional[Path] = None) -> Path:
    """Return the path to a usable ``Z02.ASK``.

    Order: already-extracted → already-downloaded zip → one ``polite_get``
    download. Network failure raises (the runner reports exit 1; no blind
    retries — ``polite_get``'s own bounded backoff is the only retry).
    """
    src = Path(src) if src else src_dir()
    ask = src / ASK_FILENAME
    if ask.exists():
        return ask
    zip_path = src / ZIP_FILENAME
    if zip_path.exists():
        _extract_zip(zip_path, src)
        if ask.exists():
            return ask
    resp = _get(DOWNLOAD_URL, timeout=120.0)
    data = resp.content
    src.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(data)
    _extract_zip(zip_path, src)
    _write_fetch_state(src, DOWNLOAD_URL, data)
    if not ask.exists():
        raise RuntimeError(
            f"{ZIP_FILENAME} did not contain {ASK_FILENAME} — archive layout "
            f"changed; manual inspection needed (src={src})")
    return ask


# ---------------------------------------------------------------------------
# Record cache — parse once per process
# ---------------------------------------------------------------------------

_RECORD_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_TITLES_CACHE: Dict[str, set] = {}


def _load_titles(src: Path) -> set:
    """Normalised title set from the ``TITLES`` index file (positive signal
    only — the index is not coextensive with the archive)."""
    key = str(src)
    if key not in _TITLES_CACHE:
        out: set = set()
        tpath = src / TITLES_FILENAME
        if tpath.exists():
            raw = tpath.read_bytes().decode("cp1252", errors="replace")
            for line in raw.splitlines():
                for col in line.split("|"):
                    t = col.strip().rstrip("*").strip()
                    if t and not t.upper().startswith("TITLES"):
                        out.add(normalize_title(t))
        _TITLES_CACHE[key] = out
    return _TITLES_CACHE[key]


def normalize_title(t: str) -> str:
    t = t.upper()
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return " ".join(t.split())


def title_in_index(title: str, titles: set) -> bool:
    """Exact or base-form (paren-stripped / ``or``-alternate) index match."""
    forms = [normalize_title(title)]
    stripped = re.sub(r"\s*\([^)]*\)", "", title)
    forms.append(normalize_title(stripped))
    forms.append(normalize_title(re.split(r"(?i)\s+or\s+", stripped)[0]))
    # truncated trailing paren fragment ('... (Farewell and' with no close)
    forms.append(normalize_title(re.sub(r"\s*\([^)]*$", "", stripped)))
    return any(f and f in titles for f in forms)


def records(src: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Parsed record list for the resolved ``_src`` (memoized per dir)."""
    src = Path(src) if src else src_dir()
    key = str(src)
    if key not in _RECORD_CACHE:
        ask = ensure_ask(src)
        text = ask_to_text(ask.read_bytes())
        recs = parse_records(text)
        # deterministic foreign ids: duplicate filename markers get an
        # occurrence suffix (the archive has ~25 dup pairs).
        seen: Dict[str, int] = {}
        for rec in recs:
            base = rec["filename"]
            seen[base] = seen.get(base, 0) + 1
            n = seen[base]
            rec["foreign_identifier"] = base if n == 1 else f"{base}~{n}"
        _RECORD_CACHE[key] = recs
    return _RECORD_CACHE[key]


def _record_map(src: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    return {r["foreign_identifier"]: r for r in records(src)}


# ---------------------------------------------------------------------------
# Lyrics cleaning
# ---------------------------------------------------------------------------

#: Inline chord brackets are a DigiTrad convention: ``[C]``, ``[G7]``,
#: ``[Am/G]`` … strip bracketed chord tokens from clean_lyrics only.
def _strip_chords(line: str) -> str:
    def repl(m: "re.Match") -> str:
        inner = m.group(1).strip()
        if _CHORD_TOKEN_RE.match(inner):
            return ""
        return m.group(0)
    return re.sub(r"\[([^\[\]]{1,10})\]", repl, line)


def _clean_lyrics(lyric_fields: List[str]) -> str:
    lines: List[str] = []
    for f in lyric_fields:
        c = _strip_chords(f.strip())
        c = re.sub(r"[ \t]+", " ", c).strip()
        lines.append(c)
    # collapse ≥2 blank lines to one stanza break; drop edge blanks
    out: List[str] = []
    blank = False
    for c in lines:
        if not c:
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(c)
            blank = False
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


def _lyric_text(lyric_fields: List[str]) -> str:
    return "\n".join(f.rstrip() for f in lyric_fields).strip("\n")


_LANG_TAGS = {
    "french": "fr", "german": "de", "gaelic": "ga", "irish": "ga",
    "scots": "sco", "welsh": "cy", "spanish": "es", "italian": "it",
    "yiddish": "yi", "hebrew": "he", "latin": "la", "dutch": "nl",
    "portuguese": "pt", "swedish": "sv", "norwegian": "no", "danish": "da",
}


def _language_for(rec: Dict[str, Any], lyric_text: str) -> str:
    tags = {t.lower() for t in rec.get("tags") or []}
    for t in tags:
        if t in _LANG_TAGS:
            return _LANG_TAGS[t]
    return "en"


# ---------------------------------------------------------------------------
# Adapter contract (SPEC §6.3)
# ---------------------------------------------------------------------------

def _entry_for(rec: Dict[str, Any], titles: set) -> CatalogEntry:
    """Map a parsed record to its catalog row, deciding the catalog-stage
    drop (copyright flag / unresolvable title / no lyric text)."""
    fid = rec["foreign_identifier"]
    drop_reason = None
    if rec["copyright"]:
        drop_reason = f"copyright-flagged:{rec['copyright_marker']}"
    elif not rec["title"] or (
            (_is_junk_title(rec["title"]) or rec["suspect_title"])
            and not title_in_index(rec["title"], titles)):
        drop_reason = "title-unresolved"
    elif not _clean_lyrics(rec["lyric_fields"]):
        drop_reason = "no-lyric-text"

    meta: Dict[str, Any] = {
        "dt_filename": rec["filename"],
        "tags": rec["tags"],
        "charter_note": CHARTER_NOTE,
        "title_verified": title_in_index(rec["title"], titles),
        "copyright_flagged": rec["copyright"],
    }
    if rec["copyright_marker"]:
        meta["copyright_marker"] = rec["copyright_marker"]
    if rec["copyright_snippet"]:
        meta["copyright_snippet"] = rec["copyright_snippet"]
    for k in ("dt_num", "child_num", "tune", "transcriber", "dt_date",
              "subtitle"):
        if rec.get(k):
            meta[k] = rec[k]
    if rec["notes_fields"]:
        meta["source_line"] = " | ".join(
            n for n in rec["notes_fields"] if n)[:500]
    if rec["suspect_title"]:
        meta["suspect_title"] = True

    return CatalogEntry(
        source_id=SOURCE_ID,
        foreign_identifier=fid,
        title=rec["title"] or fid,
        url=SOURCE_URL,
        artist=rec["creator"],
        creator=rec["creator"],
        creator_url=None,
        source_url=SOURCE_URL,
        license=LICENSE_TOKEN if drop_reason is None else None,
        license_url=PD_LICENSE_URL if drop_reason is None else None,
        license_tier="pd",
        release_ok="yes" if drop_reason is None else None,
        copyright_notice=None,
        category=CATEGORY,
        status="dropped" if drop_reason else "pending",
        drop_reason=drop_reason,
        meta=meta,
    )


def iter_catalog(limit: Optional[int] = None, offset: int = 0,
                 *, src_dir: Optional[Path] = None
                 ) -> Iterator[CatalogEntry]:
    """Enumerate the offline DigiTrad archive (SPEC §6.3).

    Copyright-flagged, title-unresolved, and lyric-less records are emitted
    as ``status='dropped'`` catalog rows (auditable) — they never reach the
    fetch loop, ``license_of``, or disk.
    """
    src = Path(src_dir) if src_dir else globals()["src_dir"]()
    titles = _load_titles(src)
    recs = records(src)
    sliced = recs[offset:] if offset else recs
    if limit is not None and limit >= 0:
        sliced = sliced[:limit]
    for rec in sliced:
        yield _entry_for(rec, titles)


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Unflagged records → pd/yes; flagged → DropItem (belt: license_of may
    only DOWNGRADE the registry default, SPEC §6.3)."""
    meta = getattr(entry, "meta", {}) or {}
    if meta.get("copyright_flagged") or (
            entry.drop_reason or "").startswith("copyright-flagged"):
        marker = meta.get("copyright_marker") or "marker"
        raise DropItem(f"copyright-flagged:{marker}")
    if (entry.drop_reason or "") and entry.status == "dropped":
        raise DropItem(entry.drop_reason)
    return LicenseInfo(
        license=LICENSE_TOKEN,
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
        copyright_notice=None,
    )


def fetch_lyrics(entry: CatalogEntry, *,
                 src_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Song JSON v2 for an approved record (SPEC §3.3).

    Defense-in-depth: re-checks the copyright flag from the archive record
    itself — a copyright-flagged item NEVER produces a song dict.
    """
    src = Path(src_dir) if src_dir else globals()["src_dir"]()
    meta = getattr(entry, "meta", {}) or {}
    if meta.get("copyright_flagged"):
        raise DropItem(
            f"copyright-flagged:{meta.get('copyright_marker') or 'marker'}")
    rec = _record_map(src).get(entry.foreign_identifier)
    if rec is None:
        raise DropItem("record-not-in-archive")
    if rec["copyright"]:
        raise DropItem(f"copyright-flagged:{rec['copyright_marker']}")

    raw = _lyric_text(rec["lyric_fields"])
    clean = _clean_lyrics(rec["lyric_fields"])
    if not clean:
        raise DropItem("no-lyric-text")

    creator = rec["creator"]
    stanzas = [s for s in clean.split("\n\n") if s.strip()]
    song: Dict[str, Any] = {
        "title": rec["title"],
        "artist": creator,
        "primary_artist": creator,
        "featured_artists": [],
        "category": CATEGORY,
        "url": SOURCE_URL,
        "language": _language_for(rec, raw),
        "raw_lyrics": raw,
        "clean_lyrics": clean,
        "sections": [{"label": None, "content": s} for s in stanzas],
        "corpus": "mudcat-digitrad",
        "source": SOURCE_ID,
        "foreign_identifier": entry.foreign_identifier,
        "source_url": SOURCE_URL,
        "creator": creator,
        "creator_url": None,
        "copyright_notice": None,
        "modified_note": CHARTER_NOTE,
        "license": LICENSE_TOKEN,
        "license_url": PD_LICENSE_URL,
        "license_tier": "pd",
        "release_ok": "yes",
        "derived_from": None,
        "meta": {
            "dt_filename": rec["filename"],
            "tags": rec["tags"],
            "charter_note": CHARTER_NOTE,
            **{k: rec[k] for k in
               ("dt_num", "child_num", "tune", "transcriber", "dt_date",
                "subtitle") if rec.get(k)},
            **({"source_line": " | ".join(
                n for n in rec["notes_fields"] if n)[:500]}
               if rec["notes_fields"] else {}),
        },
    }
    return song
