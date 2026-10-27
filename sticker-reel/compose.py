"""scenes.json + voiceover timings -> HyperFrames composition, SFX and audio mix.

usage: compose.py <project>
Every time in scenes.json is a phrase from the script ("jangan abaikan"), optionally with an offset
("jangan abaikan+0.3", "+0.5" = scene start + 0.5 s) or a plain number of seconds, so the same scenes.json
keeps working when the voiceover is re-recorded. Texts may use {{variables}} from project.json.
Writes build/reel/ (index.html + assets), build/sfx_cues.json and build/timeline.txt (resolved times).
"""
import html, json, os, re, shutil, subprocess, sys, wave
import numpy as np
from common import HERE, Project

NM = os.path.join(HERE, "node_modules")
THEME = {"bg1": "#FFE46E", "bg2": "#FFD23C", "bg3": "#FFC41E", "ink": "#1E1B16", "accent": "#FF2E7E", "accent2": "#1FA2E8",
         "navy": "#1C2B5A", "green": "#1DB954", "red": "#FF3B30", "key": "#FFD23C"}
COLORS = {"ink": "var(--ink)", "white": "#fff", "accent": "var(--accent)", "accent2": "var(--accent2)", "navy": "var(--navy)", "grey": "#888"}
SIZES = {"xxl": 200, "xl": 150, "l": 104, "m": 72, "s": 54}
RAINBOW = ["#FF2E7E", "#FF8A00", "#1FA2E8", "#8B5CF6", "#1DB954"]
SPOTS = [(40, 120), (880, 200), (70, 760), (880, 880), (470, 1060), (900, 1380), (20, 1420), (600, 40)]
SFX = {"pop": ("pop", .45), "slam": ("boom", .5), "drop": ("whoosh", .35), "rise": ("whoosh", .5), "left": ("whoosh", .4),
       "right": ("whoosh", .4), "burst": ("pop", .4), "cursor": ("click", .7)}
DEFAULT_ANIM = {"kick": "up", "text": "pop", "stamp": "slam", "chip": "pop", "image": "rise", "bubble": "pop", "counter": "pop",
                "count_chip": "pop", "bar": "pop", "blowtext": "pop", "rays_icon": "pop", "icon": "drop", "doodle": "burst",
                "nosign": "pop", "price": "slam", "cta": "pop"}


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def emoji_code(s):
    """'✏️' or '270f' -> twemoji file name"""
    if re.fullmatch(r"[0-9a-f]+(-[0-9a-f]+)*", s):
        return s
    return "-".join(f"{ord(c):x}" for c in s if ord(c) != 0xFE0F)


class Clock:
    """phrase -> video time, using the aligned script words"""

    def __init__(self, words, fill=lambda s: s):
        self.words = words; self.n = [norm(w[2]) for w in words]; self.fill = fill

    def find(self, phrase, after=0.0):
        toks = [norm(t) for t in phrase.split() if norm(t)]
        for i in range(len(self.n)):
            if self.words[i][0] >= after - 0.05 and self.n[i:i + len(toks)] == toks:
                return self.words[i][0]
        ctx = " ".join(w[2] for w in self.words if w[0] >= after - 0.05)[:120]
        raise SystemExit(f'scenes.json: phrase "{phrase}" not found after {after:.2f} s. Script from there: "{ctx}..."')

    def at(self, spec, base):
        if isinstance(spec, (int, float)):
            return float(spec)
        m = re.match(r"^(.*?)\s*([+-]\d+(?:\.\d+)?)?$", self.fill(spec).strip())
        phrase, off = m.group(1).strip(), float(m.group(2) or 0)
        return round(max(0.0, (self.find(phrase, base) if phrase else base) + off), 3)


