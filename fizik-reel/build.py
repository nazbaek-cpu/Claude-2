"""Generate the HyperFrames project (reel/) from the transcript, edit map and cue plan."""
import json, os, re, shutil, subprocess, html

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = f"{HERE}/work"
OUT = f"{HERE}/reel"
TW = f"{HERE}/pk/twemoji-svg-15.0.0/package"
FONTS = f"{HERE}/pk/fontsource-plus-jakarta-sans-5.3.0/package/files"

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
FIX = {"Cemelang": "Cemerlang", "numenik": "mnemonik", "Buayah,": "Ibu ayah,", "konstruk,": "Konstruk,",
       "konstruk": "Konstruk", "modul": "Modul", "better": "better"}
words = []
for seg in json.load(open(f"{WORK}/tr_large.json")):
    for a, b, w, p in seg["w"]:
        w = w.strip()
        if a >= 63.0:  # whisper duplicated the last line
            continue
        if w.startswith("-") and words:  # "anak -anak" -> "anak-anak"
            words[-1][2] += w; words[-1][1] = b; continue
        words.append([a, b, FIX.get(w, w)])

KEY = re.compile(r"(?i)^(fizik|formula|spm|mudah|senang|konstruk|tingkatan|jawapan|soalan|mnemonik|kreatif|cemerlang|link|lemah|best\w*|teknik)")
chunks, cur = [], []
for w in words:
    cur.append(w)
    txt = " ".join(x[2] for x in cur)
    if len(cur) >= 3 or len(txt) >= 17 or w[2][-1] in ".,?":
        chunks.append(cur); cur = []
if cur:
    chunks.append(cur)


# ---------------------------------------------------------------- helpers
def icon(cp, size=88, cls="ico"):
    shutil.copy(f"{TW}/{cp}.svg", f"{OUT}/assets/icons/{cp}.svg")
    return f'<img class="{cls}" src="assets/icons/{cp}.svg" style="width:{size}px;height:{size}px">'


def at(t):
    return f'data-at="{s2o(t):.3f}"'


CUES, SFX = [], []


def cue(start, end, body, cls="top", style=""):
    CUES.append((s2o(start), s2o(end), cls, style, body))


def sfx(t, kind, g=1.0):
    SFX.append([round(s2o(t), 3), kind, g])


# ---------------------------------------------------------------- cue plan (source-time words)
# 1  Subjek fizik ... banyak sangat formula nak kena ingat
chips = [("F = ma", 1.52, 60, 330), ("V = IR", 1.85, 760, 330), ("P = F/A", 2.15, 60, 460),
         ("E = mc²", 2.55, 770, 460), ("p = mv", 3.0, 60, 590), ("W = Fs", 3.42, 800, 590)]
cue(0.42, 4.76, f"""
  <div class="glass hero pop" {at(0.42)}><span class="sheen"></span>
    {icon('269b', 96)}<div><div class="kicker">SUBJEK</div><div class="huge" >FIZIK</div></div></div>
  """ + "".join(f'<div class="glass chip float pop" {at(t)} style="left:{x}px;top:{y}px">{html.escape(c)}</div>'
                for c, t, x, y in chips), cls="free")
sfx(0.38, "whoosh", 0.9); sfx(0.82, "pop", 0.8)
for c, t, x, y in chips:
    sfx(t, "pop", 0.55)
sfx(4.12, "boom", 0.5)

# 2  Sebab tu anak-anak selalu lemah dalam fizik
cue(5.27, 8.45, f"""
  <div class="glass card pop" {at(5.6)}><span class="sheen"></span>
    {icon('1f4c9', 92)}<div class="txt"><div class="sm pop" {at(5.58)}>Anak-anak selalu</div>
    <div class="lg"><span class="pop shake" {at(6.96)} style="color:var(--pink)">lemah</span> <span class="pop" {at(7.72)}>dalam Fizik</span></div></div></div>""")
sfx(5.5, "whoosh", 0.7); sfx(6.96, "boom", 0.8)

