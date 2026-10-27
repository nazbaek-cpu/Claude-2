"""Talking-head footage + project.json -> cinematic 9:16 affiliate video.

Warm muted grade, natural beauty pass, punch-in cuts per subtitle phrase, Inter typography with
blur-in animations, headlines tucked behind the subject, pills, count-up, yellow CTA, SFX mix.

    python render.py projects/<name> [--limit SECONDS] [--out FILE]
"""
import argparse, json, math, os, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import project

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
F = "/usr/share/fonts/opentype/inter/"
def font(name, size): return ImageFont.truetype(F + name, size)
K_FONT = font("Inter-Medium.otf", 30)          # kicker: small caps, wide tracking
H_FONT = font("InterDisplay-Bold.otf", 104)    # headline, ends with a full stop
N_FONT = font("Inter-ExtraBold.otf", 230)      # count-up number
L_FONT = font("Inter-SemiBold.otf", 42)        # label under the number
P_FONT = font("Inter-SemiBold.otf", 34)        # pills
S_FONT = font("Inter-SemiBold.otf", 48)        # subtitles
C_FONT = font("Inter-Bold.otf", 38)            # CTA pill
YELLOW, GREEN = (255, 214, 10), (48, 209, 88)
KICK_Y, HEAD_Y, PILL_Y, SUB_Y, CTA_Y = 425, 525, 1165, 1300, 335

# opening title card: left-aligned editorial block, Plus Jakarta Sans, one accent colour
def jakarta(weight, size):
    f = ImageFont.truetype(os.path.join(HERE, "fonts", "PlusJakartaSans.ttf"), size); f.set_variation_by_name(weight); return f
TK_FONT = jakarta("Bold", 30)
TL_FONT = jakarta("ExtraBold", 132)
GOLD = (233, 185, 73)
TITLE_X, TITLE_LINE_H = 70, 132
# "bottom": lower-left like a product cover (subtitles drop below it); "top": above the head when the face is centred
TITLE_POS = {"bottom": dict(kick=1000, line=1100, sub=1480), "top": dict(kick=250, line=350, sub=SUB_Y)}

# "theme": "skrip" -- simple food look: yellow handwritten line (thin white outline) over bold white sans
SKRIP_YELLOW = (255, 204, 41)
SK_HEAD, SK_NUM, SK_SUB, SK_LABEL = jakarta("ExtraBold", 96), jakarta("ExtraBold", 220), jakarta("SemiBold", 50), jakarta("Bold", 44)

def script_img(txt, size=110):
    key = ("script", txt, size)
    if key in cache: return cache[key]
    fnt = ImageFont.truetype(os.path.join(HERE, "fonts", "Pacifico-Regular.ttf"), size)
    asc, desc = fnt.getmetrics(); pad = 30
    img = Image.new("RGBA", (int(fnt.getlength(txt)) + pad * 2, asc + desc + pad * 2), (255, 255, 255, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad, pad), txt, font=fnt, fill=(0, 0, 0, 140), stroke_width=3, stroke_fill=(0, 0, 0, 140))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), (0, 4))
    ImageDraw.Draw(img).text((pad, pad), txt, font=fnt, fill=SKRIP_YELLOW + (255,), stroke_width=3, stroke_fill=(255, 255, 255, 255))
    cache[key] = img
    return img

GRADE = ("colortemperature=temperature=5600:mix=0.35,"
         "eq=saturation=0.86:contrast=1.06:gamma=0.98,"
         "curves=master='0/0.035 0.25/0.22 0.75/0.75 1/0.94',"
         "colorbalance=rs=0.03:bs=-0.03:rh=0.02:bh=-0.02,"
         "vignette=PI/5,format=rgb24")
GRADES = {"muted": GRADE,   # "grade": "bright" (project.json): lifted mids and full whites for a dim or grey take
          "bright": ("colortemperature=temperature=5400:mix=0.3,"
                     "eq=saturation=1.08:contrast=1.04:gamma=1.18,"
                     "curves=master='0/0.02 0.25/0.34 0.6/0.75 1/1',"
                     "colorbalance=rs=0.025:bs=-0.02:rh=0.01,"
                     "vignette=PI/9,format=rgb24")}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return s["width"], s["height"], num / den, s["r_frame_rate"], float(j["format"]["duration"])


