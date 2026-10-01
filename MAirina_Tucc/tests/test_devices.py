"""devices: advisory tags for sound patterns and mechanical figures.

All fixtures are hand-written lines; no real lyrics, no real corpus.
"""

import pytest

from mairina import devices as D
from mairina.used import tokenize


def kinds(rep_or_tags):
    seq = rep_or_tags.devices if hasattr(rep_or_tags, "devices") else rep_or_tags
    return [d["kind"] for d in seq]


def test_every_tag_is_advisory_and_typed():
    rep = D.analyze_verse(["lep kao san", "crn ko ćud"])
    for lr in rep.lines:
        for d in lr.devices:
            assert set(d) == {"kind", "span", "confidence", "advisory"}
            assert d["advisory"] is True
            assert d["confidence"] in ("high", "medium", "low")


def test_simile_markers_and_ko_disambiguation():
    rep = D.analyze_verse(["usne crvene ko lava", "lep kao san i miran poput vode"])
    d1 = rep.lines[0].devices
    assert any(d["kind"] == "simile" and d["span"] == "ko" for d in d1)
    d2 = {d["span"]: d for d in rep.lines[1].devices if d["kind"] == "simile"}
    assert set(d2) == {"kao", "poput"} and d2["kao"]["confidence"] == "high"


def test_ko_means_who_in_questions_and_before_verbs(index):
    rep = D.analyze_verse(["ko ti je dao sve?", "ko pade prvi u vodu"], index=index)
    assert "simile" not in kinds(rep.lines[0])            # question: 'ko' = who
    assert "simile" not in kinds(rep.lines[1])            # 'pade' is VERB in fixture index
    rep = D.analyze_verse(["ko sanjam te nocas"])
    sim = [d for d in rep.lines[0].devices if d["kind"] == "simile"]
    assert sim and sim[0]["confidence"] == "low"          # line-initial, unverifiable


def test_ko_who_check_at_any_position(index):
    rep = D.analyze_verse(["pitaj ko je gazda", "ne znam ko me zove"], index=index)
    assert "simile" not in kinds(rep.lines[0])            # 'ko je' -> who, mid-line
    assert "simile" not in kinds(rep.lines[1])            # 'ko me zove': clitic then VERB
    rep = D.analyze_verse(["hladna ko led", "k\u2019o mafija"], index=index)
    assert [d["confidence"] for d in rep.lines[0].devices if d["kind"] == "simile"] == ["medium"]
    assert "simile" in kinds(rep.lines[1])                # curly apostrophe k'o recognised
    rep = D.analyze_verse(["tiho kao da spava", "tiho kao što spava", "lep kao san"])
    assert [d["confidence"] for d in rep.lines[0].devices if d["kind"] == "simile"] == ["low"]
    assert [d["confidence"] for d in rep.lines[1].devices if d["kind"] == "simile"] == ["low"]
    assert [d["confidence"] for d in rep.lines[2].devices if d["kind"] == "simile"] == ["high"]


def test_alliteration_strong_and_weak():
    rep = D.analyze_verse(["kučka kuca kroz kapiju"])      # k onsets x3 in window
    strong = [d for d in rep.lines[0].devices if d["kind"] == "alliteration"]
    assert strong and strong[0]["confidence"] == "high" and "k" in strong[0]["span"]
    rep = D.analyze_verse(["sala šalju"])
    weak = [d for d in rep.lines[0].devices if d["kind"] == "alliteration"]
    assert weak and weak[0]["confidence"] == "low"         # s/š: same class, not phoneme
    rep = D.analyze_verse(["ima ona uvek osmeh"])          # vowel onsets: nothing to repeat
    assert "alliteration" not in kinds(rep.lines[0])


def test_consonance_density_and_gauge():
    line = "prst kroz krst tvrd"
    d = D.consonance_density(line)
    assert d > 0.6
    assert "consonance" in kinds(D.analyze_line(line))
    assert D.gauge(0.0) == "▯▯▯" and D.gauge(2.0) == "▮▮▮" and D.gauge(0.7) == "▮▮▯"


def test_internal_rhyme_keeps_only_maximal_non_overlapping_echoes():
    rep = D.analyze_verse(["u panameri da se snimas"])
    ir = [d["span"] for d in rep.lines[0].devices if d["kind"] == "internal_rhyme"]
    assert ir == []            # 'aeia' recurs only in overlapping windows: not a rhyme
    rep = D.analyze_verse(["mira pita"])                  # 'ia' twice, disjoint
    assert [d["span"] for d in rep.lines[0].devices if d["kind"] == "internal_rhyme"] == ["ia"]


