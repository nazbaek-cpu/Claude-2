"""Word timings for the voiceover, spelled exactly like script.txt.

usage: align.py <project> [--retranscribe]
Whisper (word timestamps) is aligned to the script, so captions use the script's spelling. Stretches of the script
Whisper skipped are transcribed again on their own; words still missing get a time inside the speech between their
neighbours. Anything spoken after the last script word (e.g. a TTS glitch at the end of the file) is ignored.
Writes build/whisper.json (cache) and build/words_src.json: [[start, end, word], ...] in VO-file seconds.
"""
import difflib, json, os, re, sys
from common import Project, load_audio16, silences

SR = 16000
_model = None


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def script_words(text):
    """script text -> words as they should appear in captions (punctuation kept)"""
    return [w for w in re.split(r"\s+", text.replace("\n", " ")) if norm(w)]


def whisper_words(tr, offset=0.0):
    """flatten whisper segments; glue "-main" pieces onto the previous word; drop zero-length and stretched words"""
    out = []
    for seg in tr:
        for a, b, w, *_ in seg["w"]:
            w = w.strip(); a += offset; b += offset
            if not w:
                continue
            if w.startswith("-") and out:
                out[-1][1] = b; out[-1][2] += w
            elif 0.02 < b - a <= 2.0:   # a "word" lasting seconds means Whisper skipped the text there
                out.append([a, b, w])
    return out


def match(script, heard):
    """script words + heard [[a, b, w]] -> per script word [a, b] or None"""
    A = [norm(w) for w in script]; B = [norm(w[2]) for w in heard]
    times = [None] * len(script)
    for op, i0, i1, j0, j1 in difflib.SequenceMatcher(a=A, b=B, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i1 - i0 == j1 - j0):
            for k in range(i1 - i0):
                times[i0 + k] = list(heard[j0 + k][:2])
        elif op == "replace":   # e.g. "kita orang" heard as "kitorang": spread the heard span over the script words
            a, b = heard[j0][0], heard[j1 - 1][1]
            n = sum(len(A[i]) for i in range(i0, i1)); t = a
            for i in range(i0, i1):
                d = (b - a) * len(A[i]) / n; times[i] = [t, t + d]; t += d
    return times


def gaps(times, min_len=1):
    """runs [i, j) of script words without a time"""
    out, i = [], 0
    while i < len(times):
        if times[i] is None:
            j = i
            while j < len(times) and times[j] is None:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def speech_span(t0, t1, sil):
    """narrow (t0, t1) to where there is actually speech, using the silence list"""
    for s, e in sil:
        if s <= t0 + 0.25 and e > t0:
            t0 = min(e, t1)
        if e >= t1 - 0.25 and s < t1:
            t1 = max(s, t0)
    return t0, t1


def interpolate(times, script, sil):
    """give the remaining missing words a share of the speech between their neighbours (by word length)"""
    A = [norm(w) for w in script]
    for i, j in gaps(times):
        t0 = times[i - 1][1] + 0.05 if i > 0 else 0.0
        t1 = times[j][0] - 0.05 if j < len(times) else t0 + 0.4 * (j - i)
        t0, t1 = speech_span(t0, max(t1, t0 + 0.1), sil)
        n = sum(len(A[k]) for k in range(i, j)); t = t0
        for k in range(i, j):
            d = (t1 - t0) * len(A[k]) / n; times[k] = [t, t + d]; t += d
    return times


def snap(words, sil):
    """Whisper often starts a word inside the pause before it: move such starts to the end of the pause"""
    for w in words:
        for s, e in sil:
            if s - 0.02 <= w[0] < e - 0.05 and w[1] > e:
                w[0] = round(e, 3)
            if s < w[1] <= e + 0.02 and w[0] < s:
                w[1] = round(s, 3)
    return words


def align(script, heard, sil=(), retry=None):
    """script words + heard words -> [[a, b, script_word]]; retry(t0, t1) -> heard words for a skipped stretch"""
    times = match(script, heard)
    if retry:
        for i, j in gaps(times, 3):
            t0 = times[i - 1][1] if i > 0 else 0.0
            t1 = times[j][0] if j < len(times) else t0 + 0.6 * (j - i) + 2
            sub = match(script[i:j], retry(max(0.0, t0 - 0.1), t1 + 0.1))
            times[i:j] = [s if s is None or (t0 - 0.2 <= s[0] and s[1] <= t1 + 0.2) else None for s in sub]
    times = interpolate(times, script, sil)
    return snap([[round(a, 3), round(b, 3), w] for (a, b), w in zip(times, script)], sil)


def transcribe(audio, language, model, prompt=None):
    global _model
    from faster_whisper import WhisperModel
    if _model is None:
        _model = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=4)
    segs, _ = _model.transcribe(audio, language=language, word_timestamps=True, beam_size=5, initial_prompt=prompt)
    out = []
    for s in segs:
        out.append({"s": s.start, "e": s.end, "t": s.text, "w": [(w.start, w.end, w.word, w.probability) for w in s.words]})
        print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}", flush=True)
    return out


def main():
    prj = Project(sys.argv[1]); vo = prj.p(prj.cfg["vo"]["file"])
    lang, model, prompt = prj.cfg.get("language", "ms"), prj.cfg.get("whisper_model", "large-v3"), prj.cfg.get("whisper_prompt")
    cache = prj.p("build", "whisper.json")
    audio = load_audio16(vo)
    if "--retranscribe" in sys.argv or not os.path.exists(cache):
        json.dump(transcribe(audio, lang, model, prompt), open(cache, "w"), ensure_ascii=False, indent=1)

    def retry(t0, t1):
        print(f"re-listening to {t0:.2f}-{t1:.2f} s", flush=True)
        return whisper_words(transcribe(audio[int(t0 * SR):int(t1 * SR)], lang, model), t0)

    words = align(script_words(prj.script()), whisper_words(json.load(open(cache))),
                  silences(vo, prj.cfg["vo"].get("silence_db", "auto"), 0.2), retry)
    json.dump(words, open(prj.p("build", "words_src.json"), "w"), ensure_ascii=False)
    print(f"{len(words)} script words timed; speech ends at {words[-1][1]:.2f} s")


if __name__ == "__main__":
    main()
