# Alignment windowing layer — design + test plan

> Written 2026-09-01 by Wave 2 Agent D. **Design only. Nothing was installed; whisperX remains absent**
> (`importlib.util.find_spec("whisperx")` → `None`, checked this session). No implementation code was
> written. Every number labelled *measured* was produced first-hand this session from
> `data/toolshop/lyrics/transcripts/borba-015.coverage-A.json` and the vocal stem it points at; every
> number labelled *derived* is arithmetic and must not be quoted as a measurement (J-000g).
>
> Builds on `specs/2026-09-01-forced-alignment-feasibility.md` (Wave 1 Agent A) and journal entries
> **J-015** (whisperX refines a segmentation, it does not produce one), **J-016** (`lyrics.db` holds no
> own material and no audio join key), **J-000a/J-000b** (margin, not confidence; a flag is not an
> answer), **J-000d** (`Word.probability` is certainty, not correctness), **J-000f** (the 69% ceiling is
> the model, not the plumbing), **J-000g** (short inputs exaggerate fixed overhead).
>
> New findings from this session are **J-050 – J-058** (`journal_inbox/agentD.md`). Four of them change
> the design materially and are flagged inline.

---

## Design Summary

The windowing layer sits between `toolshop/transcribe.py` and a whisperX alignment backend. It takes
**audio + an ASR transcript + a known lyric sheet** and produces **windows of ~25 s, each carrying the
run of lyric lines believed to be sung inside it**, ready to hand to `whisperx.align()` one window at a
time. It does not itself align anything.

Five decisions carry the design.

**1. The layer assigns lines to *windows*, not times to *lines*.** A window's job is to supply
`SingleSegment(text, start, end)`; CTC then does the within-window placement and produces the word
timings. So the assignment only has to be right at ~25 s granularity, not at word granularity. This is
the whole reason the approach is tractable — and it is the reason the failure mode is *containable*: a
wrong assignment damages one window, not the track.

**2. Ordering is enforced by construction, not by detection.** Anchoring is a monotone dynamic-programming
alignment of the ASR token stream against the lyric token stream. A monotone path cannot represent a
reordering, so "an assignment that reorders lines" is not something the layer detects and rejects — it is
something the layer **cannot emit**. What remains to be judged is quality, not order.

**3. The verdict rests on a margin, never on a score.** Measured (J-053): the recurring hook in
borba-015 is transcribed four different ways, and our lyric sheets write hooks out up to **6×**. A fuzzy
match against a repeated hook scores high against *every* occurrence. Similarity therefore says nothing
about *which* occurrence — exactly J-000a's 0.9173-on-the-wrong-lag. Every anchor carries a
`uniqueness_margin`, and a window anchored only by repeated-hook matches is graded `contested`, not
`anchored`.

**4. Where it cannot know, it refuses rather than interpolates.** A run of lyric lines bounded by anchors
on **both** sides is placed by syllable-proportional interpolation and marked `interpolated`. A run
bounded on **one** side — the head and tail of the track — is **not placed at all** by default. It is
emitted as an `unanchored_span` naming the line range and the time range, with no timings. This is
J-000b applied properly: rather than emit a flagged wrong answer, emit the span and withhold the answer.

**5. The two outputs are made structurally different.** Wave 1's central risk is that a silent fallback
to ASR timings produces a file "structurally identical" to an aligned one, so only a guard can tell them
apart. The stronger fix is to break the symmetry: every emitted `Word` carries a required
`origin` field (`"asr"` | `"aligned"`), with **no default**. A fallback then cannot masquerade as a
result, and `--require-alignment` becomes a cheap assertion over a field that already exists rather than
the only line of defence. Measured justification (J-054): `Transcript.source` — the field
`transcribe.py` introduced for exactly this purpose — reads `full_mix` on **five stem transcripts**,
because it has a default and the default is what got recorded. **A provenance field that can fall back
to a default records the default, not the truth.**

### The baseline this has to beat is 49.2%, not 69.1%

**Measured, first-hand (J-050).** The project's headline "69% coverage / 31% uncovered" is the union of
**segment** spans. Segments contain large internal dead zones:

```
segment-time coverage  172.37 s / 249.48 s = 69.1%
word-time coverage     122.70 s / 249.48 s = 49.2%
dead time INSIDE segments  49.67 s
```

Segment 25 is 22.34 s long, holds **3 words**, and contains a **19.26 s** stretch with no word in it.
Segment 16 is 18.79 s with a **15.59 s** internal gap. Counting properly there are **nine** word-level
silent gaps > 2 s, not the four or five visible at segment level:

```
   0.00 ->  48.31   48.31 s   (head — no ASR output at all)
  87.05 ->  99.08   12.03 s
 130.00 -> 135.95    5.95 s   (inside segment 15)
 141.87 -> 157.46   15.59 s   (inside segment 16)
 181.90 -> 185.77    3.87 s
 199.33 -> 202.91    3.58 s   (inside segment 22)
 206.17 -> 212.22    6.05 s
 224.86 -> 244.12   19.26 s   (inside segment 25)
 245.42 -> 249.48    4.06 s   (tail)
```

**The gap to close is half the track.** Two consequences: the acceptance criterion is stated in *words
that receive a timing*, never in segment-span coverage; and a design that only fills the inter-segment
gaps solves less than half the problem, because 49.67 s of the deficit is *inside* segments the ASR
claims to cover. The layer must therefore be free to re-window across segment interiors — it treats ASR
segments as evidence, not as structure.

### And the gaps are loud

**Measured, first-hand (J-051), and it refuted the shortcut I intended to take.** I expected the 48.31 s
lead-in to be an instrumental intro with a silent vocal stem, and expected a cheap energy/VAD gate to
decide which gaps hold vocal. Both wrong:

| region | length | p50 dBFS | p95 dBFS | frac < −60 dBFS |
|---|---|---|---|---|
| head, **no ASR output** | 48.3 s | −27.5 | **−22.3** | 30.2% |
| dense vocal (48.3–87.0) | 38.7 s | −24.9 | −21.9 | 0.8% |
| dense vocal (99.1–130.0) | 30.9 s | −24.3 | −21.8 | 3.9% |
| gap 87.0–99.1 | 12.0 s | −28.0 | −21.8 | 25.8% |
| gap 224.9–244.1 (inside seg 25) | 19.3 s | −33.0 | **−19.6** | 50.3% |
| tail 245.4–249.5 | 4.1 s | −240.0 | −30.3 | 79.5% |

