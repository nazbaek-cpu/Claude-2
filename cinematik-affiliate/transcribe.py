"""Whisper word timings -> build/words.json and a draft subtitle list (build/subs_draft.json).

Copy the draft into project.json "subs", fix the spelling, then plan the segments on those times.

    python transcribe.py projects/<name> [--model medium] [--lang ms]
"""
import argparse, json, os, subprocess
import numpy as np
from faster_whisper import WhisperModel

MAX_CHARS, GAP = 36, 0.25

def phrases(words):
    """split on punctuation, sentence starts, pauses and length"""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text = " ".join(x["w"] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        # Whisper often drops full stops but still capitalises the next sentence
        if (nxt is None or w["w"][-1] in ",.?!" or nxt["s"] - w["e"] > GAP or nxt["w"][:1].isupper()
                or len(text) + len(nxt["w"]) + 1 > MAX_CHARS):
            out.append([round(cur[0]["s"], 2), round(nxt["s"] - 0.03, 2) if nxt else None, text])
            cur = []
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--model", default="medium"); ap.add_argument("--lang", default="ms")
    args = ap.parse_args()
    cfg = json.load(open(os.path.join(args.project, "project.json")))
    src = os.path.join(args.project, cfg["source"])
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, language=args.lang, word_timestamps=True, vad_filter=True,
                               initial_prompt=cfg.get("whisper_prompt"))
    words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words]
    build = os.path.join(args.project, "build"); os.makedirs(build, exist_ok=True)
    json.dump(words, open(os.path.join(build, "words.json"), "w"), ensure_ascii=False, indent=1)
    subs = phrases(words)
    json.dump(subs, open(os.path.join(build, "subs_draft.json"), "w"), ensure_ascii=False, indent=1)
    for a, b, txt in subs: print(f"{a:6.2f} {'end' if b is None else f'{b:6.2f}'}  {txt}")

if __name__ == "__main__":
    main()
