"""Find removable pauses and write work/keep.json (source-second segments to keep).

Only true silence is cut: frames whose 120-7800 Hz energy is within `silence_db_above_floor` of the
noise floor. `tail_s` of silence is kept after every word so soft endings (-k, -s, -zik) survive,
and `head_s` before the next onset.
usage: cuts.py [src] [out.json]
"""
import json, sys
import numpy as np
from media import SRC, WORK, config, load_audio16

SR, HOP, WIN = 16000, 160, 512


def envelope(a):
    fr = np.lib.stride_tricks.sliding_window_view(np.pad(a, (WIN // 2, WIN // 2)), WIN)[::HOP] * np.hanning(WIN)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(WIN, 1 / SR)
    e = 10 * np.log10(S[:, (f > 120) & (f < 7800)].sum(1) + 1e-9)
    return np.convolve(e, np.ones(3) / 3, "same")


def silent_runs(e, above_floor_db):
    floor = np.percentile(e, 5)
    sil = (e - floor) < above_floor_db
    runs, i, n = [], 0, len(sil)
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            runs.append((i * 0.01, j * 0.01)); i = j
        else:
            i += 1
    return runs


def keep_segments(runs, end, tail, head, min_cut, no_cuts_after):
    cuts = []
    for a, b in runs:
        if a < 0.05:  # leading silence
            cuts.append((0.0, round(max(0, b - head), 2))); continue
        if b >= no_cuts_after:
            continue
        c = (round(a + tail, 2), round(b - head, 2))
        if c[1] - c[0] >= min_cut:
            cuts.append(c)
    k, t = [], 0
    for a, b in cuts:
        k.append((t, a)); t = b
    k.append((t, end))
    return [(round(a, 2), round(b, 2)) for a, b in k if b - a > 0.01]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out = sys.argv[2] if len(sys.argv) > 2 else f"{WORK}/keep.json"
    c = config()["cuts"]
    a = load_audio16(src)
    end = c.get("end_s") or round(len(a) / SR, 2)
    keep = keep_segments(silent_runs(envelope(a), c["silence_db_above_floor"]), end, c["tail_s"], c["head_s"],
                         c["min_cut_s"], c.get("no_cuts_after_s") or end - 0.3)
    json.dump(keep, open(out, "w"))
    print(len(keep), "segments,", len(keep) - 1, "cuts,", round(sum(b - a for a, b in keep), 2), "s kept")


if __name__ == "__main__":
    main()
