"""Release-tree export from lyrics.db (SPEC §8.2).

Reads ``data/toolshop/lyrics/lyrics.db`` via sqlite3 directly — **never
``import toolshop``** (the eager package ``__init__`` costs ~70 s cold,
megaplan F-B1). ``ensure_license_columns`` is vendored below (mirror of
``toolshop/lyricsdb.py``) so a v1-shaped DB self-heals on open, matching
``corpus_inventory.py``.

Usage:
    python export_release.py --release-cleared --out <dir> [--corpus TAG]
                             [--include-conditional] [--db PATH]
    python export_release.py --include-study --out <dir> [--corpus TAG] [--db PATH]

Emission contract (BINDING, SPEC §8.2 + wave-5b task):

- ``--release-cleared`` emits ONLY ``release_ok='yes'`` rows into
  ``<out>/<corpus>/<category>/<artist-slug>-<title-slug>.json`` (+ ``.txt``
  clean lyrics) — the same song-JSON v2 shape as the corpus dirs, with the
  DB's audited license columns stamped over the file's license block so
  recorded user decisions (``modified_note`` flips) propagate.
- ``release_ok='conditional'`` is NEVER emitted by ``--release-cleared``
  alone. ``--include-conditional`` emits only conditional items carrying a
  ``modified_note`` recording the user's decision; the rest are reported in
  the manifest's ``pending_decisions`` list.
- ``release_ok='no'``/``'uncleared'`` rows (genius-pro, lrclib, …) are never
  even selected in release mode — and a pre-write audit aborts the whole
  export (exit 3) if any planned emit row is not release-safe. A
  ``--release-cleared`` run that would emit a non-``yes`` row is a BLOCKER.
- No flag at all REFUSES (exit 2). ``--include-study`` is the explicit
  opt-in escape hatch: it emits every matching row (including study-only
  corpora) into a *study* tree — the manifest is stamped ``"mode": "study"``
  and every item carries its ``release_ok`` so the tree stays auditable.
- ``CREDITS.md`` — one computed TASL credit line per emitted item
  (``tasl_credit``), grouped by corpus then license.
- ``RELEASE_MANIFEST.json`` — counts per corpus, license histogram, per-item
  rows (``song_id``/``title``/``creator``/``license_ref``/``license_url``/
  ``source_url``/``release_ok``/emit path), ``pending_decisions``, ``gaps``
  (emitted items missing TASL fields), and ``skipped`` counts.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Folder-local imports only (sources/ package — never toolshop).
from sources._common import song_base_name, tasl_credit  # noqa: E402
from sources import registry as source_registry  # noqa: E402

# ── Vendored migrate-on-open (SPEC §4.2) ──────────────────────────────
# Mirror of toolshop.lyricsdb.ensure_license_columns — folder scripts must not
# `import toolshop` (eager package __init__ ≈70 s, megaplan F-B1).
# Keep in sync with toolshop/lyricsdb.py::_LICENSE_COLUMNS.
_LICENSE_COLUMNS = {
    "license_tier": "TEXT NOT NULL DEFAULT 'study-only'",
    "license_ref": "TEXT",
    "license_url": "TEXT",
    "release_ok": "TEXT NOT NULL DEFAULT 'no'",
    "creator": "TEXT",
    "creator_url": "TEXT",
    "source_url": "TEXT",
    "copyright_notice": "TEXT",
    "modified_note": "TEXT",
    "foreign_identifier": "TEXT",
    "script": "TEXT",
    "derived_from": "TEXT",
}


def _ensure_license_columns(conn: sqlite3.Connection) -> int:
    """Add §4.1 license columns to a v1-shaped DB + backfill genius rows.
    Returns rows backfilled (0 on a fresh or migrated DB)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    if not existing:
        return 0
    for col, clause in _LICENSE_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {col} {clause}")
    cur = conn.execute(
        """UPDATE songs SET license_tier='study-only',
                            license_ref='proprietary',
                            release_ok='no'
           WHERE corpus='genius-pro' AND license_ref IS NULL"""
    )
    n = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return n


# ── Selection + emission ──────────────────────────────────────────────

_SONG_COLS = (
    "id", "corpus", "category", "title", "primary_artist", "url",
    "license_tier", "license_ref", "license_url", "release_ok",
    "creator", "creator_url", "source_url", "copyright_notice",
    "modified_note", "foreign_identifier", "script", "derived_from",
    "source_path",
)

#: DB column -> song-JSON v2 key (``license_ref`` maps back to ``license``).
_DB_TO_JSON = {
    "license_tier": "license_tier",
    "license_ref": "license",
    "license_url": "license_url",
    "release_ok": "release_ok",
    "creator": "creator",
    "creator_url": "creator_url",
    "source_url": "source_url",
    "copyright_notice": "copyright_notice",
    "modified_note": "modified_note",
    "foreign_identifier": "foreign_identifier",
    "script": "script",
    "derived_from": "derived_from",
}

