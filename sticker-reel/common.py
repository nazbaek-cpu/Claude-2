"""Shared helpers: project loading, {{variable}} filling, audio decoding, silence detection."""
import json, os, re, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")


class Project:
    """a project folder: project.json, script.txt, scenes.json, input/ (media, not committed), build/ (generated)"""

    def __init__(self, path):
        self.dir = os.path.abspath(path)
        with open(self.p("project.json")) as f:
            self.cfg = json.load(f)
        self.vars = {k: str(v) for k, v in self.cfg.get("vars", {}).items()}
        os.makedirs(self.p("build"), exist_ok=True)

    def p(self, *parts):
        return os.path.join(self.dir, *parts)

    def fill(self, text):
        return fill(text, self.vars)

    def script(self):
        with open(self.p("script.txt")) as f:
            return self.fill(f.read()).strip()


def fill(text, variables):
    """replace {{name}} (or {{name|upper}}, |lower, |title) with variables[name];
    unknown names are an error so typos don't reach the video"""
    def sub(m):
        k, _, f = m.group(1).strip().partition("|")
        k = k.strip()
        if k not in variables:
            raise KeyError(f"unknown variable {{{{{k}}}}} (define it in project.json \"vars\")")
        v = variables[k]
        return {"upper": v.upper(), "lower": v.lower(), "title": v.title(), "": v}[f.strip()]
    return re.sub(r"\{\{([^{}]+)\}\}", sub, text)


def load_audio16(path):
    """decode any media file to 16 kHz mono float32"""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


def silences(path, db=-38, min_s=0.3):
    """-> [(start, end)] of silent stretches (ffmpeg silencedetect)"""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=n={db}dB:d={min_s}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(st, en))


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)
