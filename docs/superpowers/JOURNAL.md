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

### J-002 — The plan doc and `pyproject.toml` disagreed about protobuf, and the plan was wrong · 2026-09-01 · deps
**Status:** verified — **first-hand, this session**
**Expected:** `plans/2026-09-01-next-moves.md` P5 states the protobuf conflict was *"RESOLVED
2026-08-31 — pinned back to 4.21.2"*, reasoning that 4.21.2 honours the only hard pin (`classla`).
I believed it and briefed a subagent with it.
**Found:** **the opposite is true**, and the plan was superseded the same day it was written.
`pyproject.toml:29` reads *"protobuf must be >= 5.x. Keep it at 7.36.0"*; installed is **7.36.0**.
Pinning down to 4.21.2 **breaks stem separation** —
`audio_separator.separator.architectures.mdx_separator` imports `onnx`, which needs
`google.protobuf.runtime_version`, absent before 5.x. `classla`'s pin is the one deliberately
violated, because classla imports and its 20 tests pass at 7.36.0.
**Evidence:** first-hand. `grep -n -A16 protobuf pyproject.toml` → lines 29–45 carry the reasoning
and the `MEASURED 2026-08-31` note. `importlib.metadata.version('protobuf')` → `7.36.0`. The
correction is recorded in `CHANGELOG.md` #053 item 5.
**Consequence:** the subagent was corrected mid-flight before it could act on the stale claim.
The generalisable lesson is about the *records*, not the pin: **a plan written the same day as the
CHANGELOG entry that overturns it will not know it is stale, and nothing in the toolchain flags
it.** P5 of `next-moves.md` should be read as history, not as current state. Superseded-by pointers
between plan and CHANGELOG would have caught this; that is a cheap convention worth adopting.

### J-003 — A package can be "not installed" and importable at the same time · 2026-09-01 · deps
**Status:** retracted my own claim within minutes of making it — **first-hand, this session**
**Expected:** `importlib.metadata.version('onnx')` returning `PackageNotFoundError` means `onnx` is
missing from the venv, which would mean stem separation is broken right now.
**Found:** **`onnx` is present and working.** The *distribution* is named `onnx-weekly`; the *import*
name is `onnx`. A metadata query keyed on the import name reports absent while the module imports
fine at `1.23.0.dev20260706`, and the entire separation path imports clean.
**Evidence:** first-hand. `importlib.metadata.version('onnx')` → `PackageNotFoundError`, while
`import onnx` → `1.23.0.dev20260706`, and `onnx2torch`, `audio_separator`,
`audio_separator.separator.architectures.mdx_separator` all import OK.
**Consequence:** a false alarm retracted before it cost anything, and a correction sent to the
subagent I had already told. **This is the same shape of error as the one #053 caught** — that one
tested `onnxruntime` when the breakage was in `onnx`, and a bare `import audio_separator` when the
breakage was in a submodule. Mine ran a metadata query when the question was whether an import
works. Both times the instrument answered a *neighbouring* question convincingly. The rule this
yields: **when the claim is "can the code run this", the check is running it, not asking a registry
about it.**

---

## Wave 1 Agent A — whisperX forced-alignment feasibility (merged 2026-09-01)

