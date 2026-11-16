# Template kertas

Panggil: **"guna template kertas"**. Contoh: `projects/melukis-kayu-2/`. Kod pembina: `templates/kertas.py`.

- **Latar:** kayu solid (lalai). Kertas atas meja: `theme="kertas"`.
- **Tulisan:** satu frasa pada satu masa, besar: baris kecil di atas, kata kunci besar di bawah (`say`, `y` 395). Tiada kad nota penuh tulisan.
- **Tajuk babak:** jalur kertas koyak di atas (`label`).
- **Watak:** Kak Kira kiri tengah, tukar pose ikut ayat.
- **Prop:** ikon sticker bertag di kanan; "?" merah, ✓ hijau, cop merah.
- **Produk:** gambar gaya sticker, bertukar ikut ayat, tiada watak.
- **CTA:** watak menyapa + gambar kecil + butang "Tekan link dekat bawah".

Struktur (video 120k views): soalan anak berjaya → "RAHSIANYA:" → "ANAK LAIN..." + cop → produk → "SIAP DENGAN:" + ✓ → "INGAT!" + CTA.

## Hijau emerald, tulisan neon

`"theme": "kertas-neon"` dengan `"bg_image": "input/emerald.jpg"` (halaman `motion.neon_page(base="emerald")`, aksen kuning):
tiada kad nota putih, tulisan tangan putih bercahaya pudina terus atas halaman, kata kunci neon kuning bergaris bawah,
sari kata putih dengan halo pudina. Label kertas koyak, cop dan sticker kekal. Contoh: `projects/b14-kertas-emerald/`.
