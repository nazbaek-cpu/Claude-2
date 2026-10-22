# Cinematik Affiliate: talking head → clean cinematic 9:16 affiliate video

Takes one talking-head take (phone, Insta360, …) and gives it the "clean product reel" look: warm muted grade, natural beauty pass, Inter typography with blur-in animations, headlines tucked behind the subject, and royalty-free SFX.

| Element | What it does |
|---|---|
| **Grade** | Warm, muted, highlights held back, lifted blacks, vignette. Top of the frame darkened for headlines, bottom slightly darkened for subtitles. |
| **Beauty** | Even, smooth skin that keeps about 30% of pore texture. Soft rosy-nude lipstick. Brows untouched by default. Uses MediaPipe face landmarks, so eyes, hijab and background are left alone. |
| **Cuts** | Hard-cut punch-in (1.0 ↔ 1.12) on every subtitle phrase, so a single take feels multi-cam. |
| **Kicker** | `PUFFER SLING BAG`: small caps, wide tracking (Inter Medium). |
| **Headline** | `Ringan.`: short, ends with a full stop (Inter Display Bold). Placed *behind* the person via a selfie-segmentation mask. |
| **Count-up** | Big number (Inter ExtraBold) that eases up to the target, with a growing green bar and a label. |
| **Pills** | White rounded tags that pop in one by one at the moment the word is said. |
| **CTA** | Yellow `Beli di beg kuning` pill with bouncing ⌄⌄ chevrons. |
| **Subtitles** | Inter SemiBold with a soft shadow, cut per phrase, no animation. |
| **Audio** | Voice at −14 LUFS. SFX synthesized from scratch: a whoosh on each headline, a pop per pill, a tick per count step and a ding on each CTA. |

All text animates in and out with blur + fade (0.32 s in, 0.25 s out).

## Quick start

```bash
./setup.sh                                        # venv, MediaPipe models, libEGL + Inter if missing
cp my_take.mp4 projects/<name>/input/source.mp4   # input/ is never committed
./run.sh projects/<name> --transcribe             # build/subs_draft.json: phrase-cut subtitles with times
#   paste the draft into project.json "subs", fix spelling, plan "segments" on those times
./run.sh projects/<name> --limit 8                # quick look at the first 8 s -> out/preview.mp4
./run.sh projects/<name>                          # final -> out/final.mp4
```

Any source size or frame rate works. It is scaled and cropped to fill 1080×1920.

## project.json

```jsonc
{
  "source": "input/source.mp4",
  "cta": "Beli di beg kuning",
  "zoom": 1.12,                       // punch-in on every other phrase
  "sfx_gain_db": 0,                   // +3 for louder SFX, -100 to mute
  "beauty": {"enabled": true, "smooth": 0.8, "keep_texture": 0.32, "tone_even": 0.75,
             "lip_rgb": [186, 92, 102], "lip_amount": 0.4, "brows": 0.0},   // brows 0.2 = soft fill
  "segments": [                       // what sits at the top of the frame, in seconds
    {"start": 0.5, "end": 4.35, "kicker": "PUFFER SLING BAG", "head": "Ringan."},
    {"start": 7.2, "end": 11.1, "kicker": "BANYAK RUANG", "count": 6, "label": "kompartmen."},
    {"start": 11.15, "end": 16.3, "kicker": "KIRI & KANAN", "head": "Poket tambahan.",
     "pills": [["Kiri", 12.33], ["Kanan", 12.97]]},                  // pill text, appear time
    {"start": 24.4, "end": 26.4, "cta": true},
    {"start": 29.3, "end": null, "cta": true, "head": "Banyak warna."}   // null = until the end
  ],
  "subs": [[0.67, 2.38, "Ringan, banyak kompartmen."], [29.37, null, "Design ni ada banyak warna lagi."]]
}
```

## Shooting tips for this look

- Use a dark background (wall or curtain) with one soft side light. Turn off the ceiling light.
- Keep the product about 40 cm from a wide lens; closer than that distorts it.
- Leave headroom: headlines sit just above the head, around 22–30% from the top.

## Files

| File | Role |
|---|---|
| `render.py` | grade, beauty, zoom cuts, text layers, person mask, encode + audio mix |
| `beauty.py` | skin smoothing / tone evening, lipstick, brow fill |
| `sfx.py` | builds `build/sfx.wav` from the segments |
| `transcribe.py` | faster-whisper word times → phrase subtitles draft |
| `projects/puffer-bag/` | example: puffer sling bag review (Malay) |
