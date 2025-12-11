import json
import sys
from pathlib import Path
from typing import Iterable


def _import_suno_downloader_module():
    """Import the existing Suno bulk downloader module from the sibling repo."""
    project_root = Path(__file__).resolve().parents[2]
    module_dir = project_root / "Suno" / "bulk_downloader_app"

    if not module_dir.is_dir():
        raise RuntimeError(
            f"Expected Suno bulk_downloader_app directory at {module_dir}, but it was not found."
        )

    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    import suno_downloader  # type: ignore

    return suno_downloader


def sync_liked(
    output_dir: Path,
    convert_to_wav: bool = True,
    delete_original_after_wav: bool = False,
    max_workers: int = 5,
) -> None:
    """Sync liked Suno clips into a local library using the existing downloader."""
    suno_downloader = _import_suno_downloader_module()
    token = suno_downloader.get_token_input()

    downloader = suno_downloader.SunoDownloader(
        token=token,
        output_dir=str(output_dir),
        convert_to_wav=convert_to_wav,
        delete_original_after_wav=delete_original_after_wav,
    )
    downloader.run(max_workers=max_workers)


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
