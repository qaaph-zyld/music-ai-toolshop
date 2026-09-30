# OGCM S6R: street-rap x synthwave x organ stabs (research only)

Date 2026-10-01. [Sn] = source, URLs in the legend at the end. Confidence: H/M/L. INF = my inference, no source. Streaming-analyzer BPMs are algorithmic and double/half-time prone (M).

## Summary
- The Cratez produced Bonez "Hollywood" and most of "Sampler 5": layered synths, 808 glides, boom-bap/trap blend. No public breakdown of stab rhythms, organs or synthwave exists (Unknown); the stab grids are INF.
- Camp tempos cluster ~85-100 (half-time) and 118-144 (straight); 105 BPM sits between them and inside synthwave's 80-120.
- Night-drive: 8th-note octave saw+square+sub bass, ~140 ms filter decay, quarter-note pump 3-6 dB (subtle) to 10-15 dB (obvious).
- Organs: string machine = 3-line ensemble (0.6 + 6 Hz); combo = square footages + bright filter; Hammond = ratios 0.5..8, ~3 dB/step, Leslie 0.83 / 6.67 Hz.
- Suno: uploads 60 s Basic / 8 min Pro; Extend keeps the original; artist names and trademarks can block a prompt. All prompts below are under 200 characters.

## Q1 Street-rap signatures
**Who (H).** The Cratez = David Kraft and Tim Wilke; they produced all 13 "Hollywood" tracks, 14/15 of "Sampler 5", 13/15 of "Palmen aus Plastik 2" [S1,S2,S3]. Other 187 producers: Jambeatz, Lukas H, 95a, P.M.B. [S2,S4]; "Ohne mein Team" is RAF Camora's, not Cratez [S6].

**Tempo (M).** Half-time feel: 187 Gang 174 (half 87) [S7]; Kokain 170 [S8]; Ebbe & Flut 87 [S10]; Roadrunner 99 [S9]; Millionär 93, Panik 97 [S8]. Straight: Lächeln 118, Lebenslauf 123, Mit den Jungz 126, CL500/Diskutieren 132, Sitzheizung 136, Wolke 7 138 [S8,S10]; Was du Liebe nennst (Cratez co-prod, pop-rap) 144-145 [S11]. INF: 105 BPM is a plausible crossover tempo.

**Melodic instruments.**
- Cratez: "vielschichtige Arrangements", "atmosphärische Synthie" (M) [S12]; fat 808s with glide, selected samples, boom-bap plus trap, influences 9th Wonder, DJ Premier, Boi-1da, Lex Luger (M) [S13]; Kraft says hip-hop/house/schlager no longer separable (M) [S14].
- "Hollywood" = rap plus dancehall, "Roadrunner" called poppig (M) [S15]; "Sampler 5" review: old-school atmosphere missing (M) [S2].
- Organs: no Cratez organ evidence found = Unknown. Adjacent only: "Gefährlich" (prod. P.M.B., not Cratez) samples Symarip "Skinhead Moonstomp" (M) [S16], a skinhead-reggae record with Hammond-style organ leads (M) [S17]; which element is sampled is unverified (L). "Kokain" (Cratez+RAF) samples La Bouche "Be My Lover", 90s Eurodance (M) [S18].
- Synthwave/80s colour, pianos, bells, plucks: Unknown. The Cratez "Winter Blues" making-of is video-only [S12].

**Chord rhythm.** Unknown (no public grids). INF: syncopated 3+3+4+3+3 and 3+3+2+3+3+2 groupings, used in the final block.

**Bass.** 808 with glide (M) [S13]; driving 8th bass for this camp: Unknown. INF: one short Bb-to-D glide at bar 8 as the nod.

**Loop energy devices.** Unknown. INF: denser stabs in bar 2, bar-8 stab roll, deeper pump late.

## Q2 Synthwave palette
**Tempo (H/M).** 80-118 typical, 128-140 upbeat [S19,S20]; 80-120 [S21].

**Bass patterns.** 16th-note sequenced bass and octave bass lines trace to Moroder/Hi-NRG (M) [S23]; bass follows chord roots with small variations [S22] (M). INF: 8th-note low/high octave bounce at 105 BPM (8th = 285.7 ms).

**Bass recipe (M).** Two saws an octave apart, LPF 727 Hz, filter decay 2.5 s (pluck) [S25]; Moroder square/PW64, filter decay 423 ms, res 32, sustain 0 [S26]; saw+square -12 st, unison 15-18%, sine -24 [S24]. Table values are INF, scaled to 8ths.

