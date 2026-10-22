""""Expensive mic" voice: AI denoise, auto-levelling so quiet and loud phrases sit at one level,
warm close-mic EQ, de-esser, two gentle compressors and light saturation (studio chain from fizik-reel).

    python voice.py projects/<name>     -> build/voice.wav (exactly the video's length)
"""
import os, subprocess, sys
from render import load

HERE = os.path.dirname(os.path.abspath(__file__))
DEEP_FILTER = os.environ.get("DEEP_FILTER", os.path.join(HERE, "tools", "deep-filter"))

CHAIN = (
    "highpass=f=70:p=2,"
    # ride the gain phrase by phrase (no more fading in and out); after denoise, so the room is not lifted
    "dynaudnorm=f=200:g=15:p=0.7:m=8:r=0.6:s=12,"
    "equalizer=f=120:t=q:w=0.9:g=3,"          # warmth / proximity
    "equalizer=f=450:t=q:w=1.0:g=-4.5,"       # remove boxiness
    "equalizer=f=2800:t=q:w=1.0:g=2.5,"       # articulation
    "equalizer=f=5500:t=q:w=1.5:g=-1.5,"      # tame harshness
    "highshelf=f=11000:g=1.5,"
    "deesser=i=0.55:m=0.5:f=0.5,"
    "acompressor=threshold=-24dB:ratio=2.5:attack=4:release=80:knee=6,"
    "asplit[d][w];[w]volume=8dB,asoftclip=type=tanh:oversample=4,volume=-22dB[s];"  # parallel saturation
    "[d][s]amix=inputs=2:normalize=0,"
    "acompressor=threshold=-16dB:ratio=1.8:attack=12:release=180:knee=4,"
    "loudnorm=I=-14:TP=-1.5:LRA=5,aresample=48000,alimiter=limit=0.89:attack=2:release=40")

def run(cmd): subprocess.run(cmd, check=True)

def main():
    prj = sys.argv[1]
    cfg = load(prj)
    build = os.path.join(prj, "build"); dfn = os.path.join(build, "dfn"); os.makedirs(dfn, exist_ok=True)
    raw = os.path.join(build, "voice_raw.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", cfg["source"], "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", raw])
    # -D compensates the model delay so the voice stays in sync with the lips
    atten = str(cfg.get("voice", {}).get("denoise_atten_db", 40))
    run([DEEP_FILTER, "-D", "-a", atten, "-o", dfn, raw])
    dur = cfg["duration"]
    fc = f"[0:a]apad=whole_dur={dur:.6f},atrim=0:{dur:.6f},{CHAIN},aformat=channel_layouts=stereo[v]"
    out = os.path.join(build, "voice.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(dfn, "voice_raw.wav"), "-filter_complex", fc, "-map", "[v]", out])
    print(f"voice: studio chain -> {out}")

if __name__ == "__main__":
    main()
