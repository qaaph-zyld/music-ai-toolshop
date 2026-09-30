"""hymnary.org adapter — pre-1931 hymn texts (SPEC §9, GATE 0 decision).

GATE 0 decision: **CSV-PRIMARY + HTML FALLBACK** — the ``&export=csv`` search
export is the primary catalog lane; a page-parse fallback walks ``/text/``
links when the export path is dead. If both fail the adapter raises (the
runner exits non-zero) and the lane defers — per R3's audit posture no
fragile forced scraper is built.

Pilot findings (2026-09-30, live-verified this wave):
- ``/search?qu=<q>&export=csv`` → ``text/csv`` with
  ``Content-Disposition: attachment; filename=searchResults.csv`` — works for
  ``in:texts``, ``in:instances``, ``in:hymnals`` lanes, capped at ~50 rows,
  ``&page=`` ignored.
- ``/search?qu=...`` HTML, ``/browse/*``, ``/hymnal/<code>``, ``/hymn/<code>/<n>``,
  ``/widgets``, ``?extended=true`` → 403 (Bunny rules; robots.txt warns "most
  bots will be blocked"). Instance hymn pages are unreachable → the emitted
  lyric text is the authority page's Representative Text; the ≤1930 evidence
  lives in instance metadata (``hymnalID`` year suffix / card ``Date`` field /
  hymnals CSV ``publicationDate``).
- ``/text/<id>`` authority pages → 200 (robots-clean — only ``/search/``,
  ``/result/*``, ``/mediawiki/`` etc. are disallowed; ``/search`` the bare path
  is *not* under the ``/search/`` prefix rule, so the CSV export URL passes).
- ``robots.txt`` declares ``Crawl-delay: 5`` for ``*`` → this adapter paces at
  5 s via ``MIN_INTERVAL_S`` (stricter than the registry default 1.5 s).
- Text pages carry a ``Copyright:`` infoTable field ("Public Domain" for
  Amazing Grace) — recorded to ``meta.copyright_field`` as corroborating
  evidence, never the sole basis.

The 1931 correctness gate (SPEC §9 + task contract):
- An item is emitted only when **some instance resolves to a publication year
  ≤ 1930** — via catalog ``hymnalID`` year suffix, a per-text instance CSV
  (``qu=<textAuthNumber> in:instances&export=csv``), the text page's instance
  cards (``data-fieldName='date'``), or the Representative Text's own trailing
  attribution ("Ancient & Modern, 2013").
- **An item with no resolvable year is DROPPED** (``date-unresolvable``) —
  silent PD assumption is a blocker. All-years-1931+ → ``post-1930-instance``.
- When the displayed Representative Text is from a post-1930 hymnal but a
  ≤1930 instance exists, the item is emitted with ``modified_note`` +
  ``meta.rep_text_source``/``rep_text_year`` recording exactly what was shown —
  the PD basis is the ≤1930 instance, and the caveat is auditable.
"""

from __future__ import annotations

import csv
import html as _html_mod
import io
import re
import time
from typing import Any, Dict, Iterator, List, Optional

try:  # package import (sources.hymnary) or flat sys.path (tests)
    from . import _common as _c
except ImportError:  # pragma: no cover
    import _common as _c  # type: ignore

CatalogEntry = _c.CatalogEntry
LicenseInfo = _c.LicenseInfo
DropItem = _c.DropItem

SOURCE_ID = "hymnary"
BASE_URL = "https://hymnary.org"
CATEGORY = "pre-1931"  # the only corpus category (SPEC §3.2 — releasable subset)

#: The 1931 boundary: a text must resolve to a publication year <= this.
MAX_PD_YEAR = 1930

#: robots.txt ``Crawl-delay: 5`` for ``User-agent: *`` (fetched 2026-09-30) —
#: enforced here because the vendored RobotsPolicy only tracks Disallow paths.
MIN_INTERVAL_S = 5.0

PD_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"

