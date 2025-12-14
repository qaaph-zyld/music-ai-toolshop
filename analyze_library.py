"""Analyze all audio tracks in Suno library for taste profiling."""

import json
import os
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add toolshop to path
sys.path.insert(0, str(Path(__file__).parent))

from toolshop import bpm_adapter, reverse_engineering_adapter

SUNO_LIBRARY = Path(r"C:\Users\cc\Documents\Project\Suno\bulk_downloader_app\suno_library")
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def find_audio_files(root: Path, limit: int = None) -> list[Path]:
    """Find all audio files under root."""
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if Path(fname).suffix.lower() in AUDIO_EXTENSIONS:
                files.append(Path(dirpath) / fname)
                if limit and len(files) >= limit:
                    return files
    return files


def analyze_tracks(files: list[Path], deep_sample: int = 10) -> dict:
    """Run BPM/key analysis on all files, deep analysis on a sample."""
    results = {
        "total_files": len(files),
        "analyzed": 0,
        "failed": 0,
        "bpm_key_results": [],
        "deep_results": [],
        "errors": [],
    }

    print(f"Found {len(files)} audio files. Analyzing...")

    for i, fpath in enumerate(files):
        print(f"  [{i+1}/{len(files)}] {fpath.name[:50]}...", end=" ")
        try:
            # BPM/key analysis (fast)
            bpm_result = bpm_adapter.analyze_track(fpath)
            results["bpm_key_results"].append({
                "file": fpath.name,
                "path": str(fpath),
                "bpm": bpm_result.get("bpm"),
                "key": bpm_result.get("key"),
                "mode": bpm_result.get("mode"),
            })
            results["analyzed"] += 1
            print(f"BPM={bpm_result.get('bpm')}, Key={bpm_result.get('key')} {bpm_result.get('mode')}")

            # Deep analysis on first N tracks
            if len(results["deep_results"]) < deep_sample:
                try:
                    deep = reverse_engineering_adapter.analyze_track(fpath)
                    results["deep_results"].append({
                        "file": fpath.name,
                        "duration": deep.get("duration"),
                        "harmonic_ratio": deep.get("harmonic_ratio"),
                        "spectral_centroid_mean": deep.get("spectral_centroid_mean"),
                        "spectral_bandwidth_mean": deep.get("spectral_bandwidth_mean"),
                        "zero_crossing_rate": deep.get("zero_crossing_rate"),
                        "rms_energy_mean": deep.get("rms_energy_mean"),
                        "chord_progression": deep.get("chord_progression", [])[:5],
                    })
                except Exception as e:
                    results["errors"].append(f"Deep analysis failed for {fpath.name}: {e}")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{fpath.name}: {e}")
            print(f"FAILED: {e}")

    return results


def aggregate_patterns(results: dict) -> dict:
    """Aggregate results to find patterns."""
    bpm_values = [r["bpm"] for r in results["bpm_key_results"] if r["bpm"]]
    keys = [r["key"] for r in results["bpm_key_results"] if r["key"]]
    modes = [r["mode"] for r in results["bpm_key_results"] if r["mode"]]

    # BPM distribution
    bpm_ranges = {"slow (<100)": 0, "mid (100-120)": 0, "upbeat (120-140)": 0, "fast (>140)": 0}
    for bpm in bpm_values:
        if bpm < 100:
            bpm_ranges["slow (<100)"] += 1
        elif bpm < 120:
            bpm_ranges["mid (100-120)"] += 1
        elif bpm < 140:
            bpm_ranges["upbeat (120-140)"] += 1
        else:
            bpm_ranges["fast (>140)"] += 1

    # Deep analysis aggregation
    harmonic_ratios = [r["harmonic_ratio"] for r in results["deep_results"] if r.get("harmonic_ratio")]
    spectral_centroids = [r["spectral_centroid_mean"] for r in results["deep_results"] if r.get("spectral_centroid_mean")]
    
    # Chord analysis
    all_chords = []
    for r in results["deep_results"]:
        for chord_info in r.get("chord_progression", []):
            if isinstance(chord_info, dict):
                all_chords.append(chord_info.get("chord", ""))
            elif isinstance(chord_info, str):
                all_chords.append(chord_info)

    return {
        "bpm_stats": {
            "min": min(bpm_values) if bpm_values else None,
            "max": max(bpm_values) if bpm_values else None,
            "avg": sum(bpm_values) / len(bpm_values) if bpm_values else None,
            "distribution": bpm_ranges,
        },
        "key_distribution": dict(Counter(keys).most_common(12)),
        "mode_distribution": dict(Counter(modes)),
        "harmonic_ratio_avg": sum(harmonic_ratios) / len(harmonic_ratios) if harmonic_ratios else None,
        "spectral_centroid_avg": sum(spectral_centroids) / len(spectral_centroids) if spectral_centroids else None,
        "common_chords": dict(Counter(all_chords).most_common(10)),
    }


def main():
    print("=" * 60)
    print("SUNO LIBRARY AUDIO ANALYSIS")
    print("=" * 60)

    # Find all audio files
    audio_files = find_audio_files(SUNO_LIBRARY)
    if not audio_files:
        print("No audio files found!")
        return

    # Run analysis
    results = analyze_tracks(audio_files, deep_sample=15)

    # Aggregate patterns
    patterns = aggregate_patterns(results)

    # Save results
    output = {
        "summary": {
            "total_files": results["total_files"],
            "analyzed": results["analyzed"],
            "failed": results["failed"],
        },
        "patterns": patterns,
        "detailed_results": results["bpm_key_results"],
        "deep_analysis_sample": results["deep_results"],
        "errors": results["errors"][:10],  # First 10 errors only
    }

    out_path = SUNO_LIBRARY / "audio_analysis_results.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to: {out_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total files: {results['total_files']}")
    print(f"Successfully analyzed: {results['analyzed']}")
    print(f"Failed: {results['failed']}")

    print("\n--- BPM Statistics ---")
    print(f"  Range: {patterns['bpm_stats']['min']:.1f} - {patterns['bpm_stats']['max']:.1f} BPM")
    print(f"  Average: {patterns['bpm_stats']['avg']:.1f} BPM")
    print("  Distribution:")
    for range_name, count in patterns["bpm_stats"]["distribution"].items():
        pct = (count / results["analyzed"] * 100) if results["analyzed"] else 0
        print(f"    {range_name}: {count} ({pct:.1f}%)")

    print("\n--- Key Distribution (Top 5) ---")
    for key, count in list(patterns["key_distribution"].items())[:5]:
        print(f"  {key}: {count}")

    print("\n--- Mode Distribution ---")
    for mode, count in patterns["mode_distribution"].items():
        pct = (count / results["analyzed"] * 100) if results["analyzed"] else 0
        print(f"  {mode}: {count} ({pct:.1f}%)")

    if patterns["harmonic_ratio_avg"]:
        print(f"\n--- Harmonic Ratio (avg): {patterns['harmonic_ratio_avg']:.4f}")

    if patterns["common_chords"]:
        print("\n--- Common Chords ---")
        for chord, count in list(patterns["common_chords"].items())[:5]:
            print(f"  {chord}: {count}")

    return output


if __name__ == "__main__":
    main()
