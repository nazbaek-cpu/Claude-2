"""Cut the voice track with the same frame-quantized keep list as the video, then clean it up.
Writes work/voice.wav and the source->output time map work/edl.json."""
import json, subprocess
from media import SRC, WORK, probe

FPS = probe()[2]
keep = json.load(open(f"{WORK}/keep.json"))
segs = [(round(a * FPS) / FPS, round(b * FPS) / FPS) for a, b in keep]
parts, labels = [], []
for i, (a, b) in enumerate(segs):
    d = b - a
    parts.append(f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d - 0.015:.4f}:d=0.015[a{i}]")
    labels.append(f"[a{i}]")
fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(segs)}:v=0:a=1[c];" \
     "[c]highpass=f=70,afftdn=nf=-30,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120," \
     "loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000[v]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", fc, "-map", "[v]",
                "-ac", "2", f"{WORK}/voice.wav"], check=True)
# source-time -> output-time map
out, t = [], 0.0
for a, b in segs:
    out.append({"src": [a, b], "out": round(t, 4)}); t += b - a
json.dump({"segs": out, "dur": round(t, 4)}, open(f"{WORK}/edl.json", "w"), indent=1)
print("dur", t)
