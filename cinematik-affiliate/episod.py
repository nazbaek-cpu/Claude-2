"""Template episod ("guna template episod"): a minimal story-series cartoon on a dark navy stage.

Look (styles/template-episod.md): navy gradient page with a soft vignette, a thin rounded frame and one floor line.
A small yellow episode pill and a big scene title sit at the top; one or two words of the title carry the scene's
emotion in colour (red = the label / the problem, yellow = a question / attention, green = the fix). Saved
characters (or stickman poses) stand on the floor with white name tags ("Abang, 16"), turn grey when they give up,
and react with a red "!!" or a yellow "?". Props tell the story: a paper with a hand-written label that gets struck
out in red and rewritten in green, a door to listen behind, a desk with a lamp at night, ticks that count 1-2-3,
the label words drifting around a sad child. Scenes cross-fade through dark. No subtitles: the VO carries the story.

    python episod.py projects/<name>            render out/final.mp4
    python episod.py projects/<name> 1.5 4 8    a sheet of stills at those times (build/stills.jpg)

project.json:
{"type": "episod", "source": "input/vo.mp4", "episode": "EPISOD 1 · JANGAN LABEL ANAK",
 "scenes": [{"start": 0.0, "end": 6.0, "title": "\\"Saya *TAK PANDAI* English\\"", "tone": "red", "flash": "IMBAS KEMBALI",
             "items": [
   {"kind": "paper", "x": 330, "y": 980, "at": 0.2, "head": "KERTAS KARANGAN", "name": "Nama: Abang · 4 Bestari",
    "text": "Saya memang|tak pandai English.", "strike_at": 30.1, "rewrite": "Saya boleh tulis English.", "rewrite_at": 31.0},
   {"kind": "char", "char": "abang/stres", "x": 820, "at": 0.4, "size": 420, "name": "Abang, 16",
    "char_at": [[3.0, "abang/sedih"]], "grey": [[8.0, 20.0]], "mark": "!!", "mark_at": 0.6},
   {"kind": "door", "x": 700, "at": 6.2}, {"kind": "desk", "x": 560, "at": 20.0, "lamp": true, "cups": 0},
   {"kind": "moon", "at": 20.0}, {"kind": "ticks", "x": 420, "y": 1060, "at": [21.0, 21.8, 22.6]},
   {"kind": "words", "text": "lemah", "x": 700, "y": 1150, "at": 12.0},
   {"kind": "photo", "img": "cover.jpg", "x": 300, "y": 1050, "w": 300, "at": 20.5},
   {"kind": "comment", "text": "CONTOH", "at": 36.0}]}],
 "follow": "Ikut untuk episod seterusnya", "cta": {"at": 37.0, "text": "Tekan link dekat bawah"}}
"""
import json, math, os, subprocess, sys, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import arab
from arab import SANS, card_box, ease, put, ramp, shadowed

W, H, FPS = 1080, 1920, 30
FLOOR = 1380
TONE = {"red": (255, 112, 96), "yellow": (255, 205, 64), "green": (110, 214, 140), "white": (255, 255, 255)}
TONE_LIGHT = {"red": (222, 58, 48), "yellow": (232, 140, 10), "green": (34, 156, 76), "white": (40, 40, 50)}
LIGHT = [False]   # "bg": "dots" -> white dotted page, dark type
NEON = [False]    # "neon": true -> titles glow like neon signs (key words in the tone colour)
INK = (24, 28, 44)
HAND = lambda s: arab.font("PatrickHand-Regular.ttf", s)


