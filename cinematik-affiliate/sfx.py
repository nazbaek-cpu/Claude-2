"""Synthesised (royalty-free) SFX track timed to the text animations in project.json.

whoosh: every headline / number entrance   pop: every pill   tick: every count-up step   ding: every CTA

    python sfx.py projects/<name>          -> projects/<name>/build/sfx.wav
"""
import os, sys, wave
import numpy as np
from render import load, count_value

SR = 48000
rng = np.random.default_rng(7)

def db(x): return 10 ** (x / 20)

def onepole(x, fc):  # time-varying one-pole lowpass, fc array in Hz
    y = np.empty_like(x); s = 0.0
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y

def whoosh(length=0.42, peak=0.62):
    n = int(SR * length); t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    fc = 300 + 5200 * np.sin(np.pi * np.clip(t / (peak * 2), 0, 1)) ** 2   # sweep up then down
    low = onepole(onepole(noise, fc), fc)
    band = low - onepole(low, fc * 0.25)                                   # remove rumble
    env = np.where(t < peak, (t / peak) ** 2.2, ((1 - t) / (1 - peak)) ** 1.6)
    sig = band * env; sig /= np.abs(sig).max()
    pan = np.clip(0.2 + 0.6 * t, 0, 1)                                    # slight L -> R movement
    return np.stack([sig * np.cos(pan * np.pi / 2), sig * np.sin(pan * np.pi / 2)], 1) * 1.3

def pop():
    n = int(SR * 0.09); t = np.arange(n) / SR
    f = 320 + 760 * np.exp(-t / 0.012)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
    sig[:60] += rng.standard_normal(60) * 0.25 * np.linspace(1, 0, 60)
    return np.stack([sig, sig], 1)

def tick():
    n = int(SR * 0.03); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.004)
    return np.stack([sig, sig], 1)

def ding():
    n = int(SR * 0.9); t = np.arange(n) / SR
    sig = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
              for f, a, d in ((1318.5, 1.0, 0.35), (1975.5, 0.55, 0.25), (2637, 0.3, 0.15), (659.3, 0.35, 0.4)))
    sig *= np.minimum(t / 0.004, 1)
    sig /= np.abs(sig).max()
    return np.stack([sig, sig], 1)

def events(cfg):
    """[(time, kind)] derived from the segments"""
    ev = []
    for s in cfg["segments"]:
        if s.get("head") or "count" in s: ev.append((s["start"] - 0.22, "whoosh"))   # peaks as the text sharpens
        for _, ts in s.get("pills", []): ev.append((ts, "pop"))
        if s.get("cta"): ev.append((s["start"] + 0.05, "ding"))
        if "count" in s:
            last, last_t = 0, -1.0
            for ms in range(2000):
                t = s["start"] + ms / 1000; v = count_value(s, t)
                if v != last and t - last_t >= 0.07: ev.append((t, "tick")); last, last_t = v, t   # decimals: no machine-gun
    return sorted(ev)

def main():
    prj = sys.argv[1]
    cfg = load(prj)
    track = np.zeros((int(SR * (cfg["duration"] + 0.5)), 2), np.float32)
    sounds = {"whoosh": (whoosh, -19), "pop": (pop, -17), "tick": (tick, -21), "ding": (ding, -18)}
    gain = cfg.get("sfx_gain_db", 0)
    for at, kind in events(cfg):
        make, level = sounds[kind]
        clip = make(); i = int(at * SR)
        if i < 0: clip, i = clip[-i:], 0
        j = min(i + len(clip), len(track))
        track[i:j] += clip[: j - i] * db(level + gain)
    track = np.clip(track, -1, 1)
    os.makedirs(os.path.join(prj, "build"), exist_ok=True)
    out = os.path.join(prj, "build", "sfx.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((track * 32767).astype("<i2").tobytes())
    print(f"sfx: {len(events(cfg))} events -> {out}")

if __name__ == "__main__":
    main()