Peak level in the gaps sits within **1.7 dB** of confirmed vocal, and the 19.3 s gap inside segment 25
is **2.2 dB louder at p95** than anything the ASR transcribed. Only the 4.1 s tail is genuinely empty.

Good news: the missing 51% is *missed* vocal, not *absent* vocal, so the lyric lines really do belong in
those gaps and the layer is attacking real content. Bad news: **an energy gate cannot be used** to decide
whether a gap holds vocal, nor to place a boundary inside one. The energy-gate idea is dropped from this
design entirely; the decision routes through anchors and refusal instead.

---

## Window Sizing

### The arithmetic

From Wave 1's own figures: the alignment model is XLS-R-300M (~315M params, 24 layers, hidden 1024,
16 heads), running fp32 at ~50 frames/s. For a window of `W` seconds, `n = 50W` frames:

- linear-layer cost ≈ `2 × 315e6 × 50 × W` = **`6.3e8 · n`** FLOP
- self-attention cost ≈ `n² × 1024 × 24 × 2 × 2` = **`98304 · n²`** FLOP
- eager attention tensor `[1, 16, n, n]` fp32 = **`64 · n²`** bytes

| W (s) | n frames | eager attn tensor | attn FLOP | linear FLOP | attn / linear |
|---:|---:|---:|---:|---:|---:|
| 10 | 500 | 16 MB | 2.5e10 | 3.2e11 | 8% |
| 15 | 750 | 36 MB | 5.5e10 | 4.7e11 | 12% |
| **20** | 1 000 | 64 MB | 9.8e10 | 6.3e11 | **16%** |
| **25** | 1 250 | 100 MB | 1.5e11 | 7.9e11 | **19%** |
| **30** | 1 500 | 144 MB | 2.2e11 | 9.5e11 | **23%** |
| 40 | 2 000 | 256 MB | 3.9e11 | 1.3e12 | 31% |
| 60 | 3 000 | 576 MB | 8.9e11 | 1.9e12 | 47% |
| 128 | 6 409 | 2.6 GB | 4.0e12 | 4.0e12 | **100% — crossover** |
| 249.48 (whole track) | 12 474 | **9.96 GB** | 1.5e13 | 7.9e12 | 195% |

*Derived, not measured.*

**A correction to Wave 1, recorded rather than quietly fixed (J-057).** Two of the numbers that motivated
windowing are softer than they read:

- The 9.96 GB figure assumes the attention matrix is **materialised**. The installed `transformers`
  **5.14.1** routes Wav2Vec2 through the pluggable attention interface and declares
  `_supports_sdpa = True`; `torch.nn.functional.scaled_dot_product_attention` exists in the installed
  torch 2.6.0+cpu. A memory-efficient SDPA path never materialises `[1,16,n,n]`. So 9.96 GB is an
  **upper bound on the eager path**, not a certainty. *Not verified:* which implementation whisperX 3.4.5
  actually selects, or what `transformers` version a sidecar venv resolves to.
- Attention does not "dwarf" the linear term at track length — it is **1.95×** it, and the two are equal
  only at **n ≈ 6 409 frames ≈ 128 s** of audio.

This does not change the recommendation, but it changes the *reason*, and a future session must not quote
"10 GB, therefore window" as settled. The real reasons are below.

### Recommendation: **25 s hop, 2.5 s aligned context margin each side (30 s submitted)**

Four independent arguments land on the same number, and one of them is measured.

**(a) Measured — 25 s is the only length whose windows all land in 20–30 s.** Snapping each nominal
boundary to the widest gap within ±5 s of it, on the real track (J-055):

```
W=20  snapped: 13 windows, 0 words cut, len  9.9-27.4 s, 4 anchor-less windows
W=25  snapped: 10 windows, 0 words cut, len 20.4-29.9 s, 2 anchor-less windows
W=30  snapped:  9 windows, 0 words cut, len  9.9-34.0 s, 1 anchor-less window
```

W=20 and W=30 both emit a **9.9 s runt**; W=25 does not. Snapped boundaries at W=25:
`0.0 · 25.0 · 46.7 · 76.6 · 97.0 · 126.7 · 150.0 · 175.7 · 201.1 · 227.4 · 249.5`.

**(b) Blast radius.** A misassignment costs one window. Our sheets run **37–47 sung lines** over a
~250 s track (measured, J-056) — about 6 s per line, so **~4 lines per 25 s window**. Four lines is
enough that a ±1-line shift is detectable by a re-scoring probe (below), and few enough that one bad
window is a recoverable local defect. At 60 s a window carries ~10 lines and CTC has enough slack to
*absorb* an extra or missing line by stretching, which makes the error both larger and less detectable.
This is the argument that actually decides it.

**(c) Anchor supply.** Measured anchors per window at W=25 (`p ≥ 0.90` ASR words as a proxy for
usable anchors):

```
win 0   0.0- 25.0 (25.0 s)  words= 0  strong= 0   wordtime  0.0 s (  0%)   <- head gap
win 1  25.0- 46.7 (21.7 s)  words= 0  strong= 0   wordtime  0.0 s (  0%)   <- head gap
win 2  46.7- 76.6 (29.9 s)  words=34  strong=24   wordtime 24.9 s ( 83%)
win 3  76.6- 97.0 (20.4 s)  words=12  strong= 6   wordtime  9.9 s ( 49%)
win 4  97.0-126.7 (29.6 s)  words=43  strong=24   wordtime 26.1 s ( 88%)
win 5 126.7-150.0 (23.3 s)  words=10  strong= 4   wordtime  8.5 s ( 36%)
win 6 150.0-175.7 (25.7 s)  words=38  strong=27   wordtime 17.7 s ( 69%)
win 7 175.7-201.1 (25.5 s)  words=31  strong=16   wordtime 18.7 s ( 73%)
win 8 201.1-227.4 (26.3 s)  words=18  strong=13   wordtime 15.6 s ( 59%)
win 9 227.4-249.5 (22.0 s)  words= 2  strong= 1   wordtime  1.3 s (  6%)
```

