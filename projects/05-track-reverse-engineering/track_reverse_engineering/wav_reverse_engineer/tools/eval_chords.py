import argparse
import json
import numpy as np


def load_estimate(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    est = data.get('chords', [])
    intervals = []
    labels = []
    for ch in est:
        start = float(ch.get('start_time', 0.0))
        dur = float(ch.get('duration', 0.0))
        end = start + dur
        root = ch.get('root', 'N')
        qual = ch.get('quality', 'maj')
        labels.append(f"{root}:{'min' if qual=='min' else 'maj'}")
        intervals.append([start, end])
    if not intervals:
        return np.zeros((0, 2)), []
    return np.array(intervals), labels


def load_reference(csv_path):
    lines = open(csv_path, 'r').read().splitlines()
    intervals = []
    labels = []
    for line in lines:
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3:
            continue
        start = float(parts[0])
        end = float(parts[1])
        label = parts[2]
        intervals.append([start, end])
        labels.append(label)
    if not intervals:
        return np.zeros((0, 2)), []
    return np.array(intervals), labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--estimate', required=True)
    parser.add_argument('--reference', required=True)
    args = parser.parse_args()

    ref_i, ref_l = load_reference(args.reference)
    est_i, est_l = load_estimate(args.estimate)

    try:
        import mir_eval
    except Exception:
        print(json.dumps({'error': 'mir_eval not installed'}))
        return 1

    scores = mir_eval.chord.evaluate(ref_i, ref_l, est_i, est_l)
    print(json.dumps(scores, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
