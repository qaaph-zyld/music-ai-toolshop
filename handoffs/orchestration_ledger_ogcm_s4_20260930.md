# Orchestration ledger · OGCM GATE S4 (recognizable riff) · 2026-09-30

- **Plan:** `D:\Projects\.workspace_archive\plans\ogcm-s4-recognizable-riff.md` (verbatim mirror of the user-approved plan; root cause measured, not to be re-litigated)
- **Waves:** `ORCHESTRATION/ogcm_flip/waves_s4.json` — separate file; `waves.json` and untracked `waves_megaplan.json` untouched
- **Mode:** native subagents, one at a time, in the foreground. The orchestrator does not code.
- **Spec chain:** S3 spec `expected_output_ogcm_suno_sample_simple_recognizable_melody_20260929_220703.md` → S4 spec `expected_output_ogcm_suno_sample_s4_<stamp>.md` (written by wave s4a)

## Root cause being fixed (from the approved plan)

S3's motif came from `region_54_67_cleaned_Dm.mid` — `bed_lanes.cleanup(root="D")` had key-snapped F#-minor material to D minor (raw pc profile C# .29 / F# .20 / D .16 / B .15 / A .14 / G# .03 / E .02; scale_lock maps C#→D, F#→F, G#→G, B→Bb). S4 reads `region_54_67_raw.mid` and **transposes −4** (F#m→Dm), never snaps. `extract_motif` stays unchanged; all S4 logic is new functions.

## Waves

| Wave | Agent | Profile | Status | Handoff | Notes |
|---|---|---|---|---|---|
| s4a Implement+render+spec | A | wave-implementer | dispatched | `wave_s4a/agent_a_s4_handoff.md` | Step 0 = audio chroma key check on instrumental.wav 54–67 s; if D minor wins the agent STOPS — plan premise falsified. |
| s4b Verify (read-only) | B | wave-implementer (read-only constraints; wave-explorer cannot write handoffs) | pending s4a | `wave_s4b/agent_b_s4_verify_handoff.md` | Re-runs O1′–O5 + independent spot-check; orchestrator reports verifier's numbers, not the implementer's. |
| GATE ear test | user | — | pending | http://127.0.0.1:8777/flip_sample/ | s4_01 / s4_04 vs `instrumental.wav` 54–67 s. Only the user's ear decides "recognizable". |

## Deviations from the plan's literal text (documented, none affect scope)

- `prompts_s4/` outdir used for generated prompts, preserving the untracked megaplan `prompts_index.md` / `subagent_dispatch.json` in `prompts/`.
- `"subagent_profile": "wave-implementer"` added to agent B — native dispatch requires a write-capable profile to emit the handoff file; the READ-ONLY constraint text is unchanged.
- :8777 audition server was down at orchestration start (curl → 000); TASK_S4A instructs the implementer to start it for O3′.

## Invariants each wave

- Python only `.venv\Scripts\python.exe` (3.11); absolute paths; Cwd = project root.
- No edits to `bed_lanes.py`, `arrange.py`, `master.py`; no new dependencies; deterministic renders.
- Foreign-lane dirty files never staged (MAirina_Tucc/, lyrics_*, Genious_*, scratch_*, ORCHESTRATION/lyrics_sources); separate `git add` / `git commit`; no WAVs committed.
- Every claim quotes command + exit code + key output.