def load(prj):
    """project.json with end=null resolved to the video length; with "speed", times move onto build/fast.mp4"""
    cfg = project.read(prj)
    cfg["source"] = os.path.join(prj, cfg["source"])
    if cfg.get("hflip") == "auto":  # mirrored product text -> flip (OCR, cached in build/mirror.json)
        import mirror
        cfg["hflip"] = mirror.cached(prj, cfg["source"])
    tm = os.path.join(prj, "build", "timemap.json")
    if cfg.get("speed") and os.path.exists(tm):
        from speed import span, to_output
        m = json.load(open(tm)); keep, tempo = m["keep"], m["tempo"]; ranges = m.get("ranges", [[0, 1e9]])
        def f(x): return round(to_output(x, keep, tempo), 3)
        def g(a, b):  # an open end (None) stays open; otherwise clipped to the piece that holds the start
            oa, ob = span(a, 1e9 if b is None else b, keep, tempo, ranges)
            return round(oa, 3), None if b is None and ranges[-1][0] <= a else round(ob, 3)
        cfg["source"] = os.path.join(prj, "build", "fast.mp4")
        for s in cfg["segments"]:
            s["start"], s["end"] = g(s["start"], s.get("end"))
            if "pills" in s: s["pills"] = [[txt, f(ts)] for txt, ts in s["pills"]]
        cfg["subs"] = [[*g(a, b), txt] for a, b, txt in cfg["subs"]]
    dur = probe(cfg["source"])[4] if os.path.exists(cfg["source"]) else 9999.0
    for s in cfg["segments"]:
        if s.get("end") is None: s["end"] = dur + 1
    cfg["subs"] = [[a, dur + 1 if b is None else b, txt] for a, b, txt in cfg["subs"]]
    cfg["duration"] = dur
    return cfg


# ---------- text rendering ----------
cache = {}
def text_img(txt, fnt, fill=(255, 255, 255), track=0, shadow=False):
    key = (txt, id(fnt), fill, track, shadow)
    if key in cache: return cache[key]
    asc, desc = fnt.getmetrics()
    widths = [fnt.getlength(c) + track for c in txt] if track else [fnt.getlength(txt)]
    tw = int(sum(widths) - (track if track else 0)) + 2
    pad = 24 if shadow else 4
    img = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), fill + (0,))
    a = Image.new("L", img.size, 0); d = ImageDraw.Draw(a)
    if track:
        x = pad
        for c, w in zip(txt, widths): d.text((x, pad), c, font=fnt, fill=255); x += w
    else:
        d.text((pad, pad), txt, font=fnt, fill=255)
    if shadow:
        sh = a.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.65))
        base = Image.new("RGBA", img.size, (0, 0, 0, 0)); base.putalpha(sh)
        fg = Image.new("RGBA", img.size, fill + (0,)); fg.putalpha(a)
        img = Image.alpha_composite(base, fg)
    else:
        img.putalpha(a)
    cache[key] = img
    return img

