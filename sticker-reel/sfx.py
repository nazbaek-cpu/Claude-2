"""Synthesize SFX and lay them on a track: sfx.py <cues.json> <dur> <out.wav>  (cues: [[t, kind, gain], ...])"""
import json, sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def env(n, a=0.004, d=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 420 + 580 * np.exp(-t / 0.018)
    return 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.035)


def whoosh(d=0.42):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    lo, hi = lp(x, 40), lp(x, 6)
    mix = np.linspace(0, 1, n) ** 1.5
    y = lo * (1 - mix) + (hi - lo) * mix * 0.6
    return 2.2 * y * np.sin(np.pi * t / d) ** 2


def tick():
    n = int(0.05 * SR); t = np.arange(n) / SR
    return 0.5 * np.sin(2 * np.pi * 2400 * t) * env(n, 0.001, 0.008)


def ding():
    n = int(0.9 * SR); t = np.arange(n) / SR
    return 0.35 * (np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t)
                   + 0.25 * np.sin(2 * np.pi * 2637 * t)) * env(n, 0.003, 0.28)


def boom():
    n = int(0.7 * SR); t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.08)
    return 0.9 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.004, 0.22)


def click():
    n = int(0.06 * SR)
    x = rng.standard_normal(n) * env(n, 0.0005, 0.006)
    t = np.arange(n) / SR
    return 0.6 * x + 0.3 * np.sin(2 * np.pi * 1800 * t) * env(n, 0.0005, 0.01)


def sparkle():
    out = np.zeros(int(0.8 * SR))
    for i, f in enumerate([2093, 2637, 3136, 4186, 3520]):
        n = int(0.4 * SR); t = np.arange(n) / SR; s = int(i * 0.06 * SR)
        out[s:s + n] += 0.18 * np.sin(2 * np.pi * f * t) * env(n, 0.002, 0.12)
    return out


def riser(d=0.6):
    n = int(d * SR); t = np.arange(n) / SR
    x = lp(rng.standard_normal(n), 4) * (t / d) ** 2
    return 0.9 * x + 0.15 * np.sin(2 * np.pi * np.cumsum(300 + 900 * t / d) / SR) * (t / d)


KINDS = dict(pop=pop, whoosh=whoosh, tick=tick, ding=ding, boom=boom, click=click, sparkle=sparkle, riser=riser)

if __name__ == "__main__":
    cues = json.load(open(sys.argv[1])); dur = float(sys.argv[2])
    track = np.zeros(int((dur + 1) * SR))
    for t0, kind, g in cues:
        s = KINDS[kind]() * g
        i = int(max(0, t0) * SR)
        track[i:i + len(s)] += s[:len(track) - i]
    track = track[:int(dur * SR)]
    pk = np.abs(track).max()
    if pk > 0.95:
        track *= 0.95 / pk
    st = (np.repeat(track[:, None], 2, 1) * 32767).astype(np.int16)
    w = wave.open(sys.argv[3], "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(st.tobytes()); w.close()
