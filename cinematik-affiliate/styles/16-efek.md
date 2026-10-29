# Gaya rujukan: "16 efek"

Rujukan: reel @tenfoldmarc, "16 video effects claude can create", 35.4 s, 9:16, 30 fps, bercakap terus ke kamera.
Fail video tidak disimpan di sini (repo awam, hak cipta pemilik asal); ini nota gaya untuk dibina semula.
Resipi yang dah diuji untuk video produk: [`nota-16-effect.md`](nota-16-effect.md) (efek dalam `fx.py`).

## Struktur

| Masa | Bahagian | Isi |
|---|---|---|
| 0.00–17.08 | Pameran | 15 efek, lebih kurang 1 s setiap satu; nama efek disebut sambil efek itu berlaku |
| 17.08–32.6 | Pitch | bercakap terus, caption kinetik di tengah, B-roll terapung ikut ayat |
| 32.6–35.4 | CTA | kotak komen Instagram, ditaip kata kunci (`STUDIO`) |

- Tiada jeda lebih 0.3 s (semua dipotong rapat), lebih kurang 2.9 perkataan sesaat.
- Kenyaringan asal −14.7 LUFS (video kita: −10).

## Elemen kekal (0–17 s)

- Tajuk dua baris di atas: putih tebal, nombor kuning (`16 video effects / claude can create`).
- Bawahnya senarai bernombor 01–16 dua lajur atas kad gelap separa telus; item yang sedang berlaku jadi kuning.
  Ini *progress bar*: penonton tunggu sampai senarai habis.

## Setiap efek

| # | Masa | Efek | Rupa |
|---|---|---|---|
| 1 | 0.00–0.88 | Headline Wall | keratan surat khabar ditampal di dinding belakang (di belakang badan); jalur kertas koyak "CREATOR NEWS / TODAY" naik di depan, highlighter kuning menyapu kata kunci |
| 2 | 0.88–2.06 | Zoom-Through Cut | kamera meluru ke dalam kertas tajuk: zoom blur jejari, kilatan kuning, potong ke shot biasa |
| 3 | 2.06–3.08 | Vertigo | dolly zoom: saiz badan kekal, latar mengembang dan tona bertukar (oren ke kelabu sejuk) |
| 4 | 3.08–4.40 | Green Screen | latar ditukar dengan footage lain (rujukan guna klip muzik berhak cipta: kita guna footage sendiri) |
| 5 | 4.40–5.42 | Phone Mockup | telefon terbang masuk dengan motion blur, mendarat di tangan; skrin tunjuk tajuk lalu skrol |
| 6 | 5.42–6.58 | Digital Zoom | UI kamkoder (titik REC, timecode, bracket fokus, `1.59×`), punch-in laju ke muka |
| 7 | 6.58–7.50 | Paper Cut | badan dipotong keluar dengan outline putih; latar kolaj kertas koyak; huruf gaya surat ugutan muncul satu-satu |
| 8 | 7.50–8.62 | UI World | panel aplikasi terapung keliling badan (prompt + progress 0→100%, preview LIVE, timeline); latar digelapkan |
| 9 | 8.62–9.30 | Orbit | kad telefon 3D berpusing mengelilingi tangan |
| 10 | 9.30–10.42 | Frame Break | video mengecil jadi bingkai reel IG atas versi kabur diri sendiri; kepala pecah keluar dari bingkai |
| 11 | 10.42–11.62 | Doodle Boil | garis lukisan tangan kuning-putih mengelilingi badan, bergetar; conteng bulatan dan kilauan |
| 12 | 11.62–12.94 | Sticky Text | label kuning melekat dan mengikut hujung jari |
| 13 | 12.94–14.58 | Before + After | wipe dengan garis putih bercahaya, label `before` / `after` (kiri belum grade, kanan dah grade) |
| 14 | 14.58–15.84 | Pull-back Reveal | zoom keluar dengan blur: video rupanya dalam app editor (checklist, senarai efek, timeline, waveform) |
| 15 | 15.84–17.08 | Depth Scatter | teks 3D satu perkataan di belakang kepala, satu lagi (kuning) di depan badan; huruf meletup jadi zarah |
| 16 | 32.6–35.4 | Comment Bubble | kotak "Add a comment…" muncul, kata kunci ditaip, butang hantar |

## Bahagian pitch

- Caption di tengah paras dada: huruf kecil putih tebal, maksimum 2 baris, perkataan muncul satu-satu;
  kata kunci besar kuning (`46`, `video effects`, `10 trial reels.`, `automatically.`, `carousels`).
- B-roll terapung ikut ayat: dinding thumbnail (jumlah besar), kad telefon kanan atas (satu video),
  mini reel berkembang kiri kanan (banyak versi), notifikasi "posting…" (automatik), slaid carousel di dua sisi.

## Kenapa berkesan

1. Saat pertama padat visual dengan janji nombor ("16 efek").
2. Senarai di skrin beri rasa progres, orang tak scroll.
3. Bertukar setiap ±1 s.
4. Apa yang disebut = apa yang ditunjuk.
5. CTA kata kunci di komen: naikkan komen dan kumpul lead.

## Formula script

| Bahagian | Contoh rujukan |
|---|---|
| Janji nombor | "16 video effects Claude can create" (tajuk di skrin, bukan disebut) |
| Senarai laju | sebut nama setiap item sambil ditunjuk, satu saat seorang |
| Tawaran lebih besar | "if you want to get all 46 … as well as a system that …" |
| Faedah bertingkat | edit reel → 1 video jadi 10 trial reels → post automatik → carousel |
| CTA kata kunci | "comment STUDIO and I'll send it to you" |

## Untuk dibina dalam render.py (belum ada)

- Dah hampir ada: tajuk di belakang badan (`behind`), outline stiker (`sticker_edge`), caption kinetik kata kunci, overlay gambar (`img`), conteng (`scribble`).
- Senang: kad checklist progres, Before/After wipe, Digital Zoom (UI kamkoder), Zoom-Through blur cut, Comment Bubble CTA, Frame Break, Pull-back ke mock editor.
- Lebih susah: Vertigo (pisah latar), Orbit (kad 3D), Sticky Text (tracking jari, MediaPipe Hands), Green Screen (footage sendiri sahaja).
