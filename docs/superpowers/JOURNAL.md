# Learning Journal

> **Append-only.** One entry per *finding* — something we did not know before and now do.
> Sibling to, not a replacement for, the other records:
>
> | Record | Answers |
> |---|---|
> | `CHANGELOG.md` | *What shipped.* Answer-format, one entry per delivered change. |
> | `docs/superpowers/STATUS.md` | *Where the portfolio stands right now.* Overwritten at each review. |
> | `docs/superpowers/plans/` | *What we intend to do next.* Checkbox format. |
> | **this file** | *What we learned, including what turned out to be false.* Never rewritten. |
>
> The gap this fills: **refuted hypotheses and retracted claims have nowhere else to live.** A plan
> ticks its box and moves on; the CHANGELOG records the fix, not the wrong belief that preceded it.
> Those are the most expensive things this project has bought and the easiest to re-buy by accident.

## Entry rules

1. **Number monotonically** (`J-001`, `J-002`, …). Never renumber, never delete. A finding that is
   later overturned gets a *new* entry that supersedes it, and the old entry is annotated with a
   pointer — the wrong belief stays visible.
2. **Evidence is mandatory and must be first-hand.** A command with its output, a `file:line`, or a
   measured number the writing session produced itself. Numbers relayed from another document are
   tagged `unverified — source: <path>` per AGENTS.md, never stated as fact.
3. **`Expected` is mandatory too.** A finding with no prior expectation is just a note. The delta
   between what we thought and what is true is the entire content.
4. **Negative results are first-class.** A refuted hypothesis costs the same to obtain as a confirmed
   one and is more likely to be re-tried by a future session.
5. **`Consequence` names what changed** — a commit, a doc line, a decision unblocked — or says
   `none yet` honestly.

### Entry template

```
### J-NNN — <one-line claim, stated as the conclusion> · YYYY-MM-DD · <lane>
**Status:** verified | refuted | retracted | open
**Expected:** what we believed before.
**Found:** what is actually true.
**Evidence:** command + output, file:line, or measured number. First-hand or tagged unverified.
**Consequence:** what changed, or `none yet`.
```

---

## Seeded backlog — carried findings, 2026-08-31 and earlier

> These predate the journal and are consolidated here from `CHANGELOG.md`, `STATUS.md` and
> `plans/2026-09-01-next-moves.md` so the expensive lessons sit in one place. **Each is tagged with
> its source and is `unverified` in this session's hands** — none were re-run while writing this
> file. Verify before relying, per AGENTS.md.