> Merged from `journal_inbox/agentA.md`. Full write-up:
> `specs/2026-09-01-forced-alignment-feasibility.md`. Verdict **GO**, conditional on a sidecar venv,
> a version pin, and a `--require-alignment` guard.
>
> **Orchestrator spot-check.** Agent handoffs are verified here, not accepted (`AGENTS.md`). I
> re-ran the claims that are cheap to check and they hold:
>
> | Claim | My check | Result |
> |---|---|---|
> | `lyrics.db` is all other people's songs, `language` NULL | `sqlite3` count by `corpus`, by `language` | **holds** — `genius-pro` 1425, `language` NULL ×1425 |
> | No audio join key | `source_path` sample + audio-extension count | **holds** — every path is a `.json` under `D:\MusicData\...\genius\`; **0** audio extensions |
> | `DEFAULT_LANGUAGE = "sr"` would be passed through | read `toolshop/transcribe.py:98` | **holds** |
> | This project's "RTF" is inverted from convention | arithmetic against the plan's own figures | **holds** — 28.3 h ÷ 1.13 = 25.04 h, i.e. `audio/elapsed`, so 1.09–1.17 means *faster* than realtime, where conventional RTF would mean slower |
>
> **Not independently verified by me:** everything read out of whisperX's own source (`align()`'s
> signature and required fields, the absence of `sr`/`bs`/`mk`/`sh` from `DEFAULT_ALIGN_MODELS_HF`,
> the lazy `diarize` import) — whisperX is not installed, deliberately. The agent cites tag `v3.4.5`
> and `main` and quotes the lines. Treat as **strongly evidenced, not re-run.** The dependency
> resolutions come from `pip install --dry-run --report`, which resolves against the real venv
> without modifying it; the venv is unchanged — `whisperx` and `pyannote` absent, torch still 2.6.0,
> protobuf still 7.36.0.
---

### J-010 — whisperX adds no colliding protobuf constraint; the trap does not fire · 2026-09-01 · deps
**Status:** refuted — **first-hand, this session**
**Expected:** the briefing named protobuf as "the thing most likely to turn GO into NO-GO." With three
already-unsatisfiable pins (`classla==4.21.2`, `onnxruntime>=4.25.8`, `onnx-weekly>=6.31.1`), a fourth
constraint from whisperX's dependency tail looked likely to collide — and a drag below protobuf 5.x
would kill stem separation, stage one of the vocal-swap lane.
**Found:** **no collision.** Every protobuf-touching package whisperX would add sets a *lower* bound
already satisfied by the installed 7.36.0. Under a torch pin, protobuf is not in the install set at all.
**Evidence:** first-hand.
`.venv\Scripts\python.exe -m pip install --dry-run --report whisperx_report.json whisperx`, then
parsing `requires_dist` out of the report:
```
opentelemetry-proto 1.44.0      -> protobuf<8.0,>=5.0
googleapis-common-protos 1.75.2 -> protobuf<8.0.0,>=6.33.5
optuna 4.9.0                    -> protobuf>=5.28.1   (extra "optional" only)
transformers 4.57.6             -> protobuf           (extras only)
```
And with `-c torch==2.6.0,torchvision==0.21.0,torchaudio==2.6.0,urllib3==2.7.0,protobuf==7.36.0`:
`protobuf in install set? False   after = 7.36.0`. Only `tensorboardX -> protobuf>=3.20` and
`sentencepiece` (extras) appear at all.
**Consequence:** the presumed NO-GO condition is withdrawn. Recorded so a future session does not
re-buy this dry-run. Noted in passing: the *unpinned* resolution would raise the effective protobuf
floor to `>=6.33.5` via `googleapis-common-protos`, foreclosing any future retreat below 6.x — one more
reason to pin.

---

### J-011 — The real collision is torch: unpinned whisperX breaks classla, `whisperx==3.4.5` does not · 2026-09-01 · deps
**Status:** verified — **first-hand, this session**
**Expected:** protobuf was the risk; torch was a secondary check ("does whisperX pull torch, and this
machine is CPU-only").
**Found:** torch is the collision, and it is severe but entirely avoidable. Unpinned, pip selects
**whisperx 3.8.6**, which requires `torch~=2.8.0` — colliding head-on with `classla 2.2.1`'s
`torch<=2.6` (installed torch is exactly 2.6.0). The same transaction performs two *major downgrades*:
`transformers 5.14.1 -> 4.57.6` and `huggingface-hub 1.23.0 -> 0.36.2` (whisperx 3.8.6 requires
`huggingface-hub<1.0.0`), plus `urllib3 2.7.0 -> 1.26.20`, which breaks `selenium`.
**Evidence:** first-hand. Requirement metadata:
```
whisperx 3.8.6       -> torch~=2.8.0, torchaudio~=2.8.0, torchvision~=0.23.0, huggingface-hub<1.0.0
pyannote-audio 4.0.7 -> torch>=2.8.0, torchaudio>=2.8.0
classla 2.2.1        -> torch<=2.6
```
Computed violation set for the unpinned resolution (52 dists):
```
classla  2.2.1 requires "protobuf==4.21.2"            but would get 7.36.0   (pre-existing)
classla  2.2.1 requires "torch<=2.6"                  but would get 2.8.0    ** NEW **
classla  2.2.1 requires "requests==2.28.0"            but would get 2.34.2   ** NEW **
selenium 4.46.0 requires "urllib3[socks]>=2.6.3,<3.0" but would get 1.26.20  ** NEW **
```
Re-running with `-c torch==2.6.0, torchvision==0.21.0, torchaudio==2.6.0, urllib3==2.7.0,
protobuf==7.36.0` backtracks to **whisperx 3.4.5**: 44 dists, **52.4 MB** of wheels (summed from
`Content-Length` over every wheel URL in the report), and only two changes — `ctranslate2 4.8.1 ->
4.4.0` and `requests 2.28.0 -> 2.34.2`.
**Consequence:** "pin the version" is not hygiene here, it is the difference between adoptable and
NO-GO. Also a `pip` trap worth carrying: with only torch pinned, pip selects **torchaudio 2.11.0**
against torch 2.6.0 — torchaudio declares no torch pin, so pip permits a pairing that fails at import
on C++ ABI. Pin `torchaudio` explicitly, always.

---

### J-012 — No whisperX release keeps both torch 2.6 and ctranslate2 4.8.1; a sidecar venv dissolves the fork · 2026-09-01 · deps
**Status:** verified — **first-hand, this session**
**Expected:** with torch held at 2.6 there would be some whisperX version that changed nothing else.
**Found:** there is not. Every whisperX that accepts `torch<=2.6` also requires `ctranslate2<4.5.0`,
so holding torch forces `ctranslate2 4.8.1 -> 4.4.0`. Adding `ctranslate2==4.8.1` to the constraints
makes the resolution impossible. The choice in `.venv` is therefore genuinely binary: move torch (breaks
classla) or move ctranslate2 (swaps the ASR inference engine underneath **J-000e's byte-identical
reproducibility** — the property that makes a 444-track corpus regeneration worth doing at all).
**Evidence:** first-hand.
`.venv\Scripts\python.exe -m pip install --dry-run -c strict.txt --report whisperx_strict.json whisperx`
→ `ERROR: ResolutionImpossible`, with:
```
whisperx 3.4.0 depends on ctranslate2<4.5.0
whisperx 3.3.6 depends on ctranslate2<4.5.0
...
whisperx 3.2.0 depends on ctranslate2==4.4.0
The user requested (constraint) ctranslate2==4.8.1
The user requested (constraint) torch==2.6.0
```
Note `faster-whisper 1.2.1` metadata *accepts* 4.4.0 (`ctranslate2<5,>=4.0`) — so nothing breaks
declaratively. The risk is that byte-identical reproducibility across a CTranslate2 minor-version
change is an **assumption**, and this project's own history (the "all green at 4.21.2" report that
tested the wrong package) is exactly about metadata checks standing in for behavioural ones.
**Consequence:** recommendation is a **separate sidecar venv**, which removes both horns for free. The
interface is unusually clean: `TranscriptSegment.to_dict()` already emits `{"start","end","text",
"words"}`, which is exactly whisperX's `SingleSegment` shape, so the boundary is the transcript JSON
already stored in `data/toolshop/lyrics/transcripts/`.

---

### J-013 — Alignment-only genuinely needs no HF token; pyannote is installed but never imported · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session**
**Expected:** the OSS integration map asserts "use alignment-only path (no diarization) unless needed"
as the mitigation for "pyannote needs HF token" — asserted, never checked. The brief explicitly said
confirm, don't assume.
**Found:** **confirmed, and the mitigation is narrower than written.** The token requirement is real and
belongs to the diarization *model*, not to whisperX. But alignment-only does **not** avoid pip
installing `pyannote.audio` — it is a core dependency in both 3.4.5 (`pyannote-audio<4.0.0,>=3.3.2`)
and 3.8.6 (`>=4.0.0`), dragging speechbrain, lightning, optuna, SQLAlchemy, alembic and ~25 more.
What it avoids is *importing* it.
**Evidence:** first-hand, two independent checks.
HuggingFace model API (`?blobs=true`):
```
classla/wav2vec2-xls-r-parlaspeech-hr   gated: False   private: False   downloads: 823787
pyannote/speaker-diarization-3.1        gated: auto    private: False   downloads: 9578771
```
The alignment checkpoint is **ungated**; the gated repo is the diarization pipeline.
And `whisperx/__init__.py` at tag `v3.4.5` uses a `_lazy_import` helper — `diarize` is imported *inside*
`assign_word_speakers()`, not at module load, so `pyannote.audio` never enters `sys.modules` on the
alignment path.
**Consequence:** the OSS map's risk row should be split — "no token" is verified; "avoids heavy deps" is
false, and is the reason the sidecar venv matters. Also usable offline: `load_align_model` takes
`model_dir`, so the 1262.0 MB checkpoint can live under `TOOLSHOP_MODEL_DIR` with `HF_HUB_OFFLINE=1`.

---

### J-014 — There is no Serbian alignment model; Croatian is the reachable proxy, published by classla · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session**
**Expected:** alignment models are per-language and the OSS map calls Serbian "usable (multilingual)" —
a property of *Whisper*, which is multilingual. Alignment models are not.
**Found:** `DEFAULT_ALIGN_MODELS_HF` has **no `sr`, no `bs`, no `mk`, no `sh`** — in either `v3.4.5` or
`main`. `load_align_model` raises `ValueError` on an unknown code. So passing
`transcribe.DEFAULT_LANGUAGE` (`"sr"`, `toolshop/transcribe.py:98`) straight through **would crash**.
`hr` is present and is the reachable proxy: BCMS is one dialect continuum and Croatian/Serbian Latin
share the identical Gaj alphabet, so the CTC character vocabulary covers Serbian Latin unchanged.
**Evidence:** first-hand, `whisperx/alignment.py` at tag `v3.4.5`:
```
"hr": "classla/wav2vec2-xls-r-parlaspeech-hr",
```
Neighbours present: `sl`, `sk`, `cs`, `pl`, `ru`, `uk`. Absent: `sr`, `bs`, `mk`, `sh`.
Signature: `load_align_model(language_code, device, model_name=None, model_dir=None)` — so an arbitrary
HF id can be substituted later without touching whisperX.
**Consequence:** an explicit `sr -> hr` mapping is a wiring requirement, and the substitution must be
*recorded* in the transcript, not inferred. Two caveats found alongside: ParlaSpeech-HR is
**parliamentary speech** (clean, formal, slow) and drill at 100–200 wpm is far out of domain — untested;
and `align()` maps out-of-vocabulary characters to a **wildcard column**, so it will return
confident-looking timings for wrong-script text. Cyrillic must be transliterated first (`cyrtranslit`
is already declared, `pyproject.toml:23`). Pleasing coincidence: the Croatian model is published by
**CLASSLA** — the same organisation whose Python package is the dependency whose protobuf pin we
deliberately violate.

---

### J-015 — whisperX aligns *within* a segmentation you supply; it does not align a bare lyric sheet · 2026-09-01 · transcribe
**Status:** verified — **first-hand, this session.** Partially refutes the premise in
`plans/2026-09-01-next-moves.md` P3.
**Expected:** the plan states forced alignment "aligns *known text* to audio instead of guessing at it,
which sidesteps the 31% entirely."
**Found:** **not by itself.** `align()` consumes `Iterable[SingleSegment]` where each segment must
already carry `text`, `start` **and** `end`. It *refines* a segmentation; it does not produce one. Fed
the existing ASR segmentation, the 31% with no segment still gets no alignment anchor — the gap
propagates. And the naive workaround (one segment spanning the track) is arithmetically ruled out:
`align()` has **no chunking and no max segment length**, so self-attention goes quadratic. A 249.48 s
track is ~12,474 frames at 50 fps; the attention matrix alone is `12474² × 4 B` ≈ **622 MB per head**,
≈ **10 GB** across 16 heads on a **15.9 GB** machine — OOM or thrash.
**Evidence:** first-hand. Signature and required fields from `whisperx/alignment.py`:
```
def align(transcript: Iterable[SingleSegment], model, align_model_metadata, audio, device, ...)
# required per segment: "text", "start", "end"   (optional: "avg_logprob")
```
Confirmed "no chunking or max-length limit" in `align()`. RAM figure measured on this machine
(`Win32_ComputerSystem.TotalPhysicalMemory` = 15.9 GB); frame count derived from the measured
`audio_duration` 249.48 s in `data/toolshop/lyrics/transcripts/borba-015.large-v3.temp0.json`.
**Consequence:** the win is real but smaller and differently shaped than the plan claims. Within the
covered 69%, substituting known lyrics makes the words *correct* and sharpens timings from whisper's
coarse spans to ~20 ms frames — exactly what syllables-per-bar needs. Closing the 31% requires **our
own windowing layer** (~20–30 s windows, lyrics assigned by ASR anchors). That is build work on top of
whisperX, not a whisperX feature, and the plan should be corrected to say so. Silver lining:
`toolshop.transcribe.TranscriptSegment` is already `(start, end, text, words)` and its `to_dict()`
emits exactly `SingleSegment`'s shape — no adapter shim needed for the data itself.

---

### J-016 — `lyrics.db` holds no own-material lyrics and no audio join key · 2026-09-01 · lyrics-db
**Status:** verified — **first-hand, this session**
**Expected:** the brief asked whether `data/toolshop/lyrics/lyrics.db` "already holds the lyrics in a
usable shape for our own tracks," implying it plausibly did.
**Found:** it does not. The schema is *well* suited to the job — `sections -> lines(text_raw, text_norm,
word_count, syllable_count) -> tokens` is exactly the hierarchy an aligner wants, and `lines` even
carries syllable counts. But the contents are entirely **other people's songs**, and there is no link
to audio.
**Evidence:** first-hand, read-only (`mode=ro`) query against `data/toolshop/lyrics/lyrics.db`:
```
corpus counts:   [('genius-pro', 1425)]        <- one corpus, no 'own'
language counts: [(None, 1425)]                <- language NULL on every row
categories:      jala-solo 200, maya-berovic-solo 145, rasta-solo 109, devito-solo 106,
                 corona-solo 92, senidah-solo 82, coby-solo 82, buba-solo 75, ...
