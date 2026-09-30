"""Shared fixtures: a tiny hand-written SQLite corpus (no real lyrics)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent          # MAirina_Tucc/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mairina import corpus  # noqa: E402

SCHEMA = """
CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT, target_artist TEXT,
                    genre_cohort TEXT, corpus TEXT NOT NULL DEFAULT 'genius-pro');
CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, ordinal INTEGER, type TEXT);
CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER, text_raw TEXT,
                    text_norm TEXT, word_count INTEGER, syllable_count INTEGER);
CREATE TABLE tokens (id INTEGER PRIMARY KEY, line_id INTEGER, ordinal INTEGER, form TEXT, lemma TEXT,
                     upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
CREATE TABLE entities (id INTEGER PRIMARY KEY, song_id INTEGER, section_id INTEGER, line_id INTEGER,
                       text TEXT, ner_type TEXT);
"""

# Gazetteer fixture rows for devices.name_drop: (song_id, text, ner_type).
# 'Tabak Mala' is a multi-word PER (must match only as a phrase); 'Glava' is a
# PER whose lowercase form is a common NOUN (freq 24 -> suppressed at match
# time); 'Melisa' is majority-PROPN (kept); 'Thameshouse' sits in the English
# corpus and must never appear.
ENTITIES = [(1, "Timbuktu", "LOC"), (2, "Acme Corp", "ORG"), (1, "Panamera", "MISC"),
            (5, "Thameshouse", "LOC"), (1, "Tabak Mala", "PER"), (1, "Glava", "PER"),
            (1, "Melisa", "PER")]

# (song id, cohort, target artist, syllables per line, primary_artist, corpus)
# Song 5 is an English-corpus song (cohort pop): nothing from it may leak into
# the vocabulary, bigrams, gazetteer, targets or lane medians.
SONGS = [(1, "drill_trap", "devito", 10, "Devito x Jala", "genius-pro"),
         (2, "drill_trap", "devito", 10, "Devito", "genius-pro"),
         (3, "pop", "jala", 7, "Senida x Jala", "genius-pro"),
         (4, None, "rasta", 9, "Rasta", "genius-pro"),
         (5, "pop", "englishbard", 3, "English Bard", "gutenberg_pd")]
COMMON = {   # in every song, REPS lines each
    "imaš": ("imati", "VERB"), "lava": ("lava", "NOUN"), "spava": ("spavati", "VERB"),
    "glava": ("glava", "NOUN"), "grade": ("grad", "NOUN"), "pade": ("pasti", "VERB"),
    "sade": ("sada", "ADV"), "da": ("da", "SCONJ"), "me": ("ja", "PRON"), "te": ("ti", "PRON"),
    "je": ("biti", "AUX"), "ne": ("ne", "PART"),
    "nekad": ("nekad", "ADV"), "ponekad": ("ponekad", "ADV"),   # a word and its own extension
    "melisa": ("melisa", "PROPN"),                              # proper noun: never a final slot
    "na": ("na", "ADP"), "ekipa": ("ekipa", "NOUN"),
    "grad": ("grad", "NOUN"), "sef": ("sef", "NOUN"), "kan": ("kan", "NOUN"),
    "zove": ("zvati", "VERB"), "znam": ("znati", "VERB"), "gazda": ("gazda", "NOUN"),
    "pitaj": ("pitati", "VERB"),
    "mala": ("mali", "ADJ"), "niko": ("niko", "PRON"),   # freq 24 common words, never name drops
    # not Serbian orthography (doubled vowel / foreign letter): never an anchor
    "taboo": ("taboo", "NOUN"), "kaboo": ("kaboo", "NOUN"), "boo": ("boo", "NOUN"), "woo": ("woo", "NOUN"),
}
REPS = 6
ONLY = {1: {"snimaš": ("snimati", "VERB")}, 2: {"snimaš": ("snimati", "VERB")},
        3: {"uzimaš": ("uzimati", "VERB"), "separe": ("separe", "NOUN"),
            "senida": ("senida", "NOUN")},       # senida = artist-name token (see SONGS)
        5: {"thelion": ("thelion", "NOUN"), "wanders": ("wander", "VERB"),
            "farway": ("farway", "ADV")}}
# (song id, form, lemma, upos, script): hygiene cases that must be filtered or merged
EXTRA = [(1, "лава", "лава", "NOUN", "cyrillic"), (1, ",", ",", "PUNCT", "latin"),
         (1, "3", "3", "NUM", "latin"), (1, "hm", "hm", "X", "latin"), (1, "$", "$", "SYM", "latin"),
         (1, "lava", "lav", "VERB", "latin"), (2, "Lava", "Lava", "NOUN", "latin")] +     [(1, "trava", "trava", "NOUN", "latin")] * 4        # freq 4: below the anchors floor of 5


# Multi-token lines (song 1). They define which word pairs are attested bigrams:
#   attested: da ekipa (case-folded), sade snimaš, te snimaš, da te, grad sef, sef snimaš, grad te
#   NOT attested: na ekipa; grade snimaš (punctuation between); pade snimaš (cyrillic between);
#                 kan sef; ekipa sade (different lines)
LINES = {1: [["Da", "Ekipa"], ["sade", "snimaš"], ["da", "te", "snimaš"], ["grade", ",", "snimaš"],
             ["pade", "лава", "snimaš"], ["grad", "sef", "snimaš"], ["grad", "te"]],
         5: [["thelion", "wanders"], ["farway", "thelion", "wanders"]]}
LEX = {**COMMON, **{w: v for d in ONLY.values() for w, v in d.items()}}


def _token(form: str):
    if form == ",":
        return (form, form, "PUNCT", "latin")
    if any("\u0400" <= ch <= "\u04ff" for ch in form):
        return (form, form, "NOUN", "cyrillic")
    lemma, upos = LEX[form.lower()]
    return (form, lemma, upos, "latin")


def build_corpus(path: Path) -> Path:
    con = sqlite3.connect(str(path))
    con.executescript(SCHEMA)
    ids = {"line": 0, "tok": 0}

    def add_line(sec, ordinal, syl, toks):
        ids["line"] += 1
        text = " ".join(f for f, *_ in toks)
        con.execute("INSERT INTO lines VALUES (?,?,?,?,?,?,?)",
                    (ids["line"], sec, ordinal, text, text.lower(), len(toks), syl))
        for i, (form, lemma, upos, script) in enumerate(toks):
            ids["tok"] += 1
            con.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?)",
                        (ids["tok"], ids["line"], i, form, lemma, upos, None, 0, script))

    for sid, cohort, artist, syl, primary, corpus_name in SONGS:
        con.execute("INSERT INTO songs VALUES (?,?,?,?,?,?)",
                    (sid, f"song{sid}", primary, artist, cohort, corpus_name))
        con.execute("INSERT INTO sections VALUES (?,?,?,?)", (sid, sid, 1, "verse"))
        words = dict(COMMON, **ONLY.get(sid, {}))
        n = 0
        for form, (lemma, upos) in words.items():
            for _ in range(REPS):
                n += 1
                add_line(sid, n, syl, [(form, lemma, upos, "latin")])
        for toks in LINES.get(sid, []):
            n += 1
            add_line(sid, n, syl, [_token(f) for f in toks])
        for esid, form, lemma, upos, script in EXTRA:
            if esid == sid:
                n += 1
                add_line(sid, n, syl, [(form, lemma, upos, script)])
    for eid, (esid, text, ner) in enumerate(ENTITIES, 1):
        con.execute("INSERT INTO entities VALUES (?,?,?,?,?,?)", (eid, esid, 0, 0, text, ner))
    con.commit()
    con.close()
    return path


@pytest.fixture(scope="session")
def corpus_db(tmp_path_factory) -> Path:
    return build_corpus(tmp_path_factory.mktemp("fixture") / "lyrics.db")


@pytest.fixture(scope="session")
def index(corpus_db, tmp_path_factory):
    return corpus.load_index(corpus_db, tmp_path_factory.mktemp("cache"))


@pytest.fixture()
def data_dir(tmp_path) -> Path:
    return tmp_path / "data"
