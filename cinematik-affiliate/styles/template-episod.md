# Template episod

Panggil: **"guna template episod"**. Kartun cerita bersiri yang minimal atas pentas biru gelap: satu tajuk ringkas
setiap babak, watak di atas satu garis lantai, prop yang bercerita, dan pudar ke gelap antara babak. Dianalisis dari
video siri parenting ("jangan label anak") untuk corak dan rentak sahaja; watak dan grafik semua milik sendiri.

## Rupa

- **Latar:** biru gelap (navy) gradient, lebih cerah di tengah atas, vignette di bucu, bingkai bulat nipis, satu
  garis lantai di bawah (y 1380).
- **Label episod:** kapsul kuning kecil di atas ("EPISOD 1 · JANGAN LABEL ANAK", `episode`).
- **Tajuk babak:** putih tebal di bawah label; `*kata*` diwarnakan ikut `tone`: `red` (label / masalah),
  `yellow` (soalan / perhatian), `green` (penyelesaian).
- **Tiada sari kata.** VO yang bawa cerita; tajuk 2-5 perkataan sahaja setiap babak.
- **Watak (`char`):** watak simpanan atau `stickman/<pose>` berdiri atas lantai, tag nama putih ("Abang, 16"),
  `char_at` tukar pose, `grey` = selang masa watak jadi kelabu (putus asa), `mark` "!!" atau "?" di atas kepala.

## Prop

- `paper`: kertas / buku latihan kuning dengan tulisan tangan; `strike_at` pangkah merah kiri ke kanan,
  `rewrite` + `rewrite_at` tulisan hijau yang menulis sendiri.
- `bubble`: gelembung cakap putih (`|` baris baru, `tail` left / right).
- `door` (anak curi dengar), `desk` (`cups`, `lamp` + `lamp_at` lampu menyala), `moon` (waktu malam).
- `ticks`: ✓ hijau bernombor 1-2-3 muncul ikut masa (`at` = senarai masa).
- `words`: perkataan label terapung samar di sekeliling watak ("lemah... lemah...").
- `photo`: gambar produk dalam kad putih (contoh kulit buku atas meja).
- `hearts`, `comment` ("Komen: SETUJU"), `follow` ("Ikut untuk episod seterusnya"), `cta` (butang kuning).

## Gerakan dan bunyi

- Babak bertukar dengan pudar ke gelap (±0.3 s); dalam babak, elemen muncul ikut masa VO dengan sedikit lantun.
- Watak bernafas perlahan; tanda "!!" berdenyut; lampu menyala perlahan.
- Bunyi: pop lembut pada setiap elemen, ding pada setiap ✓, coretan marker pada pangkah dan tulisan semula,
  hembusan lembut antara babak, chime pada CTA.

## Struktur cerita (formula)

Petikan label → "SIAPA ajar dia?" → imbas kembali "Minggu LEPAS" → "Dia BERHENTI cuba" → "Dia PERCAYA" →
"Satu, dua, TIGA" (produk masuk di sini sebagai alat langkah kecil) → label dipangkah, "BOLEH" → moral 3-4 perkataan →
"Komen: ..." + "Ikut untuk episod seterusnya".

## Cara bina (kod)

Renderer: `episod.py`; contoh penuh `projects/episod-english-1/` (120 SPM English Model Essays).
`python episod.py projects/<nama>` untuk video, `python episod.py projects/<nama> 2 5.5 11` untuk stills.
VO tidak dinormalkan dalam renderer: naikkan gain semasa encode akhir sampai lebih kurang −10 LUFS.
