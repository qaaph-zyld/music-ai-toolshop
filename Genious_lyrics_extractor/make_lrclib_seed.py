"""make_lrclib_seed.py — regenerate the lrclib ``_seed.json`` from lyrics.db.

P2-A/S1 (megaplan wave P2-A): the lrclib adapter is a *lookup* API — its
``iter_catalog`` reads a local seed file (``sources/lrclib.py`` seed
contract: ``<lrclib corpus root>/_seed.json|_seed.csv`` or the
``LRCLIB_SEED`` env var). This script rebuilds that seed from the
genius-pro corpus already ingested in ``lyrics.db``.

Reads ``lyrics.db`` via sqlite3 DIRECTLY — NEVER ``import toolshop``
(megaplan F-B1). Stdlib only; read-only connection.

db path resolution order::

    --db flag
    > TOOLSHOP_DATA_DIR env + '/lyrics/lyrics.db'
    > <repo>/data/toolshop/lyrics/lyrics.db

Emits ``<lrclib corpus root>/_seed.json``::

    {"entries": [{"artist": ..., "title": ...}, ...]}

No album/duration (genius lacks them) — every row routes the adapter to
``/api/search`` (1 call/row, see ``sources/lrclib.py:_lookup``).

Dedup on normalized ``(artist, title)`` — lowercase + strip + collapse
whitespace; rows with empty title/artist are skipped. Entries are sorted
by ``(artist, title)`` so re-running rewrites the file byte-identical.

``--dry-run`` prints the entry count only (no file written).
``--corpus`` overrides the default ``'genius-pro'`` for future corpora.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = "genius-pro"
LRCLIB_CORPUS_DIR = "lrclib"          # registry corpus_tag for the lrclib row
SEED_NAME = "_seed.json"

_WS_RE = re.compile(r"\s+")


def data_dir() -> Path:
    """TOOLSHOP_DATA_DIR > ``<repo>/data/toolshop`` — mirrors
    ``sources/registry.py:data_dir`` without importing the package."""
    raw = os.environ.get("TOOLSHOP_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return REPO_ROOT / "data" / "toolshop"


def default_db_path() -> Path:
    return data_dir() / "lyrics" / "lyrics.db"


def default_seed_path() -> Path:
    """``<data>/lyrics/lrclib/_seed.json`` — the corpus root the adapter
    resolves via ``sources.lrclib.seed_path``."""
    return data_dir() / "lyrics" / LRCLIB_CORPUS_DIR / SEED_NAME


def _norm(value: Optional[str]) -> str:
    """lowercase + strip + collapse whitespace — the dedup key unit."""
    return _WS_RE.sub(" ", (value or "").lower()).strip()


def _clean(value: Optional[str]) -> str:
    """Strip + collapse whitespace, preserving case — the emitted value."""
    return _WS_RE.sub(" ", (value or "")).strip()


def build_entries(db_path: Path, corpus: str = DEFAULT_CORPUS) -> List[Dict[str, str]]:
    """Query ``songs`` for ``corpus`` and return deduped, sorted seed
    entries ``[{"artist":..., "title":...}]`` — facts only, no lyric text.

    Dedup key: normalized ``(artist, title)``; first row in
    ``foreign_identifier`` order wins (deterministic representative).
    Rows whose normalized artist or title is empty are skipped.
    """
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute(
            "SELECT title, primary_artist, foreign_identifier "
            "FROM songs WHERE corpus = ? ORDER BY foreign_identifier",
            (corpus,),
        )
        seen: set[Tuple[str, str]] = set()
        entries: List[Dict[str, str]] = []
        for title, artist, _fid in rows:
            key = (_norm(artist), _norm(title))
            if not key[0] or not key[1]:
                continue
            if key in seen:
                continue
            seen.add(key)
            entries.append({"artist": _clean(artist), "title": _clean(title)})
    finally:
        con.close()
    entries.sort(key=lambda e: (_norm(e["artist"]), _norm(e["title"]),
                                e["artist"], e["title"]))
    return entries


def render_seed(entries: List[Dict[str, str]]) -> str:
    """Canonical serialization — stable across runs (idempotent rewrite)."""
    return json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n"


def write_seed(entries: List[Dict[str, str]], out: Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(render_seed(entries))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(
        description="Regenerate lrclib _seed.json from the lyrics.db corpus "
                    "(facts only: artist+title — no lyric text).")
    p.add_argument("--db", type=Path, default=None,
                   help="lyrics.db path (default: TOOLSHOP_DATA_DIR/lyrics/"
                        "lyrics.db > <repo>/data/toolshop/lyrics/lyrics.db)")
    p.add_argument("--corpus", default=DEFAULT_CORPUS,
                   help="songs.corpus value to seed from "
                        f"(default: {DEFAULT_CORPUS})")
    p.add_argument("--out", type=Path, default=None,
                   help="seed output path (default: <data>/lyrics/lrclib/"
                        f"{SEED_NAME})")
    p.add_argument("--dry-run", action="store_true",
                   help="print the entry count only — write nothing")
    args = p.parse_args(argv)

    db = Path(args.db) if args.db else default_db_path()
    if not db.exists():
        print(f"error: lyrics.db not found at {db} "
              f"(set --db or TOOLSHOP_DATA_DIR)", file=sys.stderr)
        return 2

    entries = build_entries(db, args.corpus)

    if args.dry_run:
        print(len(entries))
        return 0

    out = write_seed(entries, Path(args.out) if args.out else default_seed_path())
    print(f"make_lrclib_seed: corpus={args.corpus} db={db}")
    print(f"make_lrclib_seed: wrote {out} — {len(entries)} entries "
          f"(artist+title only; adapter routes to /api/search)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
