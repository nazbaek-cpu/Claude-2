"""Neon "tiub": thin, even-stroke letters that look like bent glass tubes (the user's reference: a pink NEON sign).

Look, read off the reference:
  - letters are single thin strokes of even width (a light geometric sans), rounded ends, airy letter spacing
  - the tube itself is a pale, almost white tint of the colour; its edges are the full, saturated colour
  - a tight bright halo hugs each stroke, a medium halo fills the counters, and a wide faint glow spills
    onto the dark page around the whole word
Any colour works: the recipe only takes the accent colour.

    import neon_tiub
    img, pad = neon_tiub.word("CALON SPM", 112, (255, 40, 160), track=0.10)
    m = neon_tiub.mask("teks", font)            # an L mask of thin text you place yourself
    img, pad = neon_tiub.light(m, (0, 229, 255), size=84)
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = ["tiub"]   # "tiub" (this look, the default for every neon theme) or "tebal" (the older heavy glowing letters)


def font(size, weight=260):
    """Plus Jakarta Sans at a light weight: thin strokes like a glass tube"""
    f = ImageFont.truetype(os.path.join(HERE, "fonts", "PlusJakartaSans.ttf"), size)
    try: f.set_variation_by_axes([weight])
    except Exception: pass
    return f


def stroke_px(size):
    """how thick the tube should look at this text size (about 5% of the size, never under 3px)"""
    return max(3, int(round(size * 0.05)))


def mask(text, f, track=0.0):
    """an L mask of `text` in font `f`; `track` adds letter spacing as a fraction of the font size"""
    size = f.size; asc, desc = f.getmetrics(); gap = size * track
    w = int(sum(f.getlength(c) for c in text) + gap * max(0, len(text) - 1)) + 8; h = asc + desc + 8
    m = Image.new("L", (max(w, 1), h), 0); d = ImageDraw.Draw(m); x = 4
    for c in text: d.text((x, 4), c, font=f, fill=255); x += f.getlength(c) + gap
    return m


def even(m, size):
    """thicken a light-weight mask so every stroke reaches the tube width (light fonts are thinner than the reference)"""
    return m.filter(ImageFilter.MaxFilter(3)) if size < 70 else m   # small text: one pixel wider so the tube still reads


def light(m, color, size, pad=None):
    """light up an L mask as a neon tube in `color`. Returns (RGBA image, pad) where the mask sits at (pad, pad)."""
    pad = pad if pad is not None else int(size * 0.55) + 20
    full = Image.new("L", (m.width + pad * 2, m.height + pad * 2), 0); full.paste(m, (pad, pad))
    out = Image.new("RGBA", full.size, (0, 0, 0, 0))
    def glow(blur, gain):
        g = full.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * gain)))
        lay = Image.new("RGBA", full.size, color + (0,)); lay.putalpha(g); out.alpha_composite(lay)
    glow(size * 0.42, 0.55)   # wide faint spill onto the page
    glow(size * 0.16, 1.05)   # medium halo that fills the counters
    glow(max(2.0, size * 0.045), 2.2)   # tight bright halo hugging the stroke
    body = Image.new("RGBA", full.size, color + (0,)); body.putalpha(full); out.alpha_composite(body)   # saturated tube edge
    core_col = tuple(int(255 * 0.62 + c * 0.38) for c in color)   # pale, nearly white glass
    inner = full.filter(ImageFilter.MinFilter(3)) if stroke_px(size) >= 5 else full.point(lambda v: v * 0.8)
    core = Image.new("RGBA", full.size, core_col + (0,)); core.putalpha(inner); out.alpha_composite(core)
    return out, pad


def word(text, size, color, track=0.08, weight=260):
    """one line of neon tube text, ready to place"""
    f = font(size, weight); return light(even(mask(text, f, track), size), color, size)


def bloom(glow, size, gains=(0.55, 1.05, 2.2)):
    """the three neon halos around a coloured RGBA layer (several colours at once, e.g. key words vs plain words).
    Blurs premultiplied colour so transparent pixels don't pull the halo towards black. Returns a new RGBA image
    with the halos under the layer itself."""
    import cv2, numpy as np
    a = np.asarray(glow).astype(np.float32) / 255.0; al = a[..., 3:4]; pre = np.dstack([a[..., :3] * al, al])
    out = np.zeros_like(pre)
    for sig, g in zip((size * 0.42, size * 0.16, max(2.0, size * 0.045)), gains):
        b = cv2.GaussianBlur(pre, (0, 0), sig); A = b[..., 3:4]; C = b[..., :3] / np.maximum(A, 1e-4)
        A = np.clip(A * g, 0, 1); lay = np.dstack([C * A, A])              # premultiplied halo
        out = lay + out * (1 - lay[..., 3:4])                               # halo over what is already there
    out = pre + out * (1 - pre[..., 3:4])                                   # the coloured letters on top
    A = out[..., 3:4]; rgb = out[..., :3] / np.maximum(A, 1e-4)
    return Image.fromarray(np.clip(np.dstack([rgb, A]) * 255, 0, 255).astype(np.uint8), "RGBA")
