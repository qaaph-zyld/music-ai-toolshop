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
