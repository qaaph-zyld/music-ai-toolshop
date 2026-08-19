# State of the Project — Comprehensive Assessment

**Date:** 2026-08-19
**Author:** Orchestrator (independent assessment, evidence re-run locally)
**Scope:** `D:\Projects\Music-AI-Toolshop` — whole repo, data, subprojects, records, governance
**Supersedes as current picture:** `docs/superpowers/STATUS.md` (last reconciled 2026-08-08)
**Feeds:** `2026-08-19-goals-v2.md` (goal set + phased strategy)

---

## 0. Method and evidence bar

Every claim below is either (a) re-run by the orchestrator in this session, or (b) explicitly
tagged `unverified — source: <path>`. Numbers relayed from handoffs are not stated as fact.
This follows the `AGENTS.md` "verified verdicts only" rule.

Commands actually run: `git status/log/show/ls-files/submodule`, `toolshop doctor`,
`toolshop --help`, `pytest -q` (full suite), direct SQLite queries against `lyrics.db`,
filesystem inventory, and five targeted web verifications of external dependencies.

---

## 1. Executive summary

The project is **technically strong and organizationally drifting**. In the four weeks since the
last orchestrator assessment (2026-07-23) the codebase grew by roughly a third and shipped real,
high-quality capability: the full lyric-intelligence stack now runs end to end on a **1,425-song**
corpus, an FL Studio DAW bridge landed, a music-video generator landed, and the L5 writing tools
(rimer DB, brief generator, draft scorer) are live.

In the same four weeks the governance layer that was mechanized on 2026-07-23 stopped being used.
**Zero executable plans were written.** Two entire lanes entered the project with no plan, no
CHANGELOG entry, and no STATUS row — one of them committed under a commit message describing
something else entirely. The safety net that matters most, backups, has not run in 28 days and now
FAILs its own health check while the corpus it protects has nearly doubled.

The right move is not more features. It is **one consolidation phase** that commits what exists,
absorbs or shelves the duplicate lane, restores the backup, and re-baselines the records — after
which the roadmap can resume with the keystone work (H1 close, Dossier v2) it has been deferring
since July.

**The single most urgent item is F1 (stale backup on a 98%-full destination).** It is also the
cheapest to fix.

---

## 2. What exists today — the catalogue

### 2.1 Code

