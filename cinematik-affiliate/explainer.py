"""Cinematik Explainer: a no-face motion-graphics reel on a voiceover.

Peach paper with a faint grid, an italic serif setup line over a heavy sans headline that ends in an
orange full stop, tilted photo cards, clay icons, and dark scenes for the low point of the story.

    python explainer.py projects/<name>                 -> out/final.mp4 (voice.py + SFX first, see run.sh)
    python explainer.py projects/<name> --limit 8       -> out/preview.mp4

project.json: {"type": "explainer", "source": "input/vo.mp4", "segments": [], "subs": [],
               "scenes": [{"start": 0.0, "in": "cut"|"whip", "dark": false, "items": [...]}, ...]}
Item kinds (times in seconds of the voiceover): setup, kicker, head, card, tile, count, timer, race,
blocks, stairs, ticks, calendar, cta, floaters. See projects/matematik-explainer for every kind in use.
"""
import argparse, json, math, os, subprocess, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import project
from render import anim, blend, probe

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
INK, ACC, CREAM = (18, 15, 11), (226, 121, 80), (244, 236, 226)
PEACH_TOP, PEACH_BOT, DARK = (250, 209, 167), (246, 236, 226), (15, 15, 11)
cache = {}

def font(kind, size):
    key = ("font", kind, size)
    if key not in cache:
        if kind == "serif":
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "InstrumentSerif-Italic.ttf"), size)
        elif kind == "kick":
            f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", size)
        else:   # heavy / bold: Plus Jakarta Sans variable
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "PlusJakartaSans.ttf"), size)
            f.set_variation_by_name("ExtraBold" if kind == "heavy" else "Bold")
        cache[key] = f
    return cache[key]

def clamp(x): return min(max(x, 0.0), 1.0)
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x, s=1.7):
    x = clamp(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def ramp(t, t0, dur): return clamp((t - t0) / dur)

# ---------- backgrounds ----------
def background(dark):
    key = ("bg", dark)
    if key in cache: return cache[key]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    if dark:
        bg = np.empty((H, W, 3), np.float32); bg[:] = DARK
        line, step, alpha = np.array(CREAM, np.float32), 108, 0.035
    else:
        top, bot = np.array(PEACH_TOP, np.float32), np.array(PEACH_BOT, np.float32)
        bg = np.broadcast_to(top + (bot - top) * yy ** 0.9, (H, W, 3)).copy()
        line, step, alpha = np.array((255, 255, 255), np.float32), 108, 0.32
    grid = np.zeros((H, W), np.float32)
    grid[::step, :] = 1; grid[:, ::step] = 1
    grid = cv2.GaussianBlur(grid, (0, 0), 0.8) * alpha * np.clip(1.2 - yy[..., 0] * 0.9, 0.25, 1)
    bg = bg * (1 - grid[..., None]) + line * grid[..., None]
    xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    vig = 1 - (0.28 if dark else 0.08) * np.clip(xx ** 2 + ((yy[..., 0] - 0.5) * 2) ** 2 - 0.4, 0, 1)
    cache[key] = (bg * vig[..., None]).astype(np.float32)
    return cache[key]

def floaters(frame, t, it):
    """slow drifting, blurred maths symbols behind a dark scene"""
    rng = np.random.default_rng(3); glyphs = it.get("glyphs", list("+−×÷="))
    for i in range(it.get("n", 16)):
        g = glyphs[i % len(glyphs)]; size = int(rng.uniform(90, 220) / max(1, len(g) / 2.5))
        key = ("float", g, size)
        if key not in cache:
            img = text_img(g, font("heavy", size), CREAM)
            cache[key] = img.filter(ImageFilter.GaussianBlur(size / 30))
        img = cache[key]
        x = rng.uniform(60, W - 60) + 20 * math.sin(t * 0.3 + i)
        y = (rng.uniform(0, H) - t * rng.uniform(8, 20)) % (H + 300) - 150
        a = rng.uniform(0.05, 0.13)
        al = img.getchannel("A").point(lambda v, a=a: int(v * a)); im = img.copy(); im.putalpha(al)
        blend(frame, im, x, y)

# ---------- text ----------
def text_img(txt, fnt, fill, track=0):
    key = ("txt", txt, id(fnt), fill, track)
    if key in cache: return cache[key]
    asc, desc = fnt.getmetrics(); pad = 10
    w = int(fnt.getlength(txt) + track * max(len(txt) - 1, 0)) + pad * 2
    img = Image.new("RGBA", (w, asc + desc + pad * 2), fill + (0,))
    d = ImageDraw.Draw(img)
    if track:
        x = pad
        for ch in txt: d.text((x, pad), ch, font=fnt, fill=fill + (255,)); x += fnt.getlength(ch) + track
    else:
        d.text((pad, pad), txt, font=fnt, fill=fill + (255,))
    cache[key] = img
    return img

def soft_shadow(img, alpha=110, blur=10, dy=6):
    """img over a soft drop shadow (not cached here: callers cache what they reuse)"""
    pad = blur * 3
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, alpha), (pad, pad + dy), img.getchannel("A"))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur))); out.alpha_composite(img, (pad, pad))
    return out

