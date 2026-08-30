# S2 — M2: Model cache + mirror

**Date:** 2026-08-20 · **Author:** orchestrator · **Size:** 1 session
**Goal:** G1 (trustworthy analysis core) · first P1 milestone, per decision D5
**Why now:** `model_cache` is the **only** remaining failing `doctor` check after P0. Two of the four
audio-separator checkpoints are absent, which silently disables the `vocals-hq` and `full-vocals-hq`
presets. This is the smallest change that flips `doctor` fully green, and H1 has been blocked on it
since 2026-07-15.

**Standing context (do not re-derive):**
- Repo: `D:\Projects\Music-AI-Toolshop`, branch `master`, remote `github.com/qaaph-zyld/music-ai-toolshop`.
- Env: `.venv` Python 3.11 in repo root — ALL pytest runs inside it.
- **Verified baseline 2026-08-20: `974 passed, 2 skipped, 0 failed`.** That is the no-NEW-failures bar.
- CI is billing-locked; the gate is LOCAL pytest with pasted output.
- Close-out discipline: AGENTS.md. Task 6 IS the gate.
- Backup target is `D:\Backups\toolshop` (code default since #038). Do not reintroduce `C:`.

---

## Verified before writing this plan (2026-08-20)

Cache at `~/.cache/toolshop-models` holds **2 of 4** audio-separator models (290 MB):
`UVR-MDX-NET-Voc_FT.onnx` and `UVR-BVE-4B_SN-44100-1.pth`.

Missing, with sizes confirmed by live `HEAD` against the release host:

| File | Size | Used by |
|---|---|---|
| `model_bs_roformer_ep_317_sdr_12.9755.ckpt` | **609.7 MB** | presets `vocals-hq`, `full-vocals-hq` |
| `mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt` | **870.8 MB** | preset `full-vocals-hq` |

**Total ≈ 1.48 GB.** D: has ~132 GB free. Both resolve from
`https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/` — the same host
`audio-separator`'s own `download_checks.json` names, so the normal download path is the honest one.

**A registry defect found while scoping this** — `stem_models.py` records
`mel-band-roformer-karaoke` as `source="https://github.com/RVC-Boss/GPT-SoVITS"`, `license="MIT"`.
GPT-SoVITS is a **text-to-speech project** and is not where this model comes from. Its real origin is
TRvlvr/model_repo (aufr33/viperx community UVR models), same as the BS-RoFormer entry. The `MIT`
licence looks inherited from that wrong attribution. The project's own rule is "adapter + licence
ledger for every adoption" — a wrong provenance entry is exactly what that rule exists to catch.

---

## Tasks

### Task 1 — Correct the registry provenance before downloading anything

Do this first, so the mirror manifest records the truth rather than copying the error forward.

1. Fix `mel-band-roformer-karaoke`: `source` → the TRvlvr release URL that `download_checks.json`
   actually names.
2. **Determine the real licence.** Do not guess and do not leave `MIT` standing because it is
   already written there. If the upstream terms cannot be established, record the licence as
   `unknown — see source` rather than asserting one. An unverified licence in the ledger is worse
   than an admitted gap.
3. Same check for `bs-roformer-317` (`MIT/BSD` is vague; confirm or downgrade to `unknown`).

**Exit evidence:** the diff, plus whatever was actually read to establish each licence.

### Task 2 — Fetch the two checkpoints · **[USER DECISION — authorised 2026-08-20]**

Use `audio-separator`'s own downloader (it resolves the URL, filename and any companion config), with
`model_file_dir` pointed at the cache root. Do **not** hand-roll URL construction — the `.yaml`
companions are not at the guessable path (both 404'd on a direct `HEAD`), and the library already
knows where they live.

Fetch one model, verify, then the other. ~1.48 GB total; expect this to be the slow part.

**Exit evidence:** both files present at the expected sizes, `doctor` re-run.

### Task 3 — Mirror + checksums

The point of M2 was never just "download the files" — it was to stop depending on a third-party
release page staying up.

1. Record `sha256` for all four audio-separator models in a version-controlled manifest
   (`docs/model_manifest.json` or similar — code, not data, since it is small and must survive a
   cache wipe).
2. Add a `toolshop doctor`-adjacent verification that checks **hashes**, not just presence. Presence
   alone is what let the backup problem hide for a month; do not repeat the pattern here.
3. Mirror the model files into the backup as **Tier-2** (`--include-audio`-style opt-in, or a
   parallel `--include-models` flag). 1.48 GB of re-downloadable weights does not belong in a
   Tier-1 restore. **[USER DECISION]** if a different tier is wanted.

**Exit evidence:** the manifest, a hash-verification run, and the backup flag demonstrated.

### Task 4 — Handle the config-file orphan problem

`check_model_cache()` ignores exactly three orphan filenames (`download_checks.json`,
`mdx_model_data.json`, `vr_model_data.json`). RoFormer models ship a companion `.yaml` config, so
after Task 2 the cache will likely contain files the check reports as **orphans** — turning a green
check amber for no real reason.

Extend the ignore rule (or the registry) to account for companion configs, and add a test.

**Exit evidence:** `doctor` shows `model_cache` OK with **zero** spurious orphans.

### Task 5 — Prove the unlocked presets actually run

A green `doctor` is not the deliverable; working separation is.

Run `vocals-hq` and `full-vocals-hq` on one real track. **Record the measured minutes/track** —
governance rule 1 requires a measured CPU cost in every ML-feature handoff, and both of these are
unmeasured today (`cpu_min_per_track=None` for both entries in the registry). Write the measured
figures back into the registry.

**Exit evidence:** output stems, wall-clock per preset, and the registry diff.

### Task 6 — Fold in debt 13b (small, and it protects the gate)

`test_build_database_dedup_log` and neighbours call `build_database(root=FIXTURE_ROOT)`, and
`build_database` writes `_dedup_log.json` **back into the tracked fixture directory**. Every plain
`pytest` run therefore leaves the working tree dirty, which quietly undermines `toolshop closeout`'s
clean-tree check — the gate the whole close-out discipline rests on.

Fix: copy the fixture into `tmp_path` before building, or give `build_database` a separate output
root. Then confirm `git status` is clean immediately after a full suite run.

**Exit evidence:** a full suite run followed by a clean `git status`.

### Task 7 — CLOSE-OUT GATE (do not skip)

1. Full suite — bar: **no new failures against 974 passed / 2 skipped / 0 failed**.
2. `toolshop doctor` — **expect `Overall: OK`.** This is the session's headline; if it is not OK, say
   why plainly rather than burying it.
3. `toolshop closeout` — must exit 0.
4. CHANGELOG entry (next free number is **#041**), STATUS update, push.

**Exit evidence:** closeout block, doctor output, pytest tail, commit hashes, empty
`git log origin/master..HEAD`.

---

## Out of scope

- M3 stems CPU optimisation (HT-Demucs FT ONNX) — that is S3
- M4, M5, Dossier v2
- `ai_modules/` — D6 still deferred pending the user's review
- The repo-root one-off scripts

## Risks

| Risk | Handling |
|---|---|
| 1.48 GB download stalls or the release host is slow | Fetch one model at a time; `audio-separator` resumes. If the host is down, stop and report — do not mirror from an unvetted third party. |
| Licence cannot be established | Record `unknown — see source`. Do not assert a licence to make the ledger look complete. |
| `full-vocals-hq` turns out to be very slow on CPU | That is a finding, not a failure. Record the measured minutes/track; the >15 min rule then routes it to the overnight batch engine. |
