"""Cut a character pose sheet (a grid of poses on a flat paper background, labels under each) into transparent PNGs.

    python poses.py sheet.png projects/<name>/input/doodle --grid 4x2 [--top 110]
    python poses.py icons.png projects/<name>/input/icons --grid 5x5 --top 100 --icons --names diari,pen,...

    python poses.py band.png projects/<name>/input/kira --auto 10 --names sapa,idea,...

Writes pose1.png ... poseN.png (left to right, top to bottom) for the explainer's "doodle" item; --top skips a title
above the grid, --icons crops every cell to its own icon (no shared box, no floor shadow) and --names names the files. The paper colour is
read from the corner; anything that colour becomes transparent (holes between arms and body too), the anti-aliased rim
next to it is un-mixed from the paper, the label under each pose is dropped and the pink floor shadow turns into a soft
dark one. --auto N is for a row of N figures that are not evenly spaced: the N largest shapes are the figures, every
smaller mark (a light bulb, a rain cloud, a thought bubble) goes to the figure it is closest to, and marks lying below a
figure's feet (its label) are dropped; each figure keeps its own place relative to its feet, so poses switch cleanly.
"""
import argparse, os

import cv2
import numpy as np
from PIL import Image

def cut(sheet, cols, rows, tol=14, top_skip=0, icons=False):
    a = np.asarray(Image.open(sheet).convert("RGB")).astype(np.float32)[top_skip:]
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
            if not icons:
                p = px.astype(np.float32)   # pink floor shadow (low, reddish) -> soft dark shadow
                pink = (p[..., 0] > 150) & (p[..., 0] - p[..., 2] > 25) & (np.arange(H)[:, None] > top + (bot - top) * 0.85)
                px[pink] = (20, 12, 8); al[pink] = np.minimum(al[pink], 0.22)
            xs = np.where((al > 0.3).sum(0) > 0)[0]
            cells.append((px, al, (xs[0], top, xs[-1], bot)))
    if icons:
        return [Image.fromarray(np.dstack([px, al[..., None] * 255]).astype(np.uint8)[max(0, b[1] - 4):b[3] + 5, max(0, b[0] - 4):b[2] + 5], "RGBA")
                for px, al, b in (_drop_slivers(*c) for c in cells)]
    # one crop box for every pose, in cell coordinates: the character stays where the sheet drew it when poses switch
    x0 = max(0, min(b[0] for *_, b in cells) - 4); y0 = max(0, min(b[1] for *_, b in cells) - 4)
    x1 = max(b[2] for *_, b in cells) + 5; y1 = max(b[3] for *_, b in cells) + 5
    out = [Image.fromarray(np.dstack([px, al[..., None] * 255]).astype(np.uint8)[y0:y1, x0:x1], "RGBA") for px, al, _ in cells]
    return out

