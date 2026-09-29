"""Live smoke test against the real lyrics.db (read-only). Skipped when it is missing."""

import re

import pytest

from mairina import DEFAULT_LYRICS_DB, cli

pytestmark = pytest.mark.skipif(not DEFAULT_LYRICS_DB.is_file(), reason="lyrics.db not present")


@pytest.fixture(scope="module")
def live_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("live_data")


def _run(capsys, live_dir, *argv):
    code = cli.main(list(argv), data_dir=live_dir)
    return code, capsys.readouterr().out


def test_live_anchors_aabb_gives_four(capsys, live_dir):
    code, out = _run(capsys, live_dir, "anchors", "--scheme", "AABB", "--lane", "drill", "--rng-seed", "1")
    assert code == 0
    assert len([l for l in out.splitlines() if "[A]" in l or "[B]" in l]) == 4


def test_live_rhyme_imas_has_snimas_in_top_10(capsys, live_dir):
    code, out = _run(capsys, live_dir, "rhyme", "imaš", "--lane", "drill")
    assert code == 0
    top10 = [m.group(1) for m in re.finditer(r"^\s*\d+\.\s+(\S+)", out, re.M)][:10]
    assert "snimaš" in top10
