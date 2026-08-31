# whisperX forced alignment — feasibility (P3)

> Written 2026-09-01 by Wave 1 Agent A. Read-only investigation: **nothing was installed.**
> Every dependency claim below comes from `pip install --dry-run --report`, which resolves against
> the real venv without modifying it. Commands are quoted inline.
> Machine: Intel i7-4770 (4C/8T, 3.4 GHz, Haswell — AVX2/FMA, **no AVX-512, no VNNI**), 15.9 GB RAM,
> 120.1 GB free on `D:`. Venv: Python 3.11.9 at `D:\Projects\Music-AI-Toolshop\.venv`.

---

## Verdict

**GO — with three binding conditions, and one correction to the premise that motivated the question.**

whisperX forced alignment is adoptable. The feared blocker did not materialise: **whisperX introduces no
protobuf constraint that collides** — every protobuf-touching package it pulls sets a *lower* bound
satisfied by the installed 7.36.0, and under a torch pin protobuf is not touched at all. The real
collision is **torch**: an unpinned `pip install whisperx` selects 3.8.6, which requires `torch~=2.8.0`
and would break `classla`'s `torch<=2.6` while also downgrading `transformers` 5.14.1 → 4.57.6 and
`huggingface-hub` 1.23.0 → 0.36.2. That is entirely avoidable by pinning `whisperx==3.4.5`. Alignment-only
genuinely needs **no HuggingFace token** — verified, not assumed: the Croatian alignment model reports
`gated: False` and whisperx 3.4.5 lazy-imports the diarization module, so `pyannote.audio` is installed
but never imported on the alignment path. The conditions are: **(1)** install into a **sidecar venv**, not
`.venv`, because every whisperX version that keeps torch at 2.6 also drags `ctranslate2` 4.8.1 → 4.4.0,
swapping the inference engine underneath the only reproducible measurement the transcription lane has
(J-000e); **(2)** pin the version, never install unpinned; **(3)** land a `--require-alignment` guard
before first real use.

**The correction:** the plan says forced alignment "sidesteps the 31% entirely." It does not, not by
itself. `whisperx.align()` consumes segments that already carry `start`/`end` — it *refines* a
segmentation, it does not produce one from a bare lyric sheet. Fed the existing ASR segmentation, the
31% with no segment still gets no alignment. Full coverage needs our own windowing layer on top. That is
buildable and worth building, but it is our work, not whisperX's.

---

## Install & Offline Operation

### What the resolver actually says

Three dry-runs, escalating constraints. None modified the environment.

**A — unpinned.**
```
.venv\Scripts\python.exe -m pip install --dry-run --report whisperx_report.json whisperx
```
Selects **whisperx 3.8.6**. 52 dists would be installed/changed:
```
huggingface-hub: 1.23.0 -> 0.36.2      transformers: 5.14.1 -> 4.57.6
torch:           2.6.0  -> 2.8.0       torchvision:  0.21.0 -> 0.23.0
urllib3:         2.7.0  -> 1.26.20     requests:     2.28.0 -> 2.34.2
+ torchaudio 2.8.0, torchcodec 0.7.0, pyannote-audio 4.0.7, lightning 2.6.5,
  pytorch-lightning, optuna, SQLAlchemy, alembic, Mako, grpcio, the full
  opentelemetry stack, googleapis-common-protos, nltk, omegaconf, aiohttp …
```

**B — torch held at 2.6.**
```
.venv\Scripts\python.exe -m pip install --dry-run -c keep_torch.txt --report whisperx_torch26.json whisperx
   # keep_torch.txt: torch==2.6.0, torchvision==0.21.0
```
Backtracks to **whisperx 3.4.5** + pyannote.audio 3.4.0 + speechbrain 1.1.1. Changes only
`ctranslate2 4.8.1 -> 4.4.0` and `urllib3 2.7.0 -> 1.26.20`. **Trap:** it also selects
`torchaudio 2.11.0` against `torch 2.6.0` — torchaudio declares no torch pin, so pip permits a
pairing that will fail at import on C++ ABI. Pin `torchaudio==2.6.0` explicitly.