total songs 1425 · total lines 65912 · distinct target_artist 18
songs whose source_path points at audio: 0
sample source_path: D:\MusicData\toolshop\lyrics\genius\ana-nikolic-solo\ana-nikolić-200100.json
```
**Consequence:** the premise "for everything the artist writes, the lyrics are already known" is true of
the **artist** and false of the **database**. Our lyrics live as loose Markdown (the
`to_be_moved/*_LYRICS.md` family). Adoption needs a prerequisite unrelated to whisperX: an ingestion
path writing `corpus='own'`, a populated `language`, and — the missing piece — **an audio join key**,
which `songs` has no column for.

---

### J-017 — `plans/2026-09-01-next-moves.md` P5 and `pyproject.toml` recorded opposite protobuf resolutions · 2026-09-01 · records
**Status:** verified — **first-hand, this session.** Found independently before the orchestrator's
correction arrived; both agree.
**Expected:** the briefing (sourced from the plan doc) stated the protobuf question was "resolved
2026-08-31 by pinning protobuf back to 4.21.2 because that honours the only *hard* pin."
**Found:** the opposite is true, and the plan doc is stale. `pyproject.toml` records that pinning **down**
to 4.21.2 **breaks stem separation** — `audio_separator...mdx_separator` imports `onnx`, which needs
`google.protobuf.runtime_version`, absent before 5.x — so the vocal-swap lane dies at its first stage.
classla's pin is the one deliberately violated. The installed state agrees with `pyproject.toml`, not
with the plan.
**Evidence:** first-hand.
`pyproject.toml:29-33`: `"NOTE — protobuf must be >= 5.x. Keep it at 7.36.0. ... classla's is the one to
violate: it imports and its 20 tests pass at 7.36.0."`
`pyproject.toml:35-39` records the measured breakage at 4.21.2.
Installed: `protobuf 7.36.0`. Requirement metadata read via `importlib.metadata.requires`:
`onnxruntime 1.27.0 -> protobuf>=4.25.8`; `onnx-weekly -> protobuf>=6.31.1`;
`classla 2.2.1 -> protobuf==4.21.2, torch<=2.6`.
**Consequence:** `plans/2026-09-01-next-moves.md` P5 needs correcting — it was superseded the same day by
CHANGELOG #053 and still reads as current. The generalisable lesson is AGENTS.md's **"no record ahead of
code"** rule inverted: a record left *behind* the code is just as expensive, and here it propagated
into an agent briefing and would have driven a wrong verdict. A resolved `[USER DECISION]` in a plan
should point at the file that now holds the truth.

---

### J-018 — This project's "RTF" is a speed factor (audio/elapsed), inverted from the conventional definition · 2026-09-01 · measurement
**Status:** verified — **first-hand, this session**
**Expected:** the briefed figure "RTF 1.09–1.17×, 3.6–3.8 min/track" read as conventional RTF
(`elapsed / audio`), i.e. slower than realtime. Under that reading it is inconsistent with the stored
artifacts, which show 229.61 s of compute for 249.48 s of audio.
**Found:** the project computes `audio_duration / elapsed` — a *speed factor*, faster than realtime.
249.48 / 229.61 = **1.087** ≈ the quoted 1.09; 249.48 / 213.2 = **1.17**. Under the conventional
definition the same runs are RTF **0.92–0.98**. Both numbers are correct; only the label is ambiguous.
**Evidence:** first-hand, read out of `data/toolshop/lyrics/transcripts/*.json`:
```
borba-015.large-v3.temp0.json  dur=249.48  el=229.61  cov=69.1%  words=188
borba-015.coverage-A.json      dur=249.48  el=245.03  cov=69.1%  words=188
borba-015.coverage-B.json      dur=249.48  el=370.49  cov=46.4%  words=127
borba-015.coverage-C.json      dur=249.48  el=166.96  cov=68.4%  words=147
old-config-baseline.large-v3   dur=249.48  el=727.79  cov=56.7%  words=202  lang=hr
```
This also re-confirms J-000e first-hand across sessions: the two temperature-0 runs both give exactly
**69.1% / 188 words**.
**Consequence:** any comparison against a published whisperX or faster-whisper RTF will be inverted
unless the definition is stated. The feasibility spec states `elapsed / audio` explicitly for every
estimate. Worth a one-line definition next to the figure wherever it is quoted — cheap now, an
embarrassing conclusion later. Machine of record for all of these: Intel i7-4770 (4C/8T, 3.4 GHz,
Haswell — AVX2/FMA, **no AVX-512, no VNNI**), 15.9 GB RAM.

---

## Session 2026-09-01 (continued)

### J-004 — `git add -A` during a live orchestration commits another agent's half-finished work under the wrong subject · 2026-09-01 · orchestration
**Status:** verified — **first-hand, and self-inflicted, this session**
**Expected:** `git add -A docs/superpowers/` would stage the Agent A merge I had just finished —
the journal, the corrected plan, and A's spec.
**Found:** it also swept **1,158 lines of Agent B's in-progress output** — `journal_inbox/agentB.md`
(242 lines) and `specs/2026-09-01-dossier-schema-v2.md` (916 lines) — into a commit whose subject
reads *"Wave 1 Agent A merged"*. Agent B was **still running**; the files were mid-write. The commit
message describes none of it.
**Evidence:** first-hand. `git show --stat ce52adb` lists five files across two agents; the subject
names one. The agent had produced no completion notification at the time of the commit.
**Consequence:** the commit is pushed and stands; not rewritten, because a false-clean history is
worse than an honest wrong one. **This is precisely the failure `AGENTS.md`'s lane-discipline rule
was written against** — commit `31224e5` shipped a 6,390-line package under *"chore: update
mastering_tool submodule"*. That rule assumed a human writing a misleading subject. Orchestration
adds a mechanism nobody wrote it for: **a wildcard stage is not scoped to the work you did when
other agents are writing into the same tree concurrently.** No hook catches this — the tree is
clean, the push succeeds, the gate passes.
**Rule adopted:** while any agent is live, **stage explicit paths, never `-A` and never a directory.**
The orchestrator's own scope memory says the same thing for a different reason (don't sweep
incidental files); this is that rule with a second, sharper edge.

---

## Wave 1 Agent B — dossier schema v2 (merged 2026-09-01)

> Merged from `journal_inbox/agentB.md`. Full write-up:
> `specs/2026-09-01-dossier-schema-v2.md`. **This wave resized M6 rather than designing it.**
>
> **Orchestrator spot-check.** Every load-bearing claim re-run here, because these findings
> invalidate numbers that are published across `STATUS.md`, two plans and a handoff:
>
> | Claim | My check | Result |
> |---|---|---|
> | The corpus is 222, not 444 | `find results/crhymetv_re -name "*_analysis.json"` → **444**; `! -name "*_voice_analysis.json"` → **222**; voice sidecars → **222** | **holds** — the glob counted each track twice |
> | The batch hard-codes the advanced backend | read `run_reverse_engineering_batch.py` → `backend="advanced"` | **holds** |
> | The four new fields come only from `_basic_analysis` | `beat_grid` at `reverse_engineering_adapter.py:122`, `premaster` at `:132`, both inside `_basic_analysis` (52–133, `analysis_backend: "basic_librosa"`); `_advanced_analysis` is 137–210 | **holds** |
> | Nothing in the corpus carries them | loaded all 222: `sections` **0**, `structure` **0**, `beat_grid` **0**, `premaster` **0**, `lyrics` **0**; `key`/`mode` **222** | **holds** — and `sections` is *absent*, not `[]` |
> | `mode` is a threshold, 215/7 | `feature_extractor.py:190` → `mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'`; corpus → **215 major / 7 minor** | **holds** (precisely: chroma energy at the tonic bin, not loudness) |
> | Backend mix | corpus → **221 `wav_reverse_engineer` + 1 `basic_librosa`** | **holds** — 221 tracks + 1 diagnostic |
> | The corpus is German | track dirs: `Sa4 – Täterprofil`, `Sa4 – NachtAktiv`, `LETZTE ANSAGE`, `MUTANTEN EICHHÖRNCHEN`, `129ers`, `Capuz` | **holds** — unambiguously German, not Balkan |
>
> **The consequence is bigger than the corrections.** M6 as written was *"re-run the corpus so the
> new fields exist"*. The new fields **are not produced by the backend the corpus batch uses**. A
> plain re-run — 13 h or 25 h, whichever number is right — would have added **nothing at all**, and
> the count check would have reported a clean 222 in / 222 out while doing so. This is the single
> most valuable thing either agent found, and it was found by reading the code rather than trusting
> the plan.

### J-020 — The "444-dossier corpus" does not exist; it is 222, double-counted by a glob · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** 444 dossiers, per `HANDOFF-2026-08-31.md:165`, `plans/2026-09-01-next-moves.md:44`,
`STATUS.md:30` and `CHANGELOG.md:263`. The handoff states it as measured: *"444 dossiers with live
source audio … (The roadmap says '222'; the real count including PapaPedro is 444.)"*
**Found:** there are **222** track dossiers, all in `results/crhymetv_re/per_track/`. The 444 is the
count of files matching `*_analysis.json`, which also matches the **`_voice_analysis.json` sidecar**
written next to each dossier. 222 dossiers + 221 voice sidecars + 1 duplicate voice sidecar under
`diagnose_voice/` = exactly 444. **PapaPedro contributes nothing** — it has 687 source mp3s and only
3 analysed directories, none of them dossiers (`results/papapedro_re/per_beat/`, per-beat output).
**Evidence:** first-hand.
```
$ find results/crhymetv_re -name "*_analysis.json" | wc -l
444
$ find results/crhymetv_re/per_track -name "*_analysis.json" -not -name "*_voice_analysis.json" | wc -l
222
$ find results/crhymetv_re/per_track -name "*_voice_analysis.json" | wc -l
221
$ ls results/crhymetv_re/diagnose_voice
2010-12-08 - Sa4 - Täterprofil [eryRCHmXItY]_voice_analysis.json
$ ls results/crhymetv_re/per_track | wc -l
222
$ ls "D:/Projects/Tools/yt_extractor/downloads/PapaPedro Beats" | wc -l   # 687 .mp3
$ ls results/papapedro_re/per_beat | wc -l
3
```
**Consequence:** M6's scope halves. The regeneration target is **222 tracks**, and the count
verification must assert 222 → 222, not 444 → 444. Written into
`specs/2026-09-01-dossier-schema-v2.md`. **The generalisable lesson is the glob:** `*_analysis.json`
is a suffix, and `_voice_analysis.json` ends with it. Any corpus count must be re-derivable from a
`--not-name` exclusion or from the batch status file, never from a bare suffix glob.

### J-021 — The 28.3 h / ~25 h CPU estimate inherits the same double count, to 3 significant figures · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** 28.3 h of audio ⇒ ~25 h CPU at RTF ~1.13 (`STATUS.md:30`, `CHANGELOG.md:263`,
`plans/2026-09-01-next-moves.md:42`).
**Found:** the real audio is **13.58 h** for the 221 completed tracks. Doubling it and adding the one
track that has no voice sidecar reproduces the published figure **exactly**:
`2 × 13.5839 h + 4062 s = 28.2961 h ≈ "28.3 h"`. The single-count total is **14.71 h**, so
transcription at RTF 1.13 is **~16.6 h**, not ~25 h — and ~15.4 h if the 67.7-minute documentary is
excluded, which it should be.
**Evidence:** first-hand, summing `duration_seconds` over `results/crhymetv_re/catalogue.csv`
(221 rows) and reading the skipped track's duration from `batch_status.json`:
```
221 completed = 48902.0 s = 13.5839 h
double-count model: 2*48902 + 4062 = 28.2961 h   <- matches published 28.3
single-count model:   48902 + 4062 = 14.7122 h
RTF 1.13 on single-count -> 16.62 h CPU
```
**Consequence:** the cost line in the M6 spec is stated as **~16.6 h transcription**, derived
first-hand, with the ~25 h relayed figure tagged `unverified — source: docs/superpowers/STATUS.md`
and marked superseded. A weekend slot is no longer required; a single overnight covers it.

### J-022 — `batch_status.json` and the filesystem disagree; the status file is not authoritative · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** the resumable batch's status JSON is the record of what was produced, so a
skip-completed resume and a count check can both read it.
**Found:** the one non-completed track — `2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ`,
a 4062 s (67.7 min) documentary — is recorded as `"status": "skipped_long"` with
`"analysis_json": null`. **An `_analysis.json` exists on disk for it anyway**, 464 bytes, from an
earlier run under an older schema. So a resume driven by the status file would re-analyse a track
that has output, and a count driven by the filesystem would count a track the status file says was
skipped. The two disagree by one, in opposite directions.
**Evidence:** first-hand.
```
$ python - <<'PY'   # batch_status.json
Counter({'completed': 221, 'skipped_long': 1});  errors: 0;  total_tracks: 222
skipped record: analysis_json=null, voice_json=null, stems=null, recipe_md=null
PY
$ ls "results/crhymetv_re/per_track/2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ/"
2023-02-07 - ,,Komm, wir schreiben Geschichte＂ ... [BKGeueSkWXQ]_analysis.json   # 464 bytes
stems
```
Also: `catalogue.csv` has **221** rows against **222** per_track directories — a third count that
disagrees with both.
**Consequence:** the M6 count verification is specified to reconcile **three** sources (input
enumeration, status JSON, filesystem) and to fail loudly on any pairwise disagreement, rather than
trusting one. This is the concrete instance of the failure mode `next-moves.md` names — *"a batch
that succeeds having skipped half its input"* — already present in the corpus at n=1.

### J-023 — The corpus holds two v1 schema variants, not one · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** one legacy dossier shape to migrate from.
**Found:** exactly two, and they differ by seven optional field groups, not by version. The 221
normal dossiers have **18** keys (`analysis_backend: "wav_reverse_engineer"`) and add `tuning_offset`,
`onset_strength`, `effects`, `instruments`, `chord_progression`, `notes`, `separation` on top of an
11-key core. The skipped documentary's 464-byte file has only that 11-key core
(`analysis_backend: "basic_librosa"`). **Neither carries a version marker of any kind** — the only
discriminator available at read time is `analysis_backend`, which describes the *engine*, not the
*schema*, and would become ambiguous the moment a v2 file used the same engine.
**Evidence:** first-hand, key-set census over all 222 dossiers — 2 distinct key-sets, sizes 18 (×221)
and 11 (×1); full listing in J-026 and in the spec's §Schema v1 As-Is.
**Consequence:** v1 detection in the spec is by **absence of the `schema_version` key**, which is
sound precisely because no existing file has one; and the optional field groups are carried through
the migration as-is rather than being treated as required, since 1 of 222 files legitimately lacks
all seven.

### J-024 — The four "real" dossier fields are emitted only by the *fallback* backend; the default emits none of them · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. This is the finding that resizes M6.**
**Expected:** M1–M4 made `key`/`mode`, `structure`, `beat_grid` and `premaster` real in the dossier,
so regenerating the corpus with the current code would produce them (`STATUS.md` H2-M4: *"Dossier now
carries four real fields"*).
**Found:** `toolshop/reverse_engineering_adapter.py` has **two** emitters and the new fields are in
the wrong one.
- `_basic_analysis` (`analysis_backend: "basic_librosa"`) emits `beat_grid`, `structure`,
  `premaster`, and K-S `key`/`mode`/`key_confidence`/`key_alternate`/`key_margin` —
  `reverse_engineering_adapter.py:116-134`.
- `_advanced_analysis` (`analysis_backend: "wav_reverse_engineer"`) emits **none** of them and takes
  `key`/`mode` straight from the external package — `reverse_engineering_adapter.py:158-159`.
- `analyze_track` prefers advanced whenever it imports (`:246`, `use_advanced = _WAV_RE_AVAILABLE and
  backend != "basic"`), the CLI defaults `--backend advanced` (`cli.py:300-303`), and the corpus batch
  **hard-codes** `backend="advanced"` (`run_reverse_engineering_batch.py:215`).

Corpus census agrees: **221 of 222 dossiers are `wav_reverse_engineer`**, 1 is `basic_librosa` — and
that one is the 464-byte skipped-documentary file, i.e. the fallback ran there by accident.
**Evidence:** first-hand; `file:line` above, plus a census of `analysis_backend` over all 222
dossiers: `{'wav_reverse_engineer': 221, 'basic_librosa': 1}`.
**Consequence:** **M6 cannot be a re-run of the existing pipeline.** Running the batch as-is over the
corpus would reproduce the same v1 dossier with new timestamps and zero new fields. The spec's
migration therefore has a prerequisite that the plan did not name: either port the four field groups
into `_advanced_analysis`, or have the migration compute them itself and merge. Recorded as **Open
Question 1** in `specs/2026-09-01-dossier-schema-v2.md`.

### J-025 — The H2-M1 key fix never reached the dossier's default path; the loudness-threshold `mode` is still live code · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. Qualifies the "all four share one detector" claim.**
**Expected:** `STATUS.md` H2-M1: *"FOUR implementations, not two … All four now share one detector."*
**Found:** the implementation actually used for every corpus dossier was not among the four that were
fixed. `_advanced_analysis` calls `FeatureExtractor.extract_features`, whose `_estimate_key` still
reads, at
`projects/05-track-reverse-engineering/track_reverse_engineering/wav_reverse_engineer/audio_analyzer/feature_extractor.py:185-190`:

    key_idx = np.argmax(chroma_vals)
    ...
    mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'

That is the exact defect H2-M1 was raised to remove — tonic by loudest chroma bin, mode by a
magnitude threshold — and it is still the code path the dossier uses by default.
**Evidence:** first-hand, `file:line` above. Corpus-scale confirmation, stronger than the 7-of-8
sample the milestone was written from: over all 222 dossiers, **`mode` is `major` on 215 and `minor`
on 7 — 96.8% major** on a German rap/hip-hop catalogue (all 221 catalogue rows describe the material
as "German rap / hip-hop"). The 7 "minor" tracks are the ones whose loudest chroma bin happened to
fall below 0.5.
**Consequence:** the `mode` collision in schema v2 is not a naming problem, it is a **live defect**.
The spec resolves it by preserving the old value under `legacy_mode_loudness_threshold` with an
explicit provenance tag, never by reinterpreting it in place. Downstream artefacts already built on
it — `catalogue.csv` (`key`,`mode` columns), `recipe.md`, `suno_prompts.md` — are wrong for the same
reason and must be regenerated after the migration.

### J-026 — `sections` is not `[]` in the corpus; it is absent, and there are only two v1 key-sets · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** *"the `sections` that were always `[]`"* — `plans/2026-09-01-next-moves.md:45`,
`HANDOFF-2026-08-31.md:169`, and the task framing "distinguish analysed-but-empty from never-analysed".
**Found:** **no dossier in the corpus has a `sections` key at all.** A census of every key in all 222
dossiers returns exactly two key-sets, 18 keys and 11 keys, and `sections` is in neither:

    sections: {'<MISSING>': 222}
    distinct key-sets: 2
      221 x 18 keys: analysis_backend, beat_count, bpm, chord_progression, duration_seconds,
                     effects, file, harmonic_ratio, instruments, key, mode, notes,
                     onset_strength, sample_rate, separation, spectral_bandwidth,
                     spectral_centroid, tuning_offset
        1 x 11 keys: analysis_backend, beat_count, bpm, duration_seconds, file, harmonic_ratio,
                     key, mode, sample_rate, spectral_bandwidth, spectral_centroid

The `[]` was real in the *code* — `librosa.segment.agglomerative(chroma, k=None)` raising into a bare
`except Exception: return []`, per #048 — but that dead segmenter lived on a path the corpus batch
never took (see J-024), so the empty list was never even serialised.
**Evidence:** first-hand, census over `results/crhymetv_re/per_track/*/*_analysis.json` (222 files,
0 unreadable).
**Consequence:** the ambiguity to design against is **three**-valued, not two: *key absent* (never
analysed), *`[]`* (the historical failure signature, present in no file but reachable from older
code), and *populated*. The spec makes v2 carry `structure.status` in
`{analysed, none_detected, not_attempted, failed}` with a `reason`, so an empty `segments` list is
never load-bearing on its own.

### J-027 — `find_vocal_stem` cannot see the corpus stems; and only 140 of 222 tracks have any · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** the M5 transcriber would find each corpus track's vocal stem, since the corpus has stems.
**Found:** it returns `None` for every corpus track under default search. `find_vocal_stem`
(`toolshop/transcribe.py:292-337`) searches the audio file's own parent, sibling `*stem*`
directories, and `paths.subdir("stems")`. The corpus audio lives at
`D:\Projects\Tools\yt_extractor\downloads\CrhymeTV\`; its stems live under
`results/crhymetv_re/per_track/<slug>/stems/` — not a sibling, and `data/toolshop/stems` contains
only `karaoke/`. Passing `search_dirs` explicitly works.
**Evidence:** first-hand, run in the venv:

    src exists: True
    default search  -> None
    explicit search -> ...\per_track\2010_12_08_Sa4_T_terprofil_eryRCHmXItY\stems\
                       2010-12-08 - Sa4 - Täterprofil [eryRCHmXItY]_(Vocals)_UVR-MDX-NET-Voc_FT.wav

Separately, a stem census: **140 tracks have a non-empty `stems/` with a vocal file, 81 have no
`stems/` directory, 1 has an empty one** — so 82 of 222 have no stem to transcribe from and would
silently fall back to the full mix. (This matches AGENTS.md's "140/222 with stems" — first-hand
confirmation of a previously relayed number.)
**Consequence:** the migration must pass `search_dirs=[<per_track>/<slug>/stems]` explicitly, and
must record `lyrics.source` (`vocal_stem` | `full_mix`) per track — the corpus will be **mixed
provenance**, which makes any corpus-level coverage statistic uninterpretable unless split by source.
`--require-stem` would refuse 82 tracks rather than degrade them, which is the honest default for a
sample run and the wrong one for the full corpus.

### J-028 — The transcriber's default language is `sr`; the corpus is German · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** decode settings measured in M5 would carry over to the corpus run unchanged.
**Found:** `DEFAULT_LANGUAGE: Optional[str] = "sr"` (`toolshop/transcribe.py:97`), chosen because
auto-detect picked `"hr" at p=0.31` on *Serbian* material — the user's own tracks. The regeneration
corpus is **CrhymeTV, German rap**: all 221 catalogue rows carry `German rap / hip-hop` in
`suno_prompt`, and the artists are Sa4, 129ers, Capuz. Running the corpus at the module default would
force Serbian decoding on 222 German tracks. `DEFAULT_MODEL` is also `"small"` (`transcribe.py:89`),
while the ~25 h / RTF 1.13 figure was measured on `large-v3` — a second default that does not match
the plan's own cost basis.
**Evidence:** first-hand — `transcribe.py:89` and `:97`, and a count over `catalogue.csv`:
`sum('German' in r['suno_prompt']) = 221 / 221`.
**Consequence:** the spec pins `language="de"` and `model="large-v3"` for this corpus **explicitly in
the migration's recorded `decode_settings`**, not as a module default change, and makes the sample
protocol's stop-criteria include a language-probability floor. The generalisable point:
`decode_settings` being recorded per track (M5's own design) is what makes this catchable at all —
but only if someone reads them, so the count-verification report prints the distinct
`decode_settings` seen across the run.

### J-029 — `run_batch`'s `total_tracks` is rewritten by any `--limit` run, so a 20-track sample corrupts the corpus status file · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** `--limit` is a safe way to run a sample against the same output directory before
committing to the full corpus, since resume is keyed by source path.
**Found:** `discover_files` applies `limit`/`offset` *before* `run_batch` sees the list
(`toolshop/batch.py:54-65`), `run_batch` sets `total = len(files)` (`:129`), and
`load_or_create_status` unconditionally overwrites the stored value with it:
`status["total_tracks"] = total` (`:77`). A `--limit 20` run against an existing
`batch_status.json` therefore rewrites `total_tracks` from 222 to **20**, destroying the very number
a count check would compare against. Two further sharp edges in the same function: `--offset` shifts
the *display* index only (`run_batch(offset=...)`, `:141`), so the slice actually processed is
recorded nowhere; and `status["last_completed_index"] = idx` is set on the **failure** path too
(`:170-176`), so the name is wrong whenever anything fails.
**Evidence:** first-hand, `file:line` above in `toolshop/batch.py`.
**Consequence:** the spec requires the sample run to use a **separate status path and output root**,
never the corpus one, and specifies that the count verification derive its expected total by
**re-enumerating the input directory**, never by reading `total_tracks` from the status file.

---

### J-005 — A subagent that writes its deliverables at the end has no partial-credit failure mode · 2026-09-01 · orchestration
**Status:** verified — **first-hand, this session**
**Expected:** an agent interrupted part-way through would leave part-way-finished output behind. The
orchestration's whole recovery story assumed this: fragments in `journal_inbox/` exist precisely so
work can be merged incrementally.
**Found:** **nothing survived.** Wave 2 Agents C and D were both killed by a session rate limit after
roughly twenty minutes of investigation each. `journal_inbox/` held only its own README; neither
spec existed; `git status` was byte-identical to before dispatch. Both agents had done real work —
C had got as far as suspecting a defect in the instrument recognizer, D was about to inspect the
real transcripts — and **all of it was in their heads, none of it on disk.**
**Evidence:** first-hand. After both failure notifications: `ls docs/superpowers/journal_inbox/` →
`README.md` only; `ls docs/superpowers/specs/ | grep 2026-09-01` → only the two **Wave 1** specs;
`git status --short` → unchanged, still just the declared other-session paths.
**Consequence:** recovered by **resuming both agents from their transcripts** rather than respawning
them cold — the investigation was preserved after all, but by the harness, not by the design. That
is luck, not architecture: a resume is not always available.
The design defect is mine. The journal contract already said *"the journal is appended **during** the
work, not at the end"* — written against a *quality* failure (a finding reconstructed at close-out is
a memory of a finding). **It turns out to be a durability rule as well**, and I wrote it for one
reason without noticing it bought the other. Agent briefs must now say so explicitly: **write the
fragment as each finding lands, and draft the spec section by section.** An agent that batches its
output converts any interruption into total loss.

---

### J-006 — The handlers protecting M6's three field-groups all raised `NameError` · 2026-09-01 · reverse-engineering
**Status:** verified and **fixed** — first-hand, this session
**Expected:** `_basic_analysis` degrades gracefully. Each of beat-grid, structure and premaster sits
inside `try/except` with a `logger.warning(...)` and a fallback — visibly defensive code.
**Found:** **`logger` was never defined in the module.** Three references (lines 74, 97, 107), no
`import logging`, no assignment. So any failure in those three stages raised `NameError` *from inside
the handler meant to absorb it* — a recoverable stage failure converted into a crash, in exactly the
three field-groups M6 depends on (`J-024`).
It survived because **both existing tests that touch `_basic_analysis` mock it out entirely**
(`@patch("toolshop.reverse_engineering_adapter._basic_analysis")`). The function body had never
executed under test. A green suite said nothing about it.
**Evidence:** first-hand. `grep -n logger toolshop/reverse_engineering_adapter.py` → three
`logger.warning` calls; `grep -n "^import logging\|logging.getLogger"` → nothing. After adding the
logger and three tests that force each stage to raise: **14 passed**. With the logger removed again:
**4 failed, 10 passed** — the three degradation tests plus the direct one.
**Consequence:** fixed, with tests that run the real function instead of mocking it. Third
undefined-name defect this project has found hiding behind an exception handler — `J-001`
(`production_analyzer`, swallowed `NameError` → zero fingerprints), the `#053` doctor incident, and
now this. **The pattern is not "we make typos"; it is that error paths are the least-executed code in
the repo and the suite systematically mocks past them.** A handler nothing ever triggers is
indistinguishable from a handler that crashes.

