# Wave 1 / Agent B — Render Inventory

Status: COMPLETE

Deliverable for D:\Projects\Music-AI-Toolshop and D:\Projects\music_toolshop_v2 (Wave 1 / Agent B). Structure: Render block table (parts 1-8) followed by Q1-Q4 and Uncertainties.
## Render block table (part 1 — music_toolshop_v2/pipeline)

| repo | file:line | function | what it does to audio | parameters accepted | hardcoded constants | library |
|---|---|---|---|---|---|---|
| v2 | pipeline/corrective_eq.py:21-32 | `to_mid_side` | stereo (2,N) -> mid/side (2,N), `mid=(L+R)/sqrt(2)`, `side=(L-R)/sqrt(2)` | none (audio only) | sqrt(2) constant | numpy |
| v2 | pipeline/corrective_eq.py:35-46 | `from_mid_side` | mid/side -> stereo inverse of above | none | sqrt(2) | numpy |
| v2 | pipeline/corrective_eq.py:49-69 | `side_hpf` | HPF on side channel only (mono-izes sub-cutoff) | `sr` (int), `cutoff` Hz (default 150.0), `stages` int cascade count (default 1) | none hardcoded beyond defaults (all overridable) | pedalboard.HighpassFilter |
| v2 | pipeline/corrective_eq.py:77-115 | `_deesser` | dynamic sibilance reduction via bandpass envelope + gain reduction | `sr`, `low_hz` (6000.0), `high_hz` (8000.0), `threshold` (0.05 linear), `reduction_db` (-6.0) | attack 0.005s, release 0.030s hardcoded inside function (not params) | scipy.signal (butter, sosfilt, lfilter) |
| v2 | pipeline/corrective_eq.py:123-130 | `_bass_chain` | 4x cascaded HPF@35Hz (48dB/oct) + PeakFilter cut -3dB@100Hz Q1.5 | none — all hardcoded | 35.0 Hz x4, 100.0/-3.0/1.5 | pedalboard HighpassFilter, PeakFilter |
| v2 | pipeline/corrective_eq.py:133-136 | `_other_chain` | PeakFilter cut -3dB @350Hz Q0.7 | none — hardcoded | 350.0/-3.0/0.7 | pedalboard PeakFilter |
| v2 | pipeline/corrective_eq.py:139-142 | `_drums_chain` | HPF @30Hz | none — hardcoded | 30.0 | pedalboard HighpassFilter |
| v2 | pipeline/corrective_eq.py:145-148 | `_vocal_chain` | HPF @100Hz only | none — hardcoded | 100.0 | pedalboard HighpassFilter |
| v2 | pipeline/corrective_eq.py:151-155 | `_mix_chain` | HPF@30Hz + PeakFilter -2dB@350Hz Q0.7 | none — hardcoded | 30.0, 350.0/-2.0/0.7 | pedalboard |
| v2 | pipeline/corrective_eq.py:158-167 | `_vocal_pocket_chain` | static 2-band cut to carve pocket for vocal: -1.5dB@250Hz Q0.7, -1.0dB@2500Hz Q1.0 | none — hardcoded | 250/-1.5/0.7, 2500/-1.0/1.0 | pedalboard PeakFilter |
| v2 | pipeline/corrective_eq.py:182-204 | `_genre_band_chain` | builds PeakFilter chain from `profile["frequency"]["bands"]` dict (name like "100_hz"->gain_db) with fixed Q=sqrt(2) octave-band | `profile: dict` — band name/gain pairs; only source of PARAMETERIZED eq in this file | Q=sqrt(2)=1.414 fixed | pedalboard PeakFilter |
| v2 | pipeline/corrective_eq.py:207-261 | `apply_eq` | dispatches stem_type -> base hardcoded chain, then optional genre_band_chain(profile), then optional vocal_pocket, then deesser if vocal | `stem_type` enum, `profile: dict\|None`, `vocal_pocket: bool` | see above | pedalboard + scipy |
| v2 | pipeline/corrective_eq.py:269-282 | `apply_corrective_eq` | back-compat wrapper -> apply_eq(stem_type="mix") | `profile`, `vocal_pocket` | — | — |
| v2 | pipeline/dynamics.py:27-57 | `compress` | single-band Compressor | `threshold_db`, `ratio`, `attack_ms`, `release_ms` — all REQUIRED args, no defaults | none in this fn itself | pedalboard.Compressor |
| v2 | pipeline/dynamics.py:60-141 | `shape_crest_factor` | iterative compression loop to hit target crest factor, with RMS gain-comp + true-peak ceiling clamp | `target_crest_db`, `true_peak_ceiling` (default -1.0) | threshold_db=-18.0, attack_ms=2.0, release_ms=100.0 hardcoded inside loop; ratio=2.0+i*2.0 hardcoded schedule; max 5 iterations; err<=0.5 break threshold | pedalboard.Compressor via compress() |
| v2 | pipeline/dynamics.py:144-164 | `vocal_chain` | 5-step: HPF80Hz -> NoiseGate(-55dB,20ms,250ms) -> Compressor(-22dB,2.5:1,15ms,200ms) -> HighShelf +3dB@4kHz | `sr` only — ALL DSP values hardcoded, no profile arg | 80.0, -55.0/20.0/250.0, -22.0/2.5/15.0/200.0, 4000.0/3.0 | pedalboard HighpassFilter, NoiseGate, Compressor, HighShelfFilter |
| v2 | pipeline/dynamics.py:167-216 | `apply_dynamics` | dispatch by stem_type to vocal_chain or compress() with per-stem-type hardcoded settings; `profile` PARAM ACCEPTED BUT NOT USED (see Q2) | `stem_type` enum, `profile: dict` (unused in body), `target` str (unused in body) | drums: -22/3.0/10/150; bus: -18/2.0/15/200; bass/other: -22/2.0/30/200; else: -20/2.0/20/200 | pedalboard |
| v2 | pipeline/saturation.py:57-74 | `saturate_tanh` | tanh waveshaper distortion + LUFS gain-comp | `drive_db` (default 0.0 = no-op), `sr` | gain=10**(drive_db/20) | numpy.tanh (not pedalboard's Distortion class) |
| v2 | pipeline/saturation.py:77-103 | `exciter` | HPF split + tanh-saturate high band + mix back + gain-comp | `sr`, `amount` (0.0-1.0, default 0.3), `freq_min` Hz (default 3000.0) | saturated_high = tanh(high_band*2.0) — the "2.0" drive is hardcoded, not exposed | pedalboard.HighpassFilter + numpy.tanh |
| v2 | pipeline/saturation.py:106-135 | `sub_bass_psychoacoustic` | PeakFilter boost @f0 then tanh-saturate to generate 2f0/3f0/4f0 harmonics | `sr`, `f0` Hz (default 55.0), `boost_db` (default 2.5) | q=1.0 fixed on PeakFilter | pedalboard.PeakFilter + numpy.tanh |
| v2 | pipeline/saturation.py:176-223 | `resolve_saturation_params` | pure param resolver, NOT audio-touching: profile["saturation"][key] else built-in default, per role | `role` enum, `profile: dict\|None` | defaults: sub_f0=55.0, sub_boost_db=2.5, exciter_amount_vocal=0.3, exciter_freq_min_vocal=3000.0, drive_db_drums=6.0, exciter_amount_master=0.15, exciter_freq_min_master=4000.0, drive_db_master=3.0 | none (pure python dict logic) |
| v2 | pipeline/saturation.py:226-287 | `apply_saturation` | dispatch stem_type -> resolve_saturation_params -> sub_bass_psychoacoustic/exciter/saturate_tanh (chained for full/other) | `stem_type` enum, `profile: dict\|None`, `provenance: dict\|None` | pshf raises NotImplementedError | pedalboard + numpy |

## Render block table (part 2 — music_toolshop_v2/pipeline continued)

| repo | file:line | function | what it does to audio | parameters accepted | hardcoded constants | library |
|---|---|---|---|---|---|---|
| v2 | pipeline/ambience.py:29-76 | `apply_ambience` | algorithmic reverb (wet-only) band-limited by HPF+LPF, mixed at wet_db level with dry signal. Explicitly NOT blind-matched — doc comment states "user tunes by ear" | `wet_db` (dB, default -18.0; <=-60 = off), `room_size` (0-1, default 0.5), `damping` (0-1, default 0.5), `hpf_hz` (Hz, default 200.0), `lpf_hz` (Hz, default 8000.0) — all pedalboard-native units | wet_level=1.0/dry_level=0.0 fixed inside Reverb (wet mix done manually outside), -60dB off-threshold | pedalboard.Reverb, HighpassFilter, LowpassFilter |
| v2 | pipeline/mastering.py:19-23 | `PLATFORM_TARGETS` (module const) | LUFS target table | n/a | spotify=-14.0, apple=-16.0, youtube=-14.0 | — |
| v2 | pipeline/mastering.py:41-44 | `_apply_gain` | linear gain scale audio by dB | `gain_db` | — | numpy |
| v2 | pipeline/mastering.py:52-124 | `master_to_target` | gain to target LUFS, measure true peak, reduce gain if over ceiling, pedalboard Limiter brick-wall safety, re-correct TP after limit | `target_lufs` (LUFS, required), `true_peak_ceiling` (dBTP, default -1.0) | _STREAMING_TP=-1.0 module const (line 26, used elsewhere not here directly) | pedalboard.Limiter; analysis.measure (measure_lufs, measure_true_peak) |
| v2 | pipeline/mastering.py:127-162 | `apply_mastering` | resolves target_lufs/tp_ceiling from PLATFORM_TARGETS or profile["streaming"]/profile["club"], calls master_to_target | `profile: dict` (streaming.lufs, streaming.true_peak_dbtp, club.lufs_range, club.true_peak_dbtp), `target` enum (streaming/club/spotify/apple/youtube) | — | pedalboard (via master_to_target) |
| v2 | pipeline/mastering.py:165-202 | `master_with_reference` | reference-based mastering (FFT freq matching, RMS/LUFS, peak ceiling, stereo width) — file-path based, not array-based | `input_path`, `reference_path`, `out_path` (paths only, no numeric knobs — Matchering auto-decides) | subtype="PCM_24", use_limiter=True, normalize=True fixed | matchering (Matchering 2.0), NOT pedalboard |
| v2 | pipeline/mastering.py:210-227 | `master` | back-compat wrapper -> apply_mastering | `profile`, `target` (default "spotify") | — | — |
| v2 | pipeline/club_master.py:36-43 | `_to_stereo` | mono->stereo duplication / shape coercion to (2,N) | — | — | numpy |
| v2 | pipeline/club_master.py:50-107 | `make_club_master` | 6-stage club chain: side_hpf(4x cascaded @ mono_below_hz) -> mid/side re-encode + side*1.5 gain -> sub_bass_psychoacoustic(role="bass" via resolve_saturation_params) -> compress(glue 2:1) -> apply_mastering(target="club") | `profile: dict` — reads `profile["stereo"]["mono_below_hz"]` (default 120.0 fallback), sub-bass params via resolve_saturation_params("bass", profile) | mono_below default 120.0; side gain x1.5 HARDCODED (not in profile); glue compress -18.0dB/2.0:1/30ms/200ms HARDCODED | pedalboard (via imported fns) |
| v2 | pipeline/club_master.py:110-142 | `export_club` | writes 24-bit PCM WAV via soundfile + 320kbps MP3 via ffmpeg subprocess | `out_stem` path | subtype="PCM_24", "320k" bitrate | soundfile, ffmpeg (subprocess) |
| v2 | pipeline/club_master.py:149-165 | `club_master` | back-compat wrapper -> make_club_master | `profile` | — | — |
| v2 | pipeline/format_norm.py:16-73 | `normalize` | decode lossy (mp3/aac/wav) -> resample if needed -> float32 [-1,1] -> write 32-bit float WAV | `input_path`, `out_dir`, `target_sr` (Hz, default 44100) | max_val = 1<<(8*sample_width-1) (PCM normalization constant, derived not hardcoded) | pydub (ffmpeg backend) for decode/resample; soundfile for WAV write; NOT pedalboard |

## Render block table (part 3 — Music-AI-Toolshop/toolshop/remix_adapter.py)

| repo | file:line | function | what it does to audio | parameters accepted | hardcoded constants | library |
|---|---|---|---|---|---|---|
| M-A-T | toolshop/remix_adapter.py:383-389 | `_to_channels_first` | shape convert (samples,channels)->(channels,samples) for pedalboard | — | assumes <=2 channels | numpy |
| M-A-T | toolshop/remix_adapter.py:392-398 | `_to_samples_first` | inverse shape convert (channels,samples)->(samples,channels) for soundfile | — | assumes <=2 channels | numpy |
| M-A-T | toolshop/remix_adapter.py:401-435 | `_stretch_segment` | tempo/pitch shift via pedalboard.time_stretch (Rubber Band) | `sr`, `src_bpm`, `dst_bpm`, `src_key`, `dst_key`, `**stretch_kwargs` passthrough | stretch_factor=1.0 fallback, 1e-6 epsilon | pedalboard.time_stretch (Rubber Band) |
| M-A-T | toolshop/remix_adapter.py:438-476 | `_build_fx_board` | builds a Pedalboard from fx name list: "reverb"/"delay"/"gain"/"compressor"/"distortion" | `fx_chain: List[str]` (names only — no numeric knobs exposed to caller), `sr` | reverb: room_size=0.4,damping=0.7,wet_level=0.15,dry_level=0.85 (ALL fixed); delay: delay_seconds=0.375,feedback=0.25,mix=0.3 (fixed); gain: gain_db=6.0 (fixed); compressor: threshold_db=-14.0,ratio=3.0,attack_ms=5.0,release_ms=50.0 (fixed); distortion: drive_db=4.0 (fixed). Unknown fx name -> logged warning, skipped. | pedalboard.Reverb, Delay, Gain, Compressor, Distortion |
| M-A-T | toolshop/remix_adapter.py:479-488 | `_apply_fx` | applies `_build_fx_board` result to audio, shape-converts in/out | `fx_chain: Optional[List[str]]`, `sr` | — | pedalboard |
| M-A-T | toolshop/remix_adapter.py:491-527 | `_crossfade_concat` | linear crossfade concatenation of audio segments | `crossfade_ms` (default 12.0) | — | numpy |
| M-A-T | toolshop/remix_adapter.py:555-568 | `_STEM_HPF` / `_STEM_GAIN_DB` (module dicts) | per-stem-name HPF cutoff + gain table used by combine_stems | n/a | drums HPF 30.0, other 150.0, guitar 120.0, piano 100.0 (no bass/vocals entries -> no HPF applied to those); gain_db: drums 0.0, bass -1.0, other -3.0, guitar -4.0, piano -4.0 | — |
| M-A-T | toolshop/remix_adapter.py:571-662 | `combine_stems` | reads stem WAVs, applies per-stem HPF (pedalboard.HighpassFilter) + gain (linear dB scale), sums to stereo (tiles mono->stereo), peak-normalizes to -1 dBFS | `stems_dir`, `output_path`, `skip_stems` (no numeric DSP params — table above is fully hardcoded, not exposed) | target_peak = 10**(-1/20) i.e. -1 dBFS ceiling hardcoded (line 651); mono->stereo via np.tile when channels==1 | pedalboard.HighpassFilter, soundfile |

## Render block table (part 4 — Music-AI-Toolshop/toolshop/vocal_swap/mix.py)

NOTE: this file works in **samples-first (n, channels)** shape throughout — the OPPOSITE convention from pedalboard's channels-first (channels, samples). See Q4.

| repo | file:line | function | what it does to audio | parameters accepted | hardcoded constants | library |
|---|---|---|---|---|---|---|
| M-A-T | toolshop/vocal_swap/mix.py:117-135 | `load_audio` | loads via librosa (channels-first internally), transposes to samples-first (n,2), mono->stereo duplicate, >2ch truncated to first 2 | `path`, `sr` (default MIX_SR=44100) | forces exactly 2 channels | librosa |
| M-A-T | toolshop/vocal_swap/mix.py:138-153 | `integrated_lufs` | ITU-R BS.1770 integrated loudness measurement (not a render, a measure) | `sr` (default 44100) | requires >= 0.5s audio else -inf | pyloudnorm |
| M-A-T | toolshop/vocal_swap/mix.py:156-160 | `peak_dbfs` | measures peak dBFS (not a render) | — | — | numpy |
| M-A-T | toolshop/vocal_swap/mix.py:163-189 | `fade_edges` | linear fade in/out at both ends to kill filter-edge transients | `sr`, `milliseconds` (default EDGE_FADE_MS=5.0) | — | numpy |
| M-A-T | toolshop/vocal_swap/mix.py:192-214 | `highpass` | 2nd-order Butterworth HPF, ZERO-PHASE (filtfilt/sosfiltfilt), then fade_edges | `sr`, `cutoff` Hz (no default — caller-supplied; DEFAULT_VOCAL_HPF_HZ=80.0 module const used by `mix()`) | order=2 fixed; fade_ms = max(5.0, 2000.0/cutoff) formula fixed | scipy.signal (butter, sosfiltfilt) — NOT pedalboard |
| M-A-T | toolshop/vocal_swap/mix.py:217-231 | `_envelope` | one-pole attack/release envelope follower over mono sum, SAMPLE-BY-SAMPLE PYTHON LOOP (not vectorized) | `sr`, `attack_ms`, `release_ms` | — | numpy |
| M-A-T | toolshop/vocal_swap/mix.py:234-245 | `duck` | sidechain-style ducking: attenuates instrumental by up to depth_db based on vocal envelope (normalized to its 95th percentile) | `depth_db` (dB, 0=disabled; DEFAULT_DUCK_DB=0.0 module const), `attack_ms` (default 10.0), `release_ms` (default 220.0) | 95th percentile ceiling calc fixed | numpy (custom, not pedalboard) |
| M-A-T | toolshop/vocal_swap/mix.py:248-264 | `_fit_lengths` | zero-pads instrumental/vocal to common length (never truncates vocal) | — | — | numpy |
| M-A-T | toolshop/vocal_swap/mix.py:267-345 | `mix` | full vocal-over-instrumental render: HPF vocal -> fit lengths -> LUFS-based vocal gain (target = instr_lufs + balance_db) -> duck instrumental -> sum -> LUFS-target bus gain clamped by peak ceiling | `sr`, `vocal_balance_db` (LU, default DEFAULT_VOCAL_BALANCE_DB=1.5), `duck_db` (default 0.0), `bus_lufs_target` (LUFS, default DEFAULT_BUS_LUFS=-17.0), `bus_peak_dbfs` (dBFS, default DEFAULT_BUS_PEAK_DBFS=-3.5), `vocal_hpf_hz` (Hz, default DEFAULT_VOCAL_HPF_HZ=80.0), `output_path` | module consts: DEFAULT_VOCAL_BALANCE_DB=1.5, DEFAULT_BUS_LUFS=-17.0 (measured/chosen per docstring, not arbitrary), DEFAULT_BUS_PEAK_DBFS=-3.5, DEFAULT_DUCK_DB=0.0, DEFAULT_VOCAL_HPF_HZ=80.0, EDGE_FADE_MS=5.0, MIX_SR=44100 | pyloudnorm, scipy, numpy — NO pedalboard anywhere in this file |
| M-A-T | toolshop/vocal_swap/mix.py:348-355 | `write_wav` | writes 32-bit float WAV | `sr` (default 44100), `subtype` (default "FLOAT") | — | soundfile |

## Render block table (part 5 — Music-AI-Toolshop/toolshop/premaster.py)

**premaster.py is NOT a render module.** Every function in it (`_windowed_correlation`, `_lowpass`, `true_peak_dbfs`, `analyze_premaster`) MEASURES audio and returns PASS/FLAG/FAIL gate verdicts (dataclass `GateResult`) — none of them return processed/rendered audio. `_lowpass` (toolshop/premaster.py:89-93, scipy butter+sosfiltfilt) is used only internally to compute a correlation gate, its filtered output is never written out. Listed here only to record that it is out of scope for "apply a parameter to audio."
- toolshop/premaster.py:96-108 `true_peak_dbfs` — measurement (4x polyphase oversample true-peak estimate), not a render.
- toolshop/premaster.py:111-225 `analyze_premaster` — orchestrates all gates, returns a dict report, writes nothing to audio.

## Render block table (part 6 — Music-AI-Toolshop/mastering_tool — shell chain, runs under WSL)

`mastering_tool/` is a bash/ffmpeg/LV2 chain, NOT Python/pedalboard. Runs under WSL2 per AGENTS.md ("WSL path: /mnt/d/Projects/Music-AI-Toolshop/mastering_tool") and per stage_clip_limit.sh comments ("DEFAULT on WSL2"). Canonical generic pipeline is `master_pipeline_v3.sh`; the `pipelines/` subdir contains one-off per-track scripts (e.g. `Hymn_to_Osiris.sh`) that are NOT generic stage scripts — out of scope beyond noting their existence (mastering_tool/pipelines/*.sh, ~30 files).

| repo | file:line | function/stage | what it does to audio | parameters accepted | hardcoded constants | tool |
|---|---|---|---|---|---|---|
| M-A-T | mastering_tool/master_pipeline_v3.sh:53-56 | Stage A "prep" | volume -3dB, DC shift 0.0004, HPF 25Hz 2-pole | none exposed as CLI args (constants baked into `-af` string) | volume=-3dB, dcshift=0.0004, highpass f=25:poles=2 | ffmpeg `-af` (volume, dcshift, highpass) |
| M-A-T | mastering_tool/master_pipeline_v3.sh:43,58-60 | Stage B "EQ" | 4-band parametric EQ via ffmpeg `equalizer` filter | `EQ_CHAIN` env var override (default baked in) | default: 200Hz/-1.5dB/w1.2, 80Hz/+0.8dB/w1.4, 3500Hz/+0.6dB/w1.5, 12000Hz/+1.5dB/w0.7 | ffmpeg `equalizer=f:t=q:w:g` |
| M-A-T | mastering_tool/master_pipeline_v3.sh:44,62-64 | Stage C "glue comp" | single-band compressor | `COMP` env var override | default: acompressor threshold=-16dB,ratio=1.8,attack=20,release=180,makeup=1.5,knee=4 | ffmpeg acompressor |
| M-A-T | mastering_tool/master_pipeline_v3.sh:67-74, lv2_stage.sh | Stage C2 "multiband" (conditional, `MULTIBAND_ENABLE=1`) | multiband compression via LSP LV2 plugin, latency-calibrated pad/process/trim | URI + `-c SYM VAL` control-port passthrough (generic — any lv2apply plugin) | latency probe uses impulse at sample 4000, amplitude 0.03, pad=LAT+64 | LV2 (`lv2apply`) via lsp-plug.in mb_compressor_stereo |
| M-A-T | mastering_tool/master_pipeline_v3.sh:76-89 | Stage D "widening + bass-mono" | `extrastereo=m=$M` widening (gated ALLOW/SKIP by phase-correlation policy) then optional bass-mono collapse | `WIDEN_M` env (default 1.10 when ALLOW), `BASS_MONO_ENABLE`, `BASS_MONO_FREQ` | widening M default 1.10; -3dB makeup gain when ALLOW; policy decided via `policy_decide_widening` in family_policy.sh | ffmpeg extrastereo, volume |
| M-A-T | mastering_tool/stage_bass_mono.sh:30-39 | bass-mono stage | phase-coherent bass-mono: common-mode 4th-order Linkwitz-Riley HP on L/R + LP on mono sum, remixed (`L_out=HP(L)+LP(mono)`) | `cutoff_hz` (positional, default `BASS_MONO_FREQ` env or 110) | 2x cascaded 2-pole highpass/lowpass = 4th order LR; mix weights 1:1 no normalize | ffmpeg filter_complex (asplit, pan, lowpass, highpass, amix, join) |
| M-A-T | mastering_tool/master_pipeline_v3.sh:97-135 | Stage E pre-gain | auto- or manual pre-gain to hit target LUFS, 2-pass correction if final master >0.5 LUFS off | `PREGAIN_DB` env (manual override) else auto-computed from `TARGET_LUFS - measured_LUFS + 1.5` | +1.5dB fudge factor in auto-gain formula; cap 18.0dB; fallback PREGAIN_DB=6.3 if ebur128 measurement fails; correction threshold 0.5 LUFS | ffmpeg volume, ebur128 (measurement) |
| M-A-T | mastering_tool/stage_clip_limit.sh:52-76 | Stage E0 soft-clip | asoftclip (ffmpeg native, default) OR LSP clipper OR Airwindows ClipOnly2 (LV2, 30s timeout fallback) | `CEILING_DBTP`/`TARGET_TP_DBTP` (dBTP), `E0_CLIPPER` env (ffmpeg\|lsp\|cliponly2), `CLIP_HEADROOM_DB` (default 1.0) | threshold=min(1.0, 10**((TP_DBTP+headroom)/20)); asoftclip param=1.0, oversample=4; LSP clipper ct=0.92 | ffmpeg asoftclip (default) / LV2 lv2apply (Airwindows ClipOnly2, LSP clipper_stereo) |
| M-A-T | mastering_tool/stage_clip_limit.sh:78-89 | Stage E1 true-peak limit | alimiter inside 4x soxr-oversampled scaffold (default/production) OR LSP limiter LV2 (flagged unreliable, overshoots 0.6-0.8dB, `USE_LSP_LIMITER=1` opt-in only) | `TPMARGIN_DB` (default 0.4), `USE_LSP_LIMITER` toggle | ALIM_LIMIT = dB2lin(TP_DBTP - TPMARGIN_DB); oversample factor 192000 (48k src) or 176400 (44.1k src); soxr precision=28 | ffmpeg alimiter+aresample(soxr) (default) / LV2 lsp-plug.in limiter_stereo (flagged unreliable) |
| M-A-T | mastering_tool/master_pipeline_v3.sh:137-146 | Stage F deliverables | copy 32f master; dither to 16-bit (triangular_hp); separate E2 limiter pass (tighter ceiling) feeding 320kbps MP3 | `MP3_CEIL` env (default 0.82, linear) | dither_method=triangular_hp; libmp3lame -b:a 320k -compression_level 0 | ffmpeg aresample(dither)+pcm_s16le, alimiter, libmp3lame |
| M-A-T | mastering_tool/family_policy.sh:26-47 | `policy_profile()` | NOT a render — returns shell var-assignment strings for TARGET_LUFS/TARGET_TP_DBTP per named profile (archival/club/streaming/hiphop/german_rap/german_drill/serbian_drill/house) | profile name string | archival -10.0/-1.0; club -8.5/-1.0; streaming -14.0/-1.5; hiphop -8.0/-1.0; german_rap -9.0/-1.0; german_drill -8.0/-0.8; serbian_drill -8.5/-1.0; house -8.5/-1.0 (all LOCKED, doc says "PRELIMINARY, calibrate against 3-5 references") | n/a — pure param table |
| M-A-T | mastering_tool/chain.json | serialized param snapshot (not a script) | records one run's resolved params: sample_rate 48000, hpf_freq 25.0, eq_bands [[3500,0.7,1.2],[7000,0.5,1.0],[12000,1.6,0.7]], comp threshold/ratio/attack/release, clip_drive_db, limit_ceiling_db=-1.4116214857141456, limit_lookahead_ms=20.0 + per-stage bypass flags | — | this is OUTPUT/state, not code — evidence that stage bypass flags and per-band EQ are individually toggleable | n/a |

Not fully read (out of primary scope per task list, flagged for completeness): `mastering_tool/vocal_prep.sh` (118 lines), `mastering_tool/vocal_restore.sh` (183 lines), `mastering_tool/mix_phase_gate.sh` (99 lines) — titles suggest vocal-specific processing; not opened in detail, see Uncertainties.

## Render block table (part 7 — vocal_prep.sh, vocal_restore.sh — directly vocal-chain relevant)

| repo | file:line | function/stage | what it does to audio | parameters accepted (all env-var overridable) | hardcoded constants | tool |
|---|---|---|---|---|---|---|
| M-A-T | mastering_tool/vocal_prep.sh:57-68 | full vocal-humanization chain (7 stages, ONE ffmpeg `-af` invocation) | de-ess -> boxiness cut -> presence lift -> transient emphasis -> saturation (soft-clip) -> glue compression -> headroom trim, on a full stereo bounce (works on `restored_full_mix.wav`, not an isolated stem) | `DEESSER_FREQ` Hz (default 6000), `BOXINESS_CUT_DB` (default 0.8), `PRESENCE_LIFT_DB` (default 1.0), `TRANSIENT_EMPHASIS_DB` (default 1.2), `GLUE_THRESHOLD_DB` (default 24, used as -24dB), `GLUE_RATIO` (default 1.3), `OUTPUT_HEADROOM_DB` (default 1.0); NOTE `DEESSER_INTENSITY` and `DEESSER_MODE` are declared (lines 25,27) but NEVER used in FILTER_CHAIN — de-ess is actually a static EQ cut, not a dynamic deesser (comment at line 55-56 explains: "this FFmpeg version's deesser uses different param syntax... use static EQ fallback") | de-ess EQ: w=2.0/g=-2.0 fixed shape (only freq configurable); boxiness EQ center fixed 400Hz w1.2; presence EQ center fixed 2500Hz w1.5; transient EQ center fixed 3500Hz w2.0; asoftclip type=0:threshold=0.794 FIXED (SATURATION_DRIVE_DB env var declared line 30 but NEVER referenced in the actual filter — dead parameter); acompressor attack=5:release=50:makeup=1:knee=2 fixed | ffmpeg -af (equalizer x4, asoftclip, acompressor, volume) |
| M-A-T | mastering_tool/vocal_restore.sh:62-91 | stem separation | delegates to `python -m ai_modules.stem_extractor.cli separate` with `--backend roformer --stem vocals,instrumental` | backend fixed to "roformer" in this script | — | Mel-Band RoFormer (via ai_modules CLI, not pedalboard/ffmpeg) |
| M-A-T | mastering_tool/vocal_restore.sh:96-113 | restoration chain dispatch | conditionally runs `restore.py` with `--stage` flags for deepfilter/voicefixer/apollo/audiosr (each a separate ML model), else passthrough copy | `VR_DEROOM`, `VR_VOICEFIXER` (default 1/on), `VR_APOLLO`, `VR_AUDIOSR` (all 0/off by default) toggles | VR_VOICEFIXER default ON, all others default OFF | DeepFilterNet3, VoiceFixer (mode 2), Apollo, AudioSR — NOT located/verified in this task; script references `tools/vocal_restore/restore.py` (not read) |
| M-A-T | mastering_tool/vocal_restore.sh:118-125 | re-mix | calls `remix.py --gain-match lufs` to sum restored vocal + instrumental | `--gain-match lufs` fixed mode | — | separate `remix.py` under `tools/vocal_restore/` (NOT read — out of the 5 named target files; note in Uncertainties) |
| M-A-T | mastering_tool/vocal_restore.sh:130-133 | optional polish | conditionally chains into vocal_prep.sh above | `VR_VOCALPREP` toggle (default 0/off) | — | — |

## Render block table (part 8 — MAJOR FINDING, outside the originally-listed file set: mastering_tool/tools/chain_dsl/)

Not in the task's "where to look" list, but directly answers the assignment ("what a vocal chain renderer could be assembled from") — a fully generic, already-built, parameterized pedalboard-based chain DSL + renderer exists at `mastering_tool/tools/chain_dsl/`. Flagged here because it is the single most load-bearing find of this inventory.

| repo | file:line | function | what it does to audio | parameters accepted | hardcoded constants | library |
|---|---|---|---|---|---|---|
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:23-27 | `HPF` dataclass | param container for highpass stage | `freq` (Hz, default 80.0), `slope` (dB/oct, default 12 — NOTE: declared but NOT read by pedalboard_exec.py, see below), `bypass` (bool, default True i.e. OFF by default) | slope field exists in schema but pedalboard_exec.py ignores it (pedalboard.HighpassFilter has no slope arg — ALWAYS 12dB/oct regardless of this field) | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:30-40 | `EQBand`/`EQ` dataclasses | param container for a list of parametric peak bands | `freq` (Hz, default 1000.0), `gain` (dB, default 0.0), `q` (default 1.0); `EQ.bands: List[EQBand]`, `EQ.bypass` (default True) | — | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:43-49 | `Deesser` dataclass | param container | `freq` (Hz, default 6800.0), `threshold_db` (default -28.0 — NOTE declared but NOT used by pedalboard_exec, see below), `ratio` (default 4.0), `width_octaves` (default 0.5), `bypass` (default True) | — | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:52-60 | `Compressor` dataclass | param container | `threshold_db` (default -18.0), `ratio` (default 3.0), `attack_ms` (default 5.0), `release_ms` (default 80.0), `knee_db` (default 4.0 — NOTE declared but NOT read by pedalboard_exec, pedalboard.Compressor has no knee arg), `makeup_db` (default 0.0), `bypass` (default True) | — | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:63-66 | `Clipper` dataclass | param container | `drive_db` (default 2.0), `bypass` (default True) | — | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:69-74 | `Limiter` dataclass | param container | `ceiling_db` (default -1.0), `lookahead_ms` (default 20.0 — NOTE declared but NOT read by pedalboard_exec, pedalboard.Limiter has no lookahead arg), `release_ms` (default 100.0), `bypass` (default True) | — | — |
| M-A-T | mastering_tool/tools/chain_dsl/schema.py:77-85 | `Chain` dataclass | top-level container: sample_rate + all 6 stages above, with to/from YAML/JSON and a lossy `to_masterbus_dict()`/`from_masterbus_dict()` bridge to the Rust-consumed flat `chain.json` (the exact file at mastering_tool/chain.json read earlier) | `sample_rate` (Hz, default 48000.0) | ALL stage `bypass` fields default **True** (every stage OFF unless explicitly enabled) — this is the "conditionally disabled, never deleted" pattern referenced in AGENTS.md | — |
| M-A-T | mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:29-34 | `_band_to_peak_filter` | one EQBand -> pedalboard.PeakFilter | `band.freq/gain/q` passthrough | — | pedalboard.PeakFilter |
| M-A-T | mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:37-48 | `_deesser_to_filters` | **approximates** a deesser as a STATIC narrow peak-cut (not dynamic/sidechain) — explicit code comment: "Pedalboard has no dedicated deesser built-in... narrow peak cut at the sibilance frequency as a transparent, honest fallback" | reads `deesser.width_octaves` (-> q = 1/max(width_octaves,0.1)) and `deesser.ratio` (-> gain_db = -6.0*(1-1/max(ratio,1.0))); `deesser.threshold_db` is IGNORED (never referenced) | -6.0 dB scale constant in the gain formula; min width_octaves clamp 0.1; min ratio clamp 1.0 | pedalboard.PeakFilter |
| M-A-T | mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:51-91 | `build_pedalboard` | assembles a `pedalboard.Pedalboard` from a `Chain`: HPF -> EQ bands -> deesser(fallback) -> Compressor(+makeup Gain) -> Distortion(clip) -> Limiter, EACH STAGE SKIPPED IF `bypass=True` | entire `Chain` object | order is FIXED: hpf, eq, deesser, comp(+makeup), clip, limit — not reorderable | pedalboard.HighpassFilter, PeakFilter, Compressor, Gain, Distortion, Limiter |
| M-A-T | mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:94-113 | `render` | runs `board(audio, sr)` — the actual apply-to-numpy-array render call | `chain`, `audio: (n_samples, n_channels) float32` (mono ok as (n,) or (n,1)), `sample_rate` override | — | pedalboard |
| M-A-T | mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:116-133 | `render_file` | reads WAV via soundfile (samples-first, dtype float32), asserts file sr == chain.sample_rate (raises ValueError on mismatch — no auto-resample), renders, writes WAV | `input_path`, `output_path`, `sample_rate` override | — | soundfile + pedalboard |
| M-A-T | mastering_tool/tools/chain_dsl/executors/masterbus_exec.py:12-22 | `to_masterbus_config` / `render_json` | NOT an audio render — serializes Chain to the flat chain.json for a SEPARATE Rust renderer (`open_DAW/daw-engine/src/master_bus.rs`, not read — out of Python/pedalboard scope) | `chain` | — | n/a (JSON only) |

**I/O contract note (feeds Q4):** `pedalboard_exec.render()`/`render_file()` use **(n_samples, n_channels)** — samples-first — matching `soundfile`'s native read/write shape and OPPOSITE of `music_toolshop_v2/pipeline/*.py`'s (channels, samples) convention. `render_file` does NOT auto-resample on sr mismatch (hard ValueError), unlike `format_norm.normalize()` which does resample.

Confirmed via grep (not exhaustive read) that a Rust master bus exists at `open_DAW/daw-engine/src/master_bus.rs` consuming the same `chain.json` shape — a SECOND, non-Python renderer for the identical DSL. Not verified further (out of scope: not Python/pedalboard, and open_DAW was explicitly flagged "Parked" in Music-AI-Toolshop/AGENTS.md).

## Q1 pedalboard vocabulary + install check

### Install check (actually run, not assumed)

Command run: `python -c "import pedalboard; print(pedalboard.__version__)"`

- Music-AI-Toolshop venv `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe` -> **0.9.24** (imported successfully, no error)
- music_toolshop_v2 venv `D:\Projects\music_toolshop_v2\.venv\Scripts\python.exe` -> **0.9.24** (imported successfully, no error)

Both venvs have the identical pedalboard version installed. pedalboard is a hard runtime dependency in music_toolshop_v2/pipeline/*.py (unconditional top-level imports) but an OPTIONAL soft dependency in Music-AI-Toolshop/toolshop/remix_adapter.py, which wraps the import in try/except and gates all pedalboard-using functions behind `_require_deps()` (remix_adapter.py:44-48, `_HAS_PEDALBOARD` flag). Same pattern in mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:10-16 (`_HAS_PEDALBOARD`, raises RuntimeError via `_require_pedalboard()` if missing).

### Plugin classes actually imported and used (renderable vocabulary)

| class | repo:file:line (import) | used at |
|---|---|---|
| `Pedalboard` | music_toolshop_v2/pipeline/corrective_eq.py:11; ambience.py:26; mastering.py:106 (local import); dynamics.py:18; Music-AI-Toolshop/toolshop/remix_adapter.py:44 (bare `import pedalboard`, used as `pedalboard.Pedalboard`); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:11 | container for every chain below |
| `HighpassFilter` | music_toolshop_v2/pipeline/corrective_eq.py:11; dynamics.py:15; ambience.py:26; saturation.py:94 (local import); Music-AI-Toolshop/toolshop/remix_adapter.py:635; mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py:58 | corrective_eq.py:65,125-128,141,147,153; dynamics.py:158; remix_adapter.py:635; pedalboard_exec.py:56-59 |
| `LowpassFilter` | music_toolshop_v2/pipeline/ambience.py:26 | ambience.py:67 |
| `PeakFilter` | music_toolshop_v2/pipeline/corrective_eq.py:11; saturation.py:127 (local import); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (bare `import pedalboard`, used as `pedalboard.PeakFilter`) | corrective_eq.py:129,135,165-166,200; saturation.py:131; pedalboard_exec.py:30-34,48 |
| `HighShelfFilter` | music_toolshop_v2/pipeline/dynamics.py:16 | dynamics.py:161 |
| `LowShelfFilter` | NOT FOUND -- grepped music_toolshop_v2 for LowShelfFilter, zero matches. The task's example list includes it but it is not actually used anywhere in that repo. Not separately re-grepped across all of Music-AI-Toolshop -- flagged in Uncertainties. | n/a |
| `NoiseGate` | music_toolshop_v2/pipeline/dynamics.py:17 | dynamics.py:159 |
| `Compressor` | music_toolshop_v2/pipeline/dynamics.py:14; Music-AI-Toolshop/toolshop/remix_adapter.py (bare, `pedalboard.Compressor`); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (bare) | dynamics.py:49-54,160; remix_adapter.py:465-471; pedalboard_exec.py:70-75 |
| `Limiter` | music_toolshop_v2/pipeline/mastering.py:106 (local import); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (bare) | mastering.py:111; pedalboard_exec.py:85-88 |
| `Reverb` | music_toolshop_v2/pipeline/ambience.py:26; Music-AI-Toolshop/toolshop/remix_adapter.py (bare) | ambience.py:65; remix_adapter.py:446-452 |
| `Delay` | Music-AI-Toolshop/toolshop/remix_adapter.py (bare) | remix_adapter.py:454-460 |
| `Gain` | Music-AI-Toolshop/toolshop/remix_adapter.py (bare); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (bare) | remix_adapter.py:462; pedalboard_exec.py:78 |
| `Distortion` | Music-AI-Toolshop/toolshop/remix_adapter.py (bare); mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (bare) | remix_adapter.py:473; pedalboard_exec.py:81 (used as a "clipper" stage in the chain DSL, not literal distortion FX) |
| `pedalboard.time_stretch` (function, not a Plugin class) | Music-AI-Toolshop/toolshop/remix_adapter.py:424 | remix_adapter.py:424-430 -- Rubber Band tempo/pitch stretch |

**Renderable vocabulary (confirmed in use, both repos combined):** Pedalboard, HighpassFilter, LowpassFilter, PeakFilter, HighShelfFilter, NoiseGate, Compressor, Limiter, Reverb, Delay, Gain, Distortion, plus the free function `pedalboard.time_stretch`. No dedicated Deesser, Chorus, Phaser, Convolution, or LowShelfFilter plugin is used anywhere -- the one "deesser" that exists in the chain_dsl executor (pedalboard_exec.py:37-48) is an explicit static PeakFilter approximation, documented in-code as such.

### Adjacent but out-of-scope: toolshop/voice_effects_adapter.py
`D:\Projects\Music-AI-Toolshop\toolshop\voice_effects_adapter.py` is a DETECTION module only -- every public function is `detect_*` (detect_reverb, detect_pitch_shift, detect_formant_shift, detect_compression, detect_eq, detect_distortion, detect_chorus, detect_autotune, detect_deessing, detect_vocoder, detect_noise_gate, detect_delay -- lines 85-1029) plus `analyze_voice`/`print_voice_summary`. It measures/classifies effects already present in audio; it does not import or use pedalboard and does not apply any parameter to audio. Listed here only to confirm it is NOT a render block despite the suggestive name and despite one of its detectors sharing a name ("Chorus/Doubling", line 1169) with a pedalboard plugin class that is otherwise unused in both repos.

## Q2 hardcoded vs parameterised

### `corrective_eq._vocal_chain()` -- FULLY HARDCODED, no profile input at all

Quote, `music_toolshop_v2/pipeline/corrective_eq.py:145-148`:
```python
def _vocal_chain() -> Pedalboard:
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=100.0),
    ])
```
Takes zero arguments. The 100.0 Hz cutoff cannot be changed without editing this function. Contrast: the *caller* `apply_eq()` (corrective_eq.py:207-261) DOES accept a `profile: dict | None` parameter, but that profile is only consulted by the separate `_genre_band_chain(profile)` helper (corrective_eq.py:182-204), which adds an ADDITIONAL PeakFilter chain on top of whatever `_vocal_chain()` (or the other stem chains) already hardcoded -- it never modifies or replaces the 100.0 Hz value inside `_vocal_chain()` itself. So: the base per-stem EQ is 100% hardcoded; a profile can only ADD extra bands via `profile["frequency"]["bands"]`, e.g.:

Quote, `corrective_eq.py:190-200`:
```python
    bands = profile.get("frequency", {}).get("bands")
    if not bands:
        return None
    filters = []
    for name, gain_db in bands.items():
        if gain_db == 0.0:
            continue
        hz = float(name.replace("_hz", ""))
        filters.append(
            PeakFilter(cutoff_frequency_hz=hz, gain_db=float(gain_db), q=_OCTAVE_Q)
        )
```
Q is ALWAYS `_OCTAVE_Q = sqrt(2.0)` (corrective_eq.py:179) regardless of profile -- only freq/gain are profile-controlled, Q never is.

### `dynamics.vocal_chain()` -- FULLY HARDCODED, no profile input at all

Quote, `music_toolshop_v2/pipeline/dynamics.py:144-164`:
```python
def vocal_chain(audio: np.ndarray, sr: int) -> np.ndarray:
    """Apply the 5-step vocal processing chain.
    ...
    """
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),
        NoiseGate(threshold_db=-55.0, attack_ms=20.0, release_ms=250.0),
        Compressor(threshold_db=-22.0, ratio=2.5, attack_ms=15.0, release_ms=200.0),
        HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=3.0),
    ])
```
Signature is `vocal_chain(audio, sr)` -- literally no `profile` parameter exists. Every one of the 4 stages' numeric values (80.0, -55.0/20.0/250.0, -22.0/2.5/15.0/200.0, 4000.0/3.0) is a Python literal in the function body. The caller `apply_dynamics()` DOES accept `profile: dict` (dynamics.py:167-173) and even carries a `target: str = "streaming"` parameter, but for `stem_type == "vocal"` it dispatches straight to `vocal_chain(x, sr)` (dynamics.py:202) -- `profile` and `target` are silently ignored on that branch. Quote, dynamics.py:199-202:
```python
    x = audio.astype(np.float32)

    if stem_type == "vocal":
        x = vocal_chain(x, sr)
```
`profile` is used in the function signature's type but never referenced in the body for ANY stem_type branch (drums/bus/bass/other/else all use hardcoded compress() literals too, dynamics.py:203-214) -- `apply_dynamics`'s `profile` argument is entirely dead/unused across the whole function.

### `saturation.resolve_saturation_params()` -- the ONE genuinely profile-driven function among the three

Quote, `music_toolshop_v2/pipeline/saturation.py:206-223`:
```python
    spec = _PARAM_SPECS[role]
    sat_block = (profile or {}).get("saturation") or {}

    resolved: dict = {}
    for arg_name, (profile_key, default) in spec.items():
        if profile_key in sat_block:
            resolved[arg_name] = {
                "value": sat_block[profile_key],
                "source": "profile",
                "profile_key": profile_key,
            }
        else:
            resolved[arg_name] = {
                "value": default,
                "source": "default",
                "profile_key": profile_key,
            }
    return resolved
```
This is the only one of the three functions that is genuinely parameterised from a `profile: dict` -- it reads `profile["saturation"][<namespaced key>]` (e.g. `exciter_amount_vocal`, `sub_f0`, `drive_db_drums` -- full key table at saturation.py:153-173) and falls back to a built-in default per-key when the profile omits it, explicitly recording `source: "profile"` vs `source: "default"` for provenance rather than silently blending them. However this function itself does not touch audio -- it only resolves numbers; the actual DSP call (`sub_bass_psychoacoustic`/`exciter`/`saturate_tanh`) in `apply_saturation()` (saturation.py:263-287) then uses `resolved[...]["value"]`.

### What a `profile: dict` argument is allowed to control, repo-wide (from the three files above plus mastering.py/club_master.py read earlier)
- `corrective_eq.py`: ONLY `profile["frequency"]["bands"]` (dict of `"<freq>_hz": gain_db`) -- adds PeakFilter bands, Q fixed at sqrt(2). Cannot change HPF cutoffs, cannot change the base stem chains, cannot change vocal_pocket or deesser constants.
- `dynamics.py`: `apply_dynamics`'s `profile` parameter exists in the signature but is DEAD CODE -- confirmed by reading every branch (dynamics.py:199-216); no dynamics values are ever profile-driven anywhere in this file.
- `saturation.py`: `profile["saturation"]["<namespaced_key>"]` -- 8 documented keys (sub_f0, sub_boost_db, exciter_amount_vocal, exciter_freq_min_vocal, drive_db_drums, exciter_amount_master, exciter_freq_min_master, drive_db_master), all resolved through the single `resolve_saturation_params()` function.
- `mastering.py`: `apply_mastering`'s `profile["streaming"]["lufs"/"true_peak_dbtp"]` and `profile["club"]["lufs_range"/"true_peak_dbtp"]` (mastering.py:147-155) -- genuinely profile-driven for LUFS/TP targets.
- `club_master.py`: `profile["stereo"]["mono_below_hz"]` (default 120.0, club_master.py:79) and the saturation "bass" role via `resolve_saturation_params` (club_master.py:93-98) -- genuinely profile-driven for those two things only; the side-gain x1.5 and glue-compression settings remain hardcoded (club_master.py:84, 101-102).

**Bottom line: of the three functions the task specifically asks about, only `resolve_saturation_params()` reads from a measured/profile source. `_vocal_chain()` (EQ) and `vocal_chain()` (dynamics) are both 100% hardcoded constants with no profile hook at all**, despite `apply_dynamics()`'s outer signature suggesting otherwise.

## Q3 voice_profile consumers

### Grep run (verbatim commands and results)

`grep -rn "voice_profile" D:\Projects\music_toolshop_v2\pipeline\` -> **zero matches** (empty output; the pipeline/ directory that contains every render block in this inventory never mentions voice_profile in any form).

`grep -rn "voice_profile" D:\Projects\Music-AI-Toolshop\toolshop\` -> **zero matches**.

Broader repo-wide grep for `voice_profile|voice_profiles|measure_voice_profile` found matches only in:
- `music_toolshop_v2/analysis/voice_profile.py` (the measurer itself -- defines `measure_voice_profile()`, `validate_profile()`, reads `voice_profiles/schema.json` at line 218)
- `music_toolshop_v2/_remeasure_nikola.py` and `nikola-remeasure.txt` (a standalone one-off script that calls `measure_voice_profile()` and writes `voice_profiles/nikola.json` -- not part of any pipeline)
- `music_toolshop_v2/tests/test_voice_profile.py` (unit tests of the measurer only)
- `music_toolshop_v2/voice_profiles/nikola.json` and `voice_profiles/schema.json` (the data files themselves)
- Various `music_toolshop_v2/ORCHESTRATION/*.md` planning/handoff docs (not code)
- In Music-AI-Toolshop, matches are ONLY inside this task's own output files and a handoff doc -- no source code.

### Consumer list: EMPTY

**No render/pipeline code in either repo reads `voice_profiles/*.json` or calls `measure_voice_profile()` for anything other than producing/testing the measurement itself.** `corrective_eq.py`, `dynamics.py`, `saturation.py`, `mastering.py`, `club_master.py`, `ambience.py`, `format_norm.py`, `remix_adapter.py`, and `vocal_swap/mix.py` -- every render block in this inventory -- take a `profile: dict` (when they take one at all) sourced from `genre_profiles/*.json`, never from `voice_profiles/*.json`. The `profile` argument's `dict` shape (frequency.bands, saturation.*, streaming.*, club.*, stereo.mono_below_hz) matches `genre_profiles/schema.json`, not `voice_profiles/schema.json`.

This is independently confirmed by the project's own adversarial-review doc, `music_toolshop_v2/ORCHESTRATION/adversarial/v3_roadmap.md:149`:
> "`voice_profiles/nikola.json` is an 851-line measurement module's output that no processing code opens."

and `music_toolshop_v2/ORCHESTRATION/v21/X3_crest_and_tree.md:95` flags the one existing profile (`nikola.json`) as measured from a clipping source and **recommended excluded from commit** -- i.e. even the sole data file that exists is flagged low-trust/provisional, and per the grep above nothing reads it regardless.

**Implication for the orchestrator:** a "vocal chain renderer" that wants to take a measured singer's voice profile and turn it into render parameters would have to build that consumer from scratch -- the measurement side (`analysis/voice_profile.py`) exists and is tested, but the render side has no wiring to it anywhere in either repo today.

## Q4 I/O contract and convention flips

### Ground truth on pedalboard own shape handling (empirically verified, not assumed)

Ran on Music-AI-Toolshop venv (pedalboard 0.9.24):
```
board = pedalboard.Pedalboard([pedalboard.Gain(gain_db=6.0)])
board(np.random.rand(2, 1000).astype(np.float32)*0.1, 44100).shape  -> (2, 1000)   # channels-first in/out
board(np.random.rand(1000, 2).astype(np.float32)*0.1, 44100).shape -> (1000, 2)   # samples-first in/out
```
The installed pedalboard.Pedalboard.process docstring (queried directly from the package) confirms this is by design:
"The layout of the provided input_array will be automatically detected, assuming that the smaller dimension corresponds with the number of channels. If the number of samples and the number of channels are the same, each Plugin object will use the last-detected channel layout until reset is explicitly called (as of v0.9.9)."

So pedalboard itself is shape-agnostic for real audio (samples always much greater than 2 channels) and preserves whatever orientation it is given. The two conventions below can BOTH feed pedalboard correctly on their own -- the actual risk is at boundaries between modules that disagree, and in non-pedalboard code (soundfile, librosa, scipy) which is NOT shape-agnostic.

### Per-module I/O contract

| module | shape convention | sample rate | dtype | evidence |
|---|---|---|---|---|
| music_toolshop_v2/pipeline/corrective_eq.py | (channels, samples) -- to_mid_side requires exactly (2, N) and raises ValueError otherwise; apply_eq accepts (channels, samples) or (samples,) mono, adds a leading axis for mono | caller-supplied sr: int, no fixed default in this file | float32 output; float64 used internally in to_mid_side/from_mid_side (line 27,41) then cast back to float32 (line 32,46) | corrective_eq.py:21-32 docstring "Convert stereo (2, N)"; corrective_eq.py:214 "audio: Input audio (channels, samples) or (samples,) float" |
| music_toolshop_v2/pipeline/dynamics.py | (channels, samples) or (samples,) per every function docstring | caller-supplied sr | float32 (.astype(np.float32) at every function entry, e.g. dynamics.py:88,163,199) | dynamics.py:38 "audio: Input audio (channels, samples) or (samples,) float32" |
| music_toolshop_v2/pipeline/saturation.py | (channels, samples), with _to_2d/_to_mono helpers (saturation.py:19-31) that add a leading axis for 1-D mono input | caller-supplied sr | float32 | saturation.py:19-23 _to_2d: "Ensure shape (channels, samples). 1-D mono -> (1, N)" |
| music_toolshop_v2/pipeline/mastering.py | (channels, samples), _to_2d helper identical pattern (mastering.py:34-38) | caller-supplied sr | float64 internally for gain-staging precision (mastering.py:78, dtype=np.float64), cast to float32 on return (mastering.py:124) | mastering.py:34-38 _to_2d docstring identical to saturation.py's |
| music_toolshop_v2/pipeline/ambience.py | (channels, samples) or (samples,) | caller-supplied sr | float32 | ambience.py:44 "vocal: Audio array (channels, samples) or (samples,)" |
| music_toolshop_v2/pipeline/club_master.py | (2, samples) enforced by _to_stereo (club_master.py:36-43, duplicates mono to stereo, always returns exactly 2 leading channels) | caller-supplied sr | float32 | club_master.py:36 "Ensure shape (2, N). Mono (N,) -> duplicate to stereo" |
| music_toolshop_v2/pipeline/format_norm.py | Internal working array is (channels, samples) (.reshape(-1, channels).T, format_norm.py:60) but the WAV FILE ON DISK is written samples-first because soundfile requires that (sf.write(..., audio.T, ...), format_norm.py:71, explicit comment "soundfile expects (samples, channels) -- transpose from (channels, samples)") | target_sr param, default 44100 | float32, normalized to [-1,1] via raw / max_val (format_norm.py:58-60) | format_norm.py:70 comment is the module's own acknowledgment of the flip at the disk boundary |
| Music-AI-Toolshop/toolshop/remix_adapter.py | DUAL, with EXPLICIT conversion helpers -- internal/at-rest arrays and soundfile I/O are (samples, channels); pedalboard calls require (channels, samples), so _to_channels_first (remix_adapter.py:383-389) and _to_samples_first (remix_adapter.py:392-398) convert at every pedalboard call site (_stretch_segment:423,434; _apply_fx:486,488) | not fixed in this file -- sr threaded through from caller/detected BPM/key logic | float32 (_stretch_segment casts at line 412-413) | remix_adapter.py:384 "Convert (samples, channels) to (channels, samples) for pedalboard"; line 393 "Convert (channels, samples) to (samples, channels) for soundfile" -- the module's own comments name the flip explicitly |
| Music-AI-Toolshop/toolshop/remix_adapter.py::combine_stems | reads stems via sf.read(..., always_2d=True) -> (samples, channels), then explicitly .T to (channels, samples) "for pedalboard" (line 630 comment) before HPF, then writes back via _to_samples_first(combined) (line 657) | reads per-file sr from soundfile, uses first stem's sr as reference, SKIPS (does not resample) any stem whose sr differs (remix_adapter.py:623-629, logs a warning and continues) -- silent-drop-on-mismatch, not a resample | float32 (.astype(np.float32), line 640) | remix_adapter.py:630 "data = data.T  # (channels, samples) for pedalboard" |
| Music-AI-Toolshop/toolshop/vocal_swap/mix.py | (samples, channels) throughout -- OPPOSITE of every music_toolshop_v2/pipeline/*.py module above. load_audio explicitly transposes librosa's native channels-first output to samples-first (mix.py:126-135, comment "librosa is channels-first; we work samples-first"). highpass filters axis=0 (mix.py:207, the samples axis in this convention). duck broadcasts gain[:, None] (mix.py:245, again samples-axis-0). This file contains NO pedalboard usage anywhere -- confirmed by earlier full read of the file -- so it never needs a channels-first conversion at all; it stays samples-first end-to-end (scipy + pyloudnorm + soundfile all accept samples-first natively) | fixed module constant MIX_SR = 44100 (mix.py:33), used as the default for every function's sr param -- but every function still ACCEPTS a different sr if the caller overrides it, so it is a default not a hard requirement | float32 for audio arrays; float64 promoted internally in integrated_lufs/highpass/_envelope for precision then cast back | mix.py:130 "audio = y.T  # librosa is channels-first; we work samples-first"; mix.py:118-121 docstring "Everything downstream assumes (n, 2)" |
| mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py | (n_samples, n_channels) -- matches soundfile's native read/write shape, explicitly documented, NO shape-conversion helper (relies on pedalboard's auto-detection, verified above, plus every real file naturally has samples much greater than 2 so the heuristic is safe) | chain.sample_rate (schema default 48000.0) OR override param; render_file (pedalboard_exec.py:126-131) hard-fails with ValueError if the input WAV's sample rate does not match -- no auto-resample, unlike format_norm.normalize() which DOES resample | float32 (sf.read(..., dtype="float32"), pedalboard_exec.py:127) | pedalboard_exec.py:103 "audio: (n_samples, n_channels) float32 array" |
| mastering_tool/*.sh (ffmpeg/LV2 shell chain) | N/A -- operates on WAV files on disk throughout, ffmpeg/LV2 handle their own internal buffer layout; no numpy array boundary exists in this part of the pipeline. Sample rate is whatever the source file has (48000 seen in chain.json; 44100/48000 both handled explicitly in stage_clip_limit.sh:47, OS=192000 if SR==48000 else 176400) | file's native sr, read via ffprobe per-call (stage_clip_limit.sh:46, lv2_stage.sh) | pcm_f32le intermediate WAVs throughout (-c:a pcm_f32le on every stage), 16-bit + dither only at the final deliverable stage (master_pipeline_v3.sh:141) | stage_clip_limit.sh:46-47 |

### Convention flips flagged (every place the convention changes)

1. music_toolshop_v2/pipeline/*.py (channels-first) vs Music-AI-Toolshop/toolshop/vocal_swap/mix.py (samples-first) -- these are the two repos' respective "vocal chain" building blocks and they use OPPOSITE array conventions. Any renderer assembled from both would need an explicit transpose at the boundary. Neither module currently imports or calls the other.
2. Within Music-AI-Toolshop/toolshop/remix_adapter.py itself -- the file's own at-rest/soundfile convention is (samples, channels) but every pedalboard call requires an explicit transpose-based conversion via _to_channels_first/_to_samples_first. This is handled correctly at every site checked (lines 423/434, 486/488, 630/657) but is a manual convention the next contributor must remember to replicate for any NEW pedalboard call added to this file.
3. mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py (samples-first, no conversion helper) vs music_toolshop_v2/pipeline/*.py (channels-first, also no conversion helper needed internally) -- both work in isolation because pedalboard auto-detects orientation (verified above), but if an array from one module were ever passed directly into the other module's function (e.g. passing a club_master.py (2, N) array into chain_dsl.render() which expects (N, 2)) the result would still "work" at the pedalboard call (auto-detected) UNLESS that same array were then handed to a non-pedalboard function (scipy sosfiltfilt with axis=0, soundfile write, pyloudnorm) that is NOT shape-agnostic -- those would silently process the wrong axis. This is a real integration hazard, not just documentation noise, precisely because pedalboard's tolerance can mask a mismatch until it hits a strict function downstream.
4. format_norm.py's internal (channels, samples) vs its own on-disk WAV (samples, channels) -- handled with one explicit transpose (format_norm.py:71) and a comment; consistent with the rest of pipeline/*.py's pattern of "channels-first in memory, transpose only at the soundfile boundary."
5. remix_adapter.py::combine_stems sample-rate handling is NOT a convention flip but a related I/O-contract gap: mismatched-sr stems are silently skipped (logged warning + continue, remix_adapter.py:625-629) rather than resampled, unlike format_norm.normalize() which actively resamples to target_sr. A caller combining stems of different sample rates loses audio silently rather than getting a resampled result.

## Uncertainties

- mastering_tool/vocal_prep.sh:25,27 declares DEESSER_INTENSITY and DEESSER_MODE env vars but they are never referenced in the actual FILTER_CHAIN (line 60-66) -- the de-ess stage is a static EQ cut regardless of these two vars. Similarly SATURATION_DRIVE_DB (line 30) is declared and echoed (line 42) but never used inside FILTER_CHAIN -- the asoftclip threshold is a fixed 0.794 literal. These look like dead/aspirational parameters rather than functioning knobs -- flagged, not fixed, since I did not find a second code path that does read them (verified by reading the whole 119-line file).
- mastering_tool/tools/chain_dsl/schema.py declares HPF.slope, Deesser.threshold_db, Compressor.knee_db, and Limiter.lookahead_ms, but pedalboard_exec.py's build_pedalboard() never reads any of these four fields when constructing the actual pedalboard plugins (pedalboard.HighpassFilter/Compressor/Limiter have no matching constructor args). They survive only in the masterbus_exec.py JSON serialization path (to_masterbus_dict does carry limit_lookahead_ms). Not verified whether the Rust master_bus.rs consumer (open_DAW/daw-engine/src/master_bus.rs) actually implements these -- that file was not read (out of scope: non-Python, and open_DAW is flagged "Parked" in Music-AI-Toolshop/AGENTS.md).
- mastering_tool/vocal_restore.sh delegates to `tools/vocal_restore/restore.py` and `tools/vocal_restore/remix.py` (lines 109-125) -- neither file was opened in this pass (outside the five explicitly named target files). Their exact parameter surface for DeepFilterNet3/VoiceFixer/Apollo/AudioSR is therefore "not verified" -- only the shell-level toggles (VR_DEROOM etc.) were confirmed.
- mastering_tool/mix_phase_gate.sh (99 lines) was located but not read in detail -- title suggests a phase-correlation gate (likely measurement, paralleling toolshop/premaster.py's gates 1-2), not a render stage. Not verified.
- LowShelfFilter/Chorus/Phaser/Convolution pedalboard classes: confirmed absent (zero matches) via targeted grep across both repos' *.py files. This is a negative-result grep, not an exhaustive read of every file in either repo -- a currently-unused import in a file outside toolshop/, mastering_tool/, and pipeline/ cannot be fully ruled out, but none of the explicitly-scoped files use them.
- mastering_tool/pipelines/*.sh (~30 files) are one-off per-track scripts, not generic stage scripts -- listed by filename only, not individually read. If the orchestrator needs per-track calibration examples (e.g. actual PREGAIN_DB values used in production), those live here and were not extracted.
- Did not verify whether Music-AI-Toolshop's toolshop/ has any OTHER pedalboard call sites beyond remix_adapter.py -- the grep in Q1 was repo-wide (`Grep pattern="from pedalboard import|import pedalboard|pedalboard\.[A-Z]\w+" path=Music-AI-Toolshop glob=*.py`) and returned matches only in remix_adapter.py and mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py, so this is believed complete, but stated here for the record rather than silently assumed.
