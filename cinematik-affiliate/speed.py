"""Make slow talking feel brisk but natural: shrink long pauses, then a gentle pitch-preserving tempo-up.

Cuts land only inside pauses (Whisper gaps or measured silence, never across the middle of a word); the punch-in zoom that
changes on every phrase hides the jump. Project times stay in source seconds; render.load() maps them.

    python speed.py projects/<name>     -> build/fast.mp4 + build/timemap.json
"""
import json, os, re, subprocess, sys

def silences(src, noise_db, min_len):
    """[(start, end)] of real silence, from ffmpeg silencedetect"""
    log = subprocess.run(["ffmpeg", "-i", src, "-af", f"silencedetect=n={noise_db}dB:d={min_len}", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    return list(zip(starts, ends))

def keep_intervals(words, quiet, duration, max_pause, lead=0.15, tail=0.8):
    """source intervals to keep: each pause (Whisper gap or measured silence) longer than max_pause is cut
    down to max_pause, but never where the middle of a word would fall inside the cut"""
    gaps = [(w["e"], n["s"]) for w, n in zip(words, words[1:])] + quiet
    mids = [(w["s"] + w["e"]) / 2 for w in words]
    t0, t1 = max(0.0, words[0]["s"] - lead), min(duration, words[-1]["e"] + tail)
    cuts = []
    for a, b in sorted(gaps):
        ca, cb = max(a + max_pause / 2, t0), min(b - max_pause / 2, t1)
        if cb - ca < 0.05 or any(ca < m < cb for m in mids): continue
        if cuts and ca <= cuts[-1][1]: cuts[-1] = (cuts[-1][0], max(cuts[-1][1], cb))
        else: cuts.append((ca, cb))
    keep, start = [], t0
    for ca, cb in cuts:
        keep.append((start, ca)); start = cb
    keep.append((start, t1))
    return [(round(a, 3), round(b, 3)) for a, b in keep if b - a > 0.05]

def to_output(t, keep, tempo):
    """source time -> output time (a time inside a cut snaps to the next kept moment)"""
    acc = 0.0
    for a, b in keep:
        if t < a: return acc / tempo
        if t <= b: return (acc + t - a) / tempo
        acc += b - a
    return acc / tempo

def main():
    prj = sys.argv[1]
    cfg = json.load(open(os.path.join(prj, "project.json")))
    sp = cfg["speed"]; tempo = sp.get("tempo", 1.12); max_pause = sp.get("max_pause", 0.22)
    src = os.path.join(prj, cfg["source"]); build = os.path.join(prj, "build")
    words = json.load(open(os.path.join(build, "words.json")))
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate:format=duration", "-of", "json", src],
                                  capture_output=True, text=True, check=True).stdout)
    duration, rate = float(j["format"]["duration"]), j["streams"][0]["r_frame_rate"]
    quiet = silences(src, sp.get("silence_db", -30), max_pause + 0.08)
    num, den = map(int, rate.split("/")); fd = den / num
    # snap every piece to the frame grid so picture and sound keep exactly the same length (no lip-sync drift)
    keep = [(round(a / fd) * fd, round(b / fd) * fd) for a, b in keep_intervals(words, quiet, duration, max_pause)]
    keep = [(round(a, 4), round(b, 4)) for a, b in keep if b > a]
    vsel = "+".join(f"between(t,{a - fd / 2:.4f},{b - fd / 2:.4f})" for a, b in keep)
    asel = "+".join(f"between(t,{a},{b})" for a, b in keep)
    vf = f"select='{vsel}',setpts=N/FRAME_RATE/TB,setpts=PTS/{tempo}"
    af = f"aselect='{asel}',asetpts=N/SR/TB,atempo={tempo}"
    out = os.path.join(build, "fast.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-af", af, "-r", rate,
                    "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", out],
                   check=True)
    json.dump({"tempo": tempo, "keep": keep}, open(os.path.join(build, "timemap.json"), "w"), indent=1)
    new = to_output(duration, keep, tempo)
    print(f"speed: {duration:.1f}s -> {new:.1f}s ({len(keep) - 1} pauses shortened, tempo {tempo}) -> {out}")

if __name__ == "__main__":
    main()
