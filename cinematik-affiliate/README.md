# Cinematik Affiliate: talking head → clean cinematic 9:16 affiliate video

Takes one talking-head take (phone, Insta360, …) and gives it the "clean product reel" look: warm muted grade, natural beauty pass, Inter typography with blur-in animations, headlines tucked behind the subject, and royalty-free SFX.

| Element | What it does |
|---|---|
| **Grade** | Warm, muted, highlights held back, lifted blacks, vignette. Top of the frame darkened for headlines, bottom slightly darkened for subtitles. |
| **Beauty** | Even, smooth skin that keeps about 30% of pore texture. Natural nude-rose lip tone (pulls back strong red). Brows untouched by default. Uses MediaPipe face landmarks, so eyes, hijab and background are left alone. |
| **Cuts** | Hard-cut punch-in (1.0 ↔ 1.12) on every subtitle phrase, so a single take feels multi-cam. |
| **Title card** | Opening block, left-aligned over a soft dark scrim: tracked accent kicker, two big Plus Jakarta Sans ExtraBold lines with accent-coloured words, short accent underline. |
| **Orbit title** | `"title_style": "orbit"`: each title line turns in about its own vertical axis on a curved "wall" (perspective, far side in shadow), over a frosted glass panel. `"glass": 0.30` is the panel's white tint. |
| **Kicker** | `PUFFER SLING BAG`: small caps, wide tracking (Inter Medium). |
| **Headline** | `Ringan.`: short, ends with a full stop (Inter Display Bold). Placed *behind* the person via a selfie-segmentation mask. |
| **Count-up** | Big number (Inter ExtraBold) that eases up to the target, with a growing green bar and a label. |
| **Pills** | White rounded tags that pop in one by one at the moment the word is said. |
| **CTA** | Yellow `Beli di beg kuning` pill with bouncing ⌄⌄ chevrons. |
| **Subtitles** | Inter SemiBold with a soft shadow, cut per phrase, no animation. |
| **Un-mirror** | `"hflip": "auto"` reads the product text both ways and flips a mirrored front-camera take, so book titles and labels never show backwards. |
| **Pace** | Optional `speed`: long pauses shortened to 0.22 s and a 1.12× pitch-preserving tempo, so slow talking feels brisk but natural. Project times stay in source seconds. |
| **Voice** | "Expensive mic" chain (on by default): DeepFilterNet AI denoise, phrase-by-phrase auto-levelling so the voice never fades in and out, warm close-mic EQ, de-esser, two gentle compressors, light saturation, −14 LUFS. `"voice": {"studio": false}` turns it off. |
| **Audio** | Voice at −14 LUFS. SFX synthesized from scratch: a whoosh on each headline, a pop per pill, a tick per count step and a ding on each CTA. |

All text animates in and out with blur + fade (0.32 s in, 0.25 s out).

## Cinematik Food Affiliate (preset `food`)

The food-review look, saved as a preset so a new project only needs its own text:

- **Text:** yellow handwritten line (Pacifico, thin white outline) over bold white Plus Jakarta Sans.
- **Title:** centred above the head.
- **CTA:** "Dapatkan di link bawah".
- **Also on:**
  - studio voice
  - speed pass (1.12×, pauses 0.22 s)
  - automatic un-mirroring when the product text reads backwards
  - natural lips, brows untouched
  - headlines in front of the subject

```jsonc
{
  "source": "input/source.mp4",
  "preset": "food",                  // presets/food.json; anything set here wins over the preset
  "top_offset": -170,                // per take: how high the head sits
  "segments": [
    {"start": 0.1, "end": 7.5, "title": {"lines": ["Sate ikan,", "saiz jumbo!"]}},
    {"start": 9.0, "end": 16.1, "kicker": "Jumbo", "head": "Besar sangat."},
    {"start": 40.5, "end": null, "cta": true, "head": "Jom cuba.", "offset": -70}
  ],
  "subs": [[0.08, 2.15, "Kalau pergi Pulau Pangkor,"]]
}
```