Eight of ten windows carry ≥ 4 strong ASR words. Shrinking to W=20 pushes **four** windows to zero
anchors instead of two, because the same anchor-free 48 s head is chopped into more pieces. Shorter
windows do not create anchors; they only create more windows that lack them.

**(d) Fixed overhead.** Each window pays model-forward setup, audio slicing and I/O. J-000g's lesson
generalised: at W=10 a 249 s track needs ~25 windows and the per-window overhead is paid 25 times for
the same audio. The compute overhead of the margins is `(W + 5) / W` — **1.20× at W=25**, 1.33× at W=15,
1.17× at W=30.

**What happens at the extremes, stated plainly.** Too long: the eager-attention memory wall at ~250 s
(conditional, per J-057), the FLOP crossover at ~128 s, and — the one that binds well before either —
a blast radius of ten-plus lines per window with enough CTC slack to hide the error. Too short: windows
that carry fewer than one rap line (a line is ~2–4 s of delivery) force every line to straddle a
boundary; more windows fall below the anchor bar; and fixed overhead is paid more often for the same
audio.

### Overlap, and the boundary word

Boundaries are placed by a three-tier snap, and **which tier fired is recorded per boundary**:

1. **`audio_silence`** — the midpoint of the widest run of audio below −60 dBFS within ±5 s of nominal.
2. **`asr_word_gap`** — failing that, the midpoint of the widest gap between consecutive ASR words
   within ±5 s.
3. **`arithmetic`** — failing both, the nominal position. **This is an admission of ignorance and is
   recorded as one.**

**Measured: silence-snapping cuts zero ASR words** at W = 20, 25 and 30, against 3–8 words cut by a fixed
grid (J-055). That looks like it dissolves the boundary-word problem. It does not, and the reason is the
sharpest single limitation in this design:

> Snapping to an ASR word gap guarantees no **known** word is cut. It does not guarantee no **sung** word
> is cut — and J-051 established the gaps are full of untranscribed vocal. Worse, audio silence is
> unavailable exactly where it is needed: **between 20.22 s and 96.00 s there is not a single silent run
> ≥ 0.6 s** — 76 continuous seconds of energy, of which nothing before 48.31 s was transcribed. Every
> boundary in 20.2–48.3 s is placed blind.

Hence the **2.5 s context margin** on each side. Window *k* is submitted to the aligner as
`[start − 2.5, end + 2.5]` but *owns* only `[start, end)`. A word cut by a blind boundary is intact in
the neighbouring window's margin, so:

**Boundary-word arbitration.** A word emitted by more than one window is kept **once**, from the window
whose owned interval contains the word's midpoint; ties (exactly on a boundary) go to the earlier
window. Words falling entirely in a margin and in no owned interval are discarded — they belong to the
neighbour. The layer asserts **exactly-once**: every emitted word appears in exactly one window, and the
count of emitted words equals the count of distinct words across windows. That assertion is a test, not
a comment.

Margins are aligned but not owned, which is why they cost compute (1.20×) and buy correctness. In
anchored regions they are redundant with silence-snapping; in the unanchored head they are the *only*
protection available.

---

## Lyric-to-Window Assignment

This is the part that can fail, so it is specified as a pipeline of stages each of which can refuse.

### Stage 0 — Lyric ingestion, and why it needs its own refusal

**Measured (J-056), and it changed the design.** The lyric side cannot be a two-line Markdown parser.
Counting sung lines against bracketed sound-effect / ad-lib directions of the form
`([night-hum] - mmmmmm)`:

| file | sung lines | SFX / ad-lib directions | section headers |
|---|---|---|---|
| `docs/lyrics/ULICNI_KODEKS_ARTIST.md` | 47 | **52** | 5 |
| `docs/lyrics/GEWONENHEIT_DR_KHANS_POPSTARR.md` | 42 | **41** | 3 — *and none is a section* |
| `docs/lyrics/LAMELA_MIXALL_POPSTARR.md` | 38 | 35 | 6 |
| `docs/lyrics/ABGEZOCKT_LYRICS.md` | 37 | 0 | 5 |

Production directions **outnumber sung lines in one of four sheets and match them in two more**. A naive
"drop headings, keep the rest" ingestion feeds the aligner roughly **half text that is never sung** —
and CTC always returns a path, so it would place `boom-boom-boom` somewhere in the audio with a
confident-looking timing. Three further shape problems: `GEWONENHEIT`'s only bracket markers are vocal
directions (`[niederer Gesangston]`, `[Vinyl-Scratch / cut]`), so a `[Chorus]`/`[Verse N]` parser
extracts **zero** structure from it; `KASPER_DRILL_GERMAN.md` carries mix directives in the same syntax
(`[MAXIMUM:all peak,808 heaviest,drums full]`, `[VOX CHAIN]`); and `ULICNI_KODEKS_ARTIST.md` /
`ULICNI_KODEKS_GERMAN_TRANSLATION.md` are the **same song in two languages** with nothing in either
filename saying which matches a given audio file.

So Stage 0:

- classifies each line as `sung` / `sfx_direction` / `section_marker` / `production_note` / `heading`;
- **retains** the non-sung classes as metadata rather than discarding them — they are real production
  content, just not alignable, and silently dropping them loses information the vocal lab wants;
- treats section markers as **advisory only**. They are never load-bearing, because one sheet has none.
- **refuses** the sheet if the sung-line count is implausible for the track length. Band: 1 line per
  1.5–15 s of audio. For a 249 s track that is 17–166 lines; the measured sheets are 37–47. A sheet that
  fails this has almost certainly been parsed wrong, and the right answer is to stop, not to align.

### Stage 1 — Normalisation, per token

**Measured (J-052), and it changed the design.** One transcript comes back in **two alphabets**: segment
0 Latin, segments 1–12 Cyrillic, segments 13–25 Latin — 12 Cyrillic segments and 14 Latin in a single
`language="sr"` run, flipping at 120.22 s with no change of anything. **A document-level script detector
gets this transcript exactly half wrong** and silently fails to anchor one half or the other.

