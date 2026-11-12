"""Template bukti ("guna template bukti"): a scrapbook evidence board on cream paper.

Look (styles/template-bukti.md): one cream, softly mottled paper page for the whole video. Every claim in the VO gets a
piece of evidence pinned to the page: torn-edge clippings of book pages / reviews with a yellow highlighter that sweeps
across the key line as it is spoken, hand-lettered sticky tags, hand-drawn charts whose points appear one by one,
red hand-drawn circles and a red rubber stamp, a stickman / character reacting in a corner, and a small source box.
Captions are one big word at a time (white, thick black outline) in the lower third. Scenes do not wipe: the old
pieces fade out quickly and the new ones pop in on the same page.

    python bukti.py projects/<name>            render out/final.mp4
    python bukti.py projects/<name> 1.5 4 8    a sheet of stills at those times (build/stills.jpg)

project.json (times in seconds of the VO):
{"type": "bukti", "source": "input/vo.mp4",
 "scenes": [{"start": 0.0, "end": 4.0, "items": [
     {"kind": "clip", "img": "ringkasan.jpg", "x": 540, "y": 520, "w": 860, "at": 0.2, "rot": -1.5,
      "marks": [[0.05, 0.42, 0.95, 0.47, 1.2]]},                                  # highlight: x0,y0,x1,y1 (0-1 of the picture), at
     {"kind": "tag", "text": "70 markah", "x": 300, "y": 1000, "at": 1.0, "color": "yellow", "rot": -4},
     {"kind": "note", "text": "Bahagian B|karangan umum", "x": 780, "y": 1000, "at": 1.4},
     {"kind": "chart", "x": 540, "y": 980, "w": 860, "h": 420, "title": "Markah karangan",
      "levels": ["A", "B", "C", "D"], "points": [["Ujian 1", "D", 2.0], ["Ujian 2", "C", 2.6]], "goal": "A"},
     {"kind": "circle", "x": 700, "y": 640, "r": 90, "at": 2.2},
     {"kind": "stamp", "text": "LULUS", "x": 600, "y": 820, "at": 3.0, "rot": -8},
     {"kind": "cross", "x": 540, "y": 600, "size": 300, "at": 2.0},
     {"kind": "char", "char": "stickman/terkejut", "x": 160, "y": 1180, "size": 260, "at": 0.5},
     {"kind": "source", "text": "Karangan Contoh dan Teknik Penulisan", "at": 0.4}]}],
 "cta": {"at": 30.0, "text": "Tekan link dekat bawah"}}
Captions come from build/words.json (one spoken word at a time); "caption_fix": {"kan?": "kan."} fixes a word.
"""
import json, math, os, subprocess, sys, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import arab
from arab import SANS, card_box, ease, put, ramp, shadowed

W, H, FPS = 1080, 1920, 30
INK = (24, 24, 26)
RED = (204, 36, 48)
HAND = lambda s: arab.font("PatrickHand-Regular.ttf", s)
TAGS = {"yellow": (247, 214, 64), "blue": (196, 222, 246), "pink": (248, 200, 210), "green": (206, 236, 196), "white": (255, 255, 255)}