Example: `projects/sate-ikan-jumbo/`.

## Animasi Edukasi Buku (preset `edukasi`)

A no-face motion-graphics reel for educational books, built on a voiceover in the style of a product explainer. The preset
sets `"type": "explainer"`, the speed pass (1.12×, pauses 0.22 s) and the clean voice chain, so a project only needs its
voiceover, photos and scenes:

```jsonc
{
  "source": "input/vo.mp4",          // the voiceover (a black CapCut export is fine)
  "preset": "edukasi",
  "end": 54.4,                       // optional: trim silence after the last word
  "scenes": [
    {"start": 0.0, "in": "cut", "items": [
      {"kind": "head", "lines": [["HAMPIR", 0.66], ["GIVE UP?", 0.96]], "accent": ["GIVE", "UP?"]},
      {"kind": "pile", "chips": ["F = ma", "V = IR"], "at": 2.8, "box": [200, 920, 880, 1560]}]}
  ]
}
```

What it looks like:

- **Look:** peach paper with a faint grid; dark scenes for the low point of the story.
- **Type:** an italic serif setup line (Instrument Serif) appears word by word over a heavy uppercase headline (Plus Jakarta Sans ExtraBold); every final full stop is orange.
- **Motion:** blur-in text, tilted photo cards with a white border, terracotta clay icons, words that scatter, and a sideways motion-blur "whip" between scenes.
- **Sound:** the studio voice chain on the voiceover, plus synthesised whooshes, pops, ticks and a ding.

Scenes are listed in `project.json` with times taken from the voiceover (`--transcribe` gives word times). Item kinds:

| Kind | What it draws |
|---|---|
| `setup` | italic line, word by word |
| `kicker` | small tracked caps |
| `head` | headline lines; `accent`, `box` (highlighter), `offset_shadow`, `scatter_at` |
| `card` | product photo card: `img` from `input/`, `x`, `y`, `w`, `rot`, `from: "bottom"` |
| `tile` | clay icon with a glyph and an optional label |
| `count` | big count-up number with a label |
| `timer` | ring that fills while the number counts up (e.g. 15 minutes) |
| `race` | two bars: the class moves on, the child lags behind |
| `blocks` | a tower of topics on a base block: `wobble_at`, then `fall_at` |
| `stairs` | steps that rise, with a ball hopping up them |
| `ticks` | a worksheet card that fills with check marks |
| `calendar` | seven days, ticked one by one |
| `cta` | orange pill with bouncing chevrons |
| `pile` | chips (e.g. formulas) that rain into a messy heap; `scatter_at` blows them away |
| `floaters` | drifting maths symbols (or your own `glyphs`) behind a dark scene |

