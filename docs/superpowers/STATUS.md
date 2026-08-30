# Toolshop Portfolio Status Board

> Orchestrator-owned. Updated at each strategy review. Backlog of record: `specs/2026-07-15-longterm-roadmap-v2.md`;
> 12-month vision layer above it: `specs/2026-07-22-longterm-goals-12mo-full-studio.md` (v1.0).
>
> **H2 STARTED 2026-08-31. H2-M1 DONE — K-S key/mode. See CHANGELOG #047.**
> Horizon plan: `plans/2026-08-31-h2-dossier-v2-horizon.md` (M1 key · M2 structure · M3 beats ·
> M4 loudness · M5 faster-whisper lyrics · M6 schema v2 + regenerate 222).
>
> | Item | Result |
> |---|---|
> | **The defect, measured first** | `mode = chroma_mean[key] > 0.5` returned **`major` for 7 of 8** real tracks — it tested how loud one bin was, not the relationship between scale degrees. The lone `minor` had peak 0.471, i.e. minor by arbitrary threshold. Tonic was `argmax(chroma)` — the loudest pitch class, tonic only by coincidence. For a drill/trap catalogue (near-universally minor) this was wrong in the worst direction. |
> | **FOUR implementations, not two** | Initial scoping found two. A second pass found four — and the one first missed was **`reverse_engineering_adapter.py`, the dossier path itself**, writing the broken pair straight into `dossier.json`. `cleaning_stages._detect_key` compared minor-3rd vs major-3rd and was *better* than what the dossier used. All four now share one detector. |
> | **New `toolshop/key_detection.py`** | Krumhansl-Schmuckler over 24 rotated profiles. Pure numpy, no new dependency. Emits **confidence, runner-up, and margin** — K-S reliably confuses relative major/minor, and hiding that would make the dossier look more certain than it is. `dossier.json` gains `key_confidence` / `key_alternate` / `key_margin`. |
> | **Tests: 17, against known answers** | Synthetic scales in all 12 keys, relative-key ambiguity pinned, low confidence on chromatic input, and a scale-invariance test that pins the exact defect (×0.2 vs ×5.0 must not change the answer — the old rule flipped). |
> | **Measured diff** | mode changed on **4/8** (all major→minor), key on **2/8**. **Stated as a diff, not an accuracy claim** — there is no ground truth for those tracks. The old code is broken and K-S is standard; that justifies the change, not a correctness claim. |
> | **Test suite** | **1008 passed, 2 skipped, 0 failed** (451s) — +17 on the 991 baseline, no regressions. |
> | **A bug I introduced, caught by the suite** | An `np.array()` wrapper in `video_features` broke 5 tests — that module's tests patch its `np` wholesale, so the detector received a MagicMock. Unnecessary as well as wrong; fixed with a comment. |
>
> ---
>
> **S5 / M5 DONE 2026-08-30 — meta-layer registered, Voicebox ADR, root cleanup. See CHANGELOG #045.**
> **H1 IS CLOSED** (M1-M6 all done). **D12 RESOLVED 2026-08-30 — user agreed to descope the package
> reorg**; replaced by the opportunistic-subpackage rule now in AGENTS.md. H1 needs nothing further.
>
> | Item | Result |
> |---|---|
> | **REGISTRATION != DETECTION** | The exit criterion is *"session_brief detects project"*. `CANONICAL_PROJECTS` alone does **not** do that — `session_brief` never reads it. **Three** maps needed updating in `ai_dev_meta_layer`: `project_inventory.CANONICAL_PROJECTS` (path), `knowledge_router.PROJECT_KEYWORDS` (text), `knowledge_router.FILE_PATH_HEURISTICS` (paths — was returning `{}`). All three verified empirically; `mrp`/`yt_extractor` still route correctly (no over-match). Stopping at "added to the table" would have been the **4th** false claim this session. |
> | **Second repo, handled carefully** | `ai_dev_meta_layer` test baseline taken **before and after**: **30 failed / 508 passed both times** — identical, so those failures are pre-existing there, not mine. Registered as `music_ai_toolshop` (the lookup normalises dashes → underscores; a dashed key would be dead code). **Committed but deliberately NOT pushed** — pushing a second repo is the user's call. |
> | **[D12] Package reorg DESCOPED** | 55 flat modules, 63 importing test files. Declined: its own exit criterion is *"imports/CLI unchanged"* (delivers nothing observable); the roadmap says *"gradual … never a big-bang rewrite"*; a mass move behind re-export shims is where a green suite lies; and **H2 Dossier v2 is the real bottleneck**. **RESOLVED 2026-08-30 — user agreed.** Replaced by a standing rule now in AGENTS.md: subpackage moves happen *opportunistically*, when a lane is next touched substantially, with that lane's tests as the net. `daw/` and `melody_carrier/` already prove the pattern. **H1 closes without it.** |
> | **Voicebox ADR** | `specs/2026-08-30-adr-voicebox-archived.md` — records the P0 removal that shipped without one. States honestly that the upstream URL was never captured before untracking, and that **GPT-SoVITS**, not Voicebox, is the likely path if the lane reopens. |
> | **Root scripts — decided, not deferred a third time** | 3 with zero importers moved to `scripts/`; 4 stay because tests import them or `.ps1` launchers call them by path. Act where free, abstain where not. |
>
> ---
>
> **S4 / M4 DONE 2026-08-30 — mastering e2e VERIFIED + 2 findings. See CHANGELOG #043.**
>
> | Item | Result |
> |---|---|
> | **Pipeline** | **Two full `german_drill` runs, both exit 0**, complete `master/` (32f + 16-bit + 320 MP3) and `verification/` (QC, codec translation matrix, spectrogram, determinism MD5). Closes the item pending since 2026-07-13 (stage-E soft-clip previously verified in isolation only). |
> | **Stale plan corrected** | July plan's source dir died with `D:\MusicData` (#030); and it called for driving the tray **GUI**. The engine is `master_pipeline_v3.sh` with a clean CLI — driving the script is reproducible and tests the same chain. |
> | **2-pass auto-gain** | **Confirmed working.** Independent `ffmpeg ebur128` matched the pipeline's own report **exactly** (-8.3 / -8.7 LUFS) — it is not grading its own homework generously. |
> | **FINDING 1 — auto-gain pass 1 is systematically biased** | Sources 9 dB apart both landed at -12.2 / -12.3 LUFS after pass 1 (delta -4.2 / -4.3). A *constant* shortfall means pass 1 ignores limiter gain reduction, so **every run pays for two full limiter passes**. Folding in a measured limiter-loss constant would usually make it one. **Reported, not fixed** — daily-use product, does not block the run. |
> | **FINDING 2 — PSR gate unreachable at this target** | PSR **6.2** and **6.3** vs a gate of **>= 8**, from sources 9 dB apart. First assumed to be an artifact of a deliberately quiet premaster; **the control run disproved that**. At -8.0 LUFS `german_drill` cannot satisfy PSR >= 8. Target or gate is wrong — a **product decision**, not a code fix. |
> | **Codec overshoot** | AAC-256 exceeds the -0.8 dBTP ceiling in both runs (**+3.0** dBFS quiet source, **+1.5** louder). Opus marginal in both; MP3-320 passes on the louder source. A master clipping 1.5-3.8 dB after AAC is a real release concern. |
> | **Submodule** | **No `mastering_tool/` code changed** → no pointer bump. |
>
> **Open for the user (D11):** the PSR-gate vs `german_drill` target tension, and the AAC ceiling
> overshoot. Both are product calls, both now have two-run evidence behind them.
>
> ---
>
> **S3 / M3 DONE 2026-08-30 — stems CPU. One real win, one retraction. See CHANGELOG #042.**
>
> | Item | Result |
> |---|---|
> | **Scoping correction** | The S2 note implied R2 (HT-Demucs ONNX) would speed up the 26-min `vocals-hq`. It would not — R2 is the **demucs** backend; `vocals-hq` is **audio-separator**. The two do not overlap. |
> | **The real finding** | **Both adapters passed zero tuning parameters.** RoFormer ran `batch_size=1`; demucs ran `jobs=0` on an 8-core machine. So the first question was "how much is unconfigured defaults", not "what do we adopt". No new dependency was added. |
> | **A MISTAKE, found and corrected in-session** | The first sweep ran baselines **cold** and variants **warm**, measuring disk warm-up as compute. It reported **2.97x** (demucs) and **1.40x** (RoFormer); both were wired in. A full-track run then measured `vocals-hq` at **25.97 min vs a 26.06 min baseline = 1.00x, nothing**. The tells were in the data and were not read: batch4 (278.1 s) and batch8 (289.2 s) clustered, the lone cold baseline stood 110 s apart. |
> | **Controlled re-measurement** | Warm-up discarded, baseline repeated: demucs `jobs=0` 30.2 s / `jobs=4` **24.6 s** / `jobs=0` 29.6 s → **1.22x**, 2.0% drift (stable instrument). |
> | **Adopted** | demucs `jobs` via `auto_jobs()` — computed per machine (cores//2, capped at 4 = highest measured), overridable, never hardcoded (fleet has other CPUs). `4stem` ≈ **0.82x realtime, ~2.5 min for a 3 min track** — interactive. |
> | **Retracted** | MDXC `batch_size` default back to the library value. Plumbing kept (it makes future controlled tuning possible and testable); a test pins `batch_size == 1` with the reason so it cannot be quietly re-raised. |
> | **Survived the confound** | **Do not lower MDXC `overlap`** — `overlap=2` took 1023.8 s vs 278.1 s at `overlap=8`, a **3.7x slowdown**, warm vs warm. Lower overlap means *more* work. Pinned by a test. |
> | **R2 reinstated** | It was dismissed against the inflated 2.97x. Against the true **1.22x**, its reported ~1.31x is comparable or better and the two may compose. Evaluate on merit. |
> | **Milestone question answered** | **HQ separation still has to be overnight.** `vocals-hq` = 25.97 min / 9.11x realtime, unchanged. That needs a different model or different hardware, not tuning. |
> | **Test suite** | **991 passed, 2 skipped, 0 failed** (390s). +8 on the 983 baseline (`auto_jobs` scaling, pass-through both backends, the `overlap` guard, the `batch_size` retraction guard). |
> | **Left unmeasured, deliberately** | `mdx_params` (`karaoke`, `full-vocals`) and `vr_params`. Guessing there would repeat the mistake above. |
>
> **AGENTS.md gained a "Measurement discipline" section** — warm up and repeat the baseline; validate
> clip results on a full input; kill the watcher with the process it watches (three polling loops were
> leaked in one session before the user spotted them).
>
> ---
>
> **S2 / M2 DONE 2026-08-30 — model cache complete. See CHANGELOG #041.**
>
> | Item | Result |
> |---|---|
> | **Model cache** | Both missing RoFormer checkpoints fetched at exactly their expected sizes (609.7 MB + 870.8 MB). Cache 4/4, 0 missing, **0 orphans**. **`doctor` model_cache FAIL → OK.** |
> | **Provenance defect** | The karaoke model recorded `source=RVC-Boss/GPT-SoVITS` (a TTS project — not its origin) and `license="MIT"`. Corrected to the TRvlvr release. **Both RoFormer licences now read `unverified — see source`**: UVR's MIT does not extend to third-party models it merely redistributes, and the weight authors declared no terms. An admitted gap beats an asserted licence. |
> | **Companion configs** | The two models use *different* sidecar naming (`….yaml` vs `…_config.yaml`). Only the real download exposed this; both handled, test each. Either would previously have shown as a spurious orphan. |
> | **Integrity** | `docs/model_manifest.json` — sha256 + size + licence + source for 4 models and 2 configs. `verify_model_cache()` re-hashes; `doctor` size-checks every run. A test proves a present-but-wrong-bytes file **passes** the old check and **fails** the new one — the F1b trap, closed here before it could form. |
> | **Measured CPU cost** | **`vocals-hq` = 26.06 min for a 2.85 min track = 9.14× realtime** — past the 15 min/track rule, so it is an **overnight-batch preset**, not interactive. `full-vocals-hq` **not measured**; run stopped after its first pass, known only to be **>26 min** (lower bound, not a figure). |
> | **Debt 13b** | ~~FIXED~~ **— THIS CLAIM WAS WRONG, see #044.** Only `test_lyricsdb.py` was patched and only that file was checked. **Six** modules write to the tracked fixture. Really fixed in #044 via a shared `tests/_fixture_support.py`, verified against the **full suite** with a clean `git status`. |
> | **Test suite** | **983 passed, 2 skipped, 0 failed** (457s). **+9 on the 974 baseline** (7 model-integrity tests, 2 new doctor tests). No test weakened. |
> | **A test caught, not weakened** | `test_model_cache_ok` asserted that a cache of **zero-byte placeholders** was healthy; the new size check correctly rejected it. The assertion was **not** flipped (that is how debt 1c happened). Its intent was restored (presence-only, manifest pointed away), and two tests added for what it could no longer cover: present-but-wrong-size, and a corrupt manifest not masking a good cache. `test_doctor.py` 16 → 19. |
> | **Clock** | The machine clock advanced ~10 days mid-session; backup-age readings across this wave are inconsistent. Backup re-run at close-out: 6,925 files, 118.5 MB, verified, DB smoke PASS. `docs/model_manifest.json` is deliberately **not** in the backup — it is version-controlled, so git is its protection. |
>
> **Next: S3 — M3 stems CPU** via the HT-Demucs FT ONNX export (R2, ~1.31× faster). The `vocals-hq`
> measurement makes that lane more valuable than it looked: HQ separation currently costs ~9× realtime.
>
> ---
>
> **P0 EXECUTED 2026-08-19/20 — consolidation + safety. See CHANGELOG #038–#040.**
>
> | Item | Result |
> |---|---|
> | **Suno preservation** | **3,426 / 3,426 tracks fetched, 15.79 GB, 0 failures**, 27.6 min. All 17 records that had no `audio_url` recovered by reconstructing the deterministic CDN path. D: 146 → 131 GB free. **Reconciled independently:** 3,426 metadata ids = 3,426 manifest entries (all `ok`) = 3,426 files on disk (15.90 GB); **0 missing, 0 orphans, 0 ids absent from the manifest, 0 size mismatches, 3,426 sha256 recorded.** |
> | **Backup coverage (F1b)** | Fixed. Tier-1 now carries Suno metadata + download manifest; Tier-2 carries the mp3s behind `--include-audio`; `_discover_external_assets()` reaches `suno_extractor/`. **+4 regression tests.** |
> | **Backup run** | `D:\Backups\toolshop` — **6,925 files, 118.5 MB, verified=True, DB smoke test PASS**, including **3,427 Suno metadata files (was 0)**, the download manifest, and the 50 `docs/lyrics` files git no longer tracks. |
> | **`doctor` backup check** | **FAIL (29d, C:) → OK (6,925 files, age 0d, verified, D:).** The default target was moved into code (`backup.DEFAULT_BACKUP_TARGET`) and `doctor` now defers to it — the two had drifted, so a fresh backup was being reported as a month-old failure. **`model_cache` is now the only failing check**, and that is M2 = session S2. |
> | **melody-carrier (F3)** | Committed (#039): 6 modules, 1,868 LOC, 107 tests. Obsolete `platform_system!='Windows'` marker lifted, `melody` extra added, **`--require-advanced` guard** added (pre-flight + runtime check). +6 tests. |
> | **`ai_modules/` (F2)** | **UNTOUCHED by decision (D6 deferred).** Recorded only — see the lane table below. |
> | **Hygiene** | 29 root run-dumps deleted, `.gitignore` globs added, `.coverage` untracked, **`Voicebox/` untracked (410 files, D9)**. Tracked files 2,256 → 1,859. |
> | **Test suite** | **974 passed, 2 skipped, 0 failed** (347s) — orchestrator re-ran it twice: once through `f532abf` and again on the final tree through `e36f509`. **+11 on the 963 baseline** (5 backup coverage tests, 6 melody-carrier guard tests). No test was weakened. |
> | **Records** | README (backups + 4 new command groups), PROJECTS_INDEX (742→1,425, stale `D:\MusicData` paths gone, 5 lanes added), AGENTS.md (lane-discipline rules), this board. |
> | **Deferred deliberately** | The 8 tracked repo-root one-off scripts. All have live importers (`tests/`, `toolshop/batch.py`) or doc references; relocating them needs import updates and deserves its own pass, not a shuffle at the end of a long session. |
>
> **Data-boundary call made during P0:** `docs/lyrics/` was committed **doctrine-only**. The nine
> song-specific documents and `reference_songs/` contain actual lyrics and are now gitignored, matching
> the existing `lyrics_research/my_lyrics/` rule. Tracked: Constitution, Craft KB, Anti-Slop Playbook,
> Sound-Effects Principles, `qc_reference.py`, lexicons, templates.
>
> ---
>
> **Last review: 2026-08-19 (FULL STATE ASSESSMENT — orchestrator, all evidence re-run locally).**
> Full report: `specs/2026-08-19-state-of-project-assessment.md`. New goal set + phased strategy:
> `specs/2026-08-19-goals-v2.md` (supersedes goals v1.0). Executable next session:
> `plans/2026-08-19-p0-consolidation-and-safety.md`.
>
> **Verified this session:** repo at `31224e5`, branch master, **0 unpushed**. Suite
> **963 passed / 2 skipped / 0 failed** (689.20s) — re-run by orchestrator, genuinely green (the
> "1 failed espeak" line below is stale). `lyrics.db` queried directly: **1,425 songs / 10,654
> sections / 65,912 lines / 273,801 line_rhymes / 501,386 tokens / 163 topics / 13,036 rhyme_pairs**;
> cohorts drill_trap 808 / pop 524 / NULL 93. `toolshop doctor` = **FAIL** (model_cache + backup).
>
> **Findings (ranked, detail in the assessment):**
> - **F1 CRITICAL — backup 28 days stale on a 98%-full destination.** Last write 2026-07-21; corpus
>   has since gone 742→1,425 songs. C: has 14 GB free. `backup.py` source path *was* correctly
>   updated for #030 — it simply has not been run.
> - **F1b CRITICAL — the backup has NEVER covered Suno** *(found after the initial pass)*.
>   `_discover_assets()` collects only genius json/txt + `lyrics.db` + `espeak-ng`;
>   `_discover_repo_assets()` adds `.env`, lyrics_research reports, 3 catalogue files. **No Suno path
>   is in either list**, so the 2026-07-21 backup that verified clean holds **zero Suno data** — a
>   *coverage* bug that a green manifest hid for a month. At stake: **3,426 metadata JSONs** (small,
>   irreplaceable, the only index of what exists) and **37 mp3s / 211 MB** at
>   `D:\Projects\suno_extractor\suno_downloads\` (outside the repo, so no source root reaches it).
>   **The other ~3,389 tracks are not on this machine at all** — they exist only as
>   `https://cdn1.suno.ai/<id>.mp3` links, which no backup can protect. Fetching them locally
>   (~13–15 GB) is a preservation task needing its own plan and explicit authorisation → **D10**.
> - **F2 HIGH — `ai_modules/` (6,390 LOC, 40 files) entered via commit `31224e5`, whose subject says
>   "chore: update mastering_tool submodule".** No CHANGELOG (#038 absent), no STATUS row, no plan.
>   Its 7 test files (1,440 LOC) sit outside `testpaths = tests` and are **never collected**. Largely
>   duplicates T1/T2/T4/suno; `musicgen` + `lora_finetuning` violate the CPU-only lock. Partly copied
>   from the **parked** `open_DAW/ai_modules/`.
> - **F3 HIGH — `toolshop/melody_carrier/` (2,043 LOC + 5 test files + tracked `cli.py` edits) is
>   uncommitted**, four weeks after the mechanical gate was installed. Its three primary ML backends
>   (`basic_pitch`, `autochord`, `adtof_pytorch`) are **all absent from the venv**, so every run takes
>   the librosa fallback; there is no `melody` extra; and `pyproject.toml` excludes basic-pitch on
>   Windows via a marker that research verdict R4 shows is **obsolete**.
> - **F4 HIGH — governance reverted to documentation-only.** Zero plans written since 2026-07-23
>   while 13 CHANGELOG entries + 2 undocumented lanes shipped. 8th+ out-of-band instance.
> - **F5–F10 MEDIUM/LOW** — video + melody lanes never research-gated; debt 1c still open (and
>   `ai_modules/vocal_cleanup` may hold its fix); M2 model cache still missing; 778.93 MiB pack,
>   410 tracked `Voicebox/` files, 29 root `.txt`, stale `PROJECTS_INDEX.md` (still says 742 songs at
>   `D:\MusicData`) and README; Agent D's orchestration handoff relayed L2.1-era DB numbers; waves 3–4
>   never ran.
>
> **Research re-verified 2026-08-19:** pedalboard **PR #476 still OPEN** (VST3 renders dry on Windows
> → E2 ships on built-in DSP only) · **HT-Demucs FT ONNX export now exists, ~1.31× faster on CPU**
> (gives M3 a concrete first move) · ACE-Step 1.5 2B **<4 GB VRAM** (G9 shelf confirmed) ·
> **basic-pitch DOES support Windows** (lift the marker) · **no dominant OSS music-video pipeline**
> (keep the in-house build).
>
> **Verdict: FREEZE new lanes. Next session = P0 consolidation + safety** (plan written).
>
> **User decisions taken 2026-08-19:** **D5 RESOLVED — P0, then P1 (keystone).** H1 close + Dossier v2
> run before further creation-loop work. · **D7 RESOLVED (revised) — Tier-1 backup target is a path on
> D:** (~148 GB free; C: abandoned at 98% full). Recorded honestly as Tier-1 convenience, **not DR** —
> D: is the 2010 Seagate holding everything; second-disk copy stays open under G5. · **D6 DEFERRED —
> user is reviewing `ai_modules/` first; P0 leaves it byte-identical** and only adds an honest STATUS
> row (exists, uncollected by pytest, disposition pending). · **D10 OPEN (new) — fetch the ~3,389
> CDN-only Suno tracks locally?** Recommended, needs explicit go-ahead. D8/D9 still open (goals v2 §8).
>
> **P0 plan updated:** new **Task 1b** (fix backup coverage — blocks the backup run itself) and
> **Task 1c** (record the CDN exposure, download nothing).
>
> **Session order now:** S1 = P0 consolidation · S2 = M2 model cache + mirror (flips `doctor` to OK) ·
> S3 = M3 stems via the HT-Demucs FT ONNX export (R2).

> **Prior review: 2026-08-08 (STATUS.md RECONCILIATION — #025–#036 reflected).**
> Repo at `84d7f65` (origin/master). Tree clean (only pre-existing `mastering_tool` submodule dirty).
> Test baseline: **780 passed, 1 failed (pre-existing espeak), 4 skipped** (256s).
>
> **#025–#036 summary (12 entries since last review on 2026-07-23):**
> - **#025** FL Studio DAW Phases 1-4: 12 modules, 143 tests, 17 CLI subcommands (`toolshop/daw/`)
> - **#026** Pro fingerprints: 16 artists + 2 cohort rollups, 3-value sanity gate verified (`pro_fingerprints.md`)
> - **#027** Batch 3 corpus expansion: 8 new artists, 722 new songs → **1,425 total** (was 742)
> - **#028** Music Video Generator P0+P1: 7 modules, 72 tests (FFmpeg compositing, shaders, stock footage)
> - **#029** L1-L4 pipeline re-run on 1,425 songs: 10,654 sections, 65,912 lines, 273,801 rhyme rows; CLASSLA 100% coverage; 163 BERTopic topics; JSD=0.7312; SQLite variable-limit fix in fingerprint.py
> - **#030** MusicData relocation: `D:\MusicData` → repo-local `data/` (portable paths, 18 files updated)
> - **#031** Batch 3 follow-up: test fixes, Suno gap report (3,381 AI vs 1,315 pro), Cohen's d=0.9841, collab network (252 artists, 370 edges)
> - **#032** Lyrics transformer: vocabulary + slang directions, 17 TDD tests
> - **#033** Transformer extensions: structure + flow directions, 15 TDD tests
> - **#034** Transformer rhyme scheme enhancement: 10 TDD tests
> - **#035** Lyrics corrector: 27 TDD tests, whitespace/phonetic/section/diacritic checks
> - **#036** 10 craft modules B1-B10 + CLI + research docs: 89 tests, 2,414 lines new code
>   (`token_cleaner`, `cliche_checker`, `structure_template`, `ai_scorer`, `scheme_checker`,
>   `slang_injector`, `similarity_retriever`, `theme_comparator`, `improve_loop`, `centaur_app`)
>
> **L1–L4 ALL DONE.** L5 (Writing Tools) is the next phase per `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md`.
>
> **Prior review: 2026-07-23 (T5-L3 INDEPENDENT VERIFICATION — VERIFIED PASS · #024).**
> All #021 claims independently reproduced from `lyrics.db`: annotation coverage 36,572/36,572
> lines (100%), 282,426 tokens, 6,708 entities — all match. Slang: 6,984 terms, 2,421 drill / 1,741
> pop distinctive, distinctiveness recompute max diff 0.0000 (10-term sample, seed=42). Themes: 84
> topics, 2,283 section_topics, JSD=0.2015 reproduces exactly. Gate: all three conditions PASS
> (slang + strong slang + theme discrimination). Direction consistent with L2.1 (different dominant
> topics, 2/5 overlap in top-5). Report: `lyrics_research/reports/2026-07-23_l3-verification.md`.
> **#021 is now REVIEW-CLEARED.** L4 (fingerprints + gap report vs 2,633 Suno lyrics) is unblocked.
>
> **Prior review: 2026-07-23 (Q1-S0 HYGIENE + CLOSE-OUT GATE — VERIFIED PASS · #023).**
> Orchestrator re-ran everything independently: pytest **429/0** (matches handoff), `toolshop
> closeout` **exit 0 PASS**, origin sync empty, `core.hooksPath=hooks` + doctor OK, `.gitignore`
> globs live, docs wave on origin. The close-out gate is now MECHANICAL (CLI verb + tracked
> pre-push hook + doctor check). First fully honest handoff in the sequence — deviations
> documented, wrong-approach config hack self-corrected and disclosed. **Q1 step 0 DONE.**
> Mystery explained: the plan's premises (3 unpushed commits, 12 junk files) had been consumed by
> a **6th out-of-band L3 session** (`7a93ad7`/`de2a528`/`2893394`, #021 claims "L3 discrimination
> gate PASS") which pushed + cleaned before Q1-S0 ran — benign this time, but **#021 is
> UNREVIEWED → next session = L3 spot-check (Q1 item 1)**. Pending orchestrator decisions
> (root-clutter audit, handoff §6): tracked one-off scripts (`diagnose_voice_analysis.py`,
> `check_batch_status.py`, `recover_batch_status.py`, `generate_crhymetv_catalogue.py`,
> `run_papapedro_pilot.*`) + `.coverage` tracked-though-ignored → keep / scripts-dir / git-rm at
> next consolidation. Minor debt: closeout docstring claims a pointer-on-remote check the code
> doesn't implement; doctor overall FAIL = pre-existing model_cache gap (M2 scope).
>
> **Last review: 2026-07-22 evening (FULL-STUDIO MANDATE adopted + landscape research received).**
> User widened scope to a complete studio toolkit (goals G1–G10, quarters Q1–Q4): new lanes =
> composition/MIDI, synthesis palette, mixing chains, vocal correction; **3-machine fleet**
> (2× i7-4770-class + 1× i5 9th-gen, all 16 GB) enables batch grid + TRUE cross-machine DR;
> stronger machines later → GPU shelf maintained with specs. Research report:
> `research/2026-07-22-full-studio-oss-landscape.md` — verdicts folded into goals §8 as `likely`
> (evidence bar unmet; re-verify at adoption). **Key alerts from the report:**
> (1) pedalboard **VST3-effects-render-dry bug (PR #476, open)** → mandatory test gate in E2;
> (2) sfizz ARCHIVED → FluidSynth is the durable SF2/SFZ path; (3) LSP Windows builds will be
> PAID → free mixing-suite question still open (goals §8.3); (4) `.als` generation has real prior
> art (ableton-set-builder, als-wire, ableton-project-processor) → **E6 substantially de-risked**;
> (5) GPU shelf is cheap now — ACE-Step v1.5 (MIT, SOTA) needs <4 GB offloaded; one used 8–12 GB
> card unlocks nearly everything (G9 spec target). **Discipline flag: 3 L3 commits UNPUSHED
> (`2318878..6f44a3c`) + 12 junk `pytest_*.txt` in repo root — push + cleanup precedes any new lane.**
>
> **Addendum same evening: gap-fill research received + verified** (`research/2026-07-22-gapfill-report.md`
> — this one MET the evidence bar; verdicts folded into goals §8.3). Mixing-suite question RESOLVED:
> Airwindows Consolidated (MIT) + ZL EQ2/Compressor (AGPL) + Dragonfly Reverb (GPL) for free Windows
> VST3. Phantom (`phantom-audio`) = stem-masking analysis INTEGRATE candidate for T8/E-lane.
> Confirmed real gaps: no OSS auto-mixing (diagnose-and-suggest only), no OSS VocAlign-style
> time-warping. Composition v0 stack fully specified (MusicLang + mido/pretty_midi + drum gens +
> FluidSynth/sforzando; miditoolkit SKIP-stale). CC0-first instrument content sourced (VCSL,
> Meadowlark, TR808-fischer, GareBear99 808s). AbletonOSC INTEGRATE (slow but only bridge);
> FL = still a poor generation target → D1 stands. All research now CLOSED except
> groove-extraction prior art (rhythm-lane fold-in).
>
> **Prior review: 2026-07-22 (T5-L2.1 INDEPENDENT VERIFICATION — PASS).** All four verification tasks
> succeeded: (1) per-artist fingerprints reproduced exactly vs baseline report; (2) discrimination proven
> — Cohen's d = 1.18 (large), pop median RF 0.7399 > drill median 0.5628, overlap 13.4%/8.9%;
> (3) persistence intact — 742 song_rhyme_metrics rows, 159,171 line_rhymes, 49.3% match_length≥3,
> 125,862 internal; (4) persisted==engine max abs diff 0.000000 (15-song random sample, seed=42).
> Report: `lyrics_research/reports/2026-07-22_l2-1-verification.md`. L3 (themes) gate confirmed OPEN.
> Multi-phase roadmap: `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md`.
>
> **Prior review: 2026-07-21 late (T5-L2.1 spot-check — PASS, now independently confirmed).**
> CI is **billing-locked** (GitHub account); gate on LOCAL pytest instead. True local baseline is
> **19 failed / 343 passed** — the extra 9 are pre-existing NON-lyrics (~8 MissingDependencyError
> from `.[remix]` not installed + 1 demucs). **Zero lyrics failures.**
>
> **Prior review: 2026-07-21 (T5-L1.1 spot-check — CORRECTS the 07-17 entry below)** — L1.1 DID run
> (commits 7ec54d4/fa3fcd6/ad00bc3): **defect-1 fold IS applied** (0 diacritics / 0 Cyrillic left in
> text_norm bar 1 homoglyph; nećemo→necemo, leđa→ledja), **genre-cohort schema IS added** (drill_trap
> 286 / pop 214 / NULL 198; featured 44 excluded), `other` 38%→**0.9%**, 742 songs, no new test failures.
> So the "L1.1 residual still open" claim just below is STALE — do not redo it. **NEW CRITICAL FINDING:
> the L2 rhyme fingerprint is defective** — `line_rhymes` is 34,598 rows of ONLY match_length=2 end
> rhymes; multis/internal/rhyme_factor/scheme are computed in code but NEVER persisted, so every artist
> saturates at ~95% rhyme rate and the fingerprint CANNOT discriminate. L2 is NOT review-cleared; fix
> populate_rhymes before any fingerprint/gap-report work. **7 commits still UNPUSHED (zero backup).**
> ⚠️ Multiple out-of-band sessions (L2, flow analyzer, a whole T8/T9 strategy pack) are outrunning
> review and rewriting this board — recommend a freeze: push, reconcile board to verified reality,
> then resume. Original 07-17 entry (for history, PARTLY STALE):
> — T5-L2 executed out of
> band while the L1.1 plan sat unstarted: it ABSORBED part of L1.1 (parser fix 1030→292 "other"; rebuild
> over 742 songs/7 dups) and delivered rhyme miner (34,598 rows), flow analyzer v1, collab CLI, Datasette
> (evidence strong: 191 passed). New strategy pack:
> `specs/2026-07-17-production-expansion-strategy.md` (T8 Restore "Track Doctor", chains core, T9 Session
> Bridge; AI-plugins reframed offline; DAW decision-gated). First plan ready: `plans/2026-07-17-e1-restore-diagnose.md`.
> **Gates D1–D4 RESOLVED same evening:** D1 = Ableton Live 12 native target (.als writer; FL 21 via
> universal pack; open_DAW parked, E5 pack = its future session format) · D2 = M6 first (plan ready:
> `plans/2026-07-17-h1m6-backups-data-governance.md`; D: is a 2010 laptop HDD — urgency real) ·
> D3 = plugin park confirmed · D4 = E4 waits for post-E3 review.

## H1 Milestone Board

| Milestone | State | Notes |
|---|---|---|
| M1 CrhymeTV analyze-only | ✅ CLOSED 2026-07-16 | 221 completed + 1 skipped_long, 0 errors; catalogue `Tracks: 222`; advanced-backend incident caught & guarded |
| M1c-final consolidation | ✅ CLOSED 2026-07-17 | 6 commits (ec42fb5..9054bf0); index rebuilt (385 songs); resume fix (11/11 tests); submodule aebcf76 (verified pushed to its remote); handoff `2026-07-17_004500`. **Orchestrator spot-check correction: CI is NOT green** — red since ≥2026-05-06 (pre-existing; see debt item 1). |
| M2 Demucs e2e + model mirror | ⏸ Ready, gated on M1c-final | Plan + prompt embedded |
| M3 Stems CPU optimization | ⬜ Not started | Needs museval eval-harness seed first (integration map §4) |
| M4 Mastering german_drill e2e | ⏸ Ready (unblocked) | Submodule committed (aebcf76); pointer bumped |
| M5 Suite reorg + meta-layer registration | ✅ DONE 2026-08-30 (#045) | Registered in all 3 meta-layer maps (path + text + file detection), verified empirically. AGENTS.md live. Voicebox ADR written. Root scripts decided. **Package reorg descoped (D12, user-agreed 2026-08-30)** — replaced by the opportunistic-subpackage rule in AGENTS.md. |
| M6 Backups + doctor disk/backup checks | ✅ DONE + committed/pushed 2026-07-22 (#019, `27cfa35`) | Backup ran: `C:\Backups\toolshop` 1954 files/32 MB, manifest+verify OK; `toolshop doctor` backup check added; suite green (383 passed/1 skipped/0 failed). Caveats: backup on C: = same physical disk as D: (not true DR); `.env` token now in backup (never sync/commit that dir). **⚠ Data relocated to `data/` (#030) — backup paths need revalidation.** |

## Tool Lanes

| Lane | State | Next meaningful step |
|---|---|---|
| T1 Stems | v0.4 shipped; idle | M2 (models+mirror), then M3 (CPU opt) |
| T2 Dossier/RE | v1 live; **222-track catalogue is the first cross-tool asset** | H2 (Dossier v2) after H1 |
| T3 Mastering | Working daily product; submodule clean (aebcf76) | M4 verification |
| T4 Vocal Lab | Shipped detectors/cleaning; idle | H2 (faster-whisper) |
| T5 Library Intelligence | lyrics.db over **1,425 songs** (was 742); 10,654 sections, 65,912 lines, 273,801 rhyme rows; L1.1 + **L2.1 VERIFIED PASS** (report: `lyrics_research/reports/2026-07-22_l2-1-verification.md`); **L3 VERIFIED PASS** (report: `lyrics_research/reports/2026-07-23_l3-verification.md`); **L4 DONE**: pro fingerprints (16 artists + 2 cohort rollups, `pro_fingerprints.md`), Suno gap report (3,381 AI vs 1,315 pro, `suno_gap_report.md`), Cohen's d=0.9841 (expanded corpus), collab network (252 artists, 370 edges); **10 craft modules** (#036): `score-ai`, `cliches`, `template`, `clean-tokens`, `inject-slang`, `check-scheme`, `retrieve-similar`, `theme-match`, `improve-loop`, `centaur`; **lyrics transformer** (#032-#034): vocabulary/structure/flow/rhyme directions; **lyrics corrector** (#035): 27 tests; roadmap `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md` | **L5 NEXT** — rimer DB (attested pro rhyme pairs), brief generator for Suno, draft scorer with originality check |
| T6 Creation Bridge | Transformer + corrector + craft modules now consume T5 outputs | **L5**: rimer DB, brief generator, draft scorer — the payoff writing tools |
| T7 Sample Forge | v1 partial: section-consuming forge + spec-aligned naming shipped; auto-detection deferred to H2 structure detector | H2: automatic section detection; H3: its pedalboard pick promoted to core chains (E2) |
| **T8 Restore "Track Doctor"** | **NEW lane** — strategy adopted 2026-07-17 (`specs/2026-07-17-production-expansion-strategy.md` §1) | **E1 plan ready**: `plans/2026-07-17-e1-restore-diagnose.md` (impurity metrics + report + batch sweep); then E2 chains core → E3 treat v1 → E4 heavy de-reverb only after E3 proves daily value (D4 decided) |
| **T9 Session Bridge** | **NEW thin lane** — dossier → DAW-ready session (universal pack first) | E5 universal export after E1–E3; **E6 = `.als` template writer for the user's Ableton Live 12** (D1 decided; FL 21 served by universal pack; AbletonOSC optional later) |
| **Video** (new #028) | Music Video Generator P0+P1: 7 modules, 72 tests — FFmpeg compositing, ASS lyrics, audio-reactive shaders, stock footage | Real-world testing with actual tracks; P2 (advanced transitions, beat-synced cuts) |
| **Melody Carrier** (new #039) | Audio→MIDI→carrier WAVs for Suno cover mode. 6 modules, 1,868 LOC, 107 tests. Committed 2026-08-19 after sitting uncommitted; `melody` extra + `--require-advanced` guard added | Install the advanced backends and measure the quality delta vs the librosa fallbacks (P2) |
| **`ai_modules/`** | ⚠ **UNDECIDED — D6 deferred, user reviewing.** 40 files / **6,390 LOC**, committed 2026-08-18 in `31224e5` under a submodule-chore subject. **Its 7 test files (~1,440 LOC) sit outside `pytest.ini`'s `testpaths = tests` and are never collected — this code is untested by the suite.** Overlaps T1/T2/T4/suno; `musicgen` + `lora_finetuning` violate the CPU-only lock. Partly copied from the parked `open_DAW/` | Disposition per the ledger in `specs/2026-08-19-state-of-project-assessment.md` §7 — **recommendation only, awaiting the user's review** |
| Parked | open_DAW (own Rust/JUCE/Python DAW build — E5 pack designed as its future session-import format), Voicebox (untracked from git 2026-08-19, D9), ACE-Step local, **real-time plugin authoring (D3 confirmed)** | No investment (roadmap §6 + expansion spec §4/§6) |

## Debt Register (after M1c-final: items 2–6 cleared)

1. ~~`test_cleaning_pipeline.py` numpy-scalar failures~~ → ✅ 9 fixed 2026-07-21 (`_scalar_tempo` for
   numpy-2.0 0-d tempo). **BUT the 10th was never numpy** — `test_keep_short_pauses` exposed a REAL
   functional bug: `PauseRemovalStage` ignores `min_silence` and removes ALL silence. Coder weakened the
   test to green (`segments_kept 1→2`) with a TODO instead of fixing the code. → **Debt 1c: min_silence
   non-functional in PauseRemovalStage (T4 Vocal Lab) — real bug, masked, not resolved.** Also note CI
   red is a **billing lock**, not tests (corrected 2026-07-21).
1b. ~~Index paths written absolute (`D:\MusicData\...`)~~ → ✅ cleared by #030 (data relocated to
    repo-local `data/`, all paths made portable).
2. ~~Uncommitted work wave~~ → ✅ cleared (5 commits + plan tick)
3. ~~Resume-status bug~~ → ✅ cleared (11/11 tests green)
4. ~~Extractor index bugs~~ → ✅ cleared (385 entries, 8 rebuild tests)
5. ~~Mastering submodule uncommitted~~ → ✅ cleared (aebcf76)
6. ~~PROJECTS_INDEX stale~~ → ✅ cleared (lyrics lane added)
7. ~~No backups of MusicData/catalogues/tokens~~ → ✅ **CLEARED 2026-08-19 (#038).** Target moved to
   `D:\Backups\toolshop` (D7); **coverage bug F1b fixed** — the backup had never collected any Suno
   data at all, which is why a green manifest hid the gap for a month. Verified run: 6,871 files /
   117.4 MB / verified=True, including 3,427 Suno metadata files (was 0). **Residual: still same-disk,
   so not DR — G5 owes a second physical disk.**
7b. **Suno CDN dependency** → ✅ **CLEARED 2026-08-19 (#038).** All 3,426 tracks now local
   (15.79 GB, 0 failures). Previously ~3,389 existed only as `cdn1.suno.ai` links.
13b. **A test dirties the tracked tree on every run** (found during P0). `test_build_database_dedup_log`
   (and neighbours) call `build_database(root=FIXTURE_ROOT, ...)`, and `build_database` writes
   `_dedup_log.json` **into `root`** — which is the tracked `tests/fixtures/lyrics_min/`. So a plain
   `pytest` run leaves `tests/fixtures/lyrics_min/_dedup_log.json` modified (a drive-letter case
   flip, `d:` → `D:`). **This quietly undermines `toolshop closeout`'s clean-tree check**, which is
   the gate the whole close-out discipline rests on, and it is why that file showed up dirty at the
   start of this session too. Fix: have the tests copy the fixture into `tmp_path` first, or teach
   `build_database` to take a separate output root. Small, but it weakens the mechanism.
14. **`ai_modules/` tests are never collected** (F2) — 7 files / ~1,440 LOC outside
   `testpaths = tests`. 6,390 LOC of committed code is untested by the suite. Blocked on D6.
15. **Repo-root one-off scripts** (8 tracked) — deferred from P0 Task 6; all have live importers or
   doc references, so relocation needs import updates in its own pass.
16. ~~`docs/lyrics/` song documents have no protection~~ → ✅ **CLEARED in the same wave.** Excluding
   them from git left them protected by nothing, so `_discover_repo_assets()` now backs up
   `docs/lyrics/**` and `lyrics_research/my_lyrics/**` (+1 test). **General rule, now in AGENTS.md:
   excluding something from version control must not silently exclude it from the backup.**
8. ~~L1 defects~~ → ✅ cleared (parser fix + ASCII-fold normalization applied, #029 re-ran on 1,425 songs)
9. ~~`extract_batch2.py` uncommitted~~ → ✅ cleared (committed in #027 wave)
10. ~~T5-L2 leftovers~~ → ✅ cleared (all commits pushed, CHANGELOG entries #016-#036 present,
    espeak-ng env vars documented in #030 note)
11. ~~L2 `line_rhymes` on pre-fold `text_norm`~~ → ✅ cleared (#029 re-ran full pipeline on 1,425 songs
    with fixed normalization; 273,801 rhyme rows computed on ASCII-folded text)
12. **espeak-ng path moved** (#030): env vars `PHONEMIZER_ESPEAK_PATH` and `PHONEMER_ESPEAK_LIBRARY`
    must point to `data/toolshop/espeak-ng/` (was `D:\MusicData\toolshop\espeak-ng/`).
13. **STATUS.md was stale for 12 entries** (2026-07-23 → 2026-08-08). 5+ out-of-band sessions delivered
    #025-#036 without updating this board. → This reconciliation addresses it. Mitigation: STATUS.md
    update should be part of closeout discipline going forward.

## Recommended Sequence — Q1 (Aug–Oct 2026, per goals v1.0 §6)

0. ~~Hygiene FIRST~~ → ✅ **DONE, VERIFIED 2026-07-23** (#022/#023)
1. ~~**T5-L3 SPOT-CHECK**~~ → ✅ **DONE** (#024)
1b. ~~**L4 fingerprints + gap report**~~ → ✅ **DONE** (#026, #029, #031): pro fingerprints, Suno gap
    report, Cohen's d on expanded corpus, collab network — all complete
1c. ~~**Craft modules B1-B10**~~ → ✅ **DONE** (#032-#036): transformer, corrector, 10 craft modules,
    CLI integration, research docs
2. **L5: Writing Tools** — rimer DB (attested pro rhyme pairs), brief generator for Suno, draft scorer
   with originality check (n-gram overlap vs corpus). The payoff: write ONE real song with the tools.
3. **H1 close:** M2 Demucs e2e · M4 mastering e2e (any evening) · M3 CPU opt (+ museval seed) · M5 reorg
4. **E1 restore diagnose** (plan ready) → **E2 chains core** (⚠ include PR#476 VST3 dry-render test
   gate) → **E3 treat v1**
5. **H2 Dossier v2** milestone chain (K-S key, structure, beats, chords, faster-whisper lyrics)
6. **Fleet pilot (new, G5):** 2-machine shared-folder/SQLite job-queue pilot on the existing batch
   engine + Syncthing/rclone sync + **first true cross-machine backup** (kills the same-box DR caveat)
7. **New-lane opener (research-gated, last):** composition/MIDI v0 — MusicLang + drum-gen +
   wobblemidi + FluidSynth render path (goals §8.1); residual research items per goals §8.3

## Standing Observations (orchestrator)

- Coder sessions deliver strong evidence but drift on close-out discipline (commits/CHANGELOG deferred
  3× now). Mitigation: consolidation sessions like M1c-final + "no new features until clean" rule.
- **New instance 2026-07-17:** M1c-final coder ticked "CI green" without checking — CI was and is red
  (pre-existing since May). Rule going forward: CI claims require pasted run URL/conclusion in the handoff;
  plans must say "no NEW failures" instead of "CI green" until debt item 1 clears.
- **Out-of-sequence work, 3rd instance (2026-07-17):** index rebuild, then a full batch-2 extraction
  (386→749) both landed outside the tracked sequence — good data, but it invalidated the L1 DB before
  L1 cleared review. Corpus growth is welcome; do it via a tracked plan so downstream artifacts (DB,
  reports) are rebuilt in the same pass, not left stale. L1.1 folds this batch in.
- **4th instance (2026-07-17 evening): T5-L2 ran while L1.1 was the tracked next session.** It silently
  absorbed the easy half of L1.1 (parser, rebuild) and skipped the hard half (normalization fold, cohorts)
  — then built 34,598 rhyme rows on top of the un-fixed normalization (debt 11). Work quality itself was
  high (TDD, evidence). Orchestrator adaptation: after any out-of-band session, write a RESIDUAL plan
  (don't re-run superseded plans) and check what the new work silently depends on. Also L2 repeated the
  close-out drift (unpushed, uncommitted tree edits, no CHANGELOG) — debt 10; the gates are now written
  INTO plan task lists (see E1 Task 6) instead of trusted to convention.
- **Deviation framing watch:** the L1 handoff labeled the normalization diacritic mismatch "correct
  behavior." Spot-check found it's a real defect (Cyrillic-source tokens don't unify with Latin-source).
  Lesson: a "deviation" that changes output semantics gets verified, not accepted on the handoff's framing.
- Handoffs citing docs ("per README") instead of verification: spot-check such claims in every review.
- The data boundary rule needs to be enforced *in code defaults* (output paths), not just documented —
  M1c-final Task 1 does this for the extractor. **✅ Resolved by #030** (all paths made repo-relative).
- **5th+ instance of out-of-band work (2026-07-27 → 2026-08-07):** 12 CHANGELOG entries (#025-#036)
  shipped across multiple sessions without STATUS.md updates. The board went 12 entries stale — this
  reconciliation (2026-08-08) addresses it. Mitigation: STATUS.md update should be part of closeout
  discipline, not deferred to a separate reconciliation session. The AGENTS.md close-out rule already
  says "update README + PROJECTS_INDEX in the same session as the behavior change" — STATUS.md
  deserves the same treatment.
