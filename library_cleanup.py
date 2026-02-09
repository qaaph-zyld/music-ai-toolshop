"""Library cleanup tool - identifies failed/incomplete audio files."""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime

SUNO_LIBRARY = Path(r"C:\Users\cc\Documents\Project\Suno\bulk_downloader_app\suno_library")
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
MIN_FILE_SIZE = 100_000  # 100KB minimum for valid audio


def find_all_audio_files(root: Path) -> list[Path]:
    """Find all audio files under root."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"_quarantine", "playlists"}]
        for fname in filenames:
            if Path(fname).suffix.lower() in AUDIO_EXTENSIONS:
                files.append(Path(dirpath) / fname)
    return files


def analyze_file_health(files: list[Path]) -> dict:
    """Analyze files and categorize by health status."""
    results = {
        "healthy": [],
        "too_small": [],
        "zero_size": [],
        "unreadable": [],
    }
    
    for fpath in files:
        try:
            size = fpath.stat().st_size
            if size == 0:
                results["zero_size"].append({"path": str(fpath), "size": 0})
            elif size < MIN_FILE_SIZE:
                results["too_small"].append({"path": str(fpath), "size": size})
            else:
                results["healthy"].append({"path": str(fpath), "size": size})
        except Exception as e:
            results["unreadable"].append({"path": str(fpath), "error": str(e)})
    
    return results


def cross_reference_with_analysis(health_results: dict, analysis_path: Path) -> dict:
    """Cross-reference with analysis results to find files that failed analysis."""
    if not analysis_path.exists():
        return {"analysis_failed": [], "analysis_succeeded": []}
    
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # Get successfully analyzed file names
    analyzed_files = {r["file"] for r in analysis.get("detailed_results", [])}
    
    # Find healthy files that failed analysis (likely corrupted internally)
    failed_analysis = []
    succeeded_analysis = []
    
    for item in health_results["healthy"]:
        fname = Path(item["path"]).name
        if fname in analyzed_files:
            succeeded_analysis.append(item)
        else:
            failed_analysis.append(item)
    
    return {
        "analysis_failed": failed_analysis,
        "analysis_succeeded": succeeded_analysis
    }


def generate_cleanup_report(health: dict, analysis_cross: dict) -> str:
    """Generate a cleanup report."""
    report = []
    report.append("=" * 60)
    report.append("SUNO LIBRARY CLEANUP REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    
    total = sum(len(v) for v in health.values())
    report.append(f"\nTotal audio files scanned: {total}")
    report.append(f"  - Healthy (>100KB): {len(health['healthy'])}")
    report.append(f"  - Too small (<100KB): {len(health['too_small'])}")
    report.append(f"  - Zero size (empty): {len(health['zero_size'])}")
    report.append(f"  - Unreadable: {len(health['unreadable'])}")
    
    report.append(f"\nAnalysis cross-reference:")
    report.append(f"  - Successfully analyzed: {len(analysis_cross['analysis_succeeded'])}")
    report.append(f"  - Failed analysis (likely corrupted): {len(analysis_cross['analysis_failed'])}")
    
    # Calculate cleanup candidates
    cleanup_candidates = (
        health["too_small"] + 
        health["zero_size"] + 
        health["unreadable"] +
        analysis_cross["analysis_failed"]
    )
    
    report.append(f"\n{'=' * 60}")
    report.append(f"CLEANUP CANDIDATES: {len(cleanup_candidates)} files")
    report.append("=" * 60)
    
    if health["zero_size"]:
        report.append(f"\n--- Zero-size files ({len(health['zero_size'])}) ---")
        for item in health["zero_size"][:20]:
            report.append(f"  {Path(item['path']).name}")
        if len(health["zero_size"]) > 20:
            report.append(f"  ... and {len(health['zero_size']) - 20} more")
    
    if health["too_small"]:
        report.append(f"\n--- Too small files ({len(health['too_small'])}) ---")
        for item in health["too_small"][:20]:
            report.append(f"  {Path(item['path']).name} ({item['size']} bytes)")
        if len(health["too_small"]) > 20:
            report.append(f"  ... and {len(health['too_small']) - 20} more")
    
    if analysis_cross["analysis_failed"]:
        report.append(f"\n--- Failed analysis ({len(analysis_cross['analysis_failed'])}) ---")
        for item in analysis_cross["analysis_failed"][:20]:
            report.append(f"  {Path(item['path']).name}")
        if len(analysis_cross["analysis_failed"]) > 20:
            report.append(f"  ... and {len(analysis_cross['analysis_failed']) - 20} more")
    
    return "\n".join(report), cleanup_candidates


def move_to_quarantine(files: list[dict], quarantine_dir: Path) -> int:
    """Move problematic files to quarantine folder."""
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    
    for item in files:
        src = Path(item["path"])
        if src.exists():
            dst = quarantine_dir / src.name
            # Handle duplicates
            if dst.exists():
                stem = dst.stem
                suffix = dst.suffix
                counter = 1
                while dst.exists():
                    dst = quarantine_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception as e:
                print(f"Failed to move {src.name}: {e}")
    
    return moved


def main():
    print("Scanning library for audio files...")
    all_files = find_all_audio_files(SUNO_LIBRARY)
    print(f"Found {len(all_files)} audio files")
    
    print("Analyzing file health...")
    health = analyze_file_health(all_files)
    
    print("Cross-referencing with analysis results...")
    analysis_path = SUNO_LIBRARY / "audio_analysis_results.json"
    analysis_cross = cross_reference_with_analysis(health, analysis_path)
    
    print("Generating cleanup report...")
    report, cleanup_candidates = generate_cleanup_report(health, analysis_cross)
    
    # Save report
    report_path = SUNO_LIBRARY / "cleanup_report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")
    print(report)
    
    # Save cleanup candidates list
    candidates_path = SUNO_LIBRARY / "cleanup_candidates.json"
    candidates_path.write_text(
        json.dumps(cleanup_candidates, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nCleanup candidates list saved to: {candidates_path}")
    
    # Ask about quarantine
    print(f"\n{'=' * 60}")
    print(f"READY TO QUARANTINE {len(cleanup_candidates)} FILES")
    print("=" * 60)
    print("Files will be moved to: suno_library/_quarantine/")
    print("This is non-destructive - you can restore files later.")
    
    # Auto-quarantine for this run
    quarantine_dir = SUNO_LIBRARY / "_quarantine"
    moved = move_to_quarantine(cleanup_candidates, quarantine_dir)
    print(f"\nMoved {moved} files to quarantine: {quarantine_dir}")
    
    return {
        "total_scanned": len(all_files),
        "healthy": len(analysis_cross["analysis_succeeded"]),
        "quarantined": moved,
        "quarantine_path": str(quarantine_dir)
    }


if __name__ == "__main__":
    main()
