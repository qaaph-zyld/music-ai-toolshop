"""Tests for the central data-dir resolver.

The rule these enforce is debt 13b's: a *relative* default path resolves against
the caller's CWD, so an artefact lands wherever the command was run from. Every
default here must be absolute regardless of what the environment holds.
"""

from __future__ import annotations

import os
from pathlib import Path

from toolshop import paths


def test_default_is_absolute_and_under_the_repo(monkeypatch):
    monkeypatch.delenv("TOOLSHOP_DATA_DIR", raising=False)
    resolved = paths.data_dir()
    assert resolved.is_absolute()
    assert resolved == paths.REPO_ROOT / "data" / "toolshop"


def test_environment_override_is_honoured(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
    assert paths.data_dir() == tmp_path.resolve()


def test_relative_environment_value_is_still_absolute(monkeypatch, tmp_path):
    """A relative TOOLSHOP_DATA_DIR must not produce CWD-dependent artefacts."""
    monkeypatch.setenv("TOOLSHOP_DATA_DIR", "some/relative/dir")
    monkeypatch.chdir(tmp_path)
    resolved = paths.data_dir()
    assert resolved.is_absolute()
    assert resolved == (tmp_path / "some" / "relative" / "dir").resolve()


def test_subdir_joins_without_creating_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
    target = paths.subdir("lyrics", "transcripts")
    assert target == tmp_path.resolve() / "lyrics" / "transcripts"
    assert not target.exists(), "importing or joining must not touch the filesystem"


def test_subdir_creates_when_asked(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
    target = paths.subdir("vocal_swap", "song", create=True)
    assert target.is_dir()


def test_repo_root_contains_the_package():
    assert (paths.REPO_ROOT / "toolshop" / "__init__.py").exists()
