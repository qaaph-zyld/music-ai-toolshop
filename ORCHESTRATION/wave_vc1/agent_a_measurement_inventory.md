# Agent A — Measurement Inventory (Wave VC1)

Status: COMPLETE.

Scope: voice_effects_adapter.py (12 detectors + analyze_voice), voice_profile.py (measure_voice_profile + helpers), premaster.py (six gates).

## Inventory table

Legend: DSP-settable = a number you could dial into a plugin control (not just a confidence/verdict). "type" is the literal Python type of the value as constructed in the return dict.

### File 1: `toolshop/voice_effects_adapter.py`

Global dep gates: `_HAS_LIBROSA` (voice_effects_adapter.py:24-32, guards module import; `_require_librosa()` at :50-55 raises RuntimeError, called only from `_load_audio` :65 and `analyze_voice` :1115 — the 12 detector functions themselves do NOT call `_require_librosa()` and will throw `NameError`/`AttributeError` if called directly without librosa installed, since they use bare `librosa.*`/`np.*` calls unconditionally), `_HAS_PARSELMOUTH` (:34-40), `_HAS_CREPE` (:42-47). Dead import: `scipy_kurtosis` (:28) is imported but never referenced anywhere in the file.

| source function | field name | type | unit | settable DSP parameter? | consuming plugin/param | gated behind optional dep? | degrades/None when dep missing? |
|---|---|---|---|---|---|---|---|
| detect_reverb (85-179) | effect | str "reverb" | — | no (label) | — | no | — |
| detect_reverb | confidence | float 0.0-0.95 | unitless | no (verdict) | — | no | — |
| detect_reverb | params.estimated_rt60_seconds | float | seconds | **yes** — RT60 decay time | reverb "decay time" knob | no (pure librosa/numpy) | omitted from dict if slope not negative enough (137/157, conditional key) |
| detect_reverb | params.type | str "hall"\|"room" | — | no (label bucket) | — | no | only set when rt60>0.5 (161/165) |
| detect_reverb | evidence | list[str] | — | no | — | no | — |
| detect_pitch_shift (182-271) | effect | str | — | no | — | no | — |
| detect_pitch_shift | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_pitch_shift | params.detected_f0_hz | float | Hz | measurement, not a "shift" param itself | reference pitch | no | omitted if f0_median None/<50 (220-223) |
| detect_pitch_shift | params.formants | dict{F1,F2,F3} | Hz | measurement (formant freqs), not directly a "shift amount" | — | **yes, parselmouth** (226) | key omitted entirely if parselmouth missing (266-269 only appends an evidence string) |
| detect_pitch_shift | params.expected_f0_range | [float,float] | Hz | no (reference range, heuristic) | — | requires parselmouth (nested under same block) | omitted if parselmouth missing |
| detect_pitch_shift | params.estimated_semitones | **str** e.g. `"-3.2"` or `"+3.2"` (246-248, 256-258) | semitones | borderline — value is quantitative (semitone shift) but stored as a **formatted string with sign prefix, not a float/int** | pitch-shift plugin "semitones" control, but needs str→float parse first | requires parselmouth | omitted unless F0 is outside expected range AND parselmouth present |
| detect_pitch_shift | evidence | list[str] | — | no | — | no | — |
| detect_formant_shift (356-431) | effect | str | — | no | — | no | — |
| detect_formant_shift | confidence | float 0.0-0.95 (=anomaly_score) | unitless | no | — | no | — |
| detect_formant_shift | params.F2_F1_ratio | float | unitless ratio | no (ratio anomaly signal, not a shift amount in Hz/semitones/%) | — | **yes, parselmouth**; whole function returns confidence 0.0 + evidence note if missing (369-373) | returns early, empty params, if parselmouth absent |
| detect_formant_shift | params.F3_F2_ratio | float | unitless ratio | no | — | parselmouth | only if F3 present (394-402) |
| detect_formant_shift | params.F1_variability_cv | float | unitless (coefficient of variation) | no | — | parselmouth | only if >10 f1 frames extracted (417-419), wrapped in try/except that swallows all errors (405-425) |
| detect_formant_shift | evidence | list[str] | — | no | — | — | — |
| detect_compression (434-504) | effect | str | — | no | — | no | — |
| detect_compression | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_compression | params.crest_factor_db | float | dB | measurement, not itself a compressor control | informs ratio/threshold choice | no | omitted only if rms_global<1e-10 (448-449, early return before any params set) |
| detect_compression | params.peak_amplitude | float | linear amplitude (0-1 abs sample peak) | no | — | no | same as above |
| detect_compression | params.rms_amplitude | float | linear amplitude | no | — | no | same as above |
| detect_compression | params.dynamic_range_db | float | dB (p95-p5 of RMS-dB) | no (a measurement, not a compressor control value) | — | no | omitted if <10 non-silent RMS-dB samples (461-465) |
| detect_compression | params.rms_variance_db2 | float | dB^2 | no | — | no | same conditional as dynamic_range_db |
| detect_compression | **params.estimated_ratio** | **str** — one of `"8:1+"`, `"4:1"`, `"2:1"` (477, 483, 489) | ratio notation | **NO — discrete bucket string, not a continuous number.** No threshold, attack, release, or knee is ever produced. | compressor "ratio" knob, but only 3 hardcoded bucket values, never interpolated | no | omitted entirely if crest_factor_db >= 14 (no `elif` branch below 14, so key absent) |
| detect_compression | evidence | list[str] | — | no | — | — | — |
| detect_eq (507-584) | effect | str "eq_filtering" | — | no | — | no | — |
| detect_eq | confidence | float 0.0-0.95 (additive, not clamped except final min(0.95,...) at 580) | unitless | no | — | no | — |
| detect_eq | params.spectral_centroid_hz | float | Hz | no (global descriptor, not a band) | — | no | always present |
| detect_eq | params.spectral_rolloff_hz | float | Hz | no | — | no | always present |
| detect_eq | params.high_pass_detected | bool | — | no (flag) | — | no | only present if hp_diff>20dB (540-546) |
| detect_eq | **params.hp_cutoff_estimate_hz** | **str, hardcoded literal `"~150Hz"`** (543) | — | **NO — not measured at all.** Always the same literal string regardless of actual audio; the "150Hz" is not derived from any computed cutoff frequency. | HPF cutoff knob (if it were real) | no | present only when high_pass_detected is True |
| detect_eq | params.low_pass_detected | bool | — | no (flag; no `lp_cutoff_estimate_hz` counterpart exists at all) | — | no | only if lp_diff>35dB (552-557) |
| detect_eq | params.presence_boost_db | float | dB | partial — it's a magnitude (boost amount) but has no center-frequency/Q, so not a full band definition | EQ band gain (if freq/Q were also known) | no | only if presence_boost>5dB (567-571) |
| detect_eq | params.spectral_flatness | float 0-1 | unitless | no | — | no | always present |
| detect_eq | evidence | list[str] | — | no | — | — | — |
| detect_eq | **no band table** | — | — | Confirms Q3: no {freq, gain_db, Q, filter_type} array is ever produced — only single-scalar centroid/rolloff/one presence-boost number and boolean HP/LP flags. | — | — | — |
| detect_distortion (587-679) | effect | str | — | no | — | no | — |
| detect_distortion | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_distortion | params.fundamental_hz | float | Hz | no (informational) | — | no | omitted if voice_range has no bins or fund_amp<1e-10 (604-612, early return) |
| detect_distortion | **params.thd_percent** | float | **%** (THD = sqrt(sum(harm^2))/fund * 100) | **yes-ish — a genuine continuous magnitude** (not a plugin knob per se, but a measurable saturation intensity that could map to a "drive" setting via a calibration curve) | saturation/distortion "amount"/drive (indirectly, needs a mapping curve) | no | only if harmonic_amps non-empty (630-634) |
| detect_distortion | params.even_odd_harmonic_ratio | float | unitless | no (informs saturation *character* — tube vs solid-state — not amount) | could hint at saturation *type* choice | no | only if both odd_amps and even_amps lists non-empty (643-647) |
| detect_distortion | params.clipped_sample_ratio | float | unitless ratio (fraction of samples \|y\|>0.99) | no | — | no | only if clip_ratio>0.001 (669-671) |
| detect_distortion | evidence | list[str] | — | no | — | — | — |
| detect_chorus (682-746) | effect | str "chorus_doubling" | — | no | — | no | — |
| detect_chorus | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_chorus | params.phase_coherence | float 0-1 | unitless | no | — | no | always present |
| detect_chorus | params.bandwidth_cv | float | unitless (coefficient of variation) | no | — | no | always present |
| detect_chorus | **no LFO rate/depth/voices** | — | — | Confirms gap: autocorrelation peak search (709-729) only counts peak *indices* to add +0.3 confidence — the modulation **rate in Hz is computed nowhere and never stored**, nor is depth (ms) or voice count. | — | — | — |
| detect_chorus | evidence | list[str] | — | no | — | — | — |
| detect_autotune (749-837) | effect | str "autotune_pitch_correction" | — | no | — | no | — |
| detect_autotune | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_autotune | params.mean_pitch_deviation_cents | float | cents | no (a deviation measurement, not a "retune speed" ms value a correction plugin exposes) | — | no | always present once >=20 voiced frames (770-772) |
| detect_autotune | params.pitch_jump_ratio | float | unitless (fraction of frame-to-frame diffs >50 cents) | no | — | no | only if any jumps >50 cents exist (798-804) |
| detect_autotune | params.clean_jump_ratio | float | unitless | no | — | no | only if jump_count>0 (811-813) |
| detect_autotune | params.pitch_histogram_peak | float 0-1 | unitless | no | — | no | always present |
| detect_autotune | **no retune-speed value** | — | ms | Confirms Q3: no `_derive`-style ms/attack value produced anywhere for correction speed. | — | — | — |
| detect_autotune | evidence | list[str] | — | no | — | — | — |
| detect_deessing (840-893) | effect | str "de_essing" | — | no | — | no | — |
| detect_deessing | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_deessing | params.sibilant_ratio | float | unitless (sib_energy/below_energy) | no (ratio, not a dB threshold/reduction) | — | no | omitted if below_energy<1e-10 (861-862, early return) |
| detect_deessing | params.sibilant_variability_cv | float | unitless | no | — | no | only if sib_envelope has >10 frames (880-882) |
| detect_deessing | **no threshold_db / freq / reduction_db** | — | — | Confirms gap: no de-esser threshold (dB), target frequency, or gain-reduction-amount is produced. | — | — | — |
| detect_deessing | evidence | list[str] | — | no | — | — | — |
| detect_vocoder (896-953) | effect | str "vocoder" | — | no | — | no | — |
| detect_vocoder | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_vocoder | params.mfcc_temporal_variance | float | unitless (MFCC variance, skipping DC) | no | — | no | always present |
| detect_vocoder | params.harmonic_spacing_cv | float | unitless | no | — | no | only if >3 spectral peaks found (923-928) |
| detect_vocoder | evidence | list[str] | — | no | — | — | — |
| detect_noise_gate (956-1026) | effect | str "noise_gate" | — | no | — | no | — |
| detect_noise_gate | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_noise_gate | params.total_transitions | int | count | no | — | no | always present |
| detect_noise_gate | params.sharp_transitions | int | count | no | — | no | always present |
| detect_noise_gate | params.sharp_ratio | float | unitless | no | — | no | only if total_transitions>0 (997-999) |
| detect_noise_gate | params.noise_floor_variance_db2 | float | dB^2 | no | — | no | only if >10 silent-region frames (1012-1014) |
| detect_noise_gate | **no gate threshold_db/attack/release/hold** | — | — | Confirms gap: despite being named "noise_gate", no threshold (dB), attack, release, or hold time is ever computed/stored — only transition counts and a fixed 40dB-below-peak detection threshold used internally (line 969, never exposed in params). | — | — | — |
| detect_noise_gate | evidence | list[str] | — | no | — | — | — |
| detect_delay (1029-1092) | effect | str "delay_echo" | — | no | — | no | — |
| detect_delay | confidence | float 0.0-0.95 | unitless | no | — | no | — |
| detect_delay | **params.delay_time_seconds** | float | seconds | **yes** | delay plugin "time" knob (seconds) | no | omitted if autocorrelation has no peaks >0.15 height in 50ms-1s search window (1058-1067, early return before this point if <5 frames in search region) |
| detect_delay | **params.delay_time_ms** | float | ms | **yes** (duplicate of seconds*1000) | delay plugin "time" knob (ms) | no | same condition as above |
| detect_delay | params.correlation_strength | float 0-1 | unitless | no | — | no | same condition |
| detect_delay | params.echo_count | int | count | no | — | no | only if >1 autocorrelation peak found (1082-1083) |
| detect_delay | **no feedback_percent / wet_dry_mix** | — | — | Confirms gap: no feedback amount or wet/dry mix ratio is produced even though "Multiple echo peaks" (feedback signature) is detected (1082-1087) — it only bumps confidence, never quantifies feedback %. | — | — | — |
| detect_delay | evidence | list[str] | — | no | — | — | — |
| analyze_voice (1100-1205) | duration_seconds | float | seconds | no (metadata) | — | no | always |
| analyze_voice | sample_rate | int | Hz | no (metadata) | — | no | always |
| analyze_voice | voice_detected | bool | — | no (label) | — | no | always |
| analyze_voice | fundamental_frequency_hz | float or **None** | Hz | measurement | reference pitch | no (uses `_librosa_f0`, pyin) | **None if `_librosa_f0` returns None** (1129,1138) — e.g., <5 voiced pyin frames (274-283) |
| analyze_voice | dependencies_available.{librosa,parselmouth,crepe} | bool | — | no | — | n/a | reports gate state itself |
| analyze_voice | spectral_profile.centroid_hz / bandwidth_hz / rolloff_hz | float | Hz | no (global descriptors) | — | no | always |
| analyze_voice | spectral_profile.flatness | float 0-1 | unitless | no | — | no | always |
| analyze_voice | effects_detected | list[dict] | — | wraps the 12 detector outputs above, sorted by confidence desc (1193) | — | — | on per-detector exception, falls back to a stub dict with confidence 0.0 and an error string in evidence (1182-1190) — degrades per-detector, not module-wide |

