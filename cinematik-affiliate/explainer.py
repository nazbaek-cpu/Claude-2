"""Animasi Edukasi Buku (preset "edukasi"): a no-face motion-graphics reel on a voiceover.

Peach paper with a faint grid, an italic serif setup line over a heavy sans headline that ends in an
orange full stop, tilted photo cards, clay icons, and dark scenes for the low point of the story.

    python explainer.py projects/<name>                 -> out/final.mp4 (voice.py + SFX first, see run.sh)
    python explainer.py projects/<name> --limit 8       -> out/preview.mp4

project.json: {"source": "input/vo.mp4", "preset": "edukasi",
               "scenes": [{"start": 0.0, "in": "cut"|"whip", "dark": false, "items": [...]}, ...]}
Item kinds (times in seconds of the original voiceover): setup, kicker, head, card, tile, count, timer, race,
blocks, stairs, ticks, calendar, cta, pile, floaters. Examples: projects/matematik-explainer, projects/timbunan-chip.
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
DARK_BOT = None                                # set by a theme: dark scenes become a top-to-bottom gradient
CAP_FILL, CAP_EDGE, HALO = INK, (255, 255, 255), (255, 255, 255)   # caption letters, thin outline, soft glow
CTA_TEXT = (255, 255, 255)
CAP_STROKE = 36                                # caption outline = size / CAP_STROKE
THEMES = {"navy": {"DARK": (20, 52, 132), "DARK_BOT": (4, 16, 52), "ACC": (255, 196, 56),   # deep royal blue, gold accent
                   "CAP_FILL": (255, 255, 255), "CAP_EDGE": (6, 20, 62), "HALO": (2, 10, 34), "CTA_TEXT": (6, 20, 62),
                   "CAP_STROKE": 14},   # white letters need a thicker edge on light footage
          # "animasi kartun" (styles/animasi-kartun.md): ruled cream paper, deep green + gold, flat props, a stick mascot
          "kartun": {"PEACH_TOP": (248, 242, 233), "PEACH_BOT": (246, 239, 228), "RULED": True, "INK": (30, 38, 34),
                     "ACC": (27, 106, 70), "TINT_PROPS": True},
          # light brown paper with a barely-there box grid: dark brown text, rust key words, colour props with a cream sticker edge
          "coklat": {"PEACH_TOP": (222, 198, 166), "PEACH_BOT": (222, 198, 166), "RULED": True, "GRID": 72, "RULE_LINE": (214, 189, 156),
                     "INK": (66, 42, 28), "ACC": (92, 58, 38), "CTA_TEXT": (255, 244, 224), "K_DARK": (66, 42, 28),
                     "K_GREEN": (142, 62, 24), "K_GOLD": (178, 58, 72), "K_TAPE": (255, 236, 172), "PROP_EDGE": (255, 248, 236)},
          # green self-healing cutting mat: white text, keyword boxes, every sticker torn out of a sheet
          # a sheet of paper on a wooden desk in window light (kartun colours on top)
          "meja": {"MEJA": True, "PEACH_TOP": (232, 229, 222), "INK": (40, 40, 40), "ACC": (27, 106, 70), "TINT_PROPS": True},
          "mat": {"MAT": True, "PEACH_TOP": (30, 102, 76), "INK": (250, 248, 240), "ACC": (246, 196, 60), "CTA_TEXT": (28, 30, 28),
                  "BADGE_BG": (246, 196, 60), "BADGE_FG": (28, 30, 28), "TORN": True, "PROP_EDGE": (255, 255, 252)}}
RULED, GRID, TINT_PROPS, RULE_LINE, PROP_EDGE = False, 0, False, (233, 225, 212), None
MAT, MEJA, TORN, BADGE_BG, BADGE_FG = False, False, False, None, (255, 255, 255)
BG_IMAGE = None                                # "bg_image" in project.json: a picture behind every light scene
K_DARK, K_GREEN, K_GOLD, K_TAPE = (16, 56, 46), (27, 106, 70), (175, 121, 33), (233, 201, 128)   # "kartun" palette
cache = {}

def set_theme(name):
    """"theme": "navy" in project.json: dark scenes on a deep blue gradient, gold accents, white captions"""
    if name: globals().update(THEMES[name])

def font(kind, size):
    key = ("font", kind, size)
    if key not in cache:
        if kind == "serif":
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "InstrumentSerif-Italic.ttf"), size)
        elif kind == "script":   # Damion: thick casual handwriting
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "Damion-Regular.ttf"), size)
        elif kind == "archivo":   # Archivo Black: heavy poster capitals for an opening title
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "ArchivoBlack-Regular.ttf"), size)
        elif kind == "kick":
            f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", size)
        else:   # heavy / bold: Plus Jakarta Sans variable
            f = ImageFont.truetype(os.path.join(HERE, "fonts", "PlusJakartaSans.ttf"), size)
            f.set_variation_by_name("ExtraBold" if kind == "heavy" else "Bold")
        cache[key] = f
    return cache[key]

def face(sc, kind):
    """"bold_text": thin faces (italic serif, tracked kicker) become Plus Jakarta Sans Bold"""
    return "bold" if sc.get("bold") and kind in ("serif", "kick") else kind

def soft_ink(sc): return (236, 226, 212) if sc.get("dark") else (60, 48, 40) if sc.get("bold") else (92, 74, 60)

def clamp(x): return min(max(x, 0.0), 1.0)
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x, s=1.7):
    x = clamp(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def ramp(t, t0, dur): return clamp((t - t0) / dur)

# ---------- backgrounds ----------
def background(dark):
    key = ("bg", dark, RULED, GRID, MAT, MEJA, PEACH_TOP, DARK, RULE_LINE, BG_IMAGE)   # the theme is part of the key: tests switch themes in one process
    if key in cache: return cache[key]
    if BG_IMAGE and not dark:   # the user's own background: cover-fit to 9:16
        im = Image.open(BG_IMAGE).convert("RGB"); s = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        cache[key] = np.asarray(im.crop((x0, y0, x0 + W, y0 + H))).astype(np.float32)
        return cache[key]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    if MAT and not dark:
        cache[key] = cutting_mat()
        return cache[key]
    if MEJA and not dark:
        cache[key] = desk_paper()
        return cache[key]
    if dark:
        top = np.array(DARK, np.float32); bot = np.array(DARK_BOT or DARK, np.float32)
        bg = np.broadcast_to(top + (bot - top) * yy ** 1.1, (H, W, 3)).copy()
        line, step, alpha = np.array(CREAM, np.float32), 108, 0.035 if DARK_BOT is None else 0.06
    elif RULED:   # notebook paper: flat cream, faint ruled lines, no grid or vignette
        bg = np.empty((H, W, 3), np.float32); bg[:] = PEACH_TOP
        if GRID:   # faint box grid over the whole page
            for v in range(GRID // 2, max(W, H), GRID): bg[v:v + 2] = RULE_LINE; bg[:, v:v + 2] = RULE_LINE
        else:
            for y in range(290, H - 120, 74): bg[y:y + 2] = RULE_LINE
        cache[key] = bg
        return bg
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
    dark = sc.get("dark"); col = (236, 226, 212) if dark else soft_ink(sc)
    kind = sc.get("setup_face") or face(sc, "serif")
    fnt = font(kind, it.get("size", 76 if kind == "script" else 66 if not sc.get("bold") else 56)); words = it["text"].split(" ")
    widths = [fnt.getlength(w + " ") for w in words]; x = W / 2 - sum(widths) / 2 + fnt.getlength(" ") / 2
    out_a = 1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25)
    for i, w in enumerate(words):
        a = ease_out(ramp(t, it["at"] + 0.07 * i, 0.3)) * out_a
        if a > 0:
            img = anim(text_img(w, fnt, col), a, 1.0)
            blend(frame, img, x + fnt.getlength(w) / 2, it.get("y", 300) - 8 * (1 - a))
        x += widths[i]

def script_line(text, size, fill, edge, width, kind="script"):
    """one title line ("script" handwriting or "archivo" capitals) with a thin outline and a soft drop shadow"""
    key = ("scriptline", text, size, fill, edge, width, kind)
    if key in cache: return cache[key]
    f = font(kind, size); pad = width + 24; asc, desc = f.getmetrics()
    img = Image.new("RGBA", (int(f.getlength(text)) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=fill + (255,), stroke_width=width, stroke_fill=edge + (255,))
    cache[key] = soft_shadow(img, 150, 10, 6)
    return cache[key]

def script_title(frame, t, it, sc):
    """big title over a picture (e.g. the opening AI clip): each line pops in on its time.
    "face": "script" (Damion, default) or "archivo" (Archivo Black); "colors" gives each line its own fill"""
    fill, edge = tuple(it.get("color", (255, 214, 92))), tuple(it.get("outline_color", (58, 30, 12)))
    kind = it.get("face", "script"); colors = it.get("colors")
    size = it.get("size", 150); sizes = it.get("sizes", [size] * len(it["lines"]))
    ys = [it.get("y", 330)]   # line centres: each line sits under the previous one, by both their sizes
    for i in range(1, len(sizes)): ys.append(ys[-1] + (sizes[i - 1] + sizes[i]) / 2 * it.get("leading", 0.95))
    out = 1 - ramp(t, it.get("until", 1e9) - 0.3, 0.3)
    for i, (text, at) in enumerate(it["lines"]):
        p = ramp(t, at, 0.45); a = ease_out(p * 2) * out
        if a <= 0: continue
        col = tuple(colors[i]) if colors else fill
        img = script_line(text, sizes[i], col, edge, it.get("outline", 3), kind)
        s = 0.8 + 0.2 * ease_back(p, 2.2)
        if abs(s - 1) > 1e-3: img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
        blend(frame, anim(img, a, 1.0), W / 2, ys[i] + 30 * (1 - ease_out(p)))

def kicker(frame, t, it, sc):
    col = (236, 226, 212) if sc.get("dark") else (60, 48, 40)
    a = ease_out(ramp(t, it["at"], 0.35)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    big = sc.get("bold")
    if a > 0: blend(frame, anim(text_img(it["text"], font(face(sc, "kick"), 42 if big else 34), col, track=6 if big else 12), a, 1.0), W / 2, it.get("y", 390))

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

FLUENT = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"   # Microsoft Fluent Emoji, MIT licence

def emoji_png(name, prj):
    """the 3D Fluent emoji "name" (e.g. "Exploding head"), fetched once into build/emoji/"""
    slug = name.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(prj, "build", "emoji", slug + ".png")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        folder = FLUENT + name.replace(" ", "%20")
        for url in (f"{folder}/3D/{slug}_3d.png", f"{folder}/Default/3D/{slug}_3d_default.png"):   # skin-tone emoji live under Default/
            if subprocess.run(["curl", "-fsSL", "-o", path, url]).returncode == 0: break
        else: raise FileNotFoundError(f"no 3D Fluent emoji called {name!r}")
    return path

def emoji_img(name, size, prj):
    """big 3D emoji with a soft light behind it and a contact shadow"""
    key = ("emoji", name, size)
    if key in cache: return cache[key]
    e = Image.open(emoji_png(name, prj)).convert("RGBA").resize((size, size), Image.LANCZOS)
    pad = size // 2; out = Image.new("RGBA", (size + pad * 2,) * 2, (255, 255, 255, 0))
    m = Image.new("L", out.size, 0); ImageDraw.Draw(m).ellipse((pad * 0.6, pad * 0.6, out.width - pad * 0.6, out.height - pad * 0.6), fill=120)
    halo = Image.new("RGBA", out.size, (255, 255, 255, 0)); halo.putalpha(m.filter(ImageFilter.GaussianBlur(size / 7))); out.alpha_composite(halo)
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh.paste((60, 30, 10, 100), (pad, pad + size // 14), e.getchannel("A"))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size / 25))); out.alpha_composite(e, (pad, pad))
    cache[key] = out
    return out

def emoji(frame, t, it, sc, prj):
    """3D emoji that pops in with a bounce, then floats; "wobble" (degrees) rocks it, e.g. a ringing alarm clock"""
    p = ramp(t, it["at"], 0.45)
    if p <= 0: return
    a = ease_out(p * 2) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    img = emoji_img(it["name"], it.get("size", 360), prj)
    s = 0.3 + 0.7 * ease_back(p, 2.2); k = t - it["at"]
    rot = it.get("wobble", 0) * math.sin(2 * math.pi * 2.0 * k) * math.exp(-0.4 * k) + it.get("rot", 0)
    im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
    if abs(rot) > 0.2: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if a < 0.999: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    blend(frame, im, it.get("x", W / 2), it.get("y", 900) + 10 * math.sin(k * 2.4 + it.get("x", 540) / 90))

# ---------- "animasi kartun" pieces ----------
def fade_in_out(t, it, tin=0.3):
    return ease_out(ramp(t, it["at"], tin)) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))

def badge(frame, t, it, sc):
    """series pill (e.g. FAHAM DUIT): dark green, white bold caps"""
    a = fade_in_out(t, it)
    if a <= 0: return
    key = ("badge", it["text"])
    if key not in cache:
        f = font("heavy", it.get("size", 34)); tw = int(f.getlength(it["text"])); asc, desc = f.getmetrics(); w, h = tw + 64, asc + desc + 26; s = 3
        m = Image.new("L", (w * s, h * s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=h * s // 2, fill=255)
        img = Image.new("RGBA", (w, h), (BADGE_BG or K_DARK) + (0,)); img.putalpha(m.resize((w, h), Image.LANCZOS))
        ImageDraw.Draw(img).text((32, 12), it["text"], font=f, fill=BADGE_FG + (255,))
        cache[key] = img
    blend(frame, anim(cache[key], a, 1.0), W / 2, it.get("y", 200))

def say(frame, t, it, sc):
    """the line being spoken as a two-line title: plain words in ink, then the key words big in green or gold"""
    a = fade_in_out(t, it, 0.22)
    if a <= 0: return
    y = it.get("y", 360) + 18 * (1 - ease_out(ramp(t, it["at"], 0.3)))
    col = K_GOLD if it.get("color") == "gold" else K_GREEN
    for txt, kind, size, fill in ((it.get("text"), "bold", it.get("size1", 74), INK), (it.get("key"), "heavy", it.get("size2", 112), col)):
        if not txt: continue
        while size > 40 and font(kind, size).getlength(txt) > 1000: size -= 4
        img = text_img(txt, font(kind, size), fill)
        blend(frame, anim(img, a, 1.0), W / 2, y + img.height / 2); y += img.height * 0.9

def tape(frame, t, it, sc):
    """yellow masking-tape label, slightly tilted"""
    p = ramp(t, it["at"], 0.35); a = ease_out(p * 2) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    key = ("tape", it["text"], it.get("rot", -2))
    if key not in cache:
        f = font("heavy", it.get("size", 40)); tw = int(f.getlength(it["text"])); asc, desc = f.getmetrics(); w, h = tw + 76, asc + desc + 34
        img = Image.new("RGBA", (w, h), K_TAPE + (255,)); d = ImageDraw.Draw(img)
        d.rectangle((w // 2 - 50, 0, w // 2 + 50, 8), fill=(255, 255, 255, 110))   # a strip of tape on top
        d.text((38, 16), it["text"], font=f, fill=K_DARK + (255,))
        cache[key] = soft_shadow(img, 60, 6, 5).rotate(it.get("rot", -2), Image.BICUBIC, expand=True)
    img = cache[key]; s = 0.6 + 0.4 * ease_back(p, 2.0)
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
    blend(frame, anim(img, a, 1.0), it.get("x", W / 2), it.get("y", 700))

def mascot_img(pose, k, face, sz=1.0):
    """the stick mascot (round head, deep green body, gold tie) drawn at 2x; k is seconds since it appeared"""
    S = 2; w, h = 600 * S, 760 * S; img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    P = lambda x, y: (x * S, y * S)   # noqa: E731
    lw = 9 * S; cx = 230
    d.ellipse((*P(cx - 90, 728), *P(cx + 90, 748)), fill=(0, 0, 0, 28))                       # floor shadow
    for x0, x1 in ((cx - 22, cx - 42), (cx + 22, cx + 42)): d.line((*P(x0, 560), *P(x1, 735)), fill=K_DARK, width=lw)
    d.rounded_rectangle((*P(cx - 62, 360), *P(cx + 62, 580)), radius=62 * S, fill=K_DARK)                 # body
    d.polygon([P(cx - 13, 368), P(cx + 13, 368), P(cx, 445)], fill=K_GOLD)                                # tie
    def arm(sx, sy, ex, ey):
        d.line((*P(sx, sy), *P(ex, ey)), fill=K_DARK, width=lw)
        d.ellipse((*P(ex - 15, ey - 15), *P(ex + 15, ey + 15)), fill=(255, 255, 255), outline=K_DARK, width=6 * S)
    arm(cx - 58, 395, cx - 115, 560)
    if pose == "wave":
        ang = math.radians(-60 + 18 * math.sin(2 * math.pi * 1.6 * k)); L = 150
        arm(cx + 58, 395, cx + 58 + L * math.cos(ang), 395 + L * math.sin(ang))
    elif pose == "think": arm(cx + 58, 395, cx + 40, 300)
    elif pose == "down": arm(cx + 58, 395, cx + 115, 560)
    else: arm(cx + 58, 395, cx + 210, 360 + 6 * math.sin(2 * math.pi * 0.8 * k))                         # point to the right
    d.ellipse((*P(cx - 88, 175), *P(cx + 88, 351)), fill=(255, 255, 255), outline=K_DARK, width=lw)      # head
    if face == "wow":
        for ex in (cx - 30, cx + 30): d.ellipse((*P(ex - 11, 240), *P(ex + 11, 262)), fill=K_DARK)
        d.ellipse((*P(cx - 14, 290), *P(cx + 14, 318)), fill=K_DARK)
    else:   # calm: closed eyes, small smile
        for ex in (cx - 32, cx + 32): d.arc((*P(ex - 16, 238), *P(ex + 16, 262)), 200, 340, fill=K_DARK, width=6 * S)
        d.arc((*P(cx - 30, 270), *P(cx + 30, 312)), 20, 160, fill=K_DARK, width=6 * S)
    return img.resize((int(w * sz / S), int(h * sz / S)), Image.LANCZOS)

def mascot(frame, t, it, sc):
    """stick mascot standing on the left ("x" body centre, "y" feet, "scale"): "pose" point | wave | think | down, "face" calm | wow;
    "poses": [[pose, face, at], ...] switches pose in place along the VO"""
    a = fade_in_out(t, it, 0.35)
    if a <= 0: return
    pose, face_ = it.get("pose", "point"), it.get("face", "calm")
    for ps, fc, at in it.get("poses", []):
        if t >= at: pose, face_ = ps, fc
    k = t - it["at"]; sz = it.get("scale", 1.3); img = mascot_img(pose, k, face_, sz)
    x = it.get("x", 230) - 60 * (1 - ease_out(ramp(t, it["at"], 0.4))); y = it.get("y", 1640) - 355 * sz + 4 * math.sin(k * 2.0)
    blend(frame, anim(img, a, 1.0), x + 70 * sz, y)   # x is the body centre; the image is wider to the right for the arm

def flat_png(name, size, prj, raw=False):
    """Fluent flat emoji "name" as a PNG at size, recoloured to the "kartun" palette when the theme asks
    (raw: the emoji's own colours, no edge or shadow, for a sticker)"""
    key = ("flat", name, size, TINT_PROPS, PROP_EDGE, raw)
    if key in cache: return cache[key]
    slug = name.lower().replace(" ", "_").replace("-", "_")
    svg = os.path.join(prj, "build", "flat", slug + ".svg")
    if not os.path.exists(svg):
        os.makedirs(os.path.dirname(svg), exist_ok=True)
        folder = FLUENT + name.replace(" ", "%20")
        for url in (f"{folder}/Flat/{slug}_flat.svg", f"{folder}/Default/Flat/{slug}_flat_default.svg"):
            if subprocess.run(["curl", "-fsSL", "-o", svg, url]).returncode == 0: break
        else: raise FileNotFoundError(f"no flat Fluent emoji called {name!r}")
    import cairosvg, io
    img = Image.open(io.BytesIO(cairosvg.svg2png(url=svg, output_width=size, output_height=size))).convert("RGBA")
    if raw:
        cache[key] = img
        return img
    if TINT_PROPS:   # map light-to-dark onto paper white, tape, gold, green, deep green
        a = np.asarray(img).astype(np.float32); rgb = a[..., :3]
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32); sat = rgb.max(-1) - rgb.min(-1)
        pal = np.array([K_DARK, K_GREEN, K_GOLD, K_TAPE, (255, 255, 255)], np.float32)
        out = pal[np.digitize(lum, [70, 120, 175, 225])]; out[(sat < 25) & (lum > 150) & (lum < 235)] = (225, 216, 200)
        img = Image.fromarray(np.dstack([out, a[..., 3]]).astype(np.uint8), "RGBA")
    if PROP_EDGE: img = sticker_edge(img, PROP_EDGE, 9)
    cache[key] = soft_shadow(img, 50, 8, 8)
    return cache[key]