def matte(sheet, tol=14, top_skip=0):
    """the sheet as un-mixed colour and alpha: paper (read from the corners) becomes transparent"""
    a = np.asarray(Image.open(sheet).convert("RGB")).astype(np.float32)[top_skip:]
    paper = np.median(np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3)]), axis=0)
    bg = np.linalg.norm(a - paper, axis=-1) < tol
    rim = cv2.dilate(bg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~bg
    lo = np.where(a < paper, (paper - a) / np.maximum(paper, 1), (a - paper) / np.maximum(255 - paper, 1))
    alpha = np.where(bg, 0.0, np.where(rim, np.clip(lo.max(-1), 0, 1), 1.0))
    rgb = np.where(rim[..., None], np.clip((a - paper) / np.maximum(alpha, 1e-3)[..., None] + paper, 0, 255), a)
    return rgb, alpha

def cut_auto(sheet, n, tol=14, top_skip=0, icons=False):
    rgb, alpha = matte(sheet, tol, top_skip)
    k, lab, stats, cent = cv2.connectedComponentsWithStats((alpha > 0.3).astype(np.uint8), connectivity=8)
    seeds = sorted(sorted(range(1, k), key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:n], key=lambda i: cent[i][0])
    dist = [cv2.distanceTransform((lab != s).astype(np.uint8), cv2.DIST_L2, 3) for s in seeds]
    owner = {s: j for j, s in enumerate(seeds)}
    feet = [stats[s, cv2.CC_STAT_TOP] + stats[s, cv2.CC_STAT_HEIGHT] for s in seeds]
    # strokes of one mark (three little lines, a pair of sparkles) travel together: cluster the small shapes first
    small = (lab > 0) & ~np.isin(lab, seeds)
    nc, clus = cv2.connectedComponents(cv2.dilate(small.astype(np.uint8), np.ones((13, 13), np.uint8)), connectivity=8)
    for c in range(1, nc):
        m = (clus == c) & small
        if not m.any(): continue
        mx = np.where(m)[1].mean()
        # nearest figure by gap, with a pull towards the figure whose centre is closer sideways
        j = int(np.argmin([d[m].min() + 0.5 * abs(mx - cent[sd][0]) for d, sd in zip(dist, seeds)]))
        for i in np.unique(lab[m]):
            if stats[i, cv2.CC_STAT_TOP] > feet[j] + 4: continue   # below the feet: the label
            owner[int(i)] = j
    figs = []
    for j, s in enumerate(seeds):
        keep = np.isin(lab, [i for i, o in owner.items() if o == j])
        a_ = cv2.dilate(keep.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)   # the soft rim around each kept shape
        al = np.where(a_, alpha, 0.0); ys, xs = np.where(al > 0.02)
        cx = stats[s, cv2.CC_STAT_LEFT] + stats[s, cv2.CC_STAT_WIDTH] / 2
        figs.append((al, (xs.min(), ys.min(), xs.max(), ys.max()), cx, feet[j]))
    img = lambda al, x0, y0, x1, y1: Image.fromarray(np.dstack([rgb, al[..., None] * 255]).astype(np.uint8)[y0:y1, x0:x1], "RGBA")   # noqa: E731
    if icons:
        return [img(al, max(0, b[0] - 4), max(0, b[1] - 4), b[2] + 5, b[3] + 5) for al, b, _, _ in figs]
    # one canvas size for every pose, each placed by its feet: the figure stands still when poses switch
    L = max(cx - b[0] for _, b, cx, _ in figs) + 4; R = max(b[2] - cx for _, b, cx, _ in figs) + 5
    U = max(f - b[1] for _, b, _, f in figs) + 4; D = max(b[3] - f for _, b, _, f in figs) + 5
    out = []
    for al, b, cx, f in figs:
        canvas = Image.new("RGBA", (int(L + R), int(U + D)), (0, 0, 0, 0))
        x0, y0 = int(cx - L), int(f - U)
        piece = img(al, max(0, x0), max(0, y0), int(cx + R), int(f + D))
        canvas.paste(piece, (max(0, -x0), max(0, -y0))); out.append(canvas)
    return out

def _drop_slivers(px, al, b):
    """an icon cell can catch the tip of its neighbour's sparkle: small shapes cut by the cell's side edge go"""
    k, lab, st, _ = cv2.connectedComponentsWithStats((al > 0.3).astype(np.uint8), connectivity=8)
    if k <= 2: return px, al, b
    big = st[1:, cv2.CC_STAT_AREA].max(); w = al.shape[1]; al = al.copy()
    for i in range(1, k):
        x0, x1 = st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]
        if st[i, cv2.CC_STAT_AREA] < 0.2 * big and (x0 == 0 or x1 >= w):
            al[cv2.dilate((lab == i).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)] = 0
    ys, xs = np.where(al > 0.3)
    return px, al, (xs.min(), ys.min(), xs.max(), ys.max())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sheet"); ap.add_argument("out"); ap.add_argument("--grid", default="4x2")
    ap.add_argument("--top", type=int, default=0); ap.add_argument("--icons", action="store_true"); ap.add_argument("--names", default="")
    ap.add_argument("--auto", type=int, default=0, help="N figures, found by shape instead of a grid")
    args = ap.parse_args(); cols, rows = map(int, args.grid.lower().split("x"))
    names = [n.strip() for n in args.names.split(",") if n.strip()]
    os.makedirs(args.out, exist_ok=True)
    ims = (cut_auto(args.sheet, args.auto, top_skip=args.top, icons=args.icons) if args.auto
           else cut(args.sheet, cols, rows, top_skip=args.top, icons=args.icons))
    for i, im in enumerate(ims, 1):
        name = (names[i - 1] if i <= len(names) else f"pose{i}") + ".png"
        im.save(os.path.join(args.out, name)); print(f"{name} {im.size}")

if __name__ == "__main__":
    main()
