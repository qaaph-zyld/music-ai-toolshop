"""Wikisource XML-dump streaming library (lyrics-sources P2, agent D1).

WHY THIS EXISTS: the MediaWiki API catalog walk (``sources/wikisource_pd.py``
``iter_catalog``) was IP-rate-limited (429) at volume. Wikimedia publishes the
sanctioned bulk channel —
``dumps.wikimedia.org/<wiki>/latest/<wiki>-latest-pages-articles.xml.bz2`` —
so the P2 ingestor reads the dump instead of calling the API. This module is
**pure streaming IO**: no network, no ``requests``, constant memory.

Three public functions, one per pipeline stage:

* :func:`iter_dump_pages` — stream ``(ns, pageid, title, wikitext)`` tuples
  out of a ``pages-articles`` XML dump (``.bz2``/``.gz``/plain ``.xml``),
  one ``<page>`` element at a time via ``ElementTree.iterparse`` with
  ``elem.clear()`` + parent removal — memory stays bounded by ONE page.
* :func:`build_member_cats` — **pass 1**: collect ns-14 category pages and
  the parent-category links inside their wikitext, then DFS from the frozen
  entry roots (``SR_ENTRY_POINTS`` / ``EN_CATEGORIES``) to compute the
  descendant set ``{wiki: {member_cat_title: branch_slug}}``.
* :func:`iter_dump_candidates` — **pass 2**: emit ``CatalogEntry`` rows for
  ns-0 pages whose wikitext links ANY member category.

ADVERSARIAL FIX (megaplan spec delta §2): ns-0 pages sitting in book
*subcats* do NOT link the root category — a naive ``Народне песме`` substring
match would miss them. Membership is graph-derived from the category graph,
never name-matched. Branch assignment reuses ``wikisource_pd._branch_for_cat``
on each parent->child edge so slugs resolve exactly as the API walk does
(sr refines by subcat name; en inherits the entry slug — ``_branch_for_cat``
tokens never match English names so it is a passthrough there anyway).

Each yielded candidate carries a transient ``._wt`` attribute holding the raw
wikitext. It is deliberately NOT in ``meta`` (``meta`` is serialized into
``_catalog.json`` — the full page text would bloat the queue). Consumers must
read ``getattr(entry, "_wt", "")`` and never persist it.
"""

from __future__ import annotations

import bz2
import gzip
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple
from urllib.parse import quote

try:
    from . import wikisource_pd as wpd
    from ._common import CatalogEntry
except ImportError:  # pragma: no cover - sources/ dir directly on sys.path
    import wikisource_pd as wpd  # type: ignore
    from _common import CatalogEntry  # type: ignore


#: MediaWiki category-namespace aliases we honour on both wikis (normalized
#: via ``wikisource_pd._latin`` + lower so Cyrillic and Latin spellings of the
#: same prefix fold to one token — ``Категорија`` and ``Kategorija`` both
#: norm to ``kategorija``). A superset is safe: pass-2 also requires the link
#: target to be a known member cat.
_CAT_PREFIXES = frozenset({
    "kategorija",   # Категорија / Kategorija (sr canonical + latin alias)
    "kategoria",    # Категориа (common sr typo variant, also seen in _LANG_PREFIXES)
    "category",     # Category: — works on EVERY MediaWiki as an alias
    "kategorie",
    "categoria",
    "categorie",
    "kategori",
})

_LINK_RE = re.compile(r"\[\[\s*([^\[\]|]+?)\s*(?:\|[^\[\]]*)?\]\]")


def _local(tag: str) -> str:
    """Namespace-agnostic element local name (``{ns}page`` -> ``page``)."""
    return tag.rsplit("}", 1)[-1]


def _open_dump(path: Any) -> io.IOBase:
    """Open a dump for binary reading: .bz2 / .gz / plain XML."""
    p = str(path)
    if p.endswith(".bz2"):
        return bz2.open(p, "rb")
    if p.endswith(".gz"):
        return gzip.open(p, "rb")
    return open(p, "rb")


