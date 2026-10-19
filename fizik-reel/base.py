"""Render the A-roll: cut pauses, un-mirror, grade, skin retouch, alternating zoom per cut.
usage: base.py <worker> <nworkers>   -> work/segs/sNN.mp4
"""
import json, subprocess, sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from look import grade, Retoucher
from media import SRC, WORK, config, probe

CFG = config()
W, H, FPS, _ = probe()
keep = json.load(open(f"{WORK}/keep.json"))
segs = [(round(a * FPS), round(b * FPS)) for a, b in keep]
wi, nw = int(sys.argv[1]), int(sys.argv[2])
os.makedirs(f"{WORK}/segs", exist_ok=True)
ZOOMS = CFG["zooms"]
VF = "hflip" if CFG["flip"] else "null"


def zoom(img, z, cx, cy):
    if z == 1.0:
        return img
    M = np.float32([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


for k, (f0, f1) in enumerate(segs):
    if k % nw != wi:
        continue
    out = f"{WORK}/segs/s{k:02d}.mp4"
    n = f1 - f0
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.4f}", "-i", SRC,
                            "-frames:v", str(n), "-vf", VF, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    mk = CFG.get("makeup", {})
    r = Retoucher(W, H, mk.get("lips", 0.0), mk.get("brows", 0.0))
    z = ZOOMS[k % len(ZOOMS)]
    anchor = None
    got = 0
    while got < n:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        img = r(grade(img))
        if anchor is None:
            b = r.box
            anchor = (b[0] + b[2] / 2, b[1] + b[3] / 2) if b is not None else (W / 2, H * 0.42)
        enc.stdin.write(zoom(img, z, *anchor).tobytes())
        got += 1
    if got == 0:
        raise SystemExit(f"segment {k}: decoder returned no frames at {f0 / FPS:.3f}s")
    # pad if decoder came up short (keeps audio/video in sync)
    while got < n:
        enc.stdin.write(zoom(img, z, *anchor).tobytes()); got += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    print("done", k, n, flush=True)