#: Curated pre-1931 hymnal IDs, harvested 2026-09-30 from live
#: ``in:instances`` CSV rows (hymnalID trailing digits = hymnary's cataloged
#: publication year). ``CC1930`` deliberately excluded — cataloged 1930 but
#: self-titled "our 1931 book": a boundary ambiguity not worth a lane call.
PD_HYMNAL_SEEDS = (
    "EC1901",   # The Eureka Carols
    "GTSS1886", # Glorious Things in Sacred Song
    "HE1900",   # The Heavenly Echoes
    "KoK1915",  # The King of Kings
    "MSN11914", # The Message in Song Numbers 1 and 2
    "NCH1929",  # The New Christian Hymnal
    "NJM1916",  # National Jubilee Melodies
    "OSSN1908", # The Old Story in Song Number Two
    "P1894",    # The Peacemaker
    "SH1835",   # The Southern Harmony (New ed.)
    "SoP1895",  # Songs of the Peacemaker
    "UT1893",   # Unfading Treasures
)

#: Seed text authority ids for the HTML fallback lane — famous PD hymns whose
#: pages carry dense "Related Texts" + instance links to walk. Only consulted
#: when every CSV export fails.
HTML_SEED_TEXTS = (
    "amazing_grace_how_sweet_the_sound",
    "o_for_a_thousand_tongues_to_sing",
    "holy_holy_holy_lord_god_almighty",
)

#: Injectable seams — tests monkeypatch these (FakeSession / no-wait limiter);
#: production leaves them None (polite_get builds a per-source limiter).
_SESSION = None
_LIMITER = None


def _get(url: str, **kw):
    return _c.polite_get(
        url,
        SOURCE_ID,
        session=_SESSION,
        limiter=_LIMITER,
        min_interval_s=MIN_INTERVAL_S,
        **kw,
    )


# ---------------------------------------------------------------------------
# Year resolution helpers — the 1931 correctness gate
# ---------------------------------------------------------------------------

_YEAR4_RE = re.compile(r"(?<!\d)(1[5-9]\d{2}|20\d{2})(?!\d)")
_HYMNAL_ID_YEAR_RE = re.compile(r"(\d{4})$")


def year_from_hymnal_id(hymnal_id: Optional[str]) -> Optional[int]:
    """Publication year from a hymnalID's trailing digits (``OSSN1908`` →
    1908); ``None`` when the code carries no year suffix (``GC2``, ``200Scrip``
    — those resolve via the hymnals CSV ``publicationDate`` instead)."""
    if not hymnal_id:
        return None
    m = _HYMNAL_ID_YEAR_RE.search(hymnal_id.strip())
    return int(m.group(1)) if m else None


def years_in_text(s: Optional[str]) -> List[int]:
    """All 4-digit years (1500-2099) in free text — attribution strings like
    ``"Ancient & Modern, 2013"`` or instance-card ``Date: 1992`` fields."""
    if not s:
        return []
    return [int(m.group(1)) for m in _YEAR4_RE.finditer(s)]


def resolve_min_year(years) -> Optional[int]:
    """Smallest resolved year; ``None`` when nothing resolved (→ dropped)."""
    vals = [int(y) for y in years if y is not None]
    return min(vals) if vals else None


def instance_year(row: Dict[str, Any]) -> Optional[int]:
    """Resolve one instance row/card's publication year: explicit ``year``/
    ``publicationDate`` first, then the hymnalID suffix."""
    for k in ("year", "publicationDate", "date"):
        ys = years_in_text(str(row.get(k) or ""))
        if ys:
            return ys[0]
    return year_from_hymnal_id(row.get("hymnalID") or row.get("hymnal_id"))


def pd_status(instance_years) -> str:
    """Gate verdict for a resolved-year list:
    ``'pd'`` (min ≤1930) / ``'post-1930'`` (resolved but all >1930) /
    ``'unresolved'`` (no year at all — item must be dropped, never assumed)."""
    m = resolve_min_year(instance_years)
    if m is None:
        return "unresolved"
    return "pd" if m <= MAX_PD_YEAR else "post-1930"


