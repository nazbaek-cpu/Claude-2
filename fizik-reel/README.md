# Fizik reel: HyperFrames edit

Source: 64 s selfie video (mirrored) promoting *Modul Konstruk Fizik Tingkatan 5*.

Pipeline (run from this folder; the source video goes in `work/src.mp4`, models in `models/`):

1. `transcribe.py`: faster-whisper large-v3 (Malay) with word timestamps, written to `work/tr_large.json`.
2. Pause detection (speech-band energy) writes the cut list to `work/keep.json`: only true silence removed (≤ floor+6 dB, 0.13 s tail kept after each word), 10 cuts, 61.4 s output.
3. `base.py`: A-roll. Un-mirrors, applies the "Grade Cerah Tajam" grade, does a natural skin retouch (`look.py`, YuNet face box + skin mask, no reshaping, 30% multiplicative lift on face + matching lift on hands (BRIGHT env)), and alternates the zoom 1.0/1.08 per cut to hide jump cuts.
4. `voice.py`: frame-matched audio cuts with 12–15 ms fades, denoise, compression, loudnorm to -15 LUFS. Also writes the output-time map to `work/edl.json`.
5. `build.py` + `template.html`: generate the HyperFrames composition `reel/index.html`, made of 13 liquid-glass keyword cues timed to the spoken words, karaoke captions on a glass pill, and a CTA.
6. `sfx.py`: synthesizes pop, whoosh, tick, ding, boom, click, sparkle and riser sounds at each cue. They are mixed under the voice into `reel/assets/mix.wav`.
7. `npx hyperframes render reel -q high -o final.mp4`

Binary assets (video, audio, fonts, icons, GSAP) are not committed.
