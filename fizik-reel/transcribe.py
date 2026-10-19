"""Whisper transcript with word timestamps -> work/tr_large.json
usage: transcribe.py [src (any audio/video)] [out.json]
Model, language and prompt come from config.json. Audio is decoded with ffmpeg (faster-whisper's own
PyAV decoder is not used: it breaks with av>=15)."""
import json, sys
from faster_whisper import WhisperModel
from media import SRC, WORK, config, load_audio16

cfg = config()
src = sys.argv[1] if len(sys.argv) > 1 else SRC
dst = sys.argv[2] if len(sys.argv) > 2 else f"{WORK}/tr_large.json"
m = WhisperModel(cfg["whisper_model"], device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(load_audio16(src), language=cfg["language"], word_timestamps=True, vad_filter=False,
                          beam_size=5, initial_prompt=cfg.get("initial_prompt") or None)
out = []
for s in segs:
    out.append({"s": s.start, "e": s.end, "t": s.text, "w": [(w.start, w.end, w.word, w.probability) for w in s.words]})
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}", flush=True)
json.dump(out, open(dst, "w"), ensure_ascii=False, indent=1)
