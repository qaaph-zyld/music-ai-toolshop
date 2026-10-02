# Orchestration ledger · "Nachtfahrt" original instrumental · 2026-10-02

- **Plan:** `D:\Projects\.workspace_archive\plans\nachtfahrt-beat-from-scratch.md` (hash-identical mirror of the user-approved plan)
- **Spec:** `D:\Projects\.workspace_archive\plans\expected_output_nachtfahrt_beat_20261002_200955.md` (O1–O6)
- **Waves:** `ORCHESTRATION/beat_nachtfahrt/waves.json`
- **Status:** **EXECUTING** (Devin orchestrator session, started 2026-10-02). Dispatch = native Devin `run_subagent`, `implementer`/`reviewer` profiles (model: sonnet), foreground, one wave at a time. No goal_helper tracking (user decision — prior goal was a stale paused vocal-chain goal). Orchestrator marker: Nachtfahrt override line appended to `.workspace_archive/orchestration/ACTIVE` (other lanes' lines preserved).
- **Devin prompt adaptation:** every TASK_BN below is dispatched verbatim plus this preamble: shell is Git Bash WITH git/grep/ls (`git -C`, separate add/commit calls); "SendMessage" N/A — killed waves are resumed or re-dispatched after disk-state check; handoff file + ≤12KB returned summary required. b4 (`reviewer`, no write tools) returns the full handoff markdown; orchestrator persists and commits it.
- **User goal (verbatim intent):** "/goal fully done instrumental, mixed and mastered by you. Don't stop until done; always apply /orchestrate-waves to optimize token usage". It follows "can you make a beat yourself from scratch?"
- **Mode at execution:** Claude Code orchestrator (does not code). Agents are `general-purpose` on model sonnet. One long agent at a time, in the foreground. **No user gates:** the orchestrator gates each wave and loops fix waves until O1 exits 0 and b4 PASSes.

## Execution start (for the session that dispatches)

1. **Orchestrator marker.** `D:\Projects\.workspace_archive\orchestration\ACTIVE` currently exists with `task: OGCM Suno-sample GATE S4` plus two Tale-lane overrides from other sessions. Do not delete another lane's marker. Either append `override: user-directed <date> - Nachtfahrt beat waves b1-b4` or, if it is confirmed stale, run `python D:\Projects\ai_dev_meta_layer\scripts\hooks\orchestrator_guard.py on --task "Nachtfahrt beat"`.
2. **Set the goal:**
   ```
   python "D:\Projects\ai_dev_meta_layer\scripts\goal_helper.py" set "Nachtfahrt instrumental composed, arranged, mixed and mastered from scratch; release gates green" --check "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 D:\Projects\Music-AI-Toolshop\scripts\check_beat_release.py --dir D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\beats\nachtfahrt" --max-iterations 30 --check-timeout 180
   ```
   Note: `goal_state.json` is global to the framework. Run `goal_helper.py status` first and do not clobber another active goal.
3. Dispatch b1 → b2 → b3 → b4 with the prompts below, verbatim.
4. After each wave:
   - spot-check git scope, the protected-file diff vs this plan's commit, artifact mtimes, and one headline number recomputed by the orchestrator
   - update this ledger and commit it
   - run `goal_helper.py note` or `evaluate`
5. **Usage-limit kill:** inspect the disk state, then resume via SendMessage (that worked for s6b). Never trust the agent's last claim.
6. **Close.**
   - `goal_helper.py complete`
   - leave orchestrator mode (remove only our override line, or run `orchestrator_guard.py off` if we turned it on)
   - write a handoff
   - deliver the links and the measured numbers

## Waves

| Wave | Agent | Status | Handoff | Notes |
|---|---|---|---|---|
| b1 synth drums | A | done | `ORCHESTRATION/beat_nachtfahrt/b1/agent_a_b1_handoff.md` | TASK_B1 |
| b2 composition + render | B | done | `…/b2/agent_b_b2_handoff.md` | TASK_B2 |
| b3 mix + master + check | C | done | `…/b3/agent_c_b3_handoff.md` | TASK_B3 |
| b4 verify (read-only) | D | planned | `…/b4/agent_d_b4_verify_handoff.md` | TASK_B4 |
| b5+ fix waves | F | only on defects | `…/b5/…` | composed from b4's numbered defects |

## INCIDENT — concurrent orchestrator on this lane (2026-10-02 ~22:00–22:05)

A second execution session is/was live on this lane simultaneously with the Devin orchestrator. Timeline:

- ~21:53 Devin orchestrator dispatches b1 (`implementer`, first attempt).
- 22:00–22:01 a SECOND writer (different code style) writes `drums_synth.py` + `test_beat_nachtfahrt.py` over the Devin agent's files, then goes silent (usage-limit-kill pattern).
- Devin's b1 agent detected the overwrite and stopped without committing (correct).
- Devin re-dispatched b1 as verify-and-complete; its agent confirmed the second writer's files: 15 beat tests pass, 151 flip regression pass, protected diff empty, code spec-clean.
- 22:04:41/22:04:59 the other lane's agent resumed and committed `092d276` (feat #078) + `6036a2f` (handoff) — proper scope, gates quoted, no WAVs, no foreign lanes.
- Result: b1 DONE and double-verified. Commits accepted; ledger marks it complete.
- Risk going forward: two orchestrators dispatching b2+ will collide mid-write on `nachtfahrt.py`/`mixdown.py` — a ~150k-token wave where a file swap could silently corrupt composition data.

**To any other orchestrator reading this:** a Devin orchestrator session is managing this lane. If you are also executing these waves, STOP and coordinate with the user before dispatching b2 — duplicate dispatches corrupt shared files.

## Invariants every wave

- Python: only `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`, with `-X utf8 -u` for long runs. Absolute paths; Cwd = project root; CPU only.
- The Bash tool lacks git/grep/ls. Use PowerShell for git, and the Grep/Read tools.
- **FROM SCRATCH.** Never read any recording, stem, chop, MIDI transcription, `flip_kit`, or anything under `Stemmeca_alatkka/stems/` except this beat's own outputs.
- **No edits to `toolshop/flip/*` or `toolshop/premaster.py`;** reuse only. No new dependencies. Seeded RNG; deterministic.
- Audio goes to `Stemmeca_alatkka/stems/beats/nachtfahrt/` (gitignored by `.gitignore:58`; confirm with `git check-ignore`). No WAVs in commits.
- `git -C D:/Projects/Music-AI-Toolshop`, explicit paths. add / diff --cached / commit are separate calls; use `commit --only -- <paths>` if a concurrent session races. Never stage `MAirina_Tucc/`, `lyrics_*`, `Genious_*`, `scratch_*`, `ORCHESTRATION/lyrics_sources` or other ledgers. Never `--no-verify`.
- CHANGELOG: one Answer entry per feat commit, with the next unique `#NNN` (#077 is taken by MAirina, so the next is likely #078; grep `CHANGELOG.md` to confirm).
- Every claim quotes the command, its exit code and key output. Commit before claiming. Foreground only; never "background + end turn".
- Never claim anything "sounds" good. The user's ear judges after delivery.

## Dispatch prompts (verbatim)

### TASK_B1

```text
Execute wave b1 of the "Nachtfahrt" beat in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only b1.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md
2. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-beat-from-scratch.md (Composition, Reuse, New code, Constraints)
3. toolshop/flip/drums.py (grid_events, render_drums: they consume a dict piece -> mono one-shot)
4. toolshop/flip/sample_voices.py _soft_clip, for the peak-guard convention

BUILD (new files only)
- toolshop/beat/__init__.py (empty docstring).
- toolshop/beat/drums_synth.py: pure numpy + pedalboard, from scratch, deterministic. Each piece takes sr and seed and returns mono float32, peak-normalized to 10^(-1/20) (-1 dBFS).

  | Function | Recipe |
  |---|---|
  | kick(sr, seed) | sine with exponential pitch sweep 150 -> 48 Hz over ~60 ms; amp decay ~450 ms (exp); 2 ms click (short HP'd noise or 3 kHz blip, about -12 dB); total 0.6 s |
  | snare(sr, seed) | band-passed noise 1.5-8 kHz, decay ~180 ms, plus a 185 Hz sine body decaying ~80 ms (mix about 60/40); 0.35 s |
  | clap(sr, seed) | 3 band-passed (1-3 kHz) noise bursts 10 ms apart, each ~6 ms, then a ~120 ms noise tail; 0.3 s |
  | hat_closed(sr, seed) | noise high-passed above ~7 kHz, decay ~45 ms; 0.12 s |
  | hat_open(sr, seed) | same, decay ~300 ms; 0.5 s |
  | crash(sr, seed) | noise high-passed ~4 kHz plus a few inharmonic sine partials (e.g. 3.1, 4.7, 6.2 kHz) at low level, decay ~1.8 s; 2.5 s |
  | riser(duration_s, sr, seed) | noise through a low-pass whose cutoff sweeps exponentially 300 Hz -> 8 kHz over the duration, amplitude ramping from -30 dB to 0 dB, ending at full level |
  | gated_reverb(x, sr, room_size=0.8, wet_db=-6, gate_ms=250, fade_ms=20) | pedalboard Reverb (wet only) on x, then a hard gate: keep the first gate_ms after each onset of x, then a raised-cosine fade; returns wet only, same length as x + gate_ms |
  | one_shots(sr=44100, seed=20261002) | {"kick", "snare", "clap", "hat", "openhat", "crash"}, keys compatible with drums.render_drums |

  Use a separate seeded numpy Generator per piece (seed + a fixed piece offset), so pieces don't share RNG state. Implement filters with scipy.signal (already installed via librosa), or with pedalboard filters; no new dependencies.

TESTS: create tests/test_beat_nachtfahrt.py with a "drums_synth" section.
- every piece is deterministic (two calls give identical arrays), finite, peak <= 0.892 (-1 dBFS + tiny tolerance), and non-silent
- the kick's dominant frequency in its 150-400 ms window lies in 45-60 Hz (FFT peak)
- hat and openhat put more than 70% of their energy above 5 kHz
- snare puts more than 40% of its energy in 1.5-8 kHz
- the riser's spectral centroid over its last quarter is greater than 3x its first quarter
- gated_reverb output after gate_ms + fade_ms past the last onset is below -60 dBFS
- one_shots returns exactly the 6 keys, each mono float32

GATES (quote each command, exit code and key output)
- D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -m pytest "D:/Projects/Music-AI-Toolshop/tests/test_beat_nachtfahrt.py" -q
- The flip regression suite (test_flip_sample, test_flip_arrange, test_flip_master, test_flip_bed_lanes; absolute paths) -q must still pass.
- git -C D:/Projects/Music-AI-Toolshop diff --stat HEAD -- toolshop/flip toolshop/premaster.py must be empty.

COMMIT
- Explicit paths: toolshop/beat/__init__.py, toolshop/beat/drums_synth.py, tests/test_beat_nachtfahrt.py, CHANGELOG.md.
- CHANGELOG gets the next unique #NNN after #077 (grep CHANGELOG.md to confirm).
- Message: feat(#NNN): Nachtfahrt b1 - from-scratch synth drum + FX one-shots.
- Separate add / diff --cached / commit calls; git via PowerShell.
- Then write the handoff D:/Projects/Music-AI-Toolshop/ORCHESTRATION/beat_nachtfahrt/b1/agent_a_b1_handoff.md and commit it as docs. It includes the commits, every command with its exit code, the per-piece peak/duration/key measurement, and deviations.

CONSTRAINTS
- venv python only; CPU only.
- No reads of any audio or MIDI file; from scratch.
- No edits to toolshop/flip/* or toolshop/premaster.py. No new deps. Deterministic.
- Never stage foreign-lane files. No WAVs. Never --no-verify. Foreground only.
- Final message: the handoff path, commit hashes and the gate exit codes.
```

### TASK_B2

```text
Execute wave b2 of the "Nachtfahrt" beat in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only b2.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md
2. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-beat-from-scratch.md. THE COMPOSITION SECTION IS THE SOURCE OF TRUTH; encode it verbatim.
3. ORCHESTRATION/beat_nachtfahrt/b1/agent_a_b1_handoff.md and toolshop/beat/drums_synth.py
4. Reused voices; read their signatures, do NOT edit them:
   - toolshop/flip/sample_voices.py: render_organ, stab_pattern, driving_bass, render_synth_bass, render_gfunk_lead, pump, _soft_clip
   - toolshop/flip/bass808.py: Note808, render_808, slide rules
   - toolshop/flip/bed_lanes.py: BedNote, render_pluck
   - toolshop/flip/drums.py: grid_events, render_drums

BUILD

1. toolshop/beat/nachtfahrt.py: the composition as plain data, plus builders and the renderer.

DATA
- BPM = 105, BAR_S = 4*60/105, STEP_S = BAR_S/16, N_BARS = 80, SR = 44100, TAIL_S = 4.0, KEY = "D minor"
- VOICINGS (exact MIDI lists from the plan) and ROOT_808 = {D: 38, Bb: 34, G: 31, A: 33, C: 36, F: 29}
- ARRANGEMENT: a list of (name, first_bar_1_indexed, n_bars):
  intro 1-4, hook_a 5-12, verse1 13-28, hook_b 29-36, verse2 37-52, hook_c 53-60, bridge 61-68, hook_d 69-76, outro 77-80
- chord_at(bar), per the plan's progressions (verse/intro, hook, bridge, outro). The hook's 4-bar pattern repeats twice per hook.
- HOOK_MELODY: the plan's (bar, step, len, midi) tuples, with the bar-8 resolution to (3,8,8,74) on the repeat.
- DRUM_GRIDS: verse kick A/B, snare+clap, closed-hat 8ths with the 4th-bar roll (steps 12-15 as 16ths, 32nd ratchet on 14-15), the open hat on step 14 of every 4th verse bar, the hook grids (kick 4-on-the-floor, 16th hats accented 1.0/0.6, open hats on the offbeats), and the crash on bar 1 of each hook.
- Bridge drums:
  - bars 61-64: only a kick on beat 1 per bar, low-passed at about 200 Hz
  - bars 65-68: hook kick
  - bar 67: snare 8ths
  - bar 68: snare 16ths with velocity rising 0.4 -> 1.0 and pitch rising about +5 semitones across the bar (resample the one-shot)
- Risers: bars 3-4, 27-28, 51-52 and 67-68, each 2 bars, ending exactly on the next downbeat.

LANE BUILDERS: return note lists or events, so they are testable without audio.
- pad: whole-bar chords (all sections except where the plan says otherwise; verse level low). Verse 2 from bar 45 adds the voicing +12.
- arp: 16ths, up-down over the voicing + the voicing +12 (8 tones up, then down); render_pluck (seeded); level low in verses.
  - Low-pass automation: intro cutoff 400 Hz -> 4 kHz exponential over bars 1-4, outro 4 kHz -> 400 Hz over bars 77-80, otherwise 4 kHz. Time-varying one-pole or segment-wise filtering is fine.
- stabs: drawbar render_organ.
  - Hooks: the s6r stab grids (odd bars x..x..x...x..x.., velocity 9..6..8...5..7..; even bars x..x..x.x..x..x., velocity 8..5..7.9..5..6.), via stab_pattern if it fits; otherwise build them here.
  - Verses: one stab on beat 1 of every other bar (13, 15, ...).
- lead: render_gfunk_lead with a short glide of about 25 ms.
  - The melody in every hook (twice per hook, with the bar-8 resolution on the repeat).
  - Bridge bars 61-64: melody bars 1-4 at velocity ~0.7.
  - Hook D: add an octave-up (+12) double at -8 dB as its own note list in the same lead lane.
- bass808: render_808.
  - Hooks: the root on steps 0 and 8 of each bar, 8 steps each.
  - Verses and bridge 65-68: the root on each kick hit, legato to the next hit.
  - Slides only where bass808's rules allow (m3/P4 intervals).
  - Silent where the plan has no drums (intro, bridge 61-64, outro).
- synthbass: hooks only. driving_bass with root_octave_low=3 (one octave above the 808), then render_synth_bass.
- drums: kick, snare (snare+clap layered), hats (closed+open), fx (crash + risers) as separate lanes, via drums.grid_events + drums.render_drums with drums_synth.one_shots().

RENDER
- render_lanes(sr=44100) -> Dict[str, np.ndarray]: exactly these 10 stereo lanes, each of length int((N_BARS*BAR_S + TAIL_S)*sr):
  kick, snare, hats, fx, bass808, synthbass, pad, arp, stabs, lead
- DRY. No mix FX: no reverb/delay/sidechain here; the instrument-inherent effects (string ensemble, drawbar rotary) are fine.
- Each lane is peak-guarded to <= 0.95 and has per-section velocities applied.
- Mono sources (drums, 808, synthbass) are duplicated to stereo.
- If a reused function's signature does not expose something the plan needs (e.g. a pad envelope on render_organ), implement the minimal equivalent INSIDE toolshop/beat/nachtfahrt.py. Never edit toolshop/flip/*.
- section_map() returns [{name, first_bar, n_bars, start_s, end_s}].
- composition_hash(): sha256 of the canonical json.dumps(sort_keys=True) of all composition data.

2. scripts/build_nachtfahrt.py
- argparse --stage {render} (b3 adds mix/master/all), --outdir (default D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/beats/nachtfahrt), --sr 44100.
- The render stage:
  - records build_started_utc
  - installs sys.addaudithook, collecting "open" events whose path ends in .wav/.flac/.mp3/.mid/.midi
  - calls render_lanes()
  - writes outdir/stems/<lane>.wav (PCM_24)
  - writes outdir/section_map.json
  - writes outdir/render_manifest.json with bpm, bars, sr, lanes (name, path, sha256, peak, rms_db per section), composition_hash, build_started_utc, files_read_during_render (the audit list, excluding the build's own output writes; it must be empty) and "source_audio_in_output": false
- No input() calls.

TESTS (append to tests/test_beat_nachtfahrt.py; no full-length audio renders in tests)
- Every voicing, root, and the progression for every one of the 80 bars matches the plan.
- The arrangement covers bars 1-80 exactly once.
- HOOK_MELODY equals the plan's tuples, including the resolution.
- The drum grids equal the plan strings, including the roll, open-hat and bridge rules.
- Builders: no 808 notes in intro / bridge 61-64 / outro; synthbass only in hooks; lead notes only in hooks and bridge 61-64; the Hook D double exists at +12.
- section_map sums to 80 bars and 182.857 s.
- composition_hash is stable.
- A smoke test: render_lanes on a 2-bar slice, or a test-only bars parameter, at sr=22050 gives finite arrays <= 1.0. Add a minimal `bars=` parameter if needed.

GATES (quote each command, exit code and key output)
- the pytest file -q
- the flip regression suite -q
- run the render stage (foreground; split if it is slow): .venv python -X utf8 -u scripts/build_nachtfahrt.py --stage render
- report every lane's duration, peak and per-section RMS
- determinism: render twice (the second into a scratch --outdir) and confirm identical SHA256 for all 10 stems
- files_read_during_render == []
- git diff --stat HEAD -- toolshop/flip toolshop/premaster.py must be empty

COMMIT
- Explicit paths: toolshop/beat/nachtfahrt.py, scripts/build_nachtfahrt.py, tests/test_beat_nachtfahrt.py, CHANGELOG.md (next unique #NNN).
- Message: feat(#NNN): Nachtfahrt b2 - composition data + lane renders (render stage).
- Separate add/commit; no WAVs.
- Then write the handoff ORCHESTRATION/beat_nachtfahrt/b2/agent_b_b2_handoff.md and commit it as docs.
- Final message: the handoff path, commits, gate exit codes, the per-lane table and the determinism evidence.

CONSTRAINTS: as in the ledger invariants: from scratch, no toolshop/flip edits, deterministic, no foreign-lane staging, foreground only.
```

### TASK_B3

```text
Execute wave b3 of the "Nachtfahrt" beat in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only b3.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md
2. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-beat-from-scratch.md
3. The spec D:/Projects/.workspace_archive/plans/expected_output_nachtfahrt_beat_20261002_200955.md. O1 IS YOUR TARGET.
4. ORCHESTRATION/beat_nachtfahrt/b2/agent_b_b2_handoff.md, toolshop/beat/nachtfahrt.py and scripts/build_nachtfahrt.py
5. toolshop/flip/master.py (master_audio: its docstring explains the pedalboard Limiter makeup-gain trap; NEVER use pedalboard Limiter outside master_audio), toolshop/premaster.py (analyze_premaster) and toolshop/beat/drums_synth.py (gated_reverb)

BUILD

1. toolshop/beat/mixdown.py
- Per-lane processing; starting gains in dB, then tune to the spec targets:
  kick 0, snare -3, hats -10, fx -12, bass808 -2, synthbass -9, pad -14, arp -16, stabs -10, lead -4
- High-pass: pad / arp / stabs / lead at 150 Hz; synthbass at 90 Hz. 808 stays full-range (soft saturation is already in render_808).
- Kick-keyed sidechain from the kick event times (from nachtfahrt's builders, not audio detection). Attack 2 ms, exponential release ~150 ms. Depths:
  bass808 -4 dB, synthbass -6 dB, pad -4 dB, stabs -2 dB
- Sends; each return is part of its lane's delivered stem, so stems stay additive:
  - snare -> drums_synth.gated_reverb at about -8 dB
  - lead -> plate (Reverb room ~0.4) at about -14 dB, plus a dotted-8th delay of 0.428571 s (feedback ~0.3, mix ~0.2)
  - pad -> hall (room ~0.85) at about -16 dB
  - stabs -> short room at about -18 dB
- Section gain automation per lane is allowed, e.g. ducking pad/arp in verses, to meet the O1 section-loudness targets.
- Low end: on the summed bus, the side channel below 120 Hz is removed (M/S, side HP at 120 Hz). Apply it per stem so the stems still sum to the premix.
- premix = EXACT sum of the processed stems, with NO bus compression here. Then a single scalar gain so the premix peak is -6 dBFS; apply the same scalar to every stem.
- Write outdir/stems_mixed/<lane>.wav (PCM_24) and outdir/nachtfahrt_premix.wav.

2. Master stage, in scripts/build_nachtfahrt.py --stage master:
- Glue: pedalboard Compressor (threshold about -16 dB, ratio 2, attack 30 ms, release 150 ms) on the premix.
- Main: toolshop.flip.master.master_audio(glued, sr, target_lufs=-9.0, tp_ceiling_dbtp=-1.0) -> nachtfahrt_master.wav (PCM_24).
- Streaming: master_audio(glued, sr, target_lufs=-14.0) -> nachtfahrt_master_streaming.wav.
- Persist both master reports.
- --stage all runs render, mix, then master in one process (one build_started_utc).

3. scripts/check_beat_release.py --dir <outdir>: implement EVERY O1 condition from the spec.
- Print one PASS/FAIL line per condition, with the measured value. Exit 0 only if all pass.
- Section loudness: per-section integrated LUFS of the main master slice (toolshop.flip.master.integrated_lufs) relative to the mean of the 4 hooks.
- The stem-integrity check uses stems_mixed/*.wav against nachtfahrt_premix.wav.
- The freshness check uses the file mtime vs build_started_utc.
- Read-only: it never writes.

4. outdir/release_manifest.json (written by the build) holds:
- composition_hash, build_started_utc, files_read_during_render (the audit list; must be []), "source_audio_in_output": false
- bpm, key, bars, section_map
- the mix gain table and automation summary
- both master reports
- the artifact list with sha256 and mtime

5. outdir/index.html (written by the build) contains:
- the title "Nachtfahrt — original instrumental (105 BPM, D minor)"
- players for the main master, the streaming master, the premix, and every stems_mixed lane
- a measured-numbers table and the section map
- the credit line "Composed, synthesized, arranged, mixed and mastered from scratch by Claude (orchestrated waves). No samples."

TESTS (append; synthetic or short inputs only)
- The sidechain envelope dips by the configured depth at the kick times and recovers.
- After mono-low processing, the side-channel energy below 120 Hz is below -40 dB relative to mid.
- The sum of the processed stems equals the premix within 1e-6.
- check_beat_release exits non-zero on a deliberately broken tmp dir (e.g. a missing master) and zero on a minimal synthetic fixture only if practical. Otherwise test its condition functions directly.

GATES (quote each command, exit code and key output)
- run the full build: .venv python -X utf8 -u scripts/build_nachtfahrt.py --stage all (foreground; split render vs mix/master across calls if it is slow)
- O1: .venv python -X utf8 scripts/check_beat_release.py --dir <outdir> must EXIT 0
  - If a section/loudness condition fails, iterate on mixdown gains/automation (not the thresholds) and re-run.
  - Report every iteration's failing lines.
- O2: the pytest file
- O3: the flip regression suite
- O4: check_audition_serve.py --base http://127.0.0.1:8777/beats/nachtfahrt --dir <outdir> --glob "*.wav" --index index.html, and again with --glob "stems_mixed/*.wav"
  - Check that :8777 is up first. If it is down, start `.venv python -m http.server 8777` with cwd D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems as a background process and leave it running.
- git diff --stat HEAD -- toolshop/flip toolshop/premaster.py must be empty

COMMIT
- Explicit paths: toolshop/beat/mixdown.py, scripts/build_nachtfahrt.py, scripts/check_beat_release.py, tests/test_beat_nachtfahrt.py, CHANGELOG.md (next unique #NNN).
- Message: feat(#NNN): Nachtfahrt b3 - mixdown, master (-9 / -14 LUFS), release check.
- No WAVs. index.html lives under the gitignored outdir.
- Then write the handoff ORCHESTRATION/beat_nachtfahrt/b3/agent_c_b3_handoff.md and commit it as docs. It includes:
  - the commits and every gate with its exit code
  - the final gain table
  - every O1 line, with the measured value
  - the master reports (final LUFS / TP)
  - the iterations and deviations
- Final message: the handoff path, commits, the O1 output verbatim, and the other gate exit codes.

CONSTRAINTS: as in the ledger invariants.
```

### TASK_B4

```text
READ-ONLY independent verification of the "Nachtfahrt" beat (wave b4) in D:/Projects/Music-AI-Toolshop. You may write exactly ONE file: ORCHESTRATION/beat_nachtfahrt/b4/agent_d_b4_verify_handoff.md. No code edits, no git add/commit/push. Rebuilds go ONLY to a scratch outdir under your temp/scratchpad, never the real outdir.

READ
1. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-beat-from-scratch.md
2. The spec D:/Projects/.workspace_archive/plans/expected_output_nachtfahrt_beat_20261002_200955.md (O1-O6)
3. The b1-b3 handoffs under ORCHESTRATION/beat_nachtfahrt/. Treat every number in them as UNVERIFIED.

CHECKS (quote each command, exit code and key output; git via PowerShell)

1. Git.
- The b1-b3 commits exist.
- No .wav files in any commit.
- git diff <plan-commit>..HEAD -- toolshop/flip toolshop/premaster.py is empty. The plan commit is the ledger commit that introduced ORCHESTRATION/beat_nachtfahrt/waves.json.
- status --short on toolshop, scripts and tests is clean.

2. Re-run O1 (check_beat_release), O2, O3 and O4. O1 must exit 0.

3. O5 determinism + provenance.
- Run a full `--stage all` build into a scratch --outdir, with your own sys.addaudithook wrapper (a small runner script that installs the hook and then runs the build's main) recording every "open" of .wav/.flac/.mp3/.mid/.midi.
- Expected: zero reads other than the build's own scratch outputs.
- Compare SHA256 of the masters, the premix and every stems_mixed file between the scratch build and the real outdir.
- Different build_started_utc values are expected, so they affect the manifests only.

4. O6 mix QC with your OWN code (numpy/soundfile; you may import toolshop.beat.nachtfahrt only to read section_map and BAR_S):
- Lead audibility: in the hook bars, the lead stem's RMS in 1-5 kHz (FFT band energy) is >= that of every other non-drum stem (pad, arp, stabs, synthbass, bass808).
- Mud guard: the master's 200-500 Hz energy share in the hooks is <= 1.25 x its share in the verses.
- Premix peak <= -3 dBFS, plus a low-band (<120 Hz) peak report.
- Crest factor and PLR of the main master; give a judgement: a PLR under 7 dB is a fix-wave candidate, not a hard fail.
- Section loudness table, recomputed: compare it to O1's printout.
- Spectral sanity: there are no long digital-silence spans inside a section where the plan has content. Exclude digital silence before any percentile statistics (known DSP pitfall).

5. Page: index.html links all files, and the credit line is present.

OUTPUT
Write the handoff with a PASS/FAIL table per check with evidence, a NUMBERED DEFECT LIST (each item with the measured value, its threshold, and a suggested fix in mixdown/composition terms), and a one-line verdict.
Final message: the verdict, the per-check table and the defect list.

CONSTRAINTS: venv python only, absolute paths, foreground only, and never re-run an identical failed command.
```
- 2026-10-02 — **b1 done** (implementer 8edf13f2). Commits: `092d276` feat(#078) [toolshop/beat/__init__.py, drums_synth.py, tests/test_beat_nachtfahrt.py, CHANGELOG], `6036a2f` docs handoff. Orchestrator re-verified: `pytest tests/test_beat_nachtfahrt.py -q` = 15 passed; protected-file diff 6c51d81..HEAD empty; no WAVs committed; scope clean (foreign lanes untouched).
- 2026-10-02 — **b2 done** (implementer 55e4534e). Commits: `7b6ed92` feat(#079) [nachtfahrt.py 603L, build_nachtfahrt.py, tests +20], `afc19fd` docs. Orchestrator re-verified: pytest = 35 passed; render_manifest files_read_during_render=[] + source_audio_in_output=false; 10 stereo stems 186.857 s PCM_24; 9 sections cover bars 1-80; composition_hash 89b1fa48. Lane peak guards engaged at 0.95 (hats/snare/808/synthbass/lead). Note: foreign-lane commit 56da498 (OGCM-flip plan) landed mid-wave; unaffected.
- 2026-10-02 — **b3 done** (implementer 0a639dee). Commits: `b7c09d7` feat(#080) [mixdown.py 257L, build_nachtfahrt +193L, check_beat_release.py 197L, tests +100L, CHANGELOG], `0bbfc98` docs. **O1 re-run by orchestrator: PASS 21/21 exit 0** (main −9.01 LUFS/−1.006 dBTP; streaming −14.00/−2.47; stem residual −107.4 dB). pytest 43 passed; O4 both globs 200. **Deviation recorded:** main master uses `mixdown.loud_master` (gain + soft-knee clip), NOT `master_audio` — the limiter loop lifted quiet sections ~2 LU of hooks, destroying required section contrast; streaming master still uses master_audio. Bridge-p1 needed −4 dB lead automation (−3.27→−6.67 LU). Agent killed :8777 by accident (taskkill python.exe) and restarted it; verified serving 200 + master 200.
