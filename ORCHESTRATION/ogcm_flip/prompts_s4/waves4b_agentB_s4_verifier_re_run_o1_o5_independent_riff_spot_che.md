FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "READ-ONLY verification of GATE S4 in d:/Projects/Music-AI-Toolshop. Read the approved plan d:/Projects/.workspace_archive/plans/ogcm-s4-recognizable-riff.md (Verification section) and the wave s4a handoff ORCHESTRATION/ogcm_flip/wave_s4a/agent_a_s4_handoff.md. Treat every number in that handoff as unverified.

1. git -C d:/Projects/Music-AI-Toolshop log --oneline -3 and status --short: the handoff's commit hash exists; sample_voices.py, ogcm_sample.py, check_riff.py, test_flip_sample.py, ogcm_transcribe_segment.py are NOT dirty; no WAVs committed; bed_lanes.py/arrange.py/master.py unchanged in that commit (git show --stat).
2. Re-run O1', O2, O3', O4, O5 from the S4 spec file under d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_*.md. Quote each exit code + key output line.
3. Independent spot-check with your own code (pretty_midi + numpy, no toolshop import needed): from audition_s4/manifest.json riff notes recompute coverage, notes/s, max leap; confirm every Dm-riff pitch class is in {2,4,5,7,9,10,0}; confirm Dm riff +4 == native riff note-for-note; recompute the duration-weighted pc histogram of Stemmeca_alatkka/stems/flip_bed_lanes/midi/region_54_67_raw.mid and confirm it is F#-minor-dominated. Compare to the manifest; flag any mismatch > 1%.
4. Confirm the 5 files exist, s4_05_chop_REF is labelled as -4 / D minor on index.html, s4_04 labelled native F# minor.
Write ORCHESTRATION/ogcm_flip/wave_s4b/agent_b_s4_verify_handoff.md: PASS/FAIL per check with evidence. No edits anywhere else.

Python: ONLY D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe. Absolute paths. Cwd = d:/Projects/Music-AI-Toolshop." --files "read-only: Stemmeca_alatkka/stems/flip_sample/audition_s4/, tests/, scripts/, git log/status".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: READ-ONLY verification of GATE S4 in d:/Projects/Music-AI-Toolshop. Read the approved plan d:/Projects/.workspace_archive/plans/ogcm-s4-recognizable-riff.md (Verification section) and the wave s4a handoff ORCHESTRATION/ogcm_flip/wave_s4a/agent_a_s4_handoff.md. Treat every number in that handoff as unverified.

1. git -C d:/Projects/Music-AI-Toolshop log --oneline -3 and status --short: the handoff's commit hash exists; sample_voices.py, ogcm_sample.py, check_riff.py, test_flip_sample.py, ogcm_transcribe_segment.py are NOT dirty; no WAVs committed; bed_lanes.py/arrange.py/master.py unchanged in that commit (git show --stat).
2. Re-run O1', O2, O3', O4, O5 from the S4 spec file under d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_*.md. Quote each exit code + key output line.
3. Independent spot-check with your own code (pretty_midi + numpy, no toolshop import needed): from audition_s4/manifest.json riff notes recompute coverage, notes/s, max leap; confirm every Dm-riff pitch class is in {2,4,5,7,9,10,0}; confirm Dm riff +4 == native riff note-for-note; recompute the duration-weighted pc histogram of Stemmeca_alatkka/stems/flip_bed_lanes/midi/region_54_67_raw.mid and confirm it is F#-minor-dominated. Compare to the manifest; flag any mismatch > 1%.
4. Confirm the 5 files exist, s4_05_chop_REF is labelled as -4 / D minor on index.html, s4_04 labelled native F# minor.
Write ORCHESTRATION/ogcm_flip/wave_s4b/agent_b_s4_verify_handoff.md: PASS/FAIL per check with evidence. No edits anywhere else.

Python: ONLY D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe. Absolute paths. Cwd = d:/Projects/Music-AI-Toolshop.
OPEN FILES: read-only: Stemmeca_alatkka/stems/flip_sample/audition_s4/, tests/, scripts/, git log/status

OUTPUT: Write your handoff to: ORCHESTRATION/ogcm_flip/wave_s4b/agent_b_s4_verify_handoff.md

CONSTRAINTS:
- READ-ONLY: no edits, no commits, no re-renders.
- Python: only the project .venv.
- Recompute headline numbers with your own code; do not trust wave s4a's handoff or manifest self-reports.
- Quote exit codes and key output for every check.

CONTEXT BUDGET: 60k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