**Pump.** Subtle 1-3 dB, creative start 5 dB, attack under 2 ms, release quarter-note-aligned, 60000/BPM ms (M) [S27]; obvious pump 10-15 dB, pads 3-5 dB with 250-400 ms release (L) [S28]. At 105 BPM a beat is 571.4 ms. INF design: bass -6 dB, pad -9 dB, stabs -2 dB, attack 5 ms, release 0.6 beat (343 ms), exponential recovery.

**Reverb/delay (M).** Long reverb, gated snare reverb, send/return with pre-delay and low cut, Juno-style chorus, bass mono below 100-120 Hz [S20,S21,S22]; dotted-8th delay on plucks (428.6 ms at 105). INF: hall 2.2 s, pre-delay 25 ms, return HP 200 Hz, wet -16 dB; tails under one beat.

### Organ recipes (stab vs pad priority in last column)
| Type | Parameter and value | Conf | Matters most |
|---|---|---|---|
| String machine | Divide-down from 12 generators, saws 16'/8'/4' weights 0.3/1/0.6 [S29] | M | Stab: 8'+4' only. Pad: add 16' |
| | 3 delay lines, LFO phase 0/120/240, slow 0.6 Hz + fast 6.0 Hz, mix 79% slow / 21% fast [S31]; RS-202 0.66/6.25 Hz [S32]; measured Solina ~0.8/6.4 Hz [S33] | M | Pad: slow rate/depth. Stab: mostly inaudible (under 1 cycle of 6 Hz) |
| | INF depth slow +-2.5 ms, fast +-0.3 ms around 6 ms | L | |
| | No filter, AR envelope only [S30]; INF LPF 5 kHz, stab A10/R150 ms, pad A300/R800 | M/L | Stab: attack, release |
| Combo organ | Square wave plus dividers (Farfisa-like raspy), Vox thinner/sine-like [S34,S35]; footages 16'/8'/4' + 2' (Vox), INF weights 0.25/1/0.7/0.35 | M/L | Stab: footage balance |
| | Farfisa switched passive filter [S34]; INF HP 150 Hz, +4 dB at 2.8 kHz, LPF 6.5 kHz | L | Stab: filter peak |
| | Vibrato simple on/off on Vox [S34]; INF 5.5 Hz, +-8 cents, onset delay 120 ms | L | Pad only |
| | Percussive attack (G-101 "harpsichord-like") [S35]; INF stab A 2 ms, decay to 70% in 50 ms, R 60 ms; pad A 15 / R 250 | L | Stab: attack, release |
| Drawbar | Ratios 16' 0.5, 5 1/3' 1.4988, 8' 1, 4' 2, 2 2/3' 2.9976, 2' 4, 1 3/5' 5.0409, 1 1/3' 5.9953, 1' 8 [S36] | H | All |
| | ~3 dB per step (amp 1, .708, .501, .355, .251, .178, .126, .089 for 8..1) [S37] (commenter measured 3-6 dB) | M | Registration shape |
| | 888000000 (Jimmy Smith, percussion 3rd soft fast); 008800000 (subdued jazz); 888611348 ("funk shots", rhythmic stabs) [S38]. INF: first = bite, second = no sub-octave clash with octave bass, third = bright accents | M | Stab |
| | Percussion: 2nd/3rd harmonic of 8', fast ~1 s, slow ~4 s (L) [S39]; single-trigger [S40]. INF: stab 3rd at 0.5x; pad off | M/L | Stab: level |
| | Key click: a few ms; emulate as envelope on 6th harmonic (Pekonen 2011) [S41]. INF: 5.9953 f burst, decay 6 ms, -18 dB, plus HP noise 1.5 ms at -26 dB | M/L | Stab: essential |
| | Scanner vibrato fixed 7 Hz [S36]; omit with Leslie | H | Pad |
| | Leslie crossover 800 Hz; chorale horn ~50 rpm (0.83 Hz), drum ~40 (0.67); tremolo horn ~400 rpm (6.67 Hz), drum ~340 (5.67) [S42] | M | Both |
| | Horn radius ~0.15 m [S43, snippet] gives derived Doppler +-4 cents slow, +-31 cents fast, delay swing +-0.44 ms; Doppler 90 degrees from AM [S44] | M | |
| | INF: horn AM +-3 dB, drum +-1.5; two horn mics [S42] so L/R LFO phase 90 degrees. Stab: fast rotor, depth halved, random start phase; pad: slow, full depth | L | Stab: phase |