def sticker_edge(img, col, px):
    """a solid outline of colour col around the shape's alpha, like a die-cut sticker"""
    a = img.getchannel("A").filter(ImageFilter.MaxFilter(px * 2 + 1)).filter(ImageFilter.GaussianBlur(1))
    out = Image.new("RGBA", img.size, col + (0,)); out.putalpha(a); out.alpha_composite(img)
    return out

def doodle(frame, t, it, sc, prj):
    """your own character from a pose sheet (cut with poses.py into input/): "poses" [[file, at]], "x"/"y" centre, "h" height;
    a cream sticker edge (PROP_EDGE, or "edge" px 0 for none), a small pop on every pose change and a gentle sway"""
    a = fade_in_out(t, it, 0.35)
    if a <= 0: return
    cur, since = it["poses"][0][0], it["at"]
    for f, at in it["poses"]:
        if t >= at: cur, since = f, max(at, it["at"])
    h, ew = it.get("h", 560), it.get("edge", 8)
    key = ("doodle", cur, h, ew, PROP_EDGE, TORN)
    if key not in cache:
        img = Image.open(os.path.join(prj, "input", cur)).convert("RGBA")
        img = img.resize((round(img.width * h / img.height), h), Image.LANCZOS)
        pad = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0)); pad.paste(img, (20, 20))
        if TORN: pad = torn_sticker(pad, ew * 2, seed=len(cur))
        elif ew and PROP_EDGE: pad = sticker_edge(pad, PROP_EDGE, ew)
        cache[key] = soft_shadow(pad, 60, 10, 8)
    img = cache[key]; k = t - since; changed = since > it["at"]
    if it.get("enter") == "slide":   # walk in from the side, hop on every pose change, slide back out at "until"
        a = 1.0 if it["at"] <= t < it.get("until", 1e9) else 0.0
        p = ramp(t, it["at"], 0.5); q = ramp(t, it.get("until", 1e9) - 0.35, 0.35)
        dx = -620 * (1 - ease_back(p, 1.3)) - 700 * ease_out(q) * q
        hop = -34 * math.sin(math.pi * min(k / 0.35, 1)) if changed and k < 0.35 else 0
        s = (1 + 0.1 * math.sin(math.pi * min(k / 0.3, 1)) * changed) * (1 + 0.02 * math.sin(2 * math.pi * 0.7 * (t - it["at"])))
    else:
        dx, hop = 0, 0
        s = (0.55 + 0.45 * ease_back(ramp(t, it["at"], 0.45), 2.0)) * (1 + 0.07 * math.sin(math.pi * min(k / 0.3, 1)) * changed)
    if a <= 0: return
    rot = 1.6 * math.sin((t - it["at"]) * 1.7)
    im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC).rotate(rot, Image.BICUBIC, expand=True)
    blend(frame, anim(im, a, 1.0), it.get("x", W / 2) + dx, it.get("y", 450) + 6 * math.sin((t - it["at"]) * 2.3) + hop)

