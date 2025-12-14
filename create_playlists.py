"""Create genre playlists based on BPM/key analysis."""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime

SUNO_LIBRARY = Path(r"C:\Users\cc\Documents\Project\Suno\bulk_downloader_app\suno_library")


def load_analysis() -> dict:
    """Load the audio analysis results."""
    analysis_path = SUNO_LIBRARY / "audio_analysis_results.json"
    with open(analysis_path, "r", encoding="utf-8") as f:
        return json.load(f)


def categorize_by_bpm(tracks: list) -> dict:
    """Categorize tracks by BPM range."""
    categories = {
        "chill_slow_60-99": [],
        "groovy_mid_100-119": [],
        "club_upbeat_120-139": [],
        "high_energy_140-159": [],
        "extreme_160+": []
    }
    
    for track in tracks:
        bpm = track.get("bpm")
        if not bpm:
            continue
        
        if bpm < 100:
            categories["chill_slow_60-99"].append(track)
        elif bpm < 120:
            categories["groovy_mid_100-119"].append(track)
        elif bpm < 140:
            categories["club_upbeat_120-139"].append(track)
        elif bpm < 160:
            categories["high_energy_140-159"].append(track)
        else:
            categories["extreme_160+"].append(track)
    
    return categories


def categorize_by_key(tracks: list) -> dict:
    """Categorize tracks by musical key."""
    categories = {}
    
    for track in tracks:
        key = track.get("key")
        if not key:
            continue
        
        key_name = f"key_{key}_major"
        if key_name not in categories:
            categories[key_name] = []
        categories[key_name].append(track)
    
    return categories


def categorize_by_energy(tracks: list) -> dict:
    """Create energy-based playlists combining BPM and key characteristics."""
    # Bright keys: G, C, D, A, E
    # Dark/moody keys: D#, F#, G#, A#, C#
    bright_keys = {"G", "C", "D", "A", "E"}
    dark_keys = {"D#", "F#", "G#", "A#", "C#", "B", "F"}
    
    categories = {
        "euphoric_bright_fast": [],      # Fast + bright key
        "dark_club_bangers": [],         # Fast + dark key
        "uplifting_grooves": [],         # Mid + bright
        "moody_underground": [],         # Mid + dark
        "chill_vibes": []                # Slow any key
    }
    
    for track in tracks:
        bpm = track.get("bpm", 0)
        key = track.get("key", "")
        
        if bpm < 110:
            categories["chill_vibes"].append(track)
        elif bpm >= 130:
            if key in bright_keys:
                categories["euphoric_bright_fast"].append(track)
            else:
                categories["dark_club_bangers"].append(track)
        else:
            if key in bright_keys:
                categories["uplifting_grooves"].append(track)
            else:
                categories["moody_underground"].append(track)
    
    return categories


def create_m3u_playlist(name: str, tracks: list, output_dir: Path) -> Path:
    """Create an M3U playlist file."""
    playlist_path = output_dir / f"{name}.m3u"
    
    lines = ["#EXTM3U", f"#PLAYLIST:{name}"]
    
    for track in tracks:
        path = track.get("path", "")
        if path and Path(path).exists():
            # Add extended info
            bpm = track.get("bpm", "?")
            key = track.get("key", "?")
            fname = Path(path).stem
            lines.append(f"#EXTINF:-1,{fname} [BPM:{bpm} Key:{key}]")
            lines.append(path)
    
    playlist_path.write_text("\n".join(lines), encoding="utf-8")
    return playlist_path


