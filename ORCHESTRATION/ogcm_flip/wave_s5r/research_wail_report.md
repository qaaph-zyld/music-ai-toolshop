# OGCM GATE S5 - Wail lead research (report-only)

Scope: re-performance on our own synth. No source-audio handling research. Access note: WhoSampled, Genius, Gearspace and Reddit pages returned 403/no hits to direct fetch. Items marked (snippet) rest on search-result text, not a full page read.

## Summary
- Q1: the wail's instrument is NOT publicly documented. Credits name producers only (no player, no instrument). Best-supported label is "G-funk portamento synth lead", confidence low-med; it is a genre-convention inference, not a credit.
- Q1: the claim that the lead samples Kleeer "Tonight" failed verification (Wikipedia lists only Audio Two "Top Billin'"). Do not use it.
- Q2: sources agree on mono-legato, saw-based lead, slow-ish glide, 5-6 Hz vibrato about +/-25-60 cents. They disagree on saw vs near-sine and give no authoritative glide time. Our voice is inside the plausible range. Main fixes: glide too long when a contour already drives pitch, and double vibrato risk.
- Q3: use pyin at frame 1024 / hop 128 (same time scale as the pYIN paper), fmin about 196 Hz, fmax about 2093 Hz, then fix octave errors per segment, short median (about 30-40 ms), bridge gaps of 100 ms or less.
- Best next step for Q1: Doug Rasheed's two-part YouTube interview (links below) likely answers it, but I could not get transcripts.

## Q1 Identity

