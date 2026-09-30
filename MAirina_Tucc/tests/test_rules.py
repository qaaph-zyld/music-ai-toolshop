"""rules: soft advisory hints with stable rule_ids. They never block."""

import pytest

from mairina import rules


@pytest.fixture(scope="module")
def lex():
    return rules.load_lexicons()


def test_lexicons_loaded(lex):
    assert "ljubav" in lex["abstract"] and "krevet" in lex["concrete"]
    assert "vreme" in lex["ekavica"] and "vrijeme" in lex["ijekavica"]
    assert lex["cliches"] and lex["calques"]
    # identical pairs (ludilo/ludilo) discriminate nothing: excluded from both
    assert "ludilo" not in lex["ekavica"] and "ludilo" not in lex["ijekavica"]
    # ambiguous pairs are dropped entirely: 'med' (honey)/'mijed' is not a dialect marker
    assert "med" not in lex["ekavica"] and "mijed" not in lex["ijekavica"]


def test_missing_lexicon_files_disable_only_their_rules(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rules, "LEX_DIR", tmp_path)          # empty dir: every file missing
    rules.load_lexicons.cache_clear()
    try:
        lex = rules.load_lexicons()
        assert lex["cliches"] == [] and lex["concrete"] == set()
        assert lex["ekavica"] == set() and lex["ijekavica"] == set()
        assert rules.line_hints("plamen ljubavi gori u meni", 1, lex) == []   # no crash
        err = capsys.readouterr().err
        assert err.count("Note: lexicon file missing:") == 5
    finally:
        rules.load_lexicons.cache_clear()


def test_missing_single_lexicon_disables_only_its_rule(tmp_path, monkeypatch, capsys):
    for f in rules.LEX_DIR.iterdir():                        # real lexicons minus cliches.txt
        if f.name != "cliches.txt":
            (tmp_path / f.name).write_bytes(f.read_bytes())
    monkeypatch.setattr(rules, "LEX_DIR", tmp_path)
    rules.load_lexicons.cache_clear()
    try:
        lex = rules.load_lexicons()
        assert lex["cliches"] == [] and "vreme" in lex["ekavica"]     # other rules still armed
        hits = rules.line_hints("plamen ljubavi gori", 1, lex)
        assert not [h for h in hits if h["rule_id"] == rules.RULE_CLICHE]
        assert [h for h in rules.verse_hints(["vreme leti", "vrijeme stoji"], lex)
                if h["rule_id"] == rules.RULE_DIALECT_MIX]
        assert capsys.readouterr().err.count("Note: lexicon file missing:") == 1
    finally:
        rules.load_lexicons.cache_clear()


def test_cliche_and_calque_hits(lex):
    hits = rules.line_hints("plamen ljubavi gori u meni", 1, lex)
    assert [h["rule_id"] for h in hits] == [rules.RULE_CLICHE]
    hits = rules.line_hints("padam za tobom nocas", 3, lex)
    assert hits[0]["rule_id"] == rules.RULE_CALQUE and hits[0]["line"] == 3
    # word boundary: 'padam zauvek' must not fire the 'padam za' calque
    assert rules.line_hints("padam zauvek veceras", 1, lex) == []


def test_abstract_stack_needs_two_and_no_concrete(lex):
    hits = rules.line_hints("ljubav i sudbina vode me", 1, lex)
    assert any(h["rule_id"] == rules.RULE_ABSTRACT_STACK for h in hits)
    assert not rules.line_hints("ljubav i sudbina na krevet tvoj", 1, lex)  # concrete present
    assert not rules.line_hints("samo ljubav ostaje", 1, lex)               # one abstract only


def test_dialect_mix_is_verse_level(lex):
    hints = rules.verse_hints(["vreme leti brzo", "vrijeme stoji"], lex)
    lines = {h["line"] for h in hints if h["rule_id"] == rules.RULE_DIALECT_MIX}
    assert lines == {1, 2}
    assert not [h for h in rules.verse_hints(["vreme leti", "mleko curi"], lex)
                if h["rule_id"] == rules.RULE_DIALECT_MIX]
    # 'ludilo' is identical in both dialects: alone it cannot mix them
    assert not [h for h in rules.verse_hints(["ludilo sve", "ludilo opet"], lex)
                if h["rule_id"] == rules.RULE_DIALECT_MIX]
    # 'med/mijed' was dropped from the pairs: it cannot fake a mix either
    assert not [h for h in rules.verse_hints(["u medu tebe", "i mijed opet"], lex)
                if h["rule_id"] == rules.RULE_DIALECT_MIX]


def test_self_rhyme_adjacent_only_and_not_on_hook_repeats(lex, index):
    hints = rules.verse_hints(["kraj je blizu", "nije blizu"], lex, index)
    assert any(h["rule_id"] == rules.RULE_SELF_RHYME for h in hints)
    # identical repeated lines (a hook) are not a self-rhyme problem
    hints = rules.verse_hints(["isti red svuda", "isti red svuda"], lex, index)
    assert not [h for h in hints if h["rule_id"] == rules.RULE_SELF_RHYME]
    # different endings: no hint
    assert not rules.verse_hints(["lava pada", "glava spava"], lex, index)


def test_self_rhyme_needs_a_real_shared_stem(lex, index):
    # 'znaš'/'znam' share the lemma znati but are too short — not a self-rhyme
    assert not [h for h in rules.verse_hints(["kraj da znaš", "nije znam"], lex, index)
                if h["rule_id"] == rules.RULE_SELF_RHYME]
    # 'lava'/'laka' share only 'la' — below the 4-letter stem floor
    assert not [h for h in rules.verse_hints(["usne lava", "crne laka"], lex, index)
                if h["rule_id"] == rules.RULE_SELF_RHYME]
    # a real shared stem (>= 4 letters) still fires
    assert [h for h in rules.verse_hints(["sve padalima", "ide padama"], lex, index)
            if h["rule_id"] == rules.RULE_SELF_RHYME]


def test_hints_have_stable_rule_ids_and_never_block(lex):
    hints = rules.verse_hints(["plamen ljubavi, vreme leti", "vrijeme stoji, padam za tobom"], lex)
    ids = {h["rule_id"] for h in hints}
    assert ids >= {rules.RULE_CLICHE, rules.RULE_DIALECT_MIX}
    assert all(isinstance(h["rule_id"], str) and h["rule_id"] == h["rule_id"].lower()
               for h in hints)
    assert rules.SHORT_LABELS.keys() >= ids                    # every id is displayable
