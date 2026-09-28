"""Tests for toolshop.flip.arrange — W3 arrangement layer (F3/F5/A26/A29).

Covers: per-arm span math + LCM supercycle, the true 2-bar drum foundation
(F5 — behavior, not docstring), section arc + mute-drops + hook-space
reservation, 808 root/slide integration, and the per-render verification
(grid adherence, clip count, mono<120 Hz).
"""

import numpy as np
import pytest

from toolshop.flip import arrange, bass808, drums


SR = 22050


def _kit(sr=SR):
    """Minimal synthetic kit (piece -> buffer)."""
    def tone(f, dur, decay):
        n = int(dur * sr)
        t = np.arange(n) / sr
        return (np.sin(2 * np.pi * f * t) * np.exp(-t / decay)).astype(np.float32)
    rng = np.random.default_rng(7)
    hat = rng.standard_normal(int(0.05 * sr)).astype(np.float32) * np.exp(
        -np.arange(int(0.05 * sr)) / (0.01 * sr))
    return {
        "kick": tone(55, 0.3, 0.06) * 0.8,
        "snare": (tone(200, 0.15, 0.04)
                  + np.resize(hat, int(0.15 * sr)) * 0.5) * 0.5,
        "hat": hat * 0.4,
        "openhat": np.tile(hat * 0.3, 4),
        "cymbal": np.tile(hat * 0.35, 8),
        "tom": tone(120, 0.25, 0.08) * 0.6,
    }


def _segment(sr=SR, bars_s=1.0):
    """Bed segment: soft 220/275 Hz pad-ish tone."""
    n = int(bars_s * sr)
    t = np.arange(n) / sr
    return (0.3 * np.sin(2 * np.pi * 220 * t)
            + 0.2 * np.sin(2 * np.pi * 275 * t)).astype(np.float32)


# ---------------------------------------------------------------------------
# Span math + supercycle
# ---------------------------------------------------------------------------

def test_felt_span_written_bars():
    assert arrange.felt_span_written_bars(4, 178.2) == pytest.approx(8.0)
    assert arrange.felt_span_written_bars(4, 133.65) == pytest.approx(6.0)
    assert arrange.felt_span_written_bars(2, 133.65) == pytest.approx(3.0)


def test_supercycle_lcm():
    # arm A: 8-written-bar bed span vs 4-bar drum group
    assert arrange.supercycle_bars(8) == 8
    # arm B: 6-written-bar bed span (or 3-written-bar motif) vs 4-bar group
    assert arrange.supercycle_bars(6) == 12
    assert arrange.supercycle_bars(3) == 12


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arm,sc,total", [("felt_89", 8, 48),
                                          ("triplet_133", 12, 72)])
def test_build_plan_shapes(arm, sc, total):
    plan = arrange.build_plan(arm)
    assert plan.supercycle_bars == sc
    assert plan.total_bars == total
    # sections tile the grid contiguously, all multiples of the supercycle
    cursor = 0
    for sec in plan.sections:
        assert sec.start_bar == cursor
        assert sec.bars % sc == 0
        cursor += sec.bars
    kinds = {s.kind for s in plan.sections}
    assert {"intro", "verse", "hook"} <= kinds
    assert plan.hook_sections, "hook space for backing_vocals must exist"


def test_triplet_arm_motif_alternation():
    plan = arrange.build_plan("triplet_133")
    verse = next(s for s in plan.sections if s.kind == "verse")
    hook = next(s for s in plan.sections if s.kind == "hook")
    assert verse.motif == "motif_dm_1" and verse.root == "D"
    assert hook.motif == "motif_csm_1" and hook.root == "C#"


def test_hook_reserves_space_and_drops():
    for arm in arrange.ARM_BPM:
        plan = arrange.build_plan(arm)
        hook = plan.hook_sections[0]
        assert hook.bed_gain < 1.0, "hook thins the bed for the vocal"
        assert hook.mute_bars, "hook should carry a mute-drop"


# ---------------------------------------------------------------------------
# Drum planning — true 2-bar foundation (F5), sparse intro, mute-drops
# ---------------------------------------------------------------------------

