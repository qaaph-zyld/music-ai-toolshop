"""toolshop/__init__.py must not drag heavy deps into stdlib-only consumers (MAirina)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HEAVY = ("numpy", "librosa", "scipy", "soundfile", "yaml", "pretty_midi")


def test_stdlib_modules_import_without_heavy_deps():
    # sys.modules[name] = None makes `import name` fail, as in a bare cloud venv.
    code = (
        "import sys\n"
        f"for m in {HEAVY!r}: sys.modules[m] = None\n"
        "import toolshop.rhyme_miner, toolshop.syllables\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_submodules_still_reachable_as_attributes():
    import toolshop

    assert toolshop.lyrics_analyzer.__name__ == "toolshop.lyrics_analyzer"
    with pytest.raises(AttributeError):
        toolshop.no_such_module
