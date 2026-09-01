# Journal fragment — Wave 2 Agent D (alignment windowing layer)

> Reserved range **J-050 – J-059**. Merge into `../JOURNAL.md`; do not renumber outside this range.
> Session: 2026-09-01. **Design session, read-only. Nothing was installed; whisperX remains absent**
> (`importlib.util.find_spec("whisperx")` → `None`, verified this session).
> Machine of record: Intel i7-4770, 15.9 GB RAM. Venv: `D:\Projects\Music-AI-Toolshop\.venv` (3.11.9).

---

### J-050 — The "69% coverage" figure is segment-time; true word-level coverage is 49.2% · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session**
**Expected:** the project's headline number — 69.1% coverage, 31% uncovered — describes how much of the
track carries usable word timings. The windowing layer's job was framed as closing that 31%.
**Found:** 69.1% is the union of **segment** spans. Segments contain large internal dead zones with no
word in them at all. Subtracting them, the union of **word** intervals is **122.70 s of 249.48 s =
49.2%**. There is **49.67 s of nominally-covered time that contains no word** — almost as much as the
77 s of uncovered time. The gap the windowing layer must close is **half the track, not a third.**
**Evidence:** first-hand, computed over
`data/toolshop/lyrics/transcripts/borba-015.coverage-A.json` (the 188-word temperature-0 artifact):
```
segment-time coverage  172.37 s = 69.1%
word-time coverage     122.70 s = 49.2%
dead time INSIDE segments 49.67 s
```
The dead time is concentrated in three segments the module docstring already distrusts:
seg 25 is 22.34 s long, holds **3 words**, and has a **19.26 s** internal word gap; seg 16 is 18.79 s,
6 words, **15.59 s** internal gap; seg 15 has a 5.95 s internal gap.
**Consequence:** the windowing spec targets 49.2%, not 69.1%, as the baseline to beat, and the
acceptance criterion is stated in **words receiving a timing**, never in segment-span coverage.
Anywhere "69%" is quoted as coverage it should be labelled *segment-time coverage* — the same
label-ambiguity class as J-018. Two segment-level gaps and seven word-level gaps is a different
problem shape, and the second is the true one.

---

### J-051 — The uncovered time is not silence; it is as loud as the transcribed vocal · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session.** Refutes the design shortcut I intended to use.
**Expected:** the 48.31 s lead-in with zero ASR output was most likely an instrumental intro — a silent
stretch of the vocal stem — and a cheap energy/VAD gate could decide which gaps hold vocal and which
should simply receive no lyric lines.
**Found:** **refuted.** The gaps are loud, at the same level as the regions whisper did transcribe.
Measured on the actual two-pass vocal stem, 100 ms RMS frames:

| region | length | p50 dBFS | p95 dBFS | frac < −60 dBFS |
|---|---|---|---|---|
| intro, **no ASR output** | 48.3 s | −27.5 | **−22.3** | 30.2% |
| dense vocal (48.3–87.0) | 38.7 s | −24.9 | −21.9 | 0.8% |
| dense vocal (99.1–130.0) | 30.9 s | −24.3 | −21.8 | 3.9% |
| gap 87.0–99.1 | 12.0 s | −28.0 | −21.8 | 25.8% |
| gap 141.9–157.5 (inside seg 16) | 15.6 s | −27.6 | −23.5 | 14.1% |
| gap 224.9–244.1 (inside seg 25) | 19.3 s | −33.0 | **−19.6** | 50.3% |
| tail 245.4–249.5 | 4.1 s | −240.0 | −30.3 | 79.5% |

Peak level in the gaps sits **within 1.7 dB** of confirmed vocal, and the 19.3 s gap inside segment 25
is **2.2 dB louder at p95 than any transcribed region in the track.** Only the 4.1 s tail is genuinely
empty.
**Evidence:** first-hand, `soundfile` read of
`data/toolshop/Stemmeca_alatkka/toolshop_stems_borba_hq/Srpskki Istocnicci - Borba 015_(Vocals)_model_bs_roformer_ep_317_sdr_12_(Vocals)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.wav`
(44100 Hz, 249.48 s, 2 ch). Whole file: p50 −25.3 dBFS, p95 −21.4, max −17.6, 16.0% of frames below
−60 dBFS.
**Consequence:** two design consequences, in opposite directions. (1) **Good news:** the missing 51% is
missed vocal, not absent vocal — the lyric lines really do belong in those gaps, so the windowing layer
is attacking real content. (2) **Bad news:** an energy or VAD gate **cannot** be used to decide whether
a gap holds vocal, nor to place window boundaries there. The spec drops the energy-gate idea entirely
and routes the decision through anchors and refusal instead. Caveat kept honest: energy at vocal level
is not proof of *lyrics* — it could be ad-libs, backing vocals, a sample, or separation artefact. That
distinction is not resolvable without listening and is listed under "What Cannot Be Known".