| Component | Size | Tracked? | State |
|---|---|---|---|
| `toolshop/` core package | **26,121 LOC**, ~70 modules | yes (except `melody_carrier/`) | The spine. 14 CLI groups. |
| `toolshop/daw/` | 12 modules, ~3,000 LOC | yes | FL Studio bridge (#025) |
| `toolshop/melody_carrier/` | 6 modules, **2,043 LOC** | **NO — uncommitted** | Audio to MIDI to carrier-WAV for Suno cover mode |
| `ai_modules/` | 40 files, **6,390 LOC** | yes (mislabeled commit) | Parallel lane, largely duplicative — see F2 |
| `tests/` | **63 files** | yes (except 5 melody_carrier tests) | Only `tests/` is collected (`pytest.ini: testpaths = tests`) |
| `scripts/` | 5 analysis one-offs | yes | collab network, Cohen's d, Suno gap/fetch |
| repo-root one-offs | 8 `.py`/`.ps1` | yes | batch runners + diagnostics; flagged for relocation since 2026-07-23 |
| `mastering_tool/` | git submodule | pointer at `35d4075` | **Daily-use product.** Pushed; on branch `claude/wonderful-johnson-h6xj4d`, not master; 5 untracked files inside |

**CLI surface (14 groups):** `suno`, `analyze`, `yt`, `track`, `voice`, `stem`, `stems`, `clean`,
`remix`, `doctor`, `closeout`, `daw`, `video`, `melody-carrier`, `lyrics`.

### 2.2 Sibling subprojects inside the repo

| Directory | Tracked files | Verdict |
|---|---|---|
| `Voicebox/` | **410** | Fully vendored despite `PROJECTS_INDEX.md` claiming "vendored fork removed" — a documented-vs-reality contradiction. Parked lane. |
| `MAirina_Tucc/` | 25 | Serbian rhyme tool + React UI (PRD, rimer-sr, rimer-ui). Now overlaps L5 `rimer_db`. |
| `Genious_lyrics_extractor/` | 11 | Corpus extraction (batches 1-3). Live, feeds `lyrics.db`. |
| `Stemmeca_alatkka/` | 14 | Remix/stem scratch lane; partially gitignored. |
| `lyrics_research/` | 38 | Reports + verification records + curriculum. Live and valuable. |
| `open_DAW/` | 0 (gitignored) | Own Rust/JUCE DAW build. Parked. **`ai_modules/` was partly copied from here.** |
| `Distro_Kidea/` | 0 (gitignored) | 59 audio/art assets — belongs under `data/`, not the repo root. |
| `ORCHESTRATION/` | 0 — **untracked** | New multi-agent wave harness (waves 1-2 ran, 3-4 did not) |

### 2.3 Data (all under repo-local `data/`, gitignored since #030)

`D:\MusicData` no longer exists — the relocation in #030 is real and complete.

**`data/toolshop/lyrics/lyrics.db` — 67 MB, 13 tables, verified by direct query 2026-08-19:**

| Table | Rows |
|---|---|
| songs | **1,425** |
| sections | 10,654 |
| lines | 65,912 |
| tokens | 501,386 |
| line_rhymes | 273,801 |
| song_metrics / song_rhyme_metrics | 1,425 / 1,425 |
| entities | 10,544 |
| slang_terms | 11,364 |
| topics / section_topics | 163 / 4,079 |
| rhyme_pairs | 13,036 |

**Cohorts:** `drill_trap` 808 · `pop` 524 · NULL 93.
**Suno corpus:** 3,428 metadata JSONs in `data/toolshop/suno/`.
**Catalogue:** `results/crhymetv_re` (222 tracks, gitignored).

### 2.4 Records and governance artifacts

`AGENTS.md` (close-out discipline, mechanical gate) · `toolshop closeout` CLI · tracked
`hooks/pre-push` · `toolshop doctor` · `CHANGELOG.md` (#001-#037) · `STATUS.md` ·
**18 plans** (newest `2026-07-23`) · 8 specs · 3 research reports.

---

## 3. Verified health readings (2026-08-19)

| Check | Result |
|---|---|
| Branch / sync | `master`, **0 unpushed commits** — good |
| Working tree | 3 modified, **26 untracked** (a whole lane among them) |
| `toolshop doctor` | **FAIL** — `model_cache` missing 2 RoFormer checkpoints; `backup` 28d old |
| Disk | D: 148 GB free · **C: 14 GB free (98% full)** — C: is the backup destination |
| Backup | `C:\Backups\toolshop`, 1,954 files, **last written 2026-07-21** |
| Git pack | **778.93 MiB** for 2,256 tracked files |
| Submodule | pointer pushed; on a non-master branch; 5 untracked files inside |
| Test suite | see §5 |

---

## 4. Findings, ranked

### F1 — CRITICAL · The backup is 28 days stale and its destination is nearly full

`toolshop doctor` reports `[FAIL] backup (age=28d)`. The last write to `C:\Backups\toolshop` was
2026-07-21. Since then the corpus went **742 to 1,425 songs**, rhyme rows **159,171 to 273,801**, and
3,428 Suno metadata files accumulated — none of it backed up. The destination drive **C: is 98%
full with 14 GB free**, so the next run may not even fit. The original same-physical-disk caveat is
still unresolved, and D: remains a 2010 Seagate laptop HDD.

`toolshop/backup.py:33` *was* correctly updated to the new repo-local `data/toolshop` root, so the
path handling is fine — **it simply has not been run.**

*Exposure:* the flagship lyric asset is one disk failure from gone.

### F1b — CRITICAL · The backup has never covered Suno at all *(found 2026-08-19, after the initial pass)* · **RESOLVED 2026-08-19/20 (#038)**

> **Outcome:** coverage fixed and regression-tested (+5 tests); **3,426 / 3,426 tracks fetched,
> 15.79 GB, zero failures**; backup live at `D:\Backups\toolshop` (6,871 files / 117.4 MB,
> verified=True) carrying **3,427 Suno metadata files, previously 0**. The finding below is kept as
> written, because how it was missed matters more than the fix.

Scheduling was not the only problem. `_discover_assets()` collects exactly four things —
`lyrics/genius/**/*.json`, `lyrics/genius/**/*.txt`, `lyrics/lyrics.db`, `espeak-ng/**` — and
`_discover_repo_assets()` adds `.env`, `lyrics_research/reports/*.md`, and three
`results/crhymetv_re/` files.

**No Suno path appears in either list.** The 2026-07-21 backup that verified clean contains **zero
Suno data**. Re-running it on a schedule would have protected nothing here. This is a *coverage* bug
and it was invisible for a month because the manifest verified successfully against the wrong set.

What is actually at stake, verified by inspection today:

| Asset | Reality | Risk |
|---|---|---|
| `data/toolshop/suno/*.json` | **3,426 metadata records** — id, title, created_at, model, tags/lyrics, and the CDN `audio_url` | Small, irreplaceable, **unbacked**. This is the only index of what exists; lose it and nothing can be re-fetched. Highest value-per-byte in the project. |
| `D:\Projects\suno_extractor\suno_downloads\` | **37 mp3 files, 211 MB** — the entire downloaded Suno audio collection | **Unbacked**, and it sits *outside* the toolshop repo, so no source root reaches it |
| The other 3,389 tracks | **Not on this machine.** They exist only as `https://cdn1.suno.ai/<id>.mp3` links | **Not a backup problem** — no backup protects a file that was never downloaded. If links expire or the account lapses, they are gone |

The last item is the one that no amount of backup hygiene fixes. Fetching the catalogue locally is a
**preservation** task, not a backup task: roughly **13–15 GB** at ~4 MB/track, comfortable against
D:'s 148 GB free. It needs its own plan (rate limits, resume, dedup against the 37 already present,
integrity checks) and explicit authorisation, because it means pulling thousands of files from an
external service.

*Correction to record:* the earlier framing of F1 as purely "the backup is stale" understated this.
Staleness was the visible symptom; **coverage was the real defect.**

### F2 — HIGH · `ai_modules/` entered the repo disguised as a submodule chore

Commit `31224e5` (2026-08-18), titled *"chore: update mastering_tool submodule — pipeline gain
fix"*, actually contains **40 files and 6,390 insertions** creating a brand-new `ai_modules/` lane,
including two binary `.db` files. There is **no CHANGELOG entry** (#038 does not exist), no STATUS
row, no plan, and no README coverage.

Its seven test files (**1,440 LOC of tests**) live inside `ai_modules/` and are therefore **never
collected** — `pytest.ini` sets `testpaths = tests`.

Content overlaps existing lanes, and two modules contradict locked decisions:

| `ai_modules/` module | LOC | Existing counterpart | Verdict |
|---|---|---|---|
| `vocal_cleanup` | 1,865 (953 test) | `cleaning_stages.py` + `cleaning_pipeline_adapter.py` (T4) | **COMBINE** — its `SilenceDetector(min_duration_sec=...)` may be the correct fix for open debt 1c |
| `production_analyzer` | 1,147 | `reverse_engineering_adapter.py` (T2) | **REASSESS** — may genuinely advance Dossier v2 |
| `suno_library` | 892 | `suno_adapter.py` + `toolshop suno` | **REMOVE** (keep `api_server.py` only if a local API is wanted) |
| `stem_extractor` | 213 | `stem_extractor_adapter` + `demucs_adapter` + `stem_models` (T1) | **REMOVE** — straight duplicate |
| `pattern_generator` | 283 | `daw/generators.py`, `melody_carrier` | **COMBINE** |
| `musicgen` | 321 | — | **SHELVE (GPU)** — violates "Suno is engine of record" |
| `lora_finetuning` | 1,000 | — | **SHELVE (GPU)** — violates the locked CPU-only decision |

Several of these were copied from the **parked** `open_DAW/ai_modules/` (their docstrings still say
"for OpenDAW"), which means a parked lane re-entered the active repo sideways.

### F3 — HIGH · The melody-carrier lane is uncommitted, and its ML backends are inert

`toolshop/melody_carrier/` (2,043 LOC), five test files, and edits to tracked `toolshop/cli.py` and
`toolshop/__init__.py` are all sitting in the working tree. This is the **exact failure mode the
mechanical close-out gate was built to stop** — four weeks after it was installed and verified.

Three further issues, all verified:

1. **None of the three primary backends are installed** — `basic_pitch`, `autochord`, and
   `adtof_pytorch` all fail to import in the venv. Every run today silently takes the
   librosa/pYIN/spectral fallback path.
2. **No dependency extra exists.** `pyproject.toml` has no `melody` extra, so there is no supported
   way to install the primary path.
3. **`pyproject.toml` actively excludes the primary melody model on this platform** —
   `"basic-pitch; platform_system!='Windows'"` in `track-full`. Research (§6, R4) shows this
   exclusion is **obsolete**: basic-pitch ships ONNX Runtime on Windows by default.

*Credit where due:* the code does the right thing structurally — lazy imports, explicit fallbacks,
and it **records which tool was used** (`"basic_pitch"` vs `"pyin_fallback"`). That is the lesson
from the earlier silent-fallback incident correctly applied. What is missing is a
`--require-advanced` guard equivalent to the one the RE backend has.

### F4 — HIGH · Governance reverted to documentation-only

- **Zero plans written since 2026-07-23**, while 13 CHANGELOG entries and 2 undocumented lanes shipped.
- `STATUS.md` was last reconciled 2026-08-08 and is **already two lanes stale**.
- `toolshop closeout` exists, is wired to a tracked pre-push hook, and `doctor` verifies the hooks
  path — yet the tree is dirty with an entire uncommitted lane, so **the gate is not being run**.
- This is the **8th+ instance** of out-of-band work in this project's history.

The mechanism is sound; the practice lapsed. Note the mechanism cannot catch F2 at all: a lane
committed under a wrong message passes every automated check.

### F5 — MEDIUM · Two major lanes were never research-gated

Goals v1.0 §7 rule 6 says *"no new domain lane opens before its landscape-report section exists."*
Both the Video lane (7 modules, 72 tests, #028) and melody-carrier opened without one.

Retroactive research (§6) finds the **video lane's in-house approach is defensible** — there is no
dominant OSS music-video pipeline to adopt. The **audio-to-MIDI picks were never validated**, and one
of them is blocked by an obsolete packaging marker (F3).

### F6 — MEDIUM · Debt 1c is still open, with a fix possibly already in the tree

`PauseRemovalStage` ignores `min_silence` and removes all silence; the test was weakened to match
the bug rather than the bug being fixed (logged 2026-07-21, untouched since). `ai_modules/vocal_cleanup`
implements a `SilenceDetector` with a real `min_duration_sec` — the consolidation in F2 may resolve
this debt as a side effect.

### F7 — MEDIUM · M2 model cache missing, so `doctor` cannot pass

`mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt` and
`model_bs_roformer_ep_317_sdr_12.9755.ckpt` are absent. This is the long-deferred M2 milestone and
it is the *only* remaining reason `doctor` returns FAIL besides the backup.

### F8 — MEDIUM · Repo hygiene and stale records

- **778.93 MiB** git pack for 2,256 tracked files — heavy for a code repo.
- **410 tracked `Voicebox/` files** contradict `PROJECTS_INDEX.md`.
- **29 `.txt` files in the repo root**, of which ~10 are not even gitignored
  (`cli-help-*.txt`, `mc-*.txt`, `test-output-*.txt`).
- `.coverage` is tracked though gitignored.
- `PROJECTS_INDEX.md` still claims a **742-song** corpus at `D:\MusicData\...` — two facts, both wrong.
- `README.md` last touched 2026-07-21; missing `daw`, `video`, `melody-carrier`, L5 tools, `ai_modules`.
- Untracked-but-wanted content: `ORCHESTRATION/`, `docs/lyrics/` (15 craft/lyric docs moved in from
  `D:\Projects\to_be_moved`), 3 research docs in `docs/`.

### F9 — LOW · The new orchestration layer already reproduced the verified-verdicts failure

In `ORCHESTRATION/`, Agent A correctly reports the DB as 1,425 songs / 65,912 lines / 273,801 rhyme
rows. Agent D's handoff, one day later, states **742 songs / 36,572 lines / 159,171 rhyme rows** —
L2.1-era numbers relayed rather than re-queried. Agent D's *outputs* look sound; its *header* is wrong.

### F10 — LOW · The wave plan stalled at 50%

`ORCHESTRATION/waves.json` defines 4 waves / 9 agents. Waves 1-2 produced handoffs (2026-08-08/09);
**waves 3-4 never ran** — draft-scoring A/B, German corpus extraction, phonemizer-de, and the flow
analyzer v2 spec. L6 prep is stalled.

---

## 5. Test suite — VERIFIED GREEN

Re-run by the orchestrator in this session, in the pinned 3.11 venv:

```
963 passed, 2 skipped, 23 warnings in 689.20s (0:11:29)
```

**Zero failures.** This is a genuine improvement over the #037 baseline (856 passed) and over the
STATUS.md line claiming "780 passed, 1 failed (pre-existing espeak)" — the espeak failure is gone.

Two caveats on what this number covers:

- It **excludes the 1,440 LOC of `ai_modules/` tests** — they sit outside `testpaths = tests` and are
  never collected (F2). So 6,390 LOC of committed code is effectively untested in CI terms.
- It **includes ~107 tests from the five uncommitted melody-carrier test files** (F3). A fresh clone
  would run neither those tests nor that code.

So the honest headline is: **the committed, collected suite is green, and roughly 20% of the
repo's Python is outside it.**

---

## 6. Research refresh — external assumptions re-verified 2026-08-19

The July landscape verdicts were recorded as `likely, re-verify at adoption`. Five that gate near-term
decisions were re-checked directly.

| # | Question | Finding | Consequence |
|---|---|---|---|
| **R1** | Is the pedalboard VST3 Windows bug fixed? | **No.** PR #476 *"Fix VST3 effect plugins rendering dry audio on Windows"* was opened **2026-04-09 and is still open**. | **E2 mix-chains cannot depend on VST3 hosting.** Ship E2 v1 on pedalboard's built-in DSP; put VST3 behind the already-speced render-difference test gate plus a locally applied patch. |
| **R2** | Any cheaper CPU path for stems? | **Yes, new.** A parity-verified **ONNX export of HT-Demucs FT** now exists and benchmarks **1.31x faster on CPU**. `htdemucs_ft` remains the top open vocal separator (~9.19 dB SDR). | **M3 gains a concrete first move** instead of "needs an eval harness first". Also consistent with the existing beat_this-ONNX pattern. |
| **R3** | Is the GPU shelf spec still right? | **Confirmed and sharpened.** ACE-Step 1.5 **2B runs under 4 GB VRAM**; XL 4B wants >=12 GB (>=20 GB recommended); runs on CUDA / ROCm / Intel XPU / Apple. HeartMuLa has emerged as a second peak. | **G9 unchanged and cheap.** One used 8-12 GB card unlocks local generation. Suno stays engine of record for now. |
| **R4** | Is basic-pitch really unavailable on Windows? | **No — obsolete assumption.** basic-pitch installs on Windows and **ships ONNX Runtime there by default**. | **Lift the `platform_system!='Windows'` marker.** This unblocks melody-carrier's primary melody path (F3). |
| **R5** | Should the video lane adopt an OSS pipeline? | **No candidate.** The field is fragmented (AudioGlow = GPU-accelerated, LyricsAnimator = MIT, plus AI-chain repos wired to cloud APIs). Nothing dominant. | **Keep the in-house FFmpeg + ASS + shader build.** F5's process violation stands, but the technical choice is retroactively sound. |

**Residual research still open:** groove-extraction prior art (carried since July); ADTOF-pytorch and
autochord have never been evaluated at all and should be gated before melody-carrier claims them.

---

## 7. Consolidation ledger — keep / combine / remove / shelve

| Asset | Verdict | Action |
|---|---|---|
| `toolshop/` core, `daw/` | **KEEP** | The spine — no change |
| `toolshop/melody_carrier/` | **KEEP** | Commit; add `melody` extra; lift the Windows marker; add `--require-advanced` |
| `ai_modules/vocal_cleanup` | **COMBINE** into T4 | Port `SilenceDetector`/`GapRemover` into `cleaning_stages`; try it against debt 1c |
| `ai_modules/production_analyzer` | **REASSESS** against T2 | Compare with `reverse_engineering_adapter` on real tracks; keep the winner only |
| `ai_modules/pattern_generator` | **COMBINE** into `daw/generators` or `melody_carrier` | |
| `ai_modules/suno_library` | **REMOVE** | Duplicate of `toolshop suno`; salvage `api_server.py` only if a local API is actually wanted |
| `ai_modules/stem_extractor` | **REMOVE** | Straight duplicate of T1 |
| `ai_modules/musicgen`, `lora_finetuning` | **SHELVE** | Move to the G9 GPU shelf with min-spec notes; they violate the CPU-only lock today |
| `ai_modules/*.db` (2 binaries) | **REMOVE from git** | Data belongs under `data/` |
| `Voicebox/` (410 files) | **REMOVE from git** | Parked; re-clone at the GPU gate — matches what `PROJECTS_INDEX.md` already claims |
| `Distro_Kidea/` | **MOVE** to `data/` | Audio/art assets, not repo root |
| root one-off scripts (8) | **MOVE** to `scripts/` | Decision pending since 2026-07-23 |
| 29 root `.txt` files | **REMOVE + ignore** | Add the missing glob patterns |
| `.coverage` | **REMOVE from git** | Tracked though ignored |
| `ORCHESTRATION/`, `docs/lyrics/`, 3 `docs/` research files | **KEEP** | Commit them — currently untracked |
| `MAirina_Tucc/` | **REASSESS** | Its rimer overlaps L5 `rimer_db` — decide: fold in, or keep as the UI surface |
| `open_DAW/` | **KEEP PARKED** | Stays out of the repo; E5 pack remains its future import format |

**Net effect if fully executed:** roughly **2,400 LOC removed** as duplicates, **3,000 LOC absorbed**
into existing lanes, **1,321 LOC shelved**, ~440 files untracked, and `doctor` able to return OK.

---

## 8. What is genuinely strong (so consolidation does not damage it)

- **The lyric-intelligence stack is the flagship and it works.** L1 to L5 complete on 1,425 songs,
  with two independent orchestrator verifications on record (L2.1, L3) that reproduced the numbers
  exactly. Cohort discrimination held up when the corpus doubled (Cohen's d 1.18 to 0.9841).
- **Test discipline is real** — 63 test files, TDD visible in every recent CHANGELOG entry.
- **The mechanical close-out gate is well-built** — it just needs to be run.
- **`mastering_tool` is a genuine daily-use product**, pushed and pointer-clean.
- **The data relocation (#030) was executed properly** — paths portable, backup source updated.
- **The failure mode is consistently close-out, never capability.** Every incident in this project's
  history is "excellent work, not recorded / not committed / not sequenced" — which is a far better
  problem to have than the reverse, and it is fixable in one session.

---

## 9. Handoff to the goals document

The phased strategy, revised goal set, and short-term attack plan derived from this assessment live
in **`2026-08-19-goals-v2.md`**. The immediate executable plan is
**`plans/2026-08-19-p0-consolidation-and-safety.md`**.