def pill(txt, fnt, bg, fg, padx=28, pady=15):
    key = ("pill", txt, bg)
    if key in cache: return cache[key]
    t = text_img(txt, fnt, fg)
    w, h = t.width - 8 + padx * 2, int(fnt.size * 1.25) + pady * 2
    img = Image.new("RGBA", (w, h), bg + (0,))
    m = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=h * 2, fill=255)
    img.putalpha(m.resize((w, h), Image.LANCZOS))
    tx = Image.new("RGBA", img.size, (0, 0, 0, 0))
    tx.paste(t, ((w - t.width) // 2, (h - t.height) // 2 - 2), t)
    tl = np.array(tx)[..., 3:4].astype(np.float32) / 255
    arr = np.array(img).astype(np.float32)
    arr[..., :3] = arr[..., :3] * (1 - tl) + np.array(fg, np.float32) * tl
    img = Image.fromarray(arr.astype(np.uint8))
    cache[key] = img
    return img

def chevrons():
    if "chev" in cache: return cache["chev"]
    s = 4; w, h = 60, 52
    m = Image.new("L", (w * s, h * s), 0); d = ImageDraw.Draw(m)
    for oy in (6, 26):
        d.line([(10 * s, oy * s), (30 * s, (oy + 16) * s), (50 * s, oy * s)], fill=255, width=6 * s, joint="curve")
    img = Image.new("RGBA", (w, h), YELLOW + (0,)); img.putalpha(m.resize((w, h), Image.LANCZOS))
    cache["chev"] = img
    return img

def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def vis(t, t0, t1, tin=0.32, tout=0.25):
    if t < t0 or t > t1: return 0.0
    return ease_out(min((t - t0) / tin, (t1 - t) / tout))

def count_value(seg, t):
    return round(seg["count"] * ease_out((t - seg["start"] - 0.1) / 1.2), seg.get("decimals", 0) or None)

def count_text(seg, t):
    return f'{count_value(seg, t):.{seg.get("decimals", 0)}f}'

def anim(img, a, scale_from=1.04):
    """blur-in / blur-out with fade"""
    if a >= 0.999: return img
    sc = scale_from + (1 - scale_from) * a
    if abs(sc - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BICUBIC)
    r = (1 - a) * 18
    if r > 0.3:
        padded = Image.new("RGBA", (img.width + 60, img.height + 60), img.getpixel((0, 0))[:3] + (0,))
        padded.paste(img, (30, 30)); img = padded.filter(ImageFilter.GaussianBlur(r))
    al = img.getchannel("A").point(lambda v: int(v * a)); img = img.copy(); img.putalpha(al)
    return img

def blend(frame, img, cx, cy):
    x0, y0 = int(cx - img.width / 2), int(cy - img.height / 2)
    x1, y1 = x0 + img.width, y0 + img.height
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0c, y0c, x1c, y1c = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1c <= x0c or y1c <= y0c: return
    arr = np.asarray(img, dtype=np.float32)[sy0:sy0 + y1c - y0c, sx0:sx0 + x1c - x0c]
    al = arr[..., 3:4] / 255
    reg = frame[y0c:y1c, x0c:x1c]
    reg[:] = reg * (1 - al) + arr[..., :3] * al

def rich_img(runs, fnt):
    """one line of (text, rgb) runs, e.g. white words + an accent word"""
    key = ("rich", tuple(runs), id(fnt))
    if key in cache: return cache[key]
    asc, desc = fnt.getmetrics(); pad = 4
    w = int(sum(fnt.getlength(txt) for txt, _ in runs)) + 2
    img = Image.new("RGBA", (w + pad * 2, asc + desc + pad * 2), (255, 255, 255, 0))
    x = pad
    for txt, rgb in runs:
        m = Image.new("L", img.size, 0); ImageDraw.Draw(m).text((x, pad), txt, font=fnt, fill=255)
        layer = Image.new("RGBA", img.size, tuple(rgb) + (0,)); layer.putalpha(m)
        img = Image.alpha_composite(img, layer); x += fnt.getlength(txt)
    cache[key] = img
    return img

def scrim(a, pos="bottom"):
    """soft dark gradient (lower-left, or from the top) so the title reads on any background"""
    key = ("scrim", pos)
    if key not in cache:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        if pos == "top":
            v = np.clip(1 - (yy - 420) / 420, 0, 1) * np.clip(1.25 - xx / W * 0.6, 0, 1)
        else:
            v = np.clip((yy - 760) / 420, 0, 1) * np.clip(1 - (yy - 1560) / 360, 0, 1) * np.clip(1.25 - xx / W * 0.6, 0, 1)
        cache[key] = Image.fromarray((np.dstack([np.zeros_like(v)] * 3 + [v * 255])).astype(np.uint8))
    img = cache[key]
    return img if a >= 0.999 else Image.merge("RGBA", (*img.split()[:3], img.getchannel("A").point(lambda v: int(v * a))))

# "title_style": "orbit" -- title lines swing round a turning wall onto a frosted glass panel
def orbit(img, p, out=False):
    """img wrapped on a vertical cylinder that turns to face the camera as p goes 0 -> 1 (out: turns away)"""
    if p >= 0.999: return img
    w, h = img.width, img.height
    e = ease_out(p)
    th = (1 - e) * 1.35 * (1 if out else -1)       # radians the line is still turned about its vertical axis
    bend = 0.35 * (1 - e)                           # the wall's curve, flattening as it lands
    D = w * 1.6                                     # camera distance
    xc = np.arange(w, dtype=np.float32) - w / 2
    Z = xc * math.sin(th) + bend * xc * xc / w      # depth of each column (+ = away)
    sc = D / (D + Z)
    X = xc * math.cos(th) * sc                      # projected column position, monotonic while cos(th) > 0
    cw, ch = w, int(h * 1.5)
    u = np.arange(cw, dtype=np.float32) - cw / 2
    order = np.argsort(X)
    src_x = np.interp(u, X[order], xc[order] + w / 2, left=-1, right=-1)
    s_u = np.interp(u, X[order], sc[order])
    v = np.arange(ch, dtype=np.float32)[:, None] - ch / 2
    map_x = np.repeat(src_x[None, :], ch, 0).astype(np.float32)
    map_y = (v / s_u[None, :] + h / 2).astype(np.float32)
    arr = cv2.remap(np.asarray(img), map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    shade = np.clip(s_u, 0, 1.2) ** 1.5             # the far side falls into shadow
    arr = arr.astype(np.float32)
    arr[..., :3] *= np.clip(shade, 0.45, 1)[None, :, None]
    arr[..., 3] *= (src_x >= 0)[None, :] * min(1, 0.25 + e)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

def shadowed(img):
    key = ("shadowed", id(img))
    if key in cache: return cache[key]
    pad = 24
    out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 120), (pad, pad + 3), img.getchannel("A"))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9))); out.alpha_composite(img, (pad, pad))
    cache[key] = out
    return out

