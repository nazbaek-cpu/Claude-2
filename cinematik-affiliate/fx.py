"""The "16 efek" camera effects for render.py (see styles/16-efek.md), driven by "fx" in project.json:

    "fx": [{"kind": "checklist", "start": 0.9, "end": 34, "title": ["6 sebab", "ibu ayah pilih"], "items": [["Sebesar tapak tangan", 5.5], ...]},
           {"kind": "headline", "start": 0.9, "end": 4.3, "tag": "BERITA PELAJAR · HARI INI", "lines": ["Calon SPM 2027,", "mula dari sekarang"]},
           {"kind": "zoomcut", "at": 4.3},
           {"kind": "digizoom", "start": 4.3, "end": 8.8, "zoom": 1.35, "focus": [540, 1000]},
           {"kind": "papercut", "start": 8.9, "end": 10.5, "word": "senang bawa"},
           {"kind": "depth", "start": 10.5, "end": 14.3, "words": [["SEJARAH", 10.8, "back"], ["FIZIK", 11.3, "front"]], "scatter_at": 13.9},
           {"kind": "beforeafter", "start": 14.4, "end": 18.4, "labels": ["buku teks", "infografik"]},
           {"kind": "doodle", "start": 18.8, "end": 24.4},
           {"kind": "framebreak", "start": 24.4, "end": 34, "user": "ibu ayah", "caption": "untuk anak calon SPM"},
           {"kind": "comment", "start": 35.6, "end": null, "text": "DAPATKAN DI LINK BAWAH"}]

picture(...) changes the frame itself (zooms, backgrounds, wipes, text behind the person); overlays(...) gives the
images drawn on top. Times are voice times; render.load() moves them onto the sped-up video like the segments.
"""
import math, os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
YEL = (255, 214, 10)
INTER = "/usr/share/fonts/opentype/inter/"
SERIF = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                          "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf") if os.path.exists(p)), INTER + "Inter-Bold.otf")
_fonts, cache = {}, {}

def font(path, size):
    key = (path, size)
    if key not in _fonts: _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]

def jak(size, weight=800):
    f = font(os.path.join(HERE, "fonts", "PlusJakartaSans.ttf"), size)
    key = ("jak", size, weight)
    if key not in _fonts:
        try: f.set_variation_by_axes([weight])
        except Exception: pass
        _fonts[key] = f
    return _fonts[key]

def heavy(size): return font(os.path.join(HERE, "fonts", "ArchivoBlack-Regular.ttf"), size)

def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def ease_back(x, k=1.7): x = min(max(x, 0.0), 1.0); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2
def ramp(t, a, d): return min(max((t - a) / d, 0.0), 1.0) if d > 0 else float(t >= a)
def vis(t, s, tin=0.3, tout=0.25):
    return ease(ramp(t, s["start"], tin)) * (1 - ramp(t, s["end"] - tout, tout))
def active(cfg, t, *kinds):
    return [s for s in cfg.get("fx", []) if s["kind"] in kinds and s.get("start", s.get("at", 0) - 0.35) <= t < s.get("end", s.get("at", 0) + 0.3)]

def fade(img, a):
    if a >= 0.999: return img
    img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * a))); return img

