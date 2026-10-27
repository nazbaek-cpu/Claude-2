"""Make slow talking feel brisk but natural: shrink long pauses, then a gentle pitch-preserving tempo-up.

Cuts land only inside pauses (Whisper gaps or measured silence, never across the middle of a word); the punch-in zoom that
changes on every phrase hides the jump. Project times stay in source seconds; render.load() maps them.

    python speed.py projects/<name>     -> build/fast.mp4 + build/timemap.json
"""
import json, os, re, subprocess, sys
import project

def silences(src, noise_db, min_len):
    """[(start, end)] of real silence, from ffmpeg silencedetect"""
    log = subprocess.run(["ffmpeg", "-i", src, "-af", f"silencedetect=n={noise_db}dB:d={min_len}", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    return list(zip(starts, ends))

def keep_intervals(words, quiet, duration, max_pause, lead=0.15, tail=0.8, hold=()):
    """source intervals to keep: each pause (Whisper gap or measured silence) longer than max_pause is cut
    down to max_pause, but never where the middle of a word would fall inside the cut, nor inside a
    "hold" range (silent moments that matter on screen: a bite, showing the inside of the product)"""
    gaps = [(w["e"], n["s"]) for w, n in zip(words, words[1:])] + quiet
    mids = [(w["s"] + w["e"]) / 2 for w in words]
    t0, t1 = max(0.0, words[0]["s"] - lead), min(duration, words[-1]["e"] + tail)
    cuts = []
    for a, b in sorted(gaps):
        ca, cb = max(a + max_pause / 2, t0), min(b - max_pause / 2, t1)
        if cb - ca < 0.05 or any(ca < m < cb for m in mids) or any(ca < hb and cb > ha for ha, hb in hold): continue
        if cuts and ca <= cuts[-1][1]: cuts[-1] = (cuts[-1][0], max(cuts[-1][1], cb))
        else: cuts.append((ca, cb))
    keep, start = [], t0
    for ca, cb in cuts:
        keep.append((start, ca)); start = cb
    keep.append((start, t1))
    return [(round(a, 3), round(b, 3)) for a, b in keep if b - a > 0.05]

def to_output(t, keep, tempo):
    """source time -> output time; keep is in playback order (may be reordered).
    A time inside a cut snaps to the next kept moment."""
    acc, snap = 0.0, None
    for a, b in keep:
        if a <= t <= b: return (acc + t - a) / tempo
        if a > t and (snap is None or a < snap[0]): snap = (a, acc)
        acc += b - a
    return (snap[1] if snap else acc) / tempo

def span(a, b, keep, tempo, ranges):
    """(start, end) source -> output; end is clipped to the reordered piece that holds start"""
    for ra, rb in ranges:
        if ra <= a < rb:
            b = min(b, rb - 1e-3); break
    return to_output(a, keep, tempo), to_output(b, keep, tempo)

def ordered(keep, ranges):
    """clip the (time-sorted) keep list to each range of "order", in that order"""
    return [(max(a, ra), min(b, rb)) for ra, rb in ranges for a, b in keep if min(b, rb) - max(a, ra) > 0.04]

def main():
    prj = sys.argv[1]
    cfg = project.read(prj)
    sp = cfg["speed"]; tempo = sp.get("tempo", 1.12); max_pause = sp.get("max_pause", 0.22)
    src = os.path.join(prj, cfg["source"]); build = os.path.join(prj, "build")
    words = json.load(open(os.path.join(build, "words.json")))
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate:format=duration", "-of", "json", src],
                                  capture_output=True, text=True, check=True).stdout)
    duration, rate = float(j["format"]["duration"]), j["streams"][0]["r_frame_rate"]
    quiet = silences(src, sp.get("silence_db", -30), max_pause + 0.08)
    num, den = map(int, rate.split("/")); fd = den / num
    # "order": play source ranges in a new order, e.g. a tasting moment first as the hook
    ranges = [(a, duration if b is None else b) for a, b in sp.get("order", [[0, None]])]
    keep = ordered(keep_intervals(words, quiet, duration, max_pause, hold=sp.get("hold", [])), ranges)
    # snap every piece to the frame grid so picture and sound keep exactly the same length (no lip-sync drift)
    keep = [(round(round(a / fd) * fd, 4), round(round(b / fd) * fd, 4)) for a, b in keep]
    keep = [(a, b) for a, b in keep if b > a]
    out = os.path.join(build, "fast.mp4")
    enc = ["-r", rate, "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", out]
    if "order" not in sp:
        vsel = "+".join(f"between(t,{a - fd / 2:.4f},{b - fd / 2:.4f})" for a, b in keep)
        asel = "+".join(f"between(t,{a},{b})" for a, b in keep)
        vf = f"select='{vsel}',setpts=N/FRAME_RATE/TB,setpts=PTS/{tempo}"
        af = f"aselect='{asel}',asetpts=N/SR/TB,atempo={tempo}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf, "-af", af] + enc, check=True)
    else:
        # reordered: trim + concat; 6 ms fades so joins inside speech do not click
        parts, labels = [], []
        for i, (a, b) in enumerate(keep):
            fa, fb = round(a / fd), round(b / fd)
            parts.append(f"[0:v]trim=start_frame={fa}:end_frame={fb},setpts=PTS-STARTPTS[v{i}];"
                         f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.006,afade=t=out:st={b - a - 0.006:.4f}:d=0.006[a{i}]")
            labels.append(f"[v{i}][a{i}]")
        fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(keep)}:v=1:a=1[cv][ca];" \
             f"[cv]setpts=PTS/{tempo}[v];[ca]atempo={tempo}[a]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "[a]"] + enc,
                       check=True)
    json.dump({"tempo": tempo, "keep": keep, "ranges": ranges}, open(os.path.join(build, "timemap.json"), "w"), indent=1)
    new = sum(b - a for a, b in keep) / tempo
    print(f"speed: {duration:.1f}s -> {new:.1f}s ({len(keep) - len(ranges)} pauses shortened, tempo {tempo}) -> {out}")

if __name__ == "__main__":
    main()