def test_multisyllabic_rhyme_and_rhyme_letters():
    rep = D.analyze_verse(["usne crvene ko lava", "s tobom uvek ludilo",
                           "niko ne pomisli da spava", "separe je nas, najludji smo - znas",
                           "mala, mogla si da me imas", "u panameri da se snimas"])
    assert [lr.rhyme_letter for lr in rep.lines] == ["A", None, "A", "B", "B", "B"]
    m5 = [d["span"] for d in rep.lines[4].devices if d["kind"] == "multisyllabic_rhyme"]
    m6 = [d["span"] for d in rep.lines[5].devices if d["kind"] == "multisyllabic_rhyme"]
    assert m5 == m6 == ["iaeia"]                          # longest shared tail, not a 3-vowel cut


def test_anaphora_shared_opening_needs_a_content_word():
    rep = D.analyze_verse(["ko sanjam te nocas", "ko vidim te sutra", "sve drugo nestaje"])
    assert "anaphora" in kinds(rep.lines[0]) and "anaphora" in kinds(rep.lines[1])
    assert "anaphora" not in kinds(rep.lines[2])
    # function-word-only openings are not anaphora
    rep = D.analyze_verse(["da se vratim", "da se sakrijem"])
    assert not any("anaphora" in kinds(lr) for lr in rep.lines)
    # the span is the shared opening text, casing kept
    rep = D.analyze_verse(["Laku noc, majko", "Laku noc, brate"])
    an = [d for d in rep.lines[0].devices if d["kind"] == "anaphora"]
    assert an and an[0]["span"] == "Laku noc"


def test_epistrophe_epizeuxis_anadiplosis_hook_repeat():
    rep = D.analyze_verse(["idem tamo nocas svuda", "ostanem tamo svuda", "gresim"])
    assert "epistrophe" in kinds(rep.lines[0]) and "epistrophe" in kinds(rep.lines[1])
    rep = D.analyze_verse(["no no no danas", "sve zove zove"])
    assert "epizeuxis" in kinds(rep.lines[0]) and "epizeuxis" in kinds(rep.lines[1])
    rep = D.analyze_verse(["vidi me kraj grad", "grad zove svaku noc"])
    assert "anadiplosis" in kinds(rep.lines[0]) and "anadiplosis" in kinds(rep.lines[1])
    rep = D.analyze_verse(["zovi me kada padne", "tekst koji ne znam", "zovi me kada padne"])
    assert "hook_repeat" in kinds(rep.lines[0]) and "hook_repeat" in kinds(rep.lines[2])
    assert "hook_repeat" not in kinds(rep.lines[1])


def test_code_switch_and_name_drop():
    rep = D.analyze_verse(["imam money i cash nocas"], gazetteer={"panama", "acme corp"})
    cs = [d for d in rep.lines[0].devices if d["kind"] == "code_switch"]
    assert {d["span"] for d in cs} == {"money", "cash"}
    rep = D.analyze_verse(["vozim acme corp do panama"], gazetteer={"panama", "acme corp"})
    nd = {d["span"] for d in rep.lines[0].devices if d["kind"] == "name_drop"}
    assert nd == {"acme corp", "panama"}
    # Serbian homographs (do/no/so/to/me/i/a/on) were dropped from english_tokens
    rep = D.analyze_verse(["ide do kuce, no ti si tu"])
    assert "code_switch" not in kinds(rep.lines[0])


def test_name_drop_wins_over_code_switch():
    rep = D.analyze_verse(["Gucci na meni, BMW ispred kuce"],
                          gazetteer={"gucci", "bmw"})
    nd = {d["span"] for d in rep.lines[0].devices if d["kind"] == "name_drop"}
    cs = {d["span"] for d in rep.lines[0].devices if d["kind"] == "code_switch"}
    assert {"gucci", "bmw"} <= nd and not (cs & nd)


def test_name_drop_filters_common_words_and_keeps_phrases(index):
    gaz = {"mala", "niko", "glava", "melisa", "gucci", "tabak mala"}
    rep = D.analyze_verse(["mala i niko i glava i melisa i gucci od tabak mala"],
                          gazetteer=gaz, index=index)
    nd = {d["span"] for d in rep.lines[0].devices if d["kind"] == "name_drop"}
    assert nd == {"melisa", "gucci", "tabak mala"}        # mala/niko/glava: freq>=20 non-PROPN
    rep = D.analyze_verse(["imam mala kod tabak mala"], gazetteer=gaz)   # no index: as-is
    nd = {d["span"] for d in rep.lines[0].devices if d["kind"] == "name_drop"}
    assert nd == {"mala", "tabak mala"}


def test_anadiplosis_from_analyze_line_prev():
    tags = D.analyze_line("grad zove svaku noc", prev_lines=["vidi me kraj grad"])
    assert "anadiplosis" in kinds(tags)


def test_gazetteer_from_fixture_db(corpus_db):
    gaz = D.load_gazetteer(str(corpus_db))
    assert "timbuktu" in gaz and "devito" in gaz            # entity + songs.target_artist
    assert "acme corp" in gaz and "acme" not in gaz         # multi-word entities stay phrases
    assert "tabak mala" in gaz and "mala" not in gaz        # 'mala' never splits off
    assert "glava" in gaz                                   # kept at load; suppressed at match
    assert "panamera" not in gaz                            # MISC is not ORG/PER/LOC
    assert not ({"yeah yeah", "a a a", "oh", "ja la"} & gaz)   # ad-lib/filler NER noise dropped
    assert "thameshouse" not in gaz and "english bard" not in gaz   # English corpus excluded


