"""Plan product zooms: when the speaker points at the product ("buku ni", "tengok ni", ...) and it is
visible in her hands, zoom gently onto it for a few seconds. Writes work/zooms.json (source seconds,
full-res pixels): [{"start", "end", "cx", "cy", "z"}].

The product is found as the area dense in printed lines/text (Canny edges) outside the face/hijab,
the dark background and the top of the frame. Its centre and size are taken as the median over the
zoom window so the framing does not jitter.

config.json "product_zoom": {"enabled", "zoom", "min_zoom", "hold_s", "min_gap_s", "triggers"}
"triggers" is a list of regexes, strongest first, matched against 2- and 3-word windows of the transcript.
"""
import json, re, subprocess
import numpy as np, cv2
from media import SRC, WORK, config, probe
from look import MODEL

AW, AH, AFPS = 270, 480, 10  # analysis size / rate


def analyse(src, flip):
    """per analysed frame: (t, score, cx, cy, bw, bh) in analysis pixels (score 0 = no product)"""
    vf = ("hflip," if flip else "") + f"scale={AW}:{AH},fps={AFPS}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, AH, AW, 3)
    det = cv2.FaceDetectorYN.create(MODEL, "", (AW, AH), 0.6, 0.3, 5)
    out, face = [], None
    yy, xx = np.mgrid[0:AH, 0:AW]
    for i, img in enumerate(frames):
        _, faces = det.detect(img)
        if faces is not None and len(faces):
            face = max(faces, key=lambda r: r[2] * r[3])[:4]
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        e = cv2.Canny(g, 60, 160).astype(np.float32) / 255
        dens = cv2.GaussianBlur(e, (0, 0), 6)
        keep = (g > 45) & (yy > 0.25 * AH)                     # no dark background, no top of frame
        if face is not None:
            x, y, w, h = face
            keep &= ~((xx > x - 0.6 * w) & (xx < x + 1.6 * w) & (yy > y - 0.5 * h) & (yy < y + 1.5 * h))
        d = dens * keep
        if d.max() <= 0.02:
            out.append((i / AFPS, 0.0, 0, 0, 0, 0)); continue
        bm = (d > 0.35 * d.max()).astype(np.uint8)
        n, lab, st, cen = cv2.connectedComponentsWithStats(bm)
        j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        area = st[j, cv2.CC_STAT_AREA]
        score = float(d[lab == j].mean()) * min(1.0, area / (0.04 * AW * AH))
        out.append((i / AFPS, score, cen[j][0], cen[j][1], st[j, cv2.CC_STAT_WIDTH], st[j, cv2.CC_STAT_HEIGHT]))
    return np.array(out)


def trigger_times(tr, patterns):
    """-> [(time, priority)], priority 0 = strongest pattern"""
    words = [(w[0], w[2].strip().lower().strip(".,?!")) for seg in tr for w in seg["w"]]
    hits = {}
    for prio, pat in enumerate(patterns):
        rx = re.compile(pat)
        for i in range(len(words) - 1):
            for n in (2, 3):
                if i + n <= len(words) and rx.fullmatch(" ".join(w for _, w in words[i:i + n])):
                    t = words[i][0]
                    hits[t] = min(prio, hits.get(t, prio))
    return sorted(hits.items())


def plan(track, triggers, W, H, dur, zoom=1.3, hold=5.0, min_gap=8.0, min_zoom=1.18):
    good = track[:, 1] > 0.5 * np.percentile(track[:, 1], 90)
    zooms = []
    for t, _ in sorted(triggers, key=lambda tp: (tp[1], tp[0])):  # strongest cue first
        if any(abs(t - z["start"]) < min_gap for z in zooms):
            continue
        near = np.nonzero(good & (track[:, 0] >= t - 0.3) & (track[:, 0] <= t + 1.5))[0]
        if not len(near):
            continue
        start = track[near[0], 0]
        end = min(start + hold, dur - 0.1)
        win = good & (track[:, 0] >= start) & (track[:, 0] <= end)
        if win.sum() < 0.5 * (end - start) * AFPS:   # product not held up long enough
            continue
        cx, cy, bw, bh = (np.median(track[win, k]) for k in (2, 3, 4, 5))
        sx, sy = W / AW, H / AH
        fit = min(0.92 * W / max(bw * sx, 1), 0.92 * H / max(bh * sy, 1))
        z = float(np.clip(fit, min_zoom, zoom))  # always a noticeable but gentle push-in
        zooms.append({"start": round(float(start), 2), "end": round(float(end), 2),
                      "cx": round(float(cx * sx), 1), "cy": round(float(cy * sy), 1), "z": round(z, 3)})
    return sorted(zooms, key=lambda z: z["start"])


def main():
    cfg = config()
    pz = cfg.get("product_zoom", {})
    zooms = []
    if pz.get("enabled"):
        W, H, _, dur = probe()
        track = analyse(SRC, cfg["flip"])
        trig = trigger_times(json.load(open(f"{WORK}/tr_large.json")), pz["triggers"])
        zooms = plan(track, trig, W, H, dur, pz.get("zoom", 1.3), pz.get("hold_s", 5.0), pz.get("min_gap_s", 8.0),
                     pz.get("min_zoom", 1.18))
    json.dump(zooms, open(f"{WORK}/zooms.json", "w"), indent=1)
    print(len(zooms), "product zooms:", ", ".join(f"{z['start']}-{z['end']}s x{z['z']}" for z in zooms))


if __name__ == "__main__":
    main()