def setup(frame, t, it, sc):
    """italic serif line, word by word"""
    dark = sc.get("dark"); col = (236, 226, 212) if dark else (92, 74, 60)
    fnt = font("serif", it.get("size", 66)); words = it["text"].split(" ")
    widths = [fnt.getlength(w + " ") for w in words]; x = W / 2 - sum(widths) / 2 + fnt.getlength(" ") / 2
    out_a = 1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25)
    for i, w in enumerate(words):
        a = ease_out(ramp(t, it["at"] + 0.07 * i, 0.3)) * out_a
        if a > 0:
            img = anim(text_img(w, fnt, col), a, 1.0)
            blend(frame, img, x + fnt.getlength(w) / 2, it.get("y", 300) - 8 * (1 - a))
        x += widths[i]

def kicker(frame, t, it, sc):
    col = (236, 226, 212) if sc.get("dark") else (60, 48, 40)
    a = ease_out(ramp(t, it["at"], 0.35)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a > 0: blend(frame, anim(text_img(it["text"], font("kick", 34), col, track=12), a, 1.0), W / 2, it.get("y", 390))

def head_size(lines, maxw=950, size=150):
    while size > 70 and max(font("heavy", size).getlength(ln) for ln in lines) > maxw: size -= 4
    return size

def word_img(w, size, col, dark, shadow=True):
    """one headline word; a final '.' is always orange"""
    key = ("word", w, size, col, dark, shadow)
    if key in cache: return cache[key]
    fnt = font("heavy", size)
    body, dot = (w[:-1], ".") if w.endswith(".") else (w, "")
    img = text_img(body, fnt, col)
    if dot:
        d = text_img(dot, fnt, ACC); comb = Image.new("RGBA", (img.width + d.width - 20, img.height), (0, 0, 0, 0))
        comb.alpha_composite(img); comb.alpha_composite(d, (img.width - 20, 0)); img = comb
    if shadow: img = soft_shadow(img, 140 if dark else 60, 8, 5)
    cache[key] = img
    return img

def head(frame, t, it, sc):
    """heavy uppercase lines, centred; accent words orange, a final '.' always orange;
    optional highlight box behind one word, an orange offset shadow, and a scatter exit"""
    dark = sc.get("dark"); ink = CREAM if dark else INK
    lines = [ln for ln, _ in it["lines"]]; size = it.get("size") or head_size(lines)
    fnt = font("heavy", size); lh = size * 1.02; acc = set(it.get("accent", []))
    until, scat = it.get("until", 1e9), it.get("scatter_at")
    rng = np.random.default_rng(len(lines) * 7 + int(it["lines"][0][1] * 10))
    for li, (line, at) in enumerate(it["lines"]):
        a = ease_out(ramp(t, at, 0.32)) * (1 - ramp(t, until - 0.22, 0.22))
        if a <= 0: continue
        words = line.split(" "); sp = fnt.getlength(" ")
        widths = [fnt.getlength(w) for w in words]; x = W / 2 - (sum(widths) + sp * (len(words) - 1)) / 2
        y = it.get("y", 520) + li * lh + 26 * (1 - ease_back(ramp(t, at, 0.45)))
        for wi, w in enumerate(words):
            body = w[:-1] if w.endswith(".") else w
            col = ACC if w in acc else ink
            img = word_img(w, size, col, dark, shadow=not it.get("offset_shadow"))
            cx, cy, rot, wa = x + widths[wi] / 2, y, 0.0, a
            if scat is not None and t > scat:     # fly apart with a spin
                p = ease_out(ramp(t, scat, 0.55)); ang = rng.uniform(0, 2 * math.pi)
                cx += math.cos(ang) * 420 * p; cy += math.sin(ang) * 380 * p; rot = rng.uniform(-40, 40) * p
                wa = a * (1 - p)
            if w == it.get("box") or body == it.get("box"):
                bp = ease_out(ramp(t, at + 0.15, 0.3)); bw = int((widths[wi] + 28) * bp)
                if bw > 2:
                    box = Image.new("RGBA", (bw, int(size * 0.86)), ACC + (int(255 * wa),))
                    bx0 = cx - widths[wi] / 2 - 14
                    blend(frame, box, bx0 + bw / 2, cy + size * 0.04)
            if it.get("offset_shadow"):
                sh = text_img(w, fnt, ACC); blend(frame, anim(sh, wa * 0.9, 1.0), cx + 7, cy + 7)
            im = anim(img, wa, 1.05)
            if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
            blend(frame, im, cx, cy)
            x += widths[wi] + sp

# ---------- cards and icons ----------
def card_img(name, w, rot, prj):
    key = ("card", name, w, rot)
    if key in cache: return cache[key]
    src = Image.open(os.path.join(prj, "input", name)).convert("RGB")   # product photos stay out of the repo
    h = int(src.height * w / src.width); b = 12; r = 26
    face = Image.new("RGBA", (w + b * 2, h + b * 2), (255, 255, 255, 255))
    face.paste(src.resize((w, h), Image.LANCZOS), (b, b))
    m = Image.new("L", (face.width * 3, face.height * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=r * 3, fill=255)
    face.putalpha(m.resize(face.size, Image.LANCZOS))
    img = soft_shadow(face, 95, 22, 16).rotate(rot, Image.BICUBIC, expand=True)
    cache[key] = img
    return img

def card(frame, t, it, sc, prj):
    p = ramp(t, it["at"], 0.5)
    if p <= 0: return
    out = ramp(t, it.get("until", 1e9) - 0.3, 0.3)
    img = card_img(it["img"], it.get("w", 420), it.get("rot", 0), prj)
    s = 0.55 + 0.45 * ease_back(p); a = ease_out(p * 1.8) * (1 - out)
    dy = (1 - ease_out(p)) * (260 if it.get("from") == "bottom" else 40) + out * 120
    if a <= 0: return
    if abs(s - 1) > 1e-3: img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
    if a < 0.999:
        img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    blend(frame, img, it["x"], it["y"] + dy)

def clay(glyph, size):
    """terracotta clay tile with a white glyph"""
    key = ("clay", glyph, size)
    if key in cache: return cache[key]
    s = 3; n = size * s
    yy = np.linspace(0, 1, n)[:, None]
    top, bot = np.array((244, 146, 104)), np.array((196, 88, 52))
    grad = (top + (bot - top) * yy[..., None] ** 1.2) * np.ones((1, n, 1))
    face = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
    m = Image.new("L", (n, n), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, n - 1, n - 1), radius=int(n * 0.26), fill=255)
    face.putalpha(m)
    hl = Image.new("L", (n, n), 0); ImageDraw.Draw(hl).ellipse((n * 0.12, n * 0.05, n * 0.88, n * 0.42), fill=70)
    face.alpha_composite(Image.merge("RGBA", (Image.new("L", (n, n), 255),) * 3 + (Image.composite(hl.filter(ImageFilter.GaussianBlur(n / 18)), Image.new("L", (n, n), 0), m),)))
    g = font("heavy", int(size * (0.62 if len(glyph) == 1 else 0.4)) * s); gw = g.getlength(glyph); asc, desc = g.getmetrics()
    gl = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(gl)
    d.text(((n - gw) / 2, (n - asc - desc) / 2 + n * 0.02 + 6 * s), glyph, font=g, fill=(120, 44, 20, 120))
    gl = gl.filter(ImageFilter.GaussianBlur(4 * s))
    ImageDraw.Draw(gl).text(((n - gw) / 2, (n - asc - desc) / 2 + n * 0.02), glyph, font=g, fill=(255, 250, 244, 255))
    face.alpha_composite(gl)
    img = soft_shadow(face.resize((size, size), Image.LANCZOS), 90, 14, 12)
    cache[key] = img
    return img

def tile(frame, t, it, sc):
    p = ramp(t, it["at"], 0.45)
    if p <= 0: return
    out = ramp(t, it.get("until", 1e9) - 0.25, 0.25); a = ease_out(p * 2) * (1 - out)
    s = 0.3 + 0.7 * ease_back(p, 2.4); img = clay(it["glyph"], it.get("size", 170))
    bob = 6 * math.sin((t - it["at"]) * 2.2 + it["x"] / 100)
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
    if a < 0.999: img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    blend(frame, img, it["x"], it["y"] + bob)
    if it.get("label"):
        la = ease_out(ramp(t, it["at"] + 0.25, 0.3)) * (1 - out)
        col = (236, 226, 212) if sc.get("dark") else (92, 74, 60)
        if la > 0: blend(frame, anim(text_img(it["label"], font("serif", 44), col), la, 1.0), it["x"], it["y"] + it.get("size", 170) * 0.5 + 50)

def chip_img(txt):
    key = ("chip", txt)
    if key in cache: return cache[key]
    f = font("heavy", 78); tw = int(f.getlength(txt)); asc, desc = f.getmetrics(); w, h = tw + 72, asc + desc + 38; s = 3
    m = Image.new("L", (w * s, h * s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=22 * s, fill=255)
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0)); img.putalpha(m.resize((w, h), Image.LANCZOS))
    ImageDraw.Draw(img).text((36, 17), txt, font=f, fill=INK + (255,))
    cache[key] = soft_shadow(img, 90, 12, 10)
    return cache[key]