def test_the_task_verse(corpus_db, index):
    """The user's gate verse: A,-,A,B,B,B; simile on 1; no name_drop on mala/niko;
    line 6 alliteration does not come from se+snimaš."""
    verse = ["Usne crvene ko lava \u2013", "s tobom uvek ludilo", "(niko ne pomisli da spava)",
             "Separe je na\u0161, najlu\u0111i smo \u2013 zna\u0161", "Mala, mogla si da me ima\u0161,",
             "u Panameri da se snima\u0161"]
    rep = D.analyze_verse(verse, gazetteer=D.load_gazetteer(str(corpus_db)), index=index)
    assert [lr.rhyme_letter for lr in rep.lines] == ["A", None, "A", "B", "B", "B"]
    assert any(d["kind"] == "simile" and d["span"] == "ko" for d in rep.lines[0].devices)
    assert not any(d["kind"] == "name_drop" for lr in rep.lines for d in lr.devices)
    assert "alliteration" not in kinds(rep.lines[5])


def test_weak_alliteration_is_detail_only_strong_sets_the_flag():
    tags = D.analyze_line("sala šalju")                 # s/š: same class, not same phoneme
    weak = [d for d in tags if d["kind"] == "alliteration"]
    assert weak and weak[0]["confidence"] == "low"          # still available as a low-confidence tag
    assert "alliteration" not in D.device_kinds(tags)       # ... but not a kind/flag
    assert not D.has_alliteration(tokenize("sala šalju"))
    strong = D.analyze_line("kučka kuca kroz kapiju")
    assert "alliteration" in D.device_kinds(strong) and D.has_alliteration(tokenize("kučka kuca kroz"))
    assert not D.has_alliteration(tokenize("pada kisa"))     # p/k: both plosives, different phonemes
    assert D.device_kinds([]) == set()


def test_strong_alliteration_needs_two_content_onsets_in_the_four_word_window():
    assert D.has_alliteration(tokenize("kuca ima kamen"))                # k . k inside the window
    assert not D.has_alliteration(tokenize("kuca ima ona oko kamen"))    # 4 words apart: outside
    assert not D.has_alliteration(tokenize("ne neguj"))                  # 'ne' is measured out
    assert not D.has_alliteration(tokenize("ja se snimam"))              # clitics are measured out
    assert D.has_alliteration(tokenize("nosi nikad novac"))


def test_noise_entries_are_recognised_and_real_names_survive():
    for noise in ("a a a", "yeah yeah", "bu bu bu", "oh yeah", "ja la", "hey", "skrr skrr",
                  "ab", "o a", "ye", "e"):
        assert D.is_noise_entry(noise), noise
    for name in ("gucci", "bmw", "sarajevo", "beograd", "porsche", "panamera",
                 "tabak mala", "toni montana", "a gucci", "kol ko", "acme corp"):
        assert not D.is_noise_entry(name), name
    forms = {"bre": {"upos": "INTJ"}, "ajde": {"upos": "INTJ"}, "gucci": {"upos": "PROPN"},
             "beograd": {"upos": "PROPN"}}
    assert D.is_noise_entry("bre ajde", forms) and D.is_noise_entry("bre", forms)
    assert not D.is_noise_entry("bre ajde")                  # INTJ test needs the corpus index
    assert not D.is_noise_entry("bre gucci", forms) and not D.is_noise_entry("beograd", forms)


def test_noise_gazetteer_entries_never_become_name_drops():
    gaz = frozenset({"yeah yeah", "a a a", "ja la", "gucci", "bmw", "sarajevo", "beograd",
                     "porsche", "panamera", "bre ajde"})

    class Idx:                                               # only .forms is read
        forms = {"bre": {"upos": "INTJ", "freq": 90, "lemma": "bre"},
                 "ajde": {"upos": "INTJ", "freq": 80, "lemma": "ajde"}}

    line = "yeah yeah a a a ja la bre ajde gucci bmw sarajevo beograd porsche panamera"
    names = lambda index: {d["span"] for d in D.analyze_line(line, gazetteer=gaz, index=index)
                           if d["kind"] == "name_drop"}
    real = {"gucci", "bmw", "sarajevo", "beograd", "porsche", "panamera"}
    assert names(Idx()) == real                              # INTJ phrase dropped with the index
    assert names(None) == real | {"bre ajde"}                # corpus-free rules only
    cs = {d["span"] for d in D.analyze_line("yeah yeah gucci", gazetteer=gaz)
          if d["kind"] == "code_switch"}
    assert "yeah" in cs                                      # the ad-lib is code-switching, not a name
