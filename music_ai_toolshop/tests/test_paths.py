"""Tests for the sibling-repo resolver."""
from __future__ import annotations

from pathlib import Path

import paths


def test_project_root_is_directory():
    assert paths.PROJECT_ROOT.is_dir()


def test_resolve_mastering_tool():
    repo = paths.resolve_mastering_tool()
    assert repo.is_dir()
    assert (repo / "tools" / "vocal_restore" / "restore.py").exists()


def test_resolve_open_daw():
    repo = paths.resolve_open_daw()
    assert repo.is_dir()
    assert (repo / "ai_modules" / "stem_extractor" / "cli.py").exists()


def test_get_repo_paths():
    repos = paths.get_repo_paths()
    assert set(repos.keys()) == {"umbrella", "mastering_tool", "open_daw"}
    for p in repos.values():
        assert isinstance(p, Path)
        assert p.is_dir()
