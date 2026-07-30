#!/usr/bin/env python3
"""Collaboration network analysis on the expanded Genius corpus.

Analyzes featured tracks to map collaboration patterns, compute
network metrics, and identify cross-cohort collaborations.

Output: lyrics_research/reports/collab_network.md
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _REPO_ROOT / "data" / "toolshop" / "lyrics" / "lyrics.db"
_REPORT_PATH = _REPO_ROOT / "lyrics_research" / "reports" / "collab_network.md"


def main() -> None:
    conn = sqlite3.connect(_DB_PATH)

    # Get all songs with their artist info
    rows = conn.execute(
        "SELECT id, title, primary_artist, featured_artists, category, "
        "role, target_artist, genre_cohort "
        "FROM songs WHERE corpus = 'genius-pro'"
    ).fetchall()

    conn.close()

    # Build collaboration edges
    # An edge = (primary_artist, featured_artist) for featured songs
    # Also duo/trio categories = collaborations between the named artists

    edges: List[Tuple[str, str, str]] = []  # (artist_a, artist_b, song_title)
    artist_cohorts: Dict[str, str] = {}
    artist_song_counts: Counter = Counter()

    for row in rows:
        song_id, title, primary_artist, featured_json, category, role, target_artist, cohort = row
        primary_artist = primary_artist or ""
        if cohort:
            artist_cohorts[primary_artist] = cohort

        artist_song_counts[primary_artist] += 1

        # Parse featured_artists
        featured = []
        if featured_json:
            try:
                featured = json.loads(featured_json)
            except (json.JSONDecodeError, TypeError):
                pass

        # Featured songs: edge between target_artist and primary_artist
        if role == "featured":
            # target_artist is the folder artist (e.g. "corona")
            # primary_artist is who actually appears on the song
            if target_artist and primary_artist:
                edges.append((target_artist, primary_artist, title))
                if not artist_cohorts.get(target_artist):
                    # Try to infer from known artists
                    pass
                for fa in featured:
                    if fa and fa != primary_artist:
                        edges.append((primary_artist, fa, title))

        # Duo/trio categories: parse from category name
        if category and ("-duo" in category or "-trio" in category):
            # e.g. "jala-buba-duo" → artists "jala" and "buba"
            parts = category.replace("-duo", "").replace("-trio", "").split("-")
            for i, p in enumerate(parts):
                for q in parts[i+1:]:
                    edges.append((p, q, title))

        # Also track featured artists on solo songs
        if role == "solo" and featured:
            for fa in featured:
                if fa and fa != primary_artist:
                    edges.append((primary_artist, fa, title))

    # Build network
    # Normalize edge directions (undirected)
    normalized_edges: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for a, b, title in edges:
        key = tuple(sorted([a.lower(), b.lower()]))
        normalized_edges[key].append(title)

    # Degree centrality
    artist_connections: Dict[str, Set[str]] = defaultdict(set)
    for (a, b), titles in normalized_edges.items():
        artist_connections[a].add(b)
        artist_connections[b].add(a)

    # Compute network metrics
    n_artists = len(artist_connections)
    n_edges = len(normalized_edges)
    total_songs_with_edges = len(set(t for titles in normalized_edges.values() for t in titles))

    # Degree centrality (normalized)
    max_degree = max(len(v) for v in artist_connections.values()) if artist_connections else 1
    degree_centrality = {
        artist: round(len(connections) / max_degree, 4)
        for artist, connections in sorted(
            artist_connections.items(), key=lambda x: len(x[1]), reverse=True
        )
    }

    # Top collaborator pairs
    top_pairs = sorted(
        ((a, b, len(titles), titles) for (a, b), titles in normalized_edges.items()),
        key=lambda x: x[2],
        reverse=True,
    )

    # Cross-cohort collaborations
    cross_cohort: List[Tuple[str, str, str, int]] = []
    same_cohort: List[Tuple[str, str, str, int]] = []
    for (a, b), titles in normalized_edges.items():
        ca = artist_cohorts.get(a, "")
        cb = artist_cohorts.get(b, "")
        # Try case-insensitive cohort lookup
        if not ca:
            for known, cohort in artist_cohorts.items():
                if known.lower() == a:
                    ca = cohort
                    break
        if not cb:
            for known, cohort in artist_cohorts.items():
                if known.lower() == b:
                    cb = cohort
                    break

        if ca and cb and ca != cb:
            cross_cohort.append((a, b, f"{ca}→{cb}", len(titles)))
        elif ca and cb and ca == cb:
            same_cohort.append((a, b, ca, len(titles)))

    # ── Generate report ───────────────────────────────────────────────
    lines: List[str] = []
    r = lines.append

    r("# Collaboration Network Analysis")
    r("")
    r(f"**Generated:** 2026-07-30  ")
    r(f"**DB:** `{_DB_PATH}`  ")
    r(f"**Corpus:** genius-pro ({len(rows)} total songs)")
    r("")
    r("---")
    r("")

    r("## Network Overview")
    r("")
    r("| Metric | Value |")
    r("|--------|-------|")
    r(f"| Total songs in corpus | {len(rows)} |")
    r(f"| Songs with collaboration edges | {total_songs_with_edges} |")
    r(f"| Unique artists in network | {n_artists} |")
    r(f"| Unique collaboration edges | {n_edges} |")
    r(f"| Network density | {round(n_edges / (n_artists * (n_artists - 1) / 2) * 100, 2) if n_artists > 1 else 0}% |")
    r("")

    r("## Top Collaborators (by degree)")
    r("")
    r("| Artist | Connections | Degree Centrality |")
    r("|--------|-------------|-------------------|")
    for artist, connections in sorted(artist_connections.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        r(f"| {artist} | {len(connections)} | {degree_centrality[artist]} |")
    r("")

    r("## Top Collaborator Pairs (by song count)")
    r("")
    r("| Artist A | Artist B | Songs Together |")
    r("|----------|----------|----------------|")
    for a, b, cnt, titles in top_pairs[:20]:
        r(f"| {a} | {b} | {cnt} |")
    r("")

    r("## Cross-Cohort Collaborations")
    r("")
    r(f"Total cross-cohort edges: **{len(cross_cohort)}**")
    r("")
    if cross_cohort:
        r("| Artist A | Artist B | Cohort Flow | Songs |")
        r("|----------|----------|-------------|-------|")
        for a, b, flow, cnt in sorted(cross_cohort, key=lambda x: x[3], reverse=True):
            r(f"| {a} | {b} | {flow} | {cnt} |")
        r("")
    else:
        r("No cross-cohort collaborations found.")
        r("")

    r("## Same-Cohort Collaborations")
    r("")
    r(f"Total same-cohort edges: **{len(same_cohort)}**")
    r("")
    if same_cohort:
        r("| Artist A | Artist B | Cohort | Songs |")
        r("|----------|----------|--------|-------|")
        for a, b, cohort, cnt in sorted(same_cohort, key=lambda x: x[3], reverse=True)[:20]:
            r(f"| {a} | {b} | {cohort} | {cnt} |")
        r("")

    r("## Artist Song Counts")
    r("")
    r("| Artist | Total Songs |")
    r("|--------|-------------|")
    for artist, cnt in artist_song_counts.most_common(20):
        r(f"| {artist} | {cnt} |")
    r("")

    r("## Summary")
    r("")
    r(f"- The collaboration network contains **{n_artists} artists** and **{n_edges} unique edges**.")
    r(f"- **{len(cross_cohort)}** cross-cohort collaborations (drill↔pop) were identified.")
    r(f"- **{len(same_cohort)}** same-cohort collaborations were identified.")
    r(f"- Most connected artist: **{max(artist_connections, key=lambda x: len(artist_connections[x])) if artist_connections else 'N/A'}**")
    r("")

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to: {_REPORT_PATH}")
    print(f"  Artists: {n_artists}")
    print(f"  Edges: {n_edges}")
    print(f"  Cross-cohort: {len(cross_cohort)}")
    print(f"  Same-cohort: {len(same_cohort)}")


if __name__ == "__main__":
    main()