`"in": "cut"` hard-cuts into a scene; the default is the whip. `"end"` trims silence after the last word.
The preset's `"speed"` shortens pauses and speeds up the voiceover (pitch kept), and every scene time follows it, so write
the times from the original recording. Its `"voice": {"chain": "clean"}` is the gentle studio chain for a voiceover that is
already loud and squashed (phone or CapCut "enhance"): declip, hum notch, light denoise, no saturation. Example: `projects/matematik-explainer/` (voiceover and product photos go in its `input/`).

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
             "lip_rgb": [164, 114, 102], "lip_amount": 0.65, "brows": 0.0},   // natural nude-rose lips; brows 0.2 = soft fill
  "head_scrim": false,                // true darkens the top behind headlines (a lit lamp or bright window behind the text)
  "behind": true,                     // false puts every headline/number in front (with a soft shadow) when the head fills the top
  "theme": "skrip",                   // optional simple food look: yellow handwritten line (Pacifico, thin white outline)
                                      // over bold white Plus Jakarta Sans; kickers become the handwritten line,
                                      // the title is "lines": ["bold line", "handwritten line"]
  "accent_rgb": [233, 185, 73],       // title accent (gold)
  "title_pos": "bottom",              // "top" when the face is centred and a lower title would cover it
  "grade": "muted",                   // "bright": warm and moderately brighter, skin keeps its colour (dim takes)
  "title_style": "orbit",             // optional: title lines turn in on a curved wall over frosted glass
  "glass": 0.30,                      // with "orbit": glass panel tint (0.30 = 30 % white over the blurred video)
  "hflip": "auto",                    // "auto" (preset default): OCR checks the product text and flips a mirrored take;
                                      // true / false force it
  "speed": {"tempo": 1.12, "max_pause": 0.22, "hold": [[20.6, 28.4]]},   // optional: shrink pauses + gentle tempo-up; "hold" = silent moments to keep (a bite, showing the inside); "order": [[22.5, 27.6], [0, 22.5], [27.6, null]] plays a moment first as the hook
  "top_offset": 0,                    // e.g. -80 lifts kickers/headlines/CTA when the head sits high in frame
  "segments": [                       // what sits at the top of the frame, in seconds
    {"start": 0.3, "end": 4.7, "title": {"kicker": "SLING BAG", "lines": ["Material", "Cordura."], "accent": ["Cordura."]}},   // optional "size": 100 for a long accent line
    {"start": 0.5, "end": 4.35, "kicker": "PUFFER SLING BAG", "head": "Ringan."},
    {"start": 7.2, "end": 11.1, "kicker": "BANYAK RUANG", "count": 6, "label": "kompartmen."},
    {"start": 26.0, "end": 30.6, "kicker": "KAPASITI", "count": 4.5, "decimals": 1, "label": "liter."},
    {"start": 0.3, "end": 2.55, "kicker": "UNTUK SEMUA", "head": "Lelaki. Wanita.", "behind": false},  // in front: subject off-centre or leaning in
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
| `project.py` | reads `project.json` over its `"preset"` (`presets/*.json`) |
| `mirror.py` | `"hflip": "auto"`: OCRs 16 frames as shot and flipped (RapidOCR); flips when only the flipped side reads. `python mirror.py projects/<name>` shows what it read |
| `explainer.py` | Animasi Edukasi Buku (`"type": "explainer"`): the no-face motion-graphics reel, scene by scene, with its own SFX track |
| `speed.py` | with `"speed"`: trims pauses (Whisper gaps + measured silence, never through a word), tempo-up, frame-aligned → `build/fast.mp4`; all project times are remapped automatically |
| `voice.py` | studio voice → `build/voice.wav` (DeepFilterNet binary in `tools/`, fetched by `setup.sh`) |
| `sfx.py` | builds `build/sfx.wav` from the segments |
| `transcribe.py` | faster-whisper word times → phrase subtitles draft |
| `projects/puffer-bag/` | example: puffer sling bag review (Malay) |
| `projects/sate-ikan-jumbo/` | example: food review in the "skrip" theme (Malay) |
| `projects/latihan-matematik/` | example: maths workbooks, head high in frame (front headlines, per-segment offset), two count-ups (Malay) |
| `projects/mms-crunchy-cookie/` | example: snack review, hflip, speed with a held tasting moment, CTA with price pills (Malay) |
| `projects/buku-melukis-karakter/` | example: children's drawing book, title on top, two count-ups, lifted top text (Malay) |
| `projects/tambah-tolak-orbit/` | example: the Tambah & Tolak take with the orbit title on 30 % glass (Malay) |
| `projects/matematik-explainer/` | example: Animasi Edukasi Buku for the Latihan Matematik 2 & 3 Digit books (Malay voiceover) |
| `projects/timbunan-chip/` | example: Animasi Edukasi Buku for Modul Konstruk Fizik T4 & T5 (formula pile, PICK mnemonic page) |
| `projects/sling-bag-cordura/` | example: Cordura slim sling bag, 4.5 L count-up, opening wide shot (Malay) |
