"""Render the A-roll: cut pauses, un-mirror, grade, skin retouch, alternating zoom per cut,
and gentle product zooms from work/zooms.json (see zoom.py).
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
PZ = json.load(open(f"{WORK}/zooms.json")) if os.path.exists(f"{WORK}/zooms.json") else []
RAMP = 0.6  # s, product zoom in/out


def zoom(img, z, cx, cy):
    """scale by z keeping (cx, cy) fixed (the per-cut punch-in)"""
    if z == 1.0:
        return img
    M = np.float32([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def product_weight(t):
    """0..1 eased weight of the product zoom active at source time t, and that zoom"""
    for pz in PZ:
        a, b = pz["start"], pz["end"]
        if a <= t <= b:
            x = min(1.0, (t - a) / RAMP, (b - t) / RAMP)
            return x * x * (3 - 2 * x), pz
    return 0.0, None


def frame_zoom(img, z0, anchor, t):
    w, pz = product_weight(t)
    if w <= 0:
        return zoom(img, z0, *anchor)
    # blend the per-cut view (as a crop window) into a crop centred on the product
    u0 = np.array(anchor) + (np.array([W / 2, H / 2]) - np.array(anchor)) / z0
    u1 = np.array([pz["cx"], pz["cy"]])
    z = z0 + (pz["z"] - z0) * w
    u = u0 + (u1 - u0) * w
    hw, hh = W / (2 * z), H / (2 * z)
    ux, uy = np.clip(u[0], hw, W - hw), np.clip(u[1], hh, H - hh)  # never show past the frame edge
    M = np.float32([[z, 0, W / 2 - z * ux], [0, z, H / 2 - z * uy]])
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
        enc.stdin.write(frame_zoom(img, z, anchor, (f0 + got) / FPS).tobytes())
        got += 1
    if got == 0:
        raise SystemExit(f"segment {k}: decoder returned no frames at {f0 / FPS:.3f}s")
    # pad if decoder came up short (keeps audio/video in sync)
    while got < n:
        enc.stdin.write(frame_zoom(img, z, anchor, (f0 + got) / FPS).tobytes()); got += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    print("done", k, n, flush=True)