---

### J-052 — One transcript, two alphabets: whisper flips Cyrillic → Latin mid-track · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session**
**Expected:** a transcript decoded with `language="sr"` would come back in one script, so normalisation
could detect the script once per document and transliterate the whole thing.
**Found:** it comes back in **both**. Segment 0 is Latin, segments 1–12 are Cyrillic, segments 13–25 are
Latin. **12 Cyrillic segments, 14 Latin, 0 mixed-within-segment.** The switch happens at 120.22 s with
no change of speaker, language or setting — the same decoder, the same run, the same track.
**Evidence:** first-hand, character-class count per segment over
`borba-015.coverage-A.json` (`[\u0400-\u04FF]` vs `[A-Za-z\u0100-\u017F]`):
```
 0 LAT  cyr=  0 lat= 14  Novo jutro, svice.
 1 CYR  cyr= 37 lat=  0  И свећ, кода нисам присутан...
...
12 CYR  cyr= 35 lat=  0  Сиксирам путању, од проблема чистим главу
13 LAT  cyr=  0 lat= 29  Prva, druga, treća, u crveno, buramska
...
cyrillic segments=12 latin=14 mixed=0
```
**Consequence:** text normalisation in the windowing layer is **per token**, never per document — a
document-level script detector gets this transcript exactly half wrong and silently fails to anchor
either the first or the second half. It also sharpens Wave 1 risk #6 (wildcard-OOV): handing the
Cyrillic half of this transcript to a Latin-vocabulary CTC model would not error, it would wildcard
every character and return confident-looking timings. The spec makes a character-set precondition
check mandatory before any window is submitted, and it must run **after** normalisation, per window.
`cyrtranslit` is already a declared dependency (`pyproject.toml:23`), so this costs nothing but the rule.

---

### J-053 — The recurring hook is transcribed four different ways, and lyric sheets repeat hooks up to 6× · 2026-09-01 · alignment
**Status:** verified — **first-hand, this session**
**Expected:** anchoring ASR output to a known lyric sheet would be mostly an exact-match problem with
fuzzy matching as a fallback for a minority of damaged tokens.
**Found:** exact matching fails in **both directions at once**, and the two failures compound.

*ASR side — the same sung line, four renderings* (transliterated to Latin for comparison):
```
seg 2   fiksiram putanju otprobanja čistim glavu
seg 4   fiksiram putanju otprobanja čistim glavu
seg 12  siksiram putanju od problema čistim glavu
seg 23  riksiram putanju od problema čisti glavu

seg 3   prva druga treća u crveno guram skalu
seg 5   prva druga treća u crveno guram skalu
seg 13  prva druga treća u crveno buramska
seg 24  prva druga treća u cvenu duram skalu
```
The first word alone is rendered `fiksiram` / `siksiram` / `riksiram`. **8 of the 26 segments (31%) are
occurrences of just two lines.**

*Lyric side — hooks are written out in full, repeatedly:*

| sheet | sung lines | most-repeated line |
|---|---|---|
| `ULICNI_KODEKS_ARTIST.md` | 47 | **6×** — "Moraš da poštuješ ulični kodeks" |
| `ABGEZOCKT_LYRICS.md` | 37 | 4× — "Abgezockt in unser'm Stil, Digga," |
| `LAMELA_MIXALL_POPSTARR.md` | 38 | 4× |
| `GEWONENHEIT_DR_KHANS_POPSTARR.md` | 42 | 2× |