def _page_fields(elem: ET.Element) -> Tuple[int, str, str, str]:
    """Extract (ns, pageid, title, wikitext) from a ``<page>`` element.

    ``<id>`` appears as a direct child (page id) AND inside ``<revision>`` /
    ``<contributor>`` — iterating direct children only and taking the first
    ``<id>`` yields the page id. The first ``<revision>``'s ``<text>`` is the
    current wikitext (pages-articles carries one revision per page).
    """
    ns = 0
    pageid = ""
    title = ""
    wikitext = ""
    for child in elem:
        tag = _local(child.tag)
        if tag == "title":
            title = child.text or ""
        elif tag == "ns":
            try:
                ns = int(child.text or "0")
            except ValueError:
                ns = 0
        elif tag == "id" and not pageid:
            pageid = child.text or ""
        elif tag == "revision" and not wikitext:
            for rc in child:
                if _local(rc.tag) == "text":
                    wikitext = rc.text or ""
                    break
    return ns, str(pageid), str(title), wikitext


def iter_dump_pages(path: Any) -> Iterator[Tuple[int, str, str, str]]:
    """Stream ``(ns, pageid, title, wikitext)`` per ``<page>`` in the dump.

    ``ElementTree.iterparse`` + ``elem.clear()`` + removal from the root
    keeps peak memory at roughly one page — a multi-GB ``.bz2`` streams in
    constant space. Works on ``.bz2``, ``.gz`` and uncompressed ``.xml``
    (the committed test fixture is plain XML).
    """
    root: Optional[ET.Element] = None
    with _open_dump(path) as fh:
        for event, elem in ET.iterparse(fh, events=("start", "end")):
            tag = _local(elem.tag)
            if event == "start":
                if root is None:
                    root = elem  # the document root (<mediawiki>)
                continue
            if tag != "page":
                continue
            try:
                yield _page_fields(elem)
            finally:
                elem.clear()
                if root is not None:
                    try:
                        root.remove(elem)
                    except ValueError:  # pragma: no cover - nonstandard nesting
                        pass


def _cat_links(wikitext: str) -> Iterator[str]:
    """Yield category-link targets (``Категорија:X`` / ``Category:X`` incl.
    aliases) found in wikitext. ``[[:Категорија:X]]`` (leading colon) is a
    plain link, NOT membership — skipped per MediaWiki semantics."""
    for m in _LINK_RE.finditer(wikitext or ""):
        target = m.group(1).strip()
        if target.startswith(":"):
            continue
        if ":" not in target:
            continue
        prefix = wpd._latin(target.split(":", 1)[0]).lower()
        prefix = prefix.replace("_", " ").strip()
        if prefix in _CAT_PREFIXES:
            yield target


def _norm(cat_title: str) -> str:
    return wpd._catnorm(cat_title)


