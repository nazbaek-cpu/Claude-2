# sticker-reel: voiceover → 9:16 reel with face stickers (HyperFrames)

Turns a voiceover (for example from ElevenLabs), a few face photos and some product images into an animated 9:16 promo reel:
- face stickers with a white outline that change pose on every line
- kinetic text, stamps, chips and product cards
- count-up numbers and price bursts
- karaoke captions and synthesized sound effects
- a progress bar

Everything that belongs to one video lives in a **project folder**:

| File | What it is |
|---|---|
| `project.json` | variables (product, price, author, …), voiceover settings, sticker inputs, colours, caption keywords |
| `script.txt` | the voiceover script, with `{{variables}}`; paste `build/script.txt` into your TTS |
| `scenes.json` | what appears when, timed by **phrases of the script** (not seconds) |
| `input/` | your media: `vo.mp3`, face photos, product images (never committed) |
| `build/`, `out/` | generated |

Because scenes are timed by phrases, re-recording the voiceover (new voice, different speed, a changed line) needs no retiming: run the pipeline again.

## Quick start

```bash
./setup.sh                                          # venv, npm, YuNet + BiRefNet models, headless Chrome
./run.sh projects/buku-melukis --until script       # build/script.txt with the variables filled in -> make the VO
./run.sh projects/buku-melukis --draft              # 720p preview -> projects/buku-melukis/out/preview_720p.mp4
./run.sh projects/buku-melukis                      # final 1080p  -> projects/buku-melukis/out/final_1080p.mp4
./run.sh projects/buku-melukis --from compose --draft   # after editing scenes.json only
```

## Steps (`run.sh`)

| Step | Script | Output |
|---|---|---|
| script | `common.py` | `build/script.txt`: the script with variables filled |
| stickers | `stickers.py` | `build/stickers/<pose>.png`, `heights.json` (each face shown about 300 px wide), `_sheet.jpg`, `yellow/*` previews |
| align | `align.py` | `build/words_src.json`: Whisper word times aligned to the script |
| vo | `vo.py` | `build/vo.wav`: cut after the last script word, pauses shrunk to `pause_s`, sped up by `tempo`, −15 LUFS |
| compose | `compose.py` | `build/reel/` (HyperFrames project + `mix.wav`), `build/timeline.txt` (resolved times) |
| render / deliver | HyperFrames + ffmpeg | `out/preview_720p.mp4` or `out/final_1080p.mp4` |

**Align step details:**
- Captions use the script's spelling.
- Stretches Whisper skips are listened to again on their own.
- Any word still missing is placed inside the speech between its neighbours.
- Whatever the TTS says after the last script word (glitches at the end of the file) is cut.

## project.json

```jsonc
{
  "vars": {"product": "Buku Melukis", "author": "penulis", "workshops": 40, "price": "RM6", ...},
  "vo": {"file": "input/vo.mp3", "tempo": 1.12, "pause_s": 0.2, "silence_db": "auto", "tail_s": 1.0},   // auto: halfway between room tone and speech; or a number like -38
  "stickers": {
    "grid": {"file": "input/poses/grid.png", "cols": 3, "rows": 2},   // a collage of poses (white separator lines are found)
    "names": ["tenang_depan", "senyum_tangan_pipi", ...],            // one name per grid cell, row by row
    "photos": {"tunjuk": "input/poses/tunjuk.jpg"},                  // single photos, cut out automatically
    "ready": {"wave": "input/poses/wave.png"},                      // finished stickers (transparent PNG), used as is
    "face_px": 300, "max_h": 720, "outline_px": 30
  },
  "theme": {"bg1": "#FFE46E", "bg2": "#FFD23C", "bg3": "#FFC41E", "accent": "#FF2E7E", "accent2": "#1FA2E8", "navy": "#1C2B5A", "key": "#FFD23C"},
  "background": {"rays": true, "doodles": ["doodle/gembira.png", ...]},   // up to 8 images from input/img, drifting faintly
  "captions": {"max_words": 3, "max_chars": 18, "keywords": ["melukis", "kreatif", ...]},
  "sfx_gain": 0.5,
  "whisper_model": "large-v3", "language": "ms"
}
```

**Variables.** `{{name}}` works in `script.txt` and in every text and phrase of `scenes.json`. `{{name|upper}}`, `|lower` and `|title` change the case. An unknown name stops the build, so a typo never reaches the video.

## scenes.json

```jsonc
{"scenes": [
  {"at": "anak korang suka",                 // the scene starts just before this phrase
   "flash": true, "riser": true,             // optional white flash / riser sound into the scene
   "poses": [{"pose": "tunjuk_korang", "x": -60},                  // first pose: enters with the scene
             {"at": "jangan abaikan", "pose": "terkejut", "x": 40}],
   "items": [
     {"type": "kick", "text": "ANAK KORANG", "at": "anak korang", "top": 200},
     {"type": "stamp", "text": "JANGAN ABAIKAN!", "at": "jangan abaikan", "rot": -5, "top": 740}
   ]}
]}
```