#: PD-dedication mark URL (ccMixter lic=pd lane etc.) — informational here;
#: the mapping itself lives in sources/ccmixter.py + _common.LICENSE_URL_MAP.
PD_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"


def _corpus_dirs() -> Dict[str, str]:
    """corpus_tag -> on-disk corpus dir from registry.json (genius-pro ->
    'genius' exception honored)."""
    out: Dict[str, str] = {}
    try:
        for row in source_registry.list_sources():
            tag = row.get("corpus_tag")
            cdir = source_registry.corpus_dir(row)
            if tag and cdir:
                out[tag] = cdir
    except Exception:
        pass
    return out


def _resolve_source_json(
    row: sqlite3.Row,
    lyrics_root: Path,
    corpus_dirs: Dict[str, str],
) -> Optional[Path]:
    """Locate the on-disk song JSON for a songs row: ``source_path`` first,
    then ``<lyrics_root>/<corpus_dir>/<category>/<basename>`` fallback."""
    src = row["source_path"]
    if src:
        p = Path(src)
        if p.is_file():
            return p
        # relocate: same basename under the corpus dir
        cdir = corpus_dirs.get(row["corpus"])
        if cdir:
            alt = lyrics_root / cdir / (row["category"] or "") / p.name
            if alt.is_file():
                return alt
    return None


def _row_tasl_dict(row: sqlite3.Row, song: Dict[str, Any]) -> Dict[str, Any]:
    """Merged TASL view — DB license columns are authoritative (audited
    state), song JSON fills anything the DB left NULL."""
    d = dict(song)
    d.setdefault("title", row["title"])
    for db_col, json_key in _DB_TO_JSON.items():
        v = row[db_col]
        if v is not None:
            d[json_key] = v
    return d


def _release_allowed(row: sqlite3.Row, include_conditional: bool) -> bool:
    """Hard release gate (BLOCKER semantics): a row is emittable by
    ``--release-cleared`` iff ``release_ok='yes'``, or — only behind
    ``--include-conditional`` — ``'conditional'`` with a recorded
    ``modified_note`` decision."""
    ok = row["release_ok"]
    if ok == "yes":
        return True
    if (
        ok == "conditional"
        and include_conditional
        and (row["modified_note"] or "").strip()
    ):
        return True
    return False