# ---------- stage ----------
def stage(kind="navy"):
    if kind == "dots":   # the white dot-grid page of template motion, plain (no glow)
        import motion
        im = motion.page(28, glow=False); d = ImageDraw.Draw(im)
        d.rounded_rectangle((26, 26, W - 27, H - 27), 30, outline=(214, 214, 220), width=2)
        d.line((40, FLOOR, W - 40, FLOOR), fill=(190, 190, 200), width=3); return im
    if NEON[0]:   # the darker navy page of template motion's neon theme, with the floor line
        import motion
        motion.ACC[0], motion.ACC[1] = (0, 229, 255), (255, 64, 200)
        im = motion.neon_page(); ImageDraw.Draw(im).line((40, FLOOR, W - 40, FLOOR), fill=(70, 110, 200), width=3); return im
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top, bot = np.array([26, 46, 110], np.float32), np.array([8, 14, 44], np.float32)
    u = (yy / H)[..., None]; a = top * (1 - u) + bot * u
    glow = np.exp(-(((xx - W * 0.45) / (W * 0.55)) ** 2 + ((yy - H * 0.28) / (H * 0.35)) ** 2))[..., None]
    a = a + glow * np.array([22, 28, 46], np.float32)
    vig = 1 - 0.45 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)[..., None]
    im = Image.fromarray((a * vig.clip(0.45, 1)).clip(0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 26, W - 27, H - 27), 30, outline=(70, 86, 140), width=2)
    d.line((40, FLOOR, W - 40, FLOOR), fill=(96, 112, 168), width=3)
    return im


# ---------- type ----------
_c = {}
def pill_img(text):
    if ("pill", text) not in _c:
        f = SANS(30, 800); w = int(f.getlength(text)) + 60; im = card_box(w, 56, 28, fill=(247, 198, 52, 255))
        ImageDraw.Draw(im).text((w / 2, 28), text, font=f, fill=INK, anchor="mm"); _c[("pill", text)] = im
    return _c[("pill", text)]

