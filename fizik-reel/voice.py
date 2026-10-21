"""Cut the voice track with the same frame-quantized keep list as the video, then clean it up.
Writes work/voice.wav and the source->output time map work/edl.json.

config.json "voice": {"preset": "studio" | "clear" | "basic" | "original", "denoise_atten_db": 40}
  studio  DeepFilterNet denoise + warm close-mic EQ, de-esser, two gentle compressors, light saturation
  clear   DeepFilterNet denoise + bright presence EQ
  basic   ffmpeg afftdn + compressor (the original chain; no extra tool needed)
  original  the recorded voice as is: no denoise, EQ, compression or loudness change
"""
import json, os, subprocess
from media import HERE, SRC, WORK, config, probe

DEEP_FILTER = os.environ.get("DEEP_FILTER", os.path.join(HERE, "tools", "deep-filter"))

PRESETS = {
    "studio": dict(denoise=True, chain=(
        "highpass=f=70:p=2,"
        "equalizer=f=120:t=q:w=0.9:g=3,"          # warmth / proximity
        "equalizer=f=450:t=q:w=1.0:g=-4.5,"       # remove boxiness
        "equalizer=f=2800:t=q:w=1.0:g=2.5,"       # articulation
        "equalizer=f=5500:t=q:w=1.5:g=-1.5,"      # tame harshness
        "highshelf=f=11000:g=1.5,"
        "deesser=i=0.55:m=0.5:f=0.5,"
        "acompressor=threshold=-24dB:ratio=2.5:attack=4:release=80:knee=6,"
        "asplit[d][w];[w]volume=8dB,asoftclip=type=tanh:oversample=4,volume=-22dB[s];"  # parallel saturation
        "[d][s]amix=inputs=2:normalize=0,"
        "acompressor=threshold=-16dB:ratio=1.8:attack=12:release=180:knee=4,"
        "loudnorm=I=-15:TP=-1.5:LRA=7,aresample=48000,alimiter=limit=0.89:attack=2:release=40")),
    "clear": dict(denoise=True, chain=(
        "highpass=f=80,equalizer=f=220:t=q:w=1.0:g=-2.5,equalizer=f=420:t=q:w=1.2:g=-3.5,"
        "equalizer=f=3300:t=q:w=0.9:g=4,highshelf=f=8000:g=3,deesser=i=0.4,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000")),
    "basic": dict(denoise=False, chain=(
        "highpass=f=70,afftdn=nf=-30,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,"
        "loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000")),
    "original": dict(denoise=False, chain="aresample=48000"),
}


def run(cmd):
    subprocess.run(cmd, check=True)


def process(raw, dst, preset, dur, atten_db=40):
    """raw: mono 48 kHz wav -> dst: stereo wav of exactly `dur` seconds through the preset chain"""
    p = PRESETS[preset]
    src = raw
    if p["denoise"]:
        out_dir = os.path.join(os.path.dirname(dst), "dfn")
        os.makedirs(out_dir, exist_ok=True)
        # -D compensates the model delay so the voice stays in sync with the video
        run([DEEP_FILTER, "-D", "-a", str(atten_db), "-o", out_dir, raw])
        src = os.path.join(out_dir, os.path.basename(raw))
    fc = f"[0:a]apad=whole_dur={dur:.6f},atrim=0:{dur:.6f},{p['chain']},aformat=channel_layouts=stereo[v]"
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", dst])


def main():
    vcfg = config().get("voice", {"preset": "basic"})
    FPS = probe()[2]
    keep = json.load(open(f"{WORK}/keep.json"))
    segs = [(round(a * FPS) / FPS, round(b * FPS) / FPS) for a, b in keep]
    parts, labels = [], []
    for i, (a, b) in enumerate(segs):
        d = b - a
        parts.append(f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d - 0.015:.4f}:d=0.015[a{i}]")
        labels.append(f"[a{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(segs)}:v=0:a=1,aresample=48000[c]"
    raw = f"{WORK}/voice_raw.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", fc, "-map", "[c]", "-ac", "1",
         "-c:a", "pcm_s16le", raw])
    # source-time -> output-time map
    out, t = [], 0.0
    for a, b in segs:
        out.append({"src": [a, b], "out": round(t, 4)}); t += b - a
    process(raw, f"{WORK}/voice.wav", vcfg["preset"], t, vcfg.get("denoise_atten_db", 40))
    json.dump({"segs": out, "dur": round(t, 4)}, open(f"{WORK}/edl.json", "w"), indent=1)
    print("dur", t, "voice preset", vcfg["preset"])


if __name__ == "__main__":
    main()
