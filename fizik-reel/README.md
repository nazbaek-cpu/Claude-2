# Fizik reel: HyperFrames edit pipeline

Turns a talking-head selfie video into a 9:16 reel. The pipeline does the following:
- Whisper transcript with word timestamps
- "studio mic" voice: AI denoise (DeepFilterNet), warm close-mic EQ, de-esser, gentle compression
- cuts only true silence, so word endings stay intact
- natural skin retouch with a 30% lift on face and hands
- liquid-glass keyword animations synced to the speech
- karaoke captions
- synthesized sound effects
- CTA at the end

Built for *Modul Konstruk Fizik Tingkatan 5* (64 s source → 61.4 s reel). The engine is generic: everything specific to one video lives in `config.json` and `cues.json`.

## Quick start

```bash
./setup.sh                                   # venv + pip, npm, YuNet, DeepFilterNet, headless Chrome (idempotent)
./run_all.sh --drive "<google drive link>"   # or --src video.mp4, or reuse work/src.mp4
./run_all.sh --from cuts --draft             # 720p preview → out/preview_720p.mp4
./run_all.sh --from cuts                     # final → out/final_1080p.mp4 (~29 MB for 60 s)
```

Requirements: ffmpeg/ffprobe, Node ≥ 18, Python ≥ 3.10, and about 4 GB of disk for the Whisper model. Network access is needed to:
- `huggingface.co`, for Whisper and YuNet
- the npm registry and PyPI
- `drive.usercontent.google.com`, only when using `--drive`

## New video

1. `./run_all.sh --drive <link> --until transcribe` downloads the video and writes `work/tr_large.json`.
2. Edit `config.json`:
   - language and prompt
   - `flip` (un-mirror selfie footage)
   - `brighten`
   - `voice.preset`: `studio` (default), `clear` or `basic`
   - transcript `fixes` (Whisper mishearings)
   - caption keywords
   - `cuts.end_s` / `no_cuts_after_s` (set them to `null` to use the whole video)
3. Write `cues.json`. Each entry has `start`/`end` in **source** seconds, a CSS `class` (`top`, `free` or `ctaz`), the cue's `html` and its `sfx`. Inside the html you can use:
   - `{at:T}`: the element pops in at source second T
   - `{icon:CODE:SIZE[:CLASSES]}`: a Twemoji icon from `node_modules/@twemoji/svg/CODE.svg`

   Copy the glass building blocks from the existing cues: `glass card`, `glass pill`, `glass chip`, `glass hero`, `glass list`, `glass cta`. SFX kinds are `pop`, `whoosh`, `tick`, `ding`, `boom`, `click`, `sparkle` and `riser`.
4. `./run_all.sh --from cuts --draft` to preview, then `./run_all.sh --from cuts` for the final render.

## Steps (`run_all.sh`)

| Step | Script | Output |
|---|---|---|
| fetch | curl / cp | `work/src.mp4` |
| transcribe | `transcribe.py` (faster-whisper, decoded via ffmpeg) | `work/tr_large.json` |
| cuts | `cuts.py`: 120–7800 Hz energy ≤ floor + 6 dB is silence; keeps a 0.13 s tail and 0.10 s head | `work/keep.json` |
| voice | `voice.py`: frame-matched cuts with 12–15 ms fades, then the `voice.preset` chain (studio: DeepFilterNet −40 dB, +3 dB @120 Hz, −4.5 dB @450 Hz, +2.5 dB @2.8 kHz, −1.5 dB @5.5 kHz, de-esser, 2 compressors, parallel tanh saturation, loudnorm −15 LUFS, limiter) | `work/voice.wav`, `work/edl.json` |
| aroll | `base.py` × `WORKERS`: flip, "Grade Cerah Tajam", retouch (`look.py`), zoom 1.0/1.08 per cut; then concat with 1 s keyframes | `reel/assets/base.mp4` |
| build | `build.py` + `template.html`: composition, captions, copies fonts/GSAP/icons | `reel/index.html`, `work/sfx_cues.json` |
| audio | `sfx.py`, then mix under the voice (`mix.sfx_gain`) | `reel/assets/mix.wav` |
| render | `hyperframes lint` + `hyperframes render` (draft / high) | `out/*_raw.mp4` |
| deliver | 720p preview, or 2-pass 1080p at 3.5 Mb/s | `out/preview_720p.mp4` / `out/final_1080p.mp4` |

`BRIGHT=0.2 ./run_all.sh --from aroll` overrides the skin lift for one run.

## Tests and lint

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check .
npx hyperframes lint reel        # needs reel/assets (after the build/audio steps)
```

The tests cover:
- pause detection, including soft word endings surviving the cut
- the source→output time map
- transcript fixes and caption chunking
- a regression check that `build.py` regenerates the committed `reel/index.html` and `work/sfx_cues.json` exactly
- SFX synthesis, ffprobe/ffmpeg helpers
- every voice preset produces stereo 48 kHz audio of exactly the video length
- skin lift when no face is detected

## Notes

- Not committed (see `.gitignore`):
  - video and audio files
  - `node_modules/`, `.venv/`
  - `models/`, `tools/`
  - `reel/assets/`
  - `out/`
- `hyperframes lint` warns about many "heavy overlay" elements (backdrop-filter glass). Inactive cues are `display:none`, and the 61 s render had no black frames, but check the output if you add many more cues.
- Claude Code cloud sessions run `setup.sh` automatically via `.claude/hooks/session-start.sh`.

## Panduan ringkas (Android)

Pipeline ni perlukan Chrome headless, model Whisper ~3 GB dan CPU yang kuat, jadi **jangan jalankan di telefon** (Termux tak sesuai). Guna Claude Code (cloud) dari app Claude di Android:

1. Mulakan session baru dengan repo **Claude-2**. Hook akan pasang semua secara automatik.
2. Pastikan Network access environment membenarkan `huggingface.co` dan `drive.usercontent.google.com`.
3. Hantar link Google Drive video dan brief kau.
4. Claude buat transcript, susun `cues.json`, dan hantar preview 720p. Lepas kau setuju, baru render final 1080p.
