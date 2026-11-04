"""Template kertas (styles/template-kertas.md): torn paper titles, sticker props, stamps and marks on solid wood, the spoken line in
big type, one phrase at a time (no note cards). Build a project.json from Python:

    from templates.kertas import *
    scenes = [scene(0.0, [label("ANAK SUKA MELUKIS?", 0.0),
                          say("kenapa ada anak yang lukisan dia", "NAMPAK HIDUP", 0.0, 2.72),
                          kira(0.05, [("berfikir", 0.0)], slide=True),
                          stk("pensel_warna", 1.0, tag="LUKISAN")], cut=True), ...]
    write("projects/<name>", scenes, whisper_prompt="...")

Scene rule of thumb (the 120k-view structure): question about the child who succeeds -> "RAHSIANYA:" one-word secret ->
"ANAK LAIN..." / "CALON LAIN..." the mistake (stamp) -> product as the secret (photos change with each phrase, no
character) -> "SIAP DENGAN:" proof with a tick -> "INGAT!" promise + CTA. Every scene starts on a VO phrase; labels
come in 0.5 s before their scene so they ride the whip.
"""
import json, os

def label(text, at):
    """torn paper section title at the top"""
    return {"kind": "label", "text": text, "at": at, "y": 215, "size": 62, "rot": -1.5}

def say(text, key, at, until, gold=False):
    """one spoken phrase: small line, then the key words big (yellow, or orange with gold=True)"""
    d = {"kind": "say", "text": text, "key": key, "at": at, "until": until, "y": 395, "size1": 60, "size2": 96}
    if gold: d["color"] = "gold"
    return d

def kira(at, poses, x=290, slide=False, folder="kira"):
    """the character (styles/watak-kak-kira.md): poses [(name, at)]; slide=True walks in (first scene and CTA)"""
    d = {"kind": "doodle", "at": at, "x": x, "y": 1120, "h": 640, "poses": [[f"{folder}/{p}.png", t] for p, t in poses]}
    if slide: d["enter"] = "slide"
    return d

def stk(name, at, until=99, x=790, y=1060, size=210, tag=None, rot=0, anim="pop", good=False, emoji=False):
    """icon from input/icons (or a Fluent emoji with emoji=True) as a white-edged sticker; tag puts a paper label above it"""
    d = {"kind": "sticker", ("emoji" if emoji else "img"): name if emoji else f"icons/{name}.png", "at": at, "until": until,
         "x": x, "y": y, "size": size, "rot": rot, "anim": anim, "edge": 11}
    if tag: d["tag"] = tag
    if good: d["good"] = True
    return d

def marks(at, x, y, typ="q", until=99, size=90):
    """three red question marks (q) over the head, or a green tick"""
    return {"kind": "marks", "type": typ, "at": at, "until": until, "x": x, "y": y, "size": size}

def stamp(text, at, x=760, y=1400, rot=-7, size=54):
    """red rubber stamp on a paper scrap (KAKU!, SEPARUH JALAN, ...)"""
    return {"kind": "stamp", "text": text, "at": at, "x": x, "y": y, "rot": rot, "size": size}

def card(img, at, until=99, w=880, x=540, y=1080, rot=0):
    """product photo as a die-cut sticker; small one for the CTA: w=440, x=790, y=1060"""
    return {"kind": "card", "img": img, "at": at, "until": until, "x": x, "y": y, "w": w, "rot": rot, "sticker": True}

def cta(at, text="Tekan link dekat bawah"):
    return {"kind": "cta", "text": text, "at": at, "y": 1690}

def scene(start, items, cut=False):
    sc = {"start": start, "items": items}
    if cut: sc["in"] = "cut"
    return sc

def config(scenes, whisper_prompt="", theme="kayu"):
    return {"type": "explainer", "source": "input/vo.mp4", "preset": "edukasi", "bold_text": True, "theme": theme,
            "whisper_prompt": whisper_prompt, "scenes": scenes}

def write(prj, scenes, whisper_prompt="", theme="kayu"):
    with open(os.path.join(prj, "project.json"), "w") as f:
        json.dump(config(scenes, whisper_prompt, theme), f, indent=1, ensure_ascii=False)
