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

DEFAULT_DATA_DIR = Path(os.environ.get("TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop"))
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


def _discover_assets(source_root: Path) -> List[Path]:
    """Discover asset files under source_root.

    Includes:
    - lyrics/genius/**/*.json (corpus)
    - lyrics/genius/**/*.txt (corpus)
    - lyrics/genius/_*.json (indices)
    - lyrics/lyrics.db (fingerprint DB)
    - espeak-ng/** (phonemizer install)
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

    return sorted(set(assets))


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
) -> BackupManifest:
    """Run a backup of toolshop data assets.

    Args:
        target: Directory to copy assets into.
        source_root: MusicData root (default: D:\\MusicData\\toolshop).
        repo_root: Repo root for repo-side assets (.env, reports).
        verify: Re-read a sample of files and compare hashes.

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

    data_assets = _discover_assets(source_root)
    repo_assets = _discover_repo_assets(repo_root)

    all_assets: List[tuple[Path, Path]] = []
    for src in data_assets:
        rel = src.relative_to(source_root)
        dst = target / rel
        all_assets.append((src, dst))
    for src in repo_assets:
        rel = src.relative_to(repo_root)
        dst = target / "repo" / rel
        all_assets.append((src, dst))

    for src, dst in all_assets:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        size = src.stat().st_size
        digest = _sha256(src)
        entry = FileEntry(
            relative_path=str(src.relative_to(source_root if source_root in src.parents else repo_root)),
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
    args = parser.parse_args(argv)

    manifest = run_backup(
        target=args.target,
        source_root=args.source,
        verify=not args.no_verify,
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