# 3  Anak-anak yang ambil SPM tahun ni
cue(8.8, 11.9, f"""
  <div class="glass pill pop" {at(9.8)}><span class="sheen"></span>{icon('1f393', 80)}
    <span class="lg">SPM</span><span class="sm" style="margin-left:14px">tahun ni</span></div>""")
sfx(9.8, "pop", 0.9)

# 4  better dapatkan formula yang senang nak ingat
cue(11.94, 16.84, f"""
  <div class="glass card pop" {at(12.0)}><span class="sheen"></span>
    {icon('1f4a1', 96)}<div class="txt"><div class="sm pop" {at(12.72)}>Dapatkan formula</div>
    <div class="lg pop glow" {at(15.68)} style="color:var(--yellow)">senang nak ingat</div></div></div>""")
sfx(12.0, "whoosh", 0.6); sfx(15.68, "ding", 0.8)

# 5  modul konstruk tingkatan 5, siap ada tingkatan 4 juga
cue(17.15, 24.13, f"""
  <div class="glass card pop" {at(17.6)}><span class="sheen"></span>
    {icon('1f4d8', 96)}<div class="txt"><div class="sm">Modul</div><div class="lg">Konstruk <span style="color:var(--pink)">Fizik</span></div></div></div>
  <div class="row">
    <div class="glass chip pop" {at(20.82)}>Tingkatan <b>5</b></div>
    <div class="glass chip pop" {at(22.84)} style="color:var(--yellow)">+ Tingkatan <b>4</b></div></div>""")
sfx(17.55, "whoosh", 0.8); sfx(20.82, "pop", 0.8); sfx(22.84, "pop", 0.8); sfx(22.9, "sparkle", 0.6)

# 6  Buku ni dia bagi siap untuk cara nak ingat formula dengan mudah sekali
cue(24.61, 29.3, f"""
  <div class="glass card pop" {at(24.65)}><span class="sheen"></span>
    {icon('1f9e0', 96)}<div class="txt"><div class="sm pop" {at(26.26)}>Cara ingat formula</div>
    <div class="lg pop glow" {at(28.08)} style="color:var(--mint)">dengan mudah ✓</div></div></div>""")
sfx(24.65, "whoosh", 0.6); sfx(26.26, "pop", 0.6); sfx(28.08, "ding", 0.8)

# 7  dibuat oleh Cikgu Cemerlang Fizik
cue(29.76, 34.05, f"""
  <div class="glass card pop" {at(31.36)}><span class="sheen"></span>
    {icon('1f3c5', 96)}<div class="txt"><div class="sm">Dibuat oleh</div>
    <div class="lg pop glow" {at(32.44)} style="color:var(--yellow)">Cikgu Cemerlang Fizik</div></div></div>""")
sfx(31.36, "whoosh", 0.6); sfx(32.44, "sparkle", 0.9)

# 8  paling best dia menggunakan mnemonik dan secara kreatif dia bagi soalan
cue(34.37, 40.08, f"""
  <div class="glass pill pop" {at(34.46)}>{icon('2b50', 64)}<span class="sm">Paling best</span></div>
  <div class="glass hero pop" {at(36.22)}><span class="sheen"></span><div class="huge" style="font-size:118px">MNEMONIK</div></div>
  <div class="glass chip pop" {at(37.92)}>{icon('270f', 56)} Soalan <span style="color:var(--yellow)">&nbsp;kreatif</span></div>""")
sfx(34.46, "pop", 0.7); sfx(36.22, "whoosh", 0.9); sfx(36.3, "boom", 0.35); sfx(37.92, "pop", 0.8)

# 9  Lepas tu dia siap jawapan cara nak guna formula ...
cue(40.32, 48.45, f"""
  <div class="glass list pop" {at(40.4)}><span class="sheen"></span>
    <div class="kicker">DALAM BUKU NI</div>
    <div class="li pop" {at(40.45)}>{icon('2705', 58)}<span>Soalan</span></div>
    <div class="li pop" {at(41.26)}>{icon('2705', 58)}<span>Siap <b style="color:var(--yellow)">jawapan</b></span></div>
    <div class="li pop" {at(43.18)}>{icon('2705', 58)}<span>Cara guna formula</span></div>
    <div class="li pop" {at(47.22)}>{icon('2705', 58)}<span>Senang nak ingat</span></div></div>""")