def scribble(frame, t, it, sc):
    """a tangled pen scribble that draws itself (a messy head): "x", "y", "size", "dur", "color", "seed"; it jitters while shown"""
    a = fade_in_out(t, it, 0.15)
    if a <= 0: return
    R = it.get("size", 260) / 2; rng = np.random.default_rng(it.get("seed", 3)); n = 420
    u = np.linspace(0, 2 * np.pi * 5, n); f = rng.uniform(0.7, 3.4, 4); ph = rng.uniform(0, 2 * np.pi, 4)   # a tangle of loops
    pts = R * np.stack([0.62 * np.cos(f[0] * u + ph[0]) + 0.38 * np.cos(f[1] * u + ph[1]),
                        0.75 * (0.62 * np.sin(f[2] * u + ph[2]) + 0.38 * np.sin(f[3] * u + ph[3]))], 1) + rng.normal(0, 2.5, (n, 2))
    m = max(2, int(n * ease_out(ramp(t, it["at"], it.get("dur", 0.9)))))
    S = 2; w = int(R * 2.6); img = Image.new("RGBA", (w * S, w * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    jit = 3 * np.array([math.sin(t * 31), math.cos(t * 27)])
    xy = [((x + w / 2 + jit[0]) * S, (y + w / 2 + jit[1]) * S) for x, y in pts[:m]]
    d.line(xy, fill=tuple(it.get("color", INK)) + (255,), width=7 * S, joint="curve")
    img = img.resize((w, w), Image.LANCZOS)
    blend(frame, anim(img, a, 1.0), it.get("x", W / 2), it.get("y", 300))

def desk_paper():
    """a pale sheet of paper lying on a dark wooden desk, with the soft shadow of a window frame and leaves across both"""
    rng = np.random.default_rng(11); yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    grain = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=40, sigmaY=1.2)
    plank = np.floor((yy + 30 * np.sin(xx / 400)) / 260) % 2
    wood = np.dstack([92 + 10 * plank + 26 * grain, 58 + 6 * plank + 17 * grain, 36 + 4 * plank + 10 * grain])
    x0, y0, x1, y1 = 34, 78, W - 34, H - 70   # the sheet
    sh = np.zeros((H, W), np.float32); sh[y0 + 14:y1 + 18, x0 + 8:x1 + 12] = 1; sh = cv2.GaussianBlur(sh, (0, 0), 14)
    img = wood * (1 - 0.55 * sh[..., None])
    paper = np.array(PEACH_TOP, np.float32) + cv2.GaussianBlur(rng.normal(0, 3, (H, W)).astype(np.float32), (0, 0), 1)[..., None]
    paper = paper * (1 - 0.05 * (yy / H))[..., None]
    m = np.zeros((H, W), np.float32); m[y0:y1, x0:x1] = 1; m = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]
    img = img * (1 - m) + paper * m
    light = np.full((H, W), 255, np.uint8)   # window shadow: frame bars and a few leaves, slanted, very soft
    def bar(pts, w): cv2.line(light, pts[0], pts[1], 150, w, cv2.LINE_AA)
    bar(((-200, 1500), (1400, 300)), 46); bar(((-200, 1900), (1400, 700)), 46)
    bar(((200, -100), (900, 1900)), 40); bar(((700, -100), (1400, 1500)), 40)
    for (cx, cy, a_, b_, ang) in ((860, 360, 70, 26, 30), (930, 300, 60, 22, -20), (800, 270, 55, 20, 70), (990, 420, 65, 24, 10), (880, 470, 50, 18, -50)):
        cv2.ellipse(light, (cx, cy), (a_, b_), ang, 0, 360, 165, -1, cv2.LINE_AA)
    poly = np.array([[0, 1250], [W, 600], [W, H], [0, H]], np.int32); band = np.full((H, W), 255, np.uint8)
    cv2.fillPoly(band, [poly], 215)   # the lower part of the page sits outside the sunlit patch
    light = cv2.GaussianBlur(np.minimum(light, band).astype(np.float32), (0, 0), 22) / 255
    img = img * (0.86 + 0.14 * light[..., None]) * (0.9 + 0.12 * light[..., None])
    return np.clip(img, 0, 255).astype(np.float32)

