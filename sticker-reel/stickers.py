"""Face photos -> outlined stickers (transparent PNG), sized so every face shows at the same size in the video.

usage: stickers.py <project> [--previews]
project.json "stickers":
  "grid":   {"file": "input/poses/grid.png", "cols": 3, "rows": 2}   one image holding several poses (optional)
  "names":  ["tenang", "senyum", ...]                                  names for the grid cells, row by row
  "photos": {"tunjuk": "input/poses/tunjuk.jpg", ...}                  single photos (optional)
  "ready":  {"wave": "input/poses/wave_sticker.png", ...}              finished stickers, used as they are
  "face_px": 300, "max_h": 720, "outline_px": 30
Photos that already have transparency are only outlined; others are cut out with BiRefNet.
Writes build/stickers/<name>.png, heights.json (display height per sticker), _sheet.jpg; --previews also
writes yellow 4:5 and 1:1 pictures to build/stickers/yellow/.
"""
import json, os, sys
import numpy as np, cv2
from common import MODELS, Project

SEG_MODEL = os.path.join(MODELS, "birefnet_lite.onnx")
FACE_MODEL = os.path.join(MODELS, "yunet.onnx")
_seg = None


def seg(img):
    """person (and anything held) alpha 0..1 with BiRefNet-lite"""
    global _seg
    if _seg is None:
        import onnxruntime as ort
        _seg = ort.InferenceSession(SEG_MODEL, providers=["CPUExecutionProvider"])
    H, W = img.shape[:2]
    x = cv2.resize(img, (1024, 1024))[..., ::-1].astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    o = _seg.run(None, {"input_image": x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
    if o.min() < 0 or o.max() > 1:
        o = 1 / (1 + np.exp(-o))
    return cv2.resize(o, (W, H))


def split_grid(img, cols, rows):
    """cells of a collage; cuts on the white separator lines when there are any, else evenly"""
    white = img.min(axis=2) > 235

    def cuts(profile, n, size):
        runs, i = [], 0
        while i < size:
            if profile[i] > 0.97:
                j = i
                while j < size and profile[j] > 0.97:
                    j += 1
                runs.append((i, j)); i = j
            else:
                i += 1
        edges = [0]
        for k in range(1, n):
            want = k * size / n
            near = [r for r in runs if abs((r[0] + r[1]) / 2 - want) < size / (4 * n)]
            edges += [near[0][0], near[0][1]] if near else [int(want), int(want)]
        return list(zip(edges[::2], edges[1::2] + [size]))

    xs = cuts(white.mean(0), cols, img.shape[1]); ys = cuts(white.mean(1), rows, img.shape[0])
    return [img[y0:y1, x0:x1] for y0, y1 in ys for x0, x1 in xs]


def outline(img, a, px=30):
    """-> RGBA: person over a white rounded outline px wide, cropped to the sticker"""
    pw = px + 40
    a = np.pad(a.astype(np.float32), pw); img = np.pad(img.astype(np.float32), ((pw, pw), (pw, pw), (0, 0)), mode="edge")
    a[a < 0.04] = 0
    b = cv2.morphologyEx((a > 0.5).astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(b)
    if n > 1:  # keep the main body only
        b = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    a = a * cv2.dilate(b, np.ones((5, 5), np.uint8))
    o = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)))
    o = cv2.GaussianBlur(o.astype(np.float32), (0, 0), 6); o = np.clip((o - 0.5) * 6 + 0.5, 0, 1)
    rgb = img * a[..., None] + 255 * (1 - a[..., None])
    alpha = np.maximum(o, a)
    ys, xs = np.nonzero(alpha > 0.01)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return np.dstack([rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1] * 255]).astype(np.uint8)