**Evidence:** first-hand. ASR renderings read out of `borba-015.coverage-A.json` and transliterated;
lyric repeat counts from a `collections.Counter` over the non-heading, non-SFX lines of each file in
`docs/lyrics/`.
**Consequence:** this is **J-000a in text form.** A fuzzy match against a repeated hook scores high
against *every* occurrence, so similarity carries no information about *which* one — precisely the
0.9173-on-the-wrong-lag failure. The spec therefore makes the anchoring verdict rest on
**`uniqueness_margin`** (best score minus best rival elsewhere in the sheet), never on similarity, and
a window anchored only by repeated-hook matches is graded `contested`, not `anchored`. It also rules
out exact matching outright: `fiksiram` → `siksiram` is edit distance 1 and must still anchor, so the
substitution score is character-level similarity, not equality.

---

### J-054 — `Transcript.source` says `full_mix` on five stem transcripts; the anti-silent-degradation field carries no information · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session**
**Expected:** `toolshop/transcribe.py:18-19` states that `source` is "always recorded" precisely because
transcribing a full mix when a stem was expected is the axis that degrades silently. The stored corpus
should therefore say which input actually ran.
**Found:** it says `full_mix` for **every** transcript in the corpus, including five whose
`source_path` is unambiguously a two-pass `(Vocals)` stem. The one transcript that genuinely *is* a
full mix (`coverage-C`, the deliberate full-mix comparison) is labelled identically. The field
discriminates nothing.
**Evidence:** first-hand, over `data/toolshop/lyrics/transcripts/*.json`:
```
Srpskki_Istocnicci_-_Borba_015__Vocals__model_  source=full_mix   path_is_stem=True
borba-015.coverage-A.json                       source=full_mix   path_is_stem=True
borba-015.coverage-B.json                       source=full_mix   path_is_stem=True
borba-015.coverage-C.json                       source=full_mix   path_is_stem=False
borba-015.large-v3.temp0.json                   source=full_mix   path_is_stem=True
old-config-baseline.large-v3.json               source=full_mix   path_is_stem=True
```
Mechanism: `transcribe_file` initialises `source = "full_mix"` (`toolshop/transcribe.py:367`) and only
promotes it when `find_vocal_stem()` returns a hit. These runs were given the stem path *directly* as
`audio_path`, so `find_vocal_stem` never matched — consistent with J-027, which found `find_vocal_stem`
cannot see the corpus stems. The provenance field then silently kept its **default**.
**Consequence:** generalisable and directly binding on the alignment design — **a provenance field that
can fall back to a default records the default, not the truth.** The windowing layer's provenance
fields (`align_language`, `align_model`, `align_backend`, per-word `origin`) are specified with **no
defaults**: each is required and is set from the value actually used at the point of the decision, and
the writer refuses to serialise a record with any of them unset. Recording is not enough; the record
has to be unable to be wrong. Worth a separate fix on `transcribe.py` — either derive `source` from the
resolved path rather than from whether the *search* succeeded, or drop the default so the caller must
state it.

---

### J-055 — Silence-snapped boundaries cut zero words, but the region that needs them most has no silence to snap to · 2026-09-01 · alignment
**Status:** verified, and my prior expectation **partly refuted** — first-hand, this session
**Expected:** window overlap would be an unnecessary complication: if boundaries are snapped to silence
rather than laid on a fixed grid, no word can straddle a boundary and the boundary-word problem
dissolves by construction.
**Found:** the first half is true and strongly so; the second half is false, and it fails exactly where
it matters. Snapping each nominal boundary to the widest gap within ±5 s:
```
W=20  fixed: 12 bnd, 8 words cut | snapped: 13 win, 0 words cut, len  9.9-27.4 s, 4 anchor-less windows
W=25  fixed:  9 bnd, 4 words cut | snapped: 10 win, 0 words cut, len 20.4-29.9 s, 2 anchor-less windows
W=30  fixed:  8 bnd, 3 words cut | snapped:  9 win, 0 words cut, len  9.9-34.0 s, 1 anchor-less window
```
**Zero words cut at every window length tested**, against 3–8 for a fixed grid. But those are *ASR*
word gaps, and snapping there only guarantees no **known** word is cut — not that no **sung** word is.
Snapping to true audio silence instead is unavailable precisely where it is needed: digital-silence
runs ≥ 0.3 s total 37.4 s over the track, but between **20.22 s and 96.00 s there is not a single
silent run ≥ 0.6 s** — 76 continuous seconds of energy, of which whisper transcribed nothing before
48.31 s. A boundary placed anywhere in 20.2–48.3 s is placed blind and may cut a sung word in half.
**Evidence:** first-hand. Boundary/cut counts computed over `borba-015.coverage-A.json`'s 188 word
intervals; silence runs from 20 ms RMS frames of the vocal stem at a −60 dBFS threshold:
```
digital-silence runs >= 0.30 s: 20, total 37.4 s
runs >= 0.6 s:  0.00-7.44 | 10.26-14.24 | 15.98-17.64 | 19.60-20.22 | 96.00-98.74 | ...
longest run inside intro 0-48.31: 7.44 s (at 0.00)
```
**Consequence:** the spec adopts **both** mechanisms rather than choosing: boundaries are snapped
(audio silence first, ASR word gap second, arithmetic last, and **which one was used is recorded per
boundary**), *and* each window carries a 2.5 s aligned context margin on each side so a word cut by a
blind boundary survives intact in the neighbouring window and can be arbitrated. Overlap costs ~20% more
compute at W=25 and is the only protection available in unanchored regions. It also produces the
recommendation of **W=25 s**: it is the only length tested whose windows all land in 20–30 s (20.4–29.9),
where W=20 and W=30 both emit a 9.9 s runt.