def cutting_mat():
    """green self-healing cutting mat: small squares, a heavier line every five, rulers along two edges, faint angle guides"""
    rng = np.random.default_rng(7)
    bg = np.empty((H, W, 3), np.float32); bg[:] = PEACH_TOP
    bg += cv2.GaussianBlur(rng.normal(0, 3.0, (H, W)).astype(np.float32), (0, 0), 1.2)[..., None]
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img, "RGBA")
    step, x0, y0 = 36, 54, 54
    for k, x in enumerate(range(x0, W, step)): d.line((x, 0, x, H), fill=(120, 190, 150, 120 if k % 5 == 0 else 52), width=2 if k % 5 == 0 else 1)
    for k, y in enumerate(range(y0, H, step)): d.line((0, y, W, y), fill=(120, 190, 150, 120 if k % 5 == 0 else 52), width=2 if k % 5 == 0 else 1)
    for ang in (30, 45, 60):   # angle guides from the bottom-left corner
        a = math.radians(ang); d.line((x0, H - y0, x0 + 3000 * math.cos(a), H - y0 - 3000 * math.sin(a)), fill=(150, 210, 170, 40), width=2)
    f = font("bold", 20)
    for k, x in enumerate(range(x0, W, step)):   # ruler along the top and the left edge
        d.line((x, 0, x, 22 if k % 5 == 0 else 12), fill=(235, 228, 160, 170), width=2)
        if k % 5 == 0 and k: d.text((x + 4, 18), str(k), font=f, fill=(235, 228, 160, 170))
    for k, y in enumerate(range(y0, H, step)):
        d.line((0, y, 22 if k % 5 == 0 else 12, y), fill=(235, 228, 160, 170), width=2)
        if k % 5 == 0 and k: d.text((18, y + 2), str(k), font=f, fill=(235, 228, 160, 170))
    return np.asarray(img).astype(np.float32)

