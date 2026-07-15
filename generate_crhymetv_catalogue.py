r"""Generate catalogue artefacts from a CrhymeTV reverse-engineering batch.

Reads results\crhymetv_re\batch_status.json and produces:
  - catalogue.csv
  - catalogue.md
  - suno_prompts.md

Usage:
    python generate_crhymetv_catalogue.py [--results-dir DIR]
"""
import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_filename(name: str) -> Dict[str, Optional[str]]:
    """Parse a CrhymeTV filename like 'YYYY-MM-DD - Artist - Title [id].mp3'."""
    result = {"year": None, "date": None, "artist": None, "title": None, "id": None}

    # Strip extension and trailing [id]
    id_match = re.search(r"\[([^\]]+)\]\.mp3$", name)
    if id_match:
        result["id"] = id_match.group(1)
        base = name[: id_match.start()].strip()
    else:
        base = Path(name).stem

    # Split into date / artist / title by first two ' - ' separators
    parts = base.split(" - ", 2)
    if len(parts) >= 3:
        result["date"] = parts[0].strip()
        result["year"] = parts[0][:4] if parts[0][:4].isdigit() else None
        result["artist"] = parts[1].strip()
        result["title"] = parts[2].strip()
    elif len(parts) == 2:
        result["date"] = parts[0].strip()
        result["year"] = parts[0][:4] if parts[0][:4].isdigit() else None
        result["artist"] = parts[1].strip()
        result["title"] = ""
    else:
        result["title"] = base.strip()

    return result


def safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_list(items: List[Any], key: str, top_n: int = 5) -> str:
    if not items:
        return ""
    vals = [i.get(key) if isinstance(i, dict) else i for i in items[:top_n]]
    return "; ".join(str(v) for v in vals if v is not None)


def build_suno_prompt(meta: Dict[str, Any]) -> str:
    bpm = meta.get("bpm", "")
    key = meta.get("key", "")
    mode = meta.get("mode", "")
    artist = meta.get("artist", "")
    title = meta.get("title", "")
    instruments = meta.get("top_instruments", "")
    effects = meta.get("top_effects", "")
    parts = [f"{bpm} bpm", f"{key} {mode}", "German rap / hip-hop"]
    if artist:
        parts.append(f"in the style of {artist}")
    if title:
        parts.append(f"title: {title}")
    if instruments:
        parts.append(f"instruments: {instruments}")
    if effects:
        parts.append(f"effects: {effects}")
    return ", ".join(parts)