## Q3 Suno (public docs only)
- **Upload limits (H/M).** Basic 60 s; Pro/Premier up to 8 min [S45,S46]. Older pages say 6-60 s and 120 s Pro (stale, L) [S47]. An 8-bar loop at 105 BPM is 18.3 s, fits every tier.
- **Extend (H).** Upload, Library, Extend; set style, title, extend-from time; original stays tagged "Uploaded", new part "Part 2" [S47]. **Cover (H):** keeps melody, restyles, accepts instrumentals [S48]. **Audio Influence** slider appears with uploads; range undocumented officially [S49]; third-party suggests ~55-65% for loops (L) [S53].
- **Drumless input.** Official example extends a drum loop; drumless is not addressed (Unknown). INF: drumless leaves room for Suno to add a beat; prefer Extend (keeps audio) over Cover; the quarter-note pump hints kick spots.
- **Copyright.** Copyrighted works are blocked on upload (M) [S50]; you confirm ownership [S47]. Our loop is original synthesis.
- **Artist names (H).** Names of well-known artists or people, and copyrighted/trademarked terms, can stop generation [S51]. Describe era, genre, instruments, mood, tempo instead (L) [S54]. INF: avoid brand words (Hammond, Farfisa, Solina, Leslie).
- **Style field (M).** 1,000 chars on v4.5+, 200 on v4 and older [S52]; under 200 is safe everywhere. Third-party: 4-7 descriptors, use Exclude rather than "no drums" (L) [S53].

## Stab pattern recommendation
105 BPM, 16th steps 1-16, beat = steps 1/5/9/13. Velocity 1-9, dot = rest (INF).
- Bar 1 Dm7 (F3 A3 C4 D4): `x..x..x...x..x..`  velocity `9..6..8...5..7..`
- Bar 2 Bbmaj7 (F3 A3 Bb3 D4): `x..x..x.x..x..x.`  velocity `8..5..7.9..5..6.`
- Gate: vel 8-9 = 200 ms, 6-7 = 110 ms, 1-5 = 80 ms. Pump ducks stabs only 2 dB, so step 1 still hits.

## Organ + bass + pump parameter table
| Item | String machine | Combo | Drawbar |
|---|---|---|---|
| Osc | saws 16'/8'/4' = 0.3/1/0.6 (stab 8'+4') | 50% pulse 16'/8'/4'/2' = 0.25/1/0.7/0.35 | ratios 0.5,1.4988,1,2,2.9976,4,5.0409,5.9953,8 |
| Registration | n/a | n/a | R1 888000000+perc 3rd 0.5x (main), R2 008800000, R3 888611348 (accents) |
| Env stab / pad | A10 R150 ms / A300 R800 | A2 R60 ms / A15 R250 | A3 R70 ms / A8 R400 |
| Modulation | ensemble 0/120/240, 0.6+6.0 Hz, 79/21, +-2.5/+-0.3 ms | vibrato 5.5 Hz +-8 cents, pad only | Leslie horn 0.83/6.67, drum 0.67/5.67, xover 800 Hz, AM +-3/+-1.5 dB, Doppler +-0.44 ms, 90 deg |
| Tone | LPF 5 kHz | HP 150, +4 dB 2.8 kHz, LPF 6.5 kHz | key click 6th harmonic 6 ms -18 dB + noise 1.5 ms -26 dB |

| Bass and pump | Value |
|---|---|
| Pattern | 8ths, low/high octave: `8.6.8.6.8.6.8.6.` D2/D3 bar 1, Bb1/Bb2 bar 2 |
| Osc | saw -12, square -12, sine -24 at -6 dB |
| Filter | LPF24 base 350 Hz, env +2.2 oct (~1.6 kHz), decay 140 ms, Q 1.2 |
| Amp | A 3 ms, gate 75% of 8th (214 ms), R 30 ms, soft clip +4 dB |
| Pump | beats 1-4, bass -6 dB, pad/strings -9 dB, stabs -2 dB, attack 5 ms, release 343 ms exponential |
| FX | hall 2.2 s, pre-delay 25 ms, return HP 200 Hz, wet -16 dB; dotted-8th delay 428.6 ms |

## Suno style prompt
- Primary (167): `German street rap x synthwave night drive, energetic, hard trap drums, organ stabs, driving octave synth bass, gritty male rap vocals, dark neon mood, 105 BPM, D minor`
- Alt 1 (170): `Gritty German gangsta rap meets 80s synthwave, neon midnight drive, retro organ chord stabs, pulsing octave saw bass, punchy 808 drums, raspy male rap, energetic, 105 BPM`
- Alt 2 (169): `Aggressive German rap over retro synthwave, combo organ stabs, pumping sidechain bass, tight trap hi-hats, hard kick, dark cinematic night drive, male rap vocal, 105 BPM`

Note: search results about bypassing upload filters were seen and ignored (out of scope).