def torn_sticker(img, border=24, amp=20, seed=1):
    """the picture on a white sticker torn out of its sheet: a white margin with a ragged edge, a grey paper-fibre rim,
    one bite torn away, and a soft shadow"""
    a = (np.asarray(img.getchannel("A")) > 40).astype(np.uint8); pad = border + amp + 14
    A = np.pad(a, pad); h, w = A.shape
    ff = A.copy(); cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 2); filled = (ff != 2).astype(np.uint8)   # holes become sticker too
    dil = cv2.dilate(filled, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (border * 2 + 1, border * 2 + 1)))
    dist = cv2.distanceTransform(dil, cv2.DIST_L2, 5)
    rng = np.random.default_rng(seed)
    def nz(sig):
        n = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), sig); return (n - n.min()) / max(1e-6, n.max() - n.min())
    keep = (dist > amp * (0.35 * nz(0.8) + 0.35 * nz(2.5) + 0.3 * nz(12))).astype(np.uint8)
    ys, xs = np.nonzero((dist > 0) & (dist < 3))   # one bite torn off the edge
    if len(xs):
        k = rng.integers(len(xs)); r = border * 1.6
        yy, xx = np.ogrid[:h, :w]; bite = (xx - xs[k]) ** 2 + (yy - ys[k]) ** 2 < (r * (0.8 + 0.4 * nz(3))) ** 2
        keep[bite & (cv2.dilate(filled, np.ones((9, 9), np.uint8)) == 0)] = 0
    d2 = cv2.distanceTransform(keep, cv2.DIST_L2, 3)
    base = np.zeros((h, w, 4), np.float32); base[keep > 0] = (255, 255, 252, 255)
    rim = (keep > 0) & (d2 < 6)   # torn fibres: grey at the very edge, fading to white
    f = np.clip(d2[rim] / 6, 0, 1)[:, None]
    base[rim, :3] = np.array((196, 192, 182), np.float32) * (1 - f) + np.array((255, 255, 252), np.float32) * f
    out = Image.fromarray(base.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.5))
    out.alpha_composite(img, (pad, pad))
    return soft_shadow(out, 80, 9, 8)

STICKER_ANIMS = ("pop", "slide_r", "drop", "spin", "slide_l")

def sticker_anim(it):
    """the entrance an icon uses: its own "anim", else one picked from its name so a run of icons varies"""
    return it.get("anim") or STICKER_ANIMS[sum(map(ord, it.get("img") or it["emoji"])) % len(STICKER_ANIMS)]

def bounce_out(x):
    """ease that lands and bounces a few times, like something dropped on the desk"""
    x = min(max(x, 0.0), 1.0); n, d = 7.5625, 2.75
    if x < 1 / d: return n * x * x
    if x < 2 / d: x -= 1.5 / d; return n * x * x + 0.75
    if x < 2.5 / d: x -= 2.25 / d; return n * x * x + 0.9375
    x -= 2.625 / d; return n * x * x + 0.984375

def sticker(frame, t, it, sc, prj):
    """an icon PNG from input/ as a sticker: "img", "x", "y", "size" (longest side), "rot"; it comes in with "anim"
    (pop | slide_r | slide_l | drop | spin), breathes gently while it stays, and zooms out at its "until" time.
    "emoji": "Light bulb" instead of "img" uses that Fluent flat emoji in its own colours"""
    if t < it["at"]: return
    until = it.get("until", 1e9); k = t - it["at"]
    if t >= until: return
    key = ("stk", it.get("img") or it["emoji"], it.get("size", 260), TORN)
    if key not in cache:
        src = (flat_png(it["emoji"], it.get("size", 260), prj, raw=True) if it.get("emoji")
               else Image.open(os.path.join(prj, "input", it["img"])).convert("RGBA"))
        kk = it.get("size", 260) / max(src.size)
        src = src.resize((max(1, int(src.width * kk)), max(1, int(src.height * kk))), Image.LANCZOS)
        if TORN: cache[key] = torn_sticker(src, seed=len(key[1]) * 3)
        else:   # a neat die-cut sticker: white edge and a soft shadow
            pad = Image.new("RGBA", (src.width + 30, src.height + 30), (0, 0, 0, 0)); pad.paste(src, (15, 15))
            cache[key] = soft_shadow(sticker_edge(pad, (255, 255, 255), 7), 60, 8, 6)
    mode = sticker_anim(it); p = ramp(t, it["at"], 0.45); x, y, rot = it.get("x", W / 2), it.get("y", 1100), it.get("rot", 0)
    s_ = 1.0; a = ease_out(ramp(t, it["at"], 0.12))
    if mode == "pop": s_ = max(0.01, ease_back(p, 2.6)); rot += 12 * (1 - ease_out(p))
    elif mode in ("slide_r", "slide_l"):
        d = 1 if mode == "slide_r" else -1; x += d * 620 * (1 - ease_back(p, 1.4)); rot += d * 16 * (1 - ease_out(p))
    elif mode == "drop": y -= 560 * (1 - bounce_out(ramp(t, it["at"], 0.6)))
    elif mode == "spin": s_ = 0.2 + 0.8 * ease_out(p); rot += 200 * (1 - ease_out(p))
    s_ *= 1 + 0.035 * math.sin(2 * math.pi * 0.85 * k) * ease_out(ramp(t, it["at"] + 0.45, 0.3))   # breathing zoom
    rot += 2.0 * math.sin(2 * math.pi * 0.5 * k + x / 90) * ease_out(ramp(t, it["at"] + 0.45, 0.3))
    q = ramp(t, until - 0.3, 0.3)   # zoom out and tip away
    if q > 0: s_ *= max(0.01, 1 - ease_out(q) * 1.0); rot += 25 * q; a *= 1 - q * 0.5
    img = cache[key]
    img = img.resize((max(1, int(img.width * s_)), max(1, int(img.height * s_))), Image.BICUBIC)
    if abs(rot) > 0.2: img = img.rotate(rot, Image.BICUBIC, expand=True)
    blend(frame, anim(img, a, 1.0), x, y + 4 * math.sin(k * 2.1 + x / 70))

HL = {"y": ((246, 196, 60), (28, 30, 28)), "r": ((232, 92, 70), (255, 255, 255)), "g": ((126, 224, 170), (16, 58, 42))}

def hl(frame, t, it, sc):
    """two-line title: plain words appear one by one, then the key words in a box whose colour carries the meaning
    ("color": "y" key, "r" bad, "g" good)"""
    a = fade_in_out(t, it, 0.2)
    if a <= 0: return
    y = it.get("y", 300); words = (it.get("text") or "").split(); n = len(words)
    if words:
        size = it.get("size1", 60)
        while size > 36 and font("bold", size).getlength(" ".join(words)) > 980: size -= 2
        f = font("bold", size); x = W / 2 - f.getlength(" ".join(words)) / 2
        for i, w_ in enumerate(words):
            wa = a * ease_out(ramp(t, it["at"] + 0.06 * i, 0.18))
            if wa > 0:
                img = soft_shadow(text_img(w_, f, INK), 120, 6, 3)
                blend(frame, anim(img, wa, 1.0), x + f.getlength(w_) / 2, y + 8 * (1 - wa))
            x += f.getlength(w_ + " ")
        y += size * 1.25
    if it.get("key"):
        bgc, fgc = HL[it.get("color", "y")]; size = it.get("size2", 84)
        while size > 44 and font("heavy", size).getlength(it["key"]) > 940: size -= 4
        f = font("heavy", size); tw = f.getlength(it["key"]); asc, desc = f.getmetrics(); bw, bh = int(tw + 36), asc + desc + 10
        t0 = it["at"] + 0.06 * n + 0.05; q = ease_out(ramp(t, t0, 0.25))
        if q > 0:
            box = Image.new("RGBA", (max(1, int(bw * q)), bh), bgc + (255,))
            blend(frame, anim(box, a, 1.0), W / 2 - bw / 2 + box.width / 2, y + bh / 2)
            ta = a * ease_out(ramp(t, t0 + 0.12, 0.15))
            if ta > 0: blend(frame, anim(text_img(it["key"], f, fgc), ta, 1.0), W / 2, y + bh / 2)