**C — minimal-harm (recommended shape).**
```
.venv\Scripts\python.exe -m pip install --dry-run -c minimal.txt --report whisperx_minimal.json whisperx
   # minimal.txt: torch==2.6.0, torchvision==0.21.0, torchaudio==2.6.0, urllib3==2.7.0, protobuf==7.36.0
```
Selects **whisperx 3.4.5**. **44 dists, 52.4 MB of wheels** (measured by summing `Content-Length`
over every wheel URL in the report). Only two version changes to the existing environment:
`ctranslate2 4.8.1 -> 4.4.0` and `requests 2.28.0 -> 2.34.2`. torch, torchvision, protobuf,
transformers and huggingface-hub are all left alone.

**D — zero-regression.** Adding `ctranslate2==4.8.1` and `transformers==5.14.1` makes it
`ResolutionImpossible`:
```
whisperx 3.4.0 depends on ctranslate2<4.5.0
whisperx 3.3.6 depends on ctranslate2<4.5.0
...
whisperx 3.2.0 depends on ctranslate2==4.4.0
```
No whisperX version accepts both `torch<=2.6` and `ctranslate2>=4.5`. **The fork is genuine** — see
Dependency Collision Analysis.

### HuggingFace token — confirmed, not assumed

The token is a *diarization* requirement and alignment-only genuinely avoids it. Two independent
first-hand checks:

```
classla/wav2vec2-xls-r-parlaspeech-hr   gated: False   private: False   downloads: 823787
pyannote/speaker-diarization-3.1        gated: auto    private: False   downloads: 9578771
```
(HF model API, `?blobs=true`.) The alignment model is **ungated**; the gated repo is the diarization
pipeline, which is only reached through `assign_word_speakers`.

Second: `whisperx/__init__.py` at tag `v3.4.5` uses a `_lazy_import` helper — `diarize` is imported
*inside* `assign_word_speakers()`, not at module load. So `pyannote.audio` is installed by pip but
**never imported** on the alignment path. The OSS map's mitigation ("use alignment-only, no
diarization") holds for the token and for import cost; it does **not** avoid pip installing pyannote
and its ~25-package tail. That distinction was not previously written down.

### Offline at inference

Yes, once cached. `load_align_model(language_code, device, model_name=None, model_dir=None)` accepts an
explicit `model_dir`, so the checkpoint can be pinned under `TOOLSHOP_MODEL_DIR` rather than the default
HF cache, and `HF_HUB_OFFLINE=1` then holds. **One-time online cost: 1262.0 MB** — the
`model.safetensors` blob of `classla/wav2vec2-xls-r-parlaspeech-hr`, measured from the HF API listing.
(The repo also carries a 2490.5 MB `optimizer.pt` which is training state and is not fetched.)

**Gap:** this checkpoint would be a new cached model asset that `toolshop.doctor`'s
`_model_cache_ok()` does not know about — that check covers `stem_models.MODEL_MANIFEST_PATH` only.
Adding it to the manifest is part of adoption, per the model-mirror policy (AGENTS.md, and the 2026-06
HF-deletion risk row in the OSS map).

---

## Dependency Collision Analysis

### The protobuf trap does not fire

`pyproject.toml:29-48` records the standing resolution: **protobuf stays at 7.36.0**; `classla`'s
`protobuf==4.21.2` is the pin deliberately violated, because pinning down to 4.21.2 breaks
`audio_separator...mdx_separator` (it imports `onnx`, which needs `google.protobuf.runtime_version`,
absent before 5.x) and kills stem separation at stage one of the vocal-swap lane.

Verified first-hand against the installed metadata:

| package | protobuf requirement | 7.36.0 |
|---|---|---|
| `onnxruntime` 1.27.0 | `protobuf>=4.25.8` | ok |
| `onnx-weekly` 1.23.0.dev20260706 | `protobuf>=6.31.1` | ok |
| `classla` 2.2.1 | `protobuf==4.21.2` | **violated (pre-existing, accepted)** |

**Every protobuf-touching package whisperX would add sets a lower bound compatible with 7.36.0:**

