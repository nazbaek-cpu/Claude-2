import json,sys
from faster_whisper import WhisperModel
m=WhisperModel(sys.argv[2],device="cpu",compute_type="int8",cpu_threads=4)
import wave,numpy as np
wf=wave.open(sys.argv[1]);aud=np.frombuffer(wf.readframes(wf.getnframes()),np.int16).astype(np.float32)/32768
segs,info=m.transcribe(aud,language="ms",word_timestamps=True,vad_filter=False,beam_size=5,
  initial_prompt="Modul Konstruk Fizik Tingkatan 5, SPM, soalan, jawapan, nota.")
out=[]
for s in segs:
    out.append({"s":s.start,"e":s.end,"t":s.text,"w":[(w.start,w.end,w.word,w.probability) for w in s.words]})
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}",flush=True)
json.dump(out,open(sys.argv[3],"w"),ensure_ascii=False,indent=1)