### File 2: `D:\Projects\music_toolshop_v2\analysis\voice_profile.py`

Group semantics per docstring (voice_profile.py:56-58): TARGET = "directly settable plugin parameters"; CONSEQUENCE = "inform decisions but are not directly settable"; UNCALIBRATED = "reported" (7 of these are Praat/parselmouth-gated, null-with-reason otherwise). SNR gate (`SNR_THRESHOLD_DB=30.0`, line 33) zeroes out most non-F0 fields when `snr_db < 30` (100-121).

| source function | field name | type | unit | settable DSP parameter? | consuming plugin/param | gated behind optional dep? | returns None/degrades when dep missing? |
|---|---|---|---|---|---|---|---|
| measure_voice_profile / target (85-88) | target.f0_range_hz | [float,float] | Hz | no (descriptive range, not itself a knob) | — | no | always: `_measure_f0` returns (50.0,600.0,None,0.0) fallback if 0 voiced frames (259-260) |
| measure_voice_profile | target.f0_mean_hz | float or None | Hz | no | — | no | None if `_measure_f0` found no voiced frames (86, 259-260 fallback f0_mean=None) |
| measure_voice_profile | **target.hpf_cutoff_hz** | float | Hz | **yes** — via `_derive_hpf_cutoff` (651-653) | HPF plugin cutoff knob | no | always computed (F0-dependent, immune to SNR gate per line 84 comment) |
| measure_voice_profile | **target.formant_ceiling_hz** | float, one of {5000.0, 5500.0} only | Hz | borderline — only 2 discrete hardcoded output values (656-664), not a continuum | formant-shift plugin ceiling param | no | always computed; returns 5000.0 if f0_mean is None (662-663) |
| measure_voice_profile / consequence (91-94) | consequence.snr_db | float | dB | no (diagnostic, gates other fields) | — | no | see `_measure_snr` branches below |
| measure_voice_profile | consequence.voiced_fraction | float 0-1 | unitless | no | — | no | always |
| measure_voice_profile | consequence.spectral_centroid_hz | float | Hz | no | — | no | always |
| measure_voice_profile | consequence.dynamic_range_db | float | dB | no (feeds `_derive_compressor_ratio`, itself not a knob) | — | no | always |
| measure_voice_profile / uncalibrated (97) | uncalibrated.spectral_flatness | float | unitless | no | — | no | always |
| measure_voice_profile, SNR<30dB branch (100-121) | target.sibilance_centre_hz, sibilance_bandwidth_hz, de_esser_threshold_db, eq_high_shelf_hz, compressor_ratio, compressor_threshold_db | **all forced to None** | — | n/a while None | — | gated by internal SNR check, not an external dep | **yes — explicitly set to None with a `warnings.warn` (116-121)**, not measured at all when SNR<30dB |
| measure_voice_profile, SNR<30dB branch | consequence.f1_centre_hz, f2_centre_hz, singer_formant_fcp_db, hammarberg_index_db | **all forced to None** | — | n/a | — | SNR gate | same as above |
| measure_voice_profile, SNR>=30dB branch (123-149) | **target.sibilance_centre_hz** | float | Hz | **yes** — via `_measure_sibilance` (343-385): STFT peak in 3-10kHz band | de-esser "frequency" knob | no | fallback 7000.0 if n_fft<256 or no bins in 3-10kHz band (357-358, 367-368) |
| measure_voice_profile | **target.sibilance_bandwidth_hz** | float | Hz | **yes** — 6dB-down bandwidth around sibilance peak (377-385) | de-esser "range/Q" | no | fallback 2000.0 (358/368/383), floored at 100.0 min (385) |
| measure_voice_profile | **target.de_esser_threshold_db** | float, clamped [-20,-3] | dB | **yes** — via `_derive_de_esser_threshold` (715-744) | de-esser threshold knob | no | fallback -6.0 if band/vocal RMS ~0 or hi<=lo (728-729, 737-738) |
| measure_voice_profile | **target.eq_high_shelf_hz** | float | Hz | **yes** — via `_measure_eq_high_shelf` (471-484): LTAS peak freq in 2-4kHz | EQ high-shelf frequency knob | no | fallback 4000.0 if no bins in 2-4kHz (480-481) |
| measure_voice_profile | **target.compressor_ratio** | float, clamped [1.5, 4.0] | ratio (X:1, unitless) | **yes** — via `_derive_compressor_ratio` (667-674) | compressor ratio knob | no | always computed in this branch (no internal fallback beyond clip) |
| measure_voice_profile | **target.compressor_threshold_db** | float | dB | **yes** — via `_derive_compressor_threshold` (677-712) | compressor threshold knob | no | fallback -22.0 for near-silent RMS (686,693,707) |
| measure_voice_profile | consequence.f1_centre_hz, f2_centre_hz | float or None | Hz | no (informational, LPC formant estimate) | — | no (pure LPC/numpy, `_measure_formants_lpc` 521-573) | None if segment too short/silent, autocorr[0]<1e-12, or <2 valid roots found (534,540,554,561,571) |
| measure_voice_profile | consequence.singer_formant_fcp_db | float or None | dB | no | — | no | None if trend/region masks empty or <3 trend freq bins (432-433, 438-439) |
| measure_voice_profile | consequence.hammarberg_index_db | float or None | dB | no | — | no | None if low/high masks empty (462-463) |
| measure_voice_profile, Praat branch (152-166) | uncalibrated.f3_centre_hz, f4_centre_hz | float or None | Hz | no (explicitly UNCALIBRATED — docstring says "do not drive processing", 179-180) | — | **yes, parselmouth** | None if parselmouth missing (160-166) OR any per-call exception/empty values (767-773) |
| measure_voice_profile | uncalibrated.jitter_percent | float or None | % | no | — | parselmouth | same None conditions (778-786) |
| measure_voice_profile | uncalibrated.shimmer_percent | float or None | **dB, despite the field name "_percent"** — code calls `get_shimmer_local_db()` (796) and returns it unconverted (797), i.e. mislabeled unit | no | — | parselmouth | None on exception (798-799) |
| measure_voice_profile | uncalibrated.hnr_db | float or None | dB | no | — | parselmouth | None if NaN or exception (810-814) |
| measure_voice_profile | uncalibrated.cpps_db | float or None | dB | no | — | parselmouth | None if NaN or exception (825-829) |
| measure_voice_profile | uncalibrated.formant_bandwidth_hz | float or None | Hz (only B1/first formant bandwidth, despite generic field name) | no | — | parselmouth | None if no bandwidths collected or exception (847-851) |
| measure_voice_profile | sources.* | str/bool metadata | — | no | — | n/a | always; `recording_path` is hardcoded to `""` (171) — never actually populated from an argument |