def glass(base, box, a, tint=0.30, radius=36):
    """frosted glass: blur what is behind box, lay a white tint (tint = its opacity), soft rim and top sheen"""
    x0, y0, x1, y1 = [int(round(c)) for c in box]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if a <= 0 or x1 <= x0 or y1 <= y0: return
    key = ("glassmask", x1 - x0, y1 - y0, radius)
    if key not in cache:
        m = Image.new("L", ((x1 - x0) * 4, (y1 - y0) * 4), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=radius * 4, fill=255)
        rim = Image.new("L", m.size, 0)
        ImageDraw.Draw(rim).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=radius * 4, outline=255, width=8)
        size = (x1 - x0, y1 - y0)
        sheen = np.clip(1 - np.arange(size[1], dtype=np.float32) / (size[1] * 0.6), 0, 1)[:, None, None] * 0.10
        cache[key] = (np.asarray(m.resize(size, Image.LANCZOS), np.float32)[..., None] / 255,
                      np.asarray(rim.resize(size, Image.LANCZOS), np.float32)[..., None] / 255, sheen)
    m, rim, sheen = cache[key]
    reg = base[y0:y1, x0:x1]
    frost = cv2.GaussianBlur(reg, (0, 0), 22) * (1 - tint) + 255 * tint
    frost = frost * (1 - sheen) + 255 * sheen
    reg[:] = reg * (1 - m * a) + frost * m * a
    reg[:] = reg * (1 - rim * a * 0.55) + 255 * rim * a * 0.55

