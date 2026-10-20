"""Synthesize a light, cheerful background loop: music.py <dur> <out.wav> [--bpm 100] [--seed 3]

Kalimba-style arpeggios over a soft pad, bass, kick and shaker on a I-V-vi-IV progression in C.
Royalty free by construction; compose.py ducks it under the voice.
"""
import argparse, wave
import numpy as np

SR = 48000
CHORDS = [[48, 55, 60, 64, 67, 72], [43, 50, 59, 62, 67, 71], [45, 52, 57, 60, 64, 69], [41, 48, 57, 60, 65, 69]]   # C G Am F
ARP = [2, 3, 4, 5, 4, 3, 4, 2]     # chord tones per eighth note


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def kalimba(f, d=0.9):
    t = np.arange(int(d * SR)) / SR
    e = np.minimum(1, t / 0.003) * np.exp(-t / 0.35)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 4.0 * f * t) * np.exp(-t / 0.05)) * e


def pad(notes, d):
    t = np.arange(int(d * SR)) / SR
    x = sum(np.sin(2 * np.pi * hz(m) * t + 0.4 * np.sin(2 * np.pi * 0.3 * t)) + 0.3 * np.sin(4 * np.pi * hz(m) * t) for m in notes)
    a = min(0.4, d / 3)
    return x * np.minimum(1, np.minimum(t / a, (d - t) / a)) / len(notes)


def bass(f, d=0.7):
    t = np.arange(int(d * SR)) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.01) * np.exp(-t / 0.35)


def kick():
    t = np.arange(int(0.3 * SR)) / SR
    f = 50 + 70 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)


def shaker(rng):
    n = int(0.08 * SR)
    x = rng.standard_normal(n)
    return (x - lp(x, 8)) * np.exp(-np.arange(n) / SR / 0.025)


def render(dur, bpm=100, seed=3):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = 4 * beat
    n = int((dur + 2) * SR)
    L = np.zeros(n); R = np.zeros(n)

    def add(sig, t, g, pan=0.0):
        i = int(t * SR); j = min(n, i + len(sig))
        if i < n:
            L[i:j] += sig[:j - i] * g * (1 - pan); R[i:j] += sig[:j - i] * g * (1 + pan)

    k, b = kick(), 0
    while b * bar < dur + 1:
        ch = CHORDS[b % len(CHORDS)]; t0 = b * bar
        p = pad(ch[1:4], bar + 0.3)
        add(p, t0, 0.10, -0.2); add(p, t0, 0.10, 0.2)
        for s in (0, 2.5):       # bass on 1 and the "and" of 3
            add(bass(hz(ch[0] - 12)), t0 + s * beat, 0.32)
        if b >= 1:               # first bar: arps only, then the groove comes in
            for s in (0, 2):
                add(k, t0 + s * beat, 0.45)
            for e in range(8):
                add(shaker(rng), t0 + (e + 0.5) * beat / 2, 0.05 + 0.03 * (e % 2), 0.3)
        for e, idx in enumerate(ARP):
            m = ch[idx] + (12 if b % 8 >= 4 and e in (3, 7) else 0)
            add(kalimba(hz(m)), t0 + e * beat / 2 + rng.uniform(0, 0.006), 0.16 if e % 2 else 0.2, 0.35 if e % 2 else -0.35)
        b += 1
    st = np.stack([L, R], 1)[:int(dur * SR)]
    t = np.arange(len(st)) / SR
    st *= np.minimum(1, np.minimum(t / 1.0, (dur - t) / 2.0))[:, None]
    return st / (np.abs(st).max() + 1e-9) * 0.9


def write(path, st):
    pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dur", type=float); ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=100); ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    write(a.out, render(a.dur, a.bpm, a.seed))