### File 3: `toolshop/premaster.py`

Note: the module docstring says "none of the six measurable gates" (premaster.py:12) but `analyze_premaster` actually constructs **7** `GateResult` entries (gates 1-6 signal-measured, gate 7 manual/`NOT_MEASURED`, 202-206) — "six" refers to the six *measurable* (signal-correlate) gates per the spec; gate 7 has no signal correlate by design (21-22, 201-206).

All gate `value` fields are real-valued magnitudes in physical units (correlation coefficient, dBFS, dB, LUFS) — genuine measurements, not mere booleans — but every one feeds a `verdict` (`PASS`/`FLAG`/`FAIL`/`NOT_MEASURED`, via `_grade()` 66-74) rather than being exposed as a settable DSP control; these are *diagnostic/gating* magnitudes (they tell you whether the material is fit to master), not parameters you'd dial into a plugin.

| source function | field name | type | unit | settable DSP parameter? | consuming plugin/param | gated behind optional dep? | returns None/degrades when dep missing? |
|---|---|---|---|---|---|---|---|
| analyze_premaster, Gate 1 (124-132) | gates[0].value (full_band_corr_min) | float or None | Pearson correlation coefficient, unitless [-1,1] | no — diagnostic magnitude, feeds PASS/FLAG/FAIL only | — | requires stereo (n_channels>=2), not an optional lib | **None + verdict `NOT_MEASURED`** if mono (141-146) — explicit design choice per module docstring 16-17 |
| analyze_premaster, Gate 2 (133-140) | gates[1].value (low_band_corr_mean) | float or None | correlation coefficient, unitless | no | — | requires stereo; uses `scipy.signal.butter/sosfiltfilt` (89-93, hard scipy dep, not optional) | None + NOT_MEASURED if mono |
| analyze_premaster, Gate 3 (148-155) | gates[2].value (sample_peak_dbfs) | float | dBFS | no (diagnostic; informs limiter ceiling decision but is the *measured* peak, not a setting) | — | no | `-inf` if mono.size==0 or peak<=0 (149-150); `to_dict()` still rounds `-inf` via `round(float(-inf),4)` which is valid Python (=-inf) — **not converted to None** |
| analyze_premaster, Gate 4 (157-165) | gates[3].value (crest_factor_db) | float | dB (peak_dbfs - rms_db) | no | — | no | falls back to 0.0 if either peak_dbfs or rms_db is non-finite (160) rather than None |
| analyze_premaster, Gate 5 (167-191) | gates[4].value (psr_db) | float | dB (Peak-to-Short-term-loudness Ratio; true peak - max short-term LUFS) | no | — | **yes — requires `pyloudnorm` (114) and `soundfile` (113), hard imports inside the function, not guarded by a `_HAS_*` flag; ImportError propagates uncaught** | no None fallback in the field itself; if `st_values` is empty, falls back to overall `integrated` loudness (184); psr defaults to 0.0 if tp/max_st non-finite (185) |
| analyze_premaster | true_peak_dbfs_approx (top-level, 218) | float or None | dBFS, **explicitly documented as an inter-sample-peak approximation, "not a certified BS.1770-4 TP meter"** (96-101) | no | — | uses `scipy.signal.resample_poly` (102, hard dep) | None only if `tp` is non-finite (218); `-inf` if input array empty (104-105) |
| analyze_premaster, Gate 6 (193-199) | gates[5].value (dc_offset) | float | linear amplitude (abs of mean sample value, unitless -1..1 scale) | no | — | no | 0.0 if mono.size==0 (194) |
| analyze_premaster, Gate 7 (201-206) | gates[6].value | **always None** | — | no — by design; docstring: "manual check - no signal correlate" (21-22, 205) | — | n/a (not a software gap, a declared-provenance / lossless-ancestry check that has no acoustic signature) | always None + NOT_MEASURED, unconditionally |
| analyze_premaster | integrated_lufs | float or None | LUFS (ITU-R BS.1770 via pyloudnorm) | no | — | pyloudnorm (hard dep) | None if non-finite (217) |
| analyze_premaster | max_short_term_lufs | float or None | LUFS | no | — | pyloudnorm | None if non-finite (219); falls back to `integrated` if no 3s windows fit (184) |
| analyze_premaster | verdict / failing_gates / flagged_gates | str / list[str] | — | no (pure verdict rollup, 208-211) | — | — | — |
| GateResult.to_dict() (55-63) | value | float or None, rounded to 4 dp | matches per-gate unit above | — | — | — | `None if self.value is None else round(...)` (59) — note this does NOT catch `-inf`/`inf`, only literal `None`, so Gate 3/true-peak infinities pass through as `-Infinity` in the dict, not JSON-serializable by the stdlib default encoder without `allow_nan=True` |

