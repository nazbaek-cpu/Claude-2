# Pasar pagi Pekan Ahad Pokok Getah

Market vlog (25 s source → 24.4 s reel). These are the settings for this video; the top-level files are the Fizik example.

To render, copy them into place and run the pipeline from the cuts step:

```bash
cp projects/pasar-pokok-getah/{config,cues}.json .
cp projects/pasar-pokok-getah/work/*.json work/
./run_all.sh --src <video.mp4> --until fetch
./run_all.sh --from cuts --draft   # or without --draft for the final 1080p
```

The source video is not committed (Google Drive file `16fgpdEqgcCW7gZXOj5OA28aeK35m5OsC`).

Captions to confirm with the speaker: "Sotong" (Whisper heard "Soya"), "Cucuk adang" at 6.9 s, and "pukul tidur pagi" at 16.4 s (probably "pukul tujuh pagi").