---

### J-056 — The lyric Markdown family is not a lyric format: production directions outnumber sung lines in 3 of 4 sheets · 2026-09-01 · lyrics
**Status:** verified — **first-hand, this session.** Extends J-016.
**Expected:** J-016 established that `lyrics.db` holds none of our own material, so the lyric side must
read the loose Markdown in `docs/lyrics/`. The implicit assumption was that those files are lyric
sheets — text lines plus `[Chorus]` / `[Verse N]` markers — and that a simple parser would do.
**Found:** they are production documents that contain lyrics. Counting sung lines against bracketed
sound-effect / ad-lib directions of the form `([night-hum] - mmmmmm)`:

| file | sung lines | SFX/ad-lib directions | section headers |
|---|---|---|---|
| `ULICNI_KODEKS_ARTIST.md` | 47 | **52** | 5 |
| `GEWONENHEIT_DR_KHANS_POPSTARR.md` | 42 | **41** | 3 — *and none is a section* |
| `LAMELA_MIXALL_POPSTARR.md` | 38 | 35 | 6 |
| `ABGEZOCKT_LYRICS.md` | 37 | 0 | 5 |

Three further shape problems. **(a)** `GEWONENHEIT`'s three bracket markers are
`[niederer Gesangston]`, `[Vinyl-Scratch / cut]`, `[Stop-Start Effekt 1/8 Beat]` — vocal and production
directions, not sections, so a parser keying on `[Chorus]`/`[Verse N]` extracts **zero** structure from
it. **(b)** `KASPER_DRILL_GERMAN.md` carries mix-engineering directives in the same bracket syntax —
`[MAXIMUM:all peak,808 heaviest,drums full]`, `[VOX CHAIN]`, `[MIX PHILOSOPHY]`. **(c)**
`ULICNI_KODEKS_ARTIST.md` and `ULICNI_KODEKS_GERMAN_TRANSLATION.md` are the **same song in two
languages** with identical marker counts, and the German one is a 197-line analysis document with 20
markdown headings; nothing in either filename or content says which matches a given audio file.
**Evidence:** first-hand, regex classification over `docs/lyrics/*.md`
(SFX `^\s*\(\s*\[.+?\]\s*-.*\)\s*$`, section `^\s*\[[^\]]{1,40}\]\s*$`), counts as tabulated above.
**Consequence:** the naive ingestion — "read the .md, drop headings, keep the rest" — would feed the
forced aligner **roughly 50% text that is never sung**, and CTC always returns a path, so it would
place `boom-boom-boom` somewhere in the audio with a confident-looking timing. The spec makes lyric
ingestion an explicit, tested stage with its own refusal: SFX directions are stripped and **retained as
metadata rather than discarded** (they are real production content, just not alignable), section
markers are treated as advisory and never load-bearing, and a sheet whose sung-line count falls outside
a plausible band for its track length is refused rather than aligned. The audio join key J-016 named as
missing is still missing, and now has a second requirement: a *language* tag, because two of these
files are translations of each other.

---