# ---------------------------------------------------------------------------
# CSV export lane (primary, GATE 0)
# ---------------------------------------------------------------------------

CSV_EXPORT = BASE_URL + "/search?qu={q}&export=csv"

_TEXTS_COLS = {"displayTitle", "firstLine", "textAuthNumber"}
_INST_COLS = {"textAuthNumber", "hymnalTitle", "hymnalID", "number"}


def parse_csv_export(text: str, *, required: set) -> List[Dict[str, str]]:
    """Parse a hymnary ``&export=csv`` body. Raises ``ValueError`` when the
    body is not the expected CSV (e.g. a Bunny 403 HTML page or an empty
    export) — callers treat that as lane failure, not bad rows."""
    rows = list(csv.DictReader(io.StringIO(text.strip("\n"))))
    if not rows:
        raise ValueError("empty CSV export (no data rows)")
    header = set(rows[0].keys())
    if not required.issubset(header):
        raise ValueError(
            f"CSV export missing expected columns {sorted(required - header)} "
            f"(got {sorted(header)}) — not a usable export"
        )
    return rows


def _instances_csv_for(query: str, *, hymnal_scope: Optional[str] = None
                       ) -> List[Dict[str, str]]:
    """GET an ``in:instances`` CSV export for ``query`` (hymnal id or
    textAuthNumber); empty/invalid bodies propagate ``ValueError``.

    The ``in:instances`` scope is mandatory — a bare id is interpreted as a
    free-text search and returns unrelated texts (live-verified 2026-09-30).
    ``hymnal_scope`` keeps only rows whose ``hymnalID`` equals the seed code —
    when at least one matches; loose free-text strays never enter the merge."""
    q = f"{query} in:instances"
    resp = _get(CSV_EXPORT.format(q=q.replace(" ", "%20")))
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "csv" not in ctype and "text" not in ctype:
        raise ValueError(f"non-CSV response ({ctype}) for query {query!r}")
    rows = parse_csv_export(resp.text, required=_INST_COLS)
    if hymnal_scope:
        scoped = [r for r in rows
                  if (r.get("hymnalID") or "").strip() == hymnal_scope]
        if scoped:
            rows = scoped
    return rows