## Q1 magnitude vs boolean

All 12 voice_effects_adapter.py detectors share the same shape: {"effect": str, "confidence": float, "params": dict, "evidence": list[str]} (e.g. voice_effects_adapter.py:93-98). confidence is always a verdict/probability, never a parameter. The question is whether params carries a real magnitude. Quoting each:

1. detect_reverb (85-179) -- MAGNITUDE. result["params"]["estimated_rt60_seconds"] = round(median_rt60, 3) (137) / round(rt60, 3) (157). Real RT60 in seconds, settable-ish as a reverb decay-time knob.
2. detect_pitch_shift (182-271) -- magnitude, but string-typed. result["params"]["estimated_semitones"] = f"-{round(shift_semitones, 1)}" (246-248) or f"+{round(shift_semitones, 1)}" (256-258). Quantitative semitone shift exists but is serialized as a signed string, not a float.
3. detect_formant_shift (356-431) -- boolean/anomaly-score only. Only ratios (F2_F1_ratio 385, F3_F2_ratio 396) and a coefficient of variation (419) feed an additive anomaly_score (387, 427) that becomes confidence. No Hz or semitone formant-shift amount is ever computed.
4. detect_compression (434-504) -- boolean bucket, not a magnitude. result["params"]["estimated_ratio"] = "8:1+" / "4:1" / "2:1" (477/483/489) -- three hardcoded strings selected by crest-factor threshold, never a continuous ratio, threshold, attack, or release value.
5. detect_eq (507-584) -- mixed: mostly boolean flags plus a couple of scalar magnitudes, but no band table. high_pass_detected/low_pass_detected are booleans (542, 554); hp_cutoff_estimate_hz = "~150Hz" is a hardcoded literal string, not measured (543); presence_boost_db (571) is a genuine dB magnitude but has no accompanying center-frequency/Q.
6. detect_distortion (587-679) -- MAGNITUDE. result["params"]["thd_percent"] = round(thd_percent, 2) (634), a real % THD value, plus clipped_sample_ratio (671).
7. detect_chorus (682-746) -- boolean/statistical only. phase_coherence (699) and bandwidth_cv (706) are unitless diagnostic ratios; the "periodic bandwidth modulation" peak search (709-729) only counts peaks to bump confidence (726) -- no LFO rate in Hz is ever stored.
8. detect_autotune (749-837) -- statistical/diagnostic only. mean_pitch_deviation_cents (781), pitch_jump_ratio (804), clean_jump_ratio (813), pitch_histogram_peak (825) -- all diagnostic distributions/ratios, no retune-speed (ms) value.
9. detect_deessing (840-893) -- boolean/ratio only. sibilant_ratio (867) and sibilant_variability_cv (882) -- no threshold dB, target frequency, or reduction-amount.
10. detect_vocoder (896-953) -- statistical only. mfcc_temporal_variance (911), harmonic_spacing_cv (928) -- no carrier frequency/band-count.
11. detect_noise_gate (956-1026) -- counts/ratios only. total_transitions, sharp_transitions (994-995, ints), sharp_ratio (999), noise_floor_variance_db2 (1014) -- no threshold dB / attack / release / hold, despite the effect name.
12. detect_delay (1029-1092) -- MAGNITUDE. result["params"]["delay_time_seconds"] = round(delay_seconds, 3) and delay_time_ms (1066-1067) are real, settable delay-time values; correlation_strength (1068) and echo_count (1083) are diagnostic, not feedback percent.

