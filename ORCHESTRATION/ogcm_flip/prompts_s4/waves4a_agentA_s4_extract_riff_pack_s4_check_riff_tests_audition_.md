FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Execute GATE S4 of the OGCM Suno-sample lane in d:/Projects/Music-AI-Toolshop. First read d:/Projects/Music-AI-Toolshop/AGENTS.md (venv-only Python, close-out discipline), then the approved plan d:/Projects/.workspace_archive/plans/ogcm-s4-recognizable-riff.md IN FULL (Context = the measured root cause; Approach steps 1-6 = your work), then the S3 spec d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_simple_recognizable_melody_20260929_220703.md (O1-O4 gates you retarget to S4).

ROOT CAUSE (measured, do not re-litigate): S3 used region_54_67_cleaned_Dm.mid, which bed_lanes.cleanup(root="D") key-snapped from F# minor (raw pc profile C#.29 F#.20 D.16 B.15 A.14 G#.03 E.02; scale_lock maps C#->D, F#->F, G#->G, B->Bb). S4 reads Stemmeca_alatkka/stems/flip_bed_lanes/midi/region_54_67_raw.mid and TRANSPOSES -4 (F#m -> Dm exactly), never snaps.

Steps:
0. git -C d:/Projects/Music-AI-Toolshop status --short and log --oneline -8. Note foreign dirty files; never touch them. Then confirm the key from AUDIO: librosa chroma_cqt on Stemmeca_alatkka/stems/instrumental.wav 54.0-67.0 s + Krumhansl correlation; expect F# minor (or its relative A major) to beat D minor. If D minor wins, STOP and report — the plan's premise is wrong.
1. sample_voices.py: add GRID_16TH_S, transpose, estimate_key, fold_octaves, extract_riff (returns (riff, cell_t0)), riff_stats — exactly as plan Approach step 1. Reuse top_line/quantize/legato/tile_motif/_snap_to_dm/derive_chords.
2. Print the extracted riff (onset, dur, midi, note name in F#m and in Dm) BEFORE rendering. Sanity check vs the plan's phrase shape (C#5 repeated -> B4 -> C#5 -> A4-G#4-F#4 descent; in Dm: A4 repeated -> G4 -> A4 -> F4-E4-D4). If it is wildly different, report it in the handoff; do not tune parameters to force a match.
3. ogcm_sample.py: --pack s4, --transpose (default -4), optional chords= on _render_s3, _s4_variants with the 5 files in the plan table (s4_01..s4_05; REF chop ref_slice_54_67.wav at --shift -4; s4_04 = all lanes +4 back to native F#m). Manifest fields per plan. Run: .venv python scripts/ogcm_sample.py --pack s4 (foreground).
4. ogcm_transcribe_segment.py: key-estimate print + >15% out-of-scale warning (plan step 3). Do not re-transcribe.
5. NEW scripts/check_riff.py (O5) per plan step 4.
6. tests/test_flip_sample.py: new tests per plan step 5 (synthetic data only).
7. flip_sample/index.html S4 section on top (key labels per plan); LEDGER.md s4 row incl. key-snap root cause; CHANGELOG next unique #NNN (grep to confirm unused); write the S4 spec d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_<YYYYMMDD_HHMMSS>.md = S3 spec with O1/O3 retargeted to audition_s4 + "s4_*.wav", O2/O4 unchanged, O5 = check_riff.py.
8. Run O1'-O5 (commands in the plan's Verification section; ensure the :8777 audition server is up for O3', start it from Stemmeca_alatkka/stems if down). Quote exit codes.
9. Commit code + index/LEDGER/CHANGELOG (explicit paths, feat(#NNN): GATE S4 ...). Handoff to ORCHESTRATION/ogcm_flip/wave_s4a/agent_a_s4_handoff.md: commit hash, per-gate exit codes, the printed riff in both keys, per-bar chord names, riff_stats, and a note that S2 regions are likely snapped too (not fixed). Do NOT claim the pack is 'recognizable' — only the user's ear decides.

Python: ONLY D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe. Absolute paths in every command. Cwd = d:/Projects/Music-AI-Toolshop." --files "toolshop/flip/sample_voices.py, scripts/ogcm_sample.py, scripts/ogcm_transcribe_segment.py, scripts/check_riff.py (new), tests/test_flip_sample.py, Stemmeca_alatkka/stems/flip_sample/ (index.html + audition_s4/), ORCHESTRATION/ogcm_flip/LEDGER.md, CHANGELOG.md, D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_<stamp>.md (new)".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Execute GATE S4 of the OGCM Suno-sample lane in d:/Projects/Music-AI-Toolshop. First read d:/Projects/Music-AI-Toolshop/AGENTS.md (venv-only Python, close-out discipline), then the approved plan d:/Projects/.workspace_archive/plans/ogcm-s4-recognizable-riff.md IN FULL (Context = the measured root cause; Approach steps 1-6 = your work), then the S3 spec d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_simple_recognizable_melody_20260929_220703.md (O1-O4 gates you retarget to S4).

ROOT CAUSE (measured, do not re-litigate): S3 used region_54_67_cleaned_Dm.mid, which bed_lanes.cleanup(root="D") key-snapped from F# minor (raw pc profile C#.29 F#.20 D.16 B.15 A.14 G#.03 E.02; scale_lock maps C#->D, F#->F, G#->G, B->Bb). S4 reads Stemmeca_alatkka/stems/flip_bed_lanes/midi/region_54_67_raw.mid and TRANSPOSES -4 (F#m -> Dm exactly), never snaps.

Steps:
0. git -C d:/Projects/Music-AI-Toolshop status --short and log --oneline -8. Note foreign dirty files; never touch them. Then confirm the key from AUDIO: librosa chroma_cqt on Stemmeca_alatkka/stems/instrumental.wav 54.0-67.0 s + Krumhansl correlation; expect F# minor (or its relative A major) to beat D minor. If D minor wins, STOP and report — the plan's premise is wrong.
1. sample_voices.py: add GRID_16TH_S, transpose, estimate_key, fold_octaves, extract_riff (returns (riff, cell_t0)), riff_stats — exactly as plan Approach step 1. Reuse top_line/quantize/legato/tile_motif/_snap_to_dm/derive_chords.
2. Print the extracted riff (onset, dur, midi, note name in F#m and in Dm) BEFORE rendering. Sanity check vs the plan's phrase shape (C#5 repeated -> B4 -> C#5 -> A4-G#4-F#4 descent; in Dm: A4 repeated -> G4 -> A4 -> F4-E4-D4). If it is wildly different, report it in the handoff; do not tune parameters to force a match.
3. ogcm_sample.py: --pack s4, --transpose (default -4), optional chords= on _render_s3, _s4_variants with the 5 files in the plan table (s4_01..s4_05; REF chop ref_slice_54_67.wav at --shift -4; s4_04 = all lanes +4 back to native F#m). Manifest fields per plan. Run: .venv python scripts/ogcm_sample.py --pack s4 (foreground).
4. ogcm_transcribe_segment.py: key-estimate print + >15% out-of-scale warning (plan step 3). Do not re-transcribe.
5. NEW scripts/check_riff.py (O5) per plan step 4.
6. tests/test_flip_sample.py: new tests per plan step 5 (synthetic data only).
7. flip_sample/index.html S4 section on top (key labels per plan); LEDGER.md s4 row incl. key-snap root cause; CHANGELOG next unique #NNN (grep to confirm unused); write the S4 spec d:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_<YYYYMMDD_HHMMSS>.md = S3 spec with O1/O3 retargeted to audition_s4 + "s4_*.wav", O2/O4 unchanged, O5 = check_riff.py.
8. Run O1'-O5 (commands in the plan's Verification section; ensure the :8777 audition server is up for O3', start it from Stemmeca_alatkka/stems if down). Quote exit codes.
9. Commit code + index/LEDGER/CHANGELOG (explicit paths, feat(#NNN): GATE S4 ...). Handoff to ORCHESTRATION/ogcm_flip/wave_s4a/agent_a_s4_handoff.md: commit hash, per-gate exit codes, the printed riff in both keys, per-bar chord names, riff_stats, and a note that S2 regions are likely snapped too (not fixed). Do NOT claim the pack is 'recognizable' — only the user's ear decides.

Python: ONLY D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe. Absolute paths in every command. Cwd = d:/Projects/Music-AI-Toolshop.
OPEN FILES: toolshop/flip/sample_voices.py, scripts/ogcm_sample.py, scripts/ogcm_transcribe_segment.py, scripts/check_riff.py (new), tests/test_flip_sample.py, Stemmeca_alatkka/stems/flip_sample/ (index.html + audition_s4/), ORCHESTRATION/ogcm_flip/LEDGER.md, CHANGELOG.md, D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s4_<stamp>.md (new)

OUTPUT: Write your handoff to: ORCHESTRATION/ogcm_flip/wave_s4a/agent_a_s4_handoff.md

CONSTRAINTS:
- Python: only D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe (3.11) — never global 3.13.
- No edits to toolshop/flip/bed_lanes.py, arrange.py, master.py; no new dependencies; deterministic renders, no model calls.
- extract_motif stays unchanged — S4 logic goes in NEW functions so --pack s3 stays reproducible and the 30 existing tests stay green.
- Foreground only; never 'background + end turn'. Split long renders across calls if needed.
- Git: git -C d:/Projects/Music-AI-Toolshop, explicit paths only, separate add and commit calls; never stage MAirina_Tucc/, lyrics_*, Genious_*, scratch_*, or other foreign-lane files. No WAVs committed.
- Every claim in the handoff quotes the command, exit code and key output. Commit before you claim.

CONTEXT BUDGET: 120k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
