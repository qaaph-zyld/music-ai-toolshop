import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def sync_liked(
    output_dir: Path,
    convert_to_wav: bool = True,
    delete_original_after_wav: bool = False,
    max_workers: int = 5,
) -> None:
    """Placeholder for Suno sync after decoupling from external repos.

    This project is self-contained and does not bundle any downloader.
    To refresh your local ``suno_library``, run your preferred Suno
    downloader separately, then use ``toolshop suno list/analyze/export-text``
    on the resulting library.
    """
    raise RuntimeError(
        "Suno sync has been decoupled from external repos. "
        "Please run your Suno downloader separately, then use "
        "'toolshop suno list/analyze/export-text' on the local library."
    )


def list_library(root: Path) -> None:
    """List tracks from a local Suno library by scanning metadata JSON files."""
    if not root.exists():
        print(f"No Suno library found at {root}")
        return

    metadata_files: Iterable[Path] = sorted(root.rglob("*_metadata.json"))
    found_any = False

    for metadata_path in metadata_files:
        try:
            with metadata_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue

        title = data.get("title") or "Untitled"
        clip_id = data.get("id") or data.get("clip_id") or metadata_path.stem
        date_folder = metadata_path.parent.relative_to(root)
        print(f"{clip_id}\t{date_folder}\t{title}")
        found_any = True

    if not found_any:
        print(f"No metadata JSON files found under {root}")


def export_text(
    root: Path,
    output_json: Path,
    output_txt: Optional[Path] = None,
) -> None:
    """Export lyrics and descriptions from liked Suno tracks.

    Scans all ``*_metadata.json`` files under ``root``, filters to clips where
    ``is_liked`` is true, and writes a JSON file containing one entry per
    track, sorted by handle then title. Optionally also writes a plain-text
    export that concatenates all lyrics and descriptions.
    """
    if not root.exists():
        print(f"No Suno library found at {root}")
        return

    metadata_files: Iterable[Path] = sorted(root.rglob("*_metadata.json"))
    songs: List[Dict[str, Any]] = []

    for metadata_path in metadata_files:
        try:
            with metadata_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue

        if not data.get("is_liked", False):
            # Only keep liked tracks, as requested.
            continue

        meta = data.get("metadata") or {}
        lyrics = meta.get("prompt") or ""
        description = meta.get("tags") or ""

        song: Dict[str, Any] = {
            "id": data.get("id"),
            "title": data.get("title"),
            "handle": data.get("handle"),
            "display_name": data.get("display_name"),
            "display_tags": data.get("display_tags"),
            "created_at": data.get("created_at"),
            "duration": meta.get("duration"),
            "lyrics": lyrics,
            "description": description,
            "metadata_path": str(metadata_path.relative_to(root)),
        }
        songs.append(song)

    # Group/sort by handle then title for easier navigation.
    songs.sort(
        key=lambda s: (
            (s.get("handle") or "").lower(),
            (s.get("title") or "").lower(),
        )
    )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "root": str(root),
        "total_liked_songs": len(songs),
        "songs": songs,
    }
    with output_json.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    if output_txt is not None:
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        with output_txt.open("w", encoding="utf-8") as fh_txt:
            for song in songs:
                handle = song.get("handle") or ""
                title = song.get("title") or ""
                header = (handle + " - " + title).strip(" -")
                fh_txt.write(f"# {header}\n")

                if song.get("description"):
                    fh_txt.write("[DESCRIPTION]\n")
                    fh_txt.write(song["description"].strip() + "\n\n")

                if song.get("lyrics"):
                    fh_txt.write("[LYRICS]\n")
                    fh_txt.write(song["lyrics"].strip() + "\n")

                fh_txt.write("\n---\n\n")

    print(f"Exported {len(songs)} liked tracks to {output_json}")
    if output_txt is not None:
        print(f"Plain-text export written to {output_txt}")