Normalisation is therefore **per token**: detect script per token, transliterate Cyrillic → Latin with
`cyrtranslit` (already declared, `pyproject.toml:23`), casefold, strip punctuation, collapse whitespace.
Applied identically to both the ASR stream and the lyric stream so they meet in one space.

### Stage 2 — Monotone token alignment (this is where ordering is enforced)

Flatten both sides to token streams: ASR words in time order (carrying their timestamps), lyric words in
sheet order (carrying their line index). Align the two with **Needleman–Wunsch over tokens**, substitution
score = character-level similarity `1 − lev(a,b)/max(|a|,|b|)`, with affine gaps (the ASR stream is
missing ~half its tokens, so gaps must be cheap to extend and expensive to open).

Two properties matter more than the algorithm choice:

- **A monotone path cannot reorder.** Any assignment derived from it is order-preserving by construction.
  The brief asks for reordering to be "rejected rather than smoothed over"; the stronger answer is that it
  is **not representable**. Detection is then unnecessary, and the corresponding test is a structural
  invariant (`max(line_indices[k]) < min(line_indices[k+1])`) rather than a heuristic.
- **Character-level, not exact.** Measured (J-053): the same sung word is rendered `fiksiram` /
  `siksiram` / `riksiram` — edit distance 1 on an 8-character word, similarity 0.875. Exact matching
  scores that 0 and loses the anchor. Equally, `otprobanja` vs `od problema` shows the ASR merges and
  splits tokens, so the aligner must tolerate 1↔2 token correspondences (handled as a gap plus a
  substitution; a proper 1↔n merge is an open question below).

### Stage 3 — Anchors, and the margin that decides them

A matched pair becomes a candidate **anchor** only if:

- similarity ≥ **0.80**, and
- it sits in a run of **≥ 2 consecutive matched tokens**. A lone match is coincidence: Serbian function
  words (`u`, `i`, `je`, `od`, `se`, `mi`, `ti`) match nearly everything, and there are dozens of them.

Then the decisive step. For each candidate, compute

```
uniqueness_margin = score(matched token run at its chosen lyric position)
                  − score(same run at its best-scoring rival position elsewhere in the sheet)
```

**This is the whole safety mechanism, and it is J-000a transposed into text.** Measured (J-053): 8 of
the 26 ASR segments — 31% — are occurrences of just two lines, and our sheets repeat a hook up to **6×**.
An ASR run matching the hook matches all six occurrences equally well, so its similarity is ~0.95 and its
`uniqueness_margin` is ~0. Reporting the similarity would be reporting `0.9173` on the wrong lag.

An anchor with `uniqueness_margin < 0.15` is **not** promoted to anchoring authority. It is retained,
recorded, and marked `contested` — it is evidence that *something* was sung there, but not evidence of
*which line*.

### Stage 4 — Assigning runs of lines to windows

Anchors partition the lyric sheet and the timeline simultaneously. Between two consecutive
authoritative anchors `(t_a, line i_a)` and `(t_b, line i_b)`, lines `i_a+1 … i_b−1` must be distributed
across the windows spanning `(t_a, t_b)`.

- **Both-sided (interior) gaps** — distribute **proportionally to syllable count**, using
  `toolshop/syllables.py` (already present). Rap delivery is roughly isochronous in syllables within a
  section, so syllable count is a better proportional weight than line count or character count, and it
  is free. A line lands in the window containing its interpolated midpoint. Verdict: `interpolated`.
- **One-sided gaps — the head and the tail.** Before the first anchor there is only one bound. Measured:
  that is **48.31 s and two whole windows** on borba-015, 19% of the track. Extrapolating backwards needs
  a delivery rate, and the only rate available is measured over the covered region — **65.4 words/min
  over covered word-time, 45.2 words/min over the whole track** — against rap's typical 100–200. Both
  are almost certainly wrong for the head, and nothing in the data says by how much.

  **Ruling: a one-sided run is not placed.** It is emitted as an `unanchored_span` naming
  `(line_start, line_end, time_start, time_end)`, with **no per-line assignment and no timings**, unless
  the caller passes `--allow-unanchored`, in which case it is placed at the measured local rate and
  marked `extrapolated` — never `interpolated`, never `anchored`. This is J-000b honoured: a flag on a
  wrong answer is not as good as declining to answer.

**When ASR text and the true lyric disagree — which is the normal case, not the exception.** Three
things follow, and they are easy to get backwards:

1. **The emitted text is always the lyric, never the ASR.** The ASR text is used only to *locate*. Once
   a window is assigned, the ASR text for that window is discarded. If the emitted text were ever the ASR
   text, forced alignment would have bought nothing. This is a test assertion, not a convention.
2. **Disagreement is expected and does not lower the verdict.** `siksiram` ≈ `fiksiram` at 0.875 is a
   *good* anchor. What lowers the verdict is ambiguity (low `uniqueness_margin`), not dissimilarity.
3. **Total disagreement is indistinguishable from absence.** A window where the ASR heard something and
   nothing in the sheet matches it above 0.80 is not evidence of a misassignment — it is the same signal
   as a window with no ASR output at all. Both grade `unanchored`. The layer does not attempt to
   distinguish them and does not pretend to.

### Stage 5 — Per-window preconditions, checked before anything is submitted