def build_member_cats(
    path: Any,
    entry_roots: Dict[str, Iterable[Tuple[str, Optional[str]]]],
    max_depth: int = 8,
) -> Dict[str, Dict[str, str]]:
    """PASS 1 — rebuild the category graph from the dump and compute the
    descendant set of each wiki's entry roots.

    ``entry_roots`` maps ``wiki -> iterable of (root_cat_title, forced_slug
    | None)`` — i.e. ``SR_ENTRY_POINTS`` / ``EN_CATEGORIES`` verbatim.
    A ``None`` forced slug means "resolve by name" (base ``ostalo`` +
    ``_branch_for_cat`` refinement per edge), matching ``_walk_sr``.

    MediaWiki category membership is recorded on the CHILD side: a
    subcategory's wikitext links its parents (``[[Категорија:Народне
    песме]]`` inside ``Категорија:Женске народне песме``). Pass 1 therefore
    inverts those links into parent -> children adjacency, then runs a
    sequential per-entry DFS (entries processed in declared order, first
    claim wins — the "broadest last" intent of the API walk) bounded by
    ``max_depth``.

    Returns ``{wiki: {member_cat_title: branch_slug}}`` keyed by the
    canonical category title as it appears in the dump (entry roots that
    have no ns-14 page in the dump still seed their own key).
    """
    # -- collect ns-14 pages: children[parent_norm] -> {child_norm, ...} ----
    children: Dict[str, set] = {}
    canonical: Dict[str, str] = {}
    for ns, _pid, title, wt in iter_dump_pages(path):
        if ns != 14:
            continue
        key = _norm(title)
        canonical.setdefault(key, title)
        for link in _cat_links(wt):
            pkey = _norm(link)
            children.setdefault(pkey, set()).add(key)
            canonical.setdefault(pkey, link.strip())

    # -- per-wiki DFS over the reversed edges ------------------------------
    out: Dict[str, Dict[str, str]] = {}
    for wiki, roots in entry_roots.items():
        member: Dict[str, str] = {}
        seen: set = set()
        refine = wiki == wpd.WIKI_SR  # en inherits the entry slug verbatim
        for root_cat, forced in roots:
            base = forced if forced else "ostalo"
            stack = [(root_cat, base, 0)]
            while stack:
                cat, branch, depth = stack.pop()
                key = _norm(cat)
                if key in seen or depth > max_depth:
                    continue
                seen.add(key)
                member[canonical.get(key, cat)] = branch
                for ck in sorted(children.get(key, ())):
                    child_branch = (
                        wpd._branch_for_cat(ck, branch) if refine else branch
                    )
                    stack.append((canonical.get(ck, ck), child_branch,
                                  depth + 1))
        out[wiki] = member
    return out


def iter_dump_candidates(
    path: Any,
    wiki: str,
    member_cats: Dict[str, str],
) -> Iterator[CatalogEntry]:
    """PASS 2 — yield ``CatalogEntry`` rows for ns-0 pages whose wikitext
    links any member category from :func:`build_member_cats`.

    ``member_cats`` is the per-wiki ``{member_cat_title: branch_slug}``
    dict; a page linking several member cats takes the branch of the FIRST
    matching link in page order (deterministic, mirrors dedup-first-wins).
    ``foreign_identifier`` is ``f"{wiki}:{pageid}"`` — identical to the API
    catalog so a mixed API/dump corpus dedups by pageid. ``meta`` carries
    ``{wiki, pageid, page_title, via: 'dump', member_cat}``; the raw wikitext
    rides the transient ``._wt`` attribute (never serialized — see module
    docstring).
    """
    lookup = {_norm(t): (slug, t) for t, slug in member_cats.items()}
    seen_pages = set()
    for ns, pageid, title, wt in iter_dump_pages(path):
        if ns != 0 or not pageid:
            continue
        slug = None
        member_title = None
        for link in _cat_links(wt):
            hit = lookup.get(_norm(link))
            if hit is not None:
                slug, member_title = hit
                break
        if slug is None or pageid in seen_pages:
            continue
        seen_pages.add(pageid)
        artist = wpd._artist(wiki)
        url = wpd.PAGE_URL[wiki].format(
            title=quote(title.replace(" ", "_")))
        entry = CatalogEntry(
            source_id=wpd.SOURCE_ID,
            foreign_identifier=f"{wiki}:{pageid}",
            title=title,
            url=url,
            artist=artist,
            creator=artist,
            source_url=url,
            license="LicenseRef-public-domain",
            license_url=wpd.PD_LICENSE_URL,
            license_tier="pd",
            release_ok="yes",
            category=slug,
            meta={
                "wiki": wiki,
                "pageid": pageid,
                "page_title": title,
                "via": "dump",
                "member_cat": member_title,
            },
        )
        entry._wt = wt  # transient — never serialized into _catalog.json
        yield entry


#: Convenience: the frozen entry roots per wiki for callers/CLI.
ENTRY_ROOTS = {
    wpd.WIKI_SR: wpd.SR_ENTRY_POINTS,
    wpd.WIKI_EN: wpd.EN_CATEGORIES,
}
