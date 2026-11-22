# Neon tiub (gaya neon lalai)

Rujukan pengguna: papan tanda "NEON" merah jambu. Bila pengguna minta "tulisan neon", guna gaya ini, warna ikut arahan.

## Ciri yang ditiru
- Huruf garisan nipis dan sekata macam tiub kaca bengkok (sans geometri ringan, hujung bulat), jarak huruf lapang.
- Tiub itu sendiri warna pucat hampir putih (62% putih + 38% warna), tepinya warna penuh.
- Tiga lapis cahaya: halo ketat terang yang memeluk garisan, halo sederhana yang mengisi ruang dalam huruf,
  dan cahaya lebar yang samar tumpah ke latar gelap.
- Latar gelap (biru tua / emerald / apa-apa gelap) supaya cahaya timbul.

## Kod
`neon_tiub.py`: `word(teks, saiz, warna)` untuk satu baris, `light(mask, warna, saiz)` untuk mask sendiri,
`bloom(lapisan_rgba, saiz)` untuk lapisan berbilang warna (perkataan kunci vs biasa).
Fon: Plus Jakarta Sans berat 260-380 (nipis).

Dipakai automatik dalam semua tema neon:
- motion `"theme": "neon"`: perkataan besar, perkataan kecil, headline
- arab `"bg": "neon"`: sari kata menyala ikut sebutan
- episod `"neon": true`: tajuk babak
- kertas theme `"kertas-neon"`: baris say() (teks biasa + kata kunci)

Latar hitam untuk neon: motion `"neon_base": "hitam"`, kertas `bg="hitam"`.

Gaya lama (huruf tebal bercahaya): tambah `"neon_style": "tebal"` dalam project.json.
