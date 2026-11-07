"""Template arab (styles/template-arab.md): a calm explainer on plain paper. One slow flat illustration at a time
(a simple drawn figure, flat icons), white cards at the top (a product photo, or a "KATA KUNCI" key-word card),
small source pills, and a white subtitle card at the bottom whose words darken as they are spoken (key words orange).
Soft fades between scenes, quiet sounds on every entrance.

    python arab.py projects/<name>          -> projects/<name>/out/final.mp4

project.json: {"type": "arab", "source": "input/vo.mp4", "bg": "putih" | "krim",
  "scenes": [{"start": 0.0, "end": 3.8, "line": "Kenapa ada pelajar ...?", "keys": ["senang"],
              "illus": {"kind": "ask"}, "card": {"kind": "photo", "img": "cover.jpg"} | {"kind": "key", ...},
              "pills": [["UPSA", 25.7]], "label": "Ibnu Kathir"}, ...],
  "cta": {"at": 31.3, "text": "Tekan link dekat bawah"}}
Times are VO seconds; word timings come from build/words.json (transcribe.py).
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
NAVY, ORANGE, SKY, BROWN, BRICK = (36, 44, 78), (232, 137, 43), (186, 214, 240), (122, 84, 56), (205, 92, 64)
INK, FAINT = (44, 44, 58), (196, 191, 182)
BG = {"putih": (251, 250, 247), "krim": (243, 235, 221)}

def font(name, size): return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
def SANS(s, w=800):
    f = font("PlusJakartaSans.ttf", s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f

def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def ease_io(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def ramp(t, a, d): return min(max((t - a) / d, 0.0), 1.0) if d > 0 else float(t >= a)

# ---------- paper ----------
def background(kind):
    c = BG.get(kind, BG["putih"]); rng = np.random.default_rng(2)
    a = np.full((H, W, 3), c, np.float32) + rng.normal(0, 1.4, (H, W, 1))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 26, W - 27, H - 27), 30, outline=(226, 220, 208), width=2)   # thin frame
    for y in (26, H - 27): d.ellipse((W / 2 - 7, y - 7, W / 2 + 7, y + 7), fill=ORANGE)    # orange dots, top and bottom
    return im

def shadowed(img, r=18, op=60, dy=10):
    pad = r * 3; sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    m = Image.new("L", sh.size, 0); m.paste(img.split()[3], (pad, pad + dy))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(r)).point(lambda v: v * op // 255))
    sh.alpha_composite(img, (pad, pad)); return sh

def card_box(w, h, rad=28, fill=(255, 255, 255, 255), outline=None, width=0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), rad, fill=fill, outline=outline, width=width)
    return im

def put(base, img, cx, cy, a=1.0, scale=1.0):
    if a <= 0: return
    if scale != 1.0: img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    if a < 1:
        img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * a)))
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))

# ---------- the figure (drawn at 2x, then reduced, for smooth lines) ----------
def figure(color=NAVY, pose="down", mood="smile", size=300, t=0.0, cap=True):
    S = 2; w, h = int(size * 0.8) * S, int(size * 1.25) * S; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    u = size * S / 300; cx = w / 2; lw = int(5 * u)
    hy, hr = 70 * u, 34 * u                                  # head
    by0, by1 = hy + hr + 8 * u, 250 * u                       # robe
    # legs
    for dx in (-16, 16): d.line((cx + dx * u, by1 - 4 * u, cx + dx * u, by1 + 62 * u), fill=INK, width=lw)
    # arms (behind the robe for "down", raised / waving / pointing otherwise)
    sy = by0 + 26 * u; wav = math.sin(t * 7) * 14
    # each arm: (shoulder side, hand dx, hand dy) in figure units, hand relative to the shoulder
    arms = {"down": [(-1, -34, 70), (1, 34, 70)], "up": [(-1, -48, -62), (1, 48, -62)],
            "wave": [(-1, -34, 70), (1, 52 + wav * 0.3, -60 + wav)], "point": [(-1, -34, 70), (1, 78, -22)],
            "think": [(-1, -34, 70), (1, 6, -40)]}[pose]
    for side, hx, hy_ in arms:
        x0 = cx + side * 22 * u; d.line((x0, sy, x0 + hx * u, sy + hy_ * u), fill=INK, width=lw)
    d.polygon([(cx - 26 * u, by0), (cx + 26 * u, by0), (cx + 50 * u, by1), (cx - 50 * u, by1)], fill=color)
    d.rounded_rectangle((cx - 50 * u, by1 - 10 * u, cx + 50 * u, by1), int(4 * u), fill=color)
    # head
    d.ellipse((cx - hr, hy - hr, cx + hr, hy + hr), fill=(255, 255, 255), outline=INK, width=lw)
    if cap: d.chord((cx - hr + 2 * u, hy - hr - 2 * u, cx + hr - 2 * u, hy + hr * 0.6), 180, 360, fill=INK)
    ey = hy + 2 * u
    for dx in (-12, 12): d.ellipse((cx + dx * u - 4 * u, ey - 4 * u, cx + dx * u + 4 * u, ey + 4 * u), fill=INK)
    my = hy + 16 * u
    if mood == "smile": d.arc((cx - 12 * u, my - 8 * u, cx + 12 * u, my + 6 * u), 20, 160, fill=INK, width=int(3 * u))
    elif mood == "worry": d.arc((cx - 10 * u, my + 2 * u, cx + 10 * u, my + 14 * u), 200, 340, fill=INK, width=int(3 * u))
    else: d.line((cx - 8 * u, my + 4 * u, cx + 8 * u, my + 4 * u), fill=INK, width=int(3 * u))
    return im.resize((w // S, h // S), Image.LANCZOS)

# ---------- small flat props ----------
def qmark(size, color=ORANGE):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); f = SANS(int(size * 0.9), 800)
    ImageDraw.Draw(im).text((size / 2, size / 2), "?", font=f, fill=color, anchor="mm"); return im

def book_icon(w, label, color=NAVY):
    h = int(w * 0.32); im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w, h), 8, fill=color); d.rectangle((0, h - 12, w, h - 6), fill=(255, 255, 255))
    d.text((w / 2, h / 2 - 4), label, font=HAND(int(h * 0.55)), fill=(255, 255, 255), anchor="mm"); return im

def hourglass(size, p):
    S = 2; w, h = int(size * 0.62) * S, size * S; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    m = 14 * S; cx = w / 2; top, bot = m + 10 * S, h - m - 10 * S; mid = h / 2
    d.rounded_rectangle((0, 0, w, m), 5 * S, fill=BROWN); d.rounded_rectangle((0, h - m, w, h), 5 * S, fill=BROWN)
    glass = [(m, top), (w - m, top), (cx + 8 * S, mid), (w - m, bot), (m, bot), (cx - 8 * S, mid)]
    d.polygon(glass, fill=(232, 240, 248))
    p = min(max(p, 0), 1); lvl_top = top + (mid - top) * (0.15 + 0.85 * p)   # upper sand drops
    if lvl_top < mid - 2:
        k = (lvl_top - top) / (mid - top); hw = (w / 2 - m) * (1 - k) + 8 * S * k
        d.polygon([(cx - hw, lvl_top), (cx + hw, lvl_top), (cx + 8 * S, mid), (cx - 8 * S, mid)], fill=ORANGE)
    pile = (bot - mid) * (0.1 + 0.8 * p)
    d.polygon([(m + 6 * S, bot), (w - m - 6 * S, bot), (cx, bot - pile)], fill=ORANGE)
    if p < 0.98: d.line((cx, mid, cx, bot - pile), fill=ORANGE, width=3 * S)
    d.polygon(glass, outline=NAVY, width=3 * S)
    return im.resize((w // S, h // S), Image.LANCZOS)

def star(r, color=ORANGE):
    im = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    pts = [(r + r * (1 if i % 2 == 0 else 0.45) * math.sin(i * math.pi / 5), r - r * (1 if i % 2 == 0 else 0.45) * math.cos(i * math.pi / 5)) for i in range(10)]
    ImageDraw.Draw(im).polygon(pts, fill=color); return im

def rays(r, t, color=(240, 196, 140)):
    S = 2; im = Image.new("RGBA", (r * 2 * S, r * 2 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = r * S
    for i in range(14):
        a = i * math.pi * 2 / 14 + t * 0.15; r0, r1 = r * S * 0.55, r * S * (0.85 + 0.08 * math.sin(t * 2 + i))
        d.line((c + math.cos(a) * r0, c + math.sin(a) * r0, c + math.cos(a) * r1, c + math.sin(a) * r1), fill=color, width=3 * S)
    return im.resize((r * 2, r * 2), Image.LANCZOS)

def pill(text, size=34, fg=INK, bg=(255, 255, 255), dot=None):
    f = HAND(size); tw = f.getlength(text); pad = int(size * 0.7); dw = size * 0.6 if dot else 0
    im = card_box(int(tw + pad * 2 + dw), int(size * 1.55), int(size * 0.78), fill=bg + (255,), outline=(226, 220, 208), width=2)
    d = ImageDraw.Draw(im)
    if dot: d.ellipse((pad - 4, im.height / 2 - 6, pad + 8, im.height / 2 + 6), fill=dot)
    d.text((pad + dw, im.height / 2), text, font=f, fill=fg, anchor="lm"); return shadowed(im, 8, 35, 3)

# ---------- illustrations ----------
def illus(base, sc, t):
    k = sc["illus"]["kind"]; a = ease(ramp(t, sc["start"], 0.45)) * (1 - ease(ramp(t, sc["end"] - 0.35, 0.35)))
    if a <= 0: return
    lt = t - sc["start"]; cy = sc["illus"].get("y", 900 if sc.get("card") else 860); bob = math.sin(t * 2.2) * 5
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); I = sc["illus"]
    if k == "ask":
        mood = "smile" if lt > I.get("smile_at", 99) - sc["start"] else "plain"
        put(layer, figure(I.get("color", NAVY), I.get("pose", "think"), mood, 420, t), W / 2, cy + 40 + bob)
        for i, (dx, dy, s) in enumerate([(-150, -250, 110), (0, -320, 150), (150, -250, 110)]):
            q = ease(ramp(lt, 0.4 + i * 0.25, 0.35))
            put(layer, qmark(s), W / 2 + dx, cy + dy + math.sin(t * 3 + i) * 6, q, 0.6 + 0.4 * q)
    elif k == "stairs":
        n = I.get("steps", 3); x0, base_y, sw, sh = 250, cy + 210, 190, 90
        d = ImageDraw.Draw(layer)
        for i in range(n):
            d.rectangle((x0 + i * sw, base_y - (i + 1) * sh, x0 + (i + 1) * sw, base_y), fill=SKY)
            lab = I.get("labels", ["T1", "T2", "T3"])[i]
            d.text((x0 + i * sw + sw / 2, base_y - (i + 1) * sh + sh / 2), lab, font=HAND(46), fill=NAVY, anchor="mm")
        # the figure climbs one step per beat
        k_ = min(n - 1, max(0, int((lt - I.get("climb_at", 0.4)) / I.get("beat", 0.9)) if lt > I.get("climb_at", 0.4) else 0))
        frac = ease_io(((lt - I.get("climb_at", 0.4)) / I.get("beat", 0.9)) % 1) if lt > I.get("climb_at", 0.4) and k_ < n - 1 else 0
        k_ = min(k_ + frac, n - 1) if I.get("climb", True) else I.get("at_step", 0)
        fx_ = x0 + k_ * sw + sw / 2; fy = base_y - (math.floor(k_) + 1) * sh - (frac * sh if k_ < n - 1 else 0) - 125
        put(layer, figure(ORANGE, I.get("pose", "down"), "smile", 230, t), fx_, fy - abs(math.sin(frac * math.pi)) * 25)
        if k_ >= n - 1: put(layer, star(36), x0 + n * sw - 40, base_y - n * sh - 250 + bob, ease(ramp(lt, 2.0, 0.4)))
    elif k == "hourglass":
        p = ramp(lt, 0.2, (sc["end"] - sc["start"]) * 0.95)
        put(layer, hourglass(440, p), W / 2 + 170, cy)
        run = math.sin(t * 9) * 8
        put(layer, figure(NAVY, "point", "worry", 330, t), W / 2 - 200 + run * 0.3, cy + 50 + abs(run))
    elif k == "books":
        put(layer, figure(NAVY, "up", "worry", 320, t), W / 2, cy + 190)
        for i, lab in enumerate(I.get("labels", ["Tingkatan 1", "Tingkatan 2", "Tingkatan 3"])):
            q = ease(ramp(lt, 0.3 + i * 0.45, 0.4)); y = cy - 40 - i * 112 - (1 - q) * 380
            put(layer, book_icon(400, lab, [NAVY, (64, 92, 150), ORANGE][i]), W / 2 + (i - 1) * 12, y, q)
        if I.get("cal_at") and lt > I["cal_at"] - sc["start"]:
            cal = card_box(170, 150, 18, outline=NAVY, width=4); dc = ImageDraw.Draw(cal)
            dc.rectangle((2, 2, 167, 42), fill=BRICK); dc.text((85, 98), "1 bulan", font=HAND(40), fill=INK, anchor="mm")
            put(layer, shadowed(cal, 8, 40, 4), W / 2 + 290, cy + 120 + bob, ease(ramp(lt, I["cal_at"] - sc["start"], 0.35)))
    elif k == "path":
        n = I.get("nodes", 8); pts = []
        for i in range(n):   # a gentle S path of chapter dots
            u = i / (n - 1); pts.append((170 + u * 740, cy + 60 + math.sin(u * math.pi * 2) * 120))
        d = ImageDraw.Draw(layer)
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            for s in np.linspace(0, 1, 9)[:-1]: d.ellipse((xa + (xb - xa) * s - 4, ya + (yb - ya) * s - 4, xa + (xb - xa) * s + 4, ya + (yb - ya) * s + 4), fill=FAINT)
        prog = ramp(lt, 0.4, (sc["end"] - sc["start"]) * 0.8) * (n - 1)
        for i, (x, y) in enumerate(pts):
            on = i <= prog; r = 30
            d.ellipse((x - r, y - r, x + r, y + r), fill=ORANGE if on else (255, 255, 255), outline=ORANGE, width=4)
            d.text((x, y), str(i + 1), font=SANS(30, 800), fill=(255, 255, 255) if on else ORANGE, anchor="mm")
        i0 = int(prog); fr = prog - i0; xa, ya = pts[i0]; xb, yb = pts[min(i0 + 1, n - 1)]
        put(layer, figure(ORANGE, "down", "smile", 240, t), xa + (xb - xa) * fr, ya + (yb - ya) * fr - 160 - abs(math.sin(fr * math.pi)) * 18)
    elif k == "glow":
        put(layer, rays(320, t), W / 2, cy - 10, ease(ramp(lt, 0.2, 0.6)))
        put(layer, figure(ORANGE, I.get("pose", "up"), "smile", 420, t), W / 2, cy + bob)
        for i, w_ in enumerate(I.get("words", [])):
            q = ease(ramp(t, w_[1], 0.35))
            put(layer, pill(w_[0], 40, fg=NAVY, dot=ORANGE), W / 2 + (i - (len(I["words"]) - 1) / 2) * 320, cy + 360, q)
    elif k == "wave":
        put(layer, figure(NAVY, "wave", "smile", 300, t), W / 2 - 230, cy + 60 + bob)
    base.alpha_composite(Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 0)), layer, 1.0) if a >= 1 else fade(layer, a))

def fade(img, a):
    img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * a))); return img

# ---------- top cards ----------
_cache = {}
def top_card(sc, prj):
    c = sc["card"]; key = json.dumps(c)
    if key in _cache: return _cache[key]
    if c["kind"] == "photo":
        im = Image.open(os.path.join(prj, "input", c["img"])).convert("RGB"); w = c.get("w", 560)
        h = int(im.height * w / im.width); mh = c.get("max_h", 640)
        if h > mh: w, h = int(w * mh / h), mh
        im = im.resize((w, h), Image.LANCZOS); pad = 18
        box = card_box(w + pad * 2, h + pad * 2, 26)
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 14, fill=255)
        box.paste(im, (pad, pad), m); out = shadowed(box, 16, 55, 8)
    else:   # "key": small orange label, big word, meaning
        f1, f2, f3 = SANS(24, 700), SANS(c.get("size", 92), 800), HAND(40)
        w = int(max(f2.getlength(c["word"]), f3.getlength(c.get("sub", ""))) + 110)
        box = card_box(w, 300, 22, outline=NAVY, width=4); d = ImageDraw.Draw(box)
        d.text((w / 2, 52), " ".join(c.get("label", "KATA KUNCI")), font=f1, fill=ORANGE, anchor="mm")
        d.text((w / 2, 150), c["word"], font=f2, fill=NAVY, anchor="mm")
        d.text((w / 2, 240), c.get("sub", ""), font=f3, fill=INK, anchor="mm")
        out = shadowed(box, 12, 45, 6)
    _cache[key] = out; return out

def scene_dots(base, i, n, a):
    d = ImageDraw.Draw(base); x0 = W / 2 - (n - 1) * 11
    for k in range(n):
        col = ORANGE if k == i else (214, 208, 196)
        c = Image.new("RGBA", (16, 16), (0, 0, 0, 0)); ImageDraw.Draw(c).ellipse((0, 0, 15, 15), fill=col)
        put(base, c, x0 + k * 22, 160, a)

# ---------- subtitle card ----------
def tokens(sc, words):
    toks = sc["line"].split(); spoken = [w for w in words if sc["start"] - 0.05 <= w["s"] < sc["end"] - 0.02]
    if not spoken: return [(tk, sc["start"]) for tk in toks]
    out = []
    for i, tk in enumerate(toks):   # map tokens onto spoken word times (proportional when counts differ)
        j = min(len(spoken) - 1, int(i * len(spoken) / len(toks)))
        out.append((tk, spoken[j]["s"]))
    return out

def sub_card(base, sc, toks, t, a):
    f = HAND(54); maxw = 860; keys = set(k.lower() for k in sc.get("keys", []))
    keyset = set()
    for k in keys: keyset.update(w.strip(".,?!") for w in k.split())
    lines, cur, cw = [], [], 0
    for tk, ts in toks:
        tw = f.getlength(tk + " ")
        if cur and cw + tw > maxw: lines.append(cur); cur, cw = [], 0
        cur.append((tk, ts)); cw += tw
    if cur: lines.append(cur)
    lh = 70; ch = lh * len(lines) + 70; card = card_box(maxw + 90, ch, 24); d = ImageDraw.Draw(card)
    for li, ln in enumerate(lines):
        tot = sum(f.getlength(tk + " ") for tk, _ in ln) - f.getlength(" "); x = (card.width - tot) / 2; y = 35 + li * lh + lh / 2
        for tk, ts in ln:
            k = tk.lower().strip(".,?!\"") in keyset; on = t >= ts - 0.05
            col = (ORANGE if on else (240, 200, 160)) if k else (INK if on else FAINT)
            d.text((x, y), tk, font=f, fill=col, anchor="lm"); x += f.getlength(tk + " ")
    put(base, shadowed(card, 14, 40, 6), W / 2, 1500, a)

def cta_button(base, cfg, t):
    c = cfg.get("cta")
    if not c or t < c["at"]: return
    q = ease(ramp(t, c["at"], 0.4)); f = SANS(44, 800); tw = f.getlength(c.get("text", "Tekan link dekat bawah"))
    b = card_box(int(tw + 110), 100, 50, fill=ORANGE + (255,)); ImageDraw.Draw(b).text((b.width / 2, 50), c.get("text", "Tekan link dekat bawah"), font=f, fill=(255, 255, 255), anchor="mm")
    put(base, shadowed(b, 12, 50, 6), W / 2, 1745 - 30 * (1 - q) + math.sin(t * 4) * 3 * q, q)

# ---------- frame ----------
def frame(cfg, prj, bg, words, t):
    im = bg.copy(); scs = cfg["scenes"]
    for i, sc in enumerate(scs):
        if not (sc["start"] - 0.01 <= t < sc["end"] + 0.4): continue
        a_in = ease(ramp(t, sc["start"], 0.4)); a_out = 1 - ease(ramp(t, sc["end"] - 0.3, 0.35)) if i < len(scs) - 1 else 1
        a = a_in * a_out
        if sc.get("card"):
            c = top_card(sc, prj); cy = sc["card"].get("y", 470) - 40 * (1 - a_in)
            put(im, c, W / 2, cy, a)
            if sc["card"]["kind"] == "photo": scene_dots(im, i, len(scs), a)
        if sc.get("label"): put(im, pill(sc["label"], 34), W / 2, sc.get("label_y", 1290), a)
        for j, (txt, at) in enumerate(sc.get("pills", [])):
            q = ease(ramp(t, at, 0.3)) * a_out
            put(im, pill(txt, 40, fg=NAVY, dot=ORANGE), W / 2 + (j - (len(sc["pills"]) - 1) / 2) * 260, sc.get("pills_y", 1300), q)
        if sc.get("illus"): illus(im, sc, t)
        sub_card(im, sc, tokens(sc, words), t, a)
    cta_button(im, cfg, t)
    return im.convert("RGB")

# ---------- sound: soft pops on every entrance, a light chime on cards ----------
SR = 48000
def tone(f, d, dec, amp=1.0):
    n = int(SR * d); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt / dec) * amp * np.minimum(tt / 0.004, 1)
def mix(*xs):
    out = np.zeros(max(len(x) for x in xs))
    for x in xs: out[: len(x)] += x
    return out
def soft_pop(): return mix(tone(620, 0.12, 0.03), tone(930, 0.1, 0.02, 0.4))
def chime(): return mix(tone(1318.5, 0.9, 0.35), tone(1975.5, 0.7, 0.25, 0.45), tone(659.3, 0.9, 0.4, 0.3))
def breeze():
    n = int(SR * 0.5); rng = np.random.default_rng(3); x = rng.standard_normal(n)
    y = np.convolve(x, np.ones(60) / 60, "same"); e = np.sin(np.pi * np.arange(n) / n) ** 2; return y * e * 3
def sfx_track(cfg, dur):
    tr = np.zeros(int(SR * (dur + 1))); ev = []
    for i, sc in enumerate(cfg["scenes"]):
        if i: ev.append((sc["start"] - 0.05, breeze, -30))
        ev.append((sc["start"] + 0.1, soft_pop, -24))
        if sc.get("card"): ev.append((sc["start"] + 0.15, chime, -27))
        for _, at in sc.get("pills", []): ev.append((at, soft_pop, -25))
        il = sc.get("illus") or {}
        if il.get("kind") == "ask": ev += [(sc["start"] + 0.4 + k * 0.25, soft_pop, -28) for k in range(3)]
        if il.get("kind") == "books": ev += [(sc["start"] + 0.3 + k * 0.45 + 0.3, soft_pop, -25) for k in range(3)]
        if il.get("kind") == "stairs": ev += [(sc["start"] + il.get("climb_at", 0.4) + k * il.get("beat", 0.9), soft_pop, -27) for k in range(il.get("steps", 3) - 1)]
    if cfg.get("cta"): ev.append((cfg["cta"]["at"], chime, -24))
    for at, make, lvl in ev:
        s = make() * 10 ** (lvl / 20); i = max(0, int(at * SR)); j = min(len(tr), i + len(s)); tr[i:j] += s[: j - i]
    return np.clip(tr, -1, 1)

def main():
    prj = sys.argv[1]; cfg = json.load(open(os.path.join(prj, "project.json")))
    words = json.load(open(os.path.join(prj, "build", "words.json"))); words = words["words"] if isinstance(words, dict) else words
    src = os.path.join(prj, cfg.get("source", "input/vo.mp4"))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    only = [float(x) for x in sys.argv[2:]]   # stills: python arab.py prj 1.0 5.0 ...
    bg = background(cfg.get("bg", "putih"))
    if only:
        ims = [frame(cfg, prj, bg, words, t).resize((360, 640)) for t in only]; cols = 4; rows = (len(ims) + cols - 1) // cols
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
        p.stdin.write(frame(cfg, prj, bg, words, k / FPS).tobytes())
        if k % 150 == 0: print(f"{k}/{n} frames", flush=True)
    p.stdin.close(); p.wait(); print(f"done: {n} frames -> {out}")

if __name__ == "__main__":
    main()