**Times (`at`, `out`, `strike_at`, …).** A time can be written in four ways. Phrases are searched forward from the start of the scene, and case and punctuation are ignored.

| Form | Example | Meaning |
|---|---|---|
| phrase | `"jangan abaikan"` | when the phrase starts |
| phrase with offset | `"jangan abaikan+0.3"` | 0.3 s after the phrase starts |
| bare offset | `"+0.5"` | scene start + 0.5 s |
| number | `12.4` | video seconds |

**Placement.** Items are centred horizontally at `top` px, or placed at `left`/`top` when `left` is given. The content area is y ≈ 120–1200. The sticker and captions use the bottom of the frame.

**Options shared by most items:**
- `anim`: `up`, `pop`, `slam` (also shakes the screen), `drop`, `rise`, `left`, `right` or `burst`
- `rot`: rotation in degrees
- `out`: time the item leaves early
- `float`: gentle bob
- `pulse`: heartbeat
- `sfx`: a kind, `[kind, gain]` or `null`

| type | fields |
|---|---|
| `kick` | `text`: small black pill label |
| `text` | `text`, `size` (`xxl` `xl` `l` `m` `s` or px), `color` (`ink` `white` `accent` `accent2` `navy` or CSS), `serif`, `stroke`, `highlight`, `rainbow`, `icon`, `strike_at` |
| `stamp` | `text`, `icon`, `size`: big pink stamp |
| `chip` | `text`, `bg` (`white` `ink` `accent` `accent2` `navy` `grey`), `icon`, `doodle` (image in `input/img`), `size`, `strike_at` |
| `image` | `src` (in `input/img`), `width`, `card` (white frame, default on) |
| `bubble` | `lines` (last one in accent colour), `underline_at` |
| `scribble` | a scribble drawn live (`dur`) |
| `counter` | `to`, `label`, `count_at`: round badge that counts up |
| `count_chip` | `to`, `suffix`, `label`, e.g. `200` + `,000+ naskhah terjual` |
| `tiles` | `items: [{icon, label, at, rot}]`: cards with a ✅ each |
| `steps` | `items: [{text, at}]`: chips in a row (the last one in accent colour) |
| `bar` | `label`, `drain_at`: a full bar that drains to red |
| `blowtext` | `text`, `icon`, `blow_at`: letters fly away |
| `rays_icon` | `icon`, `size`: big emoji on spinning rays |
| `icon` | `icon`, `left`, `top`, `size`: floating emoji |
| `doodle` | `src`, `left`, `top`, `width`: image bursting in |
| `nosign` | `icon`, `label`, `strike_at` (draws a red no-sign), `serif` |
| `arrow` | `left`, `top`: arrow drawn live |
| `price` | `lines: [small, big, small]`: spinning starburst |
| `cta` | `text`, `icon`, `cursor_at`: pulsing button and a finger that taps it |
| `html` | raw HTML; `{at:phrase}` becomes `data-at="…"` |

Icons are emoji (`"✏️"`) or Twemoji codes (`"270f"`).

## Helpers

- `ink.py out_dir page.jpg --crop x0,y0,x1,y1`: line art on white → transparent ink PNG (for doodles)
- `build/timeline.txt`: every scene and pose with its resolved time; check it when something appears at the wrong moment

## Tests and lint

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check .
```

The tests cover:
- variable filling
- script alignment: spelling, split words, skipped stretches, junk after the script, pause snapping
- pause shrinking and the time map
- phrase anchors
- every scene component
- the page build
- grid splitting, outlines and ink
- the example project: every phrase in `projects/buku-melukis/scenes.json` must exist in its script, in order

## Privacy

`input/`, `build/` and `out/` are git-ignored: face photos, voice recordings and product images stay out of the (public) repository. Only the configuration is committed.

## Panduan ringkas (Bahasa Melayu)

1. **Salin projek contoh.** `cp -r projects/buku-melukis projects/<nama-baru>`
2. **Isi butiran produk.** Tukar `vars` dalam `project.json` (produk, harga, penulis, CTA). Edit `script.txt` kalau perlu.
3. **Jana skrip untuk TTS.** `./run.sh projects/<nama-baru> --until script`. Salin `build/script.txt` ke ElevenLabs dan jana suara.
4. **Letak fail dalam `input/`:**
   - `vo.mp3`
   - gambar pose muka dalam `input/poses/`: satu kolaj (grid) atau gambar satu-satu
   - gambar produk dalam `input/img/`
5. **Susun babak.** Edit `scenes.json`: setiap babak dan elemen ikut **frasa skrip**, jadi tak perlu kira saat.
6. **Tengok preview.** `./run.sh projects/<nama-baru> --draft`. Kalau dah ok, buang `--draft` untuk final 1080p.
