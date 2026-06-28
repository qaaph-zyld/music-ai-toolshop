r"""PapaPedro beats — Pilot reverse-engineering pipeline.

Run via PowerShell with:
    & "d:\Projects\Music-AI-Toolshop\run_papapedro_pilot.ps1"

Outputs are saved to:
    d:\Projects\Music-AI-Toolshop\results\papapedro_re
"""
import json
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Force UTF-8 for stdout/stderr so filenames with fullwidth chars do not crash cp1252 console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RESULTS_DIR = Path(r"d:\Projects\Music-AI-Toolshop\results\papapedro_re")
BEATS_DIR = Path(r"d:\Projects\Tools\yt_extractor\downloads\PapaPedro Beats")


def safe_slug(name: str) -> str:
    m = re.search(r"\[([^\]]+)\]\.mp3$", name)
    if m:
        base = name[: m.start()].strip()
        id_part = m.group(1)
    else:
        base = Path(name).stem
        id_part = "unknown"
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", base).strip("_")
    return f"{slug[:50]}_{id_part}"


def select_beats():
    selection = [
        ("trap", "Future x Migos"),
        ("lofi", "somewhere in krakow at midnight"),
        ("rnb", "BITTERSWEET"),
    ]
    selected = []
    for style, keyword in selection:
        candidates = [p for p in BEATS_DIR.glob("*.mp3") if keyword.lower() in p.name.lower()]
        if candidates:
            selected.append((style, candidates[0]))
    if not selected:
        # Fallback: first 3 mp3s
        for p in list(BEATS_DIR.glob("*.mp3"))[:3]:
            selected.append(("unknown", p))
    return selected


def write_recipe(beat_path: Path, style: str, beat_out: Path, analysis: dict, voice: dict, stems: dict):
    recipe_path = beat_out / "recipe.md"
    md = [
        f"# {beat_path.stem}",
        f"- **Style tag:** {style}",
        f"- **Source:** `{beat_path}`",
        "",
        "## Tempo & Key",
        f"- **BPM:** {analysis.get('bpm')}",
        f"- **Key:** {analysis.get('key')} {analysis.get('mode')}",
        f"- **Duration:** {analysis.get('duration_seconds')} s",
        f"- **Backend:** {analysis.get('analysis_backend')}",
    ]
    if analysis.get("tuning_offset"):
        md.append(f"- **Tuning offset:** {analysis.get('tuning_offset')}")
    md += ["", "## Chord Progression"]
    for c in analysis.get("chord_progression", [])[:8]:
        md.append(f"- `{c.get('name')}` @ {c.get('start_time', 0):.2f}s")
    md += ["", "## Detected Instruments"]
    for i in analysis.get("instruments", [])[:8]:
        score = i.get("score")
        score_str = f"{score:.0%}" if isinstance(score, (int, float)) else str(score)
        md.append(f"- {i.get('label')} ({score_str})")
    md += ["", "## Production Effects (full-mix proxy)"]
    for e in voice.get("effects_detected", []):
        if e.get("confidence", 0) > 0.3:
            md.append(f"- **{e.get('effect')}** — {e.get('confidence', 0):.0%}")
            if "reason" in e:
                md.append(f"  - {e.get('reason')}")
    md += ["", "## Stems"]
    stem_paths = stems.get("stems", {}) if isinstance(stems, dict) else {}
    if isinstance(stem_paths, dict):
        for k, v in stem_paths.items():
            md.append(f"- **{k}:** `{v}`")
    else:
        md.append(str(stems))
    md += [
        "",
        "## Recreation Notes",
        "- Start with the BPM and key above.",
        "- Use the chord progression as the harmonic skeleton.",
        "- Match the detected effects chain to approximate the PapaPedro mix.",
        "- Reference the separated stems for layer layout.",
        "",
        "## Suno Prompt Seed",
        f"{style} type beat, {analysis.get('bpm')} bpm, {analysis.get('key')} {analysis.get('mode')}, "
        f"instrumental hip-hop, {style} production",
    ]
    recipe_path.write_text("\n".join(md), encoding="utf-8")
    return str(recipe_path)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    status = {
        "started": datetime.now().isoformat(),
        "beats_dir": str(BEATS_DIR),
        "results_dir": str(RESULTS_DIR),
        "beats": [],
        "errors": [],
    }

    try:
        from toolshop import reverse_engineering_adapter, stem_extractor_adapter, voice_effects_adapter
    except Exception as e:
        status["errors"].append(f"toolshop import failed: {traceback.format_exc()}")
        (RESULTS_DIR / "pilot_status.json").write_text(json.dumps(status, indent=2, default=str))
        print("IMPORT_FAILED", file=sys.stderr)
        return 1

    selected = select_beats()
    print(f"Pilot beats: {len(selected)}")
    for style, p in selected:
        print(f"  [{style}] {p.name}")

    for style, beat_path in selected:
        slug = safe_slug(beat_path.name)
        beat_out = RESULTS_DIR / "per_beat" / slug
        beat_out.mkdir(parents=True, exist_ok=True)
        beat_info = {
            "style": style,
            "source": str(beat_path),
            "slug": slug,
            "out_dir": str(beat_out),
            "analysis_json": None,
            "stems": None,
            "voice_json": None,
            "recipe_md": None,
        }
        try:
            print(f"Analyzing {slug}...")
            analysis = reverse_engineering_adapter.analyze_track(
                beat_path,
                export_json=True,
                output_dir=beat_out,
                effects=True,
                instruments=True,
                chords=True,
                notes=True,
                separation="hpss",
                backend="advanced",
            )
            beat_info["analysis_json"] = str(beat_out / f"{beat_path.stem}_analysis.json")
            beat_info["analysis_summary"] = {
                "bpm": analysis.get("bpm"),
                "key": f"{analysis.get('key')} {analysis.get('mode')}",
                "duration": analysis.get("duration_seconds"),
                "backend": analysis.get("analysis_backend"),
                "chords": [c.get("name") for c in analysis.get("chord_progression", [])[:6]],
                "instruments": [i.get("label") for i in analysis.get("instruments", [])[:5]],
            }

            print(f"Extracting stems {slug}...")
            stems = stem_extractor_adapter.extract_stems(
                beat_path,
                output_dir=beat_out / "stems",
                use_gpu=False,
                high_quality=False,
            )
            # Normalize relative stem paths to absolute
            if isinstance(stems, dict):
                stem_paths = stems.get("stems", {})
                if isinstance(stem_paths, dict):
                    for k, v in stem_paths.items():
                        if v and not Path(v).is_absolute():
                            stem_paths[k] = str(beat_out / "stems" / v)
            beat_info["stems"] = stems

            print(f"Analyzing voice/effects {slug}...")
            voice = voice_effects_adapter.analyze_voice(
                beat_path,
                export_json=True,
                output_dir=beat_out,
            )
            beat_info["voice_json"] = str(beat_out / f"{beat_path.stem}_voice_analysis.json")
            beat_info["voice_summary"] = [
                e.get("effect") for e in voice.get("effects_detected", []) if e.get("confidence", 0) > 0.3
            ]

            beat_info["recipe_md"] = write_recipe(beat_path, style, beat_out, analysis, voice, stems)
        except Exception as e:
            beat_info["error"] = traceback.format_exc()
            status["errors"].append(f"{slug}: {str(e)}")
        finally:
            status["beats"].append(beat_info)

    status["finished"] = datetime.now().isoformat()
    (RESULTS_DIR / "pilot_status.json").write_text(json.dumps(status, indent=2, default=str))
    print("PILOT_DONE")
    return 0 if not status["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
