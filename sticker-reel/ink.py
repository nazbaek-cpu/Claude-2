"""Line art on white paper -> transparent ink PNG (for background doodles and decorations).

usage: ink.py <out_dir> <image> [<image> ...]   [--crop x0,y0,x1,y1] [--scale 1.5]
--crop cuts a box (pixels of the source) first, e.g. one face out of a page of drawings.
"""
import os, sys
import numpy as np, cv2


def ink(img, color=(30, 30, 30)):
    """paper -> transparent, strokes -> opaque `color` (BGR)"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    a = np.clip((235 - g) / 150, 0, 1)
    return np.dstack([np.full_like(g, c) for c in color] + [a * 255]).astype(np.uint8)


def main():
    args = sys.argv[1:]
    crop = scale = None
    if "--crop" in args:
        i = args.index("--crop"); crop = [int(v) for v in args[i + 1].split(",")]; del args[i:i + 2]
    if "--scale" in args:
        i = args.index("--scale"); scale = float(args[i + 1]); del args[i:i + 2]
    out, files = args[0], args[1:]
    os.makedirs(out, exist_ok=True)
    for f in files:
        img = cv2.imread(f)
        if crop:
            x0, y0, x1, y1 = crop; img = img[y0:y1, x0:x1]
        if scale:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        dst = os.path.join(out, os.path.splitext(os.path.basename(f))[0] + ".png")
        cv2.imwrite(dst, ink(img)); print(dst)


if __name__ == "__main__":
    main()