def orbit_title(cfg, s, t, front):
    t0, t1 = s["start"], s["end"]
    tc = s["title"]; accent = tuple(cfg.get("accent_rgb", GOLD)); acc_words = set(tc.get("accent", []))
    a = vis(t, t0, t1, 0.35, 0.45)
    if a <= 0: return
    pos = TITLE_POS[cfg.get("title_pos", "bottom")]
    size = tc.get("size", 132)
    if ("tl", size) not in cache: cache[("tl", size)] = TL_FONT if size == 132 else jakarta("ExtraBold", size)
    fnt, lh = cache[("tl", size)], TITLE_LINE_H * size / 132
    bottom = pos["line"] + (len(tc["lines"]) - 1) * lh + 108 * size / 132
    rise = 24 * (1 - ease_out((t - t0) / 0.45))
    front.append((("glass", (30, pos["kick"] - 52 + rise, W - 30, bottom + 44 + rise), a, cfg.get("glass", 0.30)), 0, 0))
    k = shadowed(text_img(tc["kicker"], TK_FONT, fill=accent, track=6))
    front.append((anim(k, a, 1.0), TITLE_X - 4 - 24 + k.width / 2, pos["kick"]))
    leaving = t > t1 - 0.45
    for i, line in enumerate(tc["lines"]):
        words = line.split(" ")
        runs = [(w + (" " if j < len(words) - 1 else ""), accent if w in acc_words else (255, 255, 255)) for j, w in enumerate(words)]
        im = shadowed(rich_img(runs, fnt))
        p = (t1 - t) / 0.45 if leaving else (t - t0 - 0.15 - 0.16 * i) / 0.75
        if p <= 0: continue
        cx = TITLE_X - 4 - 24 + im.width / 2       # the turned copy is centred on the flat line
        front.append((orbit(im, min(p, 1), out=leaving), cx, pos["line"] + i * lh))
    bw = int(190 * ease_out((t - t0 - 0.9) / 0.45))
    if bw > 3:
        bar = Image.new("RGBA", (bw, 5), accent + (255,))
        front.append((anim(bar, a, 1.0), TITLE_X + bw / 2, bottom))

def title_layers(cfg, s, t, front):
    if cfg.get("title_style") == "orbit" and cfg.get("theme") != "skrip":
        return orbit_title(cfg, s, t, front)
    t0, t1 = s["start"], s["end"]
    tc = s["title"]; accent = tuple(cfg.get("accent_rgb", GOLD)); acc_words = set(tc.get("accent", []))
    a = vis(t, t0, t1, 0.4, 0.3)
    if a <= 0: return
    pos = TITLE_POS[cfg.get("title_pos", "bottom")]
    front.append((scrim(a * 0.72, cfg.get("title_pos", "bottom")), W / 2, H / 2))
    if cfg.get("theme") == "skrip":   # centred: bold white line, then the yellow handwritten line
        l1, l2 = tc["lines"][0], tc["lines"][-1]
        front.append((anim(text_img(l1, SK_HEAD, shadow=True), min(a, vis(t, t0 + 0.1, t1, 0.4, 0.3)), 1.0), 540, pos["line"] - 40))
        front.append((anim(script_img(l2, 120), min(a, vis(t, t0 + 0.25, t1, 0.4, 0.3)), 1.06), 540, pos["line"] + 105))
        return
    size = tc.get("size", 132)   # smaller for a long accent phrase that must stay on one line
    if ("tl", size) not in cache: cache[("tl", size)] = TL_FONT if size == 132 else jakarta("ExtraBold", size)
    fnt, lh = cache[("tl", size)], TITLE_LINE_H * size / 132
    k = text_img(tc["kicker"], TK_FONT, fill=accent, track=6)
    front.append((anim(k, a, 1.0), TITLE_X - 4 + k.width / 2, pos["kick"]))
    for i, line in enumerate(tc["lines"]):
        words = line.split(" ")
        runs = [(w + (" " if j < len(words) - 1 else ""), accent if w in acc_words else (255, 255, 255)) for j, w in enumerate(words)]
        im = anim(rich_img(runs, fnt), min(a, vis(t, t0 + 0.1 * (i + 1), t1, 0.4, 0.3)), 1.0)
        front.append((im, TITLE_X - 4 + im.width / 2, pos["line"] + i * lh))
    bw = int(190 * ease_out((t - t0 - 0.45) / 0.45))
    if bw > 3:
        bar = Image.new("RGBA", (bw, 5), accent + (255,))
        front.append((anim(bar, a, 1.0), TITLE_X + bw / 2, pos["line"] + (len(tc["lines"]) - 1) * lh + 108 * size / 132))

