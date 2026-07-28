# Building a Drill/Trap Flip Remix from Demucs Stems in Python — A Complete Technical Guide

## Diagnosis: Why the Current Segment-Based Approach Fails

The user's pipeline — slicing the combined instrumental into 8-beat segments, independently running `pedalboard.time_stretch` (Rubber Band) on each segment, then crossfading — fails for a well-understood, documented reason. Rubber Band is a **phase-vocoder-based frequency-domain time stretcher with phase resynchronization at transients** ([jlank/rubberband on GitHub](https://github.com/jlank/rubberband)). Every time a phase vocoder starts fresh on a new buffer, it has no information about the phase state of the previous buffer, so it re-initializes phase relationships between frequency bins. When two independently-stretched segments are crossfaded, the phase relationships across the seam don't line up, which is audible as **warbling, phasiness, and timbre shifts** — exactly the symptoms described.

The [Producer's Bible entry on time-stretching](https://musicproductionwiki.com/bible/time-stretching) states this directly: "any seam between repositioned fragments is audible as a click, phase artifact, or unnatural timbre shift if the algorithm gets it wrong," and that grain/frame boundaries in granular or phase-vocoder algorithms are the primary source of "buzzing texture when crossfade windows overlap imperfectly." The same source notes a hard rule that professional workflows follow: **process the whole clip as one continuous buffer, and if you must split it, split only at points the algorithm is designed to handle (e.g., DAW warp markers within one continuous warp operation), never as fully independent stretch calls**. A first-hand account on a production forum confirms the exact failure mode: engineers who warped stems individually versus the whole song reported the individually-warped stems sounded "hollow," while warping the whole track first and extracting stems afterward avoided it, because "the quality is way less and you need the transients to properly stretch/warp" when material is chopped into small pieces before stretching ([Facebook Ableton Live Users group discussion](https://www.facebook.com/groups/abletonliveusers/posts/25261854966831462/)).

The fix is architectural, not parametric: **stop slicing before stretching.** Run the time-stretch/pitch-shift operation once, on the full-length signal (or at most on whole stems), and do the beat-chopping (if any is still needed for rearrangement) only on the already-stretched, pitch-corrected audio — ideally at zero crossings, not by crossfading independently-processed segments.

---

## 1. Whole-Audio Time-Stretching: Doing It Once, Not Per-Segment

### `pedalboard.time_stretch` on a full 5-minute file — yes, this works and is the recommended fix

`pedalboard.time_stretch()` operates on an in-memory NumPy buffer of arbitrary length and is a direct binding to the Rubber Band library ([Pedalboard API reference](https://spotify.github.io/pedalboard/reference/pedalboard.html)). There is nothing in the API that constrains it to short clips — it is designed to processes a full buffer at once, using Rubber Band's internal frame-overlap-add machinery to maintain **phase continuity across the entire signal**, which is precisely the property that breaks when you split the file into independent chunks. Spotify's own examples load an entire audio file into memory and process it as one array ([Pedalboard examples documentation](https://spotify.github.io/pedalboard/examples.html)):

```python
from pedalboard.io import AudioFile
import pedalboard

samplerate = 44100.0
with AudioFile("instrumental_full_mix.wav").resampled_to(samplerate) as f:
    audio = f.read(f.frames)  # read the ENTIRE file as one array, shape (channels, samples)

# 89 BPM -> 87 BPM stretch factor. Rubber Band's stretch_factor multiplies SPEED,
# so to slow down (increase duration), use ratio < 1.0 relative to speed:
stretch_factor = 87.0 / 89.0   # ~0.9775 => slightly slower playback = longer duration
pitch_shift_semitones = -2.0   # -2 semitones ~ A major -> G major-ish; see key section below

stretched = pedalboard.time_stretch(
    input_audio=audio,
    samplerate=samplerate,
    stretch_factor=stretch_factor,
    pitch_shift_in_semitones=pitch_shift_semitones,
    high_quality=True,          # use the higher-quality R3 "Finer" engine
    transient_mode="crisp",     # good default for mixed material with drums
    retain_phase_continuity=True,
    preserve_formants=True,     # keeps vocal timbre natural if vocals are included
)

with AudioFile("instrumental_stretched.wav", "w", samplerate, stretched.shape[0]) as o:
    o.write(stretched)
```

Key parameters, per the [Pedalboard API documentation](https://spotify.github.io/pedalboard/reference/pedalboard.html):
- `stretch_factor` and `pitch_shift_in_semitones` are **independent** — you can set both in the same call without one affecting the other, unlike naive resample-based pitch shifting.
- `high_quality=True` engages Rubber Band's better (slower) "R3" processing engine.
- `transient_mode` (`'crisp'`, `'mixed'`, `'smooth'`) controls how aggressively transients are detected and treated — `'crisp'` is best for material with drums; `'smooth'` suits pads/sustained harmonic content.
- `preserve_formants=True` prevents the "chipmunk"/"demon" timbral shift on vocal or vocal-like content when pitch-shifting down.
- Pedalboard's file I/O also supports **O(1)-memory streaming** via `AudioFile` for reading/writing in chunks ([Pedalboard README](https://github.com/spotify/pedalboard/blob/master/README.md)), but `time_stretch` itself still wants one contiguous buffer per call — for a 5-minute stereo 44.1kHz file this is roughly 105 MB as float32, trivial for modern RAM, so there's no practical reason to chunk it.

Under the hood, Rubber Band Library and FFTW are statically bundled and dual-licensed under GPLv2/commercial ([pedalboard dependency table](https://blog.csdn.net/gitblog_00904/article/details/148504969)) — this is the same DSP engine used by `pyrubberband`, just with a native Python binding instead of shelling out to a CLI.

### `pydub` — usable for tempo but weak/lossy for pitch, and its "speedup" is itself a chunk-and-splice tool

`pydub.effects.speedup()` internally works by **splitting the sound into small chunks (150ms default) and overlapping them with crossfades (25ms default)** to shorten duration ([Stack Overflow: change playback speed with pydub](https://stackoverflow.com/questions/51434897/how-to-change-audio-playback-speed-using-pydub)) — this is conceptually the *same class of algorithm* causing the user's current problem, just applied to raw speed change rather than combined with pitch. It works reasonably for speeding up, but pydub has no dedicated slow-down function; community workarounds duplicate chunks to slow down, which is comparatively crude ([`audio-effects` PyPI package `speed_down`](https://pypi.org/project/audio-effects/)). For pitch shifting, pydub has no native implementation — common recipes either do a "chipmunk" varispeed shift (changing `frame_rate` metadata, which changes speed and pitch together, [pydub issue #157](https://github.com/jiaaro/pydub/issues/157)), or delegate to `librosa.effects.pitch_shift` on the raw sample buffer ([Stack Overflow: pydub pitch modulation](https://stackoverflow.com/a/44730611)). **Conclusion: pydub is not competitive with pedalboard/Rubber Band for this task** — it's fine for basic format conversion and simple tempo nudges, but for pitched-down, tempo-changed, artifact-free instrumental processing, it should not be the core engine.

### FFmpeg: `atempo`+`asetrate` vs. the `rubberband` filter — very different quality tiers

There are **two fundamentally different techniques** available in FFmpeg, and they should not be confused:

**(a) `asetrate` + `aresample` + `atempo` — "varispeed" chipmunk-style, changes pitch and speed together, then partially corrects**
This reinterprets the sample rate (changing both pitch and speed together, like a turntable), resamples back to the original rate (which stretches/compresses the waveform, undoing the *speed* change but not the *pitch* change), and then uses `atempo` to correct any residual tempo mismatch. It is described step by step here: "asetrate changes the interpreted sample rate to shift the pitch... aresample converts the audio back to the original sample rate (which stretches/compresses the waveform)... atempo adjusts the playback speed" ([nah.tools pitch shifter explainer](https://nah.tools/audio/pitch)). This is a **cheap, phase-continuous, single-pass method with no chunking artifacts at all** (because it never splits the buffer) but the pitch and tempo are coupled unless you add a correcting `atempo` stage, and audio quality on the pitch axis is essentially "tape speed change" — perfectly smooth but tied to the tempo ratio, not independently controllable.

For "slow down + pitch down" simultaneously (which is actually what a drill flip needs — both), the interesting property is that a pure `asetrate` slowdown **already pitches the audio down proportionally**, so for a pitched-down + slowed-down drill flip you may not even need `atempo` at all if the ratios line up. To go from 89 BPM/A major to 87 BPM with an *additional* -2 semitones beyond what the tempo change alone gives you:

```bash
# Step 1: tempo-only ratio for 89 -> 87 BPM
# ratio = 87/89 = 0.97753 (target/original)

# Combined "slow + pitch down" filter chain using asetrate (single elegant filter for BOTH):
# To slow tempo by 87/89 AND additionally drop pitch by 2 semitones beyond
# what that tempo change gives, compute total pitch ratio:
#   tempo_ratio   = 87/89              = 0.977528
#   pitch_ratio   = 2^(-2/12)          = 0.890899   (extra -2 semitones on top)
#   combined_rate = tempo_ratio * pitch_ratio  -- if you want BOTH coupled via asetrate alone
# But usually you want pitch and tempo independent, so use atempo to decouple:

ffmpeg -i instrumental.wav -af \
  "asetrate=44100*0.890899,aresample=44100,atempo=0.977528" \
  instrumental_pitched_slowed.wav
```

Explanation of the chain: `asetrate=44100*0.890899` drops the pitch by 2 semitones (and as a side effect slows playback by the same factor); `aresample=44100` restores the nominal sample rate so downstream players/filters treat it as normal 44.1kHz audio (this is the step that actually "prints" the pitch shift into the waveform); `atempo=0.977528` then independently retimes the *already pitch-shifted* audio to hit the exact 87 BPM target tempo without touching pitch further. This gives full independent control over final pitch and tempo in one filter graph, no chunking. Note FFmpeg's own documentation constraint: `atempo` accepts values in `[0.5, 2.0]` — outside that range you must **daisy-chain multiple atempo filters** to reach the desired product, e.g., `atempo=0.7,atempo=0.7` for a 0.49 ratio ([FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)). The 89→87 BPM ratio (0.9775) and a few semitones of pitch are both comfortably inside the single-filter range, so no daisy-chaining is needed here.

**(b) FFmpeg's `rubberband` filter — same DSP engine as pedalboard, if your FFmpeg build has it**
FFmpeg has a native `rubberband` audio filter that wraps librubberband directly, giving Rubber Band-quality independent tempo/pitch control in a single filter: `rubberband=tempo=0.5:pitch=0.5` ([ffmpegbyexample.com filter breakdown](https://ffmpegbyexample.com/examples/749f6u35/timestretch_audio_and_video_using_rubberband_filter/)). **Critically, this filter is not compiled into most stock/distro FFmpeg builds** — it requires `--enable-librubberband` at compile time, and this is confirmed as absent from, e.g., the default Arch Linux `ffmpeg` package, requiring either a manual rebuild or a community `-full` variant ([Arch Linux forum: "No rubberband filter in FFmpeg"](https://bbs.archlinux.org/viewtopic.php?id=284082); [FFmpeg filter docs](https://ayosec.github.io/ffmpeg-filters-docs/8.0/Filters/Audio/rubberband.html)). Given this is the exact same underlying algorithm as `pedalboard.time_stretch()` (both wrap librubberband), **there is no quality reason to fight with a custom FFmpeg build** when `pedalboard` gives you the same engine as a pure pip install with no compilation step. Use FFmpeg's `asetrate`/`atempo` chain only if you specifically want the "coupled" tape-style character for a small correction, or need it inside a shell pipeline without Python; use `pedalboard`/`pyrubberband` for the main creative pitch/time move.

### `librosa.effects.time_stretch` / `pitch_shift` — technically viable, audibly the weakest option here

Librosa's phase vocoder implementation is the textbook reference algorithm — `time_stretch` computes an STFT, phase-vocodes it, and does an inverse STFT; `pitch_shift` is implemented internally as `time_stretch` followed by resampling ([librosa `phase_vocoder` walkthrough](https://www.wizard-notes.com/entry/music-analysis/librosa-phase-vocoder); [librosa effects source](https://librosa.org/doc/0.11.0/_modules/librosa/effects.html)). It absolutely can run on a full 5-minute buffer in one call — there's no per-segment requirement — so it *would* fix the specific boundary-artifact bug the user has now. However, independent, non-search-engine-influenced technical documentation directly comparing algorithms states librosa's phase vocoder "can significantly degrade the audio quality by 'smearing' transient sounds, altering the timbre of harmonic sounds, and distorting pitch modulations" relative to newer alternatives ([audiomentations PitchShift documentation](https://iver56.github.io/audiomentations/waveform_transforms/pitch_shift/), which offers `signalsmith_stretch` as a higher-quality alternative backend precisely because of this). Chinese-language DSP writeups converge on the same finding: pushing librosa's `rate` outside roughly 0.5–2.0 or using default FFT settings introduces "metallic distortion" (金属声失真), and recommend manually raising `n_fft` to 4096 and `hop_length` to 1024 for cleaner results ([CSDN librosa deep-dive](https://blog.gitcode.com/1cab39e91e6ead571dd793f274914ada.html)). For an 87/89 BPM ratio (~2.5% change) librosa would likely sound fine, since that's a tiny stretch, but Rubber Band (via `pedalboard`) is a purpose-built, more modern phase-vocoder-plus-transient-handling algorithm and is the better default. **Use librosa only as a fallback/cross-check, not the primary engine.**

### Quality comparison summary

| Method | Whole-file capable | Independent pitch+tempo | Typical artifact risk | Setup effort (CPU-only, Py 3.11) |
|---|---|---|---|---|
| `pedalboard.time_stretch` (Rubber Band) | Yes, natively | Yes | Low — phase-continuity retained across whole buffer | `pip install pedalboard`, zero compile |
| `pyrubberband` (CLI wrapper) | Yes | Yes | Low, same engine as above | Needs system `rubberband` CLI binary installed |
| FFmpeg `rubberband` filter | Yes | Yes | Low, same engine | Requires custom FFmpeg build (`--enable-librubberband`), often unavailable |
| FFmpeg `asetrate`+`atempo` | Yes | Yes (with the 3-filter chain) | Low for phase; slightly more "tape-like" tonal character since pitch axis is a literal resample | Built into any stock FFmpeg |
| `librosa.effects.*` | Yes | Yes (via internal 2-step) | Medium — documented smearing/metallic artifacts, especially outside 0.5–2x | Pure Python/pip, no binary deps |
| `pydub.speedup` / chipmunk resample | Chunk-based internally | No (coupled) or crude workaround | Medium-high — same "chunk and crossfade" architecture as the user's current failing approach | `pip install pydub` |

**Recommendation for this project:** use `pedalboard.time_stretch()` once on the fully assembled instrumental (or once per stem, see Section 5), with `high_quality=True`, `preserve_formants=True`, and `transient_mode='crisp'`. This is a drop-in fix for the reported artifacts because it removes the segment-boundary phase discontinuities entirely — the core bug is architectural (segmenting), not which stretch library was chosen.

---

## 2. Stem-Level Processing Before Mixing (Summing Stems into an Instrumental)

### Should EQ/compression be applied per-stem before summing? Yes — this is standard practice

Every mixing source consulted converges on the same subtractive-EQ-first workflow, and it applies whether the "tracks" are live recordings or Demucs-derived stems: **cut what you don't need before you sum, boost only afterward if still necessary.** The core rule from a dedicated EQ workflow guide: "subtract first, add if necessary... When you cut a frequency, you're removing energy that was potentially causing problems — mud, harshness, frequency masking" ([Producer Hub EQ fundamentals](https://producerhub.co.uk/blog/eq-fundamentals/)).

### High-passing drums / low-passing bass, and standard HPF starting points by element

Multiple independent mixing guides give nearly identical starting-point numbers. Consolidated guidance ([mixmasterpro.io low-end control guide](https://mixmasterpro.io/articles/lowendcontrol); [Producer Hub EQ fundamentals](https://producerhub.co.uk/blog/eq-fundamentals/); [Old Cottage Audio low-frequency management](https://oldcottageaudio.co.uk/low-frequency-management-in-mixing-and-mastering-part-1-filters-and-eq/)):

| Stem/element | High-pass filter starting point | Notes |
|---|---|---|
| Kick / 808-adjacent low drum content | 20–30 Hz (very gentle) or none | Don't cut higher — you lose the foundation |
| Snare | 80–120 Hz | Below this is just rumble, no useful "snare" content |
| Hi-hats/cymbals (drums stem, upper content) | 200–400 Hz (some sources say up to 800 Hz) | No useful information below fundamental |
| Bass stem | No HPF, or extremely gentle ~20 Hz | The bass needs its full low-frequency content — do not high-pass a bass stem meaningfully |
| Other/Piano/Guitar (melodic/harmonic stems) | 100–250 Hz | Removes "junk bass"/mud that would otherwise clash with 808/bass |
| Vocals (if retained in the flip) | 80–150 Hz | Removes rumble/breath noise without harming tone |

Because Demucs' **drums** stem contains kick, snare, and hats together as one bus, you generally do **not** high-pass the whole drums stem aggressively (that would gut the kick) — instead apply a *gentle* low-end trim (e.g., 30–40 Hz) mainly to remove sub-rumble, and rely on the bass-stem processing to avoid masking. The **bass** stem (and any 808 you layer in for the drill flip) should be the stem that "owns" true sub content; the **other/guitar/piano** stems are where you high-pass more assertively (100–250 Hz) because melodic backing material rarely needs sub-bass energy and that energy, left in, just clutters the space where your 808 needs to sit.

### Avoiding frequency masking when summing stems

The standard toolkit, consistent across sources ([SoundGym: four techniques to fix frequency masking](https://www.soundgym.co/blog/item?id=four-ways-to-fix-frequency-masking-in-your-mix); [fadelab masking guide](https://fadelab.net/blog/frequency-masking-in-mixing)):
1. **Subtractive EQ** at the point of overlap — identify which two stems clash (e.g., a synth in the "other" stem sitting at the same frequency as the bass) and cut the *less important* one there, boosting the important one is secondary.
2. **High-pass/low-pass filtering** — remove frequency ranges an element contributes nothing useful in, freeing headroom for kick/bass.
3. **Sidechain compression** — duck the bass stem against the kick transient from the drums stem so both can occupy the same low-frequency pocket without permanently cutting bass level. Typical settings: attack 5–10 ms, release 50–100 ms, ratio 3:1–6:1, gain reduction 3–6 dB ([mixmasterpro.io](https://mixmasterpro.io/articles/lowendcontrol)).
4. **Panning** — masking is strongest when two elements sit at the same stereo position; if the "other"/"guitar"/"piano" stems overlap in frequency, panning them apart reduces perceived masking even without EQ changes.

A specific and very actionable rule for kick/bass coexistence: identify the kick's fundamental (commonly 60–80 Hz), give the kick dominance there with a gentle boost, cut the bass 3–6 dB at that same frequency, then give the bass dominance in the 120–200 Hz "body" range and cut any kick resonance there — "solo them together and carve while listening to both simultaneously," never in isolation ([Producer Hub EQ fundamentals](https://producerhub.co.uk/blog/eq-fundamentals/)).

### Normalize per-stem, or normalize the final mix? Neither — set relative gain, normalize once at the very end (if at all)

This is a point of real disagreement in casual forum discussion but a clear consensus among more experienced voices: **normalizing individual stems to their own peak is actively harmful to a mix**, because it discards the relative loudness relationships between elements that make a mix sound balanced (a kick that peaks at -20 dBFS and a hat that peaks at -6 dBFS were probably like that on purpose; normalizing both to 0 dBFS destroys that relationship). Direct quote from a mixing forum with strong upvote consensus: "OMG, never normalize stems, terrible idea, because in the future if you need to re-sum them yourself... the balance will be all wrong! ... normalizing pre-mixdown... an exceedingly bad idea" ([Image-Line forum discussion](https://forum.image-line.com/viewtopic.php?t=275257&start=50)). A professional engineer's take: normalizing every track "simply forces the mix fader down... top-level mixes peak between –6 to –10 dBFS. This gives room for relative volumes to be adjusted during mastering" ([Reddit r/WeAreTheMusicMakers](https://www.reddit.com/r/WeAreTheMusicMakers/comments/vndu0c/should_you_normalize_each_individual_audio_track/)). The practical, correct workflow for stem-summing:
- Set the **gain of each stem manually** (a scalar multiply, e.g., `stem_audio * db_to_amplitude(gain_db)`), balanced by ear/RMS, not by peak-normalizing each one.
- If anything, measure **RMS level** per stem and set a target range (e.g., –18 to –12 dB RMS as a starting point, per [Harrison Mixbus forum](https://forum.harrisonconsoles.com/archive/index.php/thread-561-2.html)) rather than peak-normalizing.
- **Normalize (or better, apply a limiter/peak-normalize) once, at the very end**, on the final summed+processed mix, purely to hit a target loudness/peak ceiling (e.g., –1 dBTP) — this step does not change the internal balance because it scales everything equally.

### Stereo width: widen drums/piano, narrow/mono the bass — yes, and there's a well-defined "why"

This is standard and well-documented technique, not a stylistic preference. The universal rule across every mixing source found: **keep everything below ~100–150 Hz mono**, because human localization of low frequencies is poor, so stereo bass content provides no perceptual width but does create phase-cancellation risk on mono playback systems (phones, club PA subs, Bluetooth) ([mixmasterpro.io stereo width guide](https://mixmasterpro.io/articles/stereowidth); [Mastering the Mix panning guide](https://www.masteringthemix.com/blogs/learn/guide-to-panning-and-stereo-width)). Concretely for this stem set:
- **Bass stem**: sum to mono entirely, or at minimum apply a mono-below-crossover (e.g., mono below 120–150 Hz using mid/side EQ that only high-passes the *side* channel, preserving any stereo content above that). "Keep kick, bass, and sub elements mono... zero exceptions" ([kernaudio.io stereo widening guide](https://kernaudio.io/guides/stereo/stereo-on-individual-tracks)).
- **Drums stem**: keep the kick/low content centered and mono; you *can* widen the hi-hat/cymbal content (which sits higher in frequency) using mid/side high-shelf boosts on the "side" channel (commonly 8–12 kHz) or subtle stereo imaging, but always with a mono-below crossover protecting the kick.
- **Piano / guitar / other stems**: safe to widen more freely since their energy is largely above the problematic low-frequency zone — mid/side widening, subtle chorus, or Haas-effect doubling are all reasonable, but always **check correlation** (aim to stay above +0.3 correlation on individual tracks, +0.5 on the full mix bus) and fold to mono to confirm nothing disappears ([kernaudio.io](https://kernaudio.io/guides/stereo/stereo-on-individual-tracks); [mixmasterpro.io](https://mixmasterpro.io/articles/stereowidth)).
- **Vocals** (if kept): should generally stay centered/narrow since they're the mix's spatial anchor — widening a lead vocal makes it sound unfocused.

A very concrete Python-applicable version of the safe approach is mid/side EQ that only touches the side channel: convert stereo to M/S (`mid = (L+R)/2`, `side = (L-R)/2`), apply a high-pass filter to `side` only (removing low-frequency side information without affecting the mono-safe mid content), then convert back (`L = mid+side`, `R = mid-side`). This "removes low end from the stereo image only, keeps everything mono-compatible" ([production tutorial on mid/side low-end management](https://www.youtube.com/watch?v=2U7KqnFFjDs)).

---

## 3. Drill Flip Aesthetic: What Makes It Sound Like "Drill"

### Typical pitch-down amount

Multiple independently-sourced tutorials and a genre breakdown converge on a **1 to 4 semitone downward pitch shift** as the common range for "flip" transformations, with larger drops (a full octave, 12 semitones) reserved for more extreme/creative sound-design moves rather than the norm. Specific data points:
- A Hindi-language FL Studio drill-remix tutorial: shifted the sample's scale up by 2 semitones for one section, then down 5 semitones ("5 semi tone niche") for another section within the same beat — demonstrating semitone-scale (not octave-scale) moves are typical within a single flip ([FL Studio Mobile drill remix tutorial](https://www.youtube.com/watch?v=MemqGqcVM48)).
- Drift Phonk — a closely related "dark, pitched-down" genre with heavy overlap in aesthetic to what's being targeted — is explicitly characterized by "lowering the pitch of the entire track by about -2 to -4 semitones" combined with heavy reverb to create a dreamlike/nightmarish atmosphere ([Phonk genre breakdown](https://note.com/soundwitches/n/nf5532d7ff868?hl=en)).
- Sample-flip pitch guidance generally frames "semitone increments" as the default unit of adjustment, with full-octave (12 semitone) shifts as a distinct, more dramatic category used deliberately for texture change rather than as the default move ([Producer's Bible sample-flip entry](https://musicproductionwiki.com/bible/sample-flip)).

Given the user's target of A major → G minor at roughly the same tempo, **the semitone distance from A to G is 2 semitones down** (A→G♯/A♭ is 1 semitone, G♯/A♭→G is 1 more), which conveniently sits squarely inside the "typical flip" and "drift-phonk-style dark pitch-down" range documented above (-2 to -4 semitones). This is a case where matching the target key coincidentally matches the aesthetically-typical pitch-down amount — reinforcing that -2 semitones (plus the major→minor mode change, discussed below) is a well-precedented, not extreme, choice.

**Important nuance — key change is not purely a pitch shift.** Moving from A major to G minor is not simply "pitch down by X semitones" in the way moving from A major to G major would be; it also changes the **mode** (major → minor), which alters the interval structure of the chords/melody, not just their absolute frequency. A uniform pitch-shift of an A-major instrumental down 2 semitones produces a G-major-sounding result, not G minor — the notes will be a whole shifted major scale, and won't automatically acquire the "minor" characteristic (flattened 3rd/6th/7th) that gives drill its dark character. Getting a true G *minor* feel from an A *major* source generally requires either (a) accepting that a straight pitch-shift only gets you to G major and layering in new minor-key elements (new 808 bassline in G minor, reharmonized pads) over the pitched instrumental, or (b) using pitch-mapping/retuning per-note (more DSP-intensive, typically not done via a single global `pitch_shift` call) if true minor reharmonization of the existing melodic stems is required. For a drill flip, the far more common and practical approach documented across tutorials is **(a)**: pitch/time-process the sampled material, then build a new dark, minor-key 808 bassline and hats on top in the target key — this is standard "sample flip" practice, not a limitation specific to this project.

### Half-time (drastically slower feel) vs. near-original tempo

The research is unambiguous that classic drill's *core tempo* sits much higher than the target 87 BPM, but is *felt* at roughly half that because of the genre's rhythmic pattern. Concrete data points:
- "Set your tempo around 140 BPM (felt as half-time)" ([Violet Recording drill workflow guide](https://violetrecording.com/how-to-make-drill-beats/)).
- "To make a modern UK or New York drill beat, start around 140–150 BPM and work in 4/4 with a heavy half-time feel" ([Beatstorapon drill beat guide](https://beatstorapon.com/blog/how-to-make-a-drill-beat-bpm-808s-drums/)).
- A tutorial explicitly: "just going to make a quick drill bit and set the temperature about 140... just going to start by putting half time on this" ([Ableton drill glides tutorial](https://www.youtube.com/watch?v=Ib7tOHaqdPo)).
- Range cited across FL Studio UK/US drill tutorials: "bpm between like 135 or 145" ([UK/US Drill Beats tutorial](https://www.youtube.com/watch?v=UqLYjlz2IOg)).

This creates a direct implication for the user's ~87 BPM target: **87 BPM is not "drill tempo" in the conventional sense (140-150 BPM), but it is very close to half of that range (140/2 = 70, 150/2 = 75) is not quite 87 either.** The practical read: 87 BPM sits between a "half-time drill feel" (roughly 70–75 BPM equivalent) and a slower boom-bap/trap tempo. For a "drill flip" specifically (as opposed to a from-scratch drill beat), producers commonly work with whatever tempo the sample naturally lands at once pitched/stretched, and impose the *drill sonic signature* (hi-hat pattern, 808 slides, dark minor tonality, sparse arrangement) rather than forcing the tempo to exactly match a canonical drill BPM. Given the near-original 87 BPM target (barely 2 BPM off the source's 89 BPM), this reads as more of a **"trap/dark remix with drill-adjacent drum programming"** than a literal half-time drill flip — which is a perfectly valid and common target; it just means the half-time low end (808 slides, sparse hats) should be *layered in via new drum programming*, not derived from literally halving the tempo of the existing instrumental.

### Standard FX chain and ordering

Consolidated from multiple drill-specific vocal chains and general mixing-chain-order guides ([abstraktmusiclab.com vocal mixing guide](https://abstraktmusiclab.com/vocal-mixing-guide/); [production tutorial: plugin order](https://www.youtube.com/watch?v=i1wW0Pl8Aw8); [production tutorial: vocal chain order](https://www.youtube.com/watch?v=xpaAijC4By0); [UK Drill vocal mixing walkthrough](https://www.youtube.com/watch?v=SvxpYKK8k9M)), the standard order — applicable to instrumentals with only minor adaptation — is:

1. **Gate/noise reduction** (only relevant for recorded stems with noise floor; less applicable to Demucs output but useful if separation artifacts introduce low-level noise)
2. **Subtractive EQ (high-pass / cut problem frequencies)** — always first, so every later stage "hears" a cleaner signal
3. **Compression (dynamics leveling)** — evens out the level before saturation/character stages act on it
4. **Additive EQ** (boost the frequencies you want to feature, now that problems are removed)
5. **Saturation / distortion** ("character" stage) — added after leveling so the harmonic content it generates is applied to an already-controlled signal; a widely-cited justification: saturation adds new frequency content, so if you saturate too early, later subtractive EQ has to fight harmonics you just created ([Vocal Chain Order Matters tutorial](https://www.youtube.com/watch?v=xpaAijC4By0)) — though some engineers do prefer a light saturation pass at the very front purely to add a bit of "grit"/character before the leveling stages; if used this way it should be very subtle and immediately followed by the corrective EQ/compression stages.
6. **Reverb / delay (time-based effects), always last, on a send/return not an insert** — because you want the reverb tail itself to carry the "flavor" of everything that happened before it (the saturation grit, the EQ shape), not a pre-effects dry version. "Any kind of EQ'ing or compression is going to have an effect on not just the dry vocal but the reverb and delay effects as well" if placed after ([Vocal Chain Order Matters tutorial](https://www.youtube.com/watch?v=xpaAijC4By0)).

For the **instrumental as a whole** (as opposed to individual stems), a practical drill/trap-flavored chain, applied in order:
```
High-pass problem stems (per Section 2) 
  → Compress each stem lightly for leveling
  → Sidechain-duck bass/other against kick 
  → Sum stems 
  → Bus-level saturation/distortion (subtle, for "dark/dirty" character — a light tape or tube-style saturator, not hard clipping) 
  → Bus EQ (final tonal shaping — often a gentle low-mid scoop around 250-400 Hz for "clarity," per the muddy-mix-fix guidance in Section 2) 
  → Reverb send (short room/plate for glue, used sparingly — drill/dark trap generally favors "leave space" over washy reverb, per genre notes below) 
  → Final limiter/compressor for loudness
```

### The 808/bass relationship in drill

This is one of the most consistently repeated technical points across every drill production source consulted:
- **Tune the 808 to the song's key** and treat kick+808 as a single low-end system rather than two competing sounds: "mix the kick and 808 as one low-end system instead of two competing sounds" ([Beatstorapon drill guide](https://beatstorapon.com/blog/how-to-make-a-drill-beat-bpm-808s-drums/)).
- **Sidechain the 808/bass to the kick**, high-pass melodic elements to clear room for the sub, keep lows mono and tight: "Drill needs a powerful, clean low end dominated by the 808. Sidechain the 808 to the kick, high-pass your melodies and hats to clear room for the sub, and keep the lows mono and tight" ([Violet Recording drill workflow guide](https://violetrecording.com/how-to-make-drill-beats/)).
- **Use "cut itself" / mono legato behavior** so 808 notes don't overlap and create mud when sliding between pitches — a dedicated technique for programming the signature drill 808 glide: set the instrument to monophonic so a new note cuts off the previous one rather than layering, verify the sample is correctly tuned to its labeled root note via pitch detection, then use portamento/slide between notes for the melodic bend ([Ultimate Guide to Drill 808 Slides](https://www.youtube.com/watch?v=pIYuTCBCJqw&vl=en); [UK Drill 808 Patterns tutorial](https://www.youtube.com/watch?v=27Pa0_winIY)).
- **Long 808 samples with tailored envelope**: turn down attack/decay/sustain/release and max out "hold" so the 808 sustains cleanly through its slide without unwanted volume shaping fighting the pitch bend ([wavgrind.com drill production guide](https://wavgrind.com/blogs/music-production/how-to-produce-drill-beats)).
- **A hard, punchy kick layered on top of the 808's attack** so the low end still punches through small speakers even though the 808 itself carries the sustained pitch content ([UK/US Drill Beats tutorial](https://www.youtube.com/watch?v=UqLYjlz2IOg)).

For the user's specific project — since a real 808 is not part of the Demucs stem set — this implies the **bass stem should be treated as the "808 equivalent"**: keep it mono/tight below ~150 Hz, sidechain it against the drums stem's kick transients, and if the drill character needs more presence, consider layering a synthesized 808 or sub tone tuned to G (the target key) underneath the pitched/processed bass stem rather than relying purely on the stretched original bass.

### Arrangement/darkness characteristics beyond FX

Repeatedly noted structural traits worth carrying into the remix, even though they're arrangement decisions rather than DSP: **sparse, minor-key melodic content that leaves gaps** ("leave space — drill is rhythmically busy in the hats but sparse elsewhere, don't overcrowd the beat," [Violet Recording](https://violetrecording.com/how-to-make-drill-beats/)); reversed or otherwise processed sample chops for an eerie quality; and restrained reverb use — a touch of reverb for space, not a wash, since drill's dark character comes more from minor tonality and space than from lush ambience.

---

## 4. Programmatic / Python-Native Remix Projects

Several open-source, Python-based, stem-aware remix tools exist and are directly relevant as either reference implementations or usable building blocks:

- **[jurihock/remucs](https://github.com/jurihock/remucs)** — the closest existing tool to exactly this use case. It's a `pip install`-able CLI wrapper around Demucs that "extract[s] the individual stems from a mix and remix them again in a certain way, e.g. by adjusting the volume gain, left-right channel balance and... applying **transient-preserving pitch shifting**." It exposes a `-p`/`--pitch` flag taking semitones+cents (e.g. `-12`, `+3-50`) and an experimental `-a`/`--a4` flag to auto-estimate a pitch-shift factor from a target tuning reference frequency. Its stem set is restricted to drums/bass/vocals/other (the 4-stem Demucs default), so it would need light modification to handle the 6-stem `htdemucs_6s` output including guitar/piano, but its **transient-preserving pitch-shift-per-stem-then-remix architecture is exactly the right shape for this project** and is worth reading as source code even if not used directly.

- **[Chunduri-Aditya/ai-remixmate](https://github.com/Chunduri-Aditya/ai-remixmate)** — a "real-time DJ engine that takes two songs and renders a beat-locked transition between them. BPM-matched, key-aware, stem-separated, mastered to broadcast LUFS standards," built with Demucs stem separation, dynamic EQ fades, and FastAPI/Streamlit. Useful primarily as an example of a full-pipeline architecture (analysis → stem separation → DSP → mastering) in idiomatic Python, though its specific goal (song-to-song transitions) differs from single-track remixing.

- **[faroit/stempeg](https://github.com/faroit/stempeg)** — Python I/O for the STEM container format (multi-stream audio files playable with per-stem selection in players like VLC); useful for packaging/distributing the final stems but not a DSP tool itself.

- **[samim23/polymath](https://github.com/samim23/polymath)** — converts a music library into a searchable sample library by separating stems, quantizing them to a common tempo/beat grid, analyzing musical structure/key, and converting audio to MIDI. Useful reference for the "quantize multiple stems to a common tempo/grid" sub-problem, though it's aimed at building a sample library rather than producing a single finished remix.

- **[spleeter](https://pypi.org/project/spleeter/)** (Deezer) — an alternative source-separation engine to Demucs (TensorFlow-based, offers 2/4/5-stem models). Not directly relevant unless dissatisfied with Demucs' 6-stem output quality, but worth knowing as the other major open-source separation option.

No large, actively-maintained, general-purpose "drill flip" specific automation framework was found — this is a genuinely under-tooled niche, meaning **remucs is the most directly transferable prior art**, and the user's own pipeline (once the segmentation bug is fixed) is a reasonable, largely correct approach that simply needs the specific fixes detailed in Sections 1 and 5.

---

## 5. Alternative Architectures — Which Order of Operations Is Actually Best?

This is the highest-leverage question, because it determines whether the artifacts come back even after switching to whole-buffer processing. There is directly relevant, though somewhat conflicting, first-hand production experience on this exact question:

### (a) Stretch the original mix first, then separate stems from the stretched audio

**Arguments in favor**, backed by direct testimony: a producer reported that "Time warping on this current tune is so bad (hollow sounding) on the stems that I just realized I might be better off time-warping the entire track, exporting it, and *then* extracting the stems after the time warp," with the community response confirming the cause: warping individual stems is "mostly cause[d] by the artefacts on those stem splitters... you need the transients to properly stretch/warp" ([Facebook Ableton Live Users group thread](https://www.facebook.com/groups/abletonliveusers/posts/25261854966831462/)). The mechanism here is that transient-detection-based stretching algorithms (which Rubber Band is) work best when they can see the **full-band transient content** (kick+snare+hats+bass+melodic attack all together, as in the original mix) to correctly identify note/beat onsets; splitting into stems first removes cross-stem transient information that can help the algorithm anchor itself, and stem separation itself introduces subtle artifacts/bleed that a phase vocoder can "hear" as extra false transients or missing energy at expected transient points.

**Arguments against**: separating stems from an already pitch/time-shifted signal means Demucs (trained on natural-tempo, natural-pitch music) is now being asked to separate a signal outside its training distribution, which could very plausibly reduce separation quality/fidelity (more bleed, more artifacts in the "other"/"piano" stems especially, which are already the weakest-performing stems per Demucs' own documentation). No direct evidence was found either confirming or ruling out meaningfully worse Demucs performance on pitch/time-shifted input, but it is a real theoretical risk given Demucs' HT-Demucs architecture relies on learned spectral/waveform patterns tuned to natural musical timing.

### (b) Separate stems first, process each stem individually, then sum

**Arguments in favor**: this is what `remucs` does, and one production-forum comment specifically prefers stem-first because "you also have the option to use different time stretching algorithms on different tracks, so you could, for example, use one algo for drums and a different one for vocals" ([Steinberg forum: best workflow for tempo correction + stem extraction](https://forums.steinberg.net/t/best-workflow-correct-tempo-and-extract-stems-remix/1013175/3)) — same poster also states stem-first "results in better sounding stems and... improves the tempo mapping process... since it's often easier to analyze... with just the drum track" (referring to *tempo detection/analysis* being easier on an isolated drum stem, not necessarily that *stretching* per stem sounds cleaner). This matters for this project because different stem types genuinely benefit from different transient-handling settings — Rubber Band's `transient_mode='crisp'` suits the drums stem, while a more `'smooth'` setting suits the piano/other stems, which is only possible if stretching per-stem.

**Arguments against**: this is precisely the architecture that produced "hollow" results in the counter-example above, and is closer (though not identical) to the user's own failing approach — the key difference being the user segmented *within* a stem (8-beat chunks), whereas per-stem-whole-buffer stretching keeps each individual stem as one continuous phase-coherent buffer. **The failure mode described in the "hollow" report was specifically about per-stem warping in a DAW using warp markers on separated stems, which is architecturally different from segment-and-crossfade** — it's a caution that stem separation itself can degrade stretch quality somewhat, not a repeat of the boundary-artifact bug.

### (c) Use the Demucs "other" stem directly instead of summing 5-6 stems

Demucs' "other" stem is defined as "everything else (keys, synths, FX)" not captured by the vocals/drums/bass/(guitar/piano) heads ([Hugging Face `htdemucs-6s-onnx` model card](https://huggingface.co/StemSplitio/htdemucs-6s-onnx)). Critically, **"other" is explicitly documented as the lowest-quality, most artifact-prone stem** of the whole set: "The 'Other' category is the most challenging, showing lower scores due to its diverse content of residual instruments" in one benchmark analysis, and per-stem SDR figures for the 6-stem ONNX model show "other" at only ~5.5 dB vs. ~9.5 dB for drums and ~9.0 dB for bass — "lower because the model now also predicts guitar + piano" ([StemSplitio htdemucs-6s-onnx model card](https://huggingface.co/StemSplitio/htdemucs-6s-onnx)). This directly contradicts the premise in the question that "other" is "often clean instrumental backing" for the 6-stem model specifically — with 6 stems, "other" is a *residual* category (whatever isn't drums/bass/vocals/guitar/piano), not a clean pre-mixed instrumental bed. Using "other" alone would drop the actual drums and bass entirely from the mix, which is not viable for a drill/trap flip where the drum and 808/bass relationship is the genre's defining feature (Section 3). **This option should be rejected** — "other" from the 6-stem model is a thin, artifact-heavy residual bucket, not a usable clean instrumental. (Note: the classic *4-stem* `htdemucs` model's "other" stem is a much richer bucket — everything non-drum/bass/vocal, including all melodic/harmonic content — and closer to what the question envisions, but the user is explicitly working with the 6-stem `htdemucs_6s` output, where this doesn't hold.)

### Practical recommendation, synthesizing the evidence

Given the conflicting-but-reconcilable evidence, the best-supported architecture is a **hybrid** that captures the benefit of both (a) and (b) while avoiding both documented failure modes:

1. **Sum all 6 stems back into a full mix first** (this recovers the full-band transient information that helps Rubber Band's transient detector, addressing the "hollow" per-stem-warping problem) — but do this summation with the light corrective EQ/leveling from Section 2 already applied per stem, so the summed signal is clean.
2. **Time-stretch + pitch-shift that one summed buffer, once, with `pedalboard.time_stretch`** on the whole 5-minute file (this is the direct fix for the boundary-artifact bug and gets the primary quality benefit reported in the "stretch the full mix" testimony).
3. If stem-level creative control is still needed after that (e.g., wanting the drums stem punchier or the bass tighter than what one global chain achieves), **re-separate the now-stretched/pitched instrumental with Demucs again** and apply final, targeted per-stem EQ/compression/width (Section 2) to the *already correctly pitched/timed* stems before the final sum — since this second separation pass only needs to support mixing-stage EQ/compression, not further time-based DSP, any residual separation artifacts from processing "off-distribution" audio are far less consequential than they would be if you tried to run the pitch/time-stretch itself on separated stems.

This ordering — **stretch/pitch the full mix once → (optionally) re-separate only for final mix-bus EQ/width shaping → sum → master** — directly targets the root cause of the reported artifacts (phase discontinuity from segment-by-segment independent stretching) while still preserving the ability to do stem-aware EQ/width work from Section 2.

### Minimal, concrete Python implementation of the recommended pipeline

```python
import numpy as np
from pedalboard.io import AudioFile
import pedalboard
from pedalboard import Pedalboard, HighpassFilter, LowpassFilter, Compressor, Gain

SR = 44100.0
STEM_DIR = "separated/htdemucs_6s/track"  # demucs output folder
STEMS = ["drums", "bass", "other", "vocals", "guitar", "piano"]

def load_stem(name):
    with AudioFile(f"{STEM_DIR}/{name}.wav").resampled_to(SR) as f:
        return f.read(f.frames)  # shape: (channels, samples)

# --- Step 1: light corrective EQ per stem BEFORE summing (Section 2) ---
stem_boards = {
    "drums":  Pedalboard([HighpassFilter(cutoff_frequency_hz=30)]),
    "bass":   Pedalboard([LowpassFilter(cutoff_frequency_hz=8000)]),  # keep bass tight, no HPF
    "other":  Pedalboard([HighpassFilter(cutoff_frequency_hz=150)]),
    "guitar": Pedalboard([HighpassFilter(cutoff_frequency_hz=120)]),
    "piano":  Pedalboard([HighpassFilter(cutoff_frequency_hz=100)]),
    "vocals": Pedalboard([HighpassFilter(cutoff_frequency_hz=100)]),  # omit vocals entirely for an instrumental flip
}

stems = {name: load_stem(name) for name in STEMS}
processed = {}
for name, audio in stems.items():
    board = stem_boards.get(name, Pedalboard([]))
    processed[name] = board(audio, SR)

# --- Step 2: manual gain balance (NOT peak-normalization, Section 2) ---
gain_db = {"drums": 0, "bass": -1, "other": -3, "guitar": -4, "piano": -4, "vocals": -100}  # drop vocals for instrumental
def apply_gain(audio, db):
    return audio * (10 ** (db / 20))

mix = sum(apply_gain(processed[name], gain_db[name]) for name in STEMS)

# --- Step 3: whole-buffer stretch + pitch shift ONCE (Section 1 fix) ---
stretch_factor = 87.0 / 89.0
pitch_shift_semitones = -2.0  # A -> G

stretched = pedalboard.time_stretch(
    input_audio=mix,
    samplerate=SR,
    stretch_factor=stretch_factor,
    pitch_shift_in_semitones=pitch_shift_semitones,
    high_quality=True,
    transient_mode="crisp",
    retain_phase_continuity=True,
    preserve_formants=True,
)

# --- Step 4: bus-level dark/drill character (Section 3 FX order) ---
final_board = Pedalboard([
    Compressor(threshold_db=-18, ratio=3.0),
    Gain(gain_db=1.0),
])
final_mix = final_board(stretched, SR)

with AudioFile("drill_flip_final.wav", "w", SR, final_mix.shape[0]) as f:
    f.write(final_mix)
```

This structure fixes the reported bug (single whole-buffer stretch call, no segmentation, no crossfading of independently-processed chunks) while incorporating the stem-EQ/gain-balance best practices from Section 2 and the FX-ordering guidance from Section 3. A dedicated 808/bass synthesis layer in G minor, and drill-style hi-hat programming, would sit on top of this instrumental as new MIDI/sample-based elements — not derived from the pitched/stretched stems — consistent with how actual drill flips are built (Section 3).

---

## Key Takeaways

1. **The root cause of the warbling/phase artifacts is segmenting before stretching.** Rubber Band (and every phase-vocoder-based algorithm) needs a continuous buffer to maintain phase coherence; independent per-segment calls reset that state at every boundary, and crossfading cannot repair a phase mismatch, only mask it partially.
2. **`pedalboard.time_stretch()` run once on the full mix is the most direct fix** — it's the same underlying Rubber Band engine, requires no compilation (unlike FFmpeg's `rubberband` filter), and supports independent pitch+tempo control with formant preservation and configurable transient handling.
3. **Per-stem EQ before summing is standard and necessary** — high-pass melodic/other stems around 100–250 Hz, keep the bass stem's low end intact and mono, sidechain bass against the kick, and never peak-normalize individual stems (balance by ear/RMS gain instead).
4. **The 87 BPM target is closer to a dark trap/half-time-adjacent tempo than canonical drill (140–150 BPM felt half-time)** — treat this as a "dark instrumental flip with drill-style drum/808 programming layered on top" rather than a literal halved-drill-tempo track, and note that A major → G minor requires new minor-key elements, not just a uniform pitch shift, to get the mode change right.
5. **Sum stems back into a full mix before stretching**, based on direct testimony that per-stem warping produced "hollow" results while whole-track warping did not; re-separate only afterward, if at all, for final mix-bus polishing.
6. **Avoid using Demucs' 6-stem "other" as a standalone instrumental** — it's the lowest-fidelity residual stem in the 6-stem model (~5.5 dB SDR vs. ~9+ dB for drums/bass), not a clean backing track.
