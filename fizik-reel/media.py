"""Shared helpers: config, source probing and 16 kHz mono audio decoding."""
import json, os, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = os.path.join(WORK, "src.mp4")


def config():
    with open(os.path.join(HERE, "config.json")) as f:
        return json.load(f)


def probe(path=SRC):
    """-> (width, height, fps, duration) of the first video stream, rotation applied"""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:stream_side_data=rotation:format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    w, h = s["width"], s["height"]
    rot = next((abs(int(sd.get("rotation", 0))) for sd in s.get("side_data_list", [])), 0)
    if rot in (90, 270):
        w, h = h, w
    return w, h, float(num) / float(den), float(d["format"]["duration"])


def load_audio16(path=SRC):
    """decode any media file to 16 kHz mono float32 (same samples as `ffmpeg -ac 1 -ar 16000 x.wav`)"""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