Verified facts
- Producers Doug Rasheed and Harold "Scrap" Freddie; writers Shakur, Rasheed, Forte, Fretty; sample credit "Top Billin'" (Audio Two). No keyboardist or instrument credit. [https://en.wikipedia.org/wiki/All_Eyez_on_Me] (high)
- WhoSampled lists the Audio Two sample and nothing for a lead instrument (snippet). [https://www.whosampled.com/2Pac/Only-God-Can-Judge-Me/] (med)
- Rasheed's written interview has no production detail. [https://rapindustry.com/doug-rasheed-beyond-the-boards-the-soul-behind-hip-hops-greatest-moments] (high)
- Not read (no transcript): Rasheed Part 1 [https://www.youtube.com/watch?v=h3EoiSwdNt4], Part 2 "Breakdown" [https://www.youtube.com/watch?v=CAXi5TTq5j4], and a forum thread on it (paywall 402) [https://www.kanyetothe.com/threads/breakdown-of-the-classic-2pac-song-only-god-can-judge-me.2510281/].

Candidates
- Synth (portamento lead): convention only. G-funk is defined by "a high-pitched portamento saw wave synthesizer lead", with the Ohio Players "Funky Worm" ARP solo as blueprint. [https://en.wikipedia.org/wiki/G-funk] (high for the genre, low-med for this track). A search snippet lists this track among 90s songs with a whiny synth lead, and a search-summary phrase calls it a "mosquito-in-your-ear G-funk synth"; I could not trace either to a primary source. (low)
- Kleeer "Tonight" sample: a URL slug claims it [https://2paclegacy.net/2pac-only-god-can-judge-me-was-sampled-of-tonight-by-kleeer/]; the page returned only a bot-check. Wikipedia credits "Tonight" to Norman Durham and lists no 2Pac sample [https://en.wikipedia.org/wiki/Intimate_Connection]. Treat as false. (med)
- Talkbox, slide guitar, female vocal: no source ties any of them to this track. The talkbox association found is California Love only. (low; not ruled out)
- Sampled-source wail: only "Top Billin'" is credited, and I could not confirm which element it supplies. (low)

Verdict: Unknown. Nothing contradicts a synth lead, nothing confirms one. Confidence low-med.

## Q2 Minimoog-style G-funk whine recipe

Evidence
- Waveform conflict. Wikipedia and Syntorial say saw: two saws at 50% each, detuned +/-1 cent [https://www.syntorial.com/preset-recipe/dr-dre-nuthin-but-a-g-thang-lead/] (med; approximate preset for a different song). A Gearspace summary says "almost pure sine, slow portamento" while another poster says saw, glide about 55% (snippet) [https://gearspace.com/threads/west-coast-whistle.425863/] (low).
- Filter: Minimoog is a 24 dB/oct low-pass ladder with resonance (snippet) [https://www.manualslib.com/manual/2919531/Moog-Minimoog-Model-D.html] (med). Syntorial: LP cutoff 75%, resonance unspecified. A Minimonsta lead uses low cutoff plus a filter contour of about 600 ms attack [https://www.musicradar.com/tuition/tech/how-to-create-a-classic-minimoog-lead-sound-using-gforce-minimonsta-642763] (med, prog-rock lead, not G-funk).
- Glide: Minimoog range 1 ms-10 s and proportional (constant-rate), so larger intervals take longer (snippet) [https://forum.moogmusic.com/viewtopic.php?t=12376] (med). Syntorial uses 10 ms legato. Generic guidance: 20-50 ms subtle, 80-200 ms lead, 300-600 ms sweeps, and at most 30-60% of the shortest note [https://musicproductionwiki.com/bible/portamento] (med). No primary G-funk glide time found.
- Vibrato: singing norm 4.5-6.5 Hz, extent 50-120 cents peak-to-peak (+/-25-60), below 20 cents heard as straight [https://www.voicescience.org/lexicon/vibrato/] (high for voice, low for G-funk synth). No sourced onset delay; belt-style singing starts vibrato later in the note (same source). Our 180 ms is unsourced.
- Amp envelope: Syntorial attack 0 ms, release 20 ms, sustain 100% (med).
- Delay: dotted 8th = 60000/BPM x 0.75 = 505 ms at 89.1 BPM [https://toolstud.io/music/delay.php] (high, arithmetic). No source for G-funk reverb or feedback; treat as taste.
- Caveat: Colin Wolfe reportedly used a Yamaha SY77, not a Minimoog, on "G Thang" [https://www.tiktok.com/@anthonymarinellimusic/video/7415522299694255406] (low). "Minimoog" is a convention label, not proof.

| parameter | recommended | our current | source |
|---|---|---|---|
| oscillator | sine + saw; A/B: saw-heavy | sine + 0.35 saw | conflicting (Wikipedia G-funk, Syntorial, Gearspace); low |
| filter | LP 24 dB/oct, open (about 4-6 kHz here), mild resonance | none/tanh only | Minimoog spec; numbers are my judgement; low |
| glide | 15-30 ms when contour-driven (contour carries the glide) | 100 ms | Syntorial 10 ms; Producer's Bible 20-50 ms; med |
| vibrato rate | 5-6 Hz | 5.5 Hz | voicescience; med |
| vibrato depth | +/-25-50 cents, only if contour lacks it | +/-45 cents | voicescience; med |
| vibrato onset | about 150-250 ms | 180 ms | unsourced; low |
| amp attack/release | 5-12 ms / 40-80 ms | 12 / 80 ms | Syntorial 0/20; low-med |
| delay | dotted 8th 0.505 s | 0.375 s (being fixed) | delay formula; high |
| reverb | keep room 0.45 | 0.45 | none found; low |

## Q3 Pitch-contour tracking with librosa only

- Range. pyin docs recommend fmin C2 (65 Hz) and fmax C7 (2093 Hz) [https://librosa.org/doc/0.11.0/generated/librosa.pyin.html] (high). The pYIN paper's HMM spans 55-880 Hz [https://webspace.eecs.qmul.ac.uk/s.e.dixon/pub/2014/MauchDixon-PYIN-ICASSP2014.pdf] (high). For MIDI 60-90 (262-1480 Hz) use G3 (196 Hz) to C7 (2093 Hz): margin for bends, while excluding bass and low-voice bleed, which cuts sub-octave errors. The window is my judgement (med).
- Frames. The paper used a 2048 frame and 256 step at 44.1 kHz (46.4 ms and 5.8 ms) (high). Equivalent at 22.05 kHz: frame_length 1024, hop_length 128. librosa defaults are 2048 (93 ms) with hop = frame/4 [https://librosa.org/doc/0.11.0/generated/librosa.yin.html] (high). 93 ms smears fast wails. fmin 196 Hz needs only about 113 samples per period, so 1024 is ample (high, arithmetic).
- HMM. The paper uses 10-cent bins, max jump 2.5 semitones per 5.8 ms frame, and reports octave-error rates of 0.5-1.7% on clean synthetic singing (high). librosa's default max_transition_rate of 35.92 oct/s equals that jump (my arithmetic, med). A single-frame octave flip is therefore impossible at hop 128, so octave errors appear as whole segments. Keep defaults for resolution, n_thresholds and beta_parameters (2,18). Use fill_na=nan.
- Voicing. Use voiced_flag AND voiced_probs >= 0.5 (libf0 default voicing probability 0.5) [https://groupmm.github.io/libf0/build/html/index_pyin.html] (med). pyin is energy-blind, so stem bleed can read as voiced. Add an RMS gate (drop frames far below the stem's own voiced level; threshold is my judgement, low).
- Octave fixes. Convert to MIDI. Per voiced segment compare its median to a roughly 1 s rolling median of neighbours; if the gap is 12 +/- 1.5 semitones, shift by 12. Drop what stays outside 55-96. Contour-level octave-duplicate removal is the standard approach (Salamon and Gomez 2012) [https://www.semanticscholar.org/paper/Melody-Extraction-From-Polyphonic-Music-Signals-Salamon-G%C3%B3mez/7db166db77f884533dfe1448ff7a15ad8b153b84] (med, snippet). Threshold logic: YIN threshold trades subharmonic against harmonic errors [http://audition.ens.fr/adc/pdf/2002_JASA_YIN.pdf] (med, snippet).
- Median filter. Smart-Median uses about 35-70 ms of look-ahead for singing contours [https://www.mdpi.com/2076-3417/12/14/7026] (med, snippet). At a 5.5 Hz vibrato (182 ms period) a window of 50 ms or less leaves the modulation nearly intact (my reasoning, med). Use 5-7 frames at hop 128, applied to MIDI values inside voiced segments only, never across NaN. scipy ships with librosa (scipy>=1.6) so scipy.ndimage.median_filter adds no dependency [https://pypi.org/project/librosa/0.9.1/] (med).
- Gaps and glides. Bridge unvoiced gaps of about 100 ms or less (17 frames) by linear interpolation in MIDI, only when the pitch difference across the gap is about 3 semitones or less; larger steps are note boundaries. Drop voiced islands shorter than about 50 ms. Do no further low-pass smoothing. Verify by comparing peak-to-peak vibrato before and after on a sustained note (judgement, low-med).

## Recommended parameters for render_f0_lead
- Pitch source: the cleaned contour in MIDI, frame step 5.8 ms, resampled to audio rate by linear interpolation.
- Pitch smoothing: 15-30 ms constant-time only. The contour already holds the glides; keep the old 100 ms portamento for note-based render_gfunk_lead only.
- Vibrato: none by default. Measure contour vibrato on sustained notes; if under about 40 cents peak-to-peak, add 5.5 Hz at +/-30-45 cents with 180 ms onset, and ramp it in.
- Oscillator: default sine + 0.35 saw; render an A/B variant saw-heavy (saw 1.0, sine 0.3) through a 24 dB/oct low-pass around 4-6 kHz, mild resonance. No ground truth exists for the original, so pick by ear.
- Envelope: attack 8-12 ms, release 60-80 ms. Legato across unvoiced gaps of 100 ms or less; retrigger beyond that.
- Level: keep tanh soft clip; gate amplitude by voiced probability, fading over about 10 ms.
- Delay: dotted 8th 0.505 s at 89.1 BPM; keep your feedback. Reverb room 0.45 unchanged.

## pyin settings
- sr 22050; fmin = note_to_hz G3 (about 196 Hz); fmax = note_to_hz C7 (about 2093 Hz).
- frame_length 1024; hop_length 128 (256 if speed matters; halve all frame counts below).
- n_thresholds 100; beta_parameters (2, 18); boltzmann_parameter 2; resolution 0.1; max_transition_rate 35.92; switch_prob 0.01; no_trough_prob 0.01 (all defaults).
- fill_na nan; center true.
- Voiced mask: voiced_flag and voiced_probs at or above 0.5, plus an RMS gate.
- Post: octave fix per segment, then median 5-7 frames, then drop islands under about 9 frames, then bridge gaps up to 17 frames with a 3-semitone limit.