### J-057 — Wave 1's 10 GB OOM figure assumes eager attention; the installed stack supports SDPA, so the memory wall is a worst case · 2026-09-01 · alignment
**Status:** verified in part, and **it weakens an argument I was relying on** — first-hand, this session
**Expected:** from J-015 and the Wave 1 spec: whole-track alignment is ruled out because a materialised
`[1, 16, n, n]` attention tensor at n = 12,474 frames is ≈ 10 GB on a 15.9 GB machine. I expected to
cite that as the settled reason windowing is mandatory.
**Found:** the arithmetic is right but its premise is conditional. `[1,16,12474,12474]` fp32 is indeed
622 MB per head and **9.96 GB** across 16 — but only if the matrix is *materialised*. The installed
`transformers` **5.14.1** routes Wav2Vec2 attention through the pluggable attention interface and
declares SDPA support, and `torch.nn.functional.scaled_dot_product_attention` exists in the installed
torch 2.6.0+cpu. A memory-efficient SDPA path never materialises the full matrix, so the 10 GB figure
is an **upper bound on the eager path**, not a certainty. Separately, the FLOP claim is overstated:
attention at n = 12,474 is ≈ 1.53e13 against a linear term of ≈ 7.86e12 for 249.48 s — attention is
**~1.95× the linear term**, not "dwarfing" it, and the two are equal only at n ≈ 6,400 frames
(**≈ 128 s** of audio).
**Evidence:** first-hand.
```
transformers 5.14.1 ; torch 2.6.0+cpu ; sdpa available: True
Wav2Vec2PreTrainedModel._supports_sdpa      True
modeling_wav2vec2 uses ALL_ATTENTION_FUNCTIONS  True
```
Arithmetic recomputed from Wave 1's own formulae: linear ≈ `2 × 315e6 × 50` = 3.15e10 FLOP per audio
second; attention ≈ `n² × 1024 × 24 × 2 × 2`; crossover at `n × 98304 = 6.3e8` → n ≈ 6409 → 128 s.
**Not verified:** which attention implementation whisperX 3.4.5 actually selects at load time, and
what `transformers` version a sidecar venv would resolve to. whisperX is absent and was not installed.
**Consequence:** the recommendation is unchanged but **the stated reason had to change**, which is the
point of recording it. Windowing is justified primarily by *assignment granularity and error
containment* — a 25 s window is the unit at which a misassignment can be caught and refused, and the
unit that keeps one bad assignment from poisoning a whole track — and only secondarily by the quadratic
term, which is real but modest below ~128 s. The `--max-window-seconds` assertion stays in the adapter
regardless: it is free, and if the eager path *is* selected the 10 GB wall is real. A future session
must not quote "10 GB, therefore window" as settled fact; it is conditional on the attention
implementation, which nobody has checked at runtime.

---

### J-058 — No track has both a transcript and a lyric sheet; the design cannot be validated end-to-end on existing data · 2026-09-01 · alignment
**Status:** verified — **first-hand, this session**
**Expected:** with real transcripts in `data/toolshop/lyrics/transcripts/` and real lyrics in
`docs/lyrics/`, at least one track would have both, giving the windowing layer a first honest test case.
**Found:** none does. Every transcript in the corpus is the **same track** — `Srpskki Istocnicci -
Borba 015` — in six decode configurations. No file in `docs/lyrics/` is that song: the sheets are
`ABGEZOCKT`, `GEWONENHEIT`, `KASPER`, `LAMELA`, `MILA_MOJA_MAJKO`, `ULICNI_KODEKS` (×2). The
intersection is **empty**.
**Evidence:** first-hand directory listings —
`data/toolshop/lyrics/transcripts/` holds 6 JSON files, all `borba-015`/`Srpskki_Istocnicci_-_Borba_015`
variants; `docs/lyrics/` holds 7 lyric-bearing `.md` files, none of them Borba.
**Consequence:** the windowing layer's *assignment* logic can be tested exhaustively against a mocked
aligner using the real borba-015 transcript plus a **synthetic** lyric sheet — that is the whole test
plan and it is worth building now. What **cannot** be done today, at any price, is the measurement that
decides the lane: whether anchors found against a *true* sheet land in the right places. That needs one
track with both, and producing it is a prerequisite that has nothing to do with whisperX — it is the
same missing ingestion path J-016 named. **Cheapest unblock: transcribe one track that already has a
sheet** (`ABGEZOCKT`, `ULICNI_KODEKS`), rather than writing a sheet for Borba. Recorded so a future
session does not discover mid-run that its acceptance test has no input.
