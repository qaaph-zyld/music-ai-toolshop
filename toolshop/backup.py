"""Backup toolshop data assets with manifest and integrity verification.

Creates a ``backup_manifest.json`` recording source paths, sizes, SHA-256
hashes, and timestamp.  Verifies backup integrity by re-reading a sample
of files and comparing hashes.

Usage (programmatic)::

    from toolshop.backup import run_backup
    manifest = run_backup(target=Path(r"C:\\Backups\\toolshop"))

CLI::

    python -m toolshop.backup --target C:\\Backups\\toolshop
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(os.environ.get("TOOLSHOP_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "toolshop")))
DEFAULT_BACKUP_TARGET = Path(os.environ.get("TOOLSHOP_BACKUP_DIR", r"C:\Backups\toolshop"))
MANIFEST_FILENAME = "backup_manifest.json"
VERIFY_SAMPLE_SIZE = 10


@dataclass
class FileEntry:
    """One file in the backup manifest."""

    relative_path: str
    size_bytes: int
    sha256: str
    source: str
    backed_up: bool = True


@dataclass
class BackupManifest:
    """Full backup manifest."""

    created: str
    target: str
    source_root: str
    file_count: int
    total_size_bytes: int
    files: List[Dict[str, Any]] = field(default_factory=list)
    verified: bool = False
    verification_errors: List[str] = field(default_factory=list)


def _sha256(path: Path, buf_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _discover_assets(source_root: Path, include_audio: bool = False) -> List[Path]:
    """Discover asset files under source_root.

    Tier-1 (always):
    - lyrics/genius/**/*.json (corpus)
    - lyrics/genius/**/*.txt (corpus)
    - lyrics/genius/_*.json (indices)
    - lyrics/lyrics.db (fingerprint DB)
    - espeak-ng/** (phonemizer install)
    - suno/*.json (track metadata + the only index of what exists)
    - suno/audio/_download_manifest.json (proof of the preservation fetch)

    Tier-2 (``include_audio=True``):
    - suno/audio/*.mp3 (~13 GB; re-fetchable while the CDN links live, so it is
      opt-in and a Tier-1 restore stays fast)
    """
    assets: List[Path] = []

    lyrics_dir = source_root / "lyrics"
    genius_dir = lyrics_dir / "genius"
    if genius_dir.exists():
        for pattern in ("*.json", "*.txt"):
            assets.extend(genius_dir.rglob(pattern))

    db_path = lyrics_dir / "lyrics.db"
    if db_path.exists():
        assets.append(db_path)

    espeak_dir = source_root / "espeak-ng"
    if espeak_dir.exists():
        for p in espeak_dir.rglob("*"):
            if p.is_file():
                assets.append(p)

    # Suno. Absent from this list until 2026-08-19 (assessment F1b): the backup
    # verified clean for a month while holding zero Suno data.
    suno_dir = source_root / "suno"
    if suno_dir.exists():
        assets.extend(p for p in suno_dir.glob("*.json") if p.is_file())
        audio_dir = suno_dir / "audio"
        if audio_dir.exists():
            manifest = audio_dir / "_download_manifest.json"
            if manifest.exists():
                assets.append(manifest)
            if include_audio:
                assets.extend(p for p in audio_dir.glob("*.mp3") if p.is_file())

    return sorted(set(assets))


def _discover_external_assets(include_audio: bool = False) -> List[tuple[Path, Path]]:
    """Discover assets that live outside both the data root and the repo.

    Returns ``(source_file, base_dir)`` pairs so callers can preserve relative
    layout under ``<target>/external/``.

    ``D:\\Projects\\suno_extractor`` holds the only Suno audio downloaded before the
    2026-08-19 preservation pass (37 mp3s, ~211 MB) plus the older liked-song
    exports. No source root reaches it, so it was never backed up.
    """
    pairs: List[tuple[Path, Path]] = []

    extractor = Path(os.environ.get("TOOLSHOP_SUNO_EXTRACTOR_DIR", r"D:\Projects\suno_extractor"))
    if not extractor.exists():
        return pairs

    # Small, irreplaceable: the liked-song exports and the library DB.
    songs_dir = extractor / "suno_songs"
    if songs_dir.exists():
        for pattern in ("*.json", "*.csv", "*.md"):
            pairs.extend((p, extractor) for p in songs_dir.glob(pattern) if p.is_file())

    library_db = extractor / "suno_library.db"
    if library_db.exists():
        pairs.append((library_db, extractor))

    if include_audio:
        downloads = extractor / "suno_downloads"
        if downloads.exists():
            pairs.extend((p, extractor) for p in downloads.glob("*.mp3") if p.is_file())

    return sorted(set(pairs))


def _discover_repo_assets(repo_root: Path) -> List[Path]:
    """Discover asset files in the repo that should be backed up."""
    assets: List[Path] = []

    env_file = repo_root / "Genious_lyrics_extractor" / ".env"
    if env_file.exists():
        assets.append(env_file)

    reports_dir = repo_root / "lyrics_research" / "reports"
    if reports_dir.exists():
        for p in reports_dir.rglob("*.md"):
            assets.append(p)

    catalogue_dir = repo_root / "results" / "crhymetv_re"
    if catalogue_dir.exists():
        for pattern in ("catalogue.csv", "catalogue.md", "suno_prompts.md"):
            p = catalogue_dir / pattern
            if p.exists():
                assets.append(p)

    return sorted(set(assets))


def run_backup(
    target: Path,
    source_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    verify: bool = True,
    include_audio: bool = False,
    include_external: bool = True,
) -> BackupManifest:
    """Run a backup of toolshop data assets.

    Args:
        target: Directory to copy assets into.
        source_root: Data root (default: ``<repo>/data/toolshop``).
        repo_root: Repo root for repo-side assets (.env, reports).
        verify: Re-read a sample of files and compare hashes.
        include_audio: Also copy Tier-2 audio (Suno mp3s, ~13 GB). Off by default so
            a Tier-1 backup stays small and fast to restore.
        include_external: Also copy assets outside the data root and repo — notably
            ``suno_extractor`` (see :func:`_discover_external_assets`).

    Returns:
        BackupManifest with per-file details.
    """
    source_root = source_root or DEFAULT_DATA_DIR
    repo_root = repo_root or Path(__file__).resolve().parent.parent

    target.mkdir(parents=True, exist_ok=True)

    manifest = BackupManifest(
        created=datetime.now(timezone.utc).isoformat(),
        target=str(target),
        source_root=str(source_root),
        file_count=0,
        total_size_bytes=0,
    )

    data_assets = _discover_assets(source_root, include_audio=include_audio)
    repo_assets = _discover_repo_assets(repo_root)
    external_assets = _discover_external_assets(include_audio=include_audio) if include_external else []

    # (source, destination, relative_path_for_manifest)
    all_assets: List[tuple[Path, Path, str]] = []
    for src in data_assets:
        rel = src.relative_to(source_root)
        all_assets.append((src, target / rel, str(rel)))
    for src in repo_assets:
        rel = src.relative_to(repo_root)
        all_assets.append((src, target / "repo" / rel, str(rel)))
    for src, base in external_assets:
        rel = src.relative_to(base.parent)
        all_assets.append((src, target / "external" / rel, str(Path("external") / rel)))

    for src, dst, rel_path in all_assets:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        size = src.stat().st_size
        digest = _sha256(src)
        entry = FileEntry(
            relative_path=rel_path,
            size_bytes=size,
            sha256=digest,
            source=str(src),
        )
        manifest.files.append(asdict(entry))
        manifest.file_count += 1
        manifest.total_size_bytes += size

    manifest_path = target / MANIFEST_FILENAME
    manifest_data = asdict(manifest)
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    if verify and manifest.files:
        _verify_backup(manifest, target, manifest_path)

    manifest_data = asdict(manifest)
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    logger.info(
        "Backup complete: %d files, %.2f MB → %s (verified=%s)",
        manifest.file_count,
        manifest.total_size_bytes / (1024 * 1024),
        target,
        manifest.verified,
    )
    return manifest


def _verify_backup(manifest: BackupManifest, target: Path, manifest_path: Path) -> None:
    """Re-read a sample of backed-up files and compare hashes."""
    import random

    sample = manifest.files[:]
    if len(sample) > VERIFY_SAMPLE_SIZE:
        sample = random.sample(sample, VERIFY_SAMPLE_SIZE)

    errors: List[str] = []
    for entry in sample:
        src = Path(entry["source"])
        rel = Path(entry["relative_path"])
        if "repo" in rel.parts[:1]:
            dst = target / rel
        else:
            dst = target / rel
        if not dst.exists():
            errors.append(f"Missing in backup: {dst}")
            continue
        dst_hash = _sha256(dst)
        if dst_hash != entry["sha256"]:
            errors.append(f"Hash mismatch: {dst}")

    if errors:
        manifest.verified = False
        manifest.verification_errors = errors
    else:
        manifest.verified = True


def check_backup(target: Optional[Path] = None, max_age_days: int = 7) -> Dict[str, Any]:
    """Check whether a recent valid backup exists.

    Returns a dict suitable for ``toolshop doctor``.
    """
    target = target or DEFAULT_BACKUP_TARGET
    manifest_path = target / MANIFEST_FILENAME

    if not manifest_path.exists():
        return {
            "check": "backup",
            "target": str(target),
            "ok": False,
            "reason": "no manifest found",
            "last_backup": None,
            "file_count": 0,
            "verified": False,
        }

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "check": "backup",
            "target": str(target),
            "ok": False,
            "reason": f"manifest unreadable: {exc}",
            "last_backup": None,
            "file_count": 0,
            "verified": False,
        }

    created_str = data.get("created", "")
    last_backup = None
    age_days = None
    if created_str:
        try:
            created = datetime.fromisoformat(created_str)
            last_backup = created_str
            age_days = (datetime.now(timezone.utc) - created).days
        except Exception:
            pass

    ok = (
        data.get("verified", False)
        and age_days is not None
        and age_days <= max_age_days
    )

    return {
        "check": "backup",
        "target": str(target),
        "ok": ok,
        "reason": "ok" if ok else f"backup is {age_days}d old or unverified" if age_days is not None else "invalid timestamp",
        "last_backup": last_backup,
        "age_days": age_days,
        "file_count": data.get("file_count", 0),
        "verified": data.get("verified", False),
    }


def verify_db(path: Path) -> bool:
    """Smoke-test a backed-up lyrics.db by opening it and counting songs."""
    try:
        conn = sqlite3.connect(str(path))
        count = conn.execute("SELECT count(*) FROM songs").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backup toolshop data assets.")
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_BACKUP_TARGET,
        help=f"Backup target directory (default: {DEFAULT_BACKUP_TARGET})",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Source data root (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument("--no-verify", action="store_true", help="Skip integrity verification.")
    parser.add_argument(
        "--include-audio",
        action="store_true",
        help="Also copy Tier-2 audio (Suno mp3s, ~13 GB). Off by default: audio is "
        "re-fetchable while the CDN links live, so Tier-1 stays small.",
    )
    parser.add_argument(
        "--no-external",
        action="store_true",
        help="Skip assets outside the data root and repo (suno_extractor).",
    )
    args = parser.parse_args(argv)

    manifest = run_backup(
        target=args.target,
        source_root=args.source,
        verify=not args.no_verify,
        include_audio=args.include_audio,
        include_external=not args.no_external,
    )

    print(f"Backup complete: {manifest.file_count} files, {manifest.total_size_bytes / (1024*1024):.1f} MB")
    print(f"  Target: {args.target}")
    print(f"  Verified: {manifest.verified}")
    if manifest.verification_errors:
        print(f"  Errors: {len(manifest.verification_errors)}")
        for e in manifest.verification_errors[:5]:
            print(f"    - {e}")

    db_backup = args.target / "lyrics" / "lyrics.db"
    if db_backup.exists():
        ok = verify_db(db_backup)
        print(f"  DB smoke test: {'PASS' if ok else 'FAIL'}")

    return 0 if manifest.verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