def title_img(text, tone):
    """big white scene title; *words* take the tone colour; wraps to the page width"""
    key = ("title", text, tone)
    if key not in _c:
        f = SANS(82, 800); col = (TONE_LIGHT if LIGHT[0] else TONE).get(tone, TONE["yellow"]); base_col = INK if LIGHT[0] else (255, 255, 255); toks, hot = [], False
        for w in text.split():
            core = w.rstrip(".,!?\"':;"); s = w.lstrip("\"'").startswith("*"); e = core.endswith("*") and (len(core.strip("\"'")) > 1 or not s); ww = w.replace("*", "")
            if s: hot = True
            if ww: toks.append((ww, hot))
            if e: hot = False
        rows, row, sp = [], [], f.getlength(" ")
        for w, h_ in toks:
            if row and sum(f.getlength(x) for x, _ in row) + sp * len(row) + f.getlength(w) > W - 140: rows.append(row); row = []
            row.append((w, h_))
        neon = NEON[0] and not LIGHT[0]; top = 40 if neon else 10   # room above for the glow
        rows.append(row); lh = 100; im = Image.new("RGBA", (W, lh * len(rows) + 20 + (top - 10) * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        for i, r in enumerate(rows):
            tw = sum(f.getlength(x) for x, _ in r) + sp * (len(r) - 1); x = (W - tw) / 2
            for w, h_ in r:
                if neon:   # pale tube core, coloured halo
                    d.text((x, top + i * lh), w, font=f, fill=tuple(int(255 * 0.7 + c * 0.3) for c in col) if h_ else (246, 248, 255))
                    dg.text((x, top + i * lh), w, font=f, fill=col + (255,) if h_ else (110, 150, 255, 200))
                else:
                    d.text((x, 10 + i * lh), w, font=f, fill=col if h_ else base_col)
                x += f.getlength(w) + sp
        if neon:
            out = Image.new("RGBA", im.size, (0, 0, 0, 0))
            for r_ in (24, 24, 8, 3): out.alpha_composite(g.filter(ImageFilter.GaussianBlur(r_)))
            out.alpha_composite(im); im = out
        _c[key] = im
    return _c[key]

def name_tag(text):
    if ("tag", text) not in _c:
        f = SANS(28, 700); w = int(f.getlength(text)) + 28
        im = card_box(w, 44, 8, fill=(255, 255, 255, 255), outline=(190, 190, 200) if LIGHT[0] else None, width=2 if LIGHT[0] else 0)
        ImageDraw.Draw(im).text((w / 2, 22), text, font=f, fill=INK, anchor="mm"); _c[("tag", text)] = im
    return _c[("tag", text)]

def mark_img(sym):
    if ("mark", sym) not in _c:
        f = SANS(90, 800); col = (240, 60, 60) if sym == "!!" else TONE["yellow"]
        im = Image.new("RGBA", (150, 130), (0, 0, 0, 0)); ImageDraw.Draw(im).text((75, 65), sym, font=f, fill=col, anchor="mm"); _c[("mark", sym)] = im
    return _c[("mark", sym)]


# ---------- characters ----------
def char_img(path, size, grey):
    key = ("ch", path, size)
    if key not in _c:
        im = Image.open(arab.asset(path + ".png")).convert("RGBA"); k = size / im.height
        im = im.resize((max(1, int(im.width * k)), size), Image.LANCZOS)
        if path.startswith("stickman/"): im = arab.outlined(im, 6)
        if LIGHT[0]:   # a soft shadow keeps white sticker rims readable on the white page
            pad = 24; sh = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0)); m = Image.new("L", sh.size, 0)
            m.paste(im.split()[3], (pad, pad + 6)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 60 // 255))
            sh.alpha_composite(im, (pad, pad)); im = sh
        _c[key] = im
    im = _c[key]
    if grey > 0:   # drain the colour (and dim) when the character gives up
        g = im.convert("LA").convert("RGBA"); g.putalpha(im.split()[3])
        dim = Image.blend(im, g, grey); px = np.array(dim).astype(np.float32); px[..., :3] *= 1 - 0.35 * grey
        im = Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA")
    return im

def grey_level(it, t):
    g = 0.0
    for a, b in it.get("grey", []): g = max(g, ramp(t, a, 0.5) * (1 - ramp(t, b, 0.5)))
    return g


# ---------- props ----------
def paper_img(it, t):
    w, h = it.get("w", 520), it.get("h", 360)
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((18, 18, w + 18, h + 18), 16, fill=(214, 168, 30))            # page edge
    d.rounded_rectangle((6, 6, w + 6, h + 6), 16, fill=it.get("color", (247, 202, 64)))
    d.rounded_rectangle((44, 30, w - 30, 92), 8, fill=(255, 255, 255)); d.text(((w + 14) / 2, 61), it.get("head", "KERTAS KARANGAN"), font=SANS(32, 800), fill=INK, anchor="mm")
    if it.get("name"): d.text((50, 122), it["name"], font=SANS(24, 600), fill=(70, 60, 30), anchor="lm")
    lines = it["text"].split("|"); f = HAND(it.get("text_size", 54)); y0 = 160; lh = 62
    for i, l in enumerate(lines): d.text((56 + i * 14, y0 + i * lh), l, font=f, fill=(40, 40, 46))
    sa = it.get("strike_at")
    if sa is not None and t >= sa:   # red strike, line by line, left to right
        p = ramp(t, sa, 0.6)
        for i, l in enumerate(lines):
            q = min(1, max(0, p * len(lines) - i)); x0 = 54 + i * 14; x1 = x0 + f.getlength(l) * q; y = y0 + i * lh + 36
            if q > 0: d.line((x0, y, x1, y + 2), fill=(226, 50, 50), width=6)
    ra = it.get("rewrite_at")
    if it.get("rewrite") and ra is not None and t >= ra:   # green hand-writing that writes itself in
        p = ramp(t, ra, 0.9); fg = HAND(it.get("rewrite_size", it.get("text_size", 54) - 6)); txt = it["rewrite"]; y = y0 + len(lines) * lh + 4
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).text((56, y), txt, font=fg, fill=(30, 150, 70))
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rectangle((0, 0, 56 + fg.getlength(txt) * p, im.height), fill=255)
        im.paste(lay, (0, 0), Image.composite(lay, Image.new("RGBA", im.size, (0, 0, 0, 0)), m))
    return shadowed(im.rotate(it.get("rot", 3), resample=Image.BICUBIC, expand=True), 14, 90, 10)

def door_img():
    if "door" not in _c:
        im = Image.new("RGBA", (230, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 229, 419), fill=(120, 74, 44)); d.rectangle((14, 14, 215, 419), fill=(40, 34, 30))
        d.rectangle((14, 14, 120, 419), fill=(150, 96, 58)); d.ellipse((96, 210, 112, 226), fill=(240, 200, 90)); _c["door"] = im
    return _c["door"]