- **Character-set precondition** (Wave 1 risk #6, sharpened by J-052). Every character of the assigned,
  normalised text must be in the alignment model's vocabulary. `align()` maps an unknown character to a
  wildcard column and returns plausible timings for it — so a script or vocabulary mismatch produces
  confident garbage rather than an error. Any OOV character → the window is **`refused`**, and the
  aligner is not called. Given J-052's mixed-script transcript this is not hypothetical.
- **Syllable-rate plausibility.** `assigned_syllables / window_seconds` must fall in **1.5–9.0 syll/s**.
  Rap runs ~3–7. Outside that band the assignment is wrong by construction — too many lines crammed in,
  or one line stretched across 30 s. Verdict `refused`, reason `syllable_rate`.
- **Length cap.** `context_end − context_start ≤ max_window_seconds` (default 30.0). Asserted in the
  adapter, raising — not enforced by convention (Wave 1 risk #7).

### Is a misassignment detectable? — honestly

Four checks, in increasing cost, and the honest answer is that they get weaker exactly where the risk is
highest.

| # | check | when | catches | cost |
|---|---|---|---|---|
| 1 | syllable-rate band | pre-flight | gross over/under-assignment | free |
| 2 | exactly-once + monotonic line indices | post-hoc | overflow, duplication, reordering | free |
| 3 | **anchor time agreement** — an anchored word must land within 0.5 s of where the ASR heard it | post-hoc | a window shifted by a line or more | free |
| 4 | **`assignment_margin`** — re-align the window with the run shifted ±1 line; margin = `score(chosen) − max(score(shifted))` | post-hoc | a window off by exactly one line | **3× compute** |

**Check 3 is the strongest and it only works in windows that have anchors — which are precisely the
windows least likely to be misassigned.** In a fully unanchored window (measured: 2 of 10 on
borba-015, covering 48 s) checks 1 and 2 are the only ones that fire, and both are weak: an off-by-two
assignment with a plausible syllable rate and monotone indices passes both. **That is why the layer
refuses to place one-sided unanchored runs at all** rather than placing them and hoping a check catches
it. The refusal is not conservatism; it is the absence of any instrument.

Check 4 costs 3× and is therefore **tiered**: run it only on windows whose verdict is `interpolated` or
`contested`, never on `anchored` ones. On the measured track that is ~4 of 10 windows, so the real cost
is ~1.8×, not 3×. It is opt-in via `--assignment-margin` and **required** in the acceptance test.
Caveat kept explicit: `assignment_margin` is a J-000a-shaped instrument by construction, but J-000a's own
lesson is that the *obvious* confidence measure was the wrong one. It has never been validated. See
"What Cannot Be Known".

### What it reports when it is not confident

Per-window verdict, exactly one of:

| verdict | meaning | timings emitted? |
|---|---|---|
| `anchored` | ≥ 2 anchors with `uniqueness_margin ≥ 0.15` | yes |
| `interpolated` | no authoritative anchor here, but bounded by anchored windows on both sides | yes, marked |
| `contested` | anchors present but all below the margin threshold (repeated hook) | yes, marked — **not ground truth** |
| `unanchored` | one-sided or wholly unbounded | **no** (unless `--allow-unanchored` → `extrapolated`) |
| `refused` | a precondition failed (OOV character, syllable rate, length cap) | **no** |

And a **track-level verdict** that is the headline number: `lines_anchored / lines_total`, with the full
histogram. The layer never reports "alignment succeeded." It reports *how many lines are anchored*, and
`lines_total` must equal the sum of the per-class counts — no line may vanish. On borba-015 with a
hypothetical 40-line sheet, the honest expected shape is roughly 6–8 lines `unanchored` in the head,
which the layer would decline to place. **That is the correct output, not a failure of the layer.**

---

## Failure Modes & What It Refuses

| # | failure | detectable? | what the layer does |
|---|---|---|---|
| 1 | Run of lines in a **one-sided** gap (head/tail) | **no** — no instrument exists | `unanchored`, no timings, span reported. Opt-in `--allow-unanchored` → `extrapolated`, never `anchored` |
| 2 | Window assigned **one line off** | partly — check 3 in anchored windows, check 4 elsewhere | `assignment_margin` recorded; below threshold → `contested` |
| 3 | Anchor on a **repeated hook** | **yes** — `uniqueness_margin` ≈ 0 | never promoted to authority; window grades `contested` |
| 4 | **Wrong-script text** handed to the model | **yes** — character-set precondition | window `refused`, aligner never called |
| 5 | Lyric sheet **mis-parsed** (SFX kept as lyrics) | partly — sung-line-count band, then syllable rate | sheet refused at Stage 0, or window `refused` |
| 6 | Boundary cuts a **sung** (untranscribed) word | **no** | context margins + arbitration make it recoverable; `boundary_source: arithmetic` records the blindness |
| 7 | Aligner **silently falls back** to ASR timings | **yes** — per-word `origin` | `--require-alignment` exits 1; the field makes the two outputs structurally different |
| 8 | `sr` silently becomes `hr` | **yes** — recorded, not inferred | always recorded + warned; unlisted substitutions fail hard |
| 9 | Window longer than the cap → OOM | **yes** — assertion | adapter raises before submitting |
| 10 | A line silently **dropped** | **yes** — conservation invariant | `lines_total == Σ per-class counts`, asserted |

**The one it cannot catch is #1, and #1 is 19% of the measured track.** That is the honest shape of this
design: it converts an undetectable error into a declared absence. It does not eliminate it.

**What it refuses outright**, in every case by declining to emit rather than by emitting with a flag:

- a lyric sheet whose sung-line count is implausible for the track length;
- any window containing a character outside the alignment model's vocabulary;
- any window whose implied syllable rate falls outside 1.5–9.0 syll/s;
- any segment longer than `max_window_seconds`;
- any one-sided unanchored run, absent `--allow-unanchored`;
- any output where a guard fired — **and it writes no output file at all in that case**, because a
  partial file that looks like a result is the failure mode this project keeps re-buying.

---

## Data Contract & Provenance

### Where it sits

`toolshop/transcribe.py` stays flat and unchanged as a module; the alignment lane is a **new subpackage**
built the way AGENTS.md's D12 rule prescribes (`toolshop/daw/`, `toolshop/melody_carrier/` are the
pattern), with **its tests inside `tests/`** where `pytest.ini`'s `testpaths` collects them:

```
toolshop/align/
    lyrics.py     Stage 0 — Markdown ingestion + line classification.       No ML.
    windows.py    Stages 1-5 — normalise, anchor, window, assign, verdict.  No ML, no whisperX import.
    backend.py    The sidecar shell-out. The only module that knows whisperX exists.
    cli.py        `toolshop align`.
```

`windows.py` is **pure and importable with whisperX absent** — that is what makes the whole test plan
runnable today. The pipeline:

```
audio + Transcript(segments) + LyricSheet
        -> align.lyrics.parse()      -> LyricSheet(lines=[LyricLine])
        -> align.windows.plan()      -> WindowPlan(windows=[Window], unanchored_spans=[...])
        -> align.backend.align()     -> Transcript(segments, words with origin="aligned")
```

### Types

```python
@dataclass
class LyricLine:
    index: int              # position in the sheet — the ordering constraint, never re-sorted
    text: str
    kind: str               # "sung" | "sfx_direction" | "section_marker" | "production_note"
    section: Optional[str]  # advisory only (J-056: one sheet has none)
    syllables: int          # toolshop.syllables
    source_path: str        # which .md — provenance, because there is no DB (J-016)

@dataclass
class Anchor:
    time: float             # the ASR word's start
    asr_text: str           # normalised
    line_index: int
    token_index: int
    similarity: float
    uniqueness_margin: float    # THE verdict field (J-000a). Never `similarity`.

@dataclass
class Window:
    index: int
    start: float; end: float                 # owned
    context_start: float; context_end: float # submitted
    boundary_source: str        # "audio_silence" | "asr_word_gap" | "arithmetic"
    line_indices: List[int]     # contiguous, strictly increasing across windows
    anchors: List[Anchor]
    verdict: str                # anchored|interpolated|contested|unanchored|refused
    refusal_reason: Optional[str]
    assignment_margin: Optional[float]

@dataclass
class UnanchoredSpan:
    line_start: int; line_end: int
    time_start: float; time_end: float
    reason: str                 # "head_gap" | "tail_gap" | "no_matching_text"
```

### Changes to existing types

`TranscriptSegment.to_dict()` already emits whisperX's `SingleSegment` shape
(`start`, `end`, `text`, `words`) — Wave 1 confirmed the structural match, so **the wire format needs no
shim.** Two additions:

**On `Word` — one required field, no default:**

```python
origin: str        # "asr" | "aligned".  REQUIRED. No default. Serialised always.
```

This is the structural fix for the silent-fallback class. Today a fallback output is, in Wave 1's words,
"structurally identical" to a real one; with `origin` it cannot be. Note deliberately: the aligned CTC
score is **not** written into `Word.probability` and is not used as a trust signal anywhere — J-000d.
If it is emitted at all it goes in a separately named `align_score`, so nothing downstream can confuse
CTC posterior with correctness.

**On `Transcript` — provenance, all required, none defaulted:**

```python
align_backend: str              # "whisperx-align"
align_model: str                # the HF id actually loaded
align_language: str             # the code actually passed to load_align_model  -> "hr"
align_language_requested: str   # what the caller asked for                     -> "sr"
align_language_substituted: bool
lyrics_source: str              # path to the .md
windowing: Dict[str, Any]       # W, margin, boundary_source histogram, verdict histogram
lines_total / lines_anchored / lines_interpolated / lines_contested / lines_unanchored: int
```

`sr → hr` is thus **recorded, not inferred** — Wave 1's requirement — because both the requested and the
used code are stored, and their difference is stored as a boolean rather than left to be recomputed by a
reader who may not know there is no `sr` model.

### The provenance rule this design adopts, and why

**Measured (J-054):** `Transcript.source` — the field `transcribe.py:18-19` introduced *specifically* to
prevent silent degradation — reads `full_mix` on **five transcripts whose `source_path` is a two-pass
`(Vocals)` stem**, and identically on the one that really is a full mix. The mechanism:
`transcribe_file` initialises `source = "full_mix"` and only promotes it if `find_vocal_stem()` matches;
these runs were handed the stem path directly, so the field silently kept its **default**.

> **Rule: no provenance field in this layer has a default.** Each is required, is set from the value
> actually used at the point of the decision, and the writer refuses to serialise a record with any of
> them unset. Recording is not enough — the record has to be unable to be wrong.

(A separate fix on `transcribe.py`'s `source` is warranted — derive it from the resolved path rather than
from whether the *search* succeeded — but it is out of scope here and is noted in the journal instead.)

---

## Guards

Following the `toolshop melody-carrier extract` pattern (`melody_cli.py:129-168`): a **pre-flight** check
so failure costs seconds not minutes, and a **post-hoc** check against the recorded path, because a
backend can import and still fall back at runtime. Both, always — "belt and braces".

### `--require-alignment` (mandatory, per Wave 1)

*Pre-flight:* the sidecar interpreter exists; `whisperx` imports **in the sidecar**; the alignment
checkpoint resolves under `TOOLSHOP_MODEL_DIR` with `HF_HUB_OFFLINE=1`. Fail before touching audio.

*Post-hoc:* **every emitted `Word` has `origin == "aligned"`.** Any `origin == "asr"` → exit 1.

*Refuses:* any output in which the alignment stage did not run, or ran and fell back for any window —
whether because `load_align_model` raised, the checkpoint was missing offline, or the sidecar died. And
**no output file is written**, so a failed run cannot leave a plausible-looking artifact behind.

### `--allow-language-substitution sr:hr` (the second guard, and why a boolean is wrong)

Wave 1 asked whether a second guard is needed for `sr → hr`. Yes — but `--require-language-match` as a
boolean is the wrong shape: **there is no `sr` alignment model at all** (J-014), so a match guard that
is on by default makes the tool unusable, and one that is off by default guards nothing.

The useful form is an **explicit allowlist**. `sr:hr` is a decision the user has made once; it passes.
Any *other* substitution — `de` quietly resolving to something else, a future `bs` or `mk` — fails hard,
because it has not been decided. `load_align_model` raising `ValueError` on an unmapped code is *not*
the safety net here: the danger is the substitution that succeeds. The substitution is recorded and
warned loudly in every case, allowlisted or not.

### `--require-anchored` (new — the gap the Wave 1 guards do not cover)

Wave 1's guards protect against *"alignment did not run."* Nothing protects against *"alignment ran
beautifully on text assigned to the wrong window"* — which is this layer's own failure mode and the more
dangerous one, because its output is clean. `--require-anchored` refuses when any line's verdict is
`unanchored` or `refused` and the corresponding `--allow-*` flag was not given; optionally
`--min-anchored-fraction F` for a softer bar. This is the guard the windowing layer has to bring with it.

### Adapter-level assertions (not flags — they raise)

- `context_end − context_start ≤ max_window_seconds` (default 30.0) — Wave 1 risk #7. Free, so asserted.
- character-set precondition before every submission — Wave 1 risk #6, sharpened by J-052's mixed-script
  transcript. A window with an OOV character is `refused`, never wildcarded.
- exactly-once word conservation and monotone line indices across windows.

### Model manifest

The 1262 MB `classla/wav2vec2-xls-r-parlaspeech-hr` checkpoint is added to the manifest
`toolshop.doctor._model_cache_ok()` checks (Wave 1's noted gap), per AGENTS.md's model-mirror policy and
the 2026-06 HF-deletion precedent.

---

## Test Plan

**First-class deliverable, written before the implementation.** Everything below runs today with
whisperX absent, because `align/windows.py` and `align/lyrics.py` import no ML. Tests live in
`tests/test_align_windows.py`, `tests/test_align_lyrics.py`, `tests/test_align_cli.py` — inside `tests/`,
per AGENTS.md's lane rule (`ai_modules/` shipped 1,440 lines of tests that have never once run).

### The mock

`FakeAligner` stands in for `whisperx.align()` and is the contract test in disguise:

- **asserts on every call** that each input segment carries `text`, `start`, `end`, and that
  `end − start ≤ max_window_seconds` — so any test that would OOM in reality fails loudly here;
- returns word timings distributed within the segment proportionally to character count;
- records call count and the exact segments it received (so "the aligner was never called" is assertable);
- configurable modes: `raises(ValueError)` (unsupported language), `returns_asr_timings` (**the silent
  fallback**), `returns_low_score`, `returns_wildcarded` (OOV).

### Fixtures, and which tests need realistic length

`tests/fixtures/borba-015.coverage-A.json` — a **copy of the real 249.48 s transcript** (26 segments,
188 words, mixed Cyrillic/Latin, the 48.31 s head gap, the 22.34 s segment with 3 words). It is JSON
already in the repo, small, and contains every pathology this layer must handle. Paired with
`tests/fixtures/borba-015-synthetic.lyrics.md`, a **hand-written 40-line sheet** with a 4× repeated hook
and a block of SFX directions — synthetic because **no track has both a transcript and a sheet** (J-058).

> **J-000g applies directly.** Tests 1, 2, 12, 16 and 17 — anything counting boundaries, coverage
> fractions, window totals or per-window overhead — **must use the 249 s fixture**. A 30 s synthetic
> input has one boundary and one window, so every fixed-overhead and boundary effect is either 0% or
> 100% of the measurement and the test proves nothing. Tests 3–11, 13–15 are logic tests on
> hand-built inputs and are correct at any length.

### The tests

| # | test | assertion |
|---|---|---|
| 1 | `test_boundaries_never_split_an_asr_word` **(249 s fixture)** | for every boundary `b` and ASR word `w`: `not (w.start < b < w.end)`. Measured expectation: **0 words cut** at W=20/25/30, vs 3–8 on a fixed grid |
| 2 | `test_no_submitted_window_exceeds_the_cap` **(249 s fixture)** | `max(context_end − context_start) ≤ 30.0`; and a *separate* test that `backend.align()` **raises** when handed a 249 s segment — the OOM guard, tested by assertion not by OOM |
| 3 | `test_head_gap_lines_are_not_silently_placed` | the 6 lines before the first anchor get `verdict == "unanchored"`, **`line.start is None`**, and appear in `result.unanchored_spans` with `reason == "head_gap"`. Asserts absence of a timing, not presence of a good one |
| 4 | `test_interior_gap_is_interpolated_and_marked` | 4 lines across the measured 12.03 s gap are all assigned, `verdict == "interpolated"`, `boundary_source` recorded, indices contiguous and increasing |
| 5 | `test_asr_lyric_disagreement_still_anchors` | the measured real case `siksiram` vs `fiksiram`: an anchor **is** found, `0.80 ≤ similarity < 1.0` (proving fuzzy, not exact), and **the emitted text is the lyric text, never the ASR text** — the last clause is the point of forced alignment |
| 6 | `test_repeated_hook_yields_zero_uniqueness_margin` | the 4× hook: `uniqueness_margin < 0.15` and `verdict == "contested"`, **not** `"anchored"`. Asserts the layer does not pick one occurrence and call itself confident (J-000a / J-000b) |
| 7 | `test_assignment_cannot_reorder_lines` | feed an ASR stream shuffled relative to the sheet. Structural invariant: `all(max(w[k].line_indices) < min(w[k+1].line_indices))`. And the verdict **degrades** to mostly `contested`/`unanchored` rather than producing a confident scrambled mapping |
| 8 | `test_empty_window_gets_no_lines_and_no_aligner_call` | the measured tail (245.42–249.48, 79.5% digital silence): `line_indices == []`, `verdict == "unanchored"`, and `FakeAligner.call_count` **does not increase** for it |
| 9 | `test_require_alignment_refuses_when_backend_missing` | mock raises `BackendUnavailable`. Exit code 1, message names the sidecar, **and no output file exists on disk** |
| 10 | `test_require_alignment_refuses_asr_origin_words` | mock in `returns_asr_timings` mode — the silent fallback, with the pre-flight **passing**. Exit 1 because some `Word.origin == "asr"`. Tested separately from #9 precisely because the pre-flight passing is when this bites |
| 11 | `test_language_substitution_is_recorded_not_inferred` | request `sr`: output has `align_language == "hr"`, `align_language_requested == "sr"`, `align_language_substituted is True`. And an **unlisted** substitution raises rather than proceeding |
| 12 | `test_mixed_script_transcript_anchors_in_both_halves` **(249 s fixture)** | the measured J-052 case (12 Cyrillic + 14 Latin segments in one file): anchors found in **both** halves. A per-document script detector fails this; per-token passes. This test exists because the bug is invisible at any smaller scale |
| 13 | `test_oov_character_refuses_the_window` | Cyrillic text against a Latin vocab: `verdict == "refused"`, `refusal_reason == "oov_character"`, **aligner never called**. Explicitly *not* "asserts it aligns with a wildcard" |
| 14 | `test_implausible_syllable_rate_refuses` | 40 lines into a 20 s window: `refused`, reason `syllable_rate`. And the converse — 1 line across 30 s |
| 15 | `test_boundary_word_arbitration_keeps_exactly_one_copy` | a word present in window *k*'s tail margin and *k+1*'s body: emitted **once**, from the window owning its midpoint; global word count equals distinct word count |
| 16 | `test_no_line_is_silently_dropped` **(249 s fixture)** | the conservation invariant: `lines_total == anchored + interpolated + contested + unanchored + refused`. The cheapest test here and the one that catches the widest class of bugs |
| 17 | `test_sfx_directions_are_stripped_but_retained` **(real `.md` fixtures)** | on `ULICNI_KODEKS_ARTIST.md`: exactly **47** lines classified `sung` and **52** `sfx_direction`; no `sfx_direction` line reaches any window's text; and the SFX lines are still present in the parsed sheet. Uses the real file because the measured counts are the assertion |
| 18 | `test_sheet_with_no_section_markers_still_parses` | `GEWONENHEIT_DR_KHANS_POPSTARR.md` — whose only brackets are `[niederer Gesangston]` etc. — yields 42 sung lines and **zero** sections, without error. Guards the "section markers are advisory" rule |
| 19 | `test_implausible_sheet_is_refused_at_ingestion` | a 400-line sheet against a 249 s track: refused at Stage 0, before any windowing |
| 20 | `test_assignment_margin_is_computed_only_for_weak_windows` | `--assignment-margin`: `FakeAligner.call_count == n_windows + 2 × n_weak_windows`. Guards the tiering, so the 3× cost cannot silently become global |

**Marked `@pytest.mark.slow` and excluded from CI** (real model, none of these can run until whisperX is
installed and a decision the user has not made): a real `load_align_model` round-trip; the per-track
wall-clock measurement; and the quality comparison against the 188-word baseline.

---

## What Cannot Be Known Without Running It

Stated separately, because design reasoning is not measurement.

1. **Whether the `hr` CTC model produces usable posteriors on out-of-domain Serbian drill.** ParlaSpeech-HR
   is parliamentary speech — clean, formal, slow. This is the question that decides the lane and nothing
   in this document touches it.
2. **The actual alignment RTF and peak RSS on this machine.** Wave 1's 0.3–0.6 (elapsed/audio) is derived
   arithmetic. My per-window figures inherit that and are equally underived-from-measurement. Derived
   total for a 249 s track at W=25 with margins: **~1.5–3.0 min alignment + 3.8 min ASR ≈ 5.3–6.8
   min/track** — *estimate, not a measurement*, and per AGENTS.md no merge happens without a measured
   number produced with a discarded warm-up and a repeated baseline.
3. **Which attention implementation is actually selected.** J-057: the 9.96 GB figure is conditional on
   eager attention, and the installed stack supports SDPA. Nobody has checked at runtime, and the sidecar
   venv's `transformers` version is unknown.
4. **Whether the 48.31 s head contains sung *lyrics*.** I measured that it contains energy at vocal peak
   level (p95 −22.3 dBFS vs −21.9 in confirmed vocal) with only 30% digital silence. Energy is not
   speech. It could be ad-libs, backing vocals, a sample, or separation artefact. **This is the single
   fact that would most change the design** — if the head is not sung lyrics, the layer's hardest problem
   evaporates. Cost to find out: one person listening for 50 seconds.
5. **Whether `uniqueness_margin` and `assignment_margin` actually discriminate.** They are J-000a-shaped
   by construction, but J-000a's own lesson is that the obvious confidence measure was wrong. The
   thresholds proposed here (0.80 similarity, 0.15 margin, 1.5–9.0 syll/s) are **placeholders chosen to
   be checked, not values derived from data.** Every one of them needs a sweep against ground truth.
6. **What CTC does with a 28 s unanchored window.** Predicted: spreads the text and returns
   confident-looking timings. Unverified — and if it instead produces a visibly degenerate path, a cheap
   detector for failure mode #1 might exist after all, which would be the most valuable single finding.
7. **Whether the syllable-proportional interpolation beats uniform.** Asserted from the isochrony of rap
   delivery. Untested, and cheap to A/B once ground truth exists.
8. **Whether any of this generalises past one track.** Every measured number here comes from
   **borba-015**, because it is the only track with a transcript. A second track could have a different
   gap structure entirely — the 48 s head gap in particular may be idiosyncratic.

---

## Open Questions for the User

1. **Produce one track with both a transcript and a lyric sheet — which one?** Measured (J-058): the
   intersection is currently **empty**. Every transcript is borba-015; no sheet is borba-015. The cheapest
   unblock is to **transcribe a track that already has a sheet** (`ABGEZOCKT`, `ULICNI_KODEKS`) — ~4 min
   of CPU — rather than writing a sheet for Borba. Nothing downstream of this design can be *validated*
   until that exists. **Which track, and does its audio exist locally?**
2. **What is in the first 48 seconds of borba-015?** Fifty seconds of listening resolves item 4 above and
   is the highest-value-per-minute action available in this lane. Sung lyrics, ad-libs, or neither?
3. **Does `--allow-unanchored` ship at all?** The design's default is to refuse to place one-sided runs.
   That is the right default, but it means ~19% of the measured track produces no timings. Is a marked,
   admittedly-extrapolated placement useful to the flow analyser, or is it worse than nothing? This is a
   product judgement, not a technical one.
4. **Is `assignment_margin`'s ~1.8× compute acceptable?** It is the only instrument that catches an
   off-by-one assignment in a window without anchors. Default on or opt-in?
5. **Lyric ingestion is a prerequisite, not part of this lane.** J-016 named the missing pieces
   (`corpus='own'` rows, a populated `language`, an audio join key); J-056 adds two more: the sheets are
   production documents where SFX directions can outnumber sung lines, and two of them are the same song
   in different languages with nothing distinguishing them. **Is that ingestion work funded, and does it
   go into `lyrics.db` or stay as parsed Markdown?**
6. **Sidecar venv — confirmed?** This design assumes Wave 1's recommendation (whisperX in
   `.venv-whisperx`, never in `.venv`, to protect J-000e's byte-identical reproducibility from the
   `ctranslate2` 4.8.1 → 4.4.0 downgrade). `align/backend.py` is a shell-out on that assumption. If the
   user prefers an in-venv install the backend module changes shape — nothing else does.
7. **Should `transcribe.py`'s `source` field be fixed in this lane or separately?** J-054 found it reads
   `full_mix` on five stem transcripts. It is a real defect in a field whose whole purpose is preventing
   silent degradation, but fixing it here would widen this lane past its deliverable.