def pill_caption(text, size=40):
    key = ("pillcap", text, size)
    if key in cache: return cache[key]
    f = font("bold", size); words = text.split(); lines, cur = [], ""
    for w_ in words:
        if cur and f.getlength(cur + " " + w_) > 860: lines.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    lines.append(cur)
    lh = int(size * 1.3); w = int(max(f.getlength(x) for x in lines)) + 64; h = lh * len(lines) + 34; s = 3
    m = Image.new("L", (w * s, h * s), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=26 * s, fill=235)
    img = Image.new("RGBA", (w, h), (22, 26, 24, 0)); img.putalpha(m.resize((w, h), Image.LANCZOS)); d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines): d.text(((w - f.getlength(ln)) / 2, 15 + i * lh), ln, font=f, fill=(255, 255, 255, 255))
    cache[key] = soft_shadow(img, 90, 10, 6)
    return cache[key]

def prop(frame, t, it, sc, prj):
    """flat prop (a Fluent flat emoji) that pops in and bobs gently"""
    p = ramp(t, it["at"], 0.4)
    if p <= 0: return
    a = ease_out(p * 2) * (1 - ramp(t, it.get("until", 1e9) - 0.25, 0.25))
    if a <= 0: return
    img = flat_png(it["name"], it.get("size", 380), prj); s = 0.4 + 0.6 * ease_back(p, 2.0)
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
    rot = it.get("wobble", 0) * math.sin(2 * math.pi * 2.0 * (t - it["at"])) * math.exp(-0.4 * (t - it["at"]))
    if abs(rot) > 0.2: img = img.rotate(rot, Image.BICUBIC, expand=True)
    blend(frame, anim(img, a, 1.0), it.get("x", 760), it.get("y", 1180) + 8 * math.sin((t - it["at"]) * 2.2 + it.get("x", 720) / 80))

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
        if la > 0: blend(frame, anim(text_img(it["label"], font(face(sc, "serif"), 44 if not sc.get("bold") else 38), col), la, 1.0), it["x"], it["y"] + it.get("size", 170) * 0.5 + 50)

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
        blend(frame, anim(text_img(it["label"], font(face(sc, "serif"), 70 if not sc.get("bold") else 58), soft_ink(sc)), la, 1.0), W / 2, it["y"] + it.get("size", 300) * 0.62)
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
    blend(frame, anim(text_img("minit", font(face(sc, "serif"), 64 if not sc.get("bold") else 52), soft_ink(sc)), a, 1.0), W / 2, it["y"] + 120)

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
        blk = Image.new("RGBA", (sw - 14, hgt), (ACC if i == n - 1 else CREAM if sc.get("dark") else INK) + (255,))
        blend(frame, blk, x0 + i * sw + sw / 2, base - hgt / 2)
        if lab:
            blend(frame, anim(text_img(lab, font(face(sc, "serif"), 58 if not sc.get("bold") else 48), soft_ink(sc)), ease_out(ramp(t, at + 0.2, 0.3)), 1.0),
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
        asc, desc = f.getmetrics(); ImageDraw.Draw(img).text(((w - tw) / 2, (h - asc - desc) / 2 - 2), it["text"], font=f, fill=CTA_TEXT + (255,))
        cache[key] = soft_shadow(img, 110, 16, 10)
    blend(frame, anim(cache[key], a, 0.85), W / 2, it["y"])
    s = 4; cw, chh = 60, 52; m = Image.new("L", (cw * s, chh * s), 0); d = ImageDraw.Draw(m)
    for oy in (6, 26): d.line([(10 * s, oy * s), (30 * s, (oy + 16) * s), (50 * s, oy * s)], fill=255, width=6 * s, joint="curve")
    chev = Image.new("RGBA", (cw, chh), ACC + (0,)); chev.putalpha(m.resize((cw, chh), Image.LANCZOS).point(lambda v: int(v * a)))
    blend(frame, chev, W / 2, it["y"] + 100 + 8 * math.sin(2 * math.pi * 1.4 * (t - it["at"])))

# ---------- photo: a still (e.g. an AI illustration) brought to life ----------
def photo_layers(it, prj):
    """the still at cover size for the largest zoom, a foreground mask (subject above the floor line + all below it),
    twinkle maps for small bright lights and a soft glow map"""
    key = ("photo", it["img"])
    if key in cache: return cache[key]
    src8 = np.asarray(Image.open(os.path.join(prj, "input", it["img"])).convert("RGB"))
    h, w = src8.shape[:2]; zmax = max(it.get("zoom", [1.0, 1.15])) * (1 + it.get("parallax", 0.035)) * 1.02
    s = max(W / w, H / h) * zmax; size = (int(w * s) + 2, int(h * s) + 2)
    big = cv2.resize(src8, size, interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    (fx0, fy0), (fx1, fy1) = it.get("floor", [[0, 1.1], [1, 1.1]])           # desk / floor edge, as fractions
    below = yy > (fy0 + (fy1 - fy0) * xx / w) * h
    subj = np.zeros((h, w), bool)
    if it.get("subject_box"):
        import mediapipe as mp
        from mediapipe.tasks.python import vision, BaseOptions
        seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=os.path.join(HERE, "models", "selfie_segmenter.tflite")),
            output_confidence_masks=True, running_mode=vision.RunningMode.IMAGE))
        m = np.squeeze(seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(src8))).confidence_masks[0].numpy_view())
        bx0, by0, bx1, by1 = it["subject_box"]
        subj = (m > 0.5) & (xx > bx0 * w) & (xx < bx1 * w) & (yy > by0 * h) & ~below
    mask = cv2.GaussianBlur((below | subj).astype(np.float32), (0, 0), 3)
    mask = cv2.resize(mask, size, interpolation=cv2.INTER_LINEAR)
    lights = []
    if it.get("lights_box"):
        lx0, ly0, lx1, ly1 = it["lights_box"]; lum = src8.mean(axis=2)
        reg = (lum > it.get("lights_min", 205)) & (xx > lx0 * w) & (xx < lx1 * w) & (yy > ly0 * h) & (yy < ly1 * h)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(reg.astype(np.uint8))
        groups = [np.zeros((h, w), np.float32) for _ in range(3)]
        for i in range(1, n):
            if 2 <= stats[i][4] <= 400: cv2.circle(groups[i % 3], (int(cent[i][0]), int(cent[i][1])), 5, 1.0, -1)
        q = (size[0] // 4, size[1] // 4)   # quarter size: warped per frame, so keep them cheap
        lights = [cv2.resize(cv2.GaussianBlur(g, (0, 0), 6), q, interpolation=cv2.INTER_AREA) for g in groups]
    glow = None
    if it.get("glow"):
        gx, gy, gr = it["glow"]; d = np.sqrt((xx / w - gx) ** 2 + ((yy / h - gy) * h / w) ** 2)
        glow = cv2.resize(np.clip(1 - d / gr, 0, 1) ** 2, (size[0] // 4, size[1] // 4), interpolation=cv2.INTER_AREA)
    cache[key] = (big, mask, lights, glow)
    return cache[key]

PHOTO_SHADE = (1 - 0.62 * np.clip(1 - np.arange(H, dtype=np.float32) / 1000, 0, 1) ** 1.2)[:, None, None]   # text stays legible

def photo(frame, t, it, sc, prj):
    """slow push-in on the focus point with foreground parallax, twinkling lights, a breathing glow and dust in it"""
    big, mask, lights, glow = photo_layers(it, prj)
    bh, bw = big.shape[:2]
    p = ramp(t, it["at"], it.get("until", it["at"] + 8) - it["at"]); p = p * p * (3 - 2 * p)
    z0, z1 = it.get("zoom", [1.0, 1.15]); z = z0 + (z1 - z0) * p
    fx, fy = it.get("focus", [0.5, 0.45])
    zmax = max(it.get("zoom", [1.0, 1.15])) * (1 + it.get("parallax", 0.035)) * 1.02   # the scale photo_layers built at
    def affine(zl):
        k = zl / zmax
        tx = min(0.0, max(W - bw * k, W / 2 - fx * bw * k))
        ty = min(0.0, max(H - bh * k, H * it.get("focus_at", 0.5) - fy * bh * k))   # where the focus point sits on screen
        return np.float32([[k, 0, tx], [0, k, ty]])
    Mb, Mf = affine(z), affine(z * (1 + it.get("parallax", 0.035) * p))
    bg = cv2.warpAffine(big, Mb, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    fg = cv2.warpAffine(big, Mf, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    m = cv2.warpAffine(mask, Mf, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[..., None]
    img = bg * (1 - m) + fg * m
    if lights or glow is not None:   # twinkle + breathing glow, built at quarter size and scaled up
        Mq = Mb.copy(); Mq[:, 2] /= 4; add = np.zeros((H // 4, W // 4, 3), np.float32)
        for i, g in enumerate(lights):
            amp = 0.5 + 0.5 * math.sin(2 * math.pi * (0.55 + 0.25 * i) * t + i * 2.1)
            add += cv2.warpAffine(g, Mq, (W // 4, H // 4))[..., None] * np.array((255, 214, 150), np.float32) * 0.55 * amp
        if glow is not None:
            add += cv2.warpAffine(glow, Mq, (W // 4, H // 4))[..., None] * np.array((255, 190, 120), np.float32) * (0.10 + 0.04 * math.sin(2 * math.pi * 0.35 * t))
        img += cv2.resize(add, (W, H), interpolation=cv2.INTER_LINEAR)
    if it.get("glow"):   # dust drifting up through the lamp light
        gx, gy, _ = it["glow"]; cx, cy = Mb @ np.array([gx * bw, gy * bh, 1.0])
        rng = np.random.default_rng(2)
        for i in range(22):
            ox, oy, sp = rng.uniform(-260, 120), rng.uniform(-200, 260), rng.uniform(10, 26)
            x = int(cx + ox + 14 * math.sin(t * 0.7 + i)); y = int(cy + (oy - t * sp) % 460 - 230)
            if 0 <= x < W and 0 <= y < H: cv2.circle(img, (x, y), 2, (255, 236, 200), -1, cv2.LINE_AA)
    dim = it.get("dim")
    if dim:
        amt = float(np.interp(t, [d[1] for d in dim], [d[0] for d in dim]))
        img *= 1 - amt
    frame[:] = img * PHOTO_SHADE

def clip_frames(name, prj):
    """every frame of a clip in input/ (e.g. an AI image-to-video), decoded once"""
    key = ("clip", name)
    if key not in cache:
        path = os.path.join(prj, "input", name)
        j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                       "-of", "json", path], capture_output=True, text=True, check=True).stdout)["streams"][0]
        w, h = j["width"], j["height"]; num, den = map(int, j["r_frame_rate"].split("/"))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        cache[key] = (np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3), num / den)
    return cache[key]

def clip(frame, t, it, sc, prj):
    """a video clip as the scene's picture; "fit" stretches it over at..until, with a gentle push-in and dim like photo;
    "card": {"w", "y", "rot"} plays it inside a white-framed card instead (e.g. landscape product footage on a paper scene)"""
    frames, fps = clip_frames(it["video"], prj)
    n, h, w = frames.shape[:3]; t0, t1 = it["at"], it.get("until", it["at"] + n / fps)
    rate = (n / fps) / (t1 - t0) if it.get("fit") else 1.0
    src = frames[min(n - 1, max(0, int((t - t0) * rate * fps)))]
    if it.get("card"):
        if t < t0 or t >= t1: return
        cd = it["card"]; cw = cd.get("w", 960); ch = int(h * cw / w); b = 14
        p = ramp(t, t0, 0.45); a = ease_out(p * 3)
        face_ = Image.new("RGBA", (cw + b * 2, ch + b * 2), (255, 255, 255, 255))
        face_.paste(Image.fromarray(cv2.resize(src, (cw, ch), interpolation=cv2.INTER_AREA)), (b, b))
        m = Image.new("L", (face_.width * 2, face_.height * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=44, fill=255); face_.putalpha(m.resize(face_.size, Image.LANCZOS))
        img = soft_shadow(face_, 90, 18, 12).rotate(cd.get("rot", 0), Image.BICUBIC, expand=True)
        q = ramp(t, t1 - 0.35, 0.35); frm = cd.get("from", "bottom")   # slide in, then slide out to the left
        dx = (900 * (1 - ease_back(p, 1.2)) if frm == "right" else 0) - 1300 * ease_out(q) * q
        dy = 760 * (1 - ease_back(p, 1.2)) if frm == "bottom" else 0
        blend(frame, anim(img, min(1.0, a + q), 1.0), cd.get("x", W / 2) + dx, cd.get("y", 1080) + dy)
        return
    p = ramp(t, t0, t1 - t0); p = p * p * (3 - 2 * p)
    z0, z1 = it.get("zoom", [1.0, 1.06]); k = max(W / w, H / h) * (z0 + (z1 - z0) * p)
    fx, fy = it.get("focus", [0.5, 0.45])
    tx = min(0.0, max(W - w * k, W / 2 - fx * w * k)); ty = min(0.0, max(H - h * k, H * it.get("focus_at", 0.5) - fy * h * k))
    img = cv2.warpAffine(src, np.float32([[k, 0, tx], [0, k, ty]]), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    dim = it.get("dim")
    if dim: img *= 1 - float(np.interp(t, [d[1] for d in dim], [d[0] for d in dim]))
    frame[:] = img * PHOTO_SHADE

DRAW = {"hl": hl, "scribble": scribble, "badge": badge, "say": say, "tape": tape, "mascot": mascot, "setup": setup, "kicker": kicker, "script_title": script_title, "head": head, "tile": tile, "count": count, "timer": timer,
        "race": race, "blocks": blocks, "stairs": stairs, "calendar": calendar, "cta": cta, "floaters": floaters, "pile": pile}

def draw_scene(sc, t, prj):
    frame = background(sc.get("dark", False)).copy()
    for it in sc["items"]:
        if it["kind"] == "photo": photo(frame, t, it, sc, prj)
        elif it["kind"] == "emoji": emoji(frame, t, it, sc, prj)
        elif it["kind"] == "prop": prop(frame, t, it, sc, prj)
        elif it["kind"] == "doodle": doodle(frame, t, it, sc, prj)
        elif it["kind"] == "sticker": sticker(frame, t, it, sc, prj)
        elif it["kind"] == "clip": clip(frame, t, it, sc, prj)
        elif it["kind"] in ("card", "ticks"): (card if it["kind"] == "card" else ticks)(frame, t, it, sc, prj)
        elif it["kind"] == "floaters": floaters(frame, t, it)
        else: DRAW[it["kind"]](frame, t, it, sc)
    return frame

def whip(a, b, p):
    """sideways motion-blur push from frame a to frame b, p 0 -> 1"""
    e = 0.5 - 0.5 * math.cos(math.pi * p); k = int(9 + 90 * math.sin(math.pi * p))
    sa = np.roll(a, -int(W * 0.35 * e), axis=1); sb = np.roll(b, int(W * 0.35 * (1 - e)), axis=1)
    mix = sa * (1 - e) + sb * e
    return cv2.blur(mix, (k, 1)) if k > 1 else mix

def frame_at(scenes, t, prj, caps=None):
    fr = scene_frame(scenes, t, prj)
    if caps: captions(fr, t, caps)
    return fr

def scene_frame(scenes, t, prj):
    i = max(j for j, s in enumerate(scenes) if s["start"] <= t or j == 0)
    sc = scenes[i]
    if i > 0 and sc.get("in", "whip") == "whip" and t < sc["start"] + 0.14:
        prev = scenes[i - 1]; p = (t - (sc["start"] - 0.14)) / 0.28
        return whip(draw_scene(prev, sc["start"] - 0.01, prj), draw_scene(sc, sc["start"], prj), p)
    if i + 1 < len(scenes) and scenes[i + 1].get("in", "whip") == "whip" and t > scenes[i + 1]["start"] - 0.14:
        nxt = scenes[i + 1]; p = (t - (nxt["start"] - 0.14)) / 0.28
        return whip(draw_scene(sc, nxt["start"] - 0.01, prj), draw_scene(nxt, nxt["start"], prj), p)
    return draw_scene(sc, t, prj)

# ---------- captions: the voiceover in big headline type ----------
def caption_img(text, size, kind="heavy"):
    """heavy capitals (or "script"), ink with a thin white outline; a final '.' is orange"""
    key = ("cap", text, size, kind)
    if key in cache: return cache[key]
    f = font(kind, size); sw = max(2, round(size / CAP_STROKE)); pad = sw + 12
    body, dot = (text[:-1], ".") if text.endswith(".") else (text, "")
    w = int(f.getlength(body) + (f.getlength(".") if dot else 0)) + pad * 2; asc, desc = f.getmetrics()
    img = Image.new("RGBA", (w, asc + desc + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((pad, pad), body, font=f, fill=CAP_FILL + (255,), stroke_width=sw, stroke_fill=CAP_EDGE + (255,))
    if dot: d.text((pad + f.getlength(body) - 4, pad), ".", font=f, fill=ACC + (255,), stroke_width=sw, stroke_fill=CAP_EDGE + (255,))
    halo = Image.new("RGBA", (img.width + 40, img.height + 40), HALO + (0,))   # soft glow (white by default): reads on dark scenes too
    thin = kind == "script"   # handwriting strokes are thinner: a stronger glow keeps them readable on dark scenes
    a = Image.new("L", halo.size, 0); a.paste(img.getchannel("A").filter(ImageFilter.MaxFilter(13 if thin else 9)), (20, 20))
    halo.putalpha(a.filter(ImageFilter.GaussianBlur(10 if thin else 12)).point(lambda v: min(255, int(v * (1.0 if thin else 0.75)))))
    halo.alpha_composite(img, (20, 20))
    cache[key] = halo
    return cache[key]

def captions(frame, t, cap):
    """the chunk being spoken pops in; long chunks wrap to two lines"""
    size, y, kind = cap.get("size", 100), cap.get("y", 1390), cap.get("face", "heavy")
    if cap.get("style") == "pill":   # whole sentence in a dark rounded pill, like a subtitle bar
        for text, s0, s1 in cap["chunks"]:
            if s0 <= t < s1:
                blend(frame, anim(pill_caption(text, cap.get("size", 40)), ease_out(ramp(t, s0, 0.12)), 1.0), W / 2, y); break
        return
    for text, s0, s1 in cap["chunks"]:
        if not s0 <= t < s1: continue
        words = text.split(" "); lines = [text]
        if font(kind, size).getlength(text) > 940 and len(words) > 1:
            k = (len(words) + 1) // 2; lines = [" ".join(words[:k]), " ".join(words[k:])]
        a = ease_out(ramp(t, s0, 0.12)); sc_ = 0.9 + 0.1 * ease_back(ramp(t, s0, 0.22), 2.0)
        for i, ln in enumerate(lines):
            img = caption_img(ln, size, kind)
            if abs(sc_ - 1) > 1e-3: img = img.resize((max(1, int(img.width * sc_)), max(1, int(img.height * sc_))), Image.BICUBIC)
            if a < 0.999: img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
            blend(frame, img, W / 2, y + (i - (len(lines) - 1) / 2) * size * 1.02)
        break

def caption_chunks(words, fixes=None, max_words=3, size=100, maxw=900, upper=True, kind="heavy"):
    """[[TEXT, start, end]] from Whisper words: break at punctuation, after max_words or when too wide;
    a chunk stays up until the next one, unless there is a real pause"""
    fixes = fixes or {}; out, cur = [], []; start = [True]   # sentence case: only a new sentence gets a capital
    def flush():
        if not cur: return
        text = " ".join(fixes.get(w["w"], w["w"]) for w in cur)
        text = text.upper() if upper else (text[:1].upper() + text[1:] if start[0] else text)
        start[0] = text[-1:] in ".?!"
        text = text.replace(",", "").rstrip("!")
        out.append([text, cur[0]["s"], cur[-1]["e"]]); cur.clear()
    for w in words:
        cand = " ".join(x["w"] for x in cur + [w])
        if cur and (len(cur) >= max_words or font(kind, size).getlength(cand.upper() if upper else cand) > maxw): flush()
        cur.append(w)
        if w["w"][-1:] in ".,?!": flush()
    flush()
    for i in range(len(out) - 1):
        out[i][2] = out[i + 1][1] if out[i + 1][1] - out[i][2] < 0.6 else out[i][2] + 0.3
    out[-1][2] += 0.6
    return [[t, round(a, 3), round(b, 3)] for t, a, b in out]

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
            elif it["kind"] in ("card", "tile", "emoji", "prop", "tape"):
                ev.append((it["at"], "pop", -16))
                if it["kind"] == "card" and it.get("until", 99) < dur: ev.append((it["until"] - 0.3, "swish", -22))
            elif it["kind"] == "doodle":
                ev += [(at, "pop", -18) for *_, at in it["poses"][1:]]
                if it.get("enter") == "slide":
                    ev.append((it["at"] - 0.05, "swish", -17))
                    if it.get("until"): ev.append((it["until"] - 0.4, "swish", -19))
            elif it["kind"] == "sticker":
                m_ = sticker_anim(it)
                ev.append((it["at"] + (0.12 if m_ == "drop" else 0), {"pop": "pop", "drop": "boing"}.get(m_, "swish"), -16))
                if it.get("good"): ev.append((it["at"] + 0.3, "ding", -24))
            elif it["kind"] == "clip" and it.get("card"):
                ev.append((it["at"] - 0.05, "whoosh", -18)); ev.append((it.get("until", it["at"] + 3) - 0.4, "swish", -21))
            elif it["kind"] == "hl": ev.append((it["at"] - 0.1, "whoosh", -24))
            elif it["kind"] == "scribble": ev.append((it["at"], "whoosh", -22))
            elif it["kind"] == "say": ev.append((it["at"] - 0.1, "whoosh", -26))
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
    make = {"whoosh": sfx.whoosh, "pop": sfx.pop, "tick": sfx.tick, "ding": sfx.ding, "boing": sfx.boing, "swish": sfx.swish}
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
    if cfg.get("captions"): cfg["captions"]["chunks"] = [[x, f(a), f(b)] for x, a, b in cfg["captions"]["chunks"]]
    for sc in cfg["scenes"]:
        sc["start"] = f(sc["start"])
        for it in sc["items"]:
            for k in TIME_KEYS:
                if k in it: it[k] = f(it[k])
            for k in ("lines", "items", "labels", "dim"):
                if k in it: it[k] = [[x, f(t)] for x, t in it[k]]
            if "poses" in it: it["poses"] = [[*v[:-1], f(v[-1])] for v in it["poses"]]   # time is last
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
    set_theme(cfg.get("theme"))
    if cfg.get("bg_image"): globals()["BG_IMAGE"] = os.path.join(prj, cfg["bg_image"])
    scenes = sorted(cfg["scenes"], key=lambda s: s["start"])
    for sc in scenes: sc.setdefault("bold", cfg.get("bold_text", False)); sc.setdefault("setup_face", cfg.get("setup_face"))
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
        fr = frame_at(scenes, t0 + n / FPS, prj, cfg.get("captions"))
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes()); n += 1
        if n % 150 == 0: print(f"{n}/{total} frames", flush=True)
    enc.stdin.close(); enc.wait()
    print(f"done: {n} frames, {n_ev} sfx -> {out}")

if __name__ == "__main__":
    main()
