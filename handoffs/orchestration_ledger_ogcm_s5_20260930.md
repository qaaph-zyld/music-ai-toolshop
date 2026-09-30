# Orchestration ledger · OGCM GATE S5 (resynthesized wail) · 2026-09-30

- **Plan:** `D:\Projects\.workspace_archive\plans\ogcm-s5-wail-resynth.md` (hash-identical mirror of the user-approved plan)
- **Waves:** `ORCHESTRATION/ogcm_flip/waves_s5.json`
- **Mode:** Claude Code orchestrator (does not code). Agents are `general-purpose` on model sonnet. One long implementer at a time, in the foreground. Only the short s5r research agent runs in the background.
- **Predecessor:** S4 is ear-accepted ("it's good"). Suno **rejected** the raw `s4_05_chop_REF.wav`, so no Suno-bound file may contain source audio. See `orchestration_ledger_ogcm_s4_20260930.md`.

## Waves

| Wave | Agent | Status | Handoff | Notes |
|---|---|---|---|---|
| s5r research | R | ✅ done (report-only; committed by the orchestrator) | `wave_s5r/research_wail_report.md` | **Identity unknown** (low-med confidence). Credits name producers Doug Rasheed and Harold "Scrap" Freddie, with no instrument credit; "portamento synth lead" rests on genre convention only. A claimed Kleeer "Tonight" sample failed verification. **Recipe:** when the voice follows a tracked contour, use a glide of 15–30 ms (not 100) and add no synthetic vibrato on top. Delay 0.505 s. **pyin:** fmin 196, fmax 2093, frame 1024, hop 128 at 22.05 kHz, voiced_prob ≥ 0.5 + RMS gate, octave fixes per segment, 5–7 frame median inside segments, bridge gaps ≤ 100 ms when the step is ≤ 3 st, drop islands < 50 ms. WhoSampled, Genius and forums returned 403, so some claims rest on search snippets. |
| s5a stem audition + probe | A | ✅ done, spot-checked by the orchestrator | `wave_s5a/agent_a_s5a_handoff.md` | Commits `3458637` feat(#074) + `d74ef20` docs; no WAVs. Protected files show no diff vs `20e1774`, and the lane is clean. Self-reported gates: O2 0 (49), O4 0 (97), O5 0, O1″ 0, O3″ 0/0. S4 re-render gave identical SHA256 hashes. The `audition_s5` manifest reads `source_audio_in_output: false` and `lead_delay_s: 0.505051`, with the single file `s5_00_riff_whine.wav` (confirmed by the orchestrator). Deviations: timeline hop 512 (cost), extra CLI flags, backing_vox clip at −22.9 LUFS (peak guard). |
| G1 | user | ✅ answered 2026-10-01 | — | **Wail = `stem_guitar`** (htdemucs_6s guitar, 54–67 s). Probe `s5_00_riff_whine`: "close, still build A/B/C". **New requirement, sent mid-turn:** "a bit faster tempo, 1.15–1.20× of the guitar riff". The orchestrator set the pack to **105 BPM** (1.1785× of 89.1, the middle of the range, rounded to a whole BPM for Suno). A `--tempo-bpm` flag keeps other values one re-render away. |
| s5b resynth A/B/C | B | dispatched (foreground) | `wave_s5b/agent_b_s5b_handoff.md` | TASK_S5B recorded below. |

## Orchestrator reading of `stem_ranking.json` (read directly, not from the handoff)

`wail_score` ranks vocals (0.906) > backing_vox (0.877) > guitar (0.849). The score, however, does not weight pyin's confidence:

| stem | mean voiced_prob | median | p10–p90 | voiced_ratio | glide_share | vibrato depth |
|---|---|---|---|---|---|---|
| guitar | **0.564** | **B4 (71.0)** | 66.3–75.7 (F#4–E5) | 0.895 | 0.13 | 0.445 st |
| vocals | 0.106 | A#3 (58.2) | 53.9–60.6 | 0.786 | 0.413 | 0.828 st |
| backing_vox | 0.113 | A#3 (57.7) | 53.6–60.1 | 0.496 | 0.389 | 0.634 st |

- **Guitar** is the only stem carrying a confident, sustained, high pitched line with vibrato. It sits in the same register as the S4 riff (61–78).
- **Vocals and backing_vox** have low-confidence pitch and a speech-register median with a high glide share, which fits rap prosody. They also cannot appear in `instrumental.wav`, where the user heard the wail.
- **Hypothesis, not a finding:** the "wail" may be the timbre of the riff instrument itself (sustained notes with vibrato), not a separate line. Only the user's ear decides.
| s5c verify | C | not started | `wave_s5c/agent_c_s5c_verify_handoff.md` | G2 follows: the user's ear test, then the user's Suno upload. |

## Invariants each wave

- Python: only `.venv\Scripts\python.exe` (3.11). Absolute paths; Cwd = project root; CPU only.
- No edits to `bed_lanes.py`, `arrange.py` or `master.py`. `extract_motif` and `extract_riff` stay unchanged. No new dependencies. Renders are deterministic.
- Suno-bound `audition_s5/s5_*` files contain **no source audio**. Stem clips exist only for local identification.
- Foreign-lane files are never staged: `MAirina_Tucc/`, `lyrics_*`, `Genious_*`, `scratch_*`, `ORCHESTRATION/lyrics_sources`. `git add` and `git commit` are separate calls, and no WAVs are committed.
- Every claim quotes the command, its exit code and key output.

## Dispatch prompts (verbatim record)

TASK_S5R and TASK_S5A are recorded below as sent. TASK_S5B and TASK_S5C are appended when they are dispatched.

### TASK_S5R

```text
Web research, REPORT-ONLY, for OGCM GATE S5. Write exactly ONE file: D:/Projects/Music-AI-Toolshop/ORCHESTRATION/ogcm_flip/wave_s5r/research_wail_report.md (create the folder). No code changes, no git, no other writes.

BACKGROUND
We are re-performing (resynthesizing) the melodic "wailing" lead from 2Pac "Only God Can Judge Me" (All Eyez on Me, 1996). The instrumental runs at about 89 BPM felt and is in F# minor; our sample transposes it -4 semitones to D minor. The wail will play on our own numpy synth voice, driven by a pitch contour tracked from a demucs-separated stem. No source audio goes into the output. The user cannot name the instrument.
Our current G-funk lead voice is render_gfunk_lead:
- sine + 0.35 x saw, mono-legato
- portamento 100 ms
- vibrato 5.5 Hz, onset delay 180 ms, depth 0.45 semitone
- attack 12 ms / release 80 ms, tanh soft clip
- lead delay 0.375 s (being corrected to a dotted 8th = 0.505 s at 89.1 BPM), reverb room 0.45

QUESTIONS
Q1 Identity. What instrument or sound makes the high wailing/whining lead on "Only God Can Judge Me"?
- Check production credits (producers, keyboardists, other musicians), liner notes and producer interviews.
- Check WhoSampled for samples or interpolations used in the track, and Genius annotations.
- Check forums (Gearspace, Reddit r/makinghiphop, r/hiphopheads and similar).
- Candidates: Minimoog/portamento synth lead, talkbox, guitar with slide or bends, female backing vocal, sampled source.
- "Unknown" is an acceptable answer. Give a confidence level and never present a guess as fact.

Q2 Synth recipe for a classic G-funk "whine"/"whistle" lead (Minimoog-style). Give concrete numbers, with sources, for:
- oscillator waveform(s) and mix
- filter type, cutoff and resonance
- portamento/glide time (ms)
- vibrato rate (Hz), depth (semitones or cents) and onset delay
- amplitude envelope (attack/release)
- typical delay note value and reverb
Then give a table: parameter | recommended value | our current value | source.

Q3 Pitch-contour tracking of ONE lead line using only librosa (pyin or yin; no new dependencies), for a lead around MIDI 60-90 in a demucs-separated stem that still carries leftover sound from other instruments. Cover:
- recommended fmin/fmax
- frame_length/hop_length at 22.05 kHz
- voiced-probability thresholding
- fixing octave errors
- median-filter length
- bridging short unvoiced gaps
- keeping vibrato and glides intact (avoid over-smoothing)
Cite the librosa docs, Mauch & Dixon 2014 (pYIN) and reputable MIR sources.

OUT OF SCOPE
Do not research or describe any technique for getting copyrighted recordings past Suno's (or any) content-identification filter. Our path is re-performance on our own synth, not disguising source audio.

FORMAT
- A 5-bullet summary.
- Sections Q1, Q2 and Q3. Every claim carries [source URL] and a confidence level (high/med/low).
- End with two code-free blocks: "Recommended parameters for render_f0_lead" and "pyin settings".
- About 1500 words at most.
Your final message: the report path plus the 5-bullet summary.
```

### TASK_S5A

```text
Execute wave s5a of OGCM GATE S5 in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only s5a.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md: the project contract (venv-only Python, close-out discipline).
2. The approved plan D:/Projects/.workspace_archive/plans/ogcm-s5-wail-resynth.md, sections Context, "s5a", Constraints and Verification.
3. The S4 code you build on: toolshop/flip/sample_voices.py and scripts/ogcm_sample.py (_s4_variants, _render_s3, _to_target, main).

CONTEXT
- S4 (audition_s4, commits f46da72..36f1d4f) was ear-accepted.
- The user wants the record's "wailing" sound but cannot name the instrument.
- Suno REJECTED the raw chop s4_05_chop_REF.wav. So nothing in audition_s5/ may contain source audio. The stem clips you cut here are LOCAL identification aids only.
- Measured in the 54-67 s window:

  | Stem | Level | Energy share 700-3000 Hz |
  |---|---|---|
  | htdemucs_6s guitar | -33.5 dBFS | 0.54 (prime suspect) |
  | v2 backing-vocal residue | -38.0 dBFS | 0.35 |
  | other | -38.2 dBFS | 0.20 |
  | piano | -71.6 dBFS | silent (skip it) |

- Bug to fix: west_coast_chain hard-codes the lead Delay at 0.375 s. The dotted 8th at 89.1 BPM is 0.505 s.

TASKS

0. Pre-flight.
- Run git -C D:/Projects/Music-AI-Toolshop status --short and log --oneline -5. Note the foreign-lane dirty files and never touch them.
- Confirm pyin exists: D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -c "import librosa; print(librosa.__version__, hasattr(librosa, 'pyin'))". If it is absent, STOP and report. No installs.

1. NEW scripts/ogcm_stem_audition.py.
- CLI: argparse with --start 54.0, --end 67.0, --outdir (default Stemmeca_alatkka/stems/flip_sample/audition_s5_stems), --no-timeline.
- Candidate stems:
  - Stemmeca_alatkka/stems/htdemucs_6s/2Pac - Only God Can Judge Me/{guitar,other,vocals,bass}.wav
  - the v2 backing-vocal residue: glob Stemmeca_alatkka/stems/v2/*_(vocals)_*_(Instrumental)_*.wav and name it "backing_vox". Glob-escape the brackets or use fnmatch, since the parentheses are literal.
- Clips: write stem_<name>.wav covering the window.
  - Loudness-match to -20 LUFS with toolshop.flip.master.integrated_lufs.
  - Peak-guard to <= -1 dBTP with master.true_peak_dbfs.
  - 44.1 kHz stereo, PCM_24.
- Per-stem measurement: run librosa.pyin on a mono 22.05 kHz copy (fmin 65 Hz, fmax 2000 Hz, hop 256). Record:
  - voiced_ratio
  - median, p10 and p90 of the voiced pitch in MIDI
  - glide_share: the share of voiced frames where |d midi| > 0.5 semitone per 50 ms
  - vibrato_score: the peak spectral magnitude of the detrended voiced MIDI curve in 4-7 Hz, divided by the peak in 1-15 Hz
  - mean voiced_prob
- Ranking: define a documented wail_score, with the formula written into the JSON. Favor high voiced_ratio, median MIDI 60-90, glides and vibrato. Write stem_ranking.json sorted by wail_score.
- Timeline, for the top-2 stems by wail_score: run pyin over the whole song in 30 s chunks.
  - Output per-2-second bins of high-register voiced activity (voiced AND midi >= 60) to timeline_<name>.json.
  - Include the top-5 bins as mm:ss timestamps, so the user can see where the wail lives if it is not in 54-67 s.
  - If one stem's whole-song pyin exceeds ~6 min of wall time, stop the timeline for that stem and report it. Do not loop.
- Report wall time per stage.

2. toolshop/flip/sample_voices.py. Minimal, additive changes only:
- Add the constant DOTTED_8TH_S = 0.75 * 60.0 / FELT_BPM (about 0.505 s).
- Give west_coast_chain a keyword lead_delay_s: float = 0.375, used as the lead Delay's delay_seconds.
- The default stays 0.375, so S2-S4 are byte-reproducible. Change nothing else in existing functions.

3. scripts/ogcm_sample.py: add --pack s5.
- In this wave it renders ONLY s5_00_riff_whine into Stemmeca_alatkka/stems/flip_sample/audition_s5/.
- Contents: the S4 riff and S4's derived chords + sub, using the same source, extraction, transpose and chord derivation as _s4_variants.
  - Reuse; do not copy-paste. If you factor out a shared helper, S4 output must stay byte-identical.
  - Voice the riff with sv.render_gfunk_lead.
  - Pass the lead through west_coast_chain(..., lead_delay_s=sv.DOTTED_8TH_S).
  - fit_loop to 8 bars, then _to_target -16 LUFS.
- Write manifest.json and verification.json the way S4 does. Add "source_audio_in_output": false and "lead_delay_s".
- NO _real_chop and no stem audio anywhere in the s5 pack.
- Prove S4 is unchanged with the cheapest valid evidence, and state which you used. Either re-render --pack s4 to a scratch outdir and compare sample hashes of s4_01 to the committed-render run, or diff the riff/chords in the manifest and show the S4 code path is byte-identical in git diff.

4. Stemmeca_alatkka/stems/flip_sample/index.html: a new S5 section at the TOP.
- (a) A player for audition_s5/s5_00_riff_whine.wav, captioned: "S4 riff on the G-funk whine voice; echo synced to the dotted 8th (0.505 s)".
- (b) "Wail finder — LOCAL ID ONLY, not for Suno":
  - one player per stem clip
  - the ranking table (stem, wail_score, voiced_ratio, median note name, glide_share, vibrato_score)
  - the top timeline bins with mm:ss timestamps
- Leave the S4/S3/S2 sections below it unchanged.

5. tests/test_flip_sample.py (synthetic data, small SR):
- west_coast_chain output is identical with no kwarg and with lead_delay_s=0.375.
- lead_delay_s=0.505 gives a different output.
- DOTTED_8TH_S == pytest.approx(0.505, abs=1e-3).

6. Gates. Quote each command, its exit code and key output.
- O2: .venv python -m pytest "D:/Projects/Music-AI-Toolshop/tests/test_flip_sample.py" -q
- O4: .venv python -m pytest on tests/test_flip_sample.py, test_flip_arrange.py, test_flip_master.py and test_flip_bed_lanes.py (absolute paths) -q
- O5: .venv python scripts/check_riff.py on Stemmeca_alatkka/stems/flip_sample/audition_s4/manifest.json (see its --help) must exit 0.
- O1'' (this wave has 1 file): verify_sample_pack.py --dir <abs>/audition_s5 --glob "s5_*.wav" --min-files 1 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0
- O3'': check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --dir <abs>/Stemmeca_alatkka/stems/flip_sample --glob "audition_s5/s5_*.wav" --index index.html
  - Run it again with --glob "audition_s5_stems/stem_*.wav".
  - If :8777 is down (check first), start `.venv python -m http.server 8777` with cwd Stemmeca_alatkka/stems as a background process and leave it running.

7. Commit.
- Explicit paths only:
  - scripts/ogcm_stem_audition.py
  - toolshop/flip/sample_voices.py
  - scripts/ogcm_sample.py
  - tests/test_flip_sample.py
  - CHANGELOG.md: take the next unique #NNN after #073; grep to confirm it is unused
  - ORCHESTRATION/ogcm_flip/LEDGER.md: an s5a row
- Message: feat(#NNN): GATE S5a - wail finder stem audition + whine probe + dotted-8th delay sync.
- Files under Stemmeca_alatkka/stems/ are gitignored. Confirm with git check-ignore and never force-add.
- Use separate git add and git commit calls.

8. Handoff: ORCHESTRATION/ogcm_flip/wave_s5a/agent_a_s5a_handoff.md, committed in a follow-up docs commit. It contains:
- the commit hash(es)
- every command with its exit code and key output
- the stem_ranking table verbatim
- the top timeline bins for the top-2 stems
- wall times
- any deviation from this prompt
Do NOT claim which stem "is" the wail. Only the user's ear decides.

CONSTRAINTS
- Python: only D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe (3.11), never the global 3.13. Absolute paths; Cwd = D:/Projects/Music-AI-Toolshop; CPU only.
- No edits to toolshop/flip/bed_lanes.py, arrange.py or master.py. extract_motif and extract_riff stay unchanged. No new dependencies. Renders are deterministic.
- Suno-bound audition_s5/s5_* contains no source audio.
- git -C D:/Projects/Music-AI-Toolshop, explicit paths, separate add/commit. Never stage MAirina_Tucc/, lyrics_*, Genious_*, scratch_* or ORCHESTRATION/lyrics_sources. No WAVs committed. Never --no-verify.
- If a hook or concurrent session races your commit, re-check git status and report. Never force.
- Foreground only; never "background + end turn". Split long pyin runs across calls.
- Your final message: the handoff path, commit hashes, the gate exit codes and the stem_ranking table.
```

### TASK_S5B

```text
Execute wave s5b of OGCM GATE S5 in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only s5b.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md
2. The approved plan D:/Projects/.workspace_archive/plans/ogcm-s5-wail-resynth.md, sections Context, "s5b", Constraints and Verification.
3. ORCHESTRATION/ogcm_flip/wave_s5a/agent_a_s5a_handoff.md: what s5a built.
4. ORCHESTRATION/ogcm_flip/wave_s5r/research_wail_report.md, especially "Recommended parameters for render_f0_lead" and "pyin settings".
5. Code: toolshop/flip/sample_voices.py, scripts/ogcm_sample.py (_s4_variants, the s5 path s5a added, _to_target) and Stemmeca_alatkka/stems/flip_sample/audition_s4/manifest.json. The manifest holds the S4 riff, cell_t0 and chords.

G1 DECISIONS (the user's, final)
- WAIL SOURCE: the htdemucs_6s guitar stem, Stemmeca_alatkka/stems/htdemucs_6s/2Pac - Only God Can Judge Me/guitar.wav. It is a full-length file, time-aligned with the record.
  - s5a measured it in 54-67 s: pyin mean voiced_prob 0.564, median B4 (MIDI 71.0), p10-p90 66.3-75.7, voiced_ratio 0.895, vibrato depth 0.445 st.
- The probe s5_00_riff_whine is "close". Build the resynthesized A/B/C pack.
- NEW TEMPO REQUIREMENT: "a bit faster, 1.15-1.20x of the guitar riff". The orchestrator chose 105 BPM for the WHOLE pack, which is 1.1785x the record's 89.1 felt BPM.
  - Add --tempo-bpm (default 105 for --pack s5; S4 and every other pack stay untouched).
  - Everything time-scales by 89.1/105: riff notes, the chord and sub bars, the wail contour's time axis (pitch unchanged) and the loop length.
  - The lead echo becomes a dotted 8th at the new tempo: 0.75*60/bpm = 0.4286 s at 105.
  - Record bpm, the tempo factor and the delay in the manifest.
  - Reuse sv.tempo_scale and the bar_s parameters of derive_chords, chord_bednotes and bass_root_notes. Do not duplicate them.

HARD RULE
Suno REJECTED raw source audio. Every file in audition_s5/ is SYNTHESIS ONLY: no _real_chop, and no stem or record samples in any output lane. Stem audio may be read ONLY to extract the pitch contour and RMS envelope.

TASKS

0. Pre-flight: git -C D:/Projects/Music-AI-Toolshop status --short and log --oneline -5. Never touch foreign-lane files.

1. toolshop/flip/sample_voices.py. ADDITIVE only; existing functions stay unchanged.
- extract_f0_contour(y, sr, fmin=196.0, fmax=2093.0, frame_length=1024, hop_length=128, target_sr=22050)
  - returns a dict of times, f0_hz (NaN where unvoiced), voiced_prob and rms
  - uses librosa.pyin with default HMM params and fill_na=nan
  - voiced mask: voiced_flag AND voiced_prob >= 0.5 AND an RMS gate
- clean_contour(...), in this order:
  1. octave fix per segment against the local median
  2. median filter of 5-7 frames inside voiced segments only
  3. drop islands shorter than about 9 frames
  4. bridge gaps up to about 17 frames, only when the step across is 3 semitones or less
  - If you use hop 256 for speed, halve the frame counts and say so.
- transpose_contour(contour, st)
- time_scale_contour(contour, factor): scales times only; pitch unchanged.
- contour_stats(contour) returns:
  - voiced coverage inside phrases
  - octave_jumps: frame-to-frame |d midi| >= 10 inside segments after cleaning
  - in_key_ratio: the share of note segments whose median MIDI, rounded, has a pitch class in D_MINOR_PCS after the transpose. Bends are allowed because it uses segment medians.
  - n_segments
  - measured contour vibrato, peak-to-peak cents, on sustained segments
- render_f0_lead(contour, sr=44100, sine=1.0, saw=0.35, lpf_hz=None, attack_ms=10, release_ms=70, smooth_ms=20, add_vibrato=False)
  - phase-accumulating oscillator following the contour, linearly interpolated to audio rate
  - smooth pitch with a constant 15-30 ms window only. The contour already holds the glides; no 100 ms portamento.
  - legato across bridged gaps; retrigger on longer gaps
  - amplitude from the smoothed RMS times voiced gating, with ~10 ms fades
  - tanh soft clip plus a peak guard; mono to stereo
  - Synthetic vibrato only if add_vibrato=True: 5.5 Hz, +/-30-45 cents, 180 ms onset, ramped in. Per the report, add it only when the measured contour vibrato is under about 40 cents peak-to-peak. Report the measurement and your choice.

2. Timing and alignment.
- Read cell_t0 and the riff from audition_s4/manifest.json. The S4 riff cell starts at absolute 54.0 + cell_t0 in record time.
- Extract the guitar contour from the SAME absolute window: 2 bars at 89.1 BPM (5.388 s). Extend it to 4 bars if the wail phrase clearly continues. The stem is full-length, so reading past 67 s is fine. Record the choice and the exact absolute window.
- Transpose -4 (F#m to Dm), time-scale to 105 BPM, and tile to the 8-bar loop so the wail keeps its original timing relative to the riff.
- DIAGNOSTIC to report: onset and pitch agreement between contour segments and the S4 riff notes, in the native key.
  - Compute the share of riff notes that have a contour segment within 1 sixteenth and 1 semitone.
  - The guitar range F#4-E5 overlaps the riff, so the guitar may be the riff instrument itself. If agreement is high, say so; it means A is a unison doubling.

3. scripts/ogcm_sample.py --pack s5. Writes to Stemmeca_alatkka/stems/flip_sample/audition_s5/. All files are at 105 BPM, loudness-matched to -16 LUFS, with TP <= -1.

   | File | Contents |
   |---|---|
   | s5_00_riff_whine | re-rendered at 105 BPM with the new-tempo delay |
   | s5_A_layer | S4 body (riff on the S4 sine lead + derived chords + sub) plus the wail from render_f0_lead on top, with the synced delay and reverb |
   | s5_B_replace | the wail as the lead over the S4 chords + sub; the S4 riff muted |
   | s5_B_replace_saw | B with a saw-heavy timbre per the report: saw 1.0, sine 0.3, 24 dB/oct LPF around 5 kHz, mild resonance (use pedalboard LadderFilter). No ground truth exists, so the user picks by ear. |
   | s5_C_texture | S4 riff as the lead; the wail at half speed (contour time axis x2, pitch kept), low-pass filtered, fully wet delay/reverb, about -12 dB under |

- Also write:
  - manifest.json, including wail_source (stem path, absolute window, bars), contour_stats, recipe, bpm, tempo_factor, lead_delay_s, the riff agreement diagnostic and "source_audio_in_output": false
  - verification.json
  - contour.npz next to the manifest, holding times, f0_hz, voiced and rms after cleaning and before tiling. The verifier recomputes from it.
- Renders must be deterministic: two runs give identical bytes. Check it.

4. NEW scripts/check_contour.py (O6). It reads audition_s5/manifest.json and contour.npz and exits 0 only if all of these hold:
- voiced coverage in phrases >= 0.6
- octave_jumps == 0
- in_key_ratio >= 0.8
- source_audio_in_output is false
- bpm is between 102.5 and 107 (1.15-1.20 x 89.1)
- stats recomputed from the npz match the manifest within 1%
If in_key_ratio fails, report the offending segments. Do not loosen the threshold.

5. tests/test_flip_sample.py (synthetic data, small SR):
- A synthetic glide + vibrato sine survives the full cycle: extract, clean, render. The median pitch comes back within 0.5 st, and the output is non-silent.
- An injected octave jump is fixed (octave_jumps == 0).
- transpose_contour is exact.
- time_scale_contour scales times and leaves pitch alone.
- render_f0_lead is deterministic, finite, <= 1.0 and mono-equal L/R.
- Silent input gives an empty contour and silence out.
- contour_stats in_key_ratio is 1.0 on a Dm scale contour.

6. Records.
- Stemmeca_alatkka/stems/flip_sample/index.html: an S5 A/B/C section at the TOP, above the s5a wail finder.
  - Caption each file with its role.
  - State: "105 BPM (1.18x), D minor, synthesis only (no source audio)".
  - Say which variant is saw-heavy.
- Write the spec D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s5_<YYYYMMDD_HHMMSS>.md:
  - O1'' verify_sample_pack --dir audition_s5 --glob "s5_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0
  - O2 and O4 unchanged
  - O3'' serve audition_s5/s5_*.wav
  - O5 check_riff on S4
  - O6 check_contour
- LEDGER.md: an s5b row.
- CHANGELOG.md: the next unique #NNN after #074; grep to confirm it is unused.

7. Gates: run O1'', O2, O3'', O4, O5 and O6, and quote each command, exit code and key output.
- Check that :8777 is up before O3''. Start it from Stemmeca_alatkka/stems as a background process only if it is down.
- The 8-bar loop at 105 BPM is about 18.3 s, inside 15-45.

8. Commit with explicit paths: sample_voices.py, ogcm_sample.py, check_contour.py, test_flip_sample.py, CHANGELOG.md and LEDGER.md.
- Message: feat(#NNN): GATE S5b - resynthesized guitar wail (pyin contour, no source audio) + A/B/C pack at 105 BPM.
- Separate add and commit calls. Stems stay gitignored; confirm with check-ignore and never force-add.
- Then write the handoff ORCHESTRATION/ogcm_flip/wave_s5b/agent_b_s5b_handoff.md and commit it as docs. It includes:
  - the commit hashes
  - every command with its exit code and key output
  - contour_stats
  - the riff agreement diagnostic
  - the vibrato measurement and choice
  - the chosen window and bars
  - wall times
  - deviations
  Do NOT claim the wail "sounds right". Only the user's ear decides.

CONSTRAINTS
- Python: only D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe (3.11). Absolute paths; Cwd = D:/Projects/Music-AI-Toolshop; CPU only.
- No edits to bed_lanes.py, arrange.py or master.py. extract_motif, extract_riff and all existing function behavior stay unchanged. S4 output must stay byte-identical; re-prove it the cheapest valid way. No new dependencies. Renders are deterministic.
- Nothing Suno-bound contains source audio.
- git -C, explicit paths, separate add/commit. Never stage MAirina_Tucc/, lyrics_*, Genious_*, scratch_* or ORCHESTRATION/lyrics_sources. No WAVs committed. Never --no-verify. If a concurrent session races you, re-check status and report; never force.
- Foreground only; never "background + end turn". pyin is slow (~30 s per 13 s at hop 256), so split long runs across calls.
- Your final message: the handoff path, commit hashes, the gate exit codes, contour_stats and the riff agreement diagnostic.
```