def pile(frame, t, it, sc):
    """formula chips rain down into a messy heap; scatter_at blows them away"""
    rng = np.random.default_rng(it.get("seed", 5)); x0, y0, x1, y1 = it["box"]
    scat, until = it.get("scatter_at"), it.get("until", 1e9)
    for i, txt in enumerate(it["chips"]):
        tx, ty, rot0, ang = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(-28, 28), rng.uniform(0, 2 * math.pi)
        at = it["at"] + i * it.get("step", 0.16); p = ramp(t, at, 0.5)
        if p <= 0: continue
        x, y = tx, ty - (1 - ease_back(p, 1.3)) * 1100
        rot = rot0 * ease_out(p); a = ease_out(p * 3) * (1 - ramp(t, until - 0.25, 0.25))
        if scat is not None and t > scat:
            q = ease_out(ramp(t, scat + 0.03 * i, 0.6))
            x += math.cos(ang) * 800 * q; y += math.sin(ang) * 800 * q; rot += 90 * q * (1 if i % 2 else -1); a *= 1 - q
        if a <= 0: continue
        im = chip_img(txt).rotate(rot, Image.BICUBIC, expand=True)
        if a < 0.999: im.putalpha(im.getchannel("A").point(lambda v, a=a: int(v * a)))
        blend(frame, im, x, y)

