# Template "kertas" (kertas atas meja, gaya cerita kartun)

Dibina daripada analisis video rujukan yang pengguna hantar (106 s, 576x1024, cerita kartun "Pernah tak... rasa hidup ni tak pernah cukup?").
Video rujukan tidak disimpan di sini; ini nota reka bentuk untuk dibina semula. Contoh: `projects/skema-kertas/`.

## Analisis rujukan

| Unsur | Rujukan | Dalam template |
|---|---|---|
| Latar | sehelai kertas besar kelabu-krim, hampir penuh skrin, senget sikit, atas meja kayu gelap (kayu nampak atas dan bawah); bayang tingkap (palang dan daun) melintang kertas dan meja | tema `"kertas"` |
| Tajuk babak | jalur kertas putih koyak di atas, tulisan tangan huruf besar ("PERNAH TAK...", "MALAM ITU...", "DIA MASIH ADA:"), condong sikit, masuk jatuh dan mendap | item `label` |
| Ayat utama | kad putih lebar di bawah tajuk, tulisan tangan; kata kunci merah dengan garis bawah dilukis | item `note` (`*kata kunci*` jadi merah) |
| Watak | tengah skrin, kira-kira 1/4 tinggi video (~450 px dalam 1920), bingkai putih sticker, tukar pose ikut ayat; ke kiri bila ada prop di kanan | `doodle` `"y": 1130, "h": 460`, `x` 540 atau 420 |
| Prop | sticker bingkai putih dengan tag kertas kecil bertulis ("KERETA", "RUMAH", "RM 0") | `sticker` dengan `"tag"` |
| Tanda | "?" merah muncul satu-satu atas kepala; ✓ hijau dilukis | item `marks` (`q` / `tick`) |
| Cop | cop getah merah ("HUTANG") terhentak, senget | item `stamp` (bunyi `thud`) |
| Subtitle | baris bawah, putih bergaris gelap, perkataan muncul ikut sebutan, baki baris pudar | `captions` `"style": "words"` |
| Transisi | setiap babak, kertas baru ditolak masuk dari sisi dengan motion blur | `whip` (lalai) |
| Bunyi | pop kecil setiap kali benda muncul (lebih kurang setiap 0.5–1.5 s), swish untuk tajuk, hentakan untuk cop; muzik latar lembut sangat perlahan (~ −40 dB) | `sfx_track` (muzik latar belum ada) |
| Babak khas | kertas biru malam (telefon), jalan hujan, kertas bergaris untuk senarai bernombor | belum dibina |

## Susun atur (1080x1920)

- `label`: `y` 235, `size` 68
- `note`: `y` 540, lebar 960 (2 baris) ; senarai semak di bawah gambar: `y` 1220 dengan `marks` tick di `x` 150
- watak: `y` 1130, `h` 460; prop kiri `x` 200, kanan `x` 850–880, `y` 1060–1110, `size` 190
- `stamp`: `x` 700, `y` 1340 (dekat kaki watak, jangan keluar tepi kertas)
- gambar produk `card` (`"sticker": true`): `y` 1050, atau `y` 700 bila ada senarai semak di bawah
- subtitle: `y` 1470, `size` 54, 4 perkataan sebaris
- CTA: `y` 1690