sfx(40.38, "whoosh", 0.7)
for t in (40.45, 41.26, 43.18, 47.22):
    sfx(t, "tick", 0.9); sfx(t + 0.03, "pop", 0.45)

# 10 Teknik senang nak ingat formula fizik
cue(48.64, 52.19, f"""
  <div class="glass hero col pop" {at(48.64)}><span class="sheen"></span>
    <div class="kicker">TEKNIK</div><div class="lg pop" {at(49.48)}>Senang ingat</div>
    <div class="huge pop" {at(51.2)} style="font-size:104px;color:var(--yellow)">FORMULA</div></div>""")
sfx(48.6, "whoosh", 0.8); sfx(49.48, "pop", 0.6); sfx(51.2, "boom", 0.45)

# 11 Ibu ayah, buku ni sesuai untuk anak-anak yang nak ingat formula dengan mudah
cue(52.52, 58.07, f"""
  <div class="glass pill pop" {at(52.52)}>{icon('1f468-200d-1f469-200d-1f467', 72)}<span class="sm">Ibu ayah,</span></div>
  <div class="glass card pop" {at(53.64)}><span class="sheen"></span>
    {icon('1f3af', 92)}<div class="txt"><div class="sm">Sesuai untuk</div>
    <div class="lg">anak-anak <span class="pop" {at(56.9)} style="color:var(--mint)">ingat formula</span></div></div></div>""")
sfx(52.5, "pop", 0.7); sfx(53.64, "whoosh", 0.6); sfx(56.9, "ding", 0.6)

# 12 Dan bantu dia orang untuk menjawab soalan dengan mudah
cue(58.41, 61.56, f"""
  <div class="glass card pop" {at(58.41)}><span class="sheen"></span>
    {icon('1f4dd', 92)}<div class="txt"><div class="sm">Bantu jawab soalan</div>
    <div class="lg pop glow" {at(61.02)} style="color:var(--mint)">dengan mudah ✓</div></div></div>""")
sfx(58.4, "whoosh", 0.6); sfx(61.02, "ding", 0.7)

# 13 CTA: Boleh dapatkan dekat link di bawah
cue(61.85, 63.6, f"""
  <div class="glass cta pop" {at(61.9)}><span class="sheen"></span><span>DAPATKAN SEKARANG</span></div>
  <div class="pill2 pop" {at(62.38)}>{icon('1f447', 64, 'ico bob')}<span>Link di bawah</span></div>
  <svg class="cursor" {at(62.0)} viewBox="0 0 40 52" width="70"><path d="M3 3 L3 42 L13 33 L20 49 L27 46 L20 30 L34 30 Z" fill="#fff" stroke="#111" stroke-width="3" stroke-linejoin="round"/></svg>
  <div class="ring" {at(62.5)}></div>""", cls="ctaz")
sfx(61.85, "riser", 0.5); sfx(61.9, "whoosh", 0.7); sfx(62.5, "click", 1.0); sfx(62.52, "ding", 0.7)

# ---------------------------------------------------------------- captions
cap_html = []
CTA_T = CUES[-1][0]
chunks = [ch for ch in chunks if s2o(ch[0][0]) < CTA_T - 0.05]
for i, ch in enumerate(chunks):
    t0 = s2o(ch[0][0]); t1 = s2o(chunks[i + 1][0][0]) if i + 1 < len(chunks) else DUR
    t1 = min(t1, s2o(ch[-1][1]) + 0.5, CTA_T)
    spans = "".join(f'<span class="w{" k" if KEY.match(w[2]) else ""}" data-at="{s2o(w[0]):.3f}">{html.escape(w[2])}</span> '
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
