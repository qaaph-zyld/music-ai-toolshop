#!/usr/bin/env python
"""Fetch dispatcher for license-tiered lyric sources (SPEC §6.4).

Usage:
    python fetch_lyrics_source.py --source <id> [--limit N] [--offset N]
        [--resume] [--category X] [--catalog-only|--rebuild-catalog] [--list]

Resolves the adapter named by ``sources/registry.json`` for ``--source``,
persists/merges ``<corpus>/_catalog.json`` (the resumable work queue), then —
for ``fetch_policy == 'auto'`` sources only — fetches each pending entry into
``data/toolshop/lyrics/<corpus_dir>/<category>/<slug>.json`` (+ ``.txt``) and
rebuilds ``_index.json``.

- ``--catalog-only`` / ``--rebuild-catalog``: run ``iter_catalog`` (bounded by
  --limit/--offset), merge into ``_catalog.json``, print counts, stop.
  ``fetch_policy != 'auto'`` sources may only ever run in this mode.
- ``--resume``: skip completed — ``fetched``/``skipped``/``dropped`` entries
  are not reprocessed, ``failed`` entries are retried (toolshop/batch.py
  semantics). Without it, ``fetched`` entries are re-fetched (refresh);
  ``skipped``/``dropped`` are never silently re-queued.
- Errors per item -> status ``failed`` + error string, flush, continue.

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
from sources._common import (  # noqa: E402
    CatalogEntry,
    DropItem,
    EnvGateError,
    entry_from_dict,
    write_index,
    write_song_json,
)
from sources.catalog import Catalog  # noqa: E402


def _eprint(*a: Any) -> None:
    print(*a, file=sys.stderr)


def _sync_entry(stored: Dict[str, Any], obj: CatalogEntry) -> None:
    """Copy adapter-mutable fields back into the stored catalog dict."""
    stored["status"] = obj.status or "pending"
    stored["drop_reason"] = obj.drop_reason
    stored["meta"] = obj.meta
    if obj.category:
        stored["category"] = obj.category
    for k in ("license", "license_url", "license_tier", "release_ok",
              "copyright_notice", "creator", "creator_url", "source_url",
              "artist", "url", "title", "foreign_identifier"):
        v = getattr(obj, k, None)
        if v is not None:
            stored[k] = v


def _fill_song_defaults(
    song: Dict[str, Any], stored: Dict[str, Any], row: Dict[str, Any]
) -> Dict[str, Any]:
    """Give fetch_lyrics() output its provenance defaults (SPEC §3.3)."""
    song.setdefault("corpus", row.get("corpus_tag"))
    song.setdefault("source", row.get("id"))
    for k in ("foreign_identifier", "source_url", "creator", "creator_url",
              "copyright_notice", "modified_note", "license", "license_url",
              "license_tier", "release_ok", "derived_from", "language"):
        if song.get(k) is None and stored.get(k) is not None:
            song[k] = stored[k]
    if song.get("url") is None and stored.get("url"):
        song["url"] = stored["url"]
    if song.get("category") is None:
        song["category"] = stored.get("category")
    # registry defaults when the adapter left license unresolved
    if song.get("license") is None:
        song["license"] = row.get("license_ref_default")
    return song


def run(
    source_id: str,
    *,
    registry_path: Optional[Path] = None,
    adapter: Any = None,
    data_dir: Optional[Path] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    resume: bool = False,
    catalog_only: bool = False,
    category: Optional[str] = None,
    quiet: bool = False,
) -> int:
    """Programmatic entry point. Returns a process exit code (0 ok, 2
    policy/config refusal, 1 unexpected setup failure)."""
    say = (lambda *a: None) if quiet else print

    # -- registry row ------------------------------------------------------
    try:
        row = source_registry.get(source_id, path=registry_path)
    except KeyError as e:
        _eprint(f"ERROR: {e}")
        return 2

    # -- fetch policy gate (clear error BEFORE any catalog work) -----------
    if not catalog_only:
        try:
            source_registry.require_fetchable(row)
        except source_registry.FetchPolicyError as e:
            _eprint(f"ERROR: {e}")
            return 2

    # -- adapter resolution -------------------------------------------------
    if adapter is None:
        try:
            adapter = source_registry.resolve_adapter(row)
        except (source_registry.FetchPolicyError, RuntimeError) as e:
            _eprint(f"ERROR: {e}")
            return 2

    # -- env gate (jamendo ships inert until keyed) -------------------------
    try:
        source_registry.check_env_gate(row)
    except EnvGateError as e:
        _eprint(f"ERROR: {e}")
        return 2

    # -- corpus dir ----------------------------------------------------------
    corpus_root = source_registry.corpus_root(row, data_dir)
    if corpus_root is None:
        _eprint(
            f"ERROR: source '{source_id}' has no corpus_tag — registry row "
            f"only (paid pack / future audio lane)."
        )
        return 2
    corpus_root.mkdir(parents=True, exist_ok=True)

    catalog = Catalog.for_corpus(
        corpus_root, source_id=row.get("id"), corpus=row.get("corpus_tag")
    )

    # -- catalog listing -----------------------------------------------------
    catalog_existed = catalog.path.exists() and bool(catalog.entries)
    if catalog_only or not catalog_existed:
        if not hasattr(adapter, "iter_catalog"):
            _eprint(
                f"ERROR: adapter for '{source_id}' has no iter_catalog() "
                f"— nothing to list."
            )
            return 2
        # --limit/--offset bound the listing itself only in --catalog-only
        # mode; on a fetch run they slice the pending queue (avoids
        # double-slicing a freshly built catalog).
        list_limit = limit if catalog_only else None
        list_offset = offset if catalog_only else 0
        say(f"[{source_id}] listing catalog "
            f"(limit={list_limit}, offset={list_offset}) ...")
        try:
            new_entries = list(
                adapter.iter_catalog(limit=list_limit, offset=list_offset)
            )
        except EnvGateError as e:
            _eprint(f"ERROR: {e}")
            return 2
        except Exception as e:
            _eprint(f"ERROR: iter_catalog failed for '{source_id}': "
                    f"{e.__class__.__name__}: {e}")
            return 1
        added = catalog.upsert_entries(new_entries)
        catalog.save()
        say(f"[{source_id}] catalog -> {catalog.path} "
            f"({added} new, {len(catalog.entries)} total)")
    if catalog_only:
        counts = catalog.counts()
        say(f"[{source_id}] catalog-only: {counts}")
        return 0

    # -- fetch loop -----------------------------------------------------------
    if not hasattr(adapter, "fetch_lyrics"):
        _eprint(
            f"ERROR: adapter for '{source_id}' has no fetch_lyrics() — "
            f"catalog-only/manual sources have no fetch path (SPEC §6.3)."
        )
        return 2

    todo = catalog.pending(
        resume=resume, category=category, limit=limit, offset=offset
    )
    total = len(todo)
    stats = {"fetched": 0, "failed": 0, "dropped": 0, "skipped": 0}
    say(f"[{source_id}] {total} entries to process "
        f"(resume={resume}, corpus={corpus_root})")

    for i, stored in enumerate(todo, 1):
        obj = entry_from_dict(stored, source_id=row.get("id", ""))
        label = f"{obj.artist or obj.creator or '?'} — {obj.title or obj.foreign_identifier}"
        try:
            info = adapter.license_of(obj) if hasattr(adapter, "license_of") else None
        except DropItem as d:
            catalog.mark_entry(stored, "dropped",
                         drop_reason=d.reason)
            stats["dropped"] += 1
            say(f"  [{i}/{total}] DROP: {label} ({d.reason})")
            continue
        except Exception as e:
            catalog.mark_entry(stored, "failed",
                         error=f"{e.__class__.__name__}: {e}")
            stats["failed"] += 1
            say(f"  [{i}/{total}] FAIL(license): {label} — {e}")
            continue
        _sync_entry(stored, obj)
        if info is not None:
            info.apply_to(stored)
            stored["license_ref"] = stored.get("license")
            if stored.get("drop_reason") and stored.get("status") == "dropped":
                catalog.save()
                stats["dropped"] += 1
                say(f"  [{i}/{total}] DROP: {label} ({stored['drop_reason']})")
                continue

        try:
            song = adapter.fetch_lyrics(obj)
        except DropItem as d:
            catalog.mark_entry(stored, "dropped",
                         drop_reason=d.reason)
            stats["dropped"] += 1
            say(f"  [{i}/{total}] DROP: {label} ({d.reason})")
            continue
        except EnvGateError as e:
            _eprint(f"ERROR: {e}")
            catalog.save()
            return 2
        except Exception as e:
            _sync_entry(stored, obj)
            catalog.mark_entry(stored, "failed",
                         error=f"{e.__class__.__name__}: {e}")
            stats["failed"] += 1
            say(f"  [{i}/{total}] FAIL: {label} — {e}")
            continue
        _sync_entry(stored, obj)

        if not song:
            catalog.mark_entry(stored, "skipped",
                         drop_reason="fetch_lyrics returned empty")
            stats["skipped"] += 1
            say(f"  [{i}/{total}] SKIP: {label}")
            continue

        _fill_song_defaults(song, stored, row)
        try:
            json_path = write_song_json(
                song, corpus_root, stored.get("category") or "uncategorized"
            )
        except Exception as e:
            catalog.mark_entry(stored, "failed",
                         error=f"write_song_json: {e.__class__.__name__}: {e}")
            stats["failed"] += 1
            say(f"  [{i}/{total}] FAIL(write): {label} — {e}")
            continue
        catalog.mark_entry(
            stored, "fetched",
            json_path=str(json_path.relative_to(corpus_root)).replace("\\", "/"),
        )
        stats["fetched"] += 1
        say(f"  [{i}/{total}] OK ({stored.get('category')}): {label}")

    # -- index rebuild --------------------------------------------------------
    result = write_index(corpus_root)
    say(f"[{source_id}] index: {len(result['index'])} unique songs, "
        f"{len(result['dedup_log'])} intra-corpus dupes")
    say(f"[{source_id}] done: {stats} "
        f"(catalog counts: {catalog.counts()})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch lyrics into a license-tiered corpus "
                    "(registry: sources/registry.json)."
    )
    p.add_argument("--source", help="registry source id (see --list)")
    p.add_argument("--limit", type=int, default=None,
                   help="max entries to process (fetch) or list (--catalog-only)")
    p.add_argument("--offset", type=int, default=0,
                   help="skip first N eligible entries")
    p.add_argument("--resume", action="store_true",
                   help="skip completed (fetched/skipped/dropped) entries; "
                        "retry failed. Without it, fetched entries are "
                        "re-fetched (refresh semantics).")
    p.add_argument("--category", default=None,
                   help="only process catalog entries of this category")
    p.add_argument("--catalog-only", "--rebuild-catalog",
                   dest="catalog_only", action="store_true",
                   help="list/refresh _catalog.json without fetching "
                        "(the only mode allowed for catalog-only/manual sources)")
    p.add_argument("--list", action="store_true",
                   help="list registry sources and exit")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        for row in source_registry.list_sources():
            print(f"  {row['id']:16s} {row['fetch_policy']:13s} "
                  f"{row['license_tier']:14s} adapter={row.get('adapter')} "
                  f"corpus={row.get('corpus_tag')}")
        return 0
    if not args.source:
        _eprint("ERROR: --source <id> required (see --list)")
        return 2
    return run(
        args.source,
        limit=args.limit,
        offset=args.offset,
        resume=args.resume,
        catalog_only=args.catalog_only,
        category=args.category,
    )


if __name__ == "__main__":
    sys.exit(main())