# ---------- paper ----------
def paper():
    rng = np.random.default_rng(7)
    base = np.array([239, 233, 222], np.float32)
    blot = rng.normal(0, 1, (H // 24, W // 24)); blot = np.array(Image.fromarray(((blot + 3) * 40).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32)
    blot = (blot - blot.mean()) / 40 * 5
    grain = rng.normal(0, 2.2, (H, W))
    a = base[None, None, :] + (blot + grain)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")


# ---------- hand-drawn helpers ----------
def wob(pts, seed, amp=1.6, steps=10):
    """a polyline through pts with a little hand wobble"""
    rng = np.random.default_rng(seed); out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for k in range(steps):
            u = k / steps; out.append((x0 + (x1 - x0) * u + rng.normal(0, amp), y0 + (y1 - y0) * u + rng.normal(0, amp)))
    out.append(pts[-1]); return out

def hand_box(d, box, width=4, seed=1, fill=None, color=INK):
    x0, y0, x1, y1 = box
    if fill: d.rectangle(box, fill=fill)
    d.line(wob([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], seed), fill=color, width=width, joint="curve")

def rotate(im, deg):
    return im.rotate(deg, resample=Image.BICUBIC, expand=True) if deg else im


# ---------- pieces ----------
_c = {}
def pic(name):
    if name not in _c:
        src = Image.open(arab.asset(name)).convert("RGBA"); flat = Image.new("RGBA", src.size, (255, 255, 255, 255))
        flat.alpha_composite(src); _c[name] = flat.convert("RGB")
    return _c[name]

def torn(w, h, seed):
    """an alpha mask with ragged top and bottom edges"""
    rng = np.random.default_rng(seed); m = Image.new("L", (w, h), 0); d = ImageDraw.Draw(m)
    top = [(x, 10 + rng.uniform(-7, 7)) for x in range(0, w + 12, 12)]; bot = [(x, h - 10 + rng.uniform(-7, 7)) for x in range(w + 12, -12, -12)]
    d.polygon(top + bot, fill=255); return m

def clip_img(it, t):
    """a torn paper clipping of a picture, with highlighter strokes that sweep in on time"""
    name, w = it["img"], it.get("w", 820); src = pic(name); k = w / src.width; h = int(src.height * k)
    if h > it.get("max_h", 900): k = it.get("max_h", 900) / src.height; w, h = int(src.width * k), it.get("max_h", 900)
    key = ("clip", name, w, h)
    if key not in _c: _c[key] = src.resize((w, h), Image.LANCZOS)
    im = _c[key].copy().convert("RGBA")
    if it.get("marks"):
        hl = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dh = ImageDraw.Draw(hl)
        for m in it["marks"]:   # [x0, y0, x1, y1, at] yellow highlighter; a 6th item "red" marks a mistake instead
            x0, y0, x1, y1, at = m[:5]; p = ease(ramp(t, at, 0.45))
            col = (236, 64, 64, 95) if len(m) > 5 and m[5] == "red" else (255, 226, 40, 120)
            if p > 0: dh.rectangle((x0 * w, y0 * h, x0 * w + (x1 - x0) * w * p, y1 * h), fill=col)
        im = Image.alpha_composite(im, hl)
    pad = 16; card = Image.new("RGBA", (w + pad * 2, h + pad * 2 + 20), (0, 0, 0, 0))
    paperw = Image.new("RGBA", card.size, (252, 251, 247, 255)); paperw.putalpha(torn(card.width, card.height, hash(name) % 997))
    card.alpha_composite(paperw); card.alpha_composite(im, (pad, pad + 10))
    tape = Image.new("RGBA", (150, 44), (236, 226, 196, 190)); card.alpha_composite(rotate(tape, -6), (card.width // 2 - 80, -2))
    return shadowed(rotate(card, it.get("rot", 0)), 14, 70, 8)

def tag_img(text, color="yellow", size=56, rot=0):
    key = ("tag", text, color, size, rot)
    if key not in _c:
        f = HAND(size); tw = int(f.getlength(text)); w, h = tw + 44, int(size * 1.3)
        im = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        hand_box(d, (5, 5, w + 3, h + 3), 3, seed=len(text), fill=TAGS.get(color, color))
        d.text(((w + 8) / 2, (h + 8) / 2), text, font=f, fill=INK, anchor="mm")
        _c[key] = shadowed(rotate(im, rot), 6, 50, 4)
    return _c[key]

def note_img(text, size=48, rot=0):
    key = ("note", text, size, rot)
    if key not in _c:
        lines = text.split("|"); f = HAND(size); tw = max(int(f.getlength(l)) for l in lines); lh = int(size * 1.15)
        w, h = tw + 60, lh * len(lines) + 44; im = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        hand_box(d, (5, 5, w + 3, h + 3), 3, seed=len(text) + 3, fill=(255, 253, 246))
        for i, l in enumerate(lines): d.text(((w + 8) / 2, 27 + lh * i + lh / 2), l, font=f, fill=INK, anchor="mm")
        _c[key] = shadowed(rotate(im, rot), 8, 55, 5)
    return _c[key]

def stamp_img(text, size=84, rot=-8):
    key = ("stamp", text, size, rot)
    if key not in _c:
        f = SANS(size, 800); tw = int(f.getlength(text)); w, h = tw + 70, int(size * 1.55)
        im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((10, 10, w + 10, h + 10), 14, outline=RED + (235,), width=8)
        d.rounded_rectangle((20, 20, w, h), 8, outline=RED + (200,), width=3)
        d.text(((w + 20) / 2, (h + 20) / 2), text, font=f, fill=RED + (235,), anchor="mm")
        rng = np.random.default_rng(len(text)); a = np.array(im.split()[3]).astype(np.float32)
        a *= (rng.random(a.shape) > 0.12) * 0.25 + 0.75     # worn ink
        im.putalpha(Image.fromarray(a.astype(np.uint8))); _c[key] = rotate(im, rot)
    return _c[key]

def circle_on(base, x, y, r, p, seed=3):
    """a red hand-drawn ring drawn on over ~0.5 s (p 0..1)"""
    if p <= 0: return
    d = ImageDraw.Draw(base); rng = np.random.default_rng(seed); n = 60; span = 2 * math.pi * 1.12 * p
    pts = [(x + (r + rng.normal(0, 2)) * math.cos(-1.9 + span * k / n) * 1.12, y + (r + rng.normal(0, 2)) * math.sin(-1.9 + span * k / n)) for k in range(n + 1)]
    d.line(pts, fill=RED, width=7, joint="curve")

def cross_on(base, x, y, s, p):
    if p <= 0: return
    d = ImageDraw.Draw(base); h = s / 2
    a = min(1, p * 2); d.line(wob([(x - h, y - h), (x - h + 2 * h * a, y - h + 2 * h * a)], 5, 1.2, 6), fill=RED, width=12)
    if p > 0.5:
        b = (p - 0.5) * 2; d.line(wob([(x + h, y - h), (x + h - 2 * h * b, y - h + 2 * h * b)], 6, 1.2, 6), fill=RED, width=12)

def chart_img(it, t):
    """a hand-drawn chart: levels on the left, points appear one by one and join with a red line"""
    w, h = it.get("w", 860), it.get("h", 440); im = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    hand_box(d, (5, 5, w, h), 4, seed=11, fill=(250, 247, 238))
    d.text((40, 42), it.get("title", ""), font=HAND(46), fill=INK, anchor="lm")
    lv = it["levels"]; top, bot, left, right = 110, h - 70, 110, w - 50
    ys = {l: top + (bot - top) * i / max(1, len(lv) - 1) for i, l in enumerate(lv)}
    d.line(wob([(left - 20, top - 20), (left - 20, bot + 20), (right, bot + 20)], 12), fill=INK, width=4)
    for l, y in ys.items():
        d.text((left - 50, y), l, font=HAND(42), fill=INK, anchor="mm")
        for x in range(left, right, 22): d.line((x, y, x + 10, y), fill=(200, 194, 182), width=2)
    if it.get("goal") in ys: d.text((right - 10, ys[it["goal"]] - 26), "sasaran", font=HAND(30), fill=RED, anchor="rm")
    pts = it["points"]; xs = [left + 60 + (right - left - 120) * (i / max(1, len(pts) - 1)) for i in range(len(pts))]
    shown = [(x, ys[lvl], lab, at) for x, (lab, lvl, at) in zip(xs, pts) if t >= at]
    if len(shown) > 1: d.line([(x, y) for x, y, _, _ in shown], fill=RED, width=6, joint="curve")
    for x, y, lab, at in shown:
        q = ease(ramp(t, at, 0.25)); r = 16 * (0.4 + 0.6 * q)
        d.ellipse((x - r, y - r, x + r, y + r), fill=RED, outline=INK, width=3)
        d.text((x, bot + 46), lab, font=HAND(30), fill=INK, anchor="mm")
    return shadowed(im, 12, 60, 8)

def source_img(text):
    key = ("src", text)
    if key not in _c:
        f = SANS(28, 600); w = int(f.getlength(text)) + 40; im = card_box(w, 52, 6, fill=(248, 245, 238, 255)); d = ImageDraw.Draw(im)
        d.text((20, 26), text, font=f, fill=(90, 86, 80), anchor="lm"); _c[key] = im
    return _c[key]

def pop(q):
    if q <= 0: return 0.0
    if q >= 1: return 1.0
    return 1 + 2.4 * (q - 1) ** 3 + 1.4 * (q - 1) ** 2

def figure(path, size):
    key = ("fig", path, size)
    if key not in _c:
        im = Image.open(arab.asset(path + ".png")).convert("RGBA"); k = size / im.height
        _c[key] = shadowed(im.resize((max(1, int(im.width * k)), size), Image.LANCZOS), 8, 40, 6)
    return _c[key]


# ---------- captions: one big word at a time ----------
def caption(base, word, t0, t):
    key = ("cap", word)
    if key not in _c:
        f = SANS(96, 800); tw = int(f.getlength(word)); im = Image.new("RGBA", (tw + 60, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((30, 75), word, font=f, fill=(255, 255, 255), anchor="lm", stroke_width=9, stroke_fill=INK)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(5)).point(lambda v: v * 90 // 255))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 6)); out.alpha_composite(im); _c[key] = out
    q = ramp(t, t0, 0.12); put(base, _c[key], W / 2, CAP_Y[0], 1.0, 0.85 + 0.15 * pop(q))


# ---------- frame ----------
CAP_Y = [1560]
def scene_index(cfg, t):
    i = 0
    for k, sc in enumerate(cfg["scenes"]):
        if t >= sc["start"]: i = k
    return i

def draw_scene(base, sc, t, alpha):
    for it in sc.get("items", []):
        at = it.get("at", sc["start"]); k = it["kind"]; q = ramp(t, at, 0.3)
        if q <= 0: continue
        a = min(1, q * 2.5) * alpha; s = 0.6 + 0.4 * pop(q); x, y = it.get("x", W / 2), it.get("y", 700)
        if k == "clip": put(base, clip_img(it, t), x, y, a, 0.85 + 0.15 * pop(q))
        elif k == "tag": put(base, tag_img(it["text"], it.get("color", "yellow"), it.get("size", 56), it.get("rot", -3)), x, y, a, s)
        elif k == "note": put(base, note_img(it["text"], it.get("size", 46), it.get("rot", 0)), x, y, a, s)
        elif k == "chart": put(base, chart_img(it, t), x, y, a, 0.9 + 0.1 * pop(q))
        elif k == "stamp":   # slams down: big and faint -> normal
            qq = ramp(t, at, 0.18); put(base, stamp_img(it["text"], it.get("size", 84), it.get("rot", -8)), x, y, min(1, qq * 1.5) * alpha, 1.6 - 0.6 * ease(qq))
        elif k == "circle":
            if alpha > 0.5: circle_on(base, x, y, it.get("r", 90), ease(ramp(t, at, 0.5)), it.get("seed", 3))
        elif k == "cross":
            if alpha > 0.5: cross_on(base, x, y, it.get("size", 260), ease(ramp(t, at, 0.4)))
        elif k == "char":
            c = it["char"]
            for when, pose in it.get("char_at", []):
                if t >= when: c = pose
            put(base, figure(c, it.get("size", 260)), x, y + math.sin(t * 2.6) * 4, a, s)
        elif k == "source":
            im = source_img(it["text"]); put(base, im, it.get("x", 50 + im.width / 2), it.get("y", 1790), a)

def frame(cfg, page, words, t):
    base = page.copy(); i = scene_index(cfg, t); scs = cfg["scenes"]
    if i > 0 and t < scs[i]["start"] + 0.2:   # the previous board fades out quickly
        draw_scene(base, scs[i - 1], scs[i - 1]["end"] - 0.01, 1 - ramp(t, scs[i]["start"], 0.2))
    draw_scene(base, scs[i], t, 1.0)
    c = cfg.get("cta")
    if c and t >= c["at"]:
        f = SANS(48, 800); txt = c.get("text", "Tekan link dekat bawah"); w = int(f.getlength(txt)) + 110
        im = card_box(w, 110, 55, fill=RED + (255,)); ImageDraw.Draw(im).text((w / 2, 55), txt, font=f, fill="white", anchor="mm")
        put(base, shadowed(im, 14, 70, 8), W / 2, 1360 + math.sin(t * 5) * 5, 1.0, 0.7 + 0.3 * pop(ramp(t, c["at"], 0.35)))
    fix = cfg.get("caption_fix", {})
    cur = [w for w in words if w["s"] <= t + 0.02]
    if cur and t - cur[-1]["s"] < 1.4 and t < cur[-1].get("e", cur[-1]["s"] + 0.6) + 0.5:
        wd = fix.get(cur[-1]["w"], cur[-1]["w"]).strip()
        if wd: caption(base, wd, cur[-1]["s"], t)
    return base.convert("RGB")


# ---------- sound ----------
SR = arab.SR
def thud(): return arab.mix(arab.tone(110, 0.25, 0.06, 1.0), arab.tone(220, 0.12, 0.03, 0.5))
def scribble():
    n = int(SR * 0.4); rng = np.random.default_rng(9); x = rng.standard_normal(n); y = np.convolve(x, np.ones(8) / 8, "same")
    e = (0.5 + 0.5 * np.sin(np.arange(n) / SR * 2 * np.pi * 14)) * np.sin(np.pi * np.arange(n) / n); return y * e * 1.4

def sfx_track(cfg, dur):
    tr = np.zeros(int(SR * (dur + 1))); ev = []
    for sc in cfg["scenes"]:
        for it in sc.get("items", []):
            at = it.get("at", sc["start"]); k = it["kind"]
            if k == "stamp": ev.append((at + 0.12, thud(), -16))
            elif k in ("circle", "cross"): ev.append((at, scribble(), -24))
            elif k == "source": continue
            else: ev.append((at, arab.soft_pop(), -22))
            for m in it.get("marks", []): ev.append((m[4], scribble(), -27))
            for p in it.get("points", []): ev.append((p[2], arab.soft_pop(), -24))
            for when, _ in it.get("char_at", []): ev.append((when, arab.soft_pop(), -26))
    if cfg.get("cta"): ev.append((cfg["cta"]["at"], arab.chime(), -22))
    for at, s, lvl in ev:
        s = s * 10 ** (lvl / 20); i = max(0, int(at * SR)); j = min(len(tr), i + len(s)); tr[i:j] += s[: j - i]
    return np.clip(tr, -1, 1)

def main():
    prj = sys.argv[1]; arab.PRJ[0] = prj; cfg = json.load(open(os.path.join(prj, "project.json")))
    words = json.load(open(os.path.join(prj, "build", "words.json"))); words = words["words"] if isinstance(words, dict) else words
    if cfg.get("caption_y"): CAP_Y[0] = cfg["caption_y"]
    src = os.path.join(prj, cfg.get("source", "input/vo.mp4"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    page = paper(); only = [float(x) for x in sys.argv[2:]]
    if only:
        ims = [frame(cfg, page, words, t).resize((360, 640)) for t in only]; cols = 4; rows = (len(ims) + cols - 1) // cols
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
        p.stdin.write(frame(cfg, page, words, k / FPS).tobytes())
        if k % 150 == 0: print(f"{k}/{n} frames", flush=True)
    p.stdin.close(); p.wait(); print(f"done: {n} frames -> {out}")

if __name__ == "__main__":
    main()