# ---------- data visuals ----------
def underline(frame, t, at, cx, y, w=220):
    bw = int(w * ease_out(ramp(t, at, 0.45)))
    if bw > 3: blend(frame, Image.new("RGBA", (bw, 8), ACC + (255,)), cx - w / 2 + bw / 2, y)

def count(frame, t, it, sc):
    a = ease_out(ramp(t, it["at"], 0.3)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    v = round(it["to"] * ease_out(ramp(t, it["at"] + 0.1, it.get("dur", 1.4))))
    ink = CREAM if sc.get("dark") else INK
    blend(frame, anim(soft_shadow(text_img(f"{v}", font("heavy", it.get("size", 300)), ink), 60, 10, 6), a, 1.0), W / 2, it["y"])
    la = ease_out(ramp(t, it.get("label_at", it["at"] + 0.6), 0.35)) * a
    if la > 0 and it.get("label"):
        blend(frame, anim(text_img(it["label"], font("serif", 70), (92, 74, 60)), la, 1.0), W / 2, it["y"] + it.get("size", 300) * 0.62)
    underline(frame, t, it["at"] + 0.4, W / 2, it["y"] + it.get("size", 300) * 0.62 + 64)

def timer(frame, t, it, sc):
    a = ease_out(ramp(t, it["at"], 0.35)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    p = ease_out(ramp(t, it["at"] + 0.15, it.get("dur", 1.3))); R, s = 250, 2
    n = (R * 2 + 60) * s; img = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    box = (30 * s, 30 * s, n - 30 * s, n - 30 * s)
    d.ellipse(box, outline=(255, 255, 255, 200), width=26 * s)
    if p > 0.005: d.arc(box, -90, -90 + 360 * p, fill=ACC + (255,), width=26 * s)
    img = img.resize((n // s, n // s), Image.LANCZOS)
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    blend(frame, soft_shadow(img, 50, 14, 8), W / 2, it["y"])
    num = text_img(f"{round(it['to'] * p)}", font("heavy", 230), INK)
    blend(frame, anim(num, a, 1.0), W / 2, it["y"] - 18)
    blend(frame, anim(text_img("minit", font("serif", 64), (92, 74, 60)), a, 1.0), W / 2, it["y"] + 120)

def race(frame, t, it, sc):
    """two bars: the class moves on, the child lags"""
    a = ease_out(ramp(t, it["at"], 0.3)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    full = 760; x0 = W / 2 - full / 2
    for i, (label, frac, col, delay) in enumerate((("Kelas", 0.92, INK, 0.0), ("Anak", 0.38, ACC, 0.25))):
        y = it["y"] + i * 150
        lab = text_img(label, font("bold", 44), (60, 48, 40))
        blend(frame, anim(lab, a, 1.0), x0 + lab.width / 2 - 10, y - 52)
        track = Image.new("RGBA", (full, 34), (255, 255, 255, int(150 * a))); blend(frame, track, W / 2, y)
        bw = int(full * frac * ease_out(ramp(t, it["at"] + 0.2 + delay, 1.6)))
        if bw > 6:
            bar = Image.new("RGBA", (bw, 34), col + (0,)); m = Image.new("L", (bw, 34), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, bw - 1, 33), radius=17, fill=int(255 * a)); bar.putalpha(m)
            blend(frame, bar, x0 + bw / 2, y)

def block_img(text, w, fill, fg):
    key = ("block", text, w, fill)
    if key in cache: return cache[key]
    h = 128; s = 3
    m = Image.new("L", (w * s, h * s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=28 * s, fill=255)
    img = Image.new("RGBA", (w, h), fill + (0,)); img.putalpha(m.resize((w, h), Image.LANCZOS))
    f = font("heavy", 54); tw = f.getlength(text); asc, desc = f.getmetrics()
    ImageDraw.Draw(img).text(((w - tw) / 2, (h - asc - desc) / 2), text, font=f, fill=fg + (255,))
    cache[key] = soft_shadow(img, 80, 12, 10)
    return cache[key]

def blocks(frame, t, it, sc):
    """a tower of topics built on the base block; it wobbles, then the top falls off"""
    base_y, gap = it["y"], 140
    wob, fall = it.get("wobble_at"), it.get("fall_at")
    th = 0.0
    if wob is not None and t > wob:
        k = t - wob; th = 5.0 * math.sin(2 * math.pi * 2.2 * k) * math.exp(-0.15 * k) + (0 if fall is None else 9 * ease_out(ramp(t, fall, 1.0)))
    rng = np.random.default_rng(11)
    for i, (text, at) in enumerate(it["items"]):
        p = ramp(t, at, 0.5)
        if p <= 0: continue
        w = 660 - i * 70
        fill, fg = (ACC, (255, 255, 255)) if i == 0 else (INK, CREAM)
        img = block_img(text, w, fill, fg)
        h_i = i * gap; drop = (1 - ease_back(p, 1.2)) * 500
        r = math.radians(th) * (1 if i else 0.25)
        cx = W / 2 + h_i * math.sin(r); cy = base_y - h_i * math.cos(r) - drop
        rot = th * (1 if i else 0.25); a = ease_out(p * 2)
        if fall is not None and t > fall and i > 0:
            q = ramp(t, fall + 0.12 * i, 1.1); dirn = 1 if rng.uniform() > 0.4 else -1
            cx += dirn * 380 * q * q; cy += 900 * q * q; rot += dirn * 70 * q; a *= 1 - q
        if a <= 0: continue
        im = img.rotate(-rot, Image.BICUBIC, expand=True) if abs(rot) > 0.05 else img
        if a < 0.999: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a=a: int(v * a)))
        blend(frame, im, cx, cy)

def stairs(frame, t, it, sc):
    labels = it["labels"]; n = len(labels); sw, sh = 250, 130; x0 = W / 2 - n * sw / 2; base = it["y"]
    for i, (lab, at) in enumerate(labels):
        p = ease_back(ramp(t, at, 0.45), 1.3)
        if p <= 0: continue
        hgt = int(sh * (i + 1) * min(p, 1.05))
        if hgt < 2: continue
        blk = Image.new("RGBA", (sw - 14, hgt), (INK if i < n - 1 else ACC) + (255,))
        blend(frame, blk, x0 + i * sw + sw / 2, base - hgt / 2)
        if lab:
            blend(frame, anim(text_img(lab, font("serif", 58), (92, 74, 60)), ease_out(ramp(t, at + 0.2, 0.3)), 1.0),
                  x0 + i * sw + sw / 2, base + 56)     # under the step, clear of the hopping ball
    # a ball hops up the steps in time with them
    hops = [at for _, at in labels]
    k = sum(1 for h in hops if t >= h) - 1
    if k >= 0:
        q = ease_out(ramp(t, hops[k], 0.4))
        xa = x0 + max(k - 1, 0) * sw + sw / 2 if k else x0 - 40; ya = base - sh * k - 40 if k else base - 40
        xb = x0 + k * sw + sw / 2; yb = base - sh * (k + 1) - 40
        x = xa + (xb - xa) * q; y = ya + (yb - ya) * q - math.sin(math.pi * q) * 120
        ball = Image.new("RGBA", (64, 64), (0, 0, 0, 0)); ImageDraw.Draw(ball).ellipse((2, 2, 62, 62), fill=ACC + (255,))
        blend(frame, soft_shadow(ball, 80, 6, 6), x, y)

def check_img(size=70):
    key = ("check", size)
    if key in cache: return cache[key]
    s = 4; n = size * s; img = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, n - 1, n - 1), fill=ACC + (255,))
    d.line([(n * 0.27, n * 0.53), (n * 0.44, n * 0.69), (n * 0.74, n * 0.36)], fill=(255, 255, 255, 255), width=int(n * 0.11), joint="curve")
    cache[key] = soft_shadow(img.resize((size, size), Image.LANCZOS), 70, 5, 4)
    return cache[key]

def ticks(frame, t, it, sc, prj):
    card(frame, t, dict(it, img=it["img"]), sc, prj)
    cw = it.get("w", 860); ch = cw * 730 / 1110
    cells = [(c, r) for r in range(5) for c in range(5)]
    for k, (c, r) in enumerate(cells[: it.get("n", 10)]):
        at = it["tick_at"] + k * it.get("step", 0.12)
        p = ramp(t, at, 0.3)
        if p <= 0: continue
        img = check_img(); s = 0.4 + 0.6 * ease_back(p, 2.5)
        im = img.resize((max(1, int(img.width * s)),) * 2, Image.BICUBIC)
        x = it["x"] - cw / 2 + cw * (0.075 + c * 0.081); y = it["y"] - ch / 2 + ch * (0.23 + r * 0.149)
        blend(frame, im, x + 18, y + 14)

def calendar(frame, t, it, sc):
    days = ["Isn", "Sel", "Rab", "Kha", "Jum", "Sab", "Ahd"]; pw, gap = 128, 10
    x0 = W / 2 - (7 * pw + 6 * gap) / 2 + pw / 2
    a = ease_out(ramp(t, it["at"], 0.35)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    for i, dname in enumerate(days):
        x = x0 + i * (pw + gap); key = ("day", dname)
        if key not in cache:
            s = 3; img = Image.new("RGBA", (pw * s, 190 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
            d.rounded_rectangle((0, 0, pw * s - 1, 190 * s - 1), radius=26 * s, fill=(255, 255, 255, 235))
            f = font("bold", 34 * s); d.text(((pw * s - f.getlength(dname)) / 2, 22 * s), dname, font=f, fill=INK + (255,))
            f2 = font("serif", 30 * s); d.text(((pw * s - f2.getlength("15 min")) / 2, 140 * s), "15 min", font=f2, fill=(110, 90, 74, 255))
            cache[key] = soft_shadow(img.resize((pw, 190), Image.LANCZOS), 60, 10, 8)
        da = a * ease_out(ramp(t, it["at"] + 0.05 * i, 0.3))
        if da > 0: blend(frame, anim(cache[key], da, 1.0), x, it["y"])
        p = ramp(t, it["tick_at"] + i * it.get("step", 0.2), 0.3)
        if p > 0:
            c = check_img(62); s = 0.4 + 0.6 * ease_back(p, 2.5)
            blend(frame, c.resize((max(1, int(c.width * s)),) * 2, Image.BICUBIC), x, it["y"] + 8)

def cta(frame, t, it, sc):
    a = ease_out(ramp(t, it["at"], 0.35))
    if a <= 0: return
    key = ("cta", it["text"])
    if key not in cache:
        f = font("bold", 50); tw = int(f.getlength(it["text"])); w, h = tw + 110, 104; s = 3
        m = Image.new("L", (w * s, h * s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=h * s // 2, fill=255)
        img = Image.new("RGBA", (w, h), ACC + (0,)); img.putalpha(m.resize((w, h), Image.LANCZOS))
        asc, desc = f.getmetrics(); ImageDraw.Draw(img).text(((w - tw) / 2, (h - asc - desc) / 2 - 2), it["text"], font=f, fill=(255, 255, 255, 255))
        cache[key] = soft_shadow(img, 110, 16, 10)
    blend(frame, anim(cache[key], a, 0.85), W / 2, it["y"])
    s = 4; cw, chh = 60, 52; m = Image.new("L", (cw * s, chh * s), 0); d = ImageDraw.Draw(m)
    for oy in (6, 26): d.line([(10 * s, oy * s), (30 * s, (oy + 16) * s), (50 * s, oy * s)], fill=255, width=6 * s, joint="curve")
    chev = Image.new("RGBA", (cw, chh), ACC + (0,)); chev.putalpha(m.resize((cw, chh), Image.LANCZOS).point(lambda v: int(v * a)))
    blend(frame, chev, W / 2, it["y"] + 100 + 8 * math.sin(2 * math.pi * 1.4 * (t - it["at"])))

DRAW = {"setup": setup, "kicker": kicker, "head": head, "tile": tile, "count": count, "timer": timer,
        "race": race, "blocks": blocks, "stairs": stairs, "calendar": calendar, "cta": cta, "floaters": floaters, "pile": pile}

def draw_scene(sc, t, prj):
    frame = background(sc.get("dark", False)).copy()
    for it in sc["items"]:
        if it["kind"] in ("card", "ticks"): (card if it["kind"] == "card" else ticks)(frame, t, it, sc, prj)
        elif it["kind"] == "floaters": floaters(frame, t, it)
        else: DRAW[it["kind"]](frame, t, it, sc)
    return frame

def whip(a, b, p):
    """sideways motion-blur push from frame a to frame b, p 0 -> 1"""
    e = 0.5 - 0.5 * math.cos(math.pi * p); k = int(9 + 90 * math.sin(math.pi * p))
    sa = np.roll(a, -int(W * 0.35 * e), axis=1); sb = np.roll(b, int(W * 0.35 * (1 - e)), axis=1)
    mix = sa * (1 - e) + sb * e
    return cv2.blur(mix, (k, 1)) if k > 1 else mix

def frame_at(scenes, t, prj):
    i = max(j for j, s in enumerate(scenes) if s["start"] <= t or j == 0)
    sc = scenes[i]
    if i > 0 and sc.get("in", "whip") == "whip" and t < sc["start"] + 0.14:
        prev = scenes[i - 1]; p = (t - (sc["start"] - 0.14)) / 0.28
        return whip(draw_scene(prev, sc["start"] - 0.01, prj), draw_scene(sc, sc["start"], prj), p)
    if i + 1 < len(scenes) and scenes[i + 1].get("in", "whip") == "whip" and t > scenes[i + 1]["start"] - 0.14:
        nxt = scenes[i + 1]; p = (t - (nxt["start"] - 0.14)) / 0.28
        return whip(draw_scene(sc, nxt["start"] - 0.01, prj), draw_scene(nxt, nxt["start"], prj), p)
    return draw_scene(sc, t, prj)

# ---------- sound ----------
def sfx_track(cfg, dur, out):
    import sfx
    track = np.zeros((int(sfx.SR * (dur + 0.5)), 2), np.float32)
    ev = []
    for k, sc in enumerate(cfg["scenes"]):
        if k and sc.get("in", "whip") == "whip": ev.append((sc["start"] - 0.2, "whoosh", -15))
        if k and sc.get("in") == "cut": ev.append((sc["start"], "pop", -14))
        for it in sc["items"]:
            if it["kind"] == "head":
                for _, at in it["lines"]: ev.append((at - 0.18, "whoosh", -21))
                if it.get("scatter_at"): ev.append((it["scatter_at"] - 0.1, "whoosh", -17))
            elif it["kind"] in ("card", "tile"): ev.append((it["at"], "pop", -16))
            elif it["kind"] == "blocks":
                ev += [(at + 0.3, "pop", -14) for _, at in it["items"]]
            elif it["kind"] in ("ticks", "calendar"):
                n = it.get("n", 10) if it["kind"] == "ticks" else 7
                ev += [(it["tick_at"] + i * it.get("step", 0.12 if it["kind"] == "ticks" else 0.2), "tick", -18) for i in range(n)]
            elif it["kind"] == "stairs": ev += [(at + 0.1, "pop", -15) for _, at in it["labels"]]
            elif it["kind"] == "pile":
                ev += [(it["at"] + i * it.get("step", 0.16) + 0.35, "tick", -17) for i in range(len(it["chips"]))]
                if it.get("scatter_at"): ev.append((it["scatter_at"] - 0.1, "whoosh", -15))
            elif it["kind"] == "cta": ev.append((it["at"], "ding", -16))
            elif it["kind"] in ("count", "timer"):
                last = -1
                for ms in range(0, int(it.get("dur", 1.4) * 1000), 70):
                    tt = it["at"] + 0.1 + ms / 1000; v = round(it["to"] * ease_out(ms / 1000 / it.get("dur", 1.4)))
                    if v != last: ev.append((tt, "tick", -22)); last = v
    make = {"whoosh": sfx.whoosh, "pop": sfx.pop, "tick": sfx.tick, "ding": sfx.ding}
    for at, kind, level in ev:
        clip = make[kind](); i = int(max(at, 0) * sfx.SR); j = min(i + len(clip), len(track))
        track[i:j] += clip[: j - i] * sfx.db(level + cfg.get("sfx_gain_db", 0))
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sfx.SR)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())
    return len(ev)

TIME_KEYS = ("start", "at", "until", "scatter_at", "label_at", "tick_at", "wobble_at", "fall_at")

def remap(cfg, m):
    """voiceover times -> times in the sped-up voice (speed.py timemap); steps and durations shrink with the tempo"""
    from speed import to_output
    keep, tempo = m["keep"], m["tempo"]
    f = lambda t: round(to_output(t, keep, tempo), 3)   # noqa: E731
    cfg = json.loads(json.dumps(cfg))
    if "end" in cfg: cfg["end"] = f(cfg["end"])
    for sc in cfg["scenes"]:
        sc["start"] = f(sc["start"])
        for it in sc["items"]:
            for k in TIME_KEYS:
                if k in it: it[k] = f(it[k])
            for k in ("lines", "items", "labels"):
                if k in it: it[k] = [[x, f(t)] for x, t in it[k]]
            for k in ("dur", "step"):
                if k in it: it[k] = round(it[k] / tempo, 3)
    return cfg

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--limit", type=float); ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--out"); args = ap.parse_args()
    prj = args.project.rstrip("/"); cfg = project.read(prj)
    src = os.path.join(prj, cfg["source"])
    tm = os.path.join(prj, "build", "timemap.json")
    if cfg.get("speed") and os.path.exists(tm):   # speed.py shortened the pauses: every scene time follows the voice
        cfg = remap(cfg, json.load(open(tm))); src = os.path.join(prj, "build", "fast.mp4")
    dur = min(probe(src)[4], cfg.get("end", 1e9))   # "end" trims trailing silence
    scenes = sorted(cfg["scenes"], key=lambda s: s["start"])
    build = os.path.join(prj, "build"); os.makedirs(build, exist_ok=True)
    sfx_wav = os.path.join(build, "sfx.wav"); n_ev = sfx_track(cfg, dur, sfx_wav)
    voice = os.path.join(build, "voice.wav")
    vin = voice if os.path.exists(voice) else src
    out = args.out or os.path.join(prj, "out", "preview.mp4" if args.limit else "final.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t0, t1 = args.start, min(dur, args.start + args.limit) if args.limit else dur
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-ss", f"{t0}", "-i", vin, "-ss", f"{t0}", "-i", sfx_wav, "-filter_complex",
                            ("[1:a]aresample=48000[v]" if vin == voice else "[1:a]loudnorm=I=-14:TP=-1.5,aresample=48000[v]") +
                            ";[2:a]aresample=48000[s];[v][s]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = 0; total = int(round((t1 - t0) * FPS))
    while n < total:
        fr = frame_at(scenes, t0 + n / FPS, prj)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes()); n += 1
        if n % 150 == 0: print(f"{n}/{total} frames", flush=True)
    enc.stdin.close(); enc.wait()
    print(f"done: {n} frames, {n_ev} sfx -> {out}")

if __name__ == "__main__":
    main()
