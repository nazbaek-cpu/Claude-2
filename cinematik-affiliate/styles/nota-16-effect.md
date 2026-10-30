# Nota 16 EFFECT

Resipi yang dah terbukti untuk video bercakap (talking head) jual produk dalam gaya "16 efek".
Rujukan asal: [`16-efek.md`](16-efek.md). Contoh lengkap: `projects/infografik-sejarah-16efek/project.json`
(Infografik Sejarah T5, 37.6 s → 32.6 s, final −9.4 LUFS).

Panggil: **"buat video ni guna Nota 16 EFFECT"**.

## Langkah

1. **Flip:** semak tulisan produk sebelah-menyebelah (asal vs flip). Kalau terbalik → `"hflip": true`.
2. **Muka:** `"grade": "bright"` (cerah sederhana), kening asli. Lipstik ikut cahaya:
   - cahaya cerah (rumah, siang): `"beauty": {"lip_rgb": [196, 92, 108], "lip_amount": 1.0, "lip_light": 1.02}` (rose terang "no 2")
   - cahaya malap (dalam kereta): `"beauty": {"lip_rgb": [172, 98, 98], "lip_amount": 1.0}` (nude-rose "biasa"); no 2 jadi terlalu merah
   - kalau ragu, buat perbandingan 4 warna pada satu frame dulu.
3. **Rentak:** `"speed": {"tempo": 1.12, "max_pause": 0.22}`.
4. **Transkrip:** `transcribe.py <projek> --model large-v3` (model yang dah ada dalam cache), ambil masa setiap perkataan.
5. **Petakan efek ke ayat** (jadual bawah), tulis `fx` dalam `project.json`, render, semak satu frame sesaat.
6. **Preview 720p** suara kuat → tunggu "render" → final 1080p (crf 19, −10 LUFS) → caption + hashtag.
   Encode final 1080p ke scratchpad **serentak dengan preview**: /dev/shm kerap terpadam, jadi bila pengguna kata
   "render" fail final dah sedia (tak perlu render semula 20 minit).

## Efek ikut jenis ayat

| Jenis ayat dalam VO | Efek | Nota |
|---|---|---|
| Hook / siapa sasaran ("Calon SPM tahun depan…") | `headline` + `wall` | jalur surat khabar di **atas** (y 330), keratan kecil di dinding sebelah kepala |
| Peralihan ke produk | `zoomcut` | di celah dua perkataan |
| Saiz / rupa produk ("sebesar tapak tangan") | `digizoom` | zoom 1.35 pada muka + produk, `zoom_at` pada kata kunci |
| Mudah dibawa / ringan | `papercut` | huruf "surat ugutan" di bawah produk (y 1560) |
| Senarai (subjek, warna, saiz) | `depth` | semua perkataan **di belakang kepala** (y 640), bertukar putih/kuning |
| Isi dalam / kelebihan | `beforeafter` | label perbandingan, contoh "buku teks" → "infografik" |
| Ciri tambahan | `doodle` | garis bergetar keliling badan |
| Bercakap kepada ibu ayah / sasaran | `framebreak` | bingkai reel IG, `user` + `caption` sasaran |
| Tiga kata sifat ("senang, ringan, mudah") | segmen `pills` | `pills_y` 330 (atas) |
| CTA | `comment` | kotak komen di **bawah** (y 1770), `cps` 40 supaya habis taip |
| Sepanjang video | `checklist` | "N sebab …", mula **lepas** headline, tamat sebelum pills; satu item = satu ciri yang disebut |

## Peraturan susun atur (dari semakan)

- Jangan tutup produk: teks di atas kepala atau di belakang badan; tiada teks di dada bila produk dipegang tinggi.
- Headline dan checklist berkongsi ruang atas: checklist masuk selepas headline keluar.
- `depth` di depan badan menutup buku: guna slot `back` sahaja.
- Pills dan kotak komen jangan di tengah: atas (330) atau bawah (1770).
- Tiada subtitle bawah untuk video bercakap.
- Semak setiap saat dalam contact sheet sebelum hantar preview.
- Produk diangkat tinggi / jauh dari badan (contoh `latih-tubi-2-3-digit`): mask orang tak tangkap seluruh buku.
  Elak `papercut` dan `depth` masa tu; `doodle` guna `box` (kepala dan bahu sahaja); checklist mula bila buku dah turun;
  teks/kotak komen di sisi yang kosong (atas atau bawah). Semak kedudukan buku setiap 0.5 s dulu.

## Templat `fx`

```json
"fx": [
 {"kind": "checklist", "start": 4.45, "end": 34.08, "title": ["6 sebab ibu ayah", "pilih buku ni"],
  "items": [["Sebesar tapak tangan", 6.76], ["Senang bawa", 8.86], ["5 subjek SPM", 10.66],
            ["Infografik menarik", 15.98], ["Tarikh & peristiwa", 19.76], ["Senang study & rujuk", 29.9]]},
 {"kind": "headline", "start": 0.9, "end": 4.45, "tag": "BERITA PELAJAR · HARI INI",
  "lines": ["Calon SPM tahun depan,", "mula persiapan sekarang"], "y": 330,
  "wall": [["SPM|2027", 175, 660, -6], ["nota|padat", 905, 720, 5], ["calon|SPM", 160, 930, 4]]},
 {"kind": "zoomcut", "at": 4.45},
 {"kind": "digizoom", "start": 4.45, "end": 8.86, "zoom": 1.35, "zoom_at": 5.46, "focus": [540, 1050]},
 {"kind": "papercut", "start": 8.86, "end": 10.56, "word": "senang bawa", "word_y": 1560},
 {"kind": "depth", "start": 10.56, "end": 14.3, "scatter_at": 13.95, "y_back": 640,
  "words": [["SEJARAH", 10.82, "back"], ["FIZIK", 11.32, "back"], ["KIMIA", 11.84, "back"],
            ["MATEMATIK", 12.48, "back"], ["ADD MATHS", 13.36, "back"]]},
 {"kind": "beforeafter", "start": 14.38, "end": 18.35, "labels": ["buku teks", "infografik"]},
 {"kind": "doodle", "start": 18.8, "end": 24.44},
 {"kind": "zoomcut", "at": 24.44},
 {"kind": "framebreak", "start": 24.44, "end": 34.0, "user": "ibu ayah", "caption": "untuk anak calon SPM tahun depan"},
 {"kind": "comment", "start": 35.2, "end": null, "text": "DAPATKAN DI LINK BAWAH", "cps": 40, "y": 1770}
]
```

Masa ditulis ikut VO asal; `speed` menggerakkan semuanya secara automatik.

## Caption

Ayat pembuka ikut tajuk checklist ("6 sebab …"), senarai ✅ ikut item checklist, satu ayat desakan, CTA "link bawah 👇",
kemudian hashtag produk + SPM + ibu ayah + TikTok Shop.

## Belum dibina

Vertigo, Orbit, Sticky Text, Green Screen (footage sendiri sahaja).
