# Template "tulisan besar"

Panggil: **"guna template tulisan besar"**. Contoh siap: `projects/melukis-kayu-2/` (Bestnya! Melukis Karakter, 30 s).
Kod pembina: `templates/tulisan_besar.py`.

Gabungan template kertas ([`template-kertas.md`](template-kertas.md)) dengan tulisan besar satu demi satu:

- **Latar:** kayu solid (`"theme": "kayu"`), atau kertas atas meja dengan `theme="kertas"`.
- **Tulisan:** tiada kad nota. Setiap frasa VO jadi satu `say`: baris kecil putih di atas, kata kunci besar kuning
  (atau oren dengan `gold=True`) di bawah, `y` 395. Frasa bertukar ikut ayat yang sedang disebut.
- **Tajuk babak:** jalur kertas koyak `label` di atas (`y` 215), masuk 0.5 s sebelum babak.
- **Watak:** Kak Kira (`kira`), kiri tengah (`x` 290, `y` 1120, `h` 640), `slide=True` pada babak pertama dan CTA,
  tukar pose ikut emosi ayat ([`watak-kak-kira.md`](watak-kak-kira.md)).
- **Prop:** ikon sticker bertag di kanan (`x` 790, `y` 1060), bertukar ikut ayat; emoji Fluent dengan `emoji=True`.
- **Tanda:** `marks` "?" merah atas kepala (`x` 300, `y` 760) bila keliru, ✓ hijau bila bukti; `stamp` merah untuk kesilapan.
- **Produk:** gambar listing gaya sticker (`card`), besar di tengah, bertukar ikut ayat; tiada watak masa intro buku.
- **CTA:** watak masuk menyapa, gambar produk kecil di sebelah, butang "Tekan link dekat bawah".

## Struktur babak (dari video 120k views)

| Babak | Tajuk kertas | Isi |
|---|---|---|
| Hook | "ANAK SUKA MELUKIS?" / "CALON A SEJARAH..." | soalan tentang anak yang berjaya, "?" |
| Rahsia | "RAHSIANYA:" | jawapan satu perkataan, watak dapat idea, ikon `good` |
| Kesilapan | "ANAK LAIN..." / "CALON LAIN..." | 2–3 frasa kesilapan, ikon bertukar, `stamp` |
| Produk | nama buku | gambar bertukar ikut setiap ciri, tiada watak |
| Bukti | "SIAP DENGAN:" | angka (topik, halaman, pengalaman), ✓ |
| Janji + CTA | "INGAT!" | janji, watak gembira, A+, CTA |

## Langkah

1. Transkrip VO (`transcribe.py --model large-v3`), ambil masa setiap frasa.
2. Tulis skrip Python guna `templates/tulisan_besar.py`, satu `say` per frasa, babak bermula pada frasa.
3. Semak stills (satu frame bagi setiap babak), betulkan tindihan, render, semak contact sheet sesaat.
4. Preview 720p dan final 1080p dienkod serentak.
