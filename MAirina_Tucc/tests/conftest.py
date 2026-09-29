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
CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT, target_artist TEXT, genre_cohort TEXT);
CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, ordinal INTEGER, type TEXT);
CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER, text_raw TEXT,
                    text_norm TEXT, word_count INTEGER, syllable_count INTEGER);
CREATE TABLE tokens (id INTEGER PRIMARY KEY, line_id INTEGER, ordinal INTEGER, form TEXT, lemma TEXT,
                     upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
"""

# (song id, cohort, target artist, syllables per line, primary_artist as Genius spells it)
SONGS = [(1, "drill_trap", "devito", 10, "Devito x Jala"), (2, "drill_trap", "devito", 10, "Devito"),
         (3, "pop", "jala", 7, "Senida x Jala"), (4, None, "rasta", 9, "Rasta")]
COMMON = {   # in every song, REPS lines each
    "imaš": ("imati", "VERB"), "lava": ("lava", "NOUN"), "spava": ("spavati", "VERB"),
    "glava": ("glava", "NOUN"), "grade": ("grad", "NOUN"), "pade": ("pasti", "VERB"),
    "sade": ("sada", "ADV"), "da": ("da", "SCONJ"), "me": ("ja", "PRON"), "te": ("ti", "PRON"),
    "je": ("biti", "AUX"), "ne": ("ne", "PART"),
    "nekad": ("nekad", "ADV"), "ponekad": ("ponekad", "ADV"),   # a word and its own extension
    "melisa": ("melisa", "PROPN"),                              # proper noun: never a final slot
    "na": ("na", "ADP"), "ekipa": ("ekipa", "NOUN"),
    "grad": ("grad", "NOUN"), "sef": ("sef", "NOUN"), "kan": ("kan", "NOUN"),
    # not Serbian orthography (doubled vowel / foreign letter): never an anchor
    "taboo": ("taboo", "NOUN"), "kaboo": ("kaboo", "NOUN"), "boo": ("boo", "NOUN"), "woo": ("woo", "NOUN"),
}
REPS = 6
ONLY = {1: {"snimaš": ("snimati", "VERB")}, 2: {"snimaš": ("snimati", "VERB")},
        3: {"uzimaš": ("uzimati", "VERB"), "separe": ("separe", "NOUN"),
            "senida": ("senida", "NOUN")}}       # senida = artist-name token (see SONGS)
# (song id, form, lemma, upos, script): hygiene cases that must be filtered or merged
EXTRA = [(1, "лава", "лава", "NOUN", "cyrillic"), (1, ",", ",", "PUNCT", "latin"),
         (1, "3", "3", "NUM", "latin"), (1, "hm", "hm", "X", "latin"), (1, "$", "$", "SYM", "latin"),
         (1, "lava", "lav", "VERB", "latin"), (2, "Lava", "Lava", "NOUN", "latin")] +     [(1, "trava", "trava", "NOUN", "latin")] * 4        # freq 4: below the anchors floor of 5


# Multi-token lines (song 1). They define which word pairs are attested bigrams:
#   attested: da ekipa (case-folded), sade snimaš, te snimaš, da te, grad sef, sef snimaš, grad te
#   NOT attested: na ekipa; grade snimaš (punctuation between); pade snimaš (cyrillic between);
#                 kan sef; ekipa sade (different lines)
LINES = {1: [["Da", "Ekipa"], ["sade", "snimaš"], ["da", "te", "snimaš"], ["grade", ",", "snimaš"],
             ["pade", "лава", "snimaš"], ["grad", "sef", "snimaš"], ["grad", "te"]]}
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
        con.execute("INSERT INTO lines VALUES (?,?,?,?,?,?,?)",
                    (ids["line"], sec, ordinal, "x", "x", len(toks), syl))
        for i, (form, lemma, upos, script) in enumerate(toks):
            ids["tok"] += 1
            con.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?)",
                        (ids["tok"], ids["line"], i, form, lemma, upos, None, 0, script))

    for sid, cohort, artist, syl, primary in SONGS:
        con.execute("INSERT INTO songs VALUES (?,?,?,?,?)", (sid, f"song{sid}", primary, artist, cohort))
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
