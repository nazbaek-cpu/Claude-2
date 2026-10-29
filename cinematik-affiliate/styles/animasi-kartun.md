# Gaya rujukan: "animasi kartun"

Rujukan: reel @rancangdulu, siri "FAHAM DUIT" ("Masak sendiri atau makan kedai?"), 80 s, 9:16.
Fail video tidak disimpan di sini (repo awam, hak cipta pemilik asal); ini nota gaya untuk dibina semula.

## Rupa

- **Latar:** kertas cream bergaris (buku nota), satu latar untuk seluruh video, tiada potongan kasar.
- **Palet 4 warna** (diambil dari frame):

  | Peranan | Warna |
  |---|---|
  | latar kertas | `#F8F2E9` (garis sedikit lebih gelap) |
  | hijau tua (pill siri, badan mascot, teks kunci) | `#10382E` / `#1B6A46` |
  | emas / oker (bar, nombor, teks kunci kedua) | `#AF7921` / `#9E6C19` |
  | pita kuning (label sub-topik) | `#E9C980` |
  | teks biasa | hitam kehijauan, lebih kurang `#1E2622` |

- **Susun atur setiap babak (dari atas):**
  1. pill gelap kecil dengan nama siri (contoh `FAHAM DUIT`), sama di setiap babak
  2. tajuk dua baris: baris biasa hitam, **kata kunci** hijau atau emas, huruf besar
  3. label "pita kuning" condong sedikit: sub-topik (`DATA DOSM`, `PURATA ISI RUMAH`, `YANG BOCOR`, `RANCANG DULU`)
  4. **mascot lidi** di kiri bawah (kepala bulat putih, badan hijau tua, tali leher emas), menunjuk ke kanan
  5. **prop rata** 2-3 warna di kanan: periuk, rumah, kalendar, carta bar dengan nombor, peti sejuk, gerai, balang duit, kotak bajet
  6. watermark akaun kecil di bawah
- Tiada muka sebenar, tiada gambar foto; semuanya ilustrasi rata.

## Rentak

- Lebih kurang 2.3 perkataan sesaat (tenang, jelas).
- Tajuk dan prop bertukar setiap 2-3 saat ikut frasa VO; elemen masuk dengan animasi lembut (pop / naik), latar tetap.
- Tajuk itu sendiri berfungsi sebagai caption (tiada caption berasingan di bawah).

## Formula script

| Bahagian | Contoh dalam rujukan |
|---|---|
| Hook soalan A atau B | "Tinggal seorang, masak sendiri atau makan kedai je? Mana satu lagi jimat?" |
| Janji topik | "Video kali ni kita cerita tentang duit makan orang yang tinggal sendiri." |
| Bukti data (nombor spesifik + sumber) | DOSM 2024: RM948 restoran vs RM876 barang dapur, ditunjuk sebagai carta bar |
| Twist | "Jadi makan luar mesti rugi? Tak semestinya." |
| Masalah sebenar | "Yang bocor bukan makan kedai, tapi makan tanpa kira" |
| Solusi praktikal | bajet sebulan bahagi ikut minggu, masak 2-3 hidangan, satu untuk bekal |
| Soalan untuk komen | "Korang tim masak sendiri atau tim kedai bawah rumah? Komen bawah." |
| CTA + brand | like, komen, save, share, follow; tagline + logo; "Info umum, bukan nasihat kewangan" |

## Dalam explainer.py

Dah ada: `"theme": "kartun"` (kertas bergaris + palet), `badge`, `say`, `tape`, `mascot` (lidi, pose bertukar ikut VO) dan
`prop` (ikon rata Fluent, warna ditukar ke palet). Contoh: `projects/mini-diari-kartun/`.

Belum ada: carta bar yang naik dengan nombor; stiker muka pengguna sebagai mascot.