### J-007 — My own verification probe read the wrong field and returned a confident zero · 2026-09-01 · method
**Status:** retracted mid-check — first-hand, this session
**Expected:** spot-checking Agent C's claim that the chord data contradicts the declared `mode`, my
probe read each chord entry's `chord` key.
**Found:** the field is `name`. Every lookup returned `None`, every track filtered out, and the probe
printed a clean **`tracks with chords: 0 | agree: 0 | DISAGREE: 0`** — which reads like a refutation
of the agent and is in fact a measurement of nothing. Re-run against `name`: **212 tracks with
chords, 170 disagree with the declared `mode`, 42 agree** — matching the agent's 170/212 exactly.
**Evidence:** first-hand, both runs. Correct probe: `chord_progression[].name`, minor detected by
`re.search(r'm(?!aj)', name)`.
**Consequence:** the agent's claim stands, and is corpus-scale confirmation of `J-025` using the
backend's **own chord output as the control** — `mode` says 96.8% major while the chords say
predominantly minor on 80% of tracks. Method note for me, the third instance today after `J-003`:
**a verification that returns an empty result is not a negative finding until you have proved the
probe can produce a positive one.** An empty result and a broken query look identical.

---

## Wave 2 Agent C — backend trade-off (merged 2026-09-01)

> Merged from `journal_inbox/agentC.md`. Full write-up: `specs/2026-09-01-backend-tradeoff.md`.
> **Recommendation: (a) narrowed — port the four field-groups into `_advanced_analysis`, and switch
> off `separation`, `instruments` and `notes` while doing it.**
>
> **Orchestrator spot-check.** Re-run here before merging:
>
> | Claim | My check | Result |
> |---|---|---|
> | `logger` undefined → `_basic_analysis` handlers crash | `grep` for references vs definition; then fix + tests both ways | **holds** — see `J-006`, now fixed |
> | `separation` is a constant | distinct JSON blocks across the corpus | **holds** — **1** distinct block, 221 dossiers |
> | `notes.duration` hard-coded | value distribution over 191,339 entries | **holds** — every sampled entry is `0.1` |
> | `rt60_seconds` tracks duration, not reverb | Pearson r and median over 221 | **holds** — **r = 0.946**, median **200.1 s** |
> | Chords refute the declared `mode` on 170/212 | corpus scan of `chord_progression[].name` | **holds** — 212 with chords, **170 disagree**, 42 agree (my first probe read the wrong field and returned a false zero — `J-007`) |
>
> **Not re-run by me:** the `librosa.pyin` tuple bug in the instrument heuristic and its predicted
> 0.7667 vocals floor; the mtime-differenced cost figure (≈0.7× realtime, median 114 s/track). Both
> are argued in the spec with their working shown. Treat as evidenced, not re-run.
>
> **What this does to the ruling.** The user chose "investigate before choosing a shape" precisely
> because `_advanced_analysis` was assumed to be the richer backend that we would be giving something
> up to leave. **The investigation dissolved that premise.** Of the seven fields only advanced emits,
> `separation` is a constant, `instruments` never reaches its ML backend and its heuristic is broken,
> and `notes` is largely an fmin-floor artefact with a hard-coded duration. Four fields carry real
> information. A **200-second reverb tail** is not a marginal quality issue — it is a field that has
> never once been right, in a dossier that has been treated as a source of truth for 221 tracks.
>
> One correction to the recommendation as stated: option (c) was rejected partly because
> `_basic_analysis`'s handlers crash. **That is no longer true** — `J-006` fixed it. (c) is still the
> wrong choice, but for the honest reason: it would drop `chord_progression`, `tuning_offset` and
> `onset_strength`, which do carry information. The blocker was removed; the argument stands without it.
> **No code was written, no batch was run, nothing under `data/` or `results/` was modified.**
> Companion design: `docs/superpowers/specs/2026-09-01-backend-tradeoff.md`.

