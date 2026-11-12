"""Template motion ("guna template motion"): a clean kinetic-type explainer on a dotted-grid page.

Look (styles/template-motion.md): white page with a fine grey dot grid, soft accent glows and pale accent rings at
the edges, small four-point sparkles. The VO is the on-screen text: words land one by one as they are spoken (each
rises a little out of a blur), small dark words for the sentence and big bold accent-coloured key words. Product
pictures ride in on a phone mockup that slides up with a bounce (with a numbered step badge), or pop in as cards;
app-style icon tiles pop into dashed placeholders; a white checklist ticks items off in green. Scenes change with a
slanted accent band that wipes across the frame. Soft whoosh on every wipe, pops on entrances, a chime on the CTA.

    python motion.py projects/<name>            render out/final.mp4
    python motion.py projects/<name> 1.5 4 8    a sheet of stills at those times (build/stills.jpg)

project.json (times in seconds of the VO):
{"type": "motion", "source": "input/vo.mp4", "accent": [226, 32, 138], "accent2": [255, 178, 64],
 "scenes": [{"start": 0.0, "end": 4.2, "align": "left", "text_y": 260,
             "lines": ["Kenapa ada calon", "yang *Add Maths* dia", "*laju* je?"],
             "items": [{"kind": "phone", "img": "cover.jpg", "at": 1.2, "step": 1, "y": 1250},
                       {"kind": "card", "img": "topik.jpg", "at": 2.0, "w": 760, "y": 1200},
                       {"kind": "icons", "tiles": [{"img": "cover.jpg", "label": "Buku", "at": 1.0}, ...], "y": 1150},
                       {"kind": "checklist", "title": "Dalam buku ni", "y": 1150,
                        "rows": [["Soalan ikut topik", 2.0], ["Dwibahasa", 2.6]]},
                       {"kind": "ban", "img": "...", "at": 3.0}]}],
 "cta": {"at": 31.0, "text": "Tekan link dekat bawah"}}
In "lines", *word* (or *two words*) is a big accent key word; the rest is small. Words are timed to the spoken words of
the scene (build/words.json).
"""
import json, math, os, subprocess, sys, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import arab
from arab import SANS, card_box, ease, put, ramp, shadowed

W, H, FPS = 1080, 1920, 30
INK = (28, 28, 34)
PRJ = [""]
ACC = [(226, 32, 138), (255, 178, 64)]


# ---------- page ----------
def page(dots_gap=28, glow=True):
    """white page with a fine grey dot grid (like the user's grid paper), soft accent glows and pale rings at the edges"""
    im = Image.new("RGB", (W, H), (254, 254, 253)); d = ImageDraw.Draw(im)
    r = 2.3
    for y in np.arange(dots_gap / 2, H, dots_gap):
        for x in np.arange(dots_gap / 2, W, dots_gap):
            d.ellipse((x - r, y - r, x + r, y + r), fill=(176, 176, 178))
    im = im.convert("RGBA")
    if glow:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(lay); a = ACC[0]
        for cx, cy, rr, op in [(130, 260, 300, 22), (980, 1650, 340, 20)]:
            g.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=a + (op,))
        lay = lay.filter(ImageFilter.GaussianBlur(120)); im.alpha_composite(lay)
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(ring); pale = a + (20,)
        g.ellipse((-520, -380, 260, 400), outline=pale, width=70)
        g.ellipse((760, 1380, 1560, 2180), outline=pale, width=70)
        im.alpha_composite(ring)
    return im


def sparkle(size, color, a=1.0):
    """a four-point star"""
    S = 4; im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = size * S / 2; r = c * 0.95; w = c * 0.22
    d.polygon([(c, c - r), (c + w, c - w), (c + r, c), (c + w, c + w), (c, c + r), (c - w, c + w), (c - r, c), (c - w, c - w)], fill=color + (int(255 * a),))
    return im.resize((size, size), Image.LANCZOS)


# ---------- kinetic words ----------
SMALL, BIG = 58, 124

