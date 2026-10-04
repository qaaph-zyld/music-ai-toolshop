#!/usr/bin/env python
"""Wikisource XML-dump ingestor (lyrics-sources P2, agent D1).

Bypasses ``fetch_lyrics_source.py`` on purpose: per-entry API refetch would
defeat the point of the sanctioned bulk channel (megaplan spec delta §1-2 —
the API catalog walk was IP-rate-limited). Two passes over the same dump:

    python wikisource_dump_ingest.py --dump <path> --wiki sr|en
        [--limit N] [--offset N] [--resume]

* pass 1 — ``sources.wikisource_dump.build_member_cats`` rebuilds the
  category graph from ns-14 pages and computes the descendant set of the
  frozen entry roots (sr: ``SR_ENTRY_POINTS`` @ depth 8; en:
  ``EN_CATEGORIES`` @ depth 2 — same bounds as the API walk).
* pass 2 — ``iter_dump_candidates`` streams ns-0 pages linking a member cat;
  each runs the SHARED ``wikisource_pd._song_from_wikitext`` pipeline
  (license-template gate -> verse cleaning -> Cyrillic->Latin fold) so
  dump-ingest songs are byte-shape identical to API-path songs, plus
  ``meta.via='dump'`` / ``meta.member_cat`` provenance.

Catalog semantics mirror ``fetch_lyrics_source.py``: candidates are upserted
into ``<corpus>/_catalog.json`` (pageid-keyed via ``foreign_identifier``);
``--resume`` skips rows already ``fetched``/``dropped``/``skipped`` (failed
and pending are retried — ``pending_slice`` parity); ``--limit``/``--offset``
slice the eligible candidate stream; statuses flush at least every
``_SAVE_EVERY`` processed items plus a final flush; ``_index.json`` is
rebuilt at the end via ``_common.write_index``.

NEVER ``import toolshop`` here — the eager package __init__ costs ~70 s
(megaplan F-B1); shared helpers live in ``sources/_common.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# UTF-8 console before anything prints (AGENTS.md hard rule).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from sources import registry as source_registry  # noqa: E402
from sources import wikisource_dump as wdump  # noqa: E402
from sources import wikisource_pd as wpd  # noqa: E402
from sources._common import DropItem, write_index, write_song_json  # noqa: E402
from sources.catalog import Catalog  # noqa: E402

SOURCE_ID = "wikisource_pd"

#: Per-wiki category-walk depth, mirroring the API walk bounds
#: (_walk_sr MAX_DEPTH=8, _walk_en depth<=2).
MAX_DEPTH = {"sr": 8, "en": 2}

#: Flush _catalog.json at least this often while processing — full per-item
#: flushes would be O(n^2) IO at 10k+ scale; a crash still loses <25 marks
#: and every write is idempotent, so --resume converges.
_SAVE_EVERY = 25

#: Statuses never reprocessed (skipped/dropped are adapter decisions;
#: fetched is completed work — mirrors pending_slice semantics).
_TERMINAL_ALWAYS = {"skipped", "dropped"}


def _eprint(*a: Any) -> None:
    print(*a, file=sys.stderr)


def run(
    dump_path: str,
    wiki: str,
    *,
    limit: Optional[int] = None,
    offset: int = 0,
    resume: bool = False,
    data_dir: Optional[Path] = None,
    quiet: bool = False,
) -> int:
    """Programmatic entry point. Returns a process exit code."""
    say = (lambda *a: None) if quiet else print

    try:
        row = source_registry.get(SOURCE_ID)
    except KeyError as e:
        _eprint(f"ERROR: {e}")
        return 2
    corpus_root = source_registry.corpus_root(row, data_dir)
    if corpus_root is None:
        _eprint(f"ERROR: source '{SOURCE_ID}' has no corpus dir.")
        return 2
    corpus_root.mkdir(parents=True, exist_ok=True)

    if wiki not in wdump.ENTRY_ROOTS:
        _eprint(f"ERROR: --wiki must be one of {sorted(wdump.ENTRY_ROOTS)}")
        return 2

    # -- pass 1: member-category set ---------------------------------------
    say(f"[{SOURCE_ID}] dump pass 1: building member-category set for "
        f"wiki '{wiki}' (roots={len(wdump.ENTRY_ROOTS[wiki])}, "
        f"max_depth={MAX_DEPTH[wiki]}) ...")
    member_cats = wdump.build_member_cats(
        dump_path, {wiki: wdump.ENTRY_ROOTS[wiki]},
        max_depth=MAX_DEPTH[wiki],
    )[wiki]
    say(f"[{SOURCE_ID}] member categories: {len(member_cats)}")
    if not member_cats:
        _eprint("ERROR: pass 1 found zero member categories — is this the "
                "right dump/wiki?")
        return 2

    catalog = Catalog.for_corpus(
        corpus_root, source_id=SOURCE_ID, corpus=row.get("corpus_tag"))

    # -- pass 2: candidate stream -> shared pipeline ------------------------
    stats: Dict[str, int] = {"fetched": 0, "failed": 0, "dropped": 0,
                             "offset_skipped": 0, "candidates": 0,
                             "terminal_skipped": 0}
    processed = 0
    eligible_seen = 0
    stopped = False

    for entry in wdump.iter_dump_candidates(dump_path, wiki, member_cats):
        stats["candidates"] += 1
        fid = entry.foreign_identifier
        existing = catalog.find(fid)
        st = (existing.get("status") or "pending") if existing else "pending"
        # pending_slice parity: skipped/dropped are never re-queued; fetched
        # is skipped only under --resume; failed/pending are (re)tried.
        if st in _TERMINAL_ALWAYS or (resume and st == "fetched"):
            stats["terminal_skipped"] += 1
            continue

        catalog.upsert_entries([entry], flush=False)
        stored = catalog.find(fid)
        wt = getattr(entry, "_wt", "")

        if eligible_seen < offset:
            eligible_seen += 1
            stats["offset_skipped"] += 1
            continue
        if limit is not None and processed >= limit:
            stopped = True
            break
        processed += 1
        label = f"{entry.artist or '?'} — {entry.title or fid}"

        try:
            song = wpd._song_from_wikitext(entry, wt, parsed_title=None)
        except DropItem as d:
            catalog.mark_entry(stored, "dropped", drop_reason=d.reason,
                               flush=False)
            stats["dropped"] += 1
            say(f"  [{processed}] DROP: {label} ({d.reason})")
        except Exception as e:  # noqa: BLE001 - per-item error, keep going
            catalog.mark_entry(stored, "failed",
                               error=f"{e.__class__.__name__}: {e}",
                               flush=False)
            stats["failed"] += 1
            say(f"  [{processed}] FAIL: {label} — {e}")
        else:
            song.setdefault("meta", {})["via"] = "dump"
            song["meta"]["member_cat"] = (entry.meta or {}).get("member_cat")
            try:
                json_path = write_song_json(
                    song, corpus_root,
                    song.get("category") or "ostalo")
            except Exception as e:  # noqa: BLE001
                catalog.mark_entry(
                    stored, "failed",
                    error=f"write_song_json: {e.__class__.__name__}: {e}",
                    flush=False)
                stats["failed"] += 1
                say(f"  [{processed}] FAIL(write): {label} — {e}")
            else:
                catalog.mark_entry(
                    stored, "fetched",
                    json_path=str(
                        json_path.relative_to(corpus_root)).replace("\\", "/"),
                    flush=False)
                stats["fetched"] += 1
                say(f"  [{processed}] OK ({song.get('category')}): {label}")

        if processed % _SAVE_EVERY == 0:
            catalog.save()

    catalog.save()

    # -- index rebuild -------------------------------------------------------
    result = write_index(corpus_root)
    say(f"[{SOURCE_ID}] index: {len(result['index'])} unique songs, "
        f"{len(result['dedup_log'])} intra-corpus dupes")
    tail = " (stopped at --limit)" if stopped else ""
    say(f"[{SOURCE_ID}] done{tail}: {stats} "
        f"(catalog counts: {catalog.counts()})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Ingest a Wikimedia pages-articles XML dump into the "
                    "wikisource_pd corpus (two passes: category graph, then "
                    "ns-0 member pages; no network).")
    p.add_argument("--dump", required=True,
                   help="path to <wiki>-latest-pages-articles.xml(.bz2/.gz)")
    p.add_argument("--wiki", required=True, choices=sorted(wdump.ENTRY_ROOTS),
                   help="which wiki the dump belongs to (entry-root set)")
    p.add_argument("--limit", type=int, default=None,
                   help="max candidates to process")
    p.add_argument("--offset", type=int, default=0,
                   help="skip first N eligible candidates")
    p.add_argument("--resume", action="store_true",
                   help="skip entries already fetched/dropped/skipped in "
                        "_catalog.json; retry pending/failed")
    p.add_argument("--quiet", action="store_true", help="suppress output")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args.dump, args.wiki, limit=args.limit, offset=args.offset,
               resume=args.resume, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
