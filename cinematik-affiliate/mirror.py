"""Is the take mirrored? OCR sampled frames as shot and flipped; the side that reads better wins.

  python mirror.py projects/<name>          prints the verdict and the text read either way

"hflip": "auto" (the presets' default) asks this once per source and caches it in build/mirror.json.
"""
import json, os, subprocess, sys

import numpy as np

import project

FRAMES = 16          # spread over 5-95 % of the take
WIDTH = 720
MIN_CONF = 0.8       # ignore OCR guesses below this
MARGIN = 1.5         # one side must read this much better to decide


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def frame(src, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                          "-vf", f"scale={WIDTH}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, WIDTH, 3)


def legible(ocr, img):
    """Sum of confident letters OCR reads in img, plus what it read."""
    res, _ = ocr(img)
    score, words = 0.0, []
    for _, text, conf in res or []:
        letters = sum(c.isalpha() for c in text)
        if float(conf) >= MIN_CONF and letters >= 3:
            score += float(conf) * letters
            words.append(text)
    return score, words


def read(src, frames=FRAMES):
    from rapidocr_onnxruntime import RapidOCR
    ocr, d = RapidOCR(), probe(src)
    plain = flipped = 0.0
    seen = {"plain": [], "flipped": []}
    for i in range(frames):
        img = frame(src, d * (0.05 + 0.9 * i / max(frames - 1, 1)))
        a, wa = legible(ocr, img)
        b, wb = legible(ocr, np.ascontiguousarray(img[:, ::-1]))
        plain, flipped = plain + a, flipped + b
        seen["plain"] += wa
        seen["flipped"] += wb
    return plain, flipped, seen


def verdict(plain, flipped):
    """True = mirrored, False = reads as shot, None = not enough text to tell."""
    if max(plain, flipped) < 8:
        return None
    if flipped > plain * MARGIN:
        return True
    if plain > flipped * MARGIN:
        return False
    return None


def cached(prj, src):
    """hflip for "auto": True when the take is mirrored; no readable text counts as not mirrored."""
    if not os.path.exists(src):
        return False
    st = os.stat(src)
    key = [st.st_size, int(st.st_mtime)]
    path = os.path.join(prj, "build", "mirror.json")
    if os.path.exists(path):
        c = json.load(open(path))
        if c.get("source") == key:
            return bool(c["mirrored"])
    plain, flipped, seen = read(src)
    v = bool(verdict(plain, flipped))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"source": key, "mirrored": v, "as_shot": round(plain), "flipped": round(flipped),
               "read": seen["flipped" if v else "plain"][:12]}, open(path, "w"), indent=1)
    return v


if __name__ == "__main__":
    prj = sys.argv[1].rstrip("/")
    cfg = project.read(prj)
    plain, flipped, seen = read(f"{prj}/{cfg['source']}")
    v = verdict(plain, flipped)
    print(f"as shot {plain:.0f}: {seen['plain'][:8]}")
    print(f"flipped {flipped:.0f}: {seen['flipped'][:8]}")
    print("mirrored -> hflip true" if v else "reads as shot -> hflip false" if v is False else "no clear text -> keep setting")