def parse(line):
    """'yang *Add Maths* dia' -> [('yang', False), ('Add', True), ('Maths', True), ('dia', False)]"""
    out, big = [], False
    for tok in line.split():
        start = tok.startswith("*"); end = tok.endswith("*") and (len(tok) > 1 or not start)
        word = tok.strip("*")
        if start: big = True
        if word: out.append((word, big))
        if end: big = False
    return out

def word_times(sc, words):
    """each display word gets the time it is spoken (proportional mapping when counts differ)"""
    toks = [w for line in sc["lines"] for w in parse(line)]
    spoken = [w for w in words if sc["start"] - 0.05 <= w["s"] < sc["end"] - 0.02]
    if not spoken: return [sc["start"]] * len(toks)
    return [spoken[min(len(spoken) - 1, int(i * len(spoken) / len(toks)))]["s"] for i in range(len(toks))]

_glyph = {}
def glyph(word, big, color):
    key = (word, big, color)
    if key not in _glyph:
        f = SANS(BIG if big else SMALL, 800 if big else 700)
        asc, desc = f.getmetrics(); l, _, r, _ = f.getbbox(word); t = 0; w, h = r - l + 8, asc + desc + 8   # same box per size: one baseline
        if big:   # accent gradient with a soft coloured glow
            m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).text((4 - l, 4), word, font=f, fill=255)
            grad = Image.new("RGBA", (w, h)); a1, a2 = np.array(ACC[0]), np.array(ACC[1])
            ys = np.linspace(0, 1, h)[:, None, None]; arr = (a1 * (1 - ys * 0.55) + a2 * ys * 0.55).repeat(w, 1)
            grad = Image.fromarray(np.dstack([arr, np.full((h, w, 1), 255)]).astype(np.uint8), "RGBA"); grad.putalpha(m)
            pad = 30; im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
            gl = Image.new("RGBA", im.size, ACC[0] + (0,)); gm = Image.new("L", im.size, 0); gm.paste(m, (pad, pad))
            gl.putalpha(gm.filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 70 // 255)); im.alpha_composite(gl)
            im.alpha_composite(grad, (pad, pad)); _glyph[key] = (im, pad, w, h)
        else:
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((4 - l, 4), word, font=f, fill=color)
            _glyph[key] = (im, 0, w, h)
    return _glyph[key]

def draw_text(base, sc, words, t, alpha):
    toks = [w for line in sc["lines"] for w in parse(line)]; times = sc.setdefault("_wt", word_times(sc, words))
    k = 0; y = sc.get("text_y", 230); x0 = sc.get("text_x", 90); align = sc.get("align", "left"); gap = 18
    rows = []   # each author line, wrapped so no row runs off the page
    for line in sc["lines"]:
        row = []
        for wd, big in parse(line):
            g = glyph(wd, big, INK)
            if row and sum(r[2][2] for r in row) + gap * len(row) + g[2] > W - 2 * x0:
                rows.append(row); row = []
            row.append((wd, big, g))
        rows.append(row)
    for row in rows:
        ws = [(r[0], r[1]) for r in row]; gs = [r[2] for r in row]
        lh = max(g[3] for g in gs); total = sum(g[2] for g in gs) + gap * (len(gs) - 1)
        x = (W - total) / 2 if align == "center" else x0
        for (wd, big), g in zip(ws, gs):
            im, pad, w, h = g; at = times[k]; k += 1
            p = ramp(t, at - 0.04, 0.22)
            if p > 0:
                q = ease(p); dy = (1 - q) * 26
                frame = im
                if q < 0.98: frame = im.filter(ImageFilter.GaussianBlur((1 - q) * 9))
                a = q * alpha
                if a < 1: frame = frame.copy(); frame.putalpha(frame.split()[3].point(lambda v: int(v * a)))
                base.alpha_composite(frame, (int(x - pad), int(y + (lh - h) * 0.82 - pad + dy)))
            x += w + gap
        y += lh + 10
    return y


# ---------- visuals ----------
_img = {}
def picture(name, w, h, mode="cover"):
    key = (name, w, h, mode)
    if key not in _img:
        src = Image.open(arab.asset(name)).convert("RGBA"); flat = Image.new("RGBA", src.size, (255, 255, 255, 255))
        flat.alpha_composite(src); src = flat.convert("RGB")   # transparent icons / stickman sit on white
        if mode == "cover":
            k = max(w / src.width, h / src.height); src = src.resize((int(src.width * k) + 1, int(src.height * k) + 1), Image.LANCZOS)
            src = src.crop(((src.width - w) // 2, 0, (src.width - w) // 2 + w, h))
        else:
            k = min(w / src.width, h / src.height); src = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
        _img[key] = src
    return _img[key]

def phone(img, step=None):
    """a dark phone frame with the picture on its screen and a numbered accent badge"""
    key = ("phone", img, step)
    if key not in _img:
        fw, fh = 470, 940; im = Image.new("RGBA", (fw + 60, fh + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((30, 30, 30 + fw, 30 + fh), 70, fill=(24, 24, 28)); d.rounded_rectangle((44, 44, 16 + fw, 16 + fh), 58, fill=(250, 250, 250))
        scr = picture(img, fw - 40, fh - 120, "fit"); sx = 30 + (fw - scr.width) // 2; sy = 30 + 100 + min(40, (fh - 120 - scr.height) // 6)
        im.paste(scr, (sx, sy)); d.rounded_rectangle((30 + fw / 2 - 70, 58, 30 + fw / 2 + 70, 92), 17, fill=(24, 24, 28))   # notch
        d.text((92, 74), "9:41", font=SANS(26, 700), fill=INK, anchor="lm")
        if step:
            d.ellipse((0, 0, 76, 76), fill=ACC[0]); d.text((38, 38), str(step), font=SANS(42, 800), fill="white", anchor="mm")
        _img[key] = shadowed(im, 26, 90, 18)
    return _img[key]

def tile(img, label):
    key = ("tile", img, label)
    if key not in _img:
        s = 210; im = card_box(s, s, 44); pic = picture(img, s - 40, s - 40, "fit")
        im.paste(pic, ((s - pic.width) // 2, (s - pic.height) // 2))
        sh = shadowed(im, 14, 70, 8); out = Image.new("RGBA", (sh.width, sh.height + 70), (0, 0, 0, 0)); out.alpha_composite(sh)
        ImageDraw.Draw(out).text((sh.width / 2, sh.height + 20), label, font=SANS(36, 700), fill=INK, anchor="mm")
        _img[key] = out
    return _img[key]

def dashed(s=210):
    im = Image.new("RGBA", (s + 8, s + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = ACC[0] + (150,)
    r = 44; per = 2 * (s - 2 * r) * 2 + 2 * math.pi * r; n = 34
    # a dashed rounded square: walk the outline, draw every other segment
    def at(u):
        L = u * per; e = s - 2 * r
        segs = [("l", e, (4 + r, 4), (1, 0)), ("a", math.pi / 2 * r, (4 + s - r, 4 + r), -90), ("l", e, (4 + s, 4 + r), (0, 1)),
                ("a", math.pi / 2 * r, (4 + s - r, 4 + s - r), 0), ("l", e, (4 + s - r, 4 + s), (-1, 0)),
                ("a", math.pi / 2 * r, (4 + r, 4 + s - r), 90), ("l", e, (4, 4 + s - r), (0, -1)), ("a", math.pi / 2 * r, (4 + r, 4 + r), 180)]
        for kind, ln, p0, dv in segs:
            if L <= ln:
                if kind == "l": return (p0[0] + dv[0] * L, p0[1] + dv[1] * L)
                ang = math.radians(dv) + L / r; return (p0[0] + r * math.cos(ang), p0[1] + r * math.sin(ang))
            L -= ln
        return p0
    for k in range(n):
        a0, a1 = k / n, (k + 0.55) / n
        q = [at(a0 + (a1 - a0) * j / 6) for j in range(7)]; d.line(q, fill=c, width=4)
    return im

def checklist(title, rows, t):
    w = 860; rh = 92; h = 120 + rh * len(rows); im = card_box(w, h, 34); d = ImageDraw.Draw(im)
    d.text((48, 64), title, font=SANS(40, 800), fill=ACC[0], anchor="lm")
    for i, (txt, at) in enumerate(rows):
        y = 140 + i * rh; on = t >= at; q = ease(ramp(t, at, 0.25))
        d.rounded_rectangle((40, y - 34, w - 40, y + 34), 18, fill=(248, 246, 247))
        col = tuple(int(160 + (INK[j] - 160) * q) for j in range(3))
        d.text((88, y), txt, font=SANS(38, 700), fill=col, anchor="lm")
        cx = w - 90
        if on:
            rr = 22 * (0.6 + 0.4 * q); d.ellipse((cx - rr, y - rr, cx + rr, y + rr), fill=(46, 170, 90))
            d.line([(cx - 10, y), (cx - 3, y + 8), (cx + 11, y - 9)], fill="white", width=5)
        else:
            d.ellipse((cx - 22, y - 22, cx + 22, y + 22), outline=(210, 210, 214), width=3)
        d.rounded_rectangle((60, y - 13, 72, y + 13), 4, fill=ACC[0] if on else (220, 220, 224))
    return shadowed(im, 22, 70, 12)

def figure_img(path, size):
    """a stickman pose (assets/stickman/<pose>.png) or saved character, scaled to `size` px tall, soft floor shadow"""
    key = ("fig", path, size)
    if key not in _img:
        im = Image.open(arab.asset(path + ".png")).convert("RGBA"); k = size / im.height
        im = im.resize((max(1, int(im.width * k)), size), Image.LANCZOS)
        out = Image.new("RGBA", (im.width + 60, size + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((out.width / 2 - im.width * 0.38, size + 4, out.width / 2 + im.width * 0.38, size + 30), fill=(0, 0, 0, 45))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); out.alpha_composite(im, (30, 10)); _img[key] = out
    return _img[key]

def ban(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = size // 11
    d.ellipse((w, w, size - w, size - w), outline=(226, 54, 54), width=w)
    c = size / 2; r = size / 2 - w * 1.5; a = math.radians(45)
    d.line([(c - r * math.cos(a), c - r * math.sin(a)), (c + r * math.cos(a), c + r * math.sin(a))], fill=(226, 54, 54), width=w)
    return im

def pop(q):
    """0 -> 1 with a small overshoot"""
    if q <= 0: return 0.0
    if q >= 1: return 1.0
    return 1 + 2.4 * (q - 1) ** 3 + 1.4 * (q - 1) ** 2

def draw_items(base, sc, t, alpha):
    for it in sc.get("items", []):
        at = it.get("at", sc["start"]); k = it["kind"]
        if k == "phone":
            q = ease(ramp(t, at, 0.55)); bounce = math.sin(min(1, ramp(t, at, 0.7)) * math.pi) * 18
            y = it.get("y", 1260) + (1 - q) * 900 - bounce * (q > 0.6)
            put(base, phone(it["img"], it.get("step")), it.get("x", W / 2), y + math.sin(t * 1.8) * 4, q * alpha)
        elif k == "card":
            q = ramp(t, at, 0.4); s = 0.82 + 0.18 * pop(q)
            im = sc.setdefault("_card_" + it["img"], shadowed(_framed(it["img"], it.get("w", 760), it.get("max_h", 900)), 22, 80, 12))
            put(base, im, it.get("x", W / 2), it.get("y", 1200) + math.sin(t * 1.6) * 4, min(1, q * 2) * alpha, s)
        elif k == "icons":
            ts = it["tiles"]; gapx = it.get("gap", 330); x0 = W / 2 - gapx * (len(ts) - 1) / 2; y = it.get("y", 1150)
            for j, tl in enumerate(ts):
                x = x0 + j * gapx; q = ramp(t, tl.get("at", at), 0.35)
                if q < 1: put(base, dashed(), x, y - 35, alpha * (1 - q))
                if q > 0: put(base, tile(tl["img"], tl.get("label", "")), x, y, min(1, q * 2) * alpha, 0.5 + 0.5 * pop(q))
                if j and it.get("plus", True) and q > 0:
                    pf = SANS(70, 800); pl = Image.new("RGBA", (80, 80), (0, 0, 0, 0)); ImageDraw.Draw(pl).text((40, 40), "+", font=pf, fill=ACC[0], anchor="mm")
                    put(base, pl, x - gapx / 2, y - 35, q * alpha)
        elif k == "checklist":
            q = ease(ramp(t, at, 0.45)); im = checklist(it.get("title", ""), it["rows"], t)
            put(base, im, W / 2, it.get("y", 1180) + (1 - q) * 120, q * alpha)
        elif k == "char":   # a big stickman / character with no tile: pops in, bobs, swaps pose on "char_at"
            q = ramp(t, at, 0.35); c = it["char"]
            for when, pose in it.get("char_at", []):
                if t >= when: c = pose
            im = figure_img(c, it.get("size", 420))
            put(base, im, it.get("x", W / 2), it.get("y", 1250) + math.sin(t * 2.4) * 6, min(1, q * 2) * alpha, 0.55 + 0.45 * pop(q))
        elif k == "ban":
            q = ramp(t, at, 0.35); put(base, ban(it.get("size", 300)), it.get("x", W / 2), it.get("y", 1200), min(1, q * 2) * alpha, 0.6 + 0.4 * pop(q))
    for j, (sx, sy, ss) in enumerate(sc.get("sparkles", [(150, 900, 34), (930, 820, 26), (880, 1580, 30)])):
        tw = 0.55 + 0.45 * math.sin(t * 3 + j * 2); put(base, sparkle(ss, ACC[0]), sx, sy, alpha * tw * ease(ramp(t, sc["start"] + 0.3, 0.4)))

def _framed(name, w, mh):
    pic = picture(name, w - 36, mh - 36, "fit"); box = card_box(pic.width + 36, pic.height + 36, 30)
    m = Image.new("L", pic.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pic.width - 1, pic.height - 1), 18, fill=255)
    box.paste(pic, (18, 18), m); return box


# ---------- CTA ----------
def cta(base, cfg, t):
    c = cfg.get("cta")
    if not c or t < c["at"]: return
    q = ramp(t, c["at"], 0.4); f = SANS(48, 800); txt = c.get("text", "Tekan link dekat bawah")
    w = int(f.getlength(txt)) + 110; im = card_box(w, 110, 55, fill=ACC[0] + (255,)); d = ImageDraw.Draw(im)
    d.text((w / 2, 55), txt, font=f, fill="white", anchor="mm")
    put(base, shadowed(im, 16, 80, 8), W / 2, 1700 + math.sin(t * 5) * 6, min(1, q * 2), 0.7 + 0.3 * pop(q))


# ---------- frame with slanted wipe between scenes ----------
WIPE = 0.42
def scene_at(cfg, t):
    scs = cfg["scenes"]; i = 0
    for k, sc in enumerate(scs):
        if t >= sc["start"]: i = k
    return i

def render_scene(cfg, page_im, words, i, t):
    base = page_im.copy(); sc = cfg["scenes"][i]
    end = sc["end"]; fade_out = 1 - ease(ramp(t, end - 0.12, 0.12)) if i == len(cfg["scenes"]) - 1 else 1
    draw_text(base, sc, words, t, fade_out); draw_items(base, sc, t, fade_out); cta(base, cfg, t)
    return base

def frame(cfg, page_im, words, t):
    scs = cfg["scenes"]; i = scene_at(cfg, t); new = render_scene(cfg, page_im, words, i, t)
    b = scs[i]["start"]
    if i == 0 or t > b + WIPE: return new.convert("RGB")
    old = render_scene(cfg, page_im, words, i - 1, min(t, scs[i - 1]["end"] - 0.01))
    p = ease(ramp(t, b - 0.02, WIPE)); slant = 0.42; band = 230
    edge = -band - H * slant + p * (W + band * 2 + H * slant)       # x of the band's right edge at y = 0
    yy = np.arange(H)[:, None]; xx = np.arange(W)[None, :]; e = edge + yy * slant
    show_new = (xx < e - band).astype(np.uint8) * 255; in_band = ((xx >= e - band) & (xx < e))
    out = Image.composite(new, old, Image.fromarray(show_new, "L")).convert("RGBA")
    ov = np.zeros((H, W, 4), np.uint8); a1, a2 = np.array(ACC[0]), np.array(ACC[1])
    u = np.clip((xx - (e - band)) / band, 0, 1)[..., None]; col = a1 * (1 - u * 0.5) + a2 * u * 0.5
    ov[..., :3] = np.broadcast_to(col, (H, W, 3)).astype(np.uint8); ov[..., 3] = in_band * 255
    out.alpha_composite(Image.fromarray(ov, "RGBA")); return out.convert("RGB")


# ---------- sound ----------
SR = arab.SR
def whoosh():
    n = int(SR * 0.45); rng = np.random.default_rng(5); x = rng.standard_normal(n)
    k = np.linspace(10, 120, n).astype(int); y = np.array([x[max(0, i - k[i]):i + 1].mean() for i in range(n)])
    e = np.sin(np.pi * np.arange(n) / n) ** 1.5; return y * e * 6
def tick(): return arab.mix(arab.tone(1500, 0.06, 0.015), arab.tone(2200, 0.05, 0.01, 0.4))

def sfx_track(cfg, dur):
    tr = np.zeros(int(SR * (dur + 1))); ev = []; wsh = whoosh()
    for i, sc in enumerate(cfg["scenes"]):
        if i: ev.append((sc["start"] - 0.05, wsh, -22))
        for it in sc.get("items", []):
            at = it.get("at", sc["start"])
            if it["kind"] == "phone": ev.append((at, arab.breeze(), -26)); ev.append((at + 0.45, arab.soft_pop(), -22))
            elif it["kind"] == "icons": ev += [(tl.get("at", at), arab.soft_pop(), -22) for tl in it["tiles"]]
            elif it["kind"] == "checklist": ev.append((at, arab.soft_pop(), -24)); ev += [(r[1], tick(), -20) for r in it["rows"]]
            elif it["kind"] == "char": ev.append((at, arab.soft_pop(), -21)); ev += [(w, arab.soft_pop(), -26) for w, _ in it.get("char_at", [])]
            else: ev.append((at, arab.soft_pop(), -22))
        for wt, (wd, big) in zip(word_times(sc, WORDS[0]), [w for line in sc["lines"] for w in parse(line)]):
            if big: ev.append((wt, arab.soft_pop(), -30))
    if cfg.get("cta"): ev.append((cfg["cta"]["at"], arab.chime(), -22))
    for at, s, lvl in ev:
        s = s * 10 ** (lvl / 20); i = max(0, int(at * SR)); j = min(len(tr), i + len(s)); tr[i:j] += s[: j - i]
    return np.clip(tr, -1, 1)

WORDS = [[]]
def main():
    prj = sys.argv[1]; PRJ[0] = prj; arab.PRJ[0] = prj; cfg = json.load(open(os.path.join(prj, "project.json")))
    if cfg.get("accent"): ACC[0] = tuple(cfg["accent"])
    if cfg.get("accent2"): ACC[1] = tuple(cfg["accent2"])
    words = json.load(open(os.path.join(prj, "build", "words.json"))); words = words["words"] if isinstance(words, dict) else words; WORDS[0] = words
    src = os.path.join(prj, cfg.get("source", "input/vo.mp4"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    page_im = page(cfg.get("dots_gap", 28))
    only = [float(x) for x in sys.argv[2:]]
    if only:
        ims = [frame(cfg, page_im, words, t).resize((360, 640)) for t in only]; cols = 4; rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (360 * cols, 640 * rows), "white")
        for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * 360, (k // cols) * 640))
        out = os.path.join(prj, "build", "stills.jpg"); sheet.save(out, quality=88); print(out); return
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
        p.stdin.write(frame(cfg, page_im, words, k / FPS).tobytes())
        if k % 150 == 0: print(f"{k}/{n} frames", flush=True)
    p.stdin.close(); p.wait(); print(f"done: {n} frames -> {out}")

if __name__ == "__main__":
    main()
