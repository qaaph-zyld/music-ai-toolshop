"""
Evaluation harness utilities (optional) for comparing analysis outputs with
reference annotations when available. All functions gracefully degrade when the
relevant optional packages are not installed.
"""
from __future__ import annotations

from typing import List, Dict, Any


def _has_mir_eval() -> bool:
    try:
        import mir_eval  # noqa: F401
        return True
    except Exception:
        return False


def evaluate_chords(ref: List[Dict[str, Any]], est: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate chord estimation results using mir_eval.chord if available.

    Args:
        ref: list of dicts with keys: start_time, duration, root, quality
        est: same format as ref

    Returns:
        dict of scores, or empty dict if mir_eval is unavailable.
    """
    if not _has_mir_eval():
        return {}
    try:
        import numpy as np
        import mir_eval
        # Convert to intervals and labels "C:maj"/"A:min" etc.
        def to_intervals_labels(items):
            intervals = []
            labels = []
            for it in items:
                s = float(it.get('start_time', 0.0))
                d = float(it.get('duration', 0.0))
                e = s + max(d, 0.0)
                root = str(it.get('root', 'N'))
                qual = str(it.get('quality', 'maj'))
                if root.upper() == 'N':
                    lab = 'N'
                else:
                    lab = f"{root}:{'min' if 'min' in qual else 'maj'}"
                intervals.append([s, e])
                labels.append(lab)
            if not intervals:
                intervals = [[0.0, 0.0]]
                labels = ['N']
            return np.asarray(intervals, dtype=float), labels
        i_ref, l_ref = to_intervals_labels(ref)
        i_est, l_est = to_intervals_labels(est)
        # Validate and evaluate
        mir_eval.util.validate_intervals(i_ref)
        mir_eval.util.validate_intervals(i_est)
        scores = mir_eval.chord.evaluate(i_ref, l_ref, i_est, l_est)
        # Keep a compact subset
        keep = ['root', 'majmin', 'triads', 'tetrads', 'sevenths', 'majmin_inv', 'triads_inv']
        return {k: float(scores[k]) for k in keep if k in scores}
    except Exception:
        return {}


def evaluate_beats(ref_times: List[float], est_times: List[float]) -> Dict[str, Any]:
    """
    Evaluate beat tracking using mir_eval.beat if available.
    Returns empty dict if mir_eval is not installed.
    """
    if not _has_mir_eval():
        return {}
    try:
        import numpy as np
        import mir_eval
        ref = np.asarray(ref_times, dtype=float)
        est = np.asarray(est_times, dtype=float)
        if ref.size == 0 or est.size == 0:
            return {}
        scores = mir_eval.beat.evaluate(ref, est)
        keep = ['f_measure', 'p_score', 'cemgil_accuracy']
        return {k: float(scores[k]) for k in keep if k in scores}
    except Exception:
        return {}