| new package (variant A) | requirement |
|---|---|
| `opentelemetry-proto` 1.44.0 | `protobuf<8.0,>=5.0` |
| `googleapis-common-protos` 1.75.2 | `protobuf<8.0.0,>=6.33.5` |
| `optuna` 4.9.0 | `protobuf>=5.28.1` *(extra `optional` only)* |
| `transformers` 4.57.6 | `protobuf` *(extras only)* |

In variant C, protobuf is **not in the install set at all**; the only protobuf-adjacent additions are
`tensorboardX` (`protobuf>=3.20`) and `sentencepiece` (extras only). **No fourth constraint collides.
Nothing drags protobuf below 5.x, directly or transitively.** The stem-separation path is safe.

Note in passing: variant A would *raise* the effective protobuf floor to `>=6.33.5` via
`googleapis-common-protos`, making a future retreat below 6.x impossible. Another reason to prefer C.

### The real collision is torch

```
whisperx 3.8.6   -> torch~=2.8.0, torchaudio~=2.8.0, torchvision~=0.23.0, huggingface-hub<1.0.0
pyannote-audio 4.0.7 -> torch>=2.8.0, torchaudio>=2.8.0
classla 2.2.1    -> torch<=2.6            <-- installed torch is exactly 2.6.0
```

Computed violation set for variant A (existing dists whose requirements the resolved set breaks):

```
classla  2.2.1 requires "protobuf==4.21.2"           but would get 7.36.0   (pre-existing)
classla  2.2.1 requires "torch<=2.6"                 but would get 2.8.0    ** NEW **
classla  2.2.1 requires "requests==2.28.0"           but would get 2.34.2   ** NEW **
selenium 4.46.0 requires "urllib3[socks]>=2.6.3,<3.0" but would get 1.26.20 ** NEW **
```

`classla` is already carrying one violated pin by deliberate decision. Adding a second (`torch`) is a
different matter: the protobuf violation was *measured* safe (classla imports, 20 tests pass at 7.36.0);
a torch 2.6 → 2.8 jump has not been measured against classla, `sentence-transformers` 5.6.0,
`onnx2torch`, `demucs`, `torchcrepe` or `panns-inference`. The `transformers` 5.14.1 → **4.57.6** and
`huggingface-hub` 1.23.0 → **0.36.2** major downgrades in the same transaction compound it. Variant A is
a **NO-GO shape.**

Same computation for variant C:
```
classla 2.2.1 requires "protobuf==4.21.2"  -> would get 7.36.0   (pre-existing, accepted)
classla 2.2.1 requires "requests==2.28.0"  -> would get 2.34.2   (new, low risk)
```
(`classla`'s `requests==2.28.0` pin is already effectively broken in this venv: `urllib3` is at 2.7.0
while requests 2.28.0 requires `urllib3<1.27`.)

### The residual fork: torch vs ctranslate2

No whisperX release satisfies both `torch<=2.6` and `ctranslate2>=4.5`. So in `.venv` the choice is:

- move **torch** → breaks classla's `torch<=2.6`, plus two major downgrades; **or**
- move **ctranslate2** 4.8.1 → 4.4.0 → declaratively fine (`faster-whisper 1.2.1` accepts
  `ctranslate2<5,>=4.0`) but it swaps the ASR inference engine underneath J-000e's byte-identical
  reproducibility result, which is the property that makes a 444-track corpus regeneration worth doing
  at all. Reproducibility across a CTranslate2 minor-version change is an assumption, not a fact.

**Both horns are avoidable: install whisperX in a separate sidecar venv.** The OSS map already
sanctions adapter/sidecar isolation, and the interface here is unusually clean — see Integration Point.
That is the recommended shape and it reduces the dependency question to "does a second venv exist",
which is free.

---

## Estimated CPU Cost — **ESTIMATE, NOT A MEASUREMENT**

> Nothing was run. Every number in this section is derived arithmetic and must not be quoted as
> measured. `J-000g` is in the journal because this project has already shipped a derived/short-input
> number as if it were a full-input measurement, twice.

### Measured anchor (first-hand, from existing artifacts)