---

### J-040 — The corpus contains no output of the *current* `_basic_analysis`, so there is no real side-by-side · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session. Refutes a premise of my own task.**
**Expected:** the corpus's single `basic_librosa` dossier gives a genuine side-by-side against the 221
`wav_reverse_engineer` ones, so the field-level diff can be read off disk.
**Found:** it does not. That file has **11 keys and none of the M1–M4 fields** — no `beat_grid`, no
`structure`, no `premaster`, no `key_confidence`. It is output of a *pre-M1* `_basic_analysis`, written
`2026-07-15T21:35:04`, 464 bytes, while M1–M4 landed later. **Zero files in the corpus were produced by
the `_basic_analysis` that exists today**, so the on-disk diff measures the old fallback, not the
candidate.

The two diffs are therefore different questions and must not be conflated:

| Diff | advanced-only | basic-only |
|---|---|---|
| **on disk** (221 vs 1, both stale) | `chord_progression`, `effects`, `instruments`, `notes`, `onset_strength`, `separation`, `tuning_offset` (7) | **none** |
| **in code today** (`:52-133` vs `:137-210`) | the same 7 | `beat_grid`, `structure`, `premaster`, `key_confidence`, `key_alternate`, `key_margin` (6) |

**Evidence:** first-hand census over `results/crhymetv_re/per_track/*/*_analysis.json`
(222 files, 0 unreadable, `*_voice_analysis.json` excluded), run in `.venv`:

    advanced: 221 basic: 1
    only advanced : ['chord_progression', 'effects', 'instruments', 'notes',
                     'onset_strength', 'separation', 'tuning_offset']
    only basic    : []
    BASIC dossier mtime: 2026-07-15T21:35:04.234117  size: 464
      keys : ['analysis_backend','beat_count','bpm','duration_seconds','file','harmonic_ratio',
              'key','mode','sample_rate','spectral_bandwidth','spectral_centroid']
      has beat_grid/structure/premaster/key_confidence: [False, False, False, False]