class Ctx:
    def __init__(self, prj, clock, t0, t1):
        self.prj, self.clock, self.t0, self.t1 = prj, clock, t0, t1
        self.icons, self.sfx = set(), []

    def at(self, spec, base=None):
        return self.clock.at(spec, self.t0 if base is None else base)

    def text(self, s):
        return html.escape(self.prj.fill(str(s))).replace("\n", "<br>")

    def icon(self, it, key="icon", size=None, cls="ico", style=""):
        code = emoji_code(it[key]); self.icons.add(code)
        return f'<img class="{cls}" src="assets/icons/{code}.svg" style="width:{size or it.get(key + "_size", 110)}px;{style}">'

    def sound(self, it, anim, t):
        s = it.get("sfx", SFX.get(anim))
        if s:
            kind, gain = (s, .5) if isinstance(s, str) else s
            self.sfx.append([round(t + (0.18 if kind == "boom" else 0), 3), kind, gain])


def attrs(it, ctx, anim, t, extra=""):
    a = f'data-a="{anim}" data-at="{t:.3f}"'
    if it.get("rot"):
        a += f' data-rot="{it["rot"]}"'
    if it.get("out"):
        a += f' data-out="{ctx.at(it["out"]):.3f}"'
    if it.get("float"):
        a += ' data-float="1"'
    if it.get("pulse"):
        a += ' data-pulse="1"'
    return a + extra


def wrap(it, ctx, inner, anim, t, extra=""):
    """centred row, or absolutely placed when "left" is given"""
    a = attrs(it, ctx, anim, t, extra)
    if "left" in it:
        return f'<div class="abs a" {a} style="left:{it["left"]}px;top:{it.get("top", 200)}px">{inner}</div>'
    return f'<div class="row a" {a} style="top:{it.get("top", 200)}px">{inner}</div>'


def strike(it, ctx):
    return f'<span class="strike a" data-a="draw" data-at="{ctx.at(it["strike_at"]):.3f}"></span>' if it.get("strike_at") else ""


def text_span(it, ctx, size="l", color="ink"):
    size = it.get("size", size); px = SIZES.get(size, size)
    color = it.get("color", color)
    cls = ["txt"]; style = [f"font-size:{px}px"]
    if it.get("serif"):
        cls.append("serif")
    if it.get("stroke", color in ("white", "accent", "accent2") and not it.get("serif")) or it.get("rainbow"):
        cls.append("stroke")
    if it.get("highlight"):
        cls.append("hl")
    if it.get("rainbow"):
        chars = ctx.prj.fill(it["text"])
        body = "".join(f'<span style="color:{RAINBOW[i % len(RAINBOW)]}">{html.escape(c)}</span>' for i, c in enumerate(chars))
        style.append("letter-spacing:.04em")
    else:
        body = ctx.text(it["text"]); style.append(f"color:{COLORS.get(color, color)}")
    s = strike(it, ctx)
    return f'<span class="{" ".join(cls)}{" rel" if s else ""}" style="{";".join(style)}">{body}{s}</span>'


def chip_html(it, ctx, t=None):
    bg = {"white": "", "ink": "background:var(--ink);color:#fff", "accent": "background:var(--accent);color:#fff",
          "navy": "background:var(--navy);color:#fff", "accent2": "background:var(--accent2);color:#fff", "grey": ""}[it.get("bg", "white")]
    cls = "chip grey" if it.get("bg") == "grey" else "chip"
    size = SIZES.get(it.get("size", 58), it.get("size", 58))
    doodle = f'<img src="assets/img/{it["doodle"]}" style="width:{int(size * 1.6)}px">' if it.get("doodle") else ""
    ic = ctx.icon(it, size=int(size * 1.25), cls="") if it.get("icon") else ""
    a = f' a" data-a="pop" data-at="{t:.3f}' if t is not None else ""
    return f'<span class="{cls}{a}" style="font-size:{size}px;{bg}">{doodle}{ctx.text(it["text"])}{ic}{strike(it, ctx)}</span>'


