"""Cut a character pose sheet (a grid of poses on a flat paper background, labels under each) into transparent PNGs.

    python poses.py sheet.png projects/<name>/input/doodle --grid 4x2

Writes pose1.png ... poseN.png (left to right, top to bottom) for the explainer's "doodle" item. The paper colour is
read from the corner; anything that colour becomes transparent (holes between arms and body too), the anti-aliased rim
next to it is un-mixed from the paper, the label under each pose is dropped and the pink floor shadow turns into a soft
dark one.
"""
import argparse, os

import cv2
import numpy as np
from PIL import Image

def cut(sheet, cols, rows, tol=14):
    a = np.asarray(Image.open(sheet).convert("RGB")).astype(np.float32)
    paper = np.median(np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3)]), axis=0)
    dist = np.linalg.norm(a - paper, axis=-1)
    bg = dist < tol
    rim = cv2.dilate(bg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~bg
    # un-mix the rim from the paper (colour-to-alpha), so the outline keeps a clean soft edge on any background
    lo = np.where(a < paper, (paper - a) / np.maximum(paper, 1), (a - paper) / np.maximum(255 - paper, 1))
    alpha = np.where(bg, 0.0, np.where(rim, np.clip(lo.max(-1), 0, 1), 1.0))
    safe = np.maximum(alpha, 1e-3)[..., None]
    rgb = np.where(rim[..., None], np.clip((a - paper) / safe + paper, 0, 255), a)
    H, W = a.shape[0] // rows, a.shape[1] // cols
    cells = []
    for r in range(rows):
        for c in range(cols):
            y0, x0 = r * H, c * W
            al = alpha[y0:y0 + H, x0:x0 + W].copy(); px = rgb[y0:y0 + H, x0:x0 + W].copy()
            used = np.where((al > 0.3).sum(1) > 0)[0]
            bands, s = [], used[0]   # vertical runs of ink; the label is the last short run near the bottom
            for i in range(1, len(used)):
                if used[i] - used[i - 1] > 12: bands.append((s, used[i - 1])); s = used[i]
            bands.append((s, used[-1]))
            if len(bands) > 1 and bands[-1][1] - bands[-1][0] < 80 and bands[-1][0] > H * 0.75: bands.pop()
            top, bot = bands[0][0], bands[-1][1]
            al[bot + 1:] = 0
            p = px.astype(np.float32)   # pink floor shadow (low, reddish) -> soft dark shadow
            pink = (p[..., 0] > 150) & (p[..., 0] - p[..., 2] > 25) & (np.arange(H)[:, None] > top + (bot - top) * 0.85)
            px[pink] = (20, 12, 8); al[pink] = np.minimum(al[pink], 0.22)
            xs = np.where((al > 0.3).sum(0) > 0)[0]
            cells.append((px, al, (xs[0], top, xs[-1], bot)))
    # one crop box for every pose, in cell coordinates: the character stays where the sheet drew it when poses switch
    x0 = max(0, min(b[0] for *_, b in cells) - 4); y0 = max(0, min(b[1] for *_, b in cells) - 4)
    x1 = max(b[2] for *_, b in cells) + 5; y1 = max(b[3] for *_, b in cells) + 5
    out = [Image.fromarray(np.dstack([px, al[..., None] * 255]).astype(np.uint8)[y0:y1, x0:x1], "RGBA") for px, al, _ in cells]
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sheet"); ap.add_argument("out"); ap.add_argument("--grid", default="4x2")
    args = ap.parse_args(); cols, rows = map(int, args.grid.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)
    for i, im in enumerate(cut(args.sheet, cols, rows), 1):
        im.save(os.path.join(args.out, f"pose{i}.png")); print(f"pose{i}.png {im.size}")

if __name__ == "__main__":
    main()
