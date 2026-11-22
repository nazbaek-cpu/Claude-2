"""Plain backgrounds shared by the templates: "grey", "dots" and "hitam" (black with a dot grid).

    import latar
    im = latar.make("hitam", 1080, 1920)      # RGB PIL image
    latar.LIGHT["grey"]                        # True: dark ink reads on it; False: use white type

episod:  "bg": "grey" | "dots" | "hitam" | "mustard"        (stage() draws the frame and floor line on top)
kertas:  "bg": "grey" | "dots" | "hitam" | "mustard" in project.json (write(..., bg=...)): the page is drawn behind every scene;
         "hitam" pairs with theme "kertas-neon" so the writing is light.
"""
import numpy as np
from PIL import Image, ImageDraw

KINDS = ("grey", "dots", "hitam", "mustard")
LIGHT = {"grey": True, "dots": True, "hitam": False, "mustard": True}


def _grain(h, w, amp, seed):
    return np.random.default_rng(seed).normal(0, amp, (h, w, 1)).astype(np.float32)


def make(kind, w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w * 0.5) / w) ** 2 + ((yy - h * 0.42) / h) ** 2)[..., None]   # soft centre light
    if kind == "mustard":   # warm mustard yellow, lighter in the middle, fine paper grain (dark ink reads on it)
        a = np.array([226, 178, 58], np.float32) * (1.05 - 0.14 * r) + _grain(h, w, 1.8, 6)
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if kind == "grey":   # light cool grey, a touch lighter in the middle, fine paper grain
        a = np.array([206, 208, 212], np.float32) * (1.04 - 0.10 * r) + _grain(h, w, 1.6, 4)
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if kind == "dots":   # white page with a fine grey dot grid
        im = Image.new("RGB", (w, h), (252, 252, 251)); d = ImageDraw.Draw(im); g, rr = 28, 2.3
        for y in np.arange(g / 2, h, g):
            for x in np.arange(g / 2, w, g): d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(178, 178, 182))
        return im
    if kind == "hitam":   # near-black with a dim dot grid and a faint lift in the middle
        a = np.array([24, 25, 29], np.float32) * (1.25 - 0.55 * r) + _grain(h, w, 1.0, 5)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im); g, rr = 32, 2.2
        for y in np.arange(g / 2, h, g):
            for x in np.arange(g / 2, w, g): d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(62, 64, 72))
        return im
    raise ValueError(f"unknown background {kind!r} (choose from {KINDS})")
