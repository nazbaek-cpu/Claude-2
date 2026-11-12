# Template bukti

Panggil: **"guna template bukti"**. Gaya papan bukti scrapbook: setiap dakwaan dalam VO ada bukti di skrin (halaman
buku, ulasan, carta), atas satu kertas krim sepanjang video. Dianalisis dari video berita bola gaya scrapbook untuk
corak sahaja; semua grafik dilukis sendiri, tiada aset, maskot atau jenama pencipta asal digunakan.

## Rupa

- **Latar:** satu kertas krim (#EFE9DF) bertompok halus untuk seluruh video. Tiada tukar latar.
- **Sari kata:** satu perkataan pada satu masa, besar, putih dengan outline hitam tebal, di tengah bawah (`caption_y`).
- **Keratan (`clip`):** gambar dalam kertas bertepi koyak dengan pita pelekat dan bayang. `marks` = highlighter kuning
  yang menyapu kiri ke kanan atas ayat penting ikut masa; tambah `"red"` untuk tanda kesalahan.
- **Tag (`tag`):** label tulisan tangan dalam kotak berbingkai hitam lukisan tangan (kuning, biru, pink, hijau, putih).
- **Nota (`note`):** kad putih tulisan tangan, `|` untuk baris baru.
- **Carta (`chart`):** carta lukis tangan, titik muncul satu-satu disambung garis merah (contoh markah D ke A).
- **Bulatan (`circle`) dan pangkah (`cross`):** dilukis dengan marker merah.
- **Cop (`stamp`):** cop getah merah yang "hentak" turun (besar ke saiz biasa) dengan bunyi thud.
- **Watak (`char`):** stickman (`stickman/<pose>`) atau watak simpanan, boleh tukar pose (`char_at`).
- **Sumber (`source`):** kotak kecil di bawah kiri (nama buku, "ulasan pembeli").

## Gerakan

- Setiap kepingan pop masuk ikut masa VO dan kekal sehingga babak tamat.
- Tiada sapuan antara babak: papan lama pudar cepat (0.2 s), papan baru pop masuk atas kertas yang sama.
- Bunyi: pop pada kepingan, coretan marker pada highlight / bulatan / pangkah, thud pada cop, chime pada CTA.

## Cara bina (kod)

Renderer: `bukti.py`. `project.json` dengan `"type": "bukti"`; contoh penuh dalam docstring `bukti.py` dan
`projects/bukti-karangan/` (Karangan Contoh dan Teknik Penulisan, "bahasa social media masuk karangan").

- Kedudukan `x`, `y` dalam piksel 1080x1920; `at` = masa muncul (saat VO); `rot` = condong (darjah).
- `marks` dalam `clip`: `[x0, y0, x1, y1, at]` sebagai pecahan 0-1 lebar/tinggi gambar.
- Gambar dicari dalam `input/` projek dahulu, kemudian `assets/` repo.
- `"caption_fix": {"kan?": "kan."}` membetulkan perkataan sari kata dari transkrip.
- `python bukti.py projects/<nama>` untuk video, `python bukti.py projects/<nama> 2 5.5 11` untuk stills.
- VO tidak dinormalkan dalam renderer: naikkan gain semasa encode akhir sampai lebih kurang −10 LUFS.