### J-000a — Confidence is not correctness; `peak_margin` carries the alignment verdict · 2026-08-31 · vocal-swap
**Status:** verified by the #052 session · `unverified — source: docs/superpowers/STATUS.md`
**Expected:** cross-correlation confidence would identify a correct alignment.
**Found:** on a 120 BPM click train displaced 0.75 s, correlation peaked **0.9173 on the wrong lag**
and 0.8972 on the true one. Rap instrumentals are periodic, so this is the *normal* case, and it is
exactly how a vocal lands a bar out.
**Evidence:** `unverified — source: docs/superpowers/STATUS.md` (#052 block).
**Consequence:** `peak_margin` (gap to the best distinct rival) now carries the verdict.

### J-000b — Cross-correlation returns the mirror placement; onset matching resolves it · 2026-08-31 · vocal-swap
**Status:** verified by the #053 session · `unverified — source: CHANGELOG.md #053`
**Expected:** a large, confident correlation peak means a large, correct offset.
**Found:** on `Na tebe sam` the true offset was **−12.31 s**; correlation returned **+12.70 s** — the
mirror — at `peak_margin` 0.0009, i.e. choosing at random between near-identical peaks. It flagged
itself ambiguous and was right to. **A flag is not an answer.**
**Evidence:** `unverified — source: CHANGELOG.md` (#053, item 1).
**Consequence:** onset matching added.

### J-000c — The alignment *reference* was the defect, not the algorithm · 2026-08-31 · vocal-swap
**Status:** verified by the #052 session · `unverified — source: docs/superpowers/STATUS.md`
**Expected:** aligning a vocal take against the instrumental is a reasonable default.
**Found:** on real Serbian material with a true offset of **exactly 0**, aligning against the
instrumental returned **+1.416 s** (confidence 0.107, margin 0.005). A rap vocal shares little onset
structure with an instrumental.
**Evidence:** `unverified — source: docs/superpowers/STATUS.md` (#052 block).
**Consequence:** `--align-reference auto` uses the separated Suno vocal stem and warns on fallback.
**Still open:** never verified on two *genuinely different* performances — this is P0.

### J-000d — `Word.probability` measures the decoder's certainty, not its correctness · 2026-08-31 · transcribe
**Status:** verified by the #052 session · `unverified — source: plans/2026-09-01-next-moves.md`
**Expected:** word probability could weight or gate timings for flow analysis.
**Found:** the backend-default run reported **0.836 mean word probability** while dropping **43%** of
the track and looping inside a 36 s block.
**Evidence:** `unverified — source: docs/superpowers/plans/2026-09-01-next-moves.md` (P4 constraint).
**Consequence:** hard design constraint on flow_analyzer v2 — use `decode_settings` + coverage for
trust instead. **Do not weight by `Word.probability`.**

### J-000e — `temperature=0` made transcription reproducible, faster *and* better · 2026-08-31 · transcribe
**Status:** verified by the #052 session · `unverified — source: docs/superpowers/STATUS.md`
**Expected:** the fallback temperature ladder was harmless quality insurance.
**Found:** it made the module nondeterministic — **154 vs 194 words on identical input**, 27–32%
repeat drift across two void measurement attempts. Disabling it gave **byte-identical** output,
**~35% faster**, coverage 62%→69%, longest span 39.0→22.3 s.
**Evidence:** `unverified — source: docs/superpowers/STATUS.md` (H2-M5 block).
**Consequence:** the first *valid* min/track figure (3.6–3.8) and the property that makes a 444-track
corpus regeneration worth doing — a future diff shows analysis changes, not decoder noise.

### J-000f — The 69% transcription ceiling is the model on this material, not the plumbing · 2026-08-31 · transcribe
**Status:** two hypotheses refuted by the #052 session · `unverified — source: plans/2026-09-01-next-moves.md`
**Expected:** two mechanical causes — VAD over-filtering, and an over-separated stem.
**Found:** **both refuted on the full track.** `vad_filter=False` *fell* 22.7 points to 46.4% and ran
50% slower. The full mix tied on coverage (68.4%) with *fewer* words and a **51.5 s** max span — its
zero gaps are not a win, it emits long continuous blocks whose internal timings are unusable.
**Evidence:** `unverified — source: docs/superpowers/plans/2026-09-01-next-moves.md` (P3 table).
**Consequence:** the remaining levers are different in kind. For **our own** material the answer is
forced alignment against known lyrics, not recognition — it sidesteps the 31% entirely.

### J-000g — A clip measurement exaggerates anything with fixed overhead · 2026-08-30 · measurement
**Status:** verified twice — M3 sweep, then M5 · `unverified — source: AGENTS.md`
**Expected:** a 30 s clip / 90 s A/B is a valid screen for a full-track result.
**Found:** the M3 sweep's **1.40×** survived a 30 s clip and died at **1.00×** on a 3 min track — it
had measured 609 MB of disk read as compute (cold baseline, warm variants). The M5 90 s A/B promised
+23 pts coverage and a 22.3→5.2 s span collapse; the full track gave **+5 pts and a worse span**.
**Evidence:** `unverified — source: AGENTS.md` (Measurement discipline) and `STATUS.md` (H2-M5).
**Consequence:** AGENTS.md rules — warm up before measuring, repeat the baseline at the end, and
validate any clip result on a full input before shipping it.

### J-000h — A verified backup on the same spindle is not disaster recovery · carried 3 sessions · G5
**Status:** open — **the only item in the project whose downside is permanent**
**Expected:** `backup.py` verifying clean meant the Suno audio was safe.
**Found:** 15.79 GB of irreplaceable audio, **single copy, on the same 2010 disk as its source**.
Separately, `backup.py` once verified clean **for a month while collecting zero Suno data** — an exit
code is not coverage.
**Evidence:** `unverified — source: docs/superpowers/plans/2026-09-01-next-moves.md` (P2).
**Consequence:** none yet — blocked on the DR-target decision. This is P2.

---

## Session 2026-09-01

### J-001 — `production_analyzer` produced zero fingerprints, and a bare `except` hid it · 2026-09-01 · production-analyzer
**Status:** verified — **first-hand, this session**
**Expected:** the fix inherited uncommitted from a spawned agent's session was plausible but
unverified; the handoff asserted it without showing the check.
**Found:** the defect is real and the fix is real. `_analyze_single_file` computed
`librosa.feature.spectral_flatness()` into `flatness_data` and then read the *undefined* name
`flatness` — `NameError` on **every** call, swallowed by the surrounding `except`, so
`analyze_directory` returned zero fingerprints and reported success. The new tests genuinely catch
the defect rather than merely passing alongside it.
**Evidence:** first-hand. With the one-word fix reverted:
`3 failed, 7 passed` — `test_returns_fingerprint_with_finite_flatness`,
`test_every_feature_is_finite`, `test_analyze_directory_yields_a_fingerprint`. Restored:
`10 passed, 11 subtests passed in 7.94s`. Fix at
`toolshop/production_analyzer/batch_analyzer.py:203`.
**Consequence:** committed rather than carried a fourth session. The generalisable lesson is the
`except`, not the typo — **a fallback that swallows `NameError` turns a crash into a silent zero
result**, which is the failure mode this repo has now hit twice (see the silent-fallback incident
behind AGENTS.md's `--require-advanced` rule).