Read directly out of `data/toolshop/lyrics/transcripts/*.json`:

| artifact | audio | elapsed | coverage | words |
|---|---|---|---|---|
| `borba-015.large-v3.temp0.json` | 249.48 s | 229.61 s | 69.1% | 188 |
| `borba-015.coverage-A.json` | 249.48 s | 245.03 s | 69.1% | 188 |
| `borba-015.coverage-B.json` (`vad_filter=False`) | 249.48 s | 370.49 s | 46.4% | 127 |
| `borba-015.coverage-C.json` (full mix) | 249.48 s | 166.96 s | 68.4% | 147 |

So the ASR stage costs **0.92 s of compute per second of audio** on this i7-4770.

**Definition warning.** The project's "RTF 1.09–1.17×" is `audio_duration / elapsed` — a *speed factor*
(faster than realtime), inverted from the conventional RTF (`elapsed / audio`). 249.48/229.61 = **1.087**;
249.48/213.2 = **1.17**. Under the conventional definition the same runs are RTF **0.92–0.98**. Anyone
comparing against a published whisperX RTF will get this backwards. Stated here so the estimate below
is unambiguous: **all RTF figures below are `elapsed / audio`.**

### Derivation

The alignment model is `classla/wav2vec2-xls-r-parlaspeech-hr` — XLS-R-300M, **1262.0 MB fp32
safetensors** (measured from the HF API), ~315M parameters, 24 layers, hidden 1024, ~50 frames/s.

Against whisper large-v3 int8 (1.55 GB) it is smaller in parameters but runs in **fp32**, and Haswell has
no VNNI, so the per-parameter arithmetic advantage of int8 is smaller here than on a modern CPU. The
decisive difference is structural: **CTC alignment is a single forward pass; Whisper decodes
autoregressively, token by token.**

Linear-layer cost ≈ `2 × 315e6 × 50` ≈ **3.15e10 FLOP per second of audio**. An i7-4770 peaks near
217 GFLOP/s fp32 (4 cores × 8 FMA lanes × 2 × 3.4 GHz); PyTorch CPU GEMM realistically lands at
30–50%, so ~65–110 GFLOP/s.

**Estimate: RTF ≈ 0.3–0.6 (elapsed/audio) → roughly 1.2–2.5 min for a 4.2 min track, provided segments
stay short (≲30 s).**

Total for the two-stage path (ASR for segmentation, then alignment): **≈ 5–6.5 min/track, estimated.**
Comfortably inside AGENTS.md's 15-minute overnight threshold. For the 444-track corpus that would be
roughly 37–48 h of added CPU — but the corpus is *other people's* songs, where lyrics are not known, so
alignment does not apply there anyway.

### The quadratic trap — why "one segment for the whole track" fails

`align()` has **no chunking and no maximum segment length**. Self-attention is O(n²) in frames. The
naive way to align a bare lyric sheet — one segment spanning the track — gives n = 249.48 × 50 ≈ **12,474
frames**:

- attention FLOPs ≈ `12474² × 1024 × 24 layers × 2 × 2` ≈ **1.5e13** — on its own ~150–230 s, dwarfing
  the linear term;
- an attention matrix of `12474² × 4 B` ≈ **622 MB per head**; at 16 heads a materialised
  `[1, 16, n, n]` tensor is ≈ **10 GB** on a **15.9 GB** machine.

**Likely OOM or heavy thrash.** Long-form alignment must be windowed by us. At 20 s segments
(n = 1000) the quadratic term is negligible and the linear estimate above holds.

---

## Input Requirements & Serbian Language Support

### What `align()` actually consumes

```python
def align(transcript: Iterable[SingleSegment], model, align_model_metadata,
          audio, device, interpolate_method="nearest",
          return_char_alignments=False, ...) -> AlignedTranscriptionResult
```

Each input segment must carry **`text`, `start`, `end`** (`avg_logprob` optional). **This is the finding
that corrects the plan's premise:** whisperX aligns *within a segmentation you supply*. It is not a
lyric-sheet-to-audio aligner. Three routes:

- **(a) ASR segmentation, known text substituted.** Take the 26 segments from `coverage-A`, replace each
  segment's text with the true lyric lines, re-align. Cheap and immediately useful — inside the covered
  69% the words become *correct* and the timings sharpen from whisper's coarse spans to wav2vec2's
  ~20 ms frames, which is exactly what syllables-per-bar and on/off-beat placement need. **But it does
  not recover the 31%:** a stretch with no ASR segment gets no alignment anchor.
- **(b) Whole track as one segment.** Mechanically legal, arithmetically ruled out above.
- **(c) Our own fixed windowing** (~20–30 s), assigning each window its slice of the known lyrics —
  the standard long-form approach, and the one that genuinely closes the 31%. The hard part is
  text-to-window assignment; the tractable method is anchor-based (use high-confidence ASR words as
  anchors, distribute the known lyrics between anchors). **This is build work on top of whisperX.**

`toolshop.transcribe.TranscriptSegment` is already `(start, end, text, words)` and its `to_dict()`
emits `{"start", "end", "text", "words"}` — a **direct structural match** for `SingleSegment`. No
adapter shim is needed for the data itself.

### Serbian: there is no `sr` model; Croatian is the reachable proxy

Verified against `whisperx/alignment.py` at tag `v3.4.5` *and* `main` — both agree:

```
"hr": "classla/wav2vec2-xls-r-parlaspeech-hr",
"sl": "anton-l/wav2vec2-large-xlsr-53-slovenian",
"sk": "comodoro/wav2vec2-xls-r-300m-sk-cv8",
"cs": "comodoro/wav2vec2-xls-r-300m-cs-250",
"pl": "jonatasgrosman/wav2vec2-large-xlsr-53-polish",
"ru": "jonatasgrosman/wav2vec2-large-xlsr-53-russian",
"uk": "Yehor/wav2vec2-xls-r-300m-uk-with-small-lm",
```

**No `sr`, no `bs`, no `mk`, no `sh`.** `load_align_model` raises `ValueError` on an unknown code —
so passing `transcribe.DEFAULT_LANGUAGE` (`"sr"`, `toolshop/transcribe.py:98`) **straight through to
whisperX would crash.** That is a hard wiring requirement, not a nicety.

Mitigating facts:

- **`hr` is a good proxy.** BCMS is one dialect continuum; Croatian and Serbian Latin share the identical
  Gaj alphabet (`č ć đ š ž`), so the CTC character vocabulary covers Serbian Latin text unchanged.
- **Pleasing coincidence:** the Croatian model is published by **CLASSLA** — the same organisation whose
  Python package is already a dependency and whose protobuf pin is the one we violate.
- **`load_align_model(..., model_name=..., model_dir=...)`** accepts an arbitrary HF model id, so a
  Serbian-specific wav2vec2 CTC checkpoint can be substituted later without touching whisperX.

Risks with the proxy:

- **Domain mismatch.** ParlaSpeech-HR is *parliamentary speech* — clean, formal, slow. Serbian drill at
  100–200 wpm with heavy slang is far out of domain. Alignment is more robust to this than recognition
  (it is scoring a known character sequence, not searching a hypothesis space), but "more robust" is a
  claim to measure, not to assume.
- **Cyrillic must be transliterated first.** `cyrtranslit` is already declared (`pyproject.toml:23`).
- **OOV characters become a wildcard.** `align()` maps unknown characters to a wildcard column (max
  non-blank score per frame). So it will happily "align" text whose script or vocabulary is wrong and
  return plausible-looking timings. **This is a silent-degradation surface** and belongs in the guard.

### The lyrics DB does not hold our own lyrics

Inspected `data/toolshop/lyrics/lyrics.db` read-only:

```
corpus counts:  [('genius-pro', 1425)]
language counts:[(None, 1425)]
categories:     jala-solo 200, maya-berovic-solo 145, rasta-solo 109, devito-solo 106,
                corona-solo 92, senidah-solo 82, coby-solo 82, buba-solo 75, ...
total songs 1425 · total lines 65912 · distinct target_artist 18
songs with source_path pointing at audio: 0
sample source_path: D:\MusicData\toolshop\lyrics\genius\ana-nikolic-solo\ana-nikolić-200100.json
```