Tally: 3 of 12 detectors (reverb, distortion via thd_percent, delay) output a genuine continuous physical magnitude usable (with a mapping) as a plugin parameter. 1 (pitch_shift) outputs a real magnitude but string-typed. 1 (eq) outputs one true magnitude (presence_boost_db) plus a fabricated hardcoded-string field. The remaining 7 (formant_shift, compression's headline field, chorus, autotune, deessing, vocoder, noise_gate) output only booleans, discrete string buckets, or unitless statistical ratios/CVs that describe likelihood, not amount.

## Q2 derive functions

All four named functions are in D:\Projects\music_toolshop_v2\analysis\voice_profile.py.

1. _derive_hpf_cutoff (651-653):
```
def _derive_hpf_cutoff(f0_min: float) -> float:
    """Derive HPF cutoff from minimum F0: f0_min * 0.75."""
    return float(f0_min * 0.75)
```
Formula: hpf_cutoff_hz = f0_min * 0.75. Directly settable (Hz, feeds target["hpf_cutoff_hz"] at line 87). Evidence for the 0.75 constant: none in the file -- no comment, citation, or reference beyond the one-line docstring restating the formula. Not verified against any external source in this codebase.

2. _derive_compressor_ratio (667-674):
```
def _derive_compressor_ratio(dynamic_range_db: float) -> float:
    """Derive compressor ratio from dynamic range.
    Wide dynamic range leads to higher ratio.
    Formula: clamp(1 + dynamic_range_db / 10, 1.5, 4.0)
    """
    ratio = 1.0 + dynamic_range_db / 10.0
    return float(np.clip(ratio, 1.5, 4.0))
```
Formula: ratio = clip(1 + dynamic_range_db/10, 1.5, 4.0), unitless X:1. Directly settable (feeds target["compressor_ratio"], line 135). Evidence for /10, 1.5, 4.0: none given -- no citation to a mixing reference or measured calibration; the docstring only restates the formula itself.

3. _derive_compressor_threshold (677-712):
```
def _derive_compressor_threshold(mono: np.ndarray, sr: int) -> float:
    """Derive compressor threshold from RMS percentile analysis.
    threshold = rms_10th_percentile_db + (rms_90th - rms_10th) * 0.3
    """
    ...
    rms_10 = float(np.percentile(rms_values, 10))
    rms_90 = float(np.percentile(rms_values, 90))
    ...
    db_10 = 20.0 * np.log10(rms_10)
    db_90 = 20.0 * np.log10(rms_90)
    return float(db_10 + (db_90 - db_10) * 0.3)
```
Formula: threshold_db = db_10 + (db_90 - db_10) * 0.3, i.e. 30 percent of the way up from the quiet-frame level to the loud-frame level, in dB, using 50ms RMS frames (682). Directly settable (feeds target["compressor_threshold_db"], line 138). Evidence for the 0.3 weighting: none in file -- no calibration/citation given. Fallback constant -22.0 (686/693/707) is likewise uncited.

4. _derive_de_esser_threshold (715-744):
```
def _derive_de_esser_threshold(
    mono: np.ndarray, sr: int, sibilance_centre_hz: float,
) -> float:
    """Derive de-esser threshold from sibilance peak level vs vocal average.
    threshold = sibilance_band_peak_db - vocal_average_db - 6 dB headroom
    Clamped to [-20, -3] dB.
    """
    ...
    sos = butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
    band = sosfilt(sos, mono.astype(np.float64))
    band_rms = float(np.sqrt(np.mean(band ** 2)))
    vocal_rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
    ...
    band_db = 20.0 * np.log10(band_rms)
    vocal_db = 20.0 * np.log10(vocal_rms)
    threshold = band_db - vocal_db - 6.0
    return float(np.clip(threshold, -20.0, -3.0))
```
Formula: threshold_db = clip(band_db - vocal_db - 6.0, -20.0, -3.0), where band is a 4th-order Butterworth bandpass (plus/minus 1000 Hz around the measured sibilance_centre_hz, clamped to [3000,10000] Hz -- lines 725-731). Directly settable (feeds target["de_esser_threshold_db"], line 129). Evidence for the 6.0 dB headroom constant and the [-20,-3] clamp range: none in file -- no citation.

All four constants (0.75, the /10 with 1.5-4.0 clamp, the 0.3 weighting plus -22.0 fallback, and the 6.0 dB headroom with -20/-3 clamp) are uncited in-file; none reference an external spec, measured calibration study, or test that validates them against real mixes. This is a load-bearing gap: the formulas are directly settable in shape (right units, right field routing) but the specific numeric constants are unverified engineering judgment calls, not measured/derived from data -- marked "not verified" per this file alone.

## Q3 gaps -- what a mix engineer would need that neither file measures

- Saturation/harmonic-distortion amount -- PARTIALLY PRESENT. detect_distortion in voice_effects_adapter.py gives thd_percent (:634) and even_odd_harmonic_ratio (:647), which are genuine magnitudes. But there is no drive/gain amount calibrated to a specific saturation plugin, and voice_profile.py has no distortion/saturation field at all (absent).
- Stereo width / doubling -- ABSENT FROM BOTH. detect_chorus (voice_effects_adapter.py:682-746) only outputs phase_coherence and bandwidth_cv -- diagnostic statistics, no width percentage, no voice count, no detune amount. voice_profile.py has no stereo field at all -- indeed measure_voice_profile only accepts mono input (_to_mono averages any stereo down to 1-D, voice_profile.py:232-237, called at line 64), so stereo-width measurement is structurally impossible in that file.
- Delay feedback and time in ms -- TIME PRESENT, FEEDBACK ABSENT. detect_delay gives delay_time_ms (voice_effects_adapter.py:1067) -- a real settable value -- but never computes feedback percent or wet/dry mix, even when it detects multiple echo peaks (a feedback signature) at line 1082-1087; it only adds +0.1 to confidence (1087), never quantifies the feedback amount.
- Reverb pre-delay -- ABSENT FROM BOTH. detect_reverb only measures RT60 (decay time, :137/:157) and a hall/room type label (:161/:165); no pre-delay (ms) is computed anywhere in the file. voice_profile.py has no reverb field at all.
- Sidechain/ducking -- ABSENT FROM BOTH. Neither file contains any cross-track/sidechain analysis; voice_effects_adapter.py detect_compression and detect_noise_gate both operate on a single mono signal in isolation, and voice_profile.py likewise takes a single vocal array with no second input.
- EQ as a band table rather than a verdict -- ABSENT FROM BOTH, confirmed gap. detect_eq (voice_effects_adapter.py:507-584) outputs single scalar values (spectral_centroid_hz, spectral_rolloff_hz, presence_boost_db) and two booleans (high_pass_detected, low_pass_detected) -- never an array of {freq, gain_db, Q} bands. voice_profile.py only EQ-adjacent field is the single scalar eq_high_shelf_hz (:471-484, one shelf frequency, no gain or Q attached).
- Pitch-correction retune speed -- ABSENT FROM BOTH. detect_autotune (voice_effects_adapter.py:749-837) measures mean_pitch_deviation_cents, pitch_jump_ratio, clean_jump_ratio -- all diagnostic -- but never derives a retune-speed value in ms that could be set on a pitch-correction plugin. voice_profile.py has no autotune/pitch-correction field at all.
- Level automation / vocal rider -- ABSENT FROM BOTH. Neither file produces any time-series/automation-curve output; both collapse dynamics to single scalar summary statistics (dynamic_range_db in both files, rms_variance_db2 in voice_effects_adapter.py:469) -- no per-phrase or per-section gain-riding curve is ever computed or stored.

Net: of the 8 checklist items, only 2 are meaningfully present (saturation-amount via THD percent, delay-time-ms), 1 is half-present (EQ has scalar fields but no band table), and 5 are fully absent (stereo width, reverb pre-delay, sidechain, retune speed, level automation).

## Uncertainties

- premaster.py Gate 3 (sample_peak_dbfs) and true_peak_dbfs_approx can be -inf mathematically (peak<=0, lines 150/108); GateResult.to_dict() only special-cases None (line 59), so a -inf value would pass through round(float(-inf), 4) = -inf unchanged in the returned dict. Whether downstream JSON serialization (json.dump) is called anywhere on this dict, and whether it uses allow_nan=True or would raise, was not traced -- not verified, out of the three named files scope (no json.dump call exists inside premaster.py itself).
- voice_profile.py uncalibrated.shimmer_percent (789-799) is documented as percent in the field name but the underlying call is get_shimmer_local_db() (796), returned unconverted -- this looks like a unit-label bug (dB reported under a "_percent" key) but confirming the intended behavior would require checking parselmouth's own API docs, which is outside the three files in scope. Flagged as observed-but-not-fully-verified against upstream library semantics.
- Whether any caller of voice_effects_adapter.py or voice_profile.py post-processes the string-typed fields (estimated_semitones, estimated_ratio) into floats before feeding a plugin was not checked -- out of scope (only the three named files were read). If such a parser exists elsewhere, the "not directly settable" classification for those two fields would need revisiting at the point of consumption, though the fields themselves, as returned by these functions, are still string-typed as documented above.
- Did not execute any code or run the analyzers on audio, per the task instructions -- all findings are static-read from source only.
