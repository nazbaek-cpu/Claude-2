# Template motion

Panggil: **"guna template motion"**. Gaya motion graphic kemas: tulisan kinetik ikut suara, mockup phone, ikon "pop",
senarai semak, dan sapuan serong antara babak. Dianalisis dari video tutorial pendek (71 s, 576x1024) untuk rentak dan
corak sahaja. Semua grafik dilukis sendiri; tiada aset, nama atau jenama pencipta asal digunakan.

## Rupa

- **Latar:** kertas putih dengan grid titik kelabu halus (macam kertas dot grid pengguna), dua cahaya lembut warna
  aksen di bucu, lengkung cincin pucat di tepi, dan bintang empat bucu kecil yang berkelip.
- **Latar biru tua neon:** `"theme": "neon"` (panggil "background biru tua, tulisan neon"). Halaman biru tua gradient
  dengan grid titik biru samar, cahaya `accent` di bucu atas dan `accent2` di bucu bawah, bingkai nipis bercahaya.
  Kata kunci jadi tiub neon: teras pucat dengan halo warna `accent`, dan berkelip-kelip masa menyala. Ayat kecil putih
  dengan haze biru. Stickman dapat bingkai putih. Contoh: `projects/b9-motion-neon-1/` (cyan `[0, 229, 255]` + pink
  `[255, 64, 200]`).
- **Warna aksen** ikut buku: `accent` (utama) dan `accent2` (hujung gradient). Contoh Sirpuloh: magenta `[226, 32, 138]`
  ke kuning `[250, 186, 40]`.
- **Tulisan:** Plus Jakarta Sans tebal. Ayat biasa kecil dan gelap; **kata kunci 2x lebih besar, gradient warna aksen
  dengan glow lembut**. Semua perkataan duduk atas satu garis dasar.

## Gerakan

- Setiap perkataan muncul **ikut masa ia disebut** dalam VO: naik sedikit dari bawah dan dari kabur ke tajam (±0.2 s).
- **Phone:** naik dari bawah skrin dengan lantun kecil, nombor langkah (①②③) dalam bulatan warna aksen di bucu.
- **Ikon (tiles):** kotak putus-putus muncul dulu, kemudian ikon "pop" masuk dengan lantun; "+" di antara ikon.
- **Senarai semak:** kad putih, setiap baris bertukar dari kelabu ke gelap dan dapat ✓ hijau ikut masa.
- **Tanda larangan:** bulatan merah ⃠ pop atas ikon ("bukan baca je").
- **Peralihan babak:** jalur serong warna aksen menyapu dari kiri ke kanan (±0.4 s) dengan bunyi whoosh.
- Bunyi: whoosh pada setiap sapuan, pop pada ikon, phone dan kata kunci, tick pada ✓, chime pada CTA.

## Cara bina (kod)

Renderer: `motion.py`. `project.json` dengan `"type": "motion"`:

```json
{"type": "motion", "source": "input/vo.mp4", "accent": [226, 32, 138], "accent2": [250, 186, 40],
 "scenes": [{"start": 0.0, "end": 5.8,
             "lines": ["Kenapa ada pelajar", "yang ujian pertama", "*Add Maths*", "terus *gagal,*"],
             "items": [{"kind": "icons", "y": 1320, "tiles": [{"img": "icons/markah_rendah.png", "label": "Add Maths", "at": 2.7}]}]},
            {"start": 18.4, "end": 21.8, "lines": ["*Latihan Topikal*", "Matematik Tambahan"],
             "items": [{"kind": "phone", "img": "cover.jpg", "at": 18.6, "step": 1, "y": 1260}]}],
 "cta": {"at": 33.0, "text": "Tekan link dekat bawah"}}
```

- `lines`: satu baris per elemen; `*kata*` atau `*dua kata*` jadi kata kunci besar. Baris panjang dibalut automatik.
  `"align": "center"`, `"text_y"`, `"text_x"` untuk ubah kedudukan.
- `items`: `phone` (gambar dalam skrin phone, `step` = nombor langkah), `card` (gambar dalam kad putih),
  `icons` (`tiles` dengan `img`, `label`, `at`; `"plus": false` buang tanda +), `checklist` (`title`, `rows`:
  `[["teks", masa], ...]`), `ban` (tanda larangan, `x`, `y`, `size`).
- Gambar dicari dalam `input/` projek dahulu, kemudian `assets/` repo (jadi `stickman/pening.png` terus boleh guna).
- `python motion.py projects/<nama>` untuk video, `python motion.py projects/<nama> 2 5.5 11` untuk lembaran stills.
- VO tidak dinormalkan dalam renderer: naikkan gain semasa encode akhir sampai lebih kurang −10 LUFS.
- Contoh: `projects/motion-sirpuloh/` (Latihan Topikal Add Maths T4).