## Source legend
S1 https://de.wikipedia.org/wiki/The_Cratez | S2 https://de.wikipedia.org/wiki/Sampler_5 | S3 https://en.wikipedia.org/wiki/Palmen_aus_Plastik_2 | S4 https://en.wikipedia.org/wiki/187_Strassenbande | S6 https://en.wikipedia.org/wiki/Ohne_mein_Team | S7 https://songbpm.com/@bonez-mc/187-gang | S8 https://tunebat.com/Info/Kokain-Bonez-MC-RAF-Camora-Gzuz/1H3oIeKUEHpBhXUiso0IMH , https://tunebat.com/Info/Sitzheizung-187-Strassenbande-Gzuz-Bonez-MC/42HI1CnQ4meVfZCTSwZK0n , https://tunebat.com/Info/Lebenslauf-Bonez-MC-Gzuz/01dCuK62A6QZ8L9ONTyMVo (search snippets, page fetch 403) | S9 https://songbpm.com/@bonez-mc/roadrunner | S10 https://songbpm.com/@gzuz/ebbe-flut | S11 https://getsongbpm.com/song/was-du-liebe-nennst/z6WGrq | S12 https://juice.de/breakdown-the-beat-the-cratez-video/ | S13 https://hiphop.de/magazin/hintergrund/deutschraps-platinmaschinerie-the-cratez-im-portrait-313709 | S14 https://omr.com/de/daily/the-cratez-producer-omr-podcast | S15 https://laut.de/Bonez-MC/Alben/Hollywood-115110 | S16 https://www.whosampled.com/sample/542326/Gzuz-Bonez-MC-Gef%C3%A4hrlich-Symarip-Skinhead-Moonstomp/ | S17 https://shit-fi.com/skinhead_reggae | S18 https://www.whosampled.com/sample/595624/Bonez-MC-RAF-Camora-Gzuz-Kokain-La-Bouche-Be-My-Lover/ | S19 https://en.wikipedia.org/wiki/Synthwave | S20 https://output.com/blog/best-plugins-for-synthwave | S21 https://create.routenote.com/blog/how-to-make-synthwave-beats/ | S22 https://www.edmprod.com/how-to-make-synthwave/ | S23 https://en.wikipedia.org/wiki/Hi-NRG | S24 https://www.syntorial.com/tutorials/synthwave-bass/ | S25 https://reverbmachine.com/blog/how-kavinsky-created-nightcall/ | S26 https://www.musicradar.com/tuition/tech/how-to-make-a-giorgio-moroder-style-bassline-209902 | S27 https://mastering.com/sidechain-compression-guide/ | S28 https://www.myloops.net/sidechain-compression-techniques-for-trance | S29 https://en.wikipedia.org/wiki/String_machine | S30 https://en.wikipedia.org/wiki/ARP_String_Ensemble | S31 https://till-kopper.de/logan_string_melody.html | S32 https://www.florian-anwander.de/roland_string_choruses/ | S33 https://www.dragonflyalley.com/synth/constructionJHTripleChorus.htm (snippet) | S34 http://sandsoftwaresound.net/tag/combo-organ/ | S35 https://en.wikipedia.org/wiki/Combo_organ | S36 https://electricdruid.net/technical-aspects-of-the-hammond-organ/ | S37 https://www.stefanv.com/electronics/hammond_drawbar_science.html | S38 https://www.hammondtoday.com/category/drawbar-settings/ | S39 https://organforum.com/forums/forum/electronic-organs-midi/hammond-organs/36949-percussion-decay-times-on-b3-c3 | S40 https://en.wikipedia.org/wiki/Hammond_organ | S41 https://pubs.aip.org/asa/jasa/article/142/5/2808/685076/Dynamic-temporal-behaviour-of-the-keyboard-action | S42 https://en.wikipedia.org/wiki/Leslie_speaker | S43 https://ccrma.stanford.edu/~jos/doppler/doppler.pdf (snippet, PDF not parsed) | S44 https://www.soundonsound.com/techniques/synthesizing-rest-hammond-organ-part-1 | S45 https://help.suno.com/en/articles/6141569 | S46 https://about.suno.com/release-notes | S47 https://help.suno.com/en/articles/2477633 | S48 https://suno.com/blog/covers | S49 https://help.suno.com/en/articles/6141377 | S50 https://suno.com/blog/audio-inputs | S51 https://help.suno.com/en/articles/3198209 | S52 https://docs.sunoapi.org/suno-api/upload-and-extend-audio | S53 https://blakecrosley.com/guides/suno | S54 https://roo.beehiiv.com/p/suno-artist-style-prompts