def display_height(rgba, face_px=300, max_h=720):
    """height on screen that makes the face face_px wide (capped at max_h)"""
    a = rgba[..., 3:4] / 255.0
    rgb = (rgba[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    h, w = rgb.shape[:2]
    det = cv2.FaceDetectorYN.create(FACE_MODEL, "", (w, h), 0.5, 0.3, 5)
    _, faces = det.detect(rgb)
    fw = max(faces, key=lambda r: r[2] * r[3])[2] if faces is not None and len(faces) else 0.38 * w
    return int(round(min(max_h, face_px / fw * h)))


def yellow(rgba, w, h, c1=(110, 228, 255), c2=(30, 196, 255)):
    """sticker on a warm yellow radial background with a soft drop shadow (BGR colours)"""
    pad, foot = round(0.065 * w), round(0.037 * h)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.clip(np.sqrt(((xx - w / 2) / w) ** 2 + ((yy - h * 0.45) / h) ** 2) / 0.7, 0, 1)[..., None]
    bg = np.array(c1, np.float32) * (1 - d) + np.array(c2, np.float32) * d
    rgb, al = rgba[..., :3].astype(np.float32), rgba[..., 3].astype(np.float32) / 255
    s = min((w - 2 * pad) / rgb.shape[1], (h - pad - foot) / rgb.shape[0])
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    r = cv2.resize(rgb, None, fx=s, fy=s, interpolation=interp); al = np.clip(cv2.resize(al, None, fx=s, fy=s), 0, 1)
    hh, ww = al.shape; ox, oy = (w - ww) // 2, h - hh - foot
    sh = np.zeros((h, w), np.float32); sh[oy:oy + hh, ox:ox + ww] = al
    sh = cv2.GaussianBlur(np.roll(sh, 14, 0), (0, 0), 16)[..., None] * 0.28
    bg = bg * (1 - sh) + np.array([20, 90, 140], np.float32) * sh
    reg = bg[oy:oy + hh, ox:ox + ww]
    bg[oy:oy + hh, ox:ox + ww] = reg * (1 - al[..., None]) + r * al[..., None]
    return np.clip(bg, 0, 255).astype(np.uint8)


def load_inputs(prj, cfg):
    """-> [(name, BGR or BGRA image)] to cut out and outline"""
    out = []
    g = cfg.get("grid")
    if g:
        img = cv2.imread(prj.p(g["file"]))
        cells = split_grid(img, g.get("cols", 3), g.get("rows", 2))
        names = cfg.get("names") or [f"pose{i + 1}" for i in range(len(cells))]
        if len(names) != len(cells):
            raise SystemExit(f"stickers.names has {len(names)} names for {len(cells)} grid cells")
        out += list(zip(names, cells))
    for name, f in cfg.get("photos", {}).items():
        img = cv2.imread(prj.p(f), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise SystemExit(f"cannot read {f}")
        out.append((name, img))
    return out


def main():
    prj = Project(sys.argv[1]); cfg = prj.cfg["stickers"]
    dst = prj.p("build", "stickers"); os.makedirs(dst, exist_ok=True)
    heights, thumbs = {}, []
    todo = [(n, img, False) for n, img in load_inputs(prj, cfg)]
    todo += [(n, cv2.imread(prj.p(f), cv2.IMREAD_UNCHANGED), True) for n, f in cfg.get("ready", {}).items()]
    for name, img, ready in todo:
        if img is None or (ready and (img.ndim != 3 or img.shape[2] != 4)):
            raise SystemExit(f"sticker {name}: cannot read it, or a ready sticker without transparency")
        if ready:
            st = img
        elif img.ndim == 3 and img.shape[2] == 4 and img[..., 3].min() < 250:   # already cut out: only outline it
            st = outline(img[..., :3], img[..., 3] / 255.0, cfg.get("outline_px", 30))
        else:
            rgb = img[..., :3]
            if max(rgb.shape[:2]) < 900:   # collage cells are small: upscale before cutting out
                rgb = cv2.resize(rgb, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
            st = outline(rgb, seg(rgb), cfg.get("outline_px", 30))
        s = min(1.0, 1000 / max(st.shape[:2]))
        st = cv2.resize(st, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(f"{dst}/{name}.png", st)
        heights[name] = display_height(st, cfg.get("face_px", 300), cfg.get("max_h", 720))
        thumbs.append(cv2.resize(yellow(st, 1080, 1350), (270, 338)))
        if "--previews" in sys.argv:
            os.makedirs(f"{dst}/yellow", exist_ok=True)
            for w, h, tag in ((1080, 1350, "4x5"), (1080, 1080, "1x1")):
                cv2.imwrite(f"{dst}/yellow/{name}_{tag}.jpg", yellow(st, w, h), [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(name, st.shape[1], "x", st.shape[0], "-> shown", heights[name], "px tall", flush=True)
    json.dump(heights, open(f"{dst}/heights.json", "w"), indent=1)
    while len(thumbs) % 4:
        thumbs.append(np.zeros_like(thumbs[0]))
    cv2.imwrite(f"{dst}/_sheet.jpg", np.vstack([np.hstack(thumbs[i:i + 4]) for i in range(0, len(thumbs), 4)]))


if __name__ == "__main__":
    main()
