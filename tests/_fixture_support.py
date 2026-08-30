"""Shared test-fixture support.

**Debt 13b.** `toolshop.lyricsdb.build_database()` writes `_dedup_log.json` into
whatever it is handed as ``root``. Six test modules used to hand it the *tracked*
``tests/fixtures/lyrics_min/`` directory, so a plain ``pytest`` run left
``tests/fixtures/lyrics_min/_dedup_log.json`` modified in the working tree.

That quietly defeated ``toolshop closeout``'s clean-tree check — the gate the whole
close-out discipline rests on — and it is why that file kept showing up dirty at
the start of sessions.

It was first "fixed" in #041 by patching `test_lyricsdb.py` alone and verifying
against that one file. Five other modules were still writing to the tracked
directory, so the fix looked complete and was not. Centralising it here means a
seventh module cannot reintroduce the bug: there is one throwaway copy and no
reason for any test to reach for the tracked path.

Usage::

    from _fixture_support import LYRICS_MIN_FIXTURE as FIXTURE_ROOT
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path

#: The tracked fixture. Read from, never written to.
TRACKED_LYRICS_MIN = Path(__file__).parent / "fixtures" / "lyrics_min"

_TMPDIR = Path(tempfile.mkdtemp(prefix="toolshop_fixtures_"))

#: A disposable copy. Point every test at this instead of the tracked directory.
LYRICS_MIN_FIXTURE = _TMPDIR / "lyrics_min"

shutil.copytree(TRACKED_LYRICS_MIN, LYRICS_MIN_FIXTURE)
atexit.register(shutil.rmtree, _TMPDIR, True)
