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
| s4a Implement+render+spec | A (`68ef5ab8`) | wave-implementer | ✅ done (self-reported) | `wave_s4a/agent_a_s4_handoff.md` | commits `f46da72` (code+records) + `38bf09c` (handoff). Step-0 audio guard PASSED: F#m r=+0.367 vs Dm r=+0.039; `estimate_key(raw)` F#m r=+0.797. Riff: 13 notes, cell t0=5.39s, transpose −4, snapped=0; chords Dm7–Bbmaj7 ×4 (native F#m7–Dmaj7). Self-reported gates: O1′ 0 (5/5, −16 LUFS, TP≤−1), O2 0 (39 tests), O3′ 0 (5×200, :8777 started), O4 0 (87 tests), O5 0 (coverage .969, 2.41 n/s, leap 10st). NOT verified by orchestrator — s4b re-runs. |
| s4b Verify (read-only) | B (`c0fc46b5`) | wave-implementer (read-only constraints; wave-explorer cannot write handoffs) | ✅ done — **all PASS, independently reproduced** | `wave_s4b/agent_b_s4_verify_handoff.md` | commit `f46da72` verified clean (9 files, no WAVs, no bed_lanes/arrange/master); O1′ 0 (5/5, −16.00 LUFS, TP −3.6…−8.8), O2 0 (39), O3′ 0 (5/5 http200 — server was down, started per spec, left running), O4 0 (87), O5 0 (6/6). Independent recompute: coverage .969, 2.413 n/s, leap 10 — all **exact** matches; Dm pcs {0,2,4,5,7,9}⊆scale; dm+4==native note-for-note; raw pc histogram 100% weight in F# nat. minor, Krumhansl F#m r=+0.7965 vs Dm r=−0.0012. No mismatches >1% anywhere. |
| GATE ear test | user | — | ✅ **accepted** ("it's good") — follow-up needed | http://127.0.0.1:8777/flip_sample/ | The user wants the record's "wailing" sound added. Suno **rejected** the raw `s4_05_chop_REF.wav` upload, so the follow-up is GATE S5: the wail re-performed from its pitch line, with no source audio. See `orchestration_ledger_ogcm_s5_20260930.md`. |

## Deviations from the plan's literal text (documented, none affect scope)

- `prompts_s4/` outdir used for generated prompts, preserving the untracked megaplan `prompts_index.md` / `subagent_dispatch.json` in `prompts/`.
- `"subagent_profile": "wave-implementer"` added to agent B — native dispatch requires a write-capable profile to emit the handoff file; the READ-ONLY constraint text is unchanged.
- :8777 audition server was down at orchestration start (curl → 000); TASK_S4A instructs the implementer to start it for O3′.

## Invariants each wave

- Python only `.venv\Scripts\python.exe` (3.11); absolute paths; Cwd = project root.
- No edits to `bed_lanes.py`, `arrange.py`, `master.py`; no new dependencies; deterministic renders.
- Foreign-lane dirty files never staged (MAirina_Tucc/, lyrics_*, Genious_*, scratch_*, ORCHESTRATION/lyrics_sources); separate `git add` / `git commit`; no WAVs committed.
- Every claim quotes command + exit code + key output.