**Consequence:** option (c) "switch the batch to `basic`" is a switch to code with **zero corpus-scale
exercise**, not to a path the corpus has already validated. J-046 shows what is sitting in it. The
field-level diff in the spec is taken from source, not from disk, for exactly this reason.

---

### J-041 — `separation: "hpss"` is a byte-identical constant across all 221 dossiers; the separation is computed and thrown away · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** `separation="hpss"` is one of five capabilities the batch switches on
(`run_reverse_engineering_batch.py:210-214`), so it contributes per-track information.
**Found:** it contributes **none**. `separate_hpss` returns `{"harmonic": y_h, "percussive": y_p}`
(`.../audio_analyzer/source_separation.py:7-9`), and the adapter stores only
`list(stems.keys())` — the audio is discarded at `reverse_engineering_adapter.py:196-199`. Every one
of the 221 dossiers therefore carries the same string:

    221 x {"method": "hpss", "stems": ["harmonic", "percussive"]}

That is a full `librosa.effects.hpss` pass over every track to serialise a constant that could be a
literal. **It is the third hpss of the track** (J-049).
**Evidence:** first-hand, census of `json.dumps(d["separation"], sort_keys=True)` over the 221
advanced dossiers — exactly 1 distinct value, count 221; plus `file:line` above.
**Consequence:** `separation` is dropped from the v2 recommendation, and it is the clearest single
instance of the pattern in J-042/J-044 — a flag that is on, produces output, and carries no
information. **Checking the flags would have counted this as a working capability.**

---

### J-042 — `instruments` never reaches its ML backend, and a `librosa.pyin` tuple bug makes the "vocals" tag unconditional · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. Two defects stacked.**
**Expected:** `instruments=True` runs PANNs audio tagging and yields a per-track instrument profile.
**Found (a) — the ML path is dead in this venv.** `InstrumentRecognizer.__init__` imports
`panns_inference` inside a bare `try/except` and sets `self._panns = None` on failure
(`.../instrument_recognizer.py:6-13`); `recognize` then silently falls through to
`_heuristic_predict`. `panns_inference` is **not installed**:

    panns_inference MISSING ModuleNotFoundError No module named 'panns_inference'
    torch OK 2.6.0+cpu   librosa OK 0.11.0   pyloudnorm OK

So 221/221 dossiers are heuristic output from a fixed 5-label vocabulary
(`drums/percussion`, `guitar/piano`, `vocals`, `bass`, `unknown`), and nothing in the dossier records
that the ML path was skipped. This is precisely the silent-fallback failure AGENTS.md's
"fallback paths must be declarable" rule was written against — there is no `--require-advanced`
equivalent here and no field naming which path ran.

**Found (b) — the heuristic's vocal test is arithmetically broken.** At
`.../instrument_recognizer.py:38-41`:

```python
f0 = librosa.pyin(audio, fmin=80, fmax=1000, sr=sr, frame_length=2048, hop_length=256)
voiced = np.isfinite(f0)
voiced_ratio = float(np.mean(voiced)) if f0 is not None else 0.0
```

`librosa.pyin` returns a **3-tuple** `(f0, voiced_flag, voiced_prob)`. `np.isfinite` on the tuple
coerces it to shape `(3, N)`; rows 2 and 3 are finite everywhere, so
`voiced_ratio == (true_ratio + 2) / 3`, floored at **0.667**. The vocals score
`min(1.0, 0.3 + 0.7 * voiced_ratio)` therefore cannot fall below **0.7667**. Verified on a synthetic
signal that is 50% tone / 50% silence, in `.venv`:

    type(f0) = tuple len = 3
    np.asarray(f0).shape = (3, 173)
    voiced_ratio AS WRITTEN     = 0.8401
    voiced_ratio IF f0[0] USED  = 0.5202          <-- (0.5202 + 2)/3 = 0.8401 exactly
    vocals score AS WRITTEN     = 0.8881
    theoretical floor 0.3+0.7*(2/3) = 0.7667

The corpus matches the prediction exactly — **no vocals score anywhere in 217 tracks falls below the
0.7667 floor**, and the tag fires almost unconditionally:

    score[vocals]  n=217  min=0.80697 med=0.86563 max=0.97578
    label freq: vocals 217, guitar/piano 207, drums/percussion 195, bass 6, unknown 1
    label-SET frequency:
       182 x ('drums/percussion', 'guitar/piano', 'vocals')     <-- 82.4% of the corpus, identical
        20 x ('guitar/piano', 'vocals')
         7 x ('drums/percussion', 'vocals')

**Evidence:** first-hand — the `file:line` above, the venv import probe, the synthetic `pyin` run, and
the corpus census of `instruments[].label` / `.score` over 221 dossiers.
**Consequence:** `instruments` is a near-constant on this corpus (82.4% share one label set) and its
strongest label is produced by a bug. It is not evidence that a track has vocals. Nothing downstream
should read it — note `run_reverse_engineering_batch.py:224` writes these labels into every
`recipe.md`, so 221 recipes carry it. Dropped from the v2 recommendation.

---

### J-043 — The advanced backend's `mode` is contradicted by the advanced backend's own chord detector, on the same chroma · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. Independent corpus-scale confirmation of J-025.**
**Expected:** J-025 established `mode` is broken (215/222 major on German rap) by reading
`feature_extractor.py:190`. My prior was that only an *external* detector could demonstrate the error.
**Found:** the refutation is already inside the same dossier. `detect_chords`
(`.../feature_extractor.py:196-247`) labels each frame from the *same* `chroma_cqt` with the *same*
`> 0.5` threshold, and its verdict is the opposite:

    chord entries: minor=3315  major=585   minor_frac=0.8500
    tracks whose chords are 100% minor: 70 / 212
    per-track minor chord frac: p25=0.706 med=0.909 p75=1.000
    mode field: major 214 / minor 7   (of 221 advanced)

    CROSS-CHECK, per track, `mode` vs that track's own chord majority:
      agrees: 42    disagrees: 170          <-- 80.2% self-contradiction

