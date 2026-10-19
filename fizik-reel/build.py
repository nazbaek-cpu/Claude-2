"""Generate the HyperFrames project (reel/) from the transcript, edit map, config.json and cues.json.

cues.json holds the per-video animation plan in SOURCE seconds. Inside a cue's html:
  {at:T}               -> data-at="<output time of source second T>"  (when the element pops in)
  {icon:CODE:SIZE}     -> Twemoji <img> (CODE = twemoji file name, e.g. 1f4a1)
  {icon:CODE:SIZE:CLS} -> same, with extra classes (e.g. "ico bob")
"""
import json, os, re, shutil, html

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = f"{HERE}/work"
OUT = f"{HERE}/reel"
NM = f"{HERE}/node_modules"
TW = f"{NM}/@twemoji/svg"
FONTS = f"{NM}/@fontsource/plus-jakarta-sans/files"

CFG = json.load(open(f"{HERE}/config.json"))
edl = json.load(open(f"{WORK}/edl.json"))
DUR = edl["dur"]


def s2o(t):
    """source seconds -> output seconds (times inside a removed pause snap to the next kept frame)"""
    for s in edl["segs"]:
        a, b = s["src"]
        if t < a:
            return s["out"]
        if t <= b:
            return s["out"] + (t - a)
    return DUR


# ---------------------------------------------------------------- transcript
def load_words(tr, fixes, drop_from=None):
    words = []
    for seg in tr:
        for a, b, w, p in seg["w"]:
            w = w.strip()
            if drop_from is not None and a >= drop_from:  # e.g. whisper repeating the last line
                continue
            if w.startswith("-") and words:  # "anak -anak" -> "anak-anak"
                words[-1][2] += w; words[-1][1] = b; continue
            words.append([a, b, fixes.get(w, w)])
    for w in words:  # also fix joined words ("main -main" -> "main-main" -> "M&M's")
        w[2] = fixes.get(w[2], w[2])
    return words


def chunk_words(words, max_words, max_chars):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x[2] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or w[2][-1] in ".,?":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


# ---------------------------------------------------------------- cue rendering
def icon(cp, size=88, cls="ico"):
    shutil.copy(f"{TW}/{cp}.svg", f"{OUT}/assets/icons/{cp}.svg")
    return f'<img class="{cls}" src="assets/icons/{cp}.svg" style="width:{size}px;height:{size}px">'


def expand(body):
    def sub(m):
        kind, arg = m.group(1), m.group(2).split(":")
        if kind == "at":
            return f'data-at="{s2o(float(arg[0])):.3f}"'
        return icon(arg[0], int(arg[1]), *arg[2:3])
    return re.sub(r"\{(at|icon):([^}]*)\}", sub, body)


def copy_assets():
    os.makedirs(f"{OUT}/assets/icons", exist_ok=True)
    os.makedirs(f"{OUT}/assets/fonts", exist_ok=True)
    for wt in (600, 800):
        shutil.copy(f"{FONTS}/plus-jakarta-sans-latin-{wt}-normal.woff2", f"{OUT}/assets/fonts/pjs-{wt}.woff2")
    shutil.copy(f"{NM}/gsap/dist/gsap.min.js", f"{OUT}/assets/gsap.min.js")
    if os.path.isdir(f"{HERE}/img"):  # per-video product images used by cues.json as assets/img/<name>
        shutil.copytree(f"{HERE}/img", f"{OUT}/assets/img", dirs_exist_ok=True)


def main():
    copy_assets()
    tcfg, ccfg = CFG["transcript"], CFG["captions"]
    words = load_words(json.load(open(f"{WORK}/tr_large.json")), tcfg["fixes"], tcfg.get("drop_words_from_s"))
    chunks = chunk_words(words, ccfg["max_words"], ccfg["max_chars"])
    key = re.compile(ccfg["keywords"])

    CUES, SFX = [], []
    for c in json.load(open(f"{HERE}/cues.json")):
        CUES.append((s2o(c["start"]), s2o(c["end"]), c.get("class", "top"), c.get("style", ""), expand(c["html"])))
        SFX += [[round(s2o(t), 3), kind, g] for t, kind, g in c.get("sfx", [])]

    # captions (hidden once the last cue, the CTA, starts)
    cap_html = []
    cap_end = CUES[-1][0] if CUES and ccfg.get("hide_from_last_cue") else DUR
    chunks = [ch for ch in chunks if s2o(ch[0][0]) < cap_end - 0.05]
    for i, ch in enumerate(chunks):
        t0 = s2o(ch[0][0]); t1 = s2o(chunks[i + 1][0][0]) if i + 1 < len(chunks) else DUR
        t1 = min(t1, s2o(ch[-1][1]) + 0.5, cap_end)
        spans = "".join(f'<span class="w{" k" if key.match(w[2]) else ""}" data-at="{s2o(w[0]):.3f}">{html.escape(w[2])}</span> '
                        for w in ch)
        cap_html.append(f'<div class="cap" data-t0="{t0:.3f}" data-t1="{t1:.3f}">{spans.strip()}</div>')

    cue_html = []
    for i, (t0, t1, cls, style, body) in enumerate(CUES):
        cue_html.append(f'<div class="cue {cls}" id="c{i}" data-t0="{t0:.3f}" data-t1="{t1:.3f}" style="{style}">{body}</div>')

    page = open(f"{HERE}/template.html").read()
    page = page.replace("{{DUR}}", f"{DUR:.3f}").replace("{{CUES}}", "\n".join(cue_html)).replace("{{CAPS}}", "\n".join(cap_html))
    open(f"{OUT}/index.html", "w").write(page)
    json.dump(SFX, open(f"{WORK}/sfx_cues.json", "w"))
    json.dump([[s2o(w[0]), s2o(w[1]), w[2]] for w in words], open(f"{WORK}/words_out.json", "w"), ensure_ascii=False)
    print(len(CUES), "cues", len(chunks), "caption chunks", len(SFX), "sfx, dur", DUR)


if __name__ == "__main__":
    main()
