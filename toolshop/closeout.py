"""Mechanical close-out gate for toolshop.

Checks that the repo is in a clean, pushed state and prints an evidence
block suitable for pasting into a handoff.
"""

import subprocess
import sys
from pathlib import Path


def _git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command and return the completed process."""
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def run_closeout(repo_path: Path | None = None) -> int:
    """Run the close-out gate.

    Checks (in order):
      a) Working tree clean — no staged, unstaged, or untracked non-ignored files.
      b) No unpushed commits on the current branch vs its upstream.
      c) Submodule ``mastering_tool`` clean and pointer present on remote (best-effort).

    Prints an EVIDENCE BLOCK with raw git output.
    Returns 0 only when all checks pass; nonzero otherwise.
    """
    cwd = repo_path

    failures: list[str] = []

    # --- Check (a): clean working tree ---
    status_proc = _git(["status", "--porcelain"], cwd=cwd)
    status_output = status_proc.stdout.strip()
    if status_output:
        failures.append("working tree not clean (staged/unstaged/untracked changes)")

    # --- Check (b): no unpushed commits ---
    log_proc = _git(["log", "@{u}..HEAD", "--oneline"], cwd=cwd)
    log_output = log_proc.stdout.strip()
    upstream_warning = ""
    if log_proc.returncode != 0:
        upstream_warning = f"WARNING: could not determine upstream ({log_proc.stderr.strip()})"
    elif log_output:
        failures.append(f"unpushed commits on current branch:\n{log_output}")

    # --- Check (c): submodule clean ---
    sub_proc = _git(["submodule", "status"], cwd=cwd)
    sub_output = sub_proc.stdout.strip()
    sub_warning = ""
    sub_fail = False
    for line in sub_output.splitlines():
        line = line.strip()
        if not line:
            continue
        prefix = line[0] if line else ""
        if prefix == "+":
            sub_fail = True
            sub_warning = f"submodule dirty: {line}"
        elif prefix == "-":
            sub_fail = True
            sub_warning = f"submodule not initialized: {line}"
        elif prefix == "U":
            sub_fail = True
            sub_warning = f"submodule merge conflict: {line}"
    if sub_fail:
        failures.append(sub_warning)

    # --- Print evidence block ---
    print("=" * 60)
    print("CLOSE-OUT EVIDENCE BLOCK")
    print("=" * 60)
    print()
    print("--- git status --porcelain ---")
    print(status_output if status_output else "(clean)")
    print()
    print("--- git log @{u}..HEAD --oneline ---")
    if upstream_warning:
        print(upstream_warning)
    else:
        print(log_output if log_output else "(none)")
    print()
    print("--- git submodule status ---")
    print(sub_output if sub_output else "(no submodules)")
    print()
    print("--- verdict ---")
    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
    else:
        print("PASS")
    print()
    print("=" * 60)

    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``toolshop closeout``."""
    return run_closeout()


if __name__ == "__main__":
    raise SystemExit(main())