def test_two_bar_kick_cycle():
    pat = drums.drill_pattern(bars=4, ghost_snare=False, hat_mode="mix")
    kicks = [e[0] for e in pat if e[1] == "kick"]
    bar0 = [b for b in kicks if b < 4]
    bar1 = [b - 4 for b in kicks if 4 <= b < 8]
    bar2 = [b - 8 for b in kicks if 8 <= b < 12]
    bar3 = [b - 12 for b in kicks if b >= 12]
    assert bar0 != bar1, "F5: kick row must differ between cycle bars"
    assert bar0 == bar2 and bar1 == bar3, "F5: 2-bar cycle must repeat"


def test_plan_drum_events_sparse_and_mute():
    plan = arrange.build_plan("felt_89")
    ev = arrange.plan_drum_events(plan)
    intro = plan.sections[0]
    intro_ev = [e for e in ev
                if intro.start_bar <= e.bar < intro.start_bar + intro.bars]
    assert intro_ev
    assert {e.piece for e in intro_ev} <= arrange.SPARSE_PIECES | {"cymbal"}
    # mute-drop bars in the hook: no kick/snare there
    hook = plan.hook_sections[0]
    for mb in hook.mute_bars:
        dropped = [e for e in ev if e.bar == mb
                   and e.piece in arrange.MUTE_DROP_PIECES]
        assert not dropped, f"mute-drop bar {mb} still has low-end hits"


def test_drum_events_on_grid():
    plan = arrange.build_plan("triplet_133")
    ev = arrange.plan_drum_events(plan)
    g = arrange.grid_adherence(ev, plan.bpm, sr=SR)
    assert g["pass"], g


def test_crash_accent_on_section_start():
    plan = arrange.build_plan("felt_89")
    ev = arrange.plan_drum_events(plan)
    verse = next(s for s in plan.sections if s.kind == "verse")
    assert any(e.piece == "cymbal" and e.bar == verse.start_bar
               for e in ev)


# ---------------------------------------------------------------------------
# 808 line (megaplan W2: root = landed key, mono-legato, m3/P4, 2-3/4 bars)
# ---------------------------------------------------------------------------

def test_plan_bass_roots_and_slides_on_kicks():
    plan = arrange.build_plan("triplet_133")
    dev = arrange.plan_drum_events(plan)
    kicks = sorted(e.time_s for e in dev if e.piece == "kick")
    notes, slides = arrange.plan_bass(plan, dev)
    assert notes
    # monophonic: strictly increasing onsets
    onsets = [n.start_s for n in notes]
    assert onsets == sorted(onsets) and len(set(onsets)) == len(onsets)
    # every note onset lands on a kick
    kset = set(round(k, 4) for k in kicks)
    assert all(round(n.start_s, 4) in kset for n in notes)
    # every slide lands on a kick; intervals are m3/P4 only
    for sl in slides:
        assert round(sl["time_s"], 4) in kset
        assert sl["interval_st"] in arrange.bass808.SLIDE_INTERVALS_ST
    # per-4-bar slide counts inside the spec window (dense blocks)
    beat_s = 60.0 / plan.bpm
    verse = next(s for s in plan.sections if s.kind == "verse")
    counts: dict = {}
    for sl in slides:
        blk = int(sl["time_s"] / (16 * beat_s))
        if verse.start_bar * 4 * beat_s <= sl["time_s"] < (
                (verse.start_bar + verse.bars) * 4 * beat_s):
            counts[blk] = counts.get(blk, 0) + 1
    assert counts, "no slides counted in verse"
    assert all(2 <= c <= 3 for c in counts.values()), counts


def test_plan_bass_section_roots():
    plan = arrange.build_plan("triplet_133")
    dev = arrange.plan_drum_events(plan)
    notes, _slides = arrange.plan_bass(plan, dev)
    beat_s = 60.0 / plan.bpm
    hook = next(s for s in plan.sections if s.kind == "hook")
    hook_notes = [n for n in notes
                  if hook.start_bar * 4 * beat_s <= n.start_s
                  < (hook.start_bar + hook.bars) * 4 * beat_s]
    # C# minor section: every note is C#2 (37) or a raised approach of it
    assert {n.note for n in hook_notes} <= {37.0, 40.0, 42.0}
    verse = next(s for s in plan.sections if s.kind == "verse")
    verse_notes = [n for n in notes
                   if verse.start_bar * 4 * beat_s <= n.start_s
                   < (verse.start_bar + verse.bars) * 4 * beat_s]
    assert {n.note for n in verse_notes} <= {38.0, 41.0, 43.0}


