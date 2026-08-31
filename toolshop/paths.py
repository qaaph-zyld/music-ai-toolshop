"""Central resolution of the toolshop data directory.

**Why this module exists.** The same six-line resolver

    Path(os.environ.get("TOOLSHOP_DATA_DIR", <repo>/data/toolshop))

was copy-pasted into `backup.py`, `remix_adapter.py`, `remix_cli.py`,
`stems_cli.py` and `video_cli.py` — five occurrences of one decision. AGENTS.md's
"fix the class, not the instance" rule says a second occurrence means centralise,
so a sixth (this milestone's transcriber) goes here instead of being pasted again.

The existing five are deliberately **not** migrated in this commit: they work, and
rewriting five unrelated modules inside a milestone diff is exactly the kind of
repo-wide move D12 descoped. They are recorded as a follow-up instead.

**The bug this prevents.** A *relative* default such as
``db_path="production_analysis.db"`` resolves against the caller's CWD, so the
artefact lands wherever the command happened to be run from — the repo root, in
practice. That is debt 13b's shape. Every default path here is absolute.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Repo root, i.e. the parent of the `toolshop/` package.
REPO_ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Return the toolshop data directory as an absolute path.

    Honours ``TOOLSHOP_DATA_DIR`` and falls back to ``<repo>/data/toolshop``.
    Never returns a relative path, even if the environment variable holds one.
    """
    raw = os.environ.get("TOOLSHOP_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return REPO_ROOT / "data" / "toolshop"


def subdir(*parts: str, create: bool = False) -> Path:
    """Return ``data_dir()/<parts...>``, optionally creating it.

    `create` is opt-in: importing a module must never have the side effect of
    making directories, which is why this is a function and not a constant.
    """
    path = data_dir().joinpath(*parts)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
