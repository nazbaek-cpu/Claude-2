"""Original background music, synthesized from scratch (no samples, no third-party recordings: free to use anywhere).

usage: music.py <project>
project.json "music": {"generate": {"bpm": 104, "key": "C", "mood": "bright", "seed": 3}, "gain_db": -6, "duck_db": 4}
A light, bouncy "study pop" loop: plucked keys on a I-V-vi-IV progression, round bass, soft kick/clap/shaker and a sparse
marimba motif. The 1-4 kHz band is kept low so the voice stays clear. Writes build/music.wav (48 kHz stereo) exactly as long
as the video. Use "music": {"file": "input/your_track.mp3"} instead to bring a track you have the rights to.
"""
import json, sys, wave
import numpy as np
from common import Project

SR = 48000
KEYS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "Bb": 10}
PROGRESSIONS = {"bright": [(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")],    # I  V  vi IV
                "calm": [(0, "maj"), (9, "min"), (5, "maj"), (7, "maj")]}      # I  vi IV V


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, attack=0.004, decay=0.5):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def keys_note(f, dur, rng):
    """soft electric-piano pluck: a few harmonics, slightly detuned pair, fast attack"""
    n = int(dur * SR); t = np.arange(n) / SR
    det = 1 + rng.uniform(-0.0015, 0.0015)
    x = sum(a * (np.sin(2 * np.pi * f * k * t) + np.sin(2 * np.pi * f * k * det * t)) for k, a in ((1, 1), (2, .35), (3, .12), (4, .05)))
    return 0.18 * x * env(n, 0.005, 0.45)


def marimba(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return 0.22 * (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / 0.05)) * env(n, 0.002, 0.28)


def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)
    return 0.45 * np.tanh(1.5 * x) * env(n, 0.006, 0.35)


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.035)
    return 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.12)


def clap(rng):
    n = int(0.22 * SR)
    x = rng.standard_normal(n)
    x = np.convolve(x, [1, -0.95], "same")                     # brighten
    e = env(n, 0.001, 0.06) + 0.5 * np.roll(env(n, 0.001, 0.02), int(0.011 * SR))
    return 0.10 * x * e


def shaker(rng, accent):
    n = int(0.07 * SR)
    x = np.diff(rng.standard_normal(n + 1))                    # high-passed noise
    return (0.035 if accent else 0.02) * x * env(n, 0.003, 0.02)


def place(track, x, t, pan=0.0):
    i = int(t * SR)
    if i >= len(track):
        return
    x = x[:len(track) - i]
    track[i:i + len(x), 0] += x * (1 - max(0, pan)); track[i:i + len(x), 1] += x * (1 + min(0, pan))


def voice_space(x):
    """gentle dip around 1-4 kHz and roll-off above 9 kHz so the music sits under the voice"""
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR)[:, None]
    dip = 1 - 0.35 * np.exp(-((np.log2(np.maximum(f, 1) / 2200)) ** 2) / (2 * 0.6 ** 2))
    lp = 1 / np.sqrt(1 + (f / 8000) ** 8)
    return np.fft.irfft(X * dip * lp, n=len(x), axis=0)


def reverb(x, wet=0.12):
    n = int(0.9 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(1)
    ir = rng.standard_normal((n, 2)) * np.exp(-t / 0.25)[:, None]
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], len(x) + n) * np.fft.rfft(ir[:, c], len(x) + n))[:len(x)] for c in (0, 1)], 1)
    return x + wet * y


def compose_music(dur, bpm=104, key="C", mood="bright", seed=3):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = 4 * beat
    root = 60 + KEYS.get(key, 0)
    prog = PROGRESSIONS.get(mood, PROGRESSIONS["bright"])
    tr = np.zeros((int((dur + 2) * SR), 2))
    scale = [0, 2, 4, 7, 9, 12, 14, 16]                         # major pentatonic + octave
    motif = [rng.choice(scale, 4) for _ in range(2)]            # two short motifs, reused (gives it a "tune")
    nbars = int(np.ceil(dur / bar)) + 1
    for b in range(nbars):
        t0 = b * bar
        deg, q = prog[b % 4]
        third = 3 if q == "min" else 4
        chord = [root + deg - 12 * (deg > 5), root + deg + third - 12 * (deg > 5), root + deg + 7 - 12 * (deg > 5)]
        # keys: syncopated plucks (1, 2-and, 3-and), chord spread across the stereo field
        for hit, vel in ((0, 1.0), (1.5, 0.75), (2.5, 0.8)):
            for i, m in enumerate(chord):
                place(tr, vel * keys_note(hz(m), 1.2, rng), t0 + hit * beat, pan=(i - 1) * 0.35)
        if b == 0:
            continue                                            # first bar: keys only, as an intro
        broot = root + deg - 24 - 12 * (deg > 5)
        for hit in (0, 2, 3.5):
            place(tr, bass(hz(broot), beat * 1.2), t0 + hit * beat)
        for hit in ((0, 2) if b % 2 else (0, 2, 2.5)):
            place(tr, kick(), t0 + hit * beat)
        for hit in (1, 3):
            place(tr, clap(rng), t0 + hit * beat, pan=0.1)
        for k in range(8):
            place(tr, shaker(rng, k % 2 == 0), t0 + k * beat / 2, pan=-0.3)
        if b % 4 in (1, 3):                                     # sparse melody: leaves room for the voice
            for k, s in enumerate(motif[(b // 4) % 2]):
                place(tr, marimba(hz(root + 12 + s), 0.6), t0 + (k * 0.75 + 0.5) * beat, pan=0.25)
    # ending: one last chord ringing out over the video's final second
    deg, q = prog[0]
    for i, m in enumerate((root, root + 4, root + 7, root + 12)):
        place(tr, 1.2 * keys_note(hz(m), 2.0, rng), dur - 1.0, pan=(i - 1.5) * 0.25)
    tr = tr[:int(dur * SR)]
    tr = reverb(voice_space(tr))
    fade = np.ones(len(tr)); n = int(0.3 * SR); fade[:n] = np.linspace(0, 1, n)
    n = int(1.2 * SR); fade[-n:] *= np.linspace(1, 0, n) ** 1.5
    tr *= fade[:, None]
    return tr / max(1e-9, np.abs(tr).max()) * 0.89


def write_wav(path, x):
    st = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(st.tobytes()); w.close()


def main():
    prj = Project(sys.argv[1])
    m = prj.cfg.get("music", {})
    if "generate" not in m:
        print("no music.generate in project.json: nothing to do"); return
    dur = json.load(open(prj.p("build", "edl.json")))["dur"] + prj.cfg["vo"].get("tail_s", 1.0)
    g = m["generate"]
    x = compose_music(dur, g.get("bpm", 104), g.get("key", "C"), g.get("mood", "bright"), g.get("seed", 3))
    write_wav(prj.p("build", "music.wav"), x)
    print(f"music: {dur:.1f} s at {g.get('bpm', 104)} bpm in {g.get('key', 'C')} ({g.get('mood', 'bright')}) -> build/music.wav")


if __name__ == "__main__":
    main()
