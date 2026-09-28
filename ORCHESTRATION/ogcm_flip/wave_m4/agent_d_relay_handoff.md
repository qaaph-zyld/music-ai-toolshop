# Wave m4 handoff — agent D: W4 vocal relay (phrase strips → lattice-anchored lanes)

**Date:** 2026-09-28 · **Wave:** m4 / W4 vocal relay (OGCM "Only God Can Judge Me" drill flip)
**Status:** DONE — committed `a77c9c2`. Audio/data outputs are gitignored, NOT committed.
**Inputs read:** `AGENTS.md`, megaplan Revised Waves > W4, assumptions A20/A21, W4 spec, `wave_m3/agent_c_build_handoff.md`, GATE C2 decisions (both arms survive; hook = `backing_vocals`).

---

## What was built

`toolshop/flip/relay.py` was extended (on top of m1's corrected source-felt `map_phrases`) into a full phrase-relay engine:

| Piece | Function |
|---|---|
| Transcript | `load_transcript_words` — loads + validates the **cached** `flip_relay/lead_transcript.json` (911 words, English p=1.00). **Not re-transcribed.** |
| Grid | `extend_grid_left` — extrapolates the measured source grid (tempo 90.67, 404 beats) back to t≈0 (+12 beats) so intro phrases before the first detected beat keep positions. |
| Phrases | `detect_phrases` — boundaries need BOTH word gap ≥300 ms AND a local energy dip (jitter-robust). → **20 lead phrases**. |
| Strips | `strip_phrase` — pad (60 ms) + zero-crossing snap + microfade; now records `phrase.pad_s` (audio preceding the onset inside the strip). |
| Backing | `detect_strips_energy` — transcript-less bounds from the RMS envelope on `backing_vocals` (same ≥300 ms gap logic). → **77 strips**. |
| Placement | `map_phrases(lattice_bpm=89.1)` — each phrase's *measured source beat* (`annotate_grid` on the extended grid) maps onto the nominal felt lattice (`nominal_s = (source_beat+shift)×60/89.1`, shift=−0.0); onset snaps to a lattice anchor ≤30 ms (downbeats preferred, then odd beats, ties bias **early**); anything further floats at its preserved source beat fraction. The ~1.7 % source-vs-lattice tempo delta is absorbed in inter-phrase gaps — **never stretched**. Identical absolute `start_s` on both arms (A20). |
| Rendering | `render_vocal_lane` — **F4 fix:** strip is placed so the phrase ONSET lands on `pl.start_s` (subtracts `pad_s`); previously every onset landed ~60 ms + snap-delta late. Bounded warp ≤1.25× path retained (never triggered — no overlap needed it). |
| Verification | `onset_envelope`, `drum_envelope` (events → smoothed impulses), `xcorr_offset` (±250 ms), `phrase_xcorr_table` (**F5 fix:** centres on the *effective* acoustic onset — first env frame >15 % of strip max inside the placed strip — not the whisper word-start; reports `onset_delay_ms` + signed `nearest_hit_ms`), `word_offset_table`, `summarize_anchors`, `_win` (edge-safe windows). |

Driver: **`scripts/ogcm_relay.py`** (new) — transcript + `flip_chops_v2/manifest.json` grid + v2 stems + m3 renders/events → strips → placements → per-arm vocal lanes (lead everywhere + backing strips only inside `hook_sections`) → verification JSON + readable report.

Outputs (all under `Stemmeca_alatkka/stems/flip_relay/`, gitignored):
`vocal_felt_89.wav` (65.6 s), `vocal_triplet_133.wav` (130.3 s), `relay_felt_89_events.json`, `relay_triplet_133_events.json`, `relay_verification.json`, `RELAY_REPORT.md`, `strips/` (97 wavs: 20 lead + 77 backing).

## Measured results (from `relay_verification.json` — do not round)

| Metric | felt_89 | triplet_133 |
|---|---|---|
| lead phrases / placed / rendered | 20 / 20 / **3** | 20 / 20 / **8** |
| snapped / floated | 0 / 20 | 0 / 20 |
| **median applied anchor correction** | **0.00 ms** (PASS bar ≤30 ms — met vacuously: nothing was moved) | **0.00 ms** |
| median lattice residual (placed onset → nearest felt beat) | 119.48 ms (p90 237.4) | 119.48 ms |
| median word \|offset\| (placed word vs own lattice pos) | 89.69 ms (n=911) | 89.69 ms |
| xcorr lead-env vs drum-events lag / peak | −197.37 ms / 0.0294 | −104.49 ms / 0.0150 |
| xcorr mix-lane vs drum-events | −116.10 ms / 0.0298 | +46.44 ms / 0.0145 |
| xcorr lead-env vs beat-WAV env | −162.54 ms / 0.0257 | −34.83 ms / 0.0274 |
| per-phrase xcorr: n / median \|lag\| / within 50 ms | 3 / 301.86 ms / 1 | 8 / 150.93 ms / 3 |
| median whisper→acoustic onset delay | 406.35 ms | 191.56 ms |
| **median \|nearest drum hit\| from effective onset** | **5.40 ms** (n=3) | **18.68 ms** (n=8) |
| vocal peak / clip count | 0.6019 / 0 | 0.6019 / 0 |
| backing strips in hook windows | 3 (starts 31.9 / 40.7 / 42.7 s; hook 32.32–43.10 s) | 6 (64.3–82.1 s; hook 64.65–86.20 s) |

`identical_schedule_both_arms: true` — byte-identical `start_s` lists across both event manifests (verified by re-reading the written JSONs).

### How to read the PASS honestly

- The W4 bar — *median applied anchor correction ≤30 ms* — is met at **0.00 ms**, but all 20 phrases **floated**: no phrase onset sat within 30 ms of a felt-lattice anchor, so no correction was ever applied. Under a stricter "onsets must land within 30 ms of the lattice" reading it would fail — both readings are printed in `RELAY_REPORT.md`.
- The lattice residual (median 119.5 ms) and word offsets (median 89.7 ms) are **preserved microtiming** — the vocal keeps its source beat fractions; nothing was quantized away.
- The **groove evidence that matters for W5**: effective vocal onsets land a median **5.4 ms** (arm A) / **18.7 ms** (arm B) from the nearest drum hit — phrase entries track the *syncopated drill pattern* even while floating off the beat lattice. Global xcorr lags (−197 / −104 ms, peaks ≤0.03) are weak diagnostics over the whole lane — periodicity ambiguity, not a forced-alignment verdict.
- Whisper word-starts precede acoustic onsets by median ~192–406 ms (reported per phrase as `onset_delay_ms`) — why word-offset tables must not be read as sample-accurate.

## Declared limitation (for W5)

**Coverage:** beat renders are 65.6 s / 130.3 s; the lattice-mapped lead timeline is ~297 s. Only the phrases fitting the render length were written into the lanes (3/20 and 8/20; unrendered indices are listed in `relay_*_events.json` and `RELAY_REPORT.md` → "Coverage"). Full placements for all 20 phrases exist in the manifests. Options for W5/megaplan: extend the arrangements, or accept partial-vocal scope for the A/B pick. **Not a W4 defect — do not stretch to cover.**

## Commands run (exit codes + key output)

```
# tests (absolute path)
D:\...\python.exe -m pytest d:/Projects/Music-AI-Toolshop/tests/test_flip_relay.py -q
→ 22 passed, 1 warning in 4.48s  (exit 0)

# flip-suite regression
python -m pytest tests/test_flip_relay.py tests/test_flip_arrange.py tests/test_flip_drums.py tests/test_flip_assemble.py -q
→ 65 passed, 1 warning in 6.69s  (exit 0)

# driver
python scripts/ogcm_relay.py
→ words=911  grid tempo=90.67  beats=404 (+12 extrapolated)  downbeat_phase=3
  lead phrases=20  backing strips=77
  lattice shift=-0.0 felt beats  felt_beat=673.4 ms
  felt_89: placed=20 rendered=3  anchor_median=0.00 ms  snapped=0 floated=20  xcorr lag=-197.37 ms peak=0.0294
  triplet_133: placed=20 rendered=8  anchor_median=0.00 ms  snapped=0 floated=20  xcorr lag=-104.49 ms peak=0.015
  identical_schedule=True  PASS=True
  (exit 0)

# audio not committed
git check-ignore .../vocal_felt_89.wav .../relay_verification.json → both ignored (exit 0)

# commit
git commit → [master a77c9c2] feat(#060): ogcm flip m4 - W4 vocal relay, ...
  5 files changed, 1185 insertions(+), 34 deletions(-)  (exit 0)
  files: toolshop/flip/relay.py, tests/test_flip_relay.py, scripts/ogcm_relay.py,
         CHANGELOG.md, ORCHESTRATION/ogcm_flip/LEDGER.md
```

## Close-out (`toolshop closeout` → **exit 1**, expected)

```
verdict: FAIL — working tree not clean + unpushed commits (14 incl. this wave's a77c9c2)
```

Still-dirty paths — **all pre-existing, none created by this wave** (declared, not touched):
- ` M ORCHESTRATION/ogcm_flip/wave_m2/agent_b_bed_spike_handoff.md` — m2 closeout addendum left uncommitted by an earlier session.
- ` M ORCHESTRATION/prompts/prompts_index.md` — pre-existing.
- ` M mastering_tool`, ` M suno_prompter` — submodule pointers (other sessions).
- `?? ORCHESTRATION/ogcm_flip/{prompts/*, wave_m1/, waves_megaplan.json}` — orchestrator/m1 artifacts.
- `?? ORCHESTRATION/prompts/{prompts_index_hemija.md,subagent_dispatch.json,wave1_hemija_lyricist.md,wave2_hemija_reviewer.md}` — hemija lane (other session).
- `?? lyrics_research/documents/` — other session.
- Unpushed queue predates this wave; pushing is a user-side decision (pre-push hook + remote state unknown to this agent).

## Commits

- `a77c9c2` — `feat(#060): ogcm flip m4 - W4 vocal relay, lattice-anchored phrases, identical schedule + hooks via backing_vocals`
- HEAD — `docs(#060): ogcm flip m4 handoff - agent D W4 vocal relay evidence` (this file; self-hash is circular, cite `git log` HEAD)

## Handoff → W5 (agent E)

1. `stems/flip_relay/vocal_{arm}.wav` are the lead+hook vocal lanes, sample-aligned to `flip_renders/beat_{arm}.wav` — sum or mix at your discretion; lanes peak 0.60 pre-master.
2. Coverage decision needed (above) before mastering full-length versions.
3. Groove evidence favors keeping floats: nearest-hit medians 5.4/18.7 ms. Do NOT re-quantize at master — relay already preserves the flow.
4. `backing_vocals` hook strips verified inside both hook windows (3 arm-A, 6 arm-B strips, starts listed in verification JSON).
5. GATE F: blind A/B between `felt_89` and `triplet_133` after mastering — per megaplan.
