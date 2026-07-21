# Plan: T7-1 — Section-aware Sample Forge (`toolshop remix` upgrade)

**Milestone:** T7 Sample Forge v1 (residual) · Horizon H3
**Author (orchestrator):** strategy session 2026-07-21
**Depends on:** #016 (`toolshop remix` shipped)
**Blocks / feeds:** T9-E5 universal pack (shares `<key>_<bpm>_<section>_<n>` naming)
**Spec of record:** `docs/superpowers/specs/2026-07-15-longterm-roadmap-v2.md` §T7 (lines 97–100)
**OSS map:** `docs/superpowers/specs/2026-07-15-oss-integration-map.md` §T7 (pedalboard ADOPTED; slicing/naming = BUILD)

---

## 1. Why this plan exists (audit finding)

Spot-check of #016 against the T7 spec found:

- **Integration is solid.** `toolshop remix` is fully wired (CLI subparser + dispatch, `__init__` export, reuse of `batch` / `bpm_adapter` / `stems` manifests, `[remix]` extra, doctor check, 18 tests). No rework needed there.
- **The defining T7 feature is absent.** The spec is *"section loops (8-bar chorus loop, intro riser)… naming `<key>_<bpm>_<section>_<n>.flac`."* The delivered tool slices by **uniform beat count or raw onsets** with **no concept of song sections**, and names files `<key>_<bpm>bps_<idx>_<start>s` — **no `<section>` token**.
- **Root cause is upstream, not laziness.** `reverse_engineering_adapter.analyze_track` (the "dossier") returns BPM/key/chords/beats but **no section boundaries** (see `reverse_engineering_adapter.py:111`). Automatic structure detection (novelty/pychorus) is an unbuilt **H2** item. So the forge could not have auto-labeled sections.
- **But the handoff over-claimed** ("No functional deviations"), hiding both the missing core and the naming divergence — the recurring close-out-discipline pattern.

**This plan decouples the two concerns** (correct architecture): the **forge consumes externally-provided sections and does the cutting/labeling/naming/manifest** (deliverable now); **automatic detection stays an H2 job**. It also delivers immediate manual-section value and makes the tool drop-in ready the moment H2 emits sections.

---

## 2. Scope

### IN scope
1. A section-consuming slicer: `_load_sections()` + `_slice_by_sections()` with optional beat-snapping and sub-slicing.
2. Spec-aligned, section-first naming: `<key>_<bpm>_<section>_<n>.<ext>` (drop `bps` and the timestamp suffix).
3. `section` field in the pack manifest.
4. CLI surface: `--sections`, `--sub-slice-beats`, `--no-beat-snap`.
5. Tests for all of the above + honest CI (remix tests must actually run).
6. Honest docs + residual close-out (README/CHANGELOG/STATUS + handoff that names what is deferred).

### OUT of scope — DO NOT DO (hard fence)
- ❌ **Do NOT build automatic structure/section detection** (librosa novelty, pychorus, allin1, madmom downbeats, etc.). That is **H2 / T2 Dossier v2**, a separate milestone with its own eval. Building it here is exactly the "out-of-band, jump-the-queue" anti-pattern. This plan only *reads* sections someone/something else produced.
- ❌ No new dependencies (`pedalboard`/`librosa`/`numpy`/`scipy`/`soundfile` already in `[remix]`).
- ❌ Do not change `--mode remix` behavior.
- ❌ Do not touch the pre-existing `tests/test_cleaning_pipeline.py` numpy failures.

---

## 3. Design (implement exactly this)

All changes in `toolshop/remix_adapter.py`, `toolshop/remix_cli.py`, `toolshop/cli.py`, and the two remix test files. Env: repo `.venv` (py3.11); `pip install -e ".[remix]"` already satisfied.

### 3.1 Section input schema
Accept a JSON file. Sections may be top-level `"sections"` **or** nested under `"structure": {"sections": [...]}` (forward-compat with a future dossier field):

```json
{
  "sections": [
    {"label": "intro",  "start": 0.0,  "end": 15.2},
    {"label": "verse",  "start": 15.2, "end": 45.0},
    {"label": "chorus", "start": 45.0, "end": 65.0}
  ]
}
```