def desk_img(lamp, cups, glow_p):
    w = 560; im = Image.new("RGBA", (w + 200, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im); ox = 100
    if lamp and glow_p > 0:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse((ox + w - 380, 40, ox + w + 60, 420), fill=(255, 230, 150, int(110 * glow_p)))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    d.rectangle((ox, 300, ox + w, 324), fill=(150, 100, 62)); d.rectangle((ox + 20, 324, ox + 36, 520), fill=(120, 78, 48)); d.rectangle((ox + w - 36, 324, ox + w - 20, 520), fill=(120, 78, 48))
    d.rectangle((ox + w / 2 - 90, 328, ox + w / 2 + 90, 400), fill=(170, 116, 72)); d.rectangle((ox + w / 2 - 20, 360, ox + w / 2 + 20, 368), fill=(240, 196, 80))
    for k in range(cups):
        cx = ox + 150 + k * 110; d.rounded_rectangle((cx - 26, 252, cx + 26, 298), 8, fill=(250, 250, 250)); d.arc((cx + 16, 262, cx + 42, 288), 270, 90, fill=(250, 250, 250), width=6)
        for j in range(2): d.arc((cx - 14 + j * 14, 200, cx + j * 14, 244), 200, 340, fill=(220, 220, 230), width=4)
    if lamp:
        lx = ox + w - 130; d.line((lx, 298, lx - 30, 200), fill=(240, 240, 240), width=8); d.line((lx - 30, 200, lx + 20, 160), fill=(240, 240, 240), width=8)
        d.polygon([(lx + 4, 130), (lx + 80, 168), (lx + 10, 196)], fill=(250, 190, 60)); d.ellipse((lx - 40, 290, lx + 30, 304), fill=(240, 240, 240))
    return im

def moon_img():
    if "moon" not in _c:
        im = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((40, 40, 180, 180), fill=(250, 226, 160)); d.ellipse((80, 22, 210, 152), fill=(0, 0, 0, 0))
        m = Image.new("L", im.size, 0); md = ImageDraw.Draw(m); md.ellipse((40, 40, 180, 180), fill=255); md.ellipse((80, 22, 210, 152), fill=0)
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.paste(Image.new("RGBA", im.size, (250, 226, 160, 255)), (0, 0), m)
        od = ImageDraw.Draw(out)
        for x, y in [(10, 120), (200, 30), (190, 200)]: od.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(220, 220, 240))
        _c["moon"] = out
    return _c["moon"]

