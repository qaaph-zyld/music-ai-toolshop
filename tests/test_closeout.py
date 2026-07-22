"""Tests for toolshop closeout command — mechanical close-out gate."""

from unittest import mock
from pathlib import Path

import pytest

from toolshop import closeout


def _mock_run(stdout: str, returncode: int = 0, stderr: str = ""):
    """Create a mock subprocess.run return value."""
    result = mock.Mock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


def test_closeout_clean_tree_all_pass(capsys):
    """All checks pass: clean tree, no unpushed, submodule clean → exit 0."""
    responses = [
        _mock_run("", returncode=0),              # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=0),              # git log @{u}..HEAD --oneline
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run("", returncode=0),              # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    assert code == 0
    captured = capsys.readouterr()
    assert "EVIDENCE BLOCK" in captured.out
    assert "PASS" in captured.out


def test_closeout_dirty_tree(capsys):
    """Working tree has staged/unstaged changes → exit nonzero."""
    responses = [
        _mock_run(" M .gitignore\n", returncode=0),  # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=0),                   # git log @{u}..HEAD --oneline
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run(" M .gitignore\n", returncode=0),  # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    assert code != 0
    captured = capsys.readouterr()
    assert "dirty" in captured.out.lower() or "not clean" in captured.out.lower()


def test_closeout_unpushed_commits(capsys):
    """Unpushed commits on current branch → exit nonzero."""
    responses = [
        _mock_run("", returncode=0),                   # git status --porcelain --ignore-submodules=dirty
        _mock_run("abc1234 some commit\n", returncode=0),  # git log @{u}..HEAD
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run("", returncode=0),                   # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    assert code != 0
    captured = capsys.readouterr()
    assert "unpushed" in captured.out.lower()


def test_closeout_untracked_files(capsys):
    """Untracked non-ignored files in working tree → exit nonzero."""
    responses = [
        _mock_run("?? junk.txt\n", returncode=0),     # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=0),                   # git log @{u}..HEAD
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run("?? junk.txt\n", returncode=0),     # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    assert code != 0
    captured = capsys.readouterr()
    assert "dirty" in captured.out.lower() or "not clean" in captured.out.lower()


def test_closeout_submodule_dirty(capsys):
    """Submodule has untracked content (dirty) → exit nonzero."""
    responses = [
        _mock_run("", returncode=0),                   # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=0),                   # git log @{u}..HEAD
        _mock_run("+aebcf76 mastering_tool\n", returncode=0),  # + prefix = dirty
        _mock_run("", returncode=0),                   # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    assert code != 0
    captured = capsys.readouterr()
    assert "submodule" in captured.out.lower()


def test_closeout_no_upstream(capsys):
    """No upstream configured — degrade to warning, not hard failure."""
    responses = [
        _mock_run("", returncode=0),                   # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=128, stderr="fatal: no upstream"),  # git log @{u}..HEAD
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run("", returncode=0),                   # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        code = closeout.run_closeout()
    # No upstream is a warning, not a hard failure — tree is clean, submodule clean
    assert code == 0
    captured = capsys.readouterr()
    assert "upstream" in captured.out.lower() or "warning" in captured.out.lower()


def test_closeout_evidence_block_contains_status(capsys):
    """Evidence block must contain git status output."""
    responses = [
        _mock_run("", returncode=0),              # git status --porcelain --ignore-submodules=dirty
        _mock_run("", returncode=0),              # git log @{u}..HEAD
        _mock_run(" aebcf76 mastering_tool\n", returncode=0),  # git submodule status
        _mock_run("", returncode=0),              # git status --porcelain (evidence block)
    ]
    with mock.patch.object(closeout.subprocess, "run", side_effect=responses):
        closeout.run_closeout()
    captured = capsys.readouterr()
    assert "git status" in captured.out.lower()
    assert "git log" in captured.out.lower()
    assert "submodule" in captured.out.lower()