### 3.2 `_load_sections(path: Path) -> List[Dict[str, Any]]`
- Read JSON; find `sections` at top level, else under `structure.sections`; else raise `ValueError`.
- Each entry needs `label:str`, `start:float`, `end:float`. Coerce numeric; **skip with a `logging.warning`** any entry where `end <= start` or fields are missing/unparseable.
- Sort by `start`. Return the cleaned list. Empty result after cleaning → raise `ValueError("No valid sections in <path>")`.

### 3.3 `_slice_by_sections(audio, sr, sections, beat_samples=None, snap_to_beats=True, sub_slice_beats=None) -> List[Tuple[np.ndarray, int, int, str, int]]`
Returns `(segment, start_sample, end_sample, label, n_within_section)`.
- For each section: `start_s = int(section["start"]*sr)`, `end_s = int(section["end"]*sr)`, clamped to `[0, len(audio)]`.
- If `snap_to_beats and beat_samples is not None and len(beat_samples)`: snap `start_s`/`end_s` to the nearest value in `beat_samples`.
- If `sub_slice_beats and beat_samples is not None`: within `[start_s, end_s)`, cut at every `sub_slice_beats`-th beat that falls inside the section → emit multiple segments with `n = 1,2,3,…`. Otherwise emit one segment with `n = 1`.
- Skip degenerate slices (`end_s <= start_s`).
- `label` passed through verbatim (sanitized at naming time).

### 3.4 Naming — replace `_sample_name`
New signature (breaking): `_sample_name(key: str, bpm: float, section: str, n: int, output_format: str) -> str`
```python
ext = ".wav" if output_format.lower() == "wav" else ".flac"
safe_key = key.replace("#", "sh").replace("b", "f")
safe_section = re.sub(r"[^a-z0-9]+", "", section.lower()) or "loop"
return f"{safe_key}_{int(round(bpm))}_{safe_section}_{n:02d}{ext}"
```
Examples: `A_120_chorus_01.flac`, `Fsh_140_oneshot_03.wav`. Matches spec `<key>_<bpm>_<section>_<n>`.

### 3.5 Wire into `create_remix` (sample mode only)
- Add params: `sections: Optional[List[Dict[str, Any]]] = None`, `sub_slice_beats: Optional[int] = None`, `snap_to_beats: bool = True`.
- In `mode == "sample"`:
  - If `sections` is not None: always compute `beat_samples` via `_detect_beats(audio, sr)` (needed for snapping), then `raw = _slice_by_sections(...)`. Each item carries a real `label`.
  - Else keep current behavior, but assign a label: `"oneshot"` for the onset path (`segment_beats <= 1`), `"loop"` for the beat-grid path.
  - Per segment: run existing `_stretch_segment(...)` (tempo/key) then `_apply_fx(...)`, unchanged.
  - Filename via new `_sample_name(src_key, src_bpm, label, n, output_format)` where `n` is a per-label running counter (dict of label→count).
  - Add `"section": label` to each manifest sample dict; keep `start_seconds`/`end_seconds`/`beats`.

### 3.6 CLI (`cli.py` remix subparser + `remix_cli.py`)
Add to the `remix` subparser:
- `--sections`, `type=Path, default=None` — "JSON file of `{label,start,end}` section boundaries; enables labeled section loops."
- `--sub-slice-beats`, `type=int, default=None` — "Sub-divide each section into N-beat loops (default: one loop per section)."
- `--no-beat-snap`, `action="store_true"` — "Do not snap section boundaries to detected beats."

In `remix_cli._process_one`:
- If `args.sections`: require `args.mode == "sample"` — else `raise ValueError("--sections requires --mode sample")`. Load via `remix_adapter._load_sections(args.sections)`; pass `sections=…, sub_slice_beats=args.sub_slice_beats, snap_to_beats=not args.no_beat_snap` into `create_remix`.
- Batch mode: a single `--sections` file applies to every input (document this; per-file sections are a future extension — do NOT build now).

---

## 4. Tasks (each ends with its evidence gate)