def layers(cfg, t):
    """returns (behind_subject, in_front) lists of (img, cx, cy)"""
    back, front = [], []
    sub_y = SUB_Y
    skrip = cfg.get("theme") == "skrip"
    head_f, num_f, sub_f = (SK_HEAD, SK_NUM, SK_SUB) if skrip else (H_FONT, N_FONT, S_FONT)
    oy = cfg.get("top_offset", 0)   # negative lifts the top text for footage where the head sits high
    for s in cfg["segments"]:
        if "title" in s:
            title_layers(cfg, s, t, front)
            if s["start"] <= t <= s["end"]: sub_y = TITLE_POS[cfg.get("title_pos", "bottom")]["sub"]
            continue
        t0, t1 = s["start"], s["end"]
        a = vis(t, t0, t1)
        if a <= 0: continue
        soy = s.get("offset", oy)   # per-segment override, e.g. a count-up that must stay clear of the app's top bar
        if cfg.get("head_scrim") and (s.get("head") or "count" in s):   # e.g. a lit lamp held up behind the text
            front.append((scrim(a * 0.6, "top"), W / 2, H / 2))
        if s.get("kicker"):
            if skrip:   # the kicker becomes the yellow handwritten line
                front.append((anim(script_img(s["kicker"]), a, 1.06), 540, (HEAD_Y - 118 if "count" not in s else 235) + soy))
            else:
                front.append((anim(text_img(s["kicker"], K_FONT, track=7), a), 540, (KICK_Y if "count" not in s else 245) + soy))
        if s.get("head"):
            behind = s.get("behind", cfg.get("behind", True))   # in front: soft shadow so it reads on a light hijab
            (back if behind else front).append((anim(text_img(s["head"], head_f, shadow=not behind or skrip), a), 540, HEAD_Y + soy))
        if "count" in s:
            p = ease_out((t - t0 - 0.1) / 1.2)
            behind = s.get("behind", cfg.get("behind", True))
            (back if behind else front).append((anim(text_img(count_text(s, t), num_f, shadow=not behind or skrip), a), 540, 385 + soy))
            la = a * ease_out((t - t0 - 0.6) / 0.35)
            if la > 0 and s.get("label"):
                front.append((anim(text_img(s["label"], SK_LABEL if skrip else L_FONT, shadow=True), la), 540, 528 + soy))
            bw = int(240 * p)
            if bw > 4:
                bar = Image.new("RGBA", (bw, 8), (SKRIP_YELLOW if skrip else GREEN) + (0,)); bm = Image.new("L", (bw, 8), 0)
                ImageDraw.Draw(bm).rounded_rectangle((0, 0, bw - 1, 7), radius=4, fill=255); bar.putalpha(bm)
                front.append((anim(bar, a, 1.0), 540 - 120 + bw / 2, 572 + soy))
        if s.get("pills"):
            imgs = [pill(txt, P_FONT, (255, 255, 255), (20, 20, 20)) for txt, _ in s["pills"]]
            gap = 16; total = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
            x = 540 - total / 2
            for (txt, ts), im in zip(s["pills"], imgs):
                pa = min(a, vis(t, ts, t1, 0.28))
                if pa > 0: front.append((anim(im, pa, 0.9), x + im.width / 2, PILL_Y))
                x += im.width + gap
        if s.get("cta"):
            front.append((anim(pill(cfg.get("cta", "Beli di beg kuning"), C_FONT, YELLOW, (17, 17, 17)), a, 0.9), 540, CTA_Y + soy))
            ca = min(a, vis(t, t0 + 0.3, t1, 0.25))
            if ca > 0:
                bob = 7 * math.sin(2 * math.pi * 1.4 * (t - t0))
                front.append((anim(chevrons(), ca, 1.0), 540, CTA_Y + soy + 72 + bob))
    for s0, s1, txt in cfg["subs"]:
        if s0 <= t < s1:
            front.append((text_img(txt, sub_f, shadow=True), 540, sub_y))
    return back, front


# ---------- picture ----------
yy = np.arange(H, dtype=np.float32)[:, None, None]
TOP = 1 - 0.40 * np.clip(1 - yy / 950, 0, 1) ** 1.6       # dark top for headline legibility
BOT = 1 - 0.22 * np.clip((yy - 1150) / 770, 0, 1) ** 1.3   # gentle bottom for subtitles
SHADE = (TOP * BOT).astype(np.float32)

def zoom_for(cfg, t):
    """hard-cut punch-in, alternating per subtitle phrase (fake multicam)"""
    cuts = [0.0] + [s[0] for s in cfg["subs"][1:]]
    i = max(j for j, c in enumerate(cuts) if c <= t)
    return 1.0 if i % 2 == 0 else cfg.get("zoom", 1.12)