def test_mute_bars_silence_the_808():
    plan = arrange.build_plan("felt_89")
    dev = arrange.plan_drum_events(plan)
    notes, _ = arrange.plan_bass(plan, dev)
    beat_s = 60.0 / plan.bpm
    hook = plan.hook_sections[0]
    for mb in hook.mute_bars:
        bar_start = mb * 4 * beat_s
        assert not any(bar_start <= n.start_s < bar_start + 4 * beat_s
                       for n in notes), f"808 still plays in mute bar {mb}"


# ---------------------------------------------------------------------------
# Bed lane + render
# ---------------------------------------------------------------------------

def test_build_bed_lane_tiles_and_filters():
    plan = arrange.build_plan("felt_89")
    seg = _segment()
    lane, places = arrange.build_bed_lane(plan, {"region_63_66": seg}, SR)
    assert lane.size > 0
    assert np.abs(lane).max() > 0.05
    assert places and places[0]["section"] == "intro"
    # filtered intro (bars 0-7) darker than verse (bars 8-15): less HF
    beat_s = 60.0 / plan.bpm
    a = lane[int(2 * beat_s * SR): int(6 * beat_s * SR)]
    b = lane[int(10 * beat_s * SR): int(14 * beat_s * SR)]
    hf_a = np.abs(np.diff(a)).mean()
    hf_b = np.abs(np.diff(b)).mean()
    assert hf_a < hf_b


def test_render_arm_end_to_end():
    plan = arrange.build_plan("felt_89")
    seg = _segment(bars_s=4 * 4 * 60.0 / 89.1)  # 4 felt bars
    res = arrange.render_arm(plan, {"region_63_66": seg}, _kit(), sr=SR)
    assert res["audio"].size > int(plan.total_s * SR * 0.9)
    v = res["verification"]
    assert v["clip_pass"], v
    assert v["grid_adherence"]["pass"], v
    assert v["mono_below_120hz"]["pass"], v
    ev = res["events"]
    assert ev["hook_sections"], "event JSON must reserve hook space"
    assert ev["hook_reserved_for"].startswith("backing_vocals")
    assert ev["bass808_notes"] and ev["bass808_slides"]
    assert ev["supercycle_bars"] == 8


def test_render_arm_rejects_glide_outside_window():
    plan = arrange.build_plan("felt_89")
    with pytest.raises(ValueError):
        arrange.render_arm(plan, {"region_63_66": _segment()}, _kit(),
                           sr=SR, glide_ms=240.0)  # old default: out of spec


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def test_clip_count():
    clean = np.sin(2 * np.pi * 100 * np.arange(SR) / SR) * 0.5
    assert arrange.clip_count(clean) == 0
    clipped = np.clip(clean * 5, -1, 1)
    clipped[:100] = 1.0
    assert arrange.clip_count(clipped) >= 100


def test_mono_below_120hz_stereo():
    sr = SR
    t = np.arange(sr) / sr
    sub = np.sin(2 * np.pi * 55 * t)
    stereo_mono = np.stack([sub, sub], axis=1)
    assert arrange.mono_below_120hz(stereo_mono, sr)["pass"]
    rng = np.random.default_rng(0)
    stereo_wide = np.stack([sub, rng.standard_normal(sr) * 0.5 + sub * 0.2],
                           axis=1)
    assert not arrange.mono_below_120hz(stereo_wide, sr)["pass"]


def test_motif_midi_roundtrip(tmp_path):
    from toolshop.flip import bed_lanes
    p = arrange.write_motif_midi(tmp_path / "motif_dm_1.mid", "motif_dm_1")
    notes = bed_lanes.pretty_midi_to_notes(bed_lanes.load_midi(p))
    assert notes and notes[0].note == 62  # D4 motif head
    meta = arrange.motif_meta("motif_csm_1")
    assert meta["root"] == "C#" and meta["voice"] == "epiano"
