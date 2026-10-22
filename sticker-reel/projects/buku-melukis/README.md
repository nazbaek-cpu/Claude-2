# Buku Melukis (example project)

The reel built in this session: a 65 s ad for the *Bestnya! Buku Lukis* drawing books, voiced with ElevenLabs.

`input/` is not in the repository. To build this project again, put these files there:

| File | What |
|---|---|
| `input/vo.mp3` | voiceover of `build/script.txt` (`../../run.sh projects/buku-melukis --until script`) |
| `input/poses/grid.png` | 3 × 2 collage of face poses, in the order of `stickers.names` |
| `input/poses/<name>.png` | the `stickers.ready` poses: finished stickers (transparent PNG) |
| `input/img/koleksi_pink.jpg`, `kraft_grid.jpg`, `page_mata.jpg`, `cover_karakter.jpg`, `cover_ekspresi.jpg` | product images used in `scenes.json` |
| `input/img/doodle/*.png` | expression doodles (made with `ink.py` from the Ekspresi page) |

Then: `./run.sh projects/buku-melukis --draft`.