def shadow(img, op=110, blur=14, dy=8):
    pad = blur * 3; out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, op)); sh.putalpha(img.getchannel("A").point(lambda v: v * op // 255))
    out.alpha_composite(sh, (pad, pad + dy)); out = out.filter(ImageFilter.GaussianBlur(blur)); out.alpha_composite(img, (pad, pad))
    return out

def rounded(size, r, fill):
    w, h = size; s = 3; m = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=r * s, fill=255)
    img = Image.new("RGBA", (w, h), fill[:3] + (0,)); img.putalpha(m.resize((w, h), Image.LANCZOS).point(lambda v: v * fill[3] // 255 if len(fill) > 3 else v))
    return img

def text(txt, f, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0)):
    x0, y0, x1, y1 = f.getbbox(txt, stroke_width=stroke); img = Image.new("RGBA", (x1 - x0 + 8, y1 - y0 + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - x0, 4 - y0), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return img

# ---------- overlays ----------
def checklist(s, t):
    """title plus a numbered two-column list; the item being spoken turns yellow (a progress bar for the viewer)"""
    items = s["items"]; cur = max([i for i, (_, at) in enumerate(items) if t >= at], default=-1)
    key = ("check", id(s), cur)
    if key not in cache:
        img = Image.new("RGBA", (960, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        y = 0
        for k, line in enumerate(s.get("title", [])):
            f = jak(56 if k == 0 else 50, 800); words = line.split(" "); x = 480 - f.getlength(line) / 2
            for w_ in words:   # a leading number is yellow, like "16 video effects"
                col = YEL if w_.isdigit() else (255, 255, 255)
                d.text((x, y), w_, font=f, fill=col, stroke_width=2, stroke_fill=(0, 0, 0, 90)); x += f.getlength(w_ + " ")
            y += 60
        rows = (len(items) + 1) // 2; cy = y + 18; ch = rows * 46 + 26
        img.alpha_composite(rounded((900, ch), 22, (14, 14, 16, 150)), (30, cy))
        fi, fn = jak(30, 700), jak(22, 600)
        for i, (txt, _) in enumerate(items):
            col, row = i // rows, i % rows; x0, y0 = 60 + col * 440, cy + 16 + row * 46
            c = YEL if i == cur else (255, 255, 255, 255 if i < cur else 150)
            d.text((x0, y0 + 6), f"{i + 1:02d}", font=fn, fill=(255, 255, 255, 120))
            d.text((x0 + 40, y0), txt, font=fi, fill=c)
        cache[key] = shadow(img, 90, 10, 4)
    hide = max([ease(ramp(t, a, 0.2)) * (1 - ease(ramp(t, b, 0.25))) for a, b in s.get("hide", [])], default=0.0)   # make room up top
    a = vis(t, s) * (1 - hide)
    return [(fade(cache[key], a), W / 2, s.get("y", 250))] if a > 0 else []

def paper_strip(lines, tag, w=900, seed=4, mark=None, mark_p=0.0):
    """torn newspaper strip: small tag line, then serif lines; mark (a line index) gets a yellow highlighter sweep"""
    size = 64
    while size > 36 and max(font(SERIF, size).getlength(x) for x in lines) > w - 80: size -= 2
    f, ft = font(SERIF, size), font(INTER + "Inter-SemiBold.otf", 22)
    h = 70 + 78 * len(lines); rng = np.random.default_rng(seed)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); m = Image.new("L", (w, h), 0)
    top = [(x, 10 + rng.uniform(-7, 7)) for x in range(0, w + 1, 18)]; bot = [(x, h - 10 + rng.uniform(-7, 7)) for x in range(w, -1, -18)]
    ImageDraw.Draw(m).polygon(top + bot, fill=255)
    paper = Image.new("RGBA", (w, h), (247, 243, 233, 255)); paper.putalpha(m); img.alpha_composite(paper)
    d = ImageDraw.Draw(img); d.text((34, 26), tag, font=ft, fill=(110, 104, 96))
    for i, line in enumerate(lines):
        y = 58 + i * 78
        if i == mark and mark_p > 0:
            mw = int((f.getlength(line) + 16) * ease(mark_p)); d.rectangle((26, y + 22, 26 + mw, y + 70), fill=YEL + (230,))
        d.text((34, y), line, font=f, fill=(22, 22, 22))
    return img

def headline(s, t):
    a = vis(t, s, 0.35)
    if a <= 0: return []
    p = ease_back(ramp(t, s["start"], 0.45), 1.4); mp = ramp(t, s["start"] + 0.5, 0.5)
    key = ("head", id(s), round(mp, 2))
    if key not in cache:
        cache[key] = shadow(paper_strip(s["lines"], s.get("tag", ""), mark=s.get("mark", len(s["lines"]) - 1), mark_p=mp)
                            .rotate(s.get("rot", -2), Image.BICUBIC, expand=True), 120, 16, 10)
    img = cache[key]; sc = 0.7 + 0.3 * p
    img = img.resize((int(img.width * sc), int(img.height * sc)), Image.BICUBIC)
    return [(fade(img, a), W / 2, s.get("y", 1080) + 120 * (1 - ease(ramp(t, s["start"], 0.4))))]

def wall_clips(s, t):
    """small newspaper clippings pinned on the wall behind the person (drawn behind, see picture())"""
    out = []
    for i, (txt, x, y, rot) in enumerate(s.get("wall", [])):
        a = vis(t, s) * ease(ramp(t, s["start"] + 0.12 * i, 0.3))
        if a <= 0: continue
        key = ("clip", txt, rot)
        if key not in cache:
            cache[key] = shadow(_clip(txt), 90, 8, 5).rotate(rot, Image.BICUBIC, expand=True)
        out.append((fade(cache[key], a), x, y))
    return out

def _clip(txt):
    f = font(SERIF, 34); lines = txt.split("|"); w = int(max(f.getlength(x) for x in lines)) + 44; h = 30 + 42 * len(lines)
    img = Image.new("RGBA", (w, h), (244, 239, 226, 255)); d = ImageDraw.Draw(img)
    for k, line in enumerate(lines): d.text((22, 14 + k * 42), line, font=f, fill=(30, 30, 30))
    return img

def digizoom_ui(s, t, face=None):
    """camcorder overlay: REC dot, timecode, focus brackets, zoom readout"""
    a = vis(t, s, 0.2, 0.2)
    if a <= 0: return []
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    z = 1 + (s.get("zoom", 1.35) - 1) * ease(ramp(t, s.get("zoom_at", s["start"] + 0.6), 0.3)); cx_, cy_ = s.get("focus", (540, 1000))
    fx0, fy0, fx1, fy1 = [c_ + (v - c_) * z for v, c_ in zip(face if face is not None else (340, 560, 740, 1000), (cx_, cy_, cx_, cy_))]
    pad = 40; x0, y0, x1, y1 = fx0 - pad, fy0 - pad, fx1 + pad, fy1 + pad; L = 46
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line((cx, cy, cx + dx * L, cy), fill=(255, 255, 255, 230), width=4); d.line((cx, cy, cx, cy + dy * L), fill=(255, 255, 255, 230), width=4)
    f = font(INTER + "Inter-SemiBold.otf", 30); y = s.get("ui_y", 1560)
    if int(t * 2) % 2 == 0: d.ellipse((60, y - 12, 84, y + 12), fill=(235, 40, 40, 255))
    k = t - s["start"]; tc = f"00:00:{int(k) % 60:02d}:{int(k * 24) % 24:02d}"
    d.text((96, y - 18), f"REC  {tc}", font=f, fill=(255, 255, 255, 235))
    d.text((W - 70 - f.getlength(f"{z:.2f}x"), y - 18), f"{z:.2f}x", font=f, fill=(255, 255, 255, 235))
    for i in range(41):   # zoom ruler
        x = 300 + i * 12; hh = 22 if i % 5 == 0 else 12
        d.line((x, y + 50 - hh, x, y + 50), fill=(255, 255, 255, 170), width=2)
    return [(fade(img, a), W / 2, H / 2)]

def comment(s, t):
    """an Instagram-style comment box; the keyword types itself in, then the send button lights up"""
    a = vis(t, s, 0.3)
    if a <= 0: return []
    txt = s.get("text", "NAK"); n = int(max(0, t - s["start"] - 0.45) * s.get("cps", 16)); shown = txt[:n]
    key = ("cmt", id(s), shown)
    if key not in cache:
        w, h = 880, 104; img = rounded((w, h), 52, (18, 18, 20, 215)); d = ImageDraw.Draw(img)
        d.ellipse((22, 20, 86, 84), fill=(150, 150, 155)); d.ellipse((42, 30, 66, 54), fill=(225, 225, 230))
        d.pieslice((32, 52, 76, 96), 180, 360, fill=(225, 225, 230))
        f = jak(38, 800) if shown else font(INTER + "Inter-Medium.otf", 34)
        d.text((108, 30 if shown else 32), shown or s.get("placeholder", "Tambah komen..."), font=f, fill=(255, 255, 255) if shown else (160, 160, 165))
        done = n >= len(txt); bx = w - 84
        d.ellipse((bx, 18, bx + 66, 84), fill=YEL if done else (70, 70, 75))
        d.line((bx + 33, 64, bx + 33, 36), fill=(20, 20, 20), width=6); d.line((bx + 20, 48, bx + 33, 34, bx + 46, 48), fill=(20, 20, 20), width=6)
        cache[key] = shadow(img, 120, 16, 8)
    sc = 0.8 + 0.2 * ease_back(ramp(t, s["start"], 0.35))
    img = cache[key].resize((int(cache[key].width * sc), int(cache[key].height * sc)), Image.BICUBIC)
    return [(fade(img, a), W / 2, s.get("y", 1500))]

def overlays(cfg, t, face=None):
    out = []
    for s in active(cfg, t, "checklist", "headline", "digizoom", "comment"):
        if s["kind"] == "checklist": out += checklist(s, t)
        elif s["kind"] == "headline": out += headline(s, t)
        elif s["kind"] == "digizoom": out += digizoom_ui(s, t, face)
        elif s["kind"] == "comment": out += comment(s, t)
    return out

# ---------- picture effects ----------
def zoom(fr, z, cx=540, cy=960):
    if abs(z - 1) < 1e-3: return fr
    M = np.float32([[z, 0, cx - cx * z], [0, z, cy - cy * z]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def radial_blur(fr, amt, cx=540, cy=960, n=6):
    acc = np.zeros_like(fr, np.float32)
    for k in range(n): acc += zoom(fr, 1 + amt * k / n, cx, cy)
    return acc / n

def zoomcut(fr, s, t):
    """punch through the frame: zoom blur and a yellow flash into the cut, then settle"""
    k = t - s["at"]
    if -0.32 <= k < 0:
        p = ease(1 + k / 0.32); fr = radial_blur(zoom(fr, 1 + 0.6 * p), 0.25 * p)
    elif 0 <= k < 0.28:
        p = 1 - ease(k / 0.28); fr = radial_blur(zoom(fr, 1 + 0.18 * p), 0.12 * p)
    flash = max(0.0, 1 - abs(k) / 0.12) * 0.55
    if flash > 0: fr = fr * (1 - flash) + np.array(YEL, np.float32) * flash
    return fr

def paper_bg(seed=3):
    key = ("paperbg", seed)
    if key in cache: return cache[key]
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (W, H), (200, 172, 120))
    noise = (rng.normal(0, 7, (H // 4, W // 4))).astype(np.float32)
    def sheet(box, col, grid=False, rot=0):
        x0, y0, x1, y1 = box; sh = Image.new("RGBA", (x1 - x0, y1 - y0), col + (255,)); sd = ImageDraw.Draw(sh)
        if grid:
            for g in range(0, sh.width, 36): sd.line((g, 0, g, sh.height), fill=(170, 190, 210, 255), width=2)
            for g in range(0, sh.height, 36): sd.line((0, g, sh.width, g), fill=(170, 190, 210, 255), width=2)
        m = Image.new("L", sh.size, 0); pts = []
        for x in range(0, sh.width + 1, 20): pts.append((x, rng.uniform(0, 12)))
        for y in range(0, sh.height + 1, 20): pts.append((sh.width - rng.uniform(0, 12), y))
        for x in range(sh.width, -1, -20): pts.append((x, sh.height - rng.uniform(0, 12)))
        for y in range(sh.height, -1, -20): pts.append((rng.uniform(0, 12), y))
        ImageDraw.Draw(m).polygon(pts, fill=255); sh.putalpha(m); sh = sh.rotate(rot, Image.BICUBIC, expand=True)
        img.paste(sh, (x0, y0), sh)
    sheet((-60, 240, 720, 1100), (247, 244, 236), grid=True, rot=4)
    sheet((420, 520, 1180, 1280), (255, 222, 60), rot=-6)
    sheet((-80, 1150, 640, 2000), (236, 230, 216), rot=-3)
    sheet((520, 1300, 1160, 2040), (247, 244, 236), grid=True, rot=5)
    a = np.asarray(img).astype(np.float32) + cv2.resize(noise, (W, H))[..., None]
    cache[key] = np.clip(a, 0, 255)
    return cache[key]

def ransom(word, t0, t, y, one_line=False):
    """paper-cut letters, each on its own scrap, popping in one by one; a line per word unless one_line"""
    out = []; rng = np.random.default_rng(len(word)); lines = [word] if one_line else word.split(" ")
    styles = [((255, 255, 255), (20, 20, 20), SERIF), ((255, 214, 10), (20, 20, 20), os.path.join(HERE, "fonts", "ArchivoBlack-Regular.ttf")),
              ((20, 20, 20), (255, 255, 255), SERIF), ((30, 60, 160), (255, 255, 255), os.path.join(HERE, "fonts", "ArchivoBlack-Regular.ttf"))]
    i = 0
    for li, line in enumerate(lines):
        tiles = []
        for ch in line:
            if ch == " ":
                tiles.append((None, 0, i)); continue
            bg, fg, fp = styles[int(rng.integers(len(styles)))]; f = font(fp, int(rng.integers(92, 118)))
            key = ("rl", ch, bg, fp, f.size)
            if key not in cache:
                x0, y0, x1, y1 = f.getbbox(ch.lower()); w, h = x1 - x0 + 34, y1 - y0 + 34
                tile = Image.new("RGBA", (w, h), bg + (255,)); ImageDraw.Draw(tile).text((17 - x0, 17 - y0), ch.lower(), font=f, fill=fg)
                cache[key] = shadow(tile, 100, 6, 4)
            tiles.append((cache[key], rng.uniform(-9, 9), i)); i += 1
        total = sum(tl.width - 30 if tl else 40 for tl, _, _ in tiles)
        if total > 980:   # shrink a long line to fit the screen
            k_ = 980 / total; tiles = [(tl.resize((int(tl.width * k_), int(tl.height * k_)), Image.LANCZOS) if tl else None, r_, n_) for tl, r_, n_ in tiles]
            total = sum(tl.width - 30 * k_ if tl else 40 * k_ for tl, _, _ in tiles)
        x = W / 2 - total / 2
        for tl, rot, k in tiles:
            if tl is None:
                x += 40; continue
            p = ramp(t, t0 + 0.07 * k, 0.18)
            if p > 0:
                im = tl.rotate(rot, Image.BICUBIC, expand=True); sc = 0.4 + 0.6 * ease_back(p, 2.2)
                im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
                out.append((im, x + (tl.width - 30) / 2, y + li * 150))
            x += tl.width - 30
    return out

def word_letters(word, f, fill, stroke=0):
    """per-letter images and their x offsets from the word's left edge"""
    key = ("letters", word, f.size, fill)
    if key not in cache:
        res, x = [], 0.0
        for ch in word:
            if ch != " ": res.append((text(ch, f, fill, stroke, (0, 0, 0)), x))
            x += f.getlength(ch)
        cache[key] = (res, x)
    return cache[key]

def depth_layers(s, t):
    """returns (behind, front) word images: a new word in a slot pushes the old one out in pieces"""
    back, front = [], []; words = s["words"]
    for slot, ys, col in (("back", s.get("y_back", 640), (255, 255, 255)), ("front", s.get("y_front", 1660), YEL)):
        ws = [(w_, at) for w_, at, sl in words if sl == slot]
        for j, (w_, at) in enumerate(ws):
            nxt = ws[j + 1][1] if j + 1 < len(ws) else s.get("scatter_at", s["end"] - 0.4)
            if t < at: continue
            size = 210
            while heavy(size).getlength(w_) > 1000 and size > 90: size -= 10
            c_ = YEL if slot == "front" or j % 2 else col   # behind-only lists alternate white and yellow
            letters, total = word_letters(w_, heavy(size), c_, 3 if slot == "front" else 0)
            p = ease_back(ramp(t, at, 0.3), 1.5); q = ease(ramp(t, nxt, 0.5)); rng = np.random.default_rng(len(w_) * 7 + j)
            if q >= 1: continue
            for im, x in letters:
                ang = rng.uniform(0, 2 * math.pi); dist = 500 * q
                sc = (0.6 + 0.4 * p) * (1 + 0.8 * q)
                li = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
                if q > 0: li = li.filter(ImageFilter.GaussianBlur(10 * q))
                cx = W / 2 + (x + im.width / 2 - total / 2) * (0.6 + 0.4 * p) + math.cos(ang) * dist
                cy = ys + math.sin(ang) * dist * 0.6
                (back if slot == "back" else front).append((fade(li, min(1, ramp(t, at, 0.15) * 1.0) * (1 - q)), cx, cy))
    return back, front

def doodle(fr, s, t, mask):
    """hand-drawn outline that boils (re-jitters 8 times a second) around the person"""
    if mask is None: return fr
    m = (cv2.resize(mask, (W // 2, H // 2)) > 0.5).astype(np.uint8)
    out = fr.copy()
    for grow, col, wd, seed in ((14, YEL, 5, 1), (24, (255, 255, 255), 3, 2)):
        g = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
        cs, _ = cv2.findContours(g, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cs: continue
        c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
        step = max(1, len(c) // 160); c = c[::step]
        rng = np.random.default_rng(int(t * 8) * 10 + seed)
        c = (c + rng.normal(0, 2.2, c.shape)) * 2
        bx0, by0, bx1, by1 = s.get("box", (0, 0, W, H))   # e.g. head and shoulders only, when a raised product is half outside the mask
        keep = (c[:, 1] < min(H - 30, by1)) & (c[:, 1] > by0) & (c[:, 0] > max(6, bx0)) & (c[:, 0] < min(W - 6, bx1))   # not along the frame edges
        runs, cur = [], []
        for pt, k in zip(c, keep):
            if k: cur.append(pt)
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        lay = np.zeros((H, W), np.uint8)
        cv2.polylines(lay, [np.array(r_, np.int32) for r_ in runs if len(r_) > 1], False, 255, wd * 2, cv2.LINE_AA)
        a = (lay.astype(np.float32) / 255 * vis(t, s, 0.25))[..., None]
        out = out * (1 - a) + np.array(col, np.float32) * a
    rng = np.random.default_rng(int(t * 8) * 7)
    lay = np.zeros((H, W), np.uint8)
    for (x, y) in s.get("sparks", [(300, 1250), (780, 1220), (250, 700), (830, 680)]):
        for k in range(4):   # little sparkle strokes
            ang = k * math.pi / 2 + rng.uniform(-0.2, 0.2); r0, r1 = 14, 34 + rng.uniform(-4, 4)
            cv2.line(lay, (int(x + math.cos(ang) * r0), int(y + math.sin(ang) * r0)), (int(x + math.cos(ang) * r1), int(y + math.sin(ang) * r1)), 255, 5, cv2.LINE_AA)
    a = (lay.astype(np.float32) / 255 * vis(t, s, 0.25))[..., None]
    return out * (1 - a) + np.array((255, 255, 255), np.float32) * a

def before_after(fr, s, t):
    """wipe from a flat, grey "before" to the graded picture, with a glowing line and two labels"""
    p = ease(ramp(t, s["start"] + 0.3, max(0.5, s["end"] - s["start"] - 1.2)))
    x = int(W * (1 - p)); g = fr.mean(-1, keepdims=True)
    flat = (g * 0.8 + fr * 0.2) * 0.86 + 18
    out = fr.copy(); out[:, :x] = flat[:, :x]
    if 2 < x < W - 2:
        glow = np.exp(-((np.arange(W, dtype=np.float32) - x) / 10) ** 2)[None, :, None]
        out = out * (1 - glow * 0.9) + 255 * glow * 0.9
    return out, x

def ba_labels(s, t, x):
    a = vis(t, s, 0.25); out = []
    f = jak(34, 700); y = s.get("label_y", 980)
    for k, (txt, side) in enumerate(zip(s.get("labels", ["before", "after"]), ("l", "r"))):
        la = a * (min(1, x / 160) if side == "l" else min(1, (W - x) / 160))
        if la <= 0: continue
        key = ("bal", txt)
        if key not in cache:
            im = text(txt, f); pill = rounded((im.width + 46, im.height + 22), 30, (12, 12, 14, 170)); pill.alpha_composite(im, (23, 11))
            cache[key] = pill
        im = cache[key]; out.append((fade(im, la), 40 + im.width / 2 if side == "l" else W - 40 - im.width / 2, y))
    return out

def frame_break(fr, s, t, mask):
    """the video shrinks into a reel frame over a blurred copy of itself; the head breaks out over the frame's top edge"""
    p = ease(ramp(t, s["start"], 0.4)) * (1 - ease(ramp(t, s["end"] - 0.35, 0.35)))
    if p <= 0: return fr
    sc = 1 - 0.2 * p
    small = cv2.resize(fr, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR) * 0.55
    sw, sh = int(W * sc), int(H * sc); x0, y0 = (W - sw) // 2, (H - sh) // 2
    vid = cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA)
    cut = int(sh * s.get("cut", 0.36) * p)   # frame top edge drops into the head, so the head pokes out above it
    box = np.zeros((sh, sw), np.float32); box[cut:] = 1
    r = 34; corner = np.zeros((sh, sw), np.uint8); cv2.rectangle(corner, (0, cut), (sw - 1, sh - 1), 255, -1)
    corner = cv2.GaussianBlur(corner, (0, 0), 1.0).astype(np.float32) / 255
    rr = np.ones((sh, sw), np.float32)
    for (cx, cy) in ((r, cut + r), (sw - r, cut + r), (r, sh - r), (sw - r, sh - r)):
        yy, xx = np.ogrid[:sh, :sw]; out_c = ((xx - cx) ** 2 + (yy - cy) ** 2 > r * r)
        sel = ((xx < r) if cx == r else (xx > sw - r)) & ((yy < cy) if cy == cut + r else (yy > cy))
        rr[out_c & sel] = 0
    a = corner * rr
    if mask is not None:
        pm = cv2.resize(mask, (sw, sh)); a = np.maximum(a, np.where(np.arange(sh)[:, None] < cut + 4, pm, 0))
    out = bg.copy(); reg = out[y0:y0 + sh, x0:x0 + sw]
    out[y0:y0 + sh, x0:x0 + sw] = reg * (1 - a[..., None]) + vid * a[..., None]
    s["_box"] = (x0, y0 + cut, x0 + sw, y0 + sh, p)
    return out

def frame_ui(s, t):
    """Instagram reel chrome inside the frame: avatar, name, Follow, caption, side icons"""
    if "_box" not in s: return []
    x0, y0, x1, y1, p = s["_box"]
    if p <= 0.05: return []
    key = ("fui", s.get("user"), s.get("caption"), x1 - x0)
    if key not in cache:
        w = x1 - x0; img = Image.new("RGBA", (w, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        d.ellipse((30, 150, 96, 216), fill=(235, 235, 240), outline=(255, 255, 255), width=3)
        f, fc = jak(34, 800), jak(28, 600)
        d.text((112, 160), s.get("user", ""), font=f, fill=(255, 255, 255))
        fx = 112 + f.getlength(s.get("user", "")) + 22
        d.rounded_rectangle((fx, 158, fx + 118, 204), radius=12, outline=(255, 255, 255), width=3); d.text((fx + 18, 164), "Follow", font=fc, fill=(255, 255, 255))
        d.text((32, 236), s.get("caption", ""), font=fc, fill=(255, 255, 255))
        for k, y in enumerate((10, 92, 172)):   # heart, bubble, plane
            cx = w - 64
            if k == 0: d.polygon([(cx, y + 52), (cx - 30, y + 22), (cx - 22, y + 4), (cx, y + 16), (cx + 22, y + 4), (cx + 30, y + 22)], outline=(255, 255, 255), width=5)
            elif k == 1: d.ellipse((cx - 28, y + 4, cx + 28, y + 52), outline=(255, 255, 255), width=5)
            else: d.polygon([(cx - 30, y + 26), (cx + 30, y + 4), (cx + 6, y + 56)], outline=(255, 255, 255), width=5)
        cache[key] = img
    return [(fade(cache[key], p), (x0 + x1) / 2, y1 - 170)]

def needs_mask(cfg, t):
    return bool(active(cfg, t, "papercut", "depth", "doodle", "framebreak", "headline"))

def picture(cfg, t, fr, get_mask):
    """apply the frame-changing effects; returns (frame, extra overlays drawn on top)"""
    extra = []
    for s in active(cfg, t, "digizoom"):
        z = 1 + (s.get("zoom", 1.35) - 1) * ease(ramp(t, s.get("zoom_at", s["start"] + 0.6), 0.3))
        fx_, fy_ = s.get("focus", (540, 1000)); fr = zoom(fr, z, fx_, fy_)
        k = t - s.get("zoom_at", s["start"] + 0.6)
        if 0 <= k < 0.3: fr = radial_blur(fr, 0.08 * (1 - k / 0.3), fx_, fy_)
    for s in active(cfg, t, "zoomcut"): fr = zoomcut(fr, s, t)
    mask = get_mask(fr) if needs_mask(cfg, t) else None
    for s in active(cfg, t, "headline"):   # clippings on the wall behind the person
        clips = wall_clips(s, t)
        if clips and mask is not None:
            withc = paint(fr.copy(), clips); m = mask[..., None]; fr = withc * (1 - m) + fr * m
    for s in active(cfg, t, "papercut"):
        a = vis(t, s, 0.15, 0.15)
        if mask is not None and a > 0:
            m = mask[..., None]; edge = cv2.dilate((mask > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29)))
            edge = cv2.GaussianBlur(edge.astype(np.float32), (0, 0), 1.2)[..., None]
            cutout = paper_bg() * (1 - edge) + 255 * edge
            cutout = cutout * (1 - m) + fr * m
            fr = fr * (1 - a) + cutout * a
        extra += ransom(s.get("word", ""), s.get("word_at", s["start"] + 0.15), t, s.get("word_y", 1560), s.get("one_line", False))
    for s in active(cfg, t, "depth"):
        back, front = depth_layers(s, t)
        if back and mask is not None:
            withw = paint(fr.copy(), back); m = mask[..., None]; fr = withw * (1 - m) + fr * m
        extra += front
    for s in active(cfg, t, "beforeafter"):
        fr, x = before_after(fr, s, t); extra += ba_labels(s, t, x)
    for s in active(cfg, t, "doodle"): fr = doodle(fr, s, t, mask)
    for s in active(cfg, t, "framebreak"):
        fr = frame_break(fr, s, t, mask); extra += frame_ui(s, t)
    return fr, extra

def paint(fr, items):
    for img, cx, cy in items:
        a = np.asarray(img).astype(np.float32); h, w = a.shape[:2]
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if X0 >= X1 or Y0 >= Y1: continue
        sub = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]; al = sub[..., 3:] / 255
        fr[Y0:Y1, X0:X1] = fr[Y0:Y1, X0:X1] * (1 - al) + sub[..., :3] * al
    return fr

TIME_KEYS = ("start", "end", "at", "zoom_at", "scatter_at", "word_at")

def remap(fx, f, dur=None):
    """voice times -> output times (render.load passes speed's mapping); lists keep their text, times move"""
    for s in fx:
        for k in TIME_KEYS:
            if s.get(k) is not None: s[k] = f(s[k])
        if "items" in s: s["items"] = [[x, f(at)] for x, at in s["items"]]
        if "words" in s: s["words"] = [[x, f(at), sl] for x, at, sl in s["words"]]
        if "hide" in s: s["hide"] = [[f(a), f(b)] for a, b in s["hide"]]
    return fx
