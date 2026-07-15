# H1-M2 — Demucs E2E + Complete Model Cache + Model Mirror

> **For agentic workers:** One milestone only. Obey `AGENTS.md`. Prerequisite: none (independent of M1,
> but do not run while the M1 batch is executing — both are CPU-heavy).
> Parent: roadmap v2 §H1-M2 + integration map §1.3 (model mirroring policy).

**Goal:** Every preset in the registry runs end-to-end on this machine; all models cached AND mirrored
with checksums; `toolshop doctor` reports a clean model cache.

**Starting state (2026-07-14 handoff):** cache holds only `UVR-MDX-NET-Voc_FT.onnx` +
`UVR-BVE-4B_SN-44100-1.pth`. Demucs adapter never run e2e. Roformer models not downloaded.
Disk is fine (~250 GB free). Downloads total roughly 1–2 GB.

### Task 1: Test fixture
- [ ] Create `D:\MusicData\toolshop\fixtures\fixture_60s.wav`: a 60-second excerpt cut with
      `ffmpeg -ss 30 -t 60` from any track under `D:\MusicData\toolshop\` (pick one, note which).
      60 s keeps CPU runs bounded (~5–10 min per heavy preset).

### Task 2: Demucs end-to-end (first real run — downloads htdemucs)
- [ ] `.venv\Scripts\python.exe -m toolshop.cli stems "D:\MusicData\toolshop\fixtures\fixture_60s.wav" --preset 4stem`
- [ ] Verify: 4 stems (drums/bass/other/vocals) + `manifest.json`; listen-length sanity (durations match).
- [ ] Record wall-time. If the Python-API path fails, the adapter's `python -m demucs` fallback must
      kick in — verify that path rather than patching around it.

### Task 3: Populate remaining preset models
- [ ] Run once per still-missing preset on the fixture: `vocals-hq` (BS-Roformer ep_317),
      `full-vocals-hq` (karaoke Roformer), `6stem` (htdemucs_6s). Record wall-time each.
- [ ] Update the benchmark table (`benchmarks/` + README) with fixture-relative numbers and a
      note extrapolating to a ~3.5-min track.

### Task 4: Model mirror (integration map policy #1.3 — TDD)
- [ ] New `toolshop/model_mirror.py`: `mirror_models(cache_dir, mirror_dir)` copies every registry-known
      checkpoint to `D:\MusicData\toolshop\models\mirror\` and writes/updates `mirror_manifest.json`
      (filename, sha256, size, source model id, mirrored_at). Idempotent; never overwrites a checksum-matching file.
- [ ] Wire: `toolshop stems --mirror-models` (or `toolshop models mirror`) subcommand.
- [ ] Doctor: new check — every registry model present in cache has a checksum-verified mirror entry;
      WARN (not FAIL) when mirror is missing. Tests with tmp dirs + fake files first.
- [ ] Run the mirror for real; then `.venv\Scripts\python.exe -m toolshop.doctor` → model cache section clean.

### Task 5: Docs + handoff
- [ ] README stems section: note mirror location + rationale (2026-06 upstream model-source deletion incident).
- [ ] CHANGELOG Answer-format entry. Handoff per template. `session_end.py`.

## Verification checklist
- [ ] All presets in `stem_models.py` executed successfully on the fixture (times recorded)
- [ ] `doctor` model-cache section: 0 warnings; mirror manifest checksums verified
- [ ] Mirror module TDD-covered; pytest green
- [ ] Benchmarks + README + CHANGELOG updated; handoff written

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "H1-M2: Demucs e2e + model cache + mirror" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m2-model-cache-demucs-e2e.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-15-h1m2-model-cache-demucs-e2e.md
exactly as written. Scope = this milestone ONLY. Use the .venv python. TDD for the mirror module. Do not run
while an H1-M1 batch is still processing (CPU contention).

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m2.md
with: per-task [x] + evidence, preset wall-times table, doctor output (model section quoted), pytest tail,
files changed, deviations, blockers. This gets reviewed before the next milestone is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m2-model-cache-demucs-e2e.md
```