def render(it, ctx):
    kind = it["type"]
    t = ctx.at(it.get("at", "+0"))
    anim = it.get("anim", DEFAULT_ANIM.get(kind, "pop"))
    if kind not in ("tiles", "steps", "scribble", "arrow", "html"):
        ctx.sound(it, anim, t)
    if kind == "kick":
        return wrap(it, ctx, f'<span class="kick">{ctx.text(it["text"])}</span>', anim, t)
    if kind == "text":
        ic = ctx.icon(it, size=it.get("icon_size", 120)) if it.get("icon") else ""
        return wrap(it, ctx, text_span(it, ctx) + ic, anim, t)
    if kind == "stamp":
        ic = ctx.icon(it, size=it.get("icon_size", 100), cls="") if it.get("icon") else ""
        return wrap(it, ctx, f'<span class="stamp" style="font-size:{SIZES.get(it.get("size", 104), it.get("size", 104))}px">'
                             f'{ctx.text(it["text"])}{ic}</span>', anim, t)
    if kind == "chip":
        return wrap(it, ctx, chip_html(it, ctx), anim, t)
    if kind == "image":
        img = f'<img class="img" src="assets/img/{it["src"]}" style="width:{it.get("width", 600)}px">'
        return wrap(it, ctx, f'<div class="card pic">{img}</div>' if it.get("card", True) else img, anim, t)
    if kind == "bubble":
        lines = [ctx.text(x) for x in it["lines"]]
        last = lines[-1]
        if it.get("underline_at"):
            last += (f'<span class="strike a" data-a="draw" data-at="{ctx.at(it["underline_at"]):.3f}" '
                     'style="background:var(--accent);top:96%;height:12px"></span>')
        body = "<br>".join(lines[:-1] + [f'<span class="rel" style="color:var(--accent)">{last}</span>'])
        return wrap(it, ctx, f'<div class="card bubble"><div class="txt serif" style="font-size:{it.get("size", 104)}px;'
                             f'line-height:1.05">{body}</div></div>', anim, t)
    if kind == "scribble":
        return (f'<svg class="scrib" viewBox="0 0 960 700" style="top:{it.get("top", 160)}px"><path class="a" data-a="draw" '
                f'data-at="{t:.3f}" data-dur="{it.get("dur", 0.9)}" fill="none" stroke="var(--ink)" stroke-width="16" '
                'stroke-linecap="round" stroke-linejoin="round" d="M60 420 C140 200 220 620 300 380 S420 160 470 420 S600 640 640 330 '
                'S790 120 860 400 C900 520 760 560 700 470 S560 300 480 520 S300 640 220 470 S120 330 180 260"/></svg>')
    if kind == "counter":
        ct = ctx.at(it.get("count_at", it.get("at", "+0")))
        ctx.sfx.append([round(ct + 1.3, 3), "ding", .4])
        return wrap(it, ctx, f'<div class="card badge"><div class="ring spin"></div><div class="count txt stroke" data-to="{ctx.prj.fill(str(it["to"]))}" '
                             f'data-at="{ct:.3f}" style="font-size:{it.get("size", 250)}px;color:var(--accent);line-height:.9"></div>'
                             f'<div class="txt" style="font-size:66px">{ctx.text(it.get("label", ""))}</div></div>', anim, t)
    if kind == "count_chip":
        ct = ctx.at(it.get("count_at", it.get("at", "+0"))) + 0.07
        return wrap(it, ctx, f'<span class="chip" style="font-size:{it.get("size", 48)}px"><span style="color:var(--accent)">'
                             f'<span class="count" data-to="{ctx.prj.fill(str(it["to"]))}" data-at="{ct:.3f}"></span>{ctx.text(it.get("suffix", ""))}</span>'
                             f'&nbsp;{ctx.text(it.get("label", ""))}</span>', anim, t)
    if kind == "tiles":
        tiles = []
        for x in it["items"]:
            tt = ctx.at(x["at"]); ctx.sound(x, "pop", tt); ctx.sfx.append([round(tt + 0.33, 3), "ding", .25])
            check = f'<img class="check a" data-a="pop" data-at="{tt + 0.33:.3f}" src="assets/icons/2705.svg">'; ctx.icons.add("2705")
            fs = 50 if len(ctx.prj.fill(x["label"])) < 9 else 40
            tiles.append(f'<div class="card tile a" data-a="pop" data-at="{tt:.3f}" data-rot="{x.get("rot", 0)}">'
                         f'{ctx.icon(x, size=170)}<span class="lbl" style="font-size:{fs}px">{ctx.text(x["label"])}</span>{check}</div>')
        return f'<div class="row" style="top:{it.get("top", 230)}px;gap:36px">{"".join(tiles)}</div>'
    if kind == "steps":
        chips = []
        for i, x in enumerate(it["items"]):
            tt = ctx.at(x["at"]); ctx.sfx.append([tt, "tick", .6])
            x = {"bg": "accent" if i == len(it["items"]) - 1 else "navy", **x}
            chips.append(chip_html(x, ctx, tt))
        return f'<div class="row" style="top:{it.get("top", 870)}px">{"".join(chips)}</div>'
    if kind == "bar":
        d = ctx.at(it["drain_at"])
        return wrap(it, ctx, f'<div class="card barwrap"><span class="txt" style="font-size:54px">{ctx.text(it["label"])}</span>'
                             f'<div class="track"><div class="fill" data-drain="{d:.3f}"></div></div></div>', anim, t)
    if kind == "blowtext":
        word = ctx.prj.fill(it["text"]); px = SIZES.get(it.get("size", "xxl"), it.get("size", "xxl"))
        chars = "".join(f'<span class="ch">{html.escape(c)}</span>' for c in word)
        ic = ctx.icon(it, size=140, cls="ico ch") if it.get("icon") else ""
        color = COLORS.get(it.get("color", "white"), it.get("color", "white"))
        inner = f'<span class="txt stroke" style="font-size:{px}px;color:{color}">{chars}</span>{ic}'
        return wrap(it, ctx, inner, anim, t, f' data-blow="{ctx.at(it["blow_at"]):.3f}"')
    if kind == "rays_icon":
        s = it.get("size", 500); left = it.get("left", (1080 - s) // 2)
        return (f'<div class="abs a" {attrs(it, ctx, anim, t)} style="left:{left}px;top:{it.get("top", 150)}px;width:{s}px;height:{s}px">'
                '<div class="abs spin" style="inset:0;border-radius:50%;background:repeating-conic-gradient(#fff 0deg 12deg, '
                'rgba(255,255,255,0) 12deg 24deg);opacity:.85"></div>'
                f'{ctx.icon(it, size=int(s * .56), cls="abs ico", style=f"left:{int(s * .22)}px;top:{int(s * .22)}px")}</div>')
    if kind == "icon":
        it = {"float": True, **it}
        code = emoji_code(it["icon"]); ctx.icons.add(code)
        return (f'<img class="abs ico a" {attrs(it, ctx, anim, t)} src="assets/icons/{code}.svg" '
                f'style="left:{it["left"]}px;top:{it["top"]}px;width:{it.get("size", 140)}px">')
    if kind == "doodle":
        return (f'<img class="abs a" {attrs(it, ctx, anim, t)} src="assets/img/{it["src"]}" '
                f'style="left:{it["left"]}px;top:{it["top"]}px;width:{it.get("width", 200)}px">')
    if kind == "nosign":
        s = ctx.at(it["strike_at"]) if it.get("strike_at") else 0
        if s:
            ctx.sfx.append([s, "whoosh", .3])
        svg = (f'<svg class="abs" viewBox="0 0 340 340" style="inset:0"><circle class="a" data-a="draw" data-at="{s:.3f}" data-dur="0.35" '
               'cx="170" cy="170" r="130" fill="none" stroke="var(--red)" stroke-width="22"/><line class="a" data-a="draw" '
               f'data-at="{s + 0.23:.3f}" data-dur="0.25" x1="78" y1="78" x2="262" y2="262" stroke="var(--red)" stroke-width="22" '
               'stroke-linecap="round"/></svg>') if it.get("strike_at") else ""
        label = f'<div class="txt{" serif" if it.get("serif", True) else ""}" style="font-size:60px;margin-top:34px;white-space:normal">' \
                f'{ctx.text(it.get("label", ""))}</div>'
        return (f'<div class="abs a" {attrs(it, ctx, anim, t)} style="left:{it["left"]}px;top:{it.get("top", 200)}px;width:360px;text-align:center">'
                '<div class="card" style="width:340px;height:340px;display:flex;align-items:center;justify-content:center;position:relative">'
                f'{ctx.icon(it, size=210)}{svg}</div>{label}</div>')
    if kind == "arrow":
        return (f'<svg class="abs" viewBox="0 0 200 120" style="left:{it["left"]}px;top:{it["top"]}px;width:{it.get("width", 200)}px">'
                f'<path class="a" data-a="draw" data-at="{t:.3f}" data-dur="0.4" d="M10 60 H170 M130 20 L180 60 L130 100" fill="none" '
                'stroke="var(--ink)" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    if kind == "price":
        lines = it.get("lines", ["", it.get("text", ""), ""])
        spans = "".join(f'<span style="font-size:{s}px">{ctx.text(x)}</span>' for x, s in zip(lines, (42, 120, 40)) if x)
        return wrap(it, ctx, f'<div class="burst"><div class="star spin"></div>{spans}</div>', anim, t)
    if kind == "cta":
        it = {"pulse": True, **it}
        size = it.get("size", 68); text = ctx.prj.fill(it["text"])
        ic = ctx.icon(it, size=int(size * 1.1), cls="") if it.get("icon") else ""
        out = wrap(it, ctx, f'<span class="chip" style="font-size:{size}px;background:var(--ink);color:#fff">{ctx.text(text)}{ic}</span>', anim, t)
        if it.get("cursor_at"):
            ct = ctx.at(it["cursor_at"]); ctx.sound({}, "cursor", ct + 0.45); ctx.icons.add("1f449")
            w = 0.52 * size * len(text) + (size * 1.1 if ic else 0) + 90
            x = int(540 + w / 2 - 110); y = it.get("top", 1060) + 20
            out += (f'<img class="cursor a" data-a="cursor" data-at="{ct:.3f}" data-tx="{x + 30}" data-ty="{y + 30}" '
                    f'src="assets/icons/1f449.svg" style="left:{x}px;top:{y}px;transform:rotate(-30deg)">')
        return out
    if kind == "html":
        return re.sub(r"\{at:([^}]*)\}", lambda m: f'data-at="{ctx.at(m.group(1)):.3f}"', ctx.prj.fill(it["html"]))
    raise SystemExit(f"scenes.json: unknown item type {kind!r}")


def captions(words, ccfg, dur):
    key = {norm(k) for k in ccfg.get("keywords", [])}
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= ccfg.get("max_words", 3) or len(" ".join(x[2] for x in cur)) >= ccfg.get("max_chars", 18) or w[2][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, ch in enumerate(chunks):
        t0 = ch[0][0]; t1 = min(chunks[i + 1][0][0] if i + 1 < len(chunks) else dur, ch[-1][1] + 0.45)
        sp = " ".join(f'<span class="w"{" data-k=\"1\"" if norm(w[2]) in key else ""} data-at="{w[0]:.3f}">{html.escape(w[2])}</span>'
                      for w in ch)
        out.append(f'<div class="cap" data-t0="{t0:.3f}" data-t1="{t1:.3f}">{sp}</div>')
    return out


def build(prj, words, vodur):
    cfg = prj.cfg
    dur = round(vodur + cfg["vo"].get("tail_s", 1.0), 3)
    clock = Clock(words, prj.fill)
    spec = json.load(open(prj.p("scenes.json")))
    heights = json.load(open(prj.p("build", "stickers", "heights.json")))
    # scene start times: just before their first phrase, always moving forward
    starts = []
    for i, sc in enumerate(spec["scenes"]):
        prev = starts[-1] if starts else 0.0
        starts.append(0.0 if i == 0 else max(prev + 0.1, round(clock.at(sc["at"], prev) - 0.06, 3)))
    scenes_html, flash, sfx, icons, poses, log = [], [], [], set(), [], []
    for i, sc in enumerate(spec["scenes"]):
        t0 = starts[i]; t1 = starts[i + 1] if i + 1 < len(starts) else dur
        ctx = Ctx(prj, clock, t0, t1)
        body = "\n".join("    " + render(it, ctx) for it in sc.get("items", []))
        scenes_html.append(f'  <!-- {html.escape(sc["at"] if isinstance(sc["at"], str) else str(sc["at"]))} -->\n'
                           f'  <div class="scene" data-t0="{t0:.3f}" data-t1="{t1:.3f}">\n{body}\n  </div>')
        if sc.get("flash"):
            flash.append(t0)
        if sc.get("riser"):
            sfx.append([round(max(0, t0 - 0.6), 3), "riser", .5])
        if i:
            sfx.append([round(t0 - 0.25, 3), "whoosh", .5])
        sfx += ctx.sfx + [[ctx.at(a), k, g] for a, k, g in sc.get("sfx", [])]; icons |= ctx.icons
        for j, p in enumerate(sc.get("poses", [])):
            if p["pose"] not in heights:
                raise SystemExit(f'scenes.json: pose "{p["pose"]}" has no sticker (have: {", ".join(sorted(heights))})')
            poses.append((t0 if j == 0 else ctx.at(p["at"]), p["pose"], p.get("x", 0), j == 0))
        log.append(f"{t0:7.2f}-{t1:7.2f}  {sc['at']}")
    stk = []
    for i, (t, name, x, big) in enumerate(poses):
        e = poses[i + 1][0] if i + 1 < len(poses) else dur
        stk.append(f'  <img class="stk" src="assets/stk/{name}.png" style="height:{heights[name]}px" data-t0="{t:.3f}" '
                   f'data-t1="{e:.3f}" data-x="{x}" data-big="{int(big)}">')
        log.append(f"   {t:7.2f}  pose {name}")
    bgc = cfg.get("background", {})
    bg = ['  <div class="rays" id="rays"></div>'] if bgc.get("rays", True) else []
    bg += [f'  <img class="bgd" src="assets/img/{src}" style="left:{x}px;top:{y}px">' for src, (x, y) in zip(bgc.get("doodles", []), SPOTS)]
    theme = {**THEME, **cfg.get("theme", {})}
    page = open(os.path.join(HERE, "template.html")).read()
    for k, v in {"{{THEME_CSS}}": " ".join(f"--{k}: {v};" for k, v in theme.items()), "{{BG}}": "\n".join(bg),
                 "{{SCENES}}": "\n".join(scenes_html), "{{STK}}": "\n".join(stk), "{{FLASH}}": json.dumps(flash),
                 "{{CAPS}}": "\n".join("    " + c for c in captions(words, cfg.get("captions", {}), dur))
                 if cfg.get("captions", {}).get("enabled", True) else "", "{{DUR}}": f"{dur}"}.items():
        page = page.replace(k, v)
    sfx.sort(); thin = []
    for c in sfx:   # no two hits closer than 0.12 s
        if not thin or c[0] - thin[-1][0] > 0.12 or c[1] in ("riser", "sparkle", "boom"):
            thin.append(c)
    return page, thin, icons, dur, log


def read_stereo(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).reshape(-1, 2)


def duck_curve(vo, depth_db, sr=48000):
    """1.0 where the voice is quiet, 10^(-depth/20) while it speaks; 80 ms in, 350 ms out"""
    hop = sr // 100
    n = len(vo) // hop
    rms = np.sqrt((vo[:n * hop] ** 2).mean(1).reshape(n, hop).mean(1) + 1e-12)
    act = (20 * np.log10(rms) > -40).astype(np.float32)
    held = np.array([act[max(0, i - 35):i + 8].max() for i in range(n)])   # open slightly early, close after the phrase
    k = np.exp(-np.arange(-15, 16) ** 2 / 50); held = np.convolve(held, k / k.sum(), "same")
    g = 1 - (1 - 10 ** (-depth_db / 20)) * np.clip(held, 0, 1)
    return np.repeat(g, hop)


def mix(prj, dur, out):
    """voice + synthesized SFX + optional background music (levelled to the voice, ducked under it)"""
    def b(*x):
        return prj.p("build", *x)
    subprocess.run([sys.executable, os.path.join(HERE, "sfx.py"), b("sfx_cues.json"), str(dur), b("sfx.wav")], check=True)
    ins, chain, n = ["-i", b("vo.wav"), "-i", b("sfx.wav")], f"[0:a]apad=whole_dur={dur}[v];[1:a]volume={prj.cfg.get('sfx_gain', 0.5)}[s];", 2
    m = prj.cfg.get("music")
    if m:
        src = prj.p(m["file"]) if "file" in m else b("music.wav")
        # same loudness as the voice (-15 LUFS) + gain_db (-6 dB = half volume), looped/trimmed to the video, faded out
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", src, "-t", str(dur), "-af",
                        f"loudnorm=I={-15 + m.get('gain_db', -6)}:TP=-2:LRA=11,afade=t=out:st={max(0, dur - 1.5)}:d=1.5",
                        "-ar", "48000", "-ac", "2", b("music_level.wav")], check=True)
        mus = read_stereo(b("music_level.wav"))
        g = duck_curve(read_stereo(b("vo.wav")), m.get("duck_db", 4))
        g = np.concatenate([g, np.ones(max(0, len(mus) - len(g)))])[:len(mus)]
        st = (np.clip(mus * g[:, None], -1, 1) * 32767).astype(np.int16)
        w = wave.open(b("music_duck.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(st.tobytes()); w.close()
        ins += ["-i", b("music_duck.wav")]; chain += "[2:a]apad=whole_dur=" + str(dur) + "[m];"; n = 3
    chain += "[v][s]" + ("[m]" if n == 3 else "") + f"amix=inputs={n}:normalize=0:duration=longest,atrim=0:{dur},alimiter=limit=0.95[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", chain, "-map", "[a]", "-ar", "48000", out], check=True)


def main():
    prj = Project(sys.argv[1])
    words = json.load(open(prj.p("build", "words.json")))
    vodur = json.load(open(prj.p("build", "edl.json")))["dur"]
    page, sfx, icons, dur, log = build(prj, words, vodur)
    out = prj.p("build", "reel"); a = f"{out}/assets"
    for d in ("icons", "fonts", "stk", "img"):
        os.makedirs(f"{a}/{d}", exist_ok=True)
    for c in icons:
        if not os.path.exists(f"{NM}/@twemoji/svg/{c}.svg"):
            raise SystemExit(f"no Twemoji icon {c} (check the emoji in scenes.json)")
        shutil.copy(f"{NM}/@twemoji/svg/{c}.svg", f"{a}/icons/{c}.svg")
    F = f"{NM}/@fontsource"
    shutil.copy(f"{F}/fredoka/files/fredoka-latin-600-normal.woff2", f"{a}/fonts/fredoka-600.woff2")
    shutil.copy(f"{F}/fredoka/files/fredoka-latin-700-normal.woff2", f"{a}/fonts/fredoka-700.woff2")
    shutil.copy(f"{F}/instrument-serif/files/instrument-serif-latin-400-italic.woff2", f"{a}/fonts/serif-italic.woff2")
    shutil.copy(f"{NM}/gsap/dist/gsap.min.js", f"{a}/gsap.min.js")
    shutil.copytree(prj.p("build", "stickers"), f"{a}/stk", dirs_exist_ok=True)
    if os.path.isdir(prj.p("input", "img")):
        shutil.copytree(prj.p("input", "img"), f"{a}/img", dirs_exist_ok=True)
    open(f"{out}/index.html", "w").write(page)
    json.dump(sfx, open(prj.p("build", "sfx_cues.json"), "w"))
    open(prj.p("build", "timeline.txt"), "w").write("\n".join(log) + "\n")
    mix(prj, dur, f"{a}/mix.wav")
    print(f"{len(log)} timeline entries, {len(sfx)} sfx, {dur:.2f} s -> {out}/index.html")


if __name__ == "__main__":
    main()