def tick_img(n):
    if ("tick", n) not in _c:
        im = Image.new("RGBA", (120, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((6, 6, 114, 114), fill=(52, 168, 90)); d.line([(32, 62), (52, 82), (88, 40)], fill="white", width=12, joint="curve")
        d.text((60, 148), str(n), font=SANS(40, 800), fill=INK if LIGHT[0] else (240, 240, 240), anchor="mm"); _c[("tick", n)] = im
    return _c[("tick", n)]

def photo_img(name, w):
    key = ("ph", name, w)
    if key not in _c:
        src = Image.open(arab.asset(name)).convert("RGB"); k = w / src.width; src = src.resize((w, int(src.height * k)), Image.LANCZOS)
        box = card_box(w + 24, src.height + 24, 18); box.paste(src, (12, 12)); _c[key] = shadowed(box, 16, 110, 10)
    return _c[key]

def comment_img(text):
    if ("cm", text) not in _c:
        f = SANS(56, 800); a = "Komen: "; w = int(f.getlength(a + text)) + 90; im = card_box(w, 110, 55)
        d = ImageDraw.Draw(im); d.text((45, 55), a, font=f, fill=INK, anchor="lm"); d.text((45 + f.getlength(a), 55), text, font=f, fill=(46, 160, 86), anchor="lm")
        _c[("cm", text)] = shadowed(im, 12, 80, 8)
    return _c[("cm", text)]

def prop_img(name, w):
    key = ("prop", name, w)
    if key not in _c:
        im = Image.open(arab.asset(name if name.endswith(".png") else name + ".png")).convert("RGBA"); k = w / im.width
        _c[key] = im.resize((w, max(1, int(im.height * k))), Image.LANCZOS)
    return _c[key]

def bubble_img(text, tail="left"):
    key = ("bub", text, tail)
    if key not in _c:
        lines = text.split("|"); f = SANS(40, 700); lh = 54; w = int(max(f.getlength(l) for l in lines)) + 70; h = lh * len(lines) + 50
        im = Image.new("RGBA", (w + 10, h + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((5, 5, w + 5, h + 5), 26, fill=(255, 255, 255), outline=(200, 200, 210) if LIGHT[0] else None, width=3)
        tx = 70 if tail == "left" else w - 70
        d.polygon([(tx - 22, h), (tx + 22, h), (tx + (-30 if tail == "left" else 30), h + 50)], fill=(255, 255, 255))
        for i, l in enumerate(lines): d.text((40, 30 + i * lh + lh / 2), l, font=f, fill=INK, anchor="lm")
        _c[key] = shadowed(im, 12, 90, 8)
    return _c[key]

def heart_img(s=64, col=(226, 100, 120)):
    if "heart" not in _c:
        S = 4; im = Image.new("RGBA", (s * S, s * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = s * S * 0.27
        d.ellipse((s * S * 0.5 - 2 * r, s * S * 0.1, s * S * 0.5, s * S * 0.1 + 2 * r), fill=col)
        d.ellipse((s * S * 0.5, s * S * 0.1, s * S * 0.5 + 2 * r, s * S * 0.1 + 2 * r), fill=col)
        d.polygon([(s * S * 0.5 - 2 * r + 4, s * S * 0.1 + r * 1.25), (s * S * 0.5 + 2 * r - 4, s * S * 0.1 + r * 1.25), (s * S * 0.5, s * S * 0.92)], fill=col)
        _c["heart"] = im.resize((s, s), Image.LANCZOS)
    return _c["heart"]

def pop(q):
    if q <= 0: return 0.0
    if q >= 1: return 1.0
    return 1 + 2.4 * (q - 1) ** 3 + 1.4 * (q - 1) ** 2


# ---------- scene ----------
def draw_items(base, sc, t, a):
    for it in sc.get("items", []):
        at = it.get("at", sc["start"]); k = it["kind"]
        if k == "ticks":
            for n, tt in enumerate(it["at"]):
                q = ramp(t, tt, 0.3)
                if q > 0: put(base, tick_img(n + 1), it.get("x", 420) + n * it.get("gap", 140), it.get("y", 1060), min(1, q * 2) * a, 0.5 + 0.5 * pop(q))
            continue
        q = ramp(t, at, 0.45)
        if q <= 0: continue
        e = ease(q); qa = min(1, q * 2) * a
        if k == "char":
            c = it["char"]
            for when, pose in it.get("char_at", []):
                if t >= when: c = pose
            im = char_img(c, it.get("size", 400), grey_level(it, t)); x = it.get("x", W / 2)
            y = FLOOR - im.height / 2 + 6 + (1 - e) * 30 + math.sin(t * 2.0 + x) * 3
            put(base, im, x, y, qa)
            if it.get("name"): put(base, name_tag(it["name"]), x, y - im.height / 2 - 30, qa)
            if it.get("mark") and t >= it.get("mark_at", at):
                pm = ramp(t, it.get("mark_at", at), 0.25); put(base, mark_img(it["mark"]), x + im.width * 0.35, y - im.height / 2 - 80 + math.sin(t * 6) * 4, a, 0.6 + 0.4 * pop(pm))
        elif k == "paper": put(base, paper_img(it, t), it.get("x", 330), it.get("y", 980) + (1 - e) * 40, qa)
        elif k == "door": put(base, door_img(), it.get("x", 700), FLOOR - 210, qa)
        elif k == "prop":   # furniture / a saved icon: stands on the floor ("floor": true) or hangs at y
            im = prop_img(it["img"], it.get("w", 300)); x = it.get("x", W / 2)
            y = FLOOR - im.height / 2 + it.get("sink", 8) if it.get("floor", True) else it.get("y", 800)
            put(base, im, x, y + (1 - e) * 24, qa)
        elif k == "desk":
            im = desk_img(it.get("lamp", False), it.get("cups", 0), ramp(t, it.get("lamp_at", at + 0.3), 0.6)); put(base, im, it.get("x", 560), FLOOR - 260 + 2, qa)
        elif k == "moon": put(base, moon_img(), it.get("x", 880), it.get("y", 700), qa)
        elif k == "photo": put(base, photo_img(it["img"], it.get("w", 300)), it.get("x", 300), it.get("y", 1050) + math.sin(t * 2) * 4, qa, 0.6 + 0.4 * pop(q))
        elif k == "words":   # the label drifting faintly around a character
            f = HAND(54)
            for j in range(it.get("n", 5)):
                ph = t * 0.6 + j * 1.3; x = it.get("x", 700) + math.cos(ph) * (150 + j * 20); y = it.get("y", 1150) + math.sin(ph * 1.3) * (110 + j * 12)
                lay = Image.new("RGBA", (260, 90), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((130, 45), it["text"], font=f, fill=(230, 110, 100, 255), anchor="mm")
                put(base, lay, x, y, qa * (0.35 + 0.25 * math.sin(ph * 2)))
        elif k == "bubble":   # a white speech bubble with a quote, tail pointing to the speaker
            put(base, bubble_img(it["text"], it.get("tail", "left")), it.get("x", 600), it.get("y", 900) + (1 - e) * 20, qa, 0.8 + 0.2 * pop(q))
        elif k == "comment": put(base, comment_img(it["text"]), W / 2, it.get("y", 760), qa, 0.6 + 0.4 * pop(q))
        elif k == "hearts":
            for j, (dx, dy) in enumerate([(-170, -40), (160, -10)]):
                put(base, heart_img(), it.get("x", 540) + dx, it.get("y", 900) + dy - math.sin(t * 2 + j) * 8, qa * 0.85)

def scene_at(cfg, t):
    i = 0
    for k, sc in enumerate(cfg["scenes"]):
        if t >= sc["start"]: i = k
    return i

def render_scene(cfg, page, i, t):
    sc = cfg["scenes"][i]; base = page.copy()
    if cfg.get("episode"): put(base, pill_img(cfg["episode"]), W / 2, 360)
    if sc.get("title"):
        q = ease(ramp(t, sc["start"] + 0.1, 0.4)); im = title_img(sc["title"], sc.get("tone", "yellow"))
        put(base, im, W / 2, 400 + im.height / 2 + (1 - q) * 20, q)
    if sc.get("flash"):
        f = HAND(44); lay = Image.new("RGBA", (500, 70), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((0, 35), sc["flash"], font=f, fill=(110, 110, 130) if LIGHT[0] else (200, 206, 230), anchor="lm")
        put(base, lay, 330, 640, ease(ramp(t, sc["start"] + 0.3, 0.4)) * 0.9)
    draw_items(base, sc, t, 1.0)
    if cfg.get("follow") and i == len(cfg["scenes"]) - 1:
        f = SANS(36, 700); lay = Image.new("RGBA", (800, 70), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((400, 35), cfg["follow"], font=f, fill=(80, 80, 96) if LIGHT[0] else (220, 226, 245), anchor="mm")
        put(base, lay, W / 2, FLOOR + 80, ease(ramp(t, sc["start"] + 0.6, 0.5)))
    c = cfg.get("cta")
    if c and t >= c["at"]:
        f = SANS(46, 800); txt = c.get("text", "Tekan link dekat bawah"); w = int(f.getlength(txt)) + 100
        im = card_box(w, 104, 52, fill=(247, 198, 52, 255)); ImageDraw.Draw(im).text((w / 2, 52), txt, font=f, fill=INK, anchor="mm")
        put(base, shadowed(im, 12, 90, 8), W / 2, FLOOR + 190 + math.sin(t * 5) * 5, 1, 0.7 + 0.3 * pop(ramp(t, c["at"], 0.35)))
    return base

FADE = 0.32
def frame(cfg, page, t):
    scs = cfg["scenes"]; i = scene_at(cfg, t); b = scs[i]["start"]
    if i > 0 and t < b + FADE:   # through dark: old fades down, new comes up
        p = (t - b) / FADE
        old = render_scene(cfg, page, i - 1, scs[i - 1]["end"] - 0.01); new = render_scene(cfg, page, i, t)
        dark = page.copy(); mix = Image.blend(old, dark, min(1, p * 2)) if p < 0.5 else Image.blend(dark, new, (p - 0.5) * 2)
        return mix.convert("RGB")
    return render_scene(cfg, page, i, t).convert("RGB")


# ---------- sound ----------
SR = arab.SR
def scribble():
    n = int(SR * 0.5); rng = np.random.default_rng(9); x = rng.standard_normal(n); y = np.convolve(x, np.ones(8) / 8, "same")
    e = (0.5 + 0.5 * np.sin(np.arange(n) / SR * 2 * np.pi * 12)) * np.sin(np.pi * np.arange(n) / n); return y * e * 1.3
def ding(): return arab.mix(arab.tone(1046.5, 0.35, 0.12), arab.tone(1568, 0.3, 0.1, 0.4))

def sfx_track(cfg, dur):
    tr = np.zeros(int(SR * (dur + 1))); ev = []
    for i, sc in enumerate(cfg["scenes"]):
        if i: ev.append((sc["start"] - 0.05, arab.breeze(), -30))
        if sc.get("title"): ev.append((sc["start"] + 0.12, arab.soft_pop(), -26))
        for it in sc.get("items", []):
            at = it.get("at", sc["start"])
            if it["kind"] == "ticks": ev += [(tt, ding(), -22) for tt in it["at"]]; continue
            if it["kind"] in ("words", "moon", "hearts"): continue
            if it["kind"] == "prop" and it.get("quiet", False): continue
            ev.append((at, arab.soft_pop(), -25))
            if it.get("mark"): ev.append((it.get("mark_at", at), arab.soft_pop(), -22))
            if it.get("strike_at") is not None: ev.append((it["strike_at"], scribble(), -22))
            if it.get("rewrite_at") is not None: ev.append((it["rewrite_at"], scribble(), -26))
            for when, _ in it.get("char_at", []): ev.append((when, arab.soft_pop(), -28))
    if cfg.get("cta"): ev.append((cfg["cta"]["at"], arab.chime(), -22))
    for at, s, lvl in ev:
        s = s * 10 ** (lvl / 20); i = max(0, int(at * SR)); j = min(len(tr), i + len(s)); tr[i:j] += s[: j - i]
    return np.clip(tr, -1, 1)

def main():
    prj = sys.argv[1]; arab.PRJ[0] = prj; arab.DARK[0] = True; cfg = json.load(open(os.path.join(prj, "project.json")))
    src = os.path.join(prj, cfg.get("source", "input/vo.mp4"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    LIGHT[0] = cfg.get("bg") == "dots"; NEON[0] = bool(cfg.get("neon")); page = stage(cfg.get("bg", "navy")); only = [float(x) for x in sys.argv[2:]]
    if only:
        ims = [frame(cfg, page, t).resize((360, 640)) for t in only]; cols = 4; rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (360 * cols, 640 * rows), "white")
        for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * 360, (k // cols) * 640))
        os.makedirs(os.path.join(prj, "build"), exist_ok=True); out = os.path.join(prj, "build", "stills.jpg"); sheet.save(out, quality=88); print(out); return
    os.makedirs(os.path.join(prj, "build"), exist_ok=True); os.makedirs(os.path.join(prj, "out"), exist_ok=True)
    sfx = os.path.join(prj, "build", "sfx.wav")
    with wave.open(sfx, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((sfx_track(cfg, dur) * 32767).astype("<i2").tobytes())
    out = os.path.join(prj, "out", "final.mp4"); n = int(dur * FPS) + 1
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", src, "-i", sfx, "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]",
                          "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(frame(cfg, page, k / FPS).tobytes())
        if k % 150 == 0: print(f"{k}/{n} frames", flush=True)
    p.stdin.close(); p.wait(); print(f"done: {n} frames -> {out}")

if __name__ == "__main__":
    main()