- [ ] **T1 — `_load_sections` + `_slice_by_sections`** in `remix_adapter.py`.
  Evidence: `test_load_sections_valid`, `_invalid_skips_bad`, `_nested_structure_key`, `test_slice_by_sections_labels_and_bounds`, `_snaps_to_beats`, `_sub_slice` all pass.
- [ ] **T2 — New `_sample_name` + manifest `section` field**; update `create_remix` sample-mode call sites and labels.
  Evidence: `test_sample_name_format` asserts exact `A_120_chorus_01.flac`; `test_create_samples_smoke` updated for new pattern and asserts `samples[0]["section"]`.
- [ ] **T3 — CLI flags + dispatch** (`cli.py`, `remix_cli.py`).
  Evidence: `python -m toolshop.cli remix --help` lists `--sections`, `--sub-slice-beats`, `--no-beat-snap`; `test_cli_sections_run` produces labeled files + manifest with sections.
- [ ] **T4 — Honest CI + test guards.**
  - Add module-level `pytest.importorskip("pedalboard")` to `tests/test_remix_adapter.py` and `tests/test_cli_remix.py` (clean skip where the extra is absent).
  - Update `.github/workflows/ci.yml` install line to include the `remix` extra (e.g. `.[audio,lyrics,remix]`) so these tests **actually run** in CI — mirrors the `[lyrics]` fix in #017.
  Evidence: CI run URL in handoff showing remix tests collected + green (not skipped).
- [ ] **T5 — Docs + honest close-out.**
  - README: "Section-aware sample forge" subsection — JSON schema, example command, naming convention, and an explicit note that **automatic section labeling is pending the H2 structure detector**; today sections come from `--sections` (dossier notes / DAW marker export).
  - CHANGELOG **#018** — new feature **+ BREAKING**: sample filename format changed `<key>_<bpm>bps_<idx>_<t>s` → `<key>_<bpm>_<section>_<n>`.
  - `docs/superpowers/STATUS.md` T7 row → "v1 partial: section-consuming forge + spec-aligned naming shipped; auto-detection deferred to H2 structure detector."
  Evidence: diffs present in the commit.

---

## 5. Close-out gates (ALL must hold to call this done — no exceptions)

1. **Targeted green:** `python -m pytest tests/test_remix_adapter.py tests/test_cli_remix.py -q` → all pass. Paste the tail.
2. **No NEW suite failures:** `python -m pytest tests -q` → failures limited to the known ~10 `test_cleaning_pipeline.py` numpy cases. **State exact pass/fail/skip counts** and confirm the delta vs. #017 is zero new failures.
3. **CLI proof:** paste `toolshop remix --help` showing the three new flags.
4. **Manual smoke (real behavior):** write a 3-section JSON, run
   `python -m toolshop.cli remix <file>.wav --mode sample --sections sections.json --output-dir <out>`
   and confirm files named `*_intro_01.*`, `*_verse_01.*`, `*_chorus_01.*` plus a `manifest.json` whose samples carry `"section"`. Paste the file listing.
5. **CI:** ci.yml updated; provide the **run URL** proving remix tests ran green (per the "CI claims need a run URL" rule).
6. **Committed + pushed:** commit(s) to `origin/master`; **put the commit hashes in the handoff.** CHANGELOG #018 + STATUS + README in the same commit wave.
7. **Honest handoff:** the handoff MUST explicitly state (a) the **breaking filename change**, (b) that **automatic section detection remains deferred to H2**, and (c) any real deviations. **Do NOT write "no functional deviations."**

---

## 6. Risks / notes
- **Breaking filename change** is intentional and low-blast-radius (fresh feature, nothing downstream consumes the old names yet). Still call it out in CHANGELOG + handoff.
- Beat-snap relies on `_detect_beats`; very short/synthetic test signals emit benign librosa `n_fft` warnings — use ≥2 s fixtures.
- Keep `_slice_by_sections` beat-snapping to **nearest beat**; bar/downbeat snapping needs downbeat detection (H2) — do not attempt here.
- If `sub_slice_beats` is set but a section is shorter than one sub-slice, emit the whole section as `n=1` (never emit zero slices for a valid section).