def _build_emit_plan(
    conn: sqlite3.Connection,
    *,
    corpus: Optional[str],
    mode: str,
    include_conditional: bool,
    lyrics_root: Path,
    corpus_dirs: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute (emit_plan, pending_decisions, skipped_missing).

    Release mode selects only ``yes``/``conditional`` rows — ``no`` and
    uncleared rows are never even candidates. Study mode selects everything.
    Plan entries carry the row, merged song dict, and relative emit path.
    """
    cols = ", ".join(_SONG_COLS)
    if mode == "release":
        where = "release_ok IN ('yes','conditional')"
    else:  # study
        where = "1=1"
    params: List[Any] = []
    if corpus:
        where += " AND corpus=?"
        params.append(corpus)
    rows = conn.execute(
        f"SELECT {cols} FROM songs WHERE {where} "
        f"ORDER BY corpus, category, primary_artist, title",
        params,
    ).fetchall()

    emit_plan: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    used_names: set = set()

    for row in rows:
        ok = row["release_ok"]
        has_note = bool((row["modified_note"] or "").strip())

        if mode == "release" and not _release_allowed(row, include_conditional):
            if ok == "conditional":
                pending.append(_manifest_row(row) | {
                    "reason": (
                        "conditional without modified_note decision"
                        if not has_note
                        else "conditional (pass --include-conditional to emit "
                             "modified_note-decided items)"
                    ),
                    "emitted": False,
                })
            continue

        src = _resolve_source_json(row, lyrics_root, corpus_dirs)
        if src is None:
            missing.append(_manifest_row(row) | {"reason": "source json missing"})
            continue
        try:
            song = json.loads(src.read_text(encoding="utf-8"))
        except Exception:
            missing.append(_manifest_row(row) | {"reason": "source json unreadable"})
            continue

        merged = _row_tasl_dict(row, song)
        category = row["category"] or song.get("category") or "uncategorized"
        base = song_base_name({
            "primary_artist": row["primary_artist"] or song.get("primary_artist"),
            "artist": song.get("artist"),
            "title": row["title"] or song.get("title"),
        })
        rel_dir = f"{row['corpus']}/{category}"
        name = base
        if f"{rel_dir}/{name}" in used_names:
            name = f"{base}-{row['id']}"
        used_names.add(f"{rel_dir}/{name}")

        emit_plan.append({
            "row": row,
            "song": merged,
            "rel_json": f"{rel_dir}/{name}.json",
            "rel_txt": f"{rel_dir}/{name}.txt",
            "txt": merged.get("clean_lyrics"),
            "src": src,
        })
        if mode == "study" and ok == "conditional" and not has_note:
            pending.append(_manifest_row(row) | {
                "reason": "conditional without modified_note decision "
                          "(emitted in study tree — release decision still pending)",
                "emitted": True,
            })

    return emit_plan, pending, missing


def _manifest_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "song_id": row["id"],
        "corpus": row["corpus"],
        "category": row["category"],
        "title": row["title"],
        "creator": row["creator"],
        "license_ref": row["license_ref"],
        "license_url": row["license_url"],
        "source_url": row["source_url"],
        "release_ok": row["release_ok"],
    }


def _audit_emit_plan(plan: List[Dict[str, Any]], include_conditional: bool) -> List[str]:
    """Pre-write audit — the BLOCKER check. Returns violation strings; an
    empty list means every planned emit row is release-safe."""
    bad: List[str] = []
    for entry in plan:
        row = entry["row"]
        if not _release_allowed(row, include_conditional):
            bad.append(
                f"song_id={row['id']} corpus={row['corpus']} "
                f"title={row['title']!r} release_ok={row['release_ok']!r}"
            )
    return bad


def _write_credits(
    outdir: Path,
    plan: List[Dict[str, Any]],
    *,
    mode: str,
    generated_at: str,
) -> None:
    """One TASL line per emitted item, grouped by corpus then license."""
    lines = [
        "# CREDITS — release-tree export",
        "",
        f"Generated: {generated_at} by Genious_lyrics_extractor/export_release.py",
    ]
    if mode == "study":
        lines += [
            "",
            "**MODE: study** — this tree includes non-release-cleared items "
            "(release_ok != 'yes'). It is NOT a release tree.",
        ]
    lines.append("")
    by_corpus: Dict[str, List[Dict[str, Any]]] = {}
    for e in plan:
        by_corpus.setdefault(e["row"]["corpus"], []).append(e)
    for corpus in sorted(by_corpus):
        lines.append(f"## {corpus}")
        lines.append("")
        by_lic: Dict[str, List[str]] = {}
        for e in by_corpus[corpus]:
            lic = e["row"]["license_ref"] or "unknown"
            by_lic.setdefault(lic, []).append(tasl_credit(e["song"]))
        for lic in sorted(by_lic):
            lines.append(f"### {lic}")
            for credit in sorted(by_lic[lic]):
                lines.append(f"- {credit}")
            lines.append("")
    (outdir / "CREDITS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(
    outdir: Path,
    *,
    mode: str,
    db_path: Path,
    corpus: Optional[str],
    include_conditional: bool,
    generated_at: str,
    plan: List[Dict[str, Any]],
    pending: List[Dict[str, Any]],
    missing: List[Dict[str, Any]],
    release_histogram: List[Tuple[str, int]],
) -> Path:
    counts_per_corpus: Dict[str, int] = {}
    license_hist: Dict[str, int] = {}
    items: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    for e in plan:
        row = e["row"]
        counts_per_corpus[row["corpus"]] = counts_per_corpus.get(row["corpus"], 0) + 1
        lic = row["license_ref"] or "unknown"
        license_hist[lic] = license_hist.get(lic, 0) + 1
        m = _manifest_row(row)
        m["path"] = e["rel_json"]
        items.append(m)
        gap = [f for f in ("creator", "source_url", "license_ref") if not row[f]]
        if gap:
            gaps.append(m | {"missing": gap})

    skipped_counts = {ok: n for ok, n in release_histogram}

    manifest = {
        "generated_at": generated_at,
        "tool": "Genious_lyrics_extractor/export_release.py",
        "db_path": str(db_path),
        "mode": mode,
        "corpus_filter": corpus,
        "include_conditional": include_conditional,
        "total_emitted": len(plan),
        "counts_per_corpus": counts_per_corpus,
        "license_histogram": license_hist,
        "items": items,
        "pending_decisions": pending,
        "gaps": gaps,
        "skipped_missing_source": missing,
        "release_ok_histogram_selected_scope": skipped_counts,
    }
    path = outdir / "RELEASE_MANIFEST.json"
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Export a release (or explicit study) tree from lyrics.db",
    )
    gate = ap.add_mutually_exclusive_group()
    gate.add_argument(
        "--release-cleared", action="store_true",
        help="emit ONLY release_ok='yes' rows (+'conditional' items carrying a "
             "modified_note decision, behind --include-conditional)",
    )
    gate.add_argument(
        "--include-study", action="store_true",
        help="explicit opt-in: emit ALL matching rows incl. study-only corpora "
             "into a study tree (manifest mode='study'; NOT a release)",
    )
    ap.add_argument(
        "--include-conditional", action="store_true",
        help="with --release-cleared: also emit 'conditional' rows that carry "
             "a modified_note recording the user's decision",
    )
    ap.add_argument("--corpus", default=None, help="corpus tag filter")
    ap.add_argument("--db", type=Path, default=None, help="lyrics.db path")
    ap.add_argument(
        "--out", "--outdir", dest="outdir", type=Path, required=True,
        help="output directory for the release tree",
    )
    args = ap.parse_args(argv)

    if not args.release_cleared and not args.include_study:
        ap.error(
            "refusing to export: pass --release-cleared for a release tree "
            "(release_ok='yes' only) or --include-study for an explicit "
            "study tree — no flag is a refusal by design (SPEC §8.2)"
        )
    if args.include_conditional and not args.release_cleared:
        ap.error("--include-conditional only applies to --release-cleared runs")

    mode = "release" if args.release_cleared else "study"
    db_path = args.db or (
        _HERE.parent / "data" / "toolshop" / "lyrics" / "lyrics.db"
    )
    if not db_path.is_file():
        print(f"error: lyrics.db not found at {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _ensure_license_columns(conn)  # migrate-on-open for v1-shaped DBs

    # --corpus validation: a tag absent from the DB is an error, never a
    # silent empty export.
    known = {r[0] for r in conn.execute("SELECT DISTINCT corpus FROM songs")}
    if args.corpus and args.corpus not in known:
        print(
            f"error: unknown corpus {args.corpus!r} — corpora in DB: "
            f"{sorted(known)}",
            file=sys.stderr,
        )
        conn.close()
        return 2

    lyrics_root = db_path.parent
    corpus_dirs = _corpus_dirs()

    plan, pending, missing = _build_emit_plan(
        conn,
        corpus=args.corpus,
        mode=mode,
        include_conditional=args.include_conditional,
        lyrics_root=lyrics_root,
        corpus_dirs=corpus_dirs,
    )
    hist = conn.execute(
        "SELECT release_ok, COUNT(*) FROM songs "
        + ("WHERE corpus=?" if args.corpus else "")
        + " GROUP BY release_ok",
        ([args.corpus] if args.corpus else []),
    ).fetchall()

    # ── BLOCKER audit ─────────────────────────────────────────────────
    # A --release-cleared export that would emit any release_ok != 'yes'
    # (or un-flagged/un-decided conditional) row must refuse and write
    # NOTHING. This is belt-and-suspenders over the SQL gate — the check
    # runs on the final emit plan itself so no future code path can leak a
    # genius-pro / lrclib / uncleared row into a release tree.
    if mode == "release":
        violations = _audit_emit_plan(plan, args.include_conditional)
        if violations:
            print(
                "BLOCKER: release export aborted — emit plan contained "
                "non-release-safe rows (refusing to write anything):",
                file=sys.stderr,
            )
            for v in violations:
                print(f"  {v}", file=sys.stderr)
            conn.close()
            return 3

    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    written = 0
    for e in plan:
        jpath = outdir / e["rel_json"]
        jpath.parent.mkdir(parents=True, exist_ok=True)
        jpath.write_text(
            json.dumps(e["song"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        txt = e["txt"]
        if txt is None:
            sib = e["src"].with_suffix(".txt")
            txt = sib.read_text(encoding="utf-8") if sib.is_file() else None
        if txt is not None:
            (outdir / e["rel_txt"]).write_text(txt, encoding="utf-8")
        written += 1

    _write_credits(outdir, plan, mode=mode, generated_at=generated_at)
    manifest_path = _write_manifest(
        outdir,
        mode=mode,
        db_path=db_path,
        corpus=args.corpus,
        include_conditional=args.include_conditional,
        generated_at=generated_at,
        plan=plan,
        pending=pending,
        missing=missing,
        release_histogram=[(r[0], r[1]) for r in hist],
    )
    conn.close()

    per_corpus = {}
    for e in plan:
        c = e["row"]["corpus"]
        per_corpus[c] = per_corpus.get(c, 0) + 1
    print(f"mode: {mode}")
    print(f"emitted: {written} song JSON(s) -> {outdir}")
    for c, n in sorted(per_corpus.items()):
        print(f"  {c}: {n}")
    print(f"pending_decisions: {len(pending)}")
    print(f"skipped (missing source): {len(missing)}")
    print(f"manifest: {manifest_path}")
    print(f"credits: {outdir / 'CREDITS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
