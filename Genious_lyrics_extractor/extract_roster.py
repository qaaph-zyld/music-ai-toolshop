"""Roster-driven lyrics extraction from Genius (P3 / batch G3).

Generalizes extract_artists.py / extract_batch3.py: the artist list lives in
``roster_g3.json`` (``{"artists": [{name, folder, cohort, variants[], ...}]}``)
instead of a hardcoded ARTISTS table, and categorization is roster-wide:

- primary artist matches the fetched artist, no other roster artist present
  -> ``<folder>-solo``
- primary + one other roster artist (anywhere in featured) -> ``<a>-<b>-duo``
  (folders sorted alphabetically)
- three roster artists -> ``<a>-<b>-<c>-trio``
- fetched artist appears only in featured (someone else's song)
  -> ``<folder>-featured``
- fetched artist not resolvable on the song -> ``other-collab``

Resumable: ``_fetch_status_g3.json`` tracks per-artist state + completed
Genius song ids; ``--resume`` skips done artists and done songs.

Disambiguation gate: after ``search_artist`` resolves, the resolved name must
match the roster variants (substring, either direction). A mismatch marks the
artist ``resolve_mismatch`` and skips its fetch — a wrong-artist ingest is
worse than no ingest. ``--dry-run`` lists the top ``search_artists`` hits per
roster artist without fetching songs.

Usage:
    python extract_roster.py [--roster roster_g3.json] [--outdir <lyrics>/genius]
        [--delay 1.5] [--artist NAME ...] [--resume] [--limit N] [--offset N]
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None  # type: ignore

from extract_artists import (
    slugify,
    load_token,
    save_song,
    get_primary_artist_name,
    extract_featured_artists,
)


# ---------------------------------------------------------------------------
# Roster + categorization
# ---------------------------------------------------------------------------

def load_roster(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["artists"]


def normalize_name(name: str) -> str:
    return name.lower().strip()


def _matches(name: str, variants: list[str]) -> bool:
    """Whole-word variant match — 'fox' hits 'Samantha Fox' but not 'Fleet Foxes'."""
    n = normalize_name(name)
    return any(re.search(rf"(?<!\w){re.escape(v)}(?!\w)", n) for v in variants)


def roster_artists_in(names: list[str], roster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Roster artists whose variants match any name in ``names``."""
    hits: list[dict[str, Any]] = []
    for cfg in roster:
        if any(_matches(n, cfg["variants"]) for n in names):
            hits.append(cfg)
    return hits


def categorize_song(
    primary_artist: str,
    featured_artists: list[str],
    roster: list[dict[str, Any]],
    current_cfg: dict[str, Any],
) -> str:
    """Category folder for a song, roster-wide."""
    primaries = roster_artists_in([primary_artist], roster)
    feats = roster_artists_in(featured_artists, roster)
    all_hits = primaries + [c for c in feats if c not in primaries]

    if not primaries:
        # Not a roster primary — this song reached us via the fetched artist's
        # page, so the current artist is a feature (or the page is off).
        if current_cfg in feats:
            return f"{current_cfg['folder']}-featured"
        return "other-collab"
    if len(all_hits) == 1:
        return f"{primaries[0]['folder']}-solo"
    if len(all_hits) <= 3:
        suffix = "duo" if len(all_hits) == 2 else "trio"
        return "-".join(sorted(c["folder"] for c in all_hits)) + f"-{suffix}"
    return "other-collab"


# ---------------------------------------------------------------------------
# Status / resume
# ---------------------------------------------------------------------------

def load_status(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"artists": {}}


def save_status(path: Path, status: dict[str, Any]) -> None:
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")


