"""Ijekavica detection: flag corpus forms that are not ekavian Serbian.

Suggestions only — the user picks the dialect, the tool never writes lines.
Each flag carries a reason string so tests and audits can see why.

Rules, first match wins:

- ``lexicon``    — the form or its majority lemma sits in
  ``lexicons/dialect_pairs.csv``'s ijekavica column.
- ``cluster``    — ``mje vje pje tje gje`` never occur in standard ekavica
  (every corpus hit verified ijekavian).
- ``lje-initial`` — a word starting ``lje`` is always ijekavian (ljeto,
  ljepota); corpus lemmatizers already normalize those to ``le…`` anyway.
- ``transform``  — an ijekavian marker rewritten to its ekavian counterpart
  lands on an attested, more frequent form, and the pair shares a lemma
  (direct, or an uninflected form's lemma rewrites to the candidate's lemma:
  ``dio`` -> deo, ``poslje`` -> posle, ``sjećanje`` -> sećanje). Markers:
  ``dje sje lje nje rje bje zje`` plus ``io`` -> ``eo`` anywhere in the word
  (the ``-io`` participle family: volio -> voleo, vidio -> video, htio ->
  hteo). The same-lemma guard is what keeps ``odjebati``/``odjednom``
  (``odebati``/``odednom`` unattested), ``izjebati``, ``objekat``,
  ``debilu`` (debil != debeo), ``gorila``, ``žile``, ``sila``, ``gazila``,
  ``radio``/``nosio``/``mislio`` (``-eo`` twin unattested — plain ``-io`` is
  ekavian too), ``nje``/``njegov``, ``bolje``/``dalje``/``šalje`` (counterpart
  exists but different lemma or rarer) — and ``kamenje``/``pitanje``
  (``-anje`` nouns, no attested twin).
- ``ije`` — an internal ``ije`` whose ``ije -> e`` rewrite is attested and
  more frequent (uvijek -> uvek, vrijeme -> vreme). Word-final ``ije`` is
  skipped: that is the ``-ija`` plural/vocative ending (``zmije``,
  ``tehnologije``, ``ranije``, ``krije``, ``nije``), not a jat reflex. No
  lemma gate here: ``i+je`` words like ``piješ`` survive because the ``peš``
  counterpart loses on frequency, and ``prije-`` compounds whose ``ije``
  really is the jat reflex (``prijedlog``, ``prijetnja``) flag correctly.
- ``lemma`` — the form's majority lemma is itself flagged (``sjeni`` via
  ``sjena``, ``bježe`` via ``bježati``, ``snježna`` via ``snježan``).

Frequencies and lemmas come from ``corpus.Index.forms``; nothing here reads
the database. ``ijekavian()`` maps form -> reason for tests and debugging;
callers normally take ``set(ijekavian(forms))``.
"""

from __future__ import annotations

from mairina import rules

STRONG = ("mje", "vje", "pje", "tje", "gje")
# 3-letter marker -> ekavian rewrite ('ije' drops 'ij'->'e', the rest keep the first consonant)
_TRANSFORMS = {"ije": "e", "dje": "de", "sje": "se", "lje": "le",
               "nje": "ne", "rje": "re", "bje": "be", "zje": "ze"}
_LEMMA_GATE = frozenset(_TRANSFORMS) - {"ije"}  # 'ije' is unambiguous: dominance alone suffices


def _transforms(w: str, final_ije: bool = False):
    """(marker, ekav candidate) pairs for marker positions inside ``w``.

    Internal ``ije`` only unless ``final_ije`` — a word-final ``ije`` is the
    -ija inflection, not jat, except when the corpus lemma itself is the ``e``
    rewrite (``prije`` lemmatized to ``pre``). The ``io -> eo`` rewrite is
    offered for any ``io`` bigram (past participles and their declensions:
    volio/voliom/vidio/htio); borrowing ``-ion`` words (milion, akcion)
    produce unattested candidates and drop out, ``-iti`` verbs (nosio, radio,
    mislio) have no attested ``-eo`` twin, and coincidence pairs (krio->kreo,
    silo->selo, mrtvi) fail the same-lemma gate.
    """
    for i in range(len(w) - 1):
        tri = w[i:i + 3]
        if tri in _TRANSFORMS and (final_ije or tri != "ije" or i + 3 < len(w)):
            yield tri, w[:i] + _TRANSFORMS[tri] + w[i + 3:]
        elif w[i:i + 2] == "io" and i > 0:
            yield "io", w[:i] + "eo" + w[i + 2:]


def _ekav_variants(w: str) -> set[str]:
    return {cand for _, cand in _transforms(w)}


def _lemma_of(w: str, forms: dict) -> str:
    return (forms.get(w) or {}).get("lemma") or w


def _same_lemma(w: str, cand: str, forms: dict) -> bool:
    """The counterpart is a dialect twin: same lemma, the candidate is already
    the corpus lemma (``hljeb`` -> hleb), or an uninflected form whose own
    lemma rewrites to the candidate's lemma (``dio`` -> deo, ``poslje`` ->
    posle). The ``lw == w`` proviso keeps inflected ekavian words like
    ``silo`` (sila) and ``milo`` safe.
    """
    lw, lc = _lemma_of(w, forms), _lemma_of(cand, forms)
    if lc == lw or cand == lw:
        return True
    return lw == w and lc in _ekav_variants(lw)


def _reason(w: str, forms: dict, lex: frozenset) -> str | None:
    """Why ``w`` is ijekavian, or None. ``w`` need not be a corpus form itself
    (called on lemmas too; an absent form simply has freq 0, which makes the
    dominance check vacuous — the lemma gate still applies)."""
    lem = _lemma_of(w, forms)
    if w in lex or lem in lex:
        return "lexicon"
    for s in STRONG:
        if s in w:
            return f"cluster:{s}"
    if w.startswith("lje"):
        return "lje-initial"
    fw = (forms.get(w) or {}).get("freq", 0)
    for kind, cand in _transforms(w, final_ije=True):
        if cand != w and cand == lem:
            # corpus lemmatizer normalized the spelling (djelimično -> delimično)
            return f"{kind}->lemma:{cand}"
        e = forms.get(cand)
        if e is None:
            continue
        if kind == "ije":
            # a word-final ije is -ija inflection, never jat — it may only
            # flag via the lemma rule above (prije -> pre)
            if cand == w[:-3] + "e":
                continue
            if e["freq"] > fw:
                return f"ije->e:{cand}"
        elif _same_lemma(w, cand, forms):
            # attested same-lemma twin: a real dialect pair regardless of
            # which spelling the corpus happens to prefer (vidjeti -> videti)
            return f"{kind}->{cand}"
    return None


def ijekavian(forms: dict) -> dict[str, str]:
    """{form: reason} for every corpus form that reads ijekavian.

    ``forms`` is ``corpus.Index.forms`` (or any ``{word: {lemma, freq}}``).
    A form whose majority lemma is flagged inherits the flag one level deep —
    that catches inflections the markers miss (``sjeni`` under ``sjena``,
    ``snježna`` under ``snježan``, ``sjetio`` under ``sjetiti``).
    """
    lex = rules.load_lexicons()["ijekavica"]
    flagged: dict[str, str] = {}
    for w in forms:
        if r := _reason(w, forms, lex):
            flagged[w] = r
    for w, e in forms.items():
        if w in flagged:
            continue
        lem = e.get("lemma") or w
        if lem == w:
            continue
        if lem in flagged:
            flagged[w] = "lemma:" + flagged[lem]
        elif r := _reason(lem, forms, lex):
            flagged[w] = "lemma:" + r
    return flagged