The `key` field fares no better against the same block — the modal chord root equals `key` on only
**88 of 212** tracks (41.5%), i.e. the backend's tonic disagrees with its own most-played chord root
on ~3 tracks in 5.

85% minor is the musically expected answer for a German drill/rap catalogue; 96.8% major is not.
The two numbers come from one chroma matrix in one function call, so this is not a disagreement
between estimators — it is one of them being wrong, and the corpus says which.
**Evidence:** first-hand census over the 221 advanced dossiers (212 with a non-empty
`chord_progression`; 9 have `[]`), plus `file:line` above.
**Consequence:** raises the confidence of J-025 from "a defect visible in the source" to "a defect the
corpus refutes using the backend's own output". Strengthens the case for porting the K-S key into
`_advanced_analysis` (spec §Recommendation). It also means the *chord* block, unlike `key`/`mode`, is
producing a musically plausible signal and should be carried forward, not discarded.

---

### J-044 — 23% of the corpus's 191,339 detected notes are the pitch-detector's floor, and every note has the same hard-coded duration · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** `notes=True` yields a note-level transcription — the most detailed block in the dossier
(median 777 notes/track) and the one most plausibly worth its cost.
**Found:** it is dominated by a floor artefact and two hard-coded values.

`detect_notes` (`.../feature_extractor.py:249-317`) runs `librosa.yin` on a **2048-sample window** —
one frame — at each onset, with `fmin=65.41` (C2), and keeps `f0[0]`. YIN on a single frame of a full
mastered mix returns the floor whenever it finds no periodicity, which on drum-heavy material is
often:

    total notes: 191339
    C2 (== the fmin floor, 65.41 Hz): 43766 = 22.87% of all notes
    tracks whose single most common pitch is C2: 186 / 221
    per-track C2 fraction: p25=0.157 med=0.232 p75=0.302 max=0.550
    frequencies at or below fmin (65.41 Hz): 35242 / 191339
    note frequency: min=65.237  p05=65.237   <-- the 5th percentile IS the floor

Separately, two fields are not measurements at all:
- `duration` is the literal `0.1` for **all 191,339 notes** (`feature_extractor.py:313`, comment
  `# Default duration, could be improved`).
- `confidence` is `np.clip(np.mean(np.abs(segment)) * 2, 0, 1)` (`:307`) — segment *loudness*, not
  pitch confidence. A loud drum hit scores high precisely where the pitch is least trustworthy.

**Evidence:** first-hand census over all `notes[]` entries in the 221 advanced dossiers, plus
`file:line` above.
**Consequence:** `notes` is the single largest block in the dossier and roughly a quarter of it is the
detector saying "I found nothing". The onset *times* are real; the pitches, durations and confidences
are not. Recommended for v2 as onset times only, or dropped — see the spec. Same class as J-041 and
J-042: **switched on, produces volume, carries little.**

---

### J-045 — `effects.rt60_seconds` measures track length, not reverberation · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** `effects` is the block with the most credible per-track physics — RT60, spectral tilt,
THD, loudness — and would be the main thing lost by leaving the advanced backend.
**Found:** its headline field is not a measurement of the room. `estimate_rt60`
(`.../effects_analyzer.py:21-38`) runs Schroeder backward integration over **the entire song** and
fits the −5 dB → −35 dB slope. On a continuous musical signal the energy-decay curve descends across
the whole track, so the slope is set by the track's length, not by any decay tail:

    pearson(duration_seconds, rt60_seconds)  = 0.9458
    spearman(duration_seconds, rt60_seconds) = 0.7923
    rt60/duration ratio: min 0.346  med 1.183  max 2.316
    rt60_seconds: min=3.35  med=200.13  p95=611.08  max=3441.9   (seconds)
    tracks with rt60 > 20 s: 219 / 221

**A median RT60 of 200 seconds is physically impossible** — the most reverberant spaces ever measured
are ~15 s. The field is, to r=0.95, a restatement of `duration_seconds`, which the dossier already
carries. Schroeder integration requires an impulse response; it was applied to a song.

Two neighbours in the same block are dimensionally incoherent rather than wrong-by-correlation:
`compression_index` is `(1/crest) * (1/(var+1e-6))` (`:76-84`) — an unnormalised product carrying
units of inverse variance, corpus range 4.47 → 194.68 with p95 34.5; and `thd_ratio` (`:41-61`) takes
the loudest bin of a song's mean spectrum as "f0" and calls the bins at 2f0…5f0 "harmonic distortion",
which on music are simply other notes (median 0.512 — i.e. "51% THD", which no released master has).

The block is not worthless: `spectral_tilt_db_per_decade` (med −22.9), `loudness_lufs` (med −12.6) and
`loudness_range` (med 6.3) are real quantities honestly computed. But `loudness_lufs` is measured on
the **22.05 kHz mono downmix** that `AudioProcessor.load_audio` returns
(`.../audio_processor.py:34-40`), so it is not the track's true integrated LUFS, and
`toolshop/premaster.py:111-119` already computes that correctly from the stereo file.
**Evidence:** first-hand correlation and distribution census over the 221 advanced dossiers, plus
`file:line` above.
**Consequence:** of the 6 `effects` sub-fields, 1 is a duration proxy, 2 are dimensionally
incoherent, 1 is superseded by `premaster`, and 2 are worth keeping. This is the finding that decides
the trade-off: **advanced provides substantially less than assumed.**

---

### J-046 — `_basic_analysis`'s three fallback handlers all raise `NameError`; `logger` is never defined · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. A live defect in the candidate for option (c).**
**Expected:** `_basic_analysis` degrades gracefully — each of `beat_grid`, `structure` and `premaster`
is wrapped in `try/except` and logs a warning before continuing with `None`.
**Found:** it cannot. `toolshop/reverse_engineering_adapter.py` uses `logger.warning(...)` at lines
**74, 97 and 107** — all three inside `except Exception:` blocks — and **the module never imports
`logging` or defines `logger`.** Verified in `.venv`:

    adapter has logger attr: False
    adapter module globals with log: []
    logger. occurrences in _basic_analysis: 3
    calling logger.warning in adapter namespace -> NameError: name 'logger' is not defined

So any failure in beat-grid, structure or premaster analysis does **not** degrade to `None` — the
handler itself raises `NameError`, which propagates out of `_basic_analysis` and fails the whole
track. Worse, when reached via `analyze_track`'s advanced→basic fallback (`:255-261`), the original
exception is already swallowed into a `warnings.warn`, so the operator sees an unrelated `NameError`
in place of the real cause.

This has never been caught because it is unreachable in the test suite: both tests that touch the path
(`tests/test_reverse_engineering_adapter.py:51` and `:64`) **mock `_basic_analysis` out entirely**, and
J-040 shows no corpus dossier was produced by the current version of the function.
**Evidence:** first-hand, `file:line` above and the venv probe.
**Consequence:** **option (c) — switch the batch to `basic` — must not be taken as-is.** It would run
222 tracks through a function whose only three error handlers are themselves broken, with no corpus
exercise and no real test coverage. Fixing it is one import line, but the fix must land *before* the
option is viable, and it should carry a test that exercises a raising stage rather than mocking the
function away.

---

### J-047 — The advanced backend costs ~0.7× realtime, ~10 h for the corpus; this is recoverable from artifacts, and no `basic` measurement exists at all · 2026-09-01 · M6
**Status:** verified (advanced) / open (basic) — **first-hand derivation, this session**
**Expected:** no per-track cost is recoverable, because the batch logs are unstamped and
`batch_status.json` records no per-item timing — so the trade-off would have to be argued without a
cost number. (`batch_status.json` carries only `started`, `finished` and one aggregate
`duration_seconds: 43708.1`, spanning 2026-07-07 → 2026-07-16 across resumed sessions, so it is not a
per-track figure.)
**Found:** it is recoverable. The `batch_offset141` run used `--no-stems`, and every track writes
`<stem>_analysis.json` and then `<stem>_voice_analysis.json`. Differencing the two mtimes isolates the
voice/effects stage; differencing the previous track's voice file against this track's analysis file
isolates the advanced analysis stage. 81 tracks, monotonic mtimes, one run:

    === derived from file mtimes, offset141 run (--no-stems), n=80 ===
    advanced analysis   min=31.8  p25=93.5   med=114.2  mean=169.9  p95=547.5  max=1177.4  s
    voice/effects       min=71.5  p25=211.3  med=249.1  mean=370.2  p95=1177.7 max=2497.5  s
    RTF advanced        min=0.6   p25=0.6    med=0.7    p95=0.9     max=1.0    x
    RTF voice/effects   med=1.5                                                x
    span: 12.10 h for 81 tracks -> 8.96 min/track wall
    longest track: dur=1632.2 s -> adv=1177.4 s (rtf 0.721)   [scales linearly, no clip artefact]

At RTF ≈ 0.7 against the 14.71 h corpus (J-021), `_advanced_analysis` alone is **≈ 10 h**. That is not
a rounding error next to the ~13 h lyrics stage — it is comparable to it.

**Discipline caveats, stated so this is not read as a benchmark.** This is derived from a production
run's artifacts, not a controlled measurement: no warm-up was discarded, no baseline was repeated,
the machine's concurrent load is unknown, and each interval includes JSON/recipe writes and status
flushes. It is an **upper bound on advanced analysis, good to roughly ±20%**, and it satisfies
AGENTS.md only as a planning figure — not as the "measured min/track before merge" a feature merge
requires. The RTF is stable across a 22× duration range (7 s → 1632 s) and holds on the 27-minute
track, which is the check AGENTS.md asks for against clip-inflated numbers.