def _touch(entry: dict[str, Any]) -> None:
    entry["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Resolution + fetch
# ---------------------------------------------------------------------------

def resolved_name_matches(resolved: str, cfg: dict[str, Any]) -> bool:
    """True if the Genius-resolved artist name fits the roster variants.

    Word-boundary match so generic names stay safe: 'Fox' matches 'Fox',
    'Fox & Surreal', 'Samantha Fox' — but not 'Fleet Foxes' or 'Foxes';
    'Žera' (different artist) does not satisfy Zera's variants.
    """
    r = normalize_name(resolved)
    if any(re.search(rf"(?<!\w){re.escape(v)}(?!\w)", r)
           or re.search(rf"(?<!\w){re.escape(r)}(?!\w)", v)
           for v in cfg["variants"]):
        return True
    return r == normalize_name(cfg["name"])


def dry_run_resolve(genius: Any, roster: list[dict[str, Any]]) -> None:
    """List top Genius artist hits per roster row without fetching songs."""
    for cfg in roster:
        try:
            res = genius.search_artists(cfg["name"], per_page=5)
        except Exception as exc:
            print(f"  {cfg['name']:25s} SEARCH ERROR: {exc}")
            continue
        hits = []
        for section in res.get("sections", []):
            hits.extend(section.get("hits", []))
        top = hits[:5]
        best = top[0]["result"] if top else None
        flag = ""
        if best and resolved_name_matches(best.get("name", ""), cfg):
            flag = "OK"
        elif best:
            flag = "CHECK"
        else:
            flag = "NO HITS"
        print(f"  {cfg['name']:25s} [{flag}]")
        for h in top:
            r = h["result"]
            match = "<-- variants match" if resolved_name_matches(r.get("name", ""), cfg) else ""
            print(f"      id={r.get('id')}  {r.get('name')}  {match}")


def fetch_artist_songs_resolving(
    genius: Any, cfg: dict[str, Any]
) -> tuple[list, dict[str, Any]]:
    """search_artist + variant check. Returns (songs, info) or raises."""
    artist = genius.search_artist(
        cfg["name"],
        max_songs=1000,
        sort="title",
        get_full_info=True,
        include_features=True,
        max_pages=50,
        artist_id=cfg.get("genius_artist_id"),  # pinned ids bypass name search
    )
    if artist is None:
        raise RuntimeError(f"no artist found for '{cfg['name']}'")
    resolved = getattr(artist, "name", "") or ""
    artist_id = getattr(artist, "id", None)
    if not resolved_name_matches(resolved, cfg):
        raise _ResolveMismatch(resolved, artist_id)
    songs = artist.songs if hasattr(artist, "songs") else []
    return songs, {"resolved_name": resolved, "genius_artist_id": artist_id}


class _ResolveMismatch(RuntimeError):
    def __init__(self, resolved: str, artist_id):
        super().__init__(f"resolved '{resolved}' (id={artist_id}) does not match roster variants")
        self.resolved = resolved
        self.artist_id = artist_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roster-driven Genius lyrics extraction (P3 batch)"
    )
    _data_dir = os.environ.get(
        "TOOLSHOP_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "toolshop")
    )
    _default_outdir = Path(_data_dir) / "lyrics" / "genius"
    parser.add_argument("--roster", type=Path,
                        default=Path(__file__).resolve().parent / "roster_g3.json",
                        help="Roster JSON (default: roster_g3.json beside this script)")
    parser.add_argument("--outdir", type=Path, default=_default_outdir,
                        help=f"Output directory (default: {_default_outdir})")
    parser.add_argument("--status-file", type=Path, default=None,
                        help="Resume status JSON (default: <outdir>/_fetch_status_g3.json)")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between requests in seconds (default: 1.5)")
    parser.add_argument("--artist", action="append", default=None,
                        help="Limit to roster artist(s) by name or folder (repeatable)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip artists marked done and per-song ids already fetched")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max songs per artist (bounded-batch mode)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N songs per artist (bounded-batch mode)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve artists only (top search_artists hits), no song fetch")
    args = parser.parse_args()

    if lyricsgenius is None:
        print("lyricsgenius is required. Install with: pip install lyricsgenius")
        sys.exit(1)

    roster = load_roster(args.roster)
    fetch_roster = roster
    if args.artist:
        wanted = {a.lower() for a in args.artist}
        fetch_roster = [c for c in roster
                        if c["name"].lower() in wanted or c["folder"].lower() in wanted]
        if not fetch_roster:
            print(f"ERROR: no roster artists matched {args.artist}")
            sys.exit(1)

    token = load_token()
    genius = lyricsgenius.Genius(
        token,
        sleep_time=args.delay,
        skip_non_songs=True,
        excluded_terms=["(Remix)", "(Instrumental)"],
        remove_section_headers=False,
        timeout=30,
    )

    if args.dry_run:
        print("DRY RUN — resolving artists only")
        dry_run_resolve(genius, fetch_roster)
        return

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    status_path = args.status_file or (outdir / "_fetch_status_g3.json")
    status = load_status(status_path)
    ast = status.setdefault("artists", {})

    run_index: list[dict[str, Any]] = []
    stats: dict[str, int] = {}

    for cfg in fetch_roster:
        folder = cfg["folder"]
        entry = ast.setdefault(folder, {
            "status": "pending", "resolved_name": None, "genius_artist_id": None,
            "total_songs": 0, "done_song_ids": [],
        })

        if args.resume and entry.get("status") == "done":
            print(f"\n=== {cfg['name']} — already done, skipping (resume) ===")
            continue

        print(f"\n{'='*60}\nFetching: {cfg['name']} (cohort={cfg['cohort']})\n{'='*60}")
        try:
            songs, info = fetch_artist_songs_resolving(genius, cfg)
        except _ResolveMismatch as exc:
            entry["status"] = "resolve_mismatch"
            entry["resolved_name"] = exc.resolved
            entry["genius_artist_id"] = exc.artist_id
            _touch(entry)
            save_status(status_path, status)
            print(f"  RESOLVE MISMATCH: {exc} — skipped")
            continue
        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
            _touch(entry)
            save_status(status_path, status)
            print(f"  ERROR fetching {cfg['name']}: {exc}")
            continue

        entry.update(info)
        entry["status"] = "in_progress"
        entry["total_songs"] = len(songs)
        _touch(entry)
        save_status(status_path, status)
        print(f"  Resolved: {info['resolved_name']} (id={info['genius_artist_id']}), {len(songs)} songs")

        done_ids = set(entry.get("done_song_ids", [])) if args.resume else set()
        seen_ids = set(done_ids)

        window = songs[args.offset:]
        if args.limit is not None:
            window = window[:args.limit]

        for i, song in enumerate(window, 1):
            song_id = getattr(song, "id", None)
            title = getattr(song, "title", "Unknown")
            primary_artist = get_primary_artist_name(song)
            featured = extract_featured_artists(song)

            if song_id is not None and song_id in seen_ids:
                print(f"  [{i}/{len(window)}] SKIP (done/dup): {title}")
                continue

            category = categorize_song(primary_artist, featured, roster, cfg)

            try:
                se = save_song(song, category, outdir, seen_ids)
                if se is None:
                    continue
                run_index.append(se)
                if song_id is not None:
                    done_ids.add(song_id)
                stats[category] = stats.get(category, 0) + (1 if se["status"] == "completed" else 0)
                tag = "OK" if se["status"] == "completed" else "NO LYRICS"
                print(f"  [{i}/{len(window)}] {tag} ({category}): {title}")
            except Exception as exc:
                print(f"  [{i}/{len(window)}] FAIL: {title} — {exc}")

            entry["done_song_ids"] = sorted(done_ids)
            if i % 25 == 0:
                _touch(entry)
                save_status(status_path, status)

        entry["done_song_ids"] = sorted(done_ids)
        entry["status"] = "done" if args.limit is None else "in_progress"
        _touch(entry)
        save_status(status_path, status)

    # Run summary (underscored — not scanned by build_unified_index)
    summary_path = outdir / "_summary_g3.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# G3 Roster Extraction Summary\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| Artist | Status | Resolved | Songs |\n|---|---|---|---|\n")
        for cfg in fetch_roster:
            e = ast.get(cfg["folder"], {})
            f.write(f"| {cfg['name']} | {e.get('status','?')} | "
                    f"{e.get('resolved_name','?')} (id={e.get('genius_artist_id')}) | "
                    f"{e.get('total_songs','?')} |\n")
        f.write("\n## Categories this run\n\n")
        for cat, n in sorted(stats.items()):
            f.write(f"- {cat}: {n}\n")
    print(f"\nSummary saved: {summary_path}")


if __name__ == "__main__":
    main()