The schema is good for this job — `sections → lines(text_raw, text_norm, word_count, syllable_count)
→ tokens` is exactly the hierarchy an aligner wants, and `lines` even carries syllable counts. But
**every one of the 1425 rows is `corpus='genius-pro'`: other people's songs.** There are zero rows of
our own material, `language` is NULL on all of them, and **no row links to an audio file**.

So the premise "for everything the artist writes, the lyrics are already known" is true **of the artist**
and false **of the database**. Our lyrics currently live as loose Markdown (the `to_be_moved/*_LYRICS.md`
family). Adoption needs a prerequisite that is not a whisperX problem:

1. an ingestion path writing `corpus='own'` rows,
2. a `language` value actually populated,
3. **an audio join key** — `songs` has no column that points at a track.

---

## Integration Point & Required Guard

### Where it sits

`toolshop/transcribe.py` (477 lines) is a **library module with no CLI wiring** — there is no
`transcribe` subparser in `toolshop/cli.py`. It exposes `transcribe_file(...)` returning a `Transcript`
of `TranscriptSegment(start, end, text, words=[Word(text, start, end, probability)])`, plus
`save_transcript` / `transcript_path_for`.

Forced alignment is a **second stage over that dataclass**, not a replacement backend:

```
audio + Transcript(segments)  ->  align stage  ->  Transcript(segments with refined Word timings)
                                                   backend = "whisperx-align"
```

Because `TranscriptSegment.to_dict()` already emits `SingleSegment`'s exact shape, the sidecar-venv
option costs almost nothing: the boundary is the transcript JSON that
`data/toolshop/lyrics/transcripts/` already stores. A `toolshop/align.py` adapter can shell out to the
sidecar interpreter with two paths (audio in, transcript in, aligned transcript out) and stay pure.

`Transcript` already has the right provenance discipline (`source`, `decode_settings`, `backend`) — extend
it with `align_backend`, `align_model` (the HF id) and `align_language` (the code *actually used*), so an
`sr → hr` substitution is recorded rather than inferred.

### The guard: `--require-alignment`

`transcribe.py:11-19` argues, correctly, that `--require-advanced` would be *vacuous* for ASR — there is
no heuristic fallback for speech recognition, so without the backend nothing runs. It offers
`--require-stem` instead, guarding the axis that actually degrades.

**Forced alignment reverses that.** It has an obvious, tempting, silent fallback: if
`load_align_model` raises `ValueError` (unsupported language — and `sr` *is* unsupported), or the
checkpoint is not cached while offline, or the sidecar is missing, the natural `except` is "keep the
faster-whisper timings." The output file is then **structurally identical** to a genuinely aligned one.
This is precisely AGENTS.md's silent-fallback class, and precisely the shape of the `NameError`-swallowed
zero result in J-001.

Required:

- **`--require-alignment`** — turns any fall-back-to-ASR-timings into a hard failure, exactly as
  `--require-advanced` does in `toolshop/melody_carrier/melody_cli.py:59,129-163`.
- **`--require-language-match`** (or at minimum a loud, recorded warning) — because `sr` silently
  becoming `hr` is a second, subtler fallback, and because the wildcard-OOV behaviour means wrong-script
  or wrong-vocabulary text still returns confident-looking timings.
- Per AGENTS.md's "new top-level packages are lanes": tests go in `tests/`, and the alignment checkpoint
  goes into the model manifest that `toolshop.doctor._model_cache_ok()` checks.

---

## Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Unpinned install takes torch to 2.8, breaks `classla`, and downgrades `transformers`/`huggingface-hub` two major versions | **High** | Pin `whisperx==3.4.5`; never install unpinned. Sidecar venv removes it entirely. |
| 2 | In-venv install downgrades `ctranslate2` 4.8.1 → 4.4.0, invalidating J-000e's byte-identical ASR reproducibility | **High** | Sidecar venv. If ever installed in `.venv`, re-run `borba-015` at temp0 and diff against the 188-word artifact **before** trusting anything. |
| 3 | Silent fallback to plain ASR timings — output is structurally identical | **High** | `--require-alignment`, plus `align_backend` recorded in `Transcript`. |
| 4 | `sr` is not a supported alignment language; `load_align_model` raises on `transcribe.DEFAULT_LANGUAGE` | Medium | Explicit `sr → hr` mapping, recorded in the transcript, guarded by `--require-language-match`. |
| 5 | ParlaSpeech-HR is parliamentary-speech domain; drill at 100–200 wpm is far out of domain | Medium | Measure coverage/word-accuracy against the 188-word baseline before adopting. Unknown until run. |
| 6 | Wildcard OOV mapping makes wrong-script text align "successfully" | Medium | Transliterate with `cyrtranslit` (already a dep); assert the character set against the model vocab before aligning. |
| 7 | Whole-track single-segment alignment OOMs (~10 GB attention tensor on 15.9 GB) | Medium | Never pass a segment longer than ~30 s. Enforce in the adapter, not by convention. |
| 8 | The 31% is **not** closed by route (a); the plan's premise overstates the win | Medium | Correct the plan. Route (c) windowing is the real fix and is separate work. |
| 9 | `lyrics.db` has no own-material rows, no `language`, and no audio join key | Medium | Prerequisite ingestion work; independent of the whisperX decision. |
| 10 | 1262 MB alignment checkpoint is outside `toolshop.doctor`'s manifest; HF model rot is a proven failure mode (2026-06) | Low | Mirror + checksum into the manifest at adoption. |
| 11 | pip pairs `torchaudio 2.11.0` with `torch 2.6.0` (torchaudio declares no torch pin) → C++ ABI failure at import | Low | Pin `torchaudio==2.6.0` explicitly in any constraint file. |
| 12 | Variant A raises the effective protobuf floor to `>=6.33.5` via `googleapis-common-protos` | Low | Avoided by variant C / sidecar. |
| 13 | Licensing | None | whisperX is BSD (OSS map §6, permissive list). ParlaSpeech-HR model card terms to be recorded at adoption per the map's rule. |

---

## What Would Have To Be Measured Next

Nothing below has been run. In order, cheapest first:

1. **Sidecar install.** `python -m venv .venv-whisperx` (3.11), then
   `pip install whisperx==3.4.5 torch==2.6.0 torchaudio==2.6.0` against the CPU index. Confirms the
   dry-run resolution actually builds on Windows/py3.11 and that `.venv` is untouched.
   Then verify the token claim behaviourally: `import whisperx` with `HF_TOKEN` unset and assert
   `pyannote` is absent from `sys.modules`.
2. **One-time model fetch,** 1262 MB, `classla/wav2vec2-xls-r-parlaspeech-hr` into `TOOLSHOP_MODEL_DIR`.
   Then re-run with `HF_HUB_OFFLINE=1` to prove offline inference.
3. **The cost measurement — the number that governs the merge.** Align `borba-015`'s 26 existing
   `coverage-A` segments against the same stem. Report wall-clock, RTF (state which definition),
   peak RSS. **AGENTS.md discipline: discard a warm-up run, repeat the baseline at the end, and if the
   two baselines disagree by >10% the machine is not a stable instrument and no conclusion holds.**
   Full track only — J-000g exists because a clip screen lied twice.
4. **The quality question that actually decides this.** Substitute the *known* lyrics for `borba-015`
   into those 26 segments, align, and compare against the 188-word ASR baseline: how many known words
   receive a timing, how many land in plausible positions, and what the longest untimed span becomes.
   This is the first honest test of whether `hr` alignment survives out-of-domain drill.
5. **Route (c) feasibility spike.** Window a full track at 20–30 s, assign lyric slices by ASR anchors,
   align per window, and measure coverage against the same 69.1% baseline. **This is the only experiment
   that tests the plan's actual claim** — that forced alignment closes the 31%.
6. **Only if 1–5 land:** the `--require-alignment` guard, `tests/` coverage, manifest entry, and a
   `toolshop transcribe`/`toolshop align` CLI surface (neither exists today).