def _merge_instances(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    """Group instance CSV rows by textAuthNumber; per text collect instance
    list + resolved years + display metadata."""
    by_text: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        fid = (r.get("textAuthNumber") or "").strip()
        if not fid:
            continue
        t = by_text.setdefault(fid, {
            "textAuthNumber": fid,
            "title": (r.get("displayTitle") or r.get("textTitle")
                      or r.get("firstLine") or "").strip(),
            "first_line": (r.get("firstLine") or "").strip(),
            "authors": (r.get("authors") or "").strip(),
            "meter": (r.get("meter") or "").strip(),
            "languages": (r.get("languages") or "").strip(),
            "instances": [],
            "instance_years": [],
        })
        inst = {
            "hymnal_id": (r.get("hymnalID") or "").strip(),
            "hymnal_title": (r.get("hymnalTitle") or "").strip(),
            "number": (r.get("number") or "").strip(),
        }
        inst["year"] = instance_year(inst)
        t["instances"].append(inst)
        if inst["year"] is not None:
            t["instance_years"].append(inst["year"])
    for t in by_text.values():
        t["instance_years"] = sorted(set(t["instance_years"]))
        t["min_instance_year"] = resolve_min_year(t["instance_years"])
    return by_text


def _catalog_csv_lane(limit: Optional[int], offset: int) -> Iterator[CatalogEntry]:
    """Primary catalog: per-seed-hymnal ``in:instances`` CSV exports merged
    into one entry per text. Raises on the *first* fetch failure that is not
    per-hymnal; a seed whose export is empty/non-CSV is skipped with a note so
    one dead export doesn't kill the lane."""
    failures: List[str] = []
    texts: Dict[str, Dict[str, Any]] = {}
    for hid in PD_HYMNAL_SEEDS:
        try:
            rows = _instances_csv_for(hid, hymnal_scope=hid)
        except Exception as e:
            failures.append(f"{hid}: {e.__class__.__name__}: {e}")
            continue
        for fid, t in _merge_instances(rows).items():
            if fid in texts:
                old = texts[fid]
                old["instances"].extend(
                    i for i in t["instances"] if i not in old["instances"])
                old["instance_years"] = sorted(set(
                    old["instance_years"] + t["instance_years"]))
                old["min_instance_year"] = resolve_min_year(
                    old["instance_years"])
            else:
                texts[fid] = t
    if not texts:
        raise RuntimeError(
            "hymnary CSV-export lane produced no catalog rows "
            f"(seeds={len(PD_HYMNAL_SEEDS)}); failures: "
            + "; ".join(failures[:5])
        )
    items = sorted(texts.values(), key=lambda t: t["textAuthNumber"])
    if offset:
        items = items[offset:]
    if limit is not None:
        items = items[:limit]
    for t in items:
        meta = {
            "lane": "csv-export",
            "instances": t["instances"],
            "instance_years": t["instance_years"],
            "min_instance_year": t["min_instance_year"],
            "meter": t["meter"] or None,
            "languages": t["languages"] or None,
        }
        yield CatalogEntry(
            source_id=SOURCE_ID,
            foreign_identifier=t["textAuthNumber"],
            title=t["title"] or t["first_line"] or t["textAuthNumber"],
            url=f"{BASE_URL}/text/{t['textAuthNumber']}",
            creator=t["authors"],
            category=CATEGORY,
            meta=meta,
        )


# ---------------------------------------------------------------------------
# HTML fallback lane (secondary, GATE 0 — bounded page-parse, never a scraper)
# ---------------------------------------------------------------------------

_TEXT_LINK_RE = re.compile(r'href="/text/([a-z0-9_]+)"')


def text_links(html: str) -> List[str]:
    """``/text/<id>`` hrefs on a page (related-texts box, instances, nav)."""
    out, seen = [], set()
    for m in _TEXT_LINK_RE.finditer(html):
        tid = m.group(1)
        if tid not in seen:
            seen.add(tid)
            out.append(tid)
    return out


def _catalog_html_lane(limit: Optional[int], offset: int) -> Iterator[CatalogEntry]:
    """Fallback catalog: fetch seed text pages and collect ``/text/<id>``
    links (related texts + cross-references). Entries carry no year data —
    the fetch-time gate resolves it via the per-text instance CSV."""
    found: List[str] = []
    seen = set()
    for tid in HTML_SEED_TEXTS:
        try:
            resp = _get(f"{BASE_URL}/text/{tid}")
        except Exception:
            continue
        for link in text_links(resp.text):
            if link not in seen:
                seen.add(link)
                found.append(link)
    if not found:
        raise RuntimeError(
            "hymnary HTML fallback lane produced no text links — "
            "both catalog lanes are dead (deferring source; GATE 0 rule: "
            "no forced scraper)"
        )
    if offset:
        found = found[offset:]
    if limit is not None:
        found = found[:limit]
    for fid in found:
        yield CatalogEntry(
            source_id=SOURCE_ID,
            foreign_identifier=fid,
            title=fid.replace("_", " "),
            url=f"{BASE_URL}/text/{fid}",
            category=CATEGORY,
            meta={"lane": "html-fallback"},  # no year — fetch gate resolves
        )


def iter_catalog(limit: Optional[int] = None, offset: int = 0) -> Iterator[CatalogEntry]:
    """SPEC §6.3: CSV-export lane primary, HTML page-parse fallback; raise
    ``RuntimeError`` (→ runner exit 1 → documented deferral) when both fail."""
    try:
        yield from _catalog_csv_lane(limit, offset)
        return
    except Exception:
        pass  # fall through to the HTML lane
    yield from _catalog_html_lane(limit, offset)


# ---------------------------------------------------------------------------
# license_of — cheap gate over catalog-resolved years
# ---------------------------------------------------------------------------


def license_of(entry: CatalogEntry) -> LicenseInfo:
    """Fast gate: when the catalog row carries resolved instance years, drop
    post-1930-only items here. Rows with NO resolved year pass through — the
    authoritative gate lives in ``fetch_lyrics`` (page + per-text CSV resolve
    what a bare catalog row couldn't). Never upgrades the registry tier."""
    years = list((entry.meta or {}).get("instance_years") or [])
    if not years:
        return LicenseInfo()  # unresolved → fetch-time hard gate decides
    verdict = pd_status(years)
    if verdict == "post-1930":
        raise DropItem(f"post-1930-instance:min={min(years)}")
    return LicenseInfo(
        license="LicenseRef-public-domain",
        license_url=PD_LICENSE_URL,
        license_tier="pd",
        release_ok="yes",
    )


# ---------------------------------------------------------------------------
# /text/<id> authority page parsing
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_STANZA_NUM_RE = re.compile(r"^\s*(\d+)[.):\s]+")
_ATTR_RE = re.compile(r"^(.*?)[,;]?\s*\(?((?:1[5-9]\d{2}|20\d{2}))\)?\.?\s*$")


def _strip_tags(s: str) -> str:
    return _html_mod.unescape(_TAG_RE.sub("", s))


def _section_html(html: str, section_id: str) -> str:
    """Slice ``<div class='authority_section' id='at_<section_id>'>`` … up to
    the next ``authority_section`` div (or EOF)."""
    i = html.find(f"id='at_{section_id}'")
    if i < 0:
        return ""
    j = html.find("authority_section", i + 10)
    return html[i: j if j > 0 else len(html)]


def _infotable(html: str) -> Dict[str, str]:
    """``hy_infoLabel``/``hy_infoItem`` pairs from the Text Information block."""
    seg = _section_html(html, "text_info")
    labels = re.findall(r'hy_infoLabel">([^<]+)</span>', seg)
    items = re.findall(r'hy_infoItem">([^<]*)', seg)
    out: Dict[str, str] = {}
    for lab, val in zip(labels, items):
        out[lab.rstrip(":").strip().lower()] = _html_mod.unescape(val).strip()
    return out


def parse_representative_text(section: str):
    """Parse the ``at_fulltext`` block: ``<div property='text'><div
    class="authority_columns"><p>…</p>…<p>…</p>ATTRIBUTION</div></div>``.

    Returns ``(stanzas, attribution)`` — stanzas as line lists (leading stanza
    numbers stripped); the trailing attribution text ("Ancient & Modern,
    2013") sits after the final ``</p>`` inside the columns div.
    """
    m = re.search(r"<div class=\"authority_columns\">(.*?)</div>\s*</div>",
                  section, re.S)
    if not m:
        return [], ""
    inner = m.group(1)
    # attribution = text after the last </p>
    last_p = inner.rfind("</p>")
    attribution = _strip_tags(inner[last_p + 4:]).strip() if last_p >= 0 else ""
    body = inner[:last_p + 4] if last_p >= 0 else inner

    stanzas: List[str] = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        txt = _BR_RE.sub("\n", p)
        txt = _strip_tags(txt)
        lines = [ln.strip() for ln in txt.splitlines()]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        # strip leading stanza number: either a bare "1" first line
        # (``<p>1<br>`` splits it onto its own line) or an inline "1. " prefix.
        if re.fullmatch(r"\d+", lines[0]):
            lines.pop(0)
        elif lines:
            lines[0] = _STANZA_NUM_RE.sub("", lines[0], count=1).strip()
        if not lines:
            continue
        stanzas.append("\n".join(ln for ln in lines if ln))
    return [s for s in stanzas if s], attribution


def attribution_year(attribution: str) -> Optional[int]:
    """Trailing year from a rep-text attribution ("Ancient & Modern, 2013")."""
    ys = years_in_text(attribution)
    return ys[-1] if ys else None


def parse_instance_cards(section: str) -> List[Dict[str, Any]]:
    """Instance resultcards in ``at_instances``: ``/hymn/<CODE>/<n>`` links +
    hidden ``data-fieldName='date'`` fields. Year = card Date, else CODE
    suffix."""
    cards: List[Dict[str, Any]] = []
    seen_urls = set()
    # ``/hymn/<CODE>/page/<n>`` links are page-scan camera icons inside the
    # same card — only the canonical ``/hymn/<CODE>/<num>`` link is an
    # instance (numeric-only pattern excludes scans; each card also repeats
    # the link in its linkbox, so dedupe by URL).
    for m in re.finditer(
            r'href="(/hymn/([A-Za-z0-9]+)/(\d+))"', section):
        url, code, num = m.group(1), m.group(2), m.group(3)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        # bound the Date search to this card — the next resultcard boundary
        # ends it (a card with no Date must not inherit its neighbour's).
        nxt = section.find("class='resultcard", m.end())
        tail = section[m.end(): nxt if nxt > 0 else len(section)]
        dm = re.search(r"data-fieldName='date'[^>]*>\s*<b[^>]*>Date</b>:\s*([^<]*)",
                       tail)
        year = years_in_text(dm.group(1)) if dm else []
        cards.append({
            "url": BASE_URL + url,
            "hymnal_id": code,
            "number": num,
            "date": (dm.group(1).strip() if dm else ""),
            "year": year[0] if year else year_from_hymnal_id(code),
        })
    return cards


def parse_text_page(html: str) -> Dict[str, Any]:
    """Whole ``/text/<id>`` authority page → structured dict."""
    fulltext = _section_html(html, "fulltext")
    stanzas, attribution = parse_representative_text(fulltext)
    rep_year = attribution_year(attribution)

    author = None
    author_url = None
    people = _section_html(html, "people")
    am = re.search(r'id="Author"[^>]*>\s*Author:\s*<span[^>]*>([^<]+)</span>',
                   people)
    if am:
        author = _html_mod.unescape(am.group(1)).strip()
    pm = re.search(r'href="(/person/[^"]+)"', people)
    if pm:
        author_url = BASE_URL + pm.group(1)

    title = None
    tm = re.search(r"<div class='page-title'\s*><h1>(.*?)\s*(?:›|&rsaquo;|<)",
                   html, re.S)
    if tm:
        title = _strip_tags(tm.group(1)).strip()

    info = _infotable(html)
    cards = parse_instance_cards(_section_html(html, "instances"))
    return {
        "title": title or info.get("title"),
        "first_line": info.get("first line"),
        "author": author or info.get("author") or None,
        "author_url": author_url,
        "meter": info.get("meter") or None,
        "language": info.get("language") or None,
        "copyright_field": info.get("copyright") or None,
        "rep_stanzas": stanzas,
        "rep_attribution": attribution or None,
        "rep_year": rep_year,
        "instances": cards,
        "instance_years": sorted({c["year"] for c in cards if c.get("year")}),
    }


# ---------------------------------------------------------------------------
# fetch_lyrics — page fetch + the authoritative 1931 gate
# ---------------------------------------------------------------------------


def _years_for_entry(entry: CatalogEntry, page: Dict[str, Any]) -> List[int]:
    """Every resolvable year for this item: catalog meta + page cards +
    rep-text attribution."""
    years: List[int] = list((entry.meta or {}).get("instance_years") or [])
    years.extend(page.get("instance_years") or [])
    if page.get("rep_year") is not None:
        years.append(page["rep_year"])
    return sorted({y for y in years if y is not None})


def fetch_lyrics(entry: CatalogEntry) -> dict:
    """Fetch ``/text/<id>``, resolve the year gate, emit song JSON v2.

    Drop reasons (item never reaches disk):
    - ``no-lyric-text`` — page had no Representative Text block
    - ``date-unresolvable`` — no year could be resolved anywhere (never
      assumed PD)
    - ``post-1930-instance:<year>`` — every resolved instance is post-1930
    """
    # Some /text/ pages sit behind a transient Bunny "Establishing a secure
    # connection" challenge (403) while others serve 200 — live-verified this
    # wave. One extra spaced retry is cheap; persistent 403s stay `failed`
    # and are retried by --resume (a JS challenge is never forced, GATE 0).
    resp = None
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            resp = _get(entry.url)
            break
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if (status == 403 or "403" in str(e)) and attempt == 0:
                time.sleep(MIN_INTERVAL_S)
                continue
            raise
    if resp is None:  # pragma: no cover - defensive
        raise last_exc  # type: ignore[misc]
    page = parse_text_page(resp.text)

    if not page["rep_stanzas"]:
        raise DropItem("no-lyric-text")

    # If catalog meta lacks any year, try the per-text instance CSV once —
    # the HTML-fallback lane relies on this resolution.
    meta = dict(entry.meta or {})
    if not meta.get("instance_years"):
        try:
            rows = _instances_csv_for(entry.foreign_identifier)
            t = _merge_instances(rows).get(entry.foreign_identifier)
            if t:
                meta["instance_years"] = t["instance_years"]
                meta["instances"] = t["instances"]
                meta["min_instance_year"] = t["min_instance_year"]
        except Exception:
            pass  # card years / attribution may still resolve

    years = sorted(set(
        _years_for_entry(entry, page) + list(meta.get("instance_years") or [])
    ))
    verdict = pd_status(years)
    if verdict == "unresolved":
        raise DropItem("date-unresolvable")
    if verdict == "post-1930":
        raise DropItem(f"post-1930-instance:min={min(years)}")

    pd_year = min(years)
    pd_instance = None
    for inst in meta.get("instances") or []:
        if inst.get("year") == pd_year:
            pd_instance = inst
            break
    if pd_instance is None:
        for c in page["instances"]:
            if c.get("year") == pd_year:
                pd_instance = {
                    "hymnal_id": c["hymnal_id"], "number": c["number"],
                    "hymnal_title": None,
                }
                break

    sections = [{"label": str(i), "content": s}
                for i, s in enumerate(page["rep_stanzas"], 1)]
    clean = "\n\n".join(page["rep_stanzas"])

    rep_year = page.get("rep_year")
    modified_note = None
    if rep_year is not None and rep_year > MAX_PD_YEAR:
        modified_note = (
            f"Representative text displayed from "
            f"{page.get('rep_attribution') or 'a post-1930 hymnal'} "
            f"({rep_year}); PD basis: printed in a {pd_year} hymnal "
            f"(see meta.instances)."
        )

    title = entry.title or page["title"] or page["first_line"] or entry.foreign_identifier
    entry.title = title  # surfaces back into the catalog row via _sync_entry
    author = page["author"] or (entry.creator or None)
    pd_hymnal = (pd_instance or {}).get("hymnal_title")
    song = {
        "title": title,
        "primary_artist": author or pd_hymnal or "Traditional",
        "artist": author or "Traditional",
        "category": entry.category or CATEGORY,
        "url": entry.url,
        "language": (meta.get("languages") or page["language"] or "English"),
        "raw_lyrics": clean,
        "clean_lyrics": clean,
        "sections": sections,
        "corpus": "hymnary",
        "source": SOURCE_ID,
        "foreign_identifier": entry.foreign_identifier,
        "source_url": entry.url,
        "creator": author or "Traditional",
        "creator_url": page.get("author_url"),
        "copyright_notice": page.get("copyright_field"),
        "modified_note": modified_note,
        "license": "LicenseRef-public-domain",
        "license_url": PD_LICENSE_URL,
        "license_tier": "pd",
        "release_ok": "yes",
        "meta": {
            **meta,
            "pd_year": pd_year,
            "pd_instance": pd_instance,
            "rep_text_source": page.get("rep_attribution"),
            "rep_text_year": rep_year,
            "page_instance_years": page["instance_years"],
            "meter": meta.get("meter") or page.get("meter"),
            "first_line": page.get("first_line"),
        },
    }
    return song
