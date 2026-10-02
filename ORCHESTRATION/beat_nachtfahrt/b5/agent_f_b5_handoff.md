# Nachtfahrt b5 — Fix Wave Handoff

Implementer: orchestrator in Normal mode (subagent quota exhausted; wave executed
by the top agent directly). Addresses b4 defects D1, D2, D3. Scope respected:
`toolshop/beat/mixdown.py`, `scripts/build_nachtfahrt.py`,
`tests/test_beat_nachtfahrt.py`, `CHANGELOG.md` only.

## D1 — Mud guard (partial fix; residual escalated)

**Spec metric (O6):** master 200–500 Hz energy share, hooks ≤ 1.25 × verses.

What was applied:

- Hook side: `MUD_EQ` in `mixdown.py` — RBJ peaking-EQ dip at 320 Hz, Q=1,
  −3 dB, blended onto `pad`, `stabs`, `arp` while `SECTION_KIND == "hook"`
  (per-sample `_section_mask`, 150 ms smoothed edges; verses untouched).
- Verse side: `AUTO_KIND = {"pad": {"verse": +4 dB}, "arp": {"verse": +3 dB}}`
  — pad chords (220–440 Hz fundamentals) and arps now carry mid content in
  verses, which were previously 808-only in that band.

Measured (main master, mean over sections):

| quantity | before (b4) | after (b5) | limit |
|---|---|---|---|
| hook 200–500 Hz share | 0.1447 | 0.1428 | — |
| verse 200–500 Hz share | 0.0040 | 0.0060 | — |
| share ratio | 36.6 | **23.9** | ≤ 1.25 |
| hook band absolute | — | 38.6 dB | — |
| verse band absolute | — | 26.0 dB | — |

**Residual:** ratio 23.9 vs 1.25. This is denominator-driven: verses are
deliberately 808-sub dominated (their 200–500 Hz band is ~0.5% of total), so a
share-ratio can only reach ~1.25 if verse mids approach hook levels — which
would erase the verse/hook contrast O1 explicitly requires
(`verse in [-6,-2] LU`). Absolute band level gap is 12.6 dB hooks-over-verses,
a normal arrangement profile. Per the wave bound ("stop tuning if the ratio
stays >2 while absolute levels are sane"), tuning stopped here.

**Options for the spec owner (unchanged by b5):**
- (a) re-baseline O6 to an absolute hook-band-level check (b4's preferred fix),
- (b) accept ratio ~24 as the measured signature of the intended arrangement,
- (c) deeper arrangement change (verse mid layer at much higher level) —
  rejected: breaks O1 section contrast.

## D2 — Dry stems linked (fixed)

`_index_html` adds a `Dry stem: <lane>` player row per lane
(`stems/<lane>.wav`); `_artifacts` includes them (freshness now covers 24
artifacts). `check_audition_serve --glob "stems/*.wav"` now PASSES.

## D3 — Audit coverage hardened (fixed)

`audited_call` in `build_nachtfahrt.py` wraps `soundfile.read` and
`soundfile.SoundFile.__init__` during the audited window, recording read-mode
opens of `.wav/.flac/.mp3/.mid/.midi` — libsndfile C-level reads can no longer
bypass the hook. Fresh build reports `files_read=[]`.

## Gates (all re-run on the rebuilt outdir)

- `python -X utf8 -u scripts/build_nachtfahrt.py --stage all` → exit 0;
  `files_read=0`; premix peak −6.0 dBFS.
- `check_beat_release.py --dir <outdir>` → **PASS 21/21** (main −9.01 LUFS /
  −1.006 dBTP; streaming −14.00 / −2.53; verses −4.04/−3.94; hook spread 0.19;
  stem residual −107.4 dB).
- `pytest tests/test_beat_nachtfahrt.py -q` → **48 passed** (+5 new: EQ biquad
  response, section mask, section-scoped dip impulse, index dry links,
  libsndfile-read audit).
- Flip regression (4 files) → **151 passed**.
- `check_audition_serve` → PASS for `*.wav`, `stems/*.wav`, `stems_mixed/*.wav`.
- `git diff 6c51d81..HEAD -- toolshop/flip toolshop/premaster.py` → empty.
- One test caught a real bug pre-commit: the first `_peaking_ba` cut had the
  RBJ `A`/`1/A` placement inverted (boosted +3 dB); fixed and covered by
  `test_peaking_eq_dips_at_f0`.

## Verdict

b5 delivered: D2 + D3 fully fixed; D1 applied the bounded musical fix and
documented that the remaining ratio-vs-limit gap is a spec-metric/
arrangement question, not a mix defect.
