"""S4 step-0 guard: confirm instrumental.wav 54-67 s is F# minor, not D minor.

chroma_cqt on the picked window, duration-weighted mean chroma, correlated
against Krumhansl major/minor templates for all 24 keys. Prints the top-5.
"""
import sys

import librosa
import numpy as np

WAV = r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\instrumental.wav"
T0, T1 = 54.0, 67.0

# Krumhansl-Schmuckler key profiles
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39,
                   3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98,
                   2.69, 3.34, 3.17])
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    y, sr = librosa.load(WAV, sr=22050, mono=True, offset=T0,
                         duration=T1 - T0)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    prof = chroma.mean(axis=1)
    prof = prof / prof.sum()

    results = []
    for k in range(12):
        for mode, templ in (("major", KS_MAJ), ("minor", KS_MIN)):
            t = np.roll(templ, k)
            r = float(np.corrcoef(prof, t)[0, 1])
            results.append((r, f"{NAMES[k]} {mode}"))
    results.sort(reverse=True)
    print(f"window {T0}-{T1}s mean chroma: "
          + " ".join(f"{NAMES[i]}={prof[i]:.3f}" for i in range(12)))
    print("top-5 Krumhansl correlations:")
    for r, name in results[:5]:
        print(f"  {name:10s} r={r:+.3f}")
    dmin = next(r for r, n in results if n == "D minor")
    fsmin = next(r for r, n in results if n == "F# minor")
    amaj = next(r for r, n in results if n == "A major")
    top = results[0]
    print(f"F# minor r={fsmin:+.3f} | A major r={amaj:+.3f} | "
          f"D minor r={dmin:+.3f} | top={top[1]} r={top[0]:+.3f}")
    # Plan guard: F#m (or relative A major) must beat D minor.
    ok = max(fsmin, amaj) > dmin
    print("VERDICT:", "OK - F#m/Amaj beats Dm" if ok else
          "STOP - D minor wins; plan premise wrong")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
