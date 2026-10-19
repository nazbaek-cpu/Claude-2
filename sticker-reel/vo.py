"""Tighten the voiceover: cut everything after the last script word, shrink pauses, speed up, level it.

usage: vo.py <project>
project.json "vo": {"file", "tempo": 1.12, "pause_s": 0.2, "silence_db": -38, "tail_s": 1.0}
Writes build/vo.wav (48 kHz stereo, -15 LUFS), build/edl.json and build/words.json (words in video seconds).
"""
import json, subprocess, sys
from common import Project, silences

KEEP = 0.10   # silence kept on each side of a cut, before the speed-up


def plan(sil, end, pause=0.2, tempo=1.12):
    """kept [a, b] spans of the VO file and the edit map; each pause becomes about `pause` s long"""
    keep, a = [], 0.0
    half = max(KEEP, pause / 2)
    for s, e in sil:
        if s >= end:
            break
        if e - s > 2 * half:
            keep.append([a, s + half]); a = e - half
    keep.append([a, end])
    keep = [[max(0.0, x), y] for x, y in keep if y - x > 0.05]
    edl, o = [], 0.0
    for x, y in keep:
        edl.append({"src": [round(x, 4), round(y, 4)], "out": round(o / tempo, 4)}); o += y - x
    return edl, o / tempo


def to_out(t, edl, dur, tempo):
    """VO-file seconds -> video seconds (times inside a removed pause snap to the next kept audio)"""
    for s in edl:
        a, b = s["src"]
        if t < a:
            return s["out"]
        if t <= b:
            return s["out"] + (t - a) / tempo
    return dur


def main():
    prj = Project(sys.argv[1]); v = prj.cfg["vo"]; src = prj.p(v["file"])
    tempo, pause = v.get("tempo", 1.12), v.get("pause_s", 0.2)
    words = json.load(open(prj.p("build", "words_src.json")))
    end = words[-1][1] + 0.25
    edl, dur = plan(silences(src, v.get("silence_db", -38), 0.3), end, pause, tempo)
    f = ";".join(f"[0:a]atrim={s['src'][0]:.4f}:{s['src'][1]:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,"
                 f"afade=t=out:st={s['src'][1] - s['src'][0] - 0.012:.4f}:d=0.012[s{i}]" for i, s in enumerate(edl))
    f += ";" + "".join(f"[s{i}]" for i in range(len(edl))) + f"concat=n={len(edl)}:v=0:a=1,atempo={tempo},highpass=f=70," \
        "equalizer=f=3000:t=q:w=1.2:g=1.5,loudnorm=I=-15:TP=-1.5:LRA=8,aresample=48000[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", f, "-map", "[a]", "-ac", "2",
                    prj.p("build", "vo.wav")], check=True)
    out = [[round(to_out(a, edl, dur, tempo), 3), round(to_out(b, edl, dur, tempo), 3), w] for a, b, w in words]
    json.dump({"segs": edl, "dur": dur, "tempo": tempo}, open(prj.p("build", "edl.json"), "w"), indent=1)
    json.dump(out, open(prj.p("build", "words.json"), "w"), ensure_ascii=False)
    print(f"VO {end:.1f} s -> {dur:.1f} s ({len(edl)} pieces, x{tempo}); {len(out) / dur:.2f} words/s")


if __name__ == "__main__":
    main()
