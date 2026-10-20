# Modul Konstruk Fizik (sticker reel)

A voiceover reel for *Modul Konstruk Fizik* (Tingkatan 5, with Tingkatan 4), the same product as the talking-head edit in `../../../fizik-reel/`. Covers: too many formulas → weak in physics → forgotten in the exam → the module, its mnemonics and its creative questions with worked answers → CTA.

`input/` is not in the repository. Put these files there:

| File | What |
|---|---|
| `input/vo.mp3` | voiceover of `build/script.txt` (`../../run.sh projects/modul-fizik --until script`) |
| `input/poses/grid.png` + `input/poses/<name>.png` | face poses, same names as `buku-melukis` (edit `stickers` in `project.json` to use others) |
| `input/img/cover_t5.jpg` | Tingkatan 5 cover |
| `input/img/cover_t4.jpg` | Tingkatan 4 cover |
| `input/img/page_mnemonik.jpg` | an inside page showing a mnemonic |
| `input/img/page_soalan.jpg` | an inside page with a question and its worked answer |

Then: `./run.sh projects/modul-fizik --draft`.