def apply_zoom(fr, z, cy=760):
    if z == 1.0: return fr
    M = np.float32([[z, 0, 540 - 540 * z], [0, z, cy - cy * z]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--limit", type=float); ap.add_argument("--out")
    args = ap.parse_args()
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    import beauty

    cfg = load(args.project)
    src = cfg["source"]
    _, _, fps, rate, _ = probe(src)
    out = args.out or os.path.join(args.project, "out", "final.mp4")
    sfx = os.path.join(args.project, "build", "sfx.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bcfg = cfg.get("beauty", {}); beauty.configure(bcfg)
    use_beauty = bcfg.get("enabled", True)

    models = os.path.join(HERE, "models")
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(models, "selfie_segmenter.tflite")),
        output_confidence_masks=True, running_mode=vision.RunningMode.IMAGE))
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(models, "face_landmarker.task")), num_faces=1,
        running_mode=vision.RunningMode.VIDEO))

    # fill 1080x1920 whatever the source size
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}," + ("hflip," if cfg.get("hflip") else "")  # hflip: un-mirror selfie footage
    dec_cmd = ["ffmpeg", "-v", "error", "-i", src] + (["-t", str(args.limit)] if args.limit else [])
    dec = subprocess.Popen(dec_cmd + ["-vf", fit + GRADES[cfg.get("grade", "muted")], "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    studio = os.path.join(args.project, "build", "voice.wav")   # from voice.py: already cleaned and levelled
    use_studio = cfg.get("voice", {}).get("studio", True) and os.path.exists(studio)
    voice = "[1:a]aresample=48000" if use_studio else "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"
    if os.path.exists(sfx):
        audio = ["-i", sfx, "-filter_complex", voice + "[v];[2:a]aresample=48000[s];"
                 "[v][s]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]", "-map", "0:v", "-map", "[a]"]
    else:
        audio = ["-filter_complex", voice + "[a]", "-map", "0:v", "-map", "[a]"]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", rate, "-i", "-", "-i", studio if use_studio else src] + audio +
                           ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
                            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)

    prev = None; pts_s = None; miss = 0; n = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        t = n / fps
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        if use_beauty:
            # before the zoom, so landmarks stay continuous across cuts
            small = cv2.resize(fr, (540, 960), interpolation=cv2.INTER_AREA)
            r = face.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(small)), int(t * 1000))
            if r.face_landmarks:
                p = np.array([[lm.x * W, lm.y * H] for lm in r.face_landmarks[0]], np.float32)
                jump = pts_s is None or np.abs(p - pts_s).mean() > 40
                pts_s = p if jump else 0.55 * p + 0.45 * pts_s
                miss = 0
            else:
                miss += 1
            if pts_s is not None and miss < 4:
                fr = beauty.beautify(fr, pts_s)
        fr = apply_zoom(fr, zoom_for(cfg, t))
        base = fr.astype(np.float32) * SHADE
        back, front = layers(cfg, t)
        if back:
            # headline sits behind the person: paint it, then put the person back on top
            small = cv2.resize(fr, (540, 960), interpolation=cv2.INTER_AREA)
            m = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(small))).confidence_masks[0].numpy_view()
            m = np.squeeze(m).astype(np.float32)
            m = m if prev is None else 0.65 * m + 0.35 * prev
            prev = m
            mm = cv2.GaussianBlur(np.clip((m - 0.35) / 0.3, 0, 1), (0, 0), 1.5)
            mm = cv2.resize(mm, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
            withtext = base.copy()
            for img, cx, cy in back: blend(withtext, img, cx, cy)
            base = withtext * (1 - mm) + base * mm
        else:
            prev = None
        for img, cx, cy in front:
            if isinstance(img, tuple): glass(base, img[1], img[2], img[3])   # ("glass", box, alpha, tint)
            else: blend(base, img, cx, cy)
        enc.stdin.write(np.clip(base, 0, 255).astype(np.uint8).tobytes())
        n += 1
        if n % 100 == 0: print(f"{n} frames", flush=True)
    enc.stdin.close(); enc.wait(); dec.wait(); seg.close(); face.close()
    print(f"done: {n} frames -> {out}")


if __name__ == "__main__":
    main()