def create_playlist_summary(all_playlists: dict, output_dir: Path) -> Path:
    """Create a summary of all playlists."""
    summary_path = output_dir / "PLAYLIST_INDEX.md"
    
    lines = [
        "# 🎵 Auto-Generated Playlists",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## By Energy/Mood",
        ""
    ]
    
    energy_playlists = [p for p in all_playlists if p.startswith(("euphoric", "dark", "uplifting", "moody", "chill"))]
    for name in sorted(energy_playlists):
        count = all_playlists[name]
        emoji = {"euphoric": "🌟", "dark": "🖤", "uplifting": "☀️", "moody": "🌙", "chill": "😌"}.get(name.split("_")[0], "🎵")
        lines.append(f"- {emoji} **{name.replace('_', ' ').title()}** - {count} tracks")
    
    lines.extend(["", "## By BPM Range", ""])
    
    bpm_playlists = [p for p in all_playlists if "bpm" in p.lower() or any(x in p for x in ["slow", "mid", "upbeat", "energy", "extreme"])]
    for name in sorted(bpm_playlists):
        count = all_playlists[name]
        lines.append(f"- 🎚️ **{name.replace('_', ' ').title()}** - {count} tracks")
    
    lines.extend(["", "## By Key", ""])
    
    key_playlists = [p for p in all_playlists if p.startswith("key_")]
    for name in sorted(key_playlists, key=lambda x: -all_playlists[x]):
        count = all_playlists[name]
        key_name = name.replace("key_", "").replace("_major", " Major")
        lines.append(f"- 🎹 **{key_name}** - {count} tracks")
    
    lines.extend([
        "",
        "## How to Use",
        "- Open any `.m3u` file with your media player (VLC, Foobar2000, etc.)",
        "- Playlists are sorted by energy, BPM, and key for easy mixing",
        "- Use energy playlists for mood-based listening",
        "- Use key playlists for harmonic mixing (DJ sets)",
        ""
    ])
    
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main():
    print("Loading audio analysis...")
    analysis = load_analysis()
    tracks = analysis.get("detailed_results", [])
    print(f"Found {len(tracks)} analyzed tracks")
    
    # Create playlists directory
    playlists_dir = SUNO_LIBRARY / "playlists"
    playlists_dir.mkdir(exist_ok=True)
    
    all_playlists = {}
    
    # BPM-based playlists
    print("\nCreating BPM-based playlists...")
    bpm_cats = categorize_by_bpm(tracks)
    for name, cat_tracks in bpm_cats.items():
        if cat_tracks:
            create_m3u_playlist(name, cat_tracks, playlists_dir)
            all_playlists[name] = len(cat_tracks)
            print(f"  ✓ {name}: {len(cat_tracks)} tracks")
    
    # Key-based playlists
    print("\nCreating key-based playlists...")
    key_cats = categorize_by_key(tracks)
    for name, cat_tracks in sorted(key_cats.items(), key=lambda x: -len(x[1])):
        if cat_tracks:
            create_m3u_playlist(name, cat_tracks, playlists_dir)
            all_playlists[name] = len(cat_tracks)
            print(f"  ✓ {name}: {len(cat_tracks)} tracks")
    
    # Energy-based playlists
    print("\nCreating energy/mood playlists...")
    energy_cats = categorize_by_energy(tracks)
    for name, cat_tracks in energy_cats.items():
        if cat_tracks:
            create_m3u_playlist(name, cat_tracks, playlists_dir)
            all_playlists[name] = len(cat_tracks)
            print(f"  ✓ {name}: {len(cat_tracks)} tracks")
    
    # Create summary
    print("\nGenerating playlist index...")
    summary_path = create_playlist_summary(all_playlists, playlists_dir)
    
    # Save playlist metadata
    meta_path = playlists_dir / "playlist_metadata.json"
    meta_path.write_text(json.dumps({
        "generated": datetime.now().isoformat(),
        "total_tracks": len(tracks),
        "playlists": all_playlists
    }, indent=2), encoding="utf-8")
    
    print(f"\n{'=' * 50}")
    print("PLAYLISTS CREATED SUCCESSFULLY")
    print("=" * 50)
    print(f"Location: {playlists_dir}")
    print(f"Total playlists: {len(all_playlists)}")
    print(f"Index file: {summary_path}")
    
    return all_playlists


if __name__ == "__main__":
    main()