**`_basic_analysis` has no measurement, and none is derivable** — J-040 shows no corpus artifact was
ever produced by it. The spec's 30–45 s/track is
`unverified — source: docs/superpowers/HANDOFF-2026-08-31.md:172`. Obtaining it requires timing
`beatgrid.analyze_beats` + `structure.segment_track` + `premaster.analyze_premaster` +
`key_detection` over a stratified handful of corpus tracks in `.venv`, warm-up discarded and baseline
repeated. **I did not run it** — the brief forbids running analysis jobs, and an estimate presented as
a measurement is the J-000g error.
**Evidence:** first-hand, the mtime derivation above (script logic: pair each slug from
`results/crhymetv_re/batch_offset141.log` with its two output files' `st_mtime`).
**Consequence:** cost is now a real input to the decision rather than a guess. It kills option (b)
outright — running both backends means paying the ~10 h advanced cost *and* the basic cost for
fields J-041/J-042/J-044/J-045 show are largely non-informative.

---

### J-048 — `_advanced_analysis` already computes the exact inputs M1 and M3 need, and discards them · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. This is what makes option (a) cheap.**
**Expected:** porting the K-S key and beat grid into `_advanced_analysis` means adding their compute
cost on top of the advanced backend's existing ~0.7× RTF.
**Found:** for the key, it adds **nothing**. `FeatureExtractor.extract_features` returns **22 fields**
and `_advanced_analysis` reads **10** (`reverse_engineering_adapter.py:148-161`). The 12 discarded
include the two the port needs:

- **`features["chroma"]`** is `np.mean(chroma, axis=1).tolist()`
  (`.../feature_extractor.py:159-166`) — a 12-element mean chroma vector, C-first from `chroma_cqt`.
  `key_detection.detect_key_from_chroma` requires exactly *"12 values, one per pitch class, C first"*
  (`toolshop/key_detection.py:86-97`), and `PITCH_CLASSES` is
  `['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']` — verified in `.venv`, an exact match.
  **The K-S key block is a one-line addition over data already in hand, at zero extra compute.**
- **`features["beat_times"]`** is already computed (`.../feature_extractor.py:139-145`). It is not
  quite sufficient for `beatgrid.analyze_beats`, which also needs the `onset_env`
  (`toolshop/beatgrid.py:125-134`) to estimate downbeat phase — and `extract_features` computes that
  too (`:128-130`) but does not return it. So the beat grid costs one extra `onset_strength` +
  `beat_track` pass, or nothing at all if the vendored function's return dict is widened by one key.

The other 10 discarded fields are `samples`, `rms_energy`, `zero_crossing_rate`, `sample_rate`,
`spectral_contrast`, `mfcc` (20 coefficients), `spectral_rolloff`, `beats_per_second`, `onset_times`
and `pitch_centroid` — all computed, none serialised.
**Evidence:** first-hand, `file:line` above; `PITCH_CLASSES` printed from `.venv`.
**Consequence:** the cost objection to option (a) is much weaker than it appears. Only `structure` and
`premaster` are genuinely new work; `key` is free and `beat_grid` is near-free. Recorded in the spec's
Recommendation.

---

### J-049 — The advanced backend runs HPSS three times and CQT chroma three times per track · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** the five capability flags each add a distinct analysis, so the backend's cost is roughly
the sum of five non-overlapping computations.
**Found:** they overlap heavily, and two of the most expensive primitives run three times each on the
same audio within a single `_advanced_analysis` call:

| Pass | HPSS (`librosa.effects.hpss`) | CQT chroma (`librosa.feature.chroma_cqt`) |
|---|---|---|
| 1 | `_extract_harmonic_features` → `harmonic_ratio` (`feature_extractor.py:150`) | `_extract_harmonic_features` (`:156`) — **result discarded by the adapter** |
| 2 | `InstrumentRecognizer._heuristic_predict` (`instrument_recognizer.py:26`) | `_estimate_key`, recomputed inside the call the line above already had chroma for (`:174`) |
| 3 | `separate_hpss` — **output discarded**, J-041 (`source_separation.py:8`) | `detect_chords` (`:213`) |

On top of that, `_heuristic_predict` runs a full-track `librosa.pyin` at `hop_length=256`
(`instrument_recognizer.py:38`) — probabilistic YIN, the single most expensive call in the backend —
purely to compute the `voiced_ratio` that J-042 proves is broken; and `detect_notes` issues one
`librosa.yin` per onset, a median of **777** and a maximum of **5228** calls per track.

So the ~0.7× RTF of J-047 is not the price of seven fields. A large share of it buys a constant
(J-041), a bug-driven near-constant (J-042), a floor artefact (J-044) and a duration proxy (J-045).
**Evidence:** first-hand, source read at every `file:line` above; onset counts from the corpus census
(`n_notes per track: min/med/max = 13 / 777 / 5228`).
**Consequence:** the backend is not cheap-for-what-it-does; it is expensive for what it does. This is
the structural reason the recommendation keeps only the chord block and two `effects` scalars, and it
means a trimmed advanced path would be materially faster than the measured 0.7× — though **by how
much is unmeasured**, and that measurement is a prerequisite named in the spec.

---

### J-008 — I broke `J-004`'s rule within the hour, because the rule named the wrong thing · 2026-09-01 · orchestration
**Status:** verified — first-hand, self-inflicted, **second occurrence**
**Expected:** `J-004` established the rule after I swept a live agent's work into the wrong commit:
*"while any agent is live, stage explicit paths, never `-A` and never a directory."* I then staged
`docs/superpowers/JOURNAL.md`, the spec, **and `docs/superpowers/journal_inbox/`** — a directory —
while Agent D was still writing into it. 300 lines of `agentD.md` went into a commit about Agent C.
**Found:** the rule was correct and I still broke it, which means the rule was not the fix. Two
reasons, and the second is the real one:
1. I read my own staging list as "explicit paths" because every entry was typed out. A typed
   directory is still a directory.
2. **`journal_inbox/` is, by construction, the one directory live agents write into.** It exists for
   exactly that. So of all the paths in the repo, it is the single one where a directory-level stage
   is guaranteed to collide whenever anything is running. `J-004` phrased the rule generically and so
   pointed at nothing in particular.
**Evidence:** first-hand. `git show --stat 8fd2cc7` → three files, one of them
`docs/superpowers/journal_inbox/agentD.md | 300 ++++`. Agent D had produced no completion
notification.
**Consequence:** not rewritten — same reasoning as `J-004`, a false-clean history is worse than an
honest wrong one, and this is now a documented pair rather than an isolated slip. **Rule sharpened:**
never stage `journal_inbox/` as a directory at all; stage the specific fragment being merged, by
name, and only after its agent has reported completion. The generic form of the rule survives but it
is the specific one that will actually fire.
The generalisable point is about rule-writing, not git: **a rule stated at the level of the category
("don't stage directories") does not fire at the moment of the mistake, because at that moment you
are thinking about a particular path, not about the category.** `J-004` needed to name
`journal_inbox/`. It did not, so it did not work.

---

## Wave 2 Agent D — alignment windowing layer (merged 2026-09-01)

> Merged from `journal_inbox/agentD.md`. Full write-up:
> `specs/2026-09-01-alignment-windowing-layer.md` (762 lines, 20-test plan against a `FakeAligner`,
> all runnable with whisperX absent). **Recommendation: 25 s windows with a 2.5 s aligned context
> margin each side.** Nothing installed; whisperX confirmed still absent.
>
> **Orchestrator spot-check.** Re-run here before merging:
>
> | Claim | My check | Result |
> |---|---|---|
> | Word-level coverage is **49.2%**, not 69% | summed word durations vs summed segment durations over `borba-015.large-v3.temp0.json` | **holds exactly** — segment-time **69.1%**, word-time **49.2%**, 26 segments, 188 words, 249.48 s |
> | One transcript, two alphabets | regex over segment texts | **holds** — **12** segments contain Cyrillic, **14** contain Latin, same run |
> | `Transcript.source` lies | read every transcript's `source`; `grep` the default | **holds, and worse than stated** — **all six** report `full_mix`, including one whose filename is explicitly a separated stem (`..._Vocals__model_bs_roformer...`). Default at `toolshop/transcribe.py:367` |
> | SFX directions rival sung lines | counted both in `docs/lyrics/ULICNI_KODEKS_ARTIST.md` | **holds directionally** — sung lines **47** (exact match), bracketed directions **58** by my broader regex vs the agent's **52**; the difference is whether `[Chorus]`/`[Artist Name]` count as directions. Either way they **outnumber** the sung lines |
>
> **Not re-run by me:** the window-length sweep and the 1.20× compute figure; the `_supports_sdpa`
> correction to Wave 1's OOM arithmetic; the empty transcript ∩ lyric-sheet intersection.
>
> **`J-050` is the finding that resizes the problem — again.** Every coverage number this project has
> quoted, including the one the user just ruled on, is **segment-time**. Word-level coverage is
> **49.2%**. One nominally-covered segment runs 22.34 s and contains **3 words**, with a 19.26 s
> internal hole. So "close the 31% gap" was already the wrong target: **the gap is half the track.**
> The ruling to build the windowing layer is unaffected — if anything it is reinforced — but the
> scope it was made against was understated by ~18 points.
>
> **`J-051` is a model refutation done right.** The agent's own shortcut — gate the gaps by energy —
> was tested and killed: the gaps are not silence, they are *loud*. p95 in the 48 s head is
> **−22.3 dBFS** against **−21.9** in confirmed vocal, and one gap is **2.2 dB louder** than anything
> transcribed. That is a hypothesis refuted at the cost of proposing it, which is exactly what the
> journal is for.
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