def generate_csv(rows: List[Dict[str, Any]], csv_path: Path) -> None:
    fieldnames = [
        "slug",
        "source_file",
        "date",
        "year",
        "artist",
        "title",
        "id",
        "bpm",
        "key",
        "mode",
        "duration_seconds",
        "backend",
        "top_chords",
        "top_instruments",
        "top_effects",
        "suno_prompt",
        "recipe_path",
        "status",
        "error",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def generate_markdown(
    rows: List[Dict[str, Any]],
    md_path: Path,
    skipped_rows: Optional[List[Dict[str, Any]]] = None,
) -> None:
    skipped_rows = skipped_rows or []
    total = len(rows) + len(skipped_rows)
    lines = [
        "# CrhymeTV Reverse-Engineering Catalogue",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Tracks: {total}",
        f"Completed: {len(rows)}",
        f"Skipped (long): {len(skipped_rows)}",
        "",
        "## Stats",
    ]

    # BPM range
    bpms = [r.get("bpm") for r in rows if r.get("bpm")]
    if bpms:
        lines.append(f"- **BPM range:** {min(bpms):.2f} - {max(bpms):.2f}")
    # Duration range
    durations = [r.get("duration_seconds") for r in rows if r.get("duration_seconds")]
    if durations:
        lines.append(f"- **Duration range:** {min(durations):.1f}s - {max(durations):.1f}s")
    # Year distribution
    years: Dict[str, int] = {}
    for r in rows:
        y = r.get("year") or "Unknown"
        years[y] = years.get(y, 0) + 1
    if years:
        lines.append("- **Year distribution:**")
        for y in sorted(years.keys()):
            lines.append(f"  - {y}: {years[y]}")
    # Top artists
    artists: Dict[str, int] = {}
    for r in rows:
        a = r.get("artist") or "Unknown"
        artists[a] = artists.get(a, 0) + 1
    top_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_artists:
        lines.append("- **Top artists:**")
        for a, c in top_artists:
            lines.append(f"  - {a}: {c}")

    lines += ["", "## Tracks"]
    for r in rows:
        lines.append(f"### {r.get('artist', 'Unknown')} — {r.get('title', 'Unknown')}")
        lines.append(f"- **Date:** {r.get('date', '')}")
        lines.append(f"- **BPM:** {r.get('bpm', '')}")
        lines.append(f"- **Key:** {r.get('key', '')} {r.get('mode', '')}")
        lines.append(f"- **Duration:** {r.get('duration_seconds', '')}s")
        lines.append(f"- **Chords:** {r.get('top_chords', '')}")
        lines.append(f"- **Instruments:** {r.get('top_instruments', '')}")
        lines.append(f"- **Effects:** {r.get('top_effects', '')}")
        lines.append(f"- **Suno prompt:** {r.get('suno_prompt', '')}")
        lines.append(f"- **Recipe:** {r.get('recipe_path', '')}")
        lines.append("")

    if skipped_rows:
        lines += ["", "## Skipped (long files)", ""]
        for r in skipped_rows:
            lines.append(f"- `{r.get('source_file', '')}` — {r.get('duration_seconds', '')}s")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def generate_suno_prompts(rows: List[Dict[str, Any]], md_path: Path) -> None:
    lines = [
        "# CrhymeTV Suno Prompt Seeds",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Tracks: {len(rows)}",
        "",
        "Copy-paste the prompt seeds below into Suno. They are ordered by year.",
        "",
    ]
    for r in rows:
        lines.append(f"## {r.get('artist', 'Unknown')} — {r.get('title', 'Unknown')} ({r.get('year', '')})")
        lines.append(f"{r.get('suno_prompt', '')}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(r"d:\Projects\Music-AI-Toolshop\results\crhymetv_re"),
    )
    args = parser.parse_args()
    results_dir = args.results_dir.resolve()

    status_path = results_dir / "batch_status.json"
    if not status_path.exists():
        print(f"ERROR: batch_status.json not found: {status_path}")
        return 1

    status = json.loads(status_path.read_text(encoding="utf-8"))
    tracks = status.get("tracks", [])

    rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    for t in tracks:
        source = Path(t.get("source", ""))
        meta = parse_filename(source.name)
        if t.get("status") == "skipped_long":
            skipped_rows.append({
                "source_file": str(source),
                "date": meta.get("date", ""),
                "artist": meta.get("artist", ""),
                "title": meta.get("title", ""),
                "duration_seconds": t.get("duration_seconds", ""),
            })
            continue
        if t.get("status") != "completed":
            continue
        analysis = safe_read_json(Path(t.get("analysis_json"))) or {}
        voice = safe_read_json(Path(t.get("voice_json"))) or {}

        row = {
            "slug": t.get("slug", ""),
            "source_file": str(source),
            "date": meta.get("date", ""),
            "year": meta.get("year", ""),
            "artist": meta.get("artist", ""),
            "title": meta.get("title", ""),
            "id": meta.get("id", ""),
            "bpm": analysis.get("bpm", ""),
            "key": analysis.get("key", ""),
            "mode": analysis.get("mode", ""),
            "duration_seconds": analysis.get("duration_seconds", ""),
            "backend": analysis.get("analysis_backend", ""),
            "top_chords": summarize_list(analysis.get("chord_progression", []), "name", 6),
            "top_instruments": summarize_list(analysis.get("instruments", []), "label", 5),
            "top_effects": "; ".join(
                e.get("effect", "")
                for e in voice.get("effects_detected", [])
                if e.get("confidence", 0) > 0.3
            ),
            "suno_prompt": "",
            "recipe_path": t.get("recipe_md", ""),
            "status": t.get("status", ""),
            "error": t.get("error", ""),
        }
        row["suno_prompt"] = build_suno_prompt(row)
        rows.append(row)

    # Sort by date, then artist
    rows.sort(key=lambda r: (r.get("date") or "", r.get("artist") or ""))
    skipped_rows.sort(key=lambda r: (r.get("date") or "", r.get("artist") or ""))

    generate_csv(rows, results_dir / "catalogue.csv")
    generate_markdown(rows, results_dir / "catalogue.md", skipped_rows=skipped_rows)
    generate_suno_prompts(rows, results_dir / "suno_prompts.md")

    print(f"Generated catalogue for {len(rows)} completed tracks ({len(skipped_rows)} skipped long):")
    print(f"  - {results_dir / 'catalogue.csv'}")
    print(f"  - {results_dir / 'catalogue.md'}")
    print(f"  - {results_dir / 'suno_prompts.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
