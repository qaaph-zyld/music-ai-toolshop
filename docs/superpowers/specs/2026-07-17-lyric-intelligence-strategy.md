# Lyric Intelligence Strategy — Learning From the Pros

**Date:** 2026-07-17 · **Lane:** T5/T6 intersection (Library Intelligence × Creation Bridge)
**Corpus trigger:** Buba Corelli / Jala Brat / Coby corpus (2026-07-16). Companion to roadmap v2
and the OSS integration map. **Gated on M1c-final** (corpus must live in `D:\MusicData\toolshop\lyrics\` first).
**Correction 2026-07-17:** verified corpus size is **386 unique songs** (2,704 sections); the "415"
figure was index inflation from the extractor dedup bug (M1c Task 2). L1 executable plan:
`plans/2026-07-17-t5l1-lyrics-db-foundation.md`.

---

## 1. Long-Term Goal

**Turn professional lyrics into three assets:**
1. **Craft knowledge** — measurable, explicit answers to "how do the pros actually rhyme, structure, and theme their songs?" (not vibes: distributions and per-artist fingerprints).
2. **Writing tools** — a corpus-powered rhyme engine (feeds the MAirina "Pro Rimer" PRD Phase 1), phrase/theme banks, and generation briefs for Suno.
3. **A quality bar** — score any draft (own pen or Suno output) against pro baselines: rhyme density, multis, hook craft, vocabulary, originality.

End state: before writing or generating a song, you consult the fingerprint of the style you're aiming at;
after drafting, the scorer tells you objectively where you fall short of the pros.

## 2. The Serbian Advantage (why this is unusually cheap for us)

Serbian orthography is nearly phonetic — text ≈ phonemes. The state-of-the-art rap-rhyme method
(Malmi's **Raplyzer**: convert to phonemes → find matching **vowel sequences** ignoring consonants →
rhyme length + "rhyme factor" density) needed eSpeak for English; for Serbian we can extract vowel
skeletons **directly from normalized text** and use espeak-ng (`sr` voice, Latin+Cyrillic) via phonemizer
only for validation. Assonance and multisyllabic rhymes — the heart of Balkan rap craft — become
string operations. German (CrhymeTV lane, later) is not phonetic and will need phonemizer properly.

## 3. Corpus Assets & Expansion

| Corpus | Size | Role |
|---|---|---|
| Buba/Jala/Coby (Genius) | 386 songs (verified) | **The pro reference** — v1 target |
| lyrics_research pilot | 10+10 songs, analysis+style_guide reports | Proven methodology to scale; port its metrics |
| Suno library lyrics | 2,633 (AI-generated) | "Own baseline" for gap analysis (mixed quality — label as such) |
| Own written drafts | growing | The thing being improved; scorer input |
| Expansion v2 | +regional artists (extend extractor list); German corpus from the 222 CrhymeTV artists | Same pipeline, new fingerprints |

## 4. Pipeline: NORMALIZE → ANNOTATE → MINE → PROFILE → COMPARE → APPLY

```
lyrics files → lyrics.db (SQLite/DuckDB: songs, sections, lines, tokens, rhymes, topics, metrics)
```

| Stage | What | Tech (verified 2026-07-17) | Verdict |
|---|---|---|---|
| Normalize | Script unification (cyrtranslit), Genius section markers (`[Refren]`, `[Strofa N]`, …) → song/section/line schema, lyrics.db | cyrtranslit + stdlib | 🔨 BUILD (small) |
| Annotate | Lemma/POS/NER tuned for **non-standard internet Serbian** (rap slang!) — sr lemma acc. 97.89; slang lexicon = systematic OOV mining | **CLASSLA** (pip, CPU) | ➕ INTEGRATE |
| Mine: rhyme | Vowel-skeleton rhyme miner: end + internal rhymes, multi-length (2/3/4+ syllable chains), Malmi rhyme factor, scheme inference (AABB/ABAB/chains), dominant vowel-pair patterns | Raplyzer method, our implementation; espeak-ng `sr` for validation sample | 🔨 BUILD (flagship) |
| Mine: structure | Section inventories, hook-repetition patterns, lines/section, syllables/line (vowel counting), where hooks land | stdlib on lyrics.db | 🔨 BUILD (small) |
| Mine: themes | Topic clusters per section (not whole songs — sharper topics), per-artist theme mix, evolution over years | **BERTopic + paraphrase-multilingual-MiniLM** (CPU; method published for Serbian short text) | ➕ INTEGRATE |
| Profile | Per-artist fingerprint JSON + human report: rhyme craft, structure playbook, lexical stats (TTR, slang rate, loanwords, NER brands/places), theme mix | DuckDB views + report renderer | 🔨 BUILD |
| Compare | Own/Suno drafts through the same pipeline → gap dashboard ("rhyme factor 1.2 vs Jala 1.9; multis rare; hook repetition low") | same stack + Datasette | 🔨 BUILD |
| Apply | (a) **Rimer DB**: attested pro rhyme pairs ranked by usage → MAirina PRD Phase 1 engine; (b) **brief generator**: structure+rhyme-scheme+theme targets formatted for Suno; (c) **draft scorer CLI** `toolshop lyrics score draft.txt --vs jala-brat` incl. **originality check** (n-gram overlap vs corpus — never plagiarize the reference) | toolshop CLI + MAirina | 🔨 BUILD |

LLM role: Claude in strategy/IDE sessions for *qualitative* craft annotation (narrative devices, wordplay
taxonomy on ~10 exemplar songs) and for consuming fingerprints when drafting briefs. Embeddings in
lyrics.db double as retrieval ("show me how Jala opens choruses"). No LLM inside the batch pipeline.

## 5. Phases (session-sized; start after M1c-final)

- **L1 Foundation (1–2 sessions):** normalize → lyrics.db; port lyrics_research metrics (word counts, TTR)
  to full 386; syllable counter + tests. *Exit: `toolshop lyrics stats` over the corpus; DB browsable in Datasette.*
- **L2 Rhyme Miner (1–2 sessions):** vowel-skeleton engine + rhyme factor + multis + schemes; validate on
  20 hand-checked rhyme pairs + espeak-ng sample; per-artist rhyme tables. *Exit: rhyme fingerprint per artist, sanity-checked by ear.*
- **L3 Language & Themes (1–2 sessions):** CLASSLA annotation; slang lexicon; BERTopic themes per section.
  *Exit: theme atlas + slang lexicon in DB.*
- **L4 Fingerprints & Gap Report (1 session):** artist profiles; run Suno-lyrics corpus through pipeline;
  first own-vs-pro gap report. *Exit: `reports/pro_fingerprints.md` + `reports/gap_report.md`.*
- **L5 Apply (2 sessions):** rimer DB export + MAirina hookup; brief generator; draft scorer CLI with
  originality check. *Exit: write one real song using the tools; A/B the Suno brief against a naive prompt.*
- **L6 Expand (later):** more regional artists; German corpus (CrhymeTV artists via the proven extractor)
  with phonemizer-de; ties into H3 flow analyzer (whisperX word timings × beat grid) so text craft meets
  delivery craft.

## 6. Governance

- Corpus = copyrighted study material: lives in `D:\MusicData`, never committed, never republished;
  reports/fingerprints contain **statistics and at most short attributed quotes**, not lyric dumps.
- Generated songs must pass the originality check (no verbatim pro lines).
- All new deps (classla, cyrtranslit, bertopic, sentence-transformers, umap/hdbscan already mapped) get
  license-ledger entries per integration-map policy.

## 7. Success Criteria (what "we learned from the pros" means)

1. For each artist: a one-page fingerprint a producer can act on (rhyme craft, structure playbook, themes).
2. The gap report changes how you write: at least 3 concrete, measured craft adjustments.
3. Rimer suggests corpus-attested rhymes, ranked by pro usage — and it measurably beats the dictionary version.
4. A Suno brief built from fingerprints produces audibly closer-to-style results than a naive prompt (A/B kept).
