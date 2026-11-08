# Template arab

Panggil: **"guna template arab"**. Dianalisis dari video rujukan tadabbur 1 min 51 s ("aku hidup untuk apa?",
Surah Al-Mu'minun 23:115), 576x1024, 30 fps. Rujukan untuk corak dan rentak sahaja: kita tidak guna semula video,
watak atau aset pencipta asal. Semua grafik dilukis sendiri.

## Rupa

- **Latar:** krim polos (lebih kurang #F3EBDD) dengan bingkai garis halus dan titik oren kecil di atas dan bawah tengah.
  Tiada tekstur kayu atau kertas; banyak ruang kosong.
- **Palet:** biru gelap (watak, ikon), oren (aksen, kata kunci), biru muda (tangga, cahaya), coklat (podium), merah
  bata kecil (hati, pinggan). Tiga hingga empat warna sahaja.
- **Watak:** figura ringkas (stick figure) berkepala bulat dan berkopiah, badan jubah satu warna. Tiada muka terperinci.
  Warna badan bertukar ikut maksud (biru = biasa, oren = beramal / berjaya).
- **Ikon:** rata (flat), garis nipis, tiada outline sticker putih: matahari, bulan, beg kerja, pinggan, telefon,
  syiling RM, hati, buku, jam pasir, kompas, tanda soal.
- **Kad ayat Arab:** kad putih bucu bulat di atas tengah, tulisan Arab besar, kata kunci Arab berwarna oren, rujukan
  kecil di bucu (contoh "Al-Mu'minun · 23:115").
- **Kad "KUNCI ARAB":** kad kecil berbingkai gelap: label oren kecil, satu perkataan Arab besar, maksud ringkas di bawah.
- **Label sumber:** pil putih kecil di atas ilustrasi ("Ibnu Kathir", "As-Sa'di", "at-Tirmizi · hasan sahih").
- **Sari kata:** kad putih lebar di bawah tengah (y lebih kurang 1450 pada 1080x1920), satu ayat VO. Perkataan
  muncul ikut suara: yang belum disebut kelabu pudar, yang disebut gelap, kata kunci oren. Fon tulisan tangan bulat.
- **Petunjuk babak:** dua titik kecil (oren + kelabu) di atas kad Arab.

## Gerakan

- Satu idea, satu ilustrasi kecil di tengah atas, bergerak perlahan dan berterusan (tiada potongan kasar):
  - rutin harian: watak di tengah, ikon berpusing dalam bulatan putus-putus, label "↻ ulang"
  - soalan: tanda soal timbul di atas kepala, kemudian gelembung fikiran
  - "sia-sia": daun gugur melayang perlahan
  - pilihan jalan: lengkung bertitik dari watak ke cahaya oren ("kembali kepada Allah"), jalan bercabang
  - tujuan: watak bercahaya dengan garis sinar
  - ujian amalan: tangga biru muda, watak oren naik ke puncak, bintang
  - umur: jam pasir, pasir oren turun
  - soalan akhirat: buku Ilmu, syiling Harta, watak Tubuh keluar satu demi satu dengan tanda soal
  - kisah tokoh: watak dengan kompas / di podium dengan gelombang suara
- Peralihan: pudar silang lembut (lebih kurang 0.4 s); kad Arab turun perlahan dari atas; tiada whip atau zoom.
- Bunyi: muzik latar lembut, bunyi "ting" halus bila kad Arab atau kata kunci muncul. Bukan whoosh kuat.

## Struktur (lebih kurang 100 s, 30 ayat pendek)

| Bahagian | Contoh rujukan | Visual |
|---|---|---|
| Hook rutin | "Bangun, kerja, makan, tidur. Esok, ulang lagi." | ikon berpusing keliling watak |
| Soalan peribadi | "Sebenarnya, aku hidup untuk apa?" | tanda soal, gelembung fikiran |
| Ayat utama | Surah + nombor ayat, bacaan maksud | kad Arab |
| Kata kunci | "Kata kuncinya: 'abathan'" | kad KUNCI ARAB |
| Tafsir 2 hingga 3 ulama | Ibnu Kathir, As-Sa'di, Ibnu 'Asyur | label sumber + ilustrasi |
| Ayat sokongan | Az-Zariyat 56, Al-Mulk 2 | kad Arab + ilustrasi |
| Hadis | at-Tirmizi, empat soalan | jam pasir, ikon ilmu / harta / tubuh |
| Kisah / kajian | Viktor Frankl, Umar bin Abdul Aziz | watak + kompas / podium |
| Aplikasi | "Kerja jadi ibadah, rumah jadi amal, penat jadi pahala." | ikon bertukar |
| Soalan penutup | "Esok bila bangun, tanya diri: hari ini aku hidup untuk apa?" | kembali ke babak pertama |
| Doa + CTA | "Moga Allah jadikan setiap hari kita bermakna. Kongsikan kepada yang tersayang." | watak bercahaya |

Untuk video jualan: tukar CTA kepada produk (buku), letak gambar buku dalam kad putih yang sama gaya, dan butang
"Tekan link dekat bawah" berwarna oren.

## Kenapa berkesan

1. Hook relatable tanpa produk: rutin yang semua orang lalui, terus disusuli soalan besar.
2. Kredibiliti berlapis: ayat, kemudian tafsir, hadis, sejarah, sains. Setiap sumber dinamakan di skrin.
3. Visual tenang dan konsisten: penonton fokus pada ayat, bukan kesan.
4. Sari kata ikut suara memberi rasa "dibacakan", sesuai untuk tazkirah.
5. Penutup sambung balik ke hook (rutin yang sama, kini bermakna) dan CTA kongsi.

## Peraturan

- Ayat Al-Quran dan hadis mesti disalin dari sumber yang sah dan disemak (teks Arab, nombor ayat, darjat hadis)
  sebelum render. Jangan menjana teks Arab dari ingatan.
- Satu ilustrasi pada satu masa; ruang kosong ialah sebahagian gaya.
- Tiada watak kartun berwarna-warni atau sticker tebal (itu template kertas).

## Cara bina (kod)

Renderer: `arab.py` (frame dilukis dengan PIL, tiada aset luar). `project.json` dengan `"type": "arab"`:

```json
{"type": "arab", "source": "input/vo.mp4", "bg": "putih",
 "scenes": [{"start": 0.0, "end": 3.8, "line": "ayat VO penuh", "keys": ["kata kunci"],
             "illus": {"kind": "ask|stairs|hourglass|books|path|glow|wave"},
             "card": {"kind": "photo", "img": "cover.jpg"} ,
             "pills": [["UPSA", 25.7]], "label": "sumber"}],
 "cta": {"at": 31.6, "text": "Tekan link dekat bawah"}}
```

- Watak: `"illus": {"char": "kira/gembira", "char_at": [[12.6, "kira/stres"]], "char_scale": 1.3}` guna watak
  yang disimpan (`kira/`, `abang/`, `adikbiru/`, `ortu/pasangan`) di tempat figura lukisan. Tanpa `char`, figura lukisan.
- Beberapa watak sekali: `"illus": {"kind": "cast", "cast": [{"char": "kira/stres", "x": 300, "size": 340, "at": 8.6,
  "char_at": [[11.0, "kira/sedih"]]}, ...]}` (kaki di satu garisan lantai). Contoh: `projects/arab-ummi/`.
- Ikon: `"icons": [{"img": "icons/kuiz.png", "x": 830, "y": 1030, "at": 1.9, "size": 170, "tag": "UJIAN", "rot": 6}]`
  (ikon sekolah dalam `icons/`, ikon matematik dalam `mat/`), muncul dengan bunyi pop lembut.
- Sari kata keluar **seketul-seketul** (besar, `sub_size` 84): letak `|` dalam `line` di tempat ketul baru bermula,
  contoh `"Kenapa ada pelajar | Tingkatan 3 | yang Sejarah dia | senang je?"`. Tanpa `|`, dipecah di koma / noktah atau
  setiap 4 perkataan (`chunk_words`). `"chunk": false` tunjuk ayat penuh sekali gus.
- `card` `"kind": "key"` ialah kad KATA KUNCI (`word`, `sub`); `"photo"` ialah gambar produk dalam kad putih.
- `bg`: `putih` (putih kertas) atau `krim` (macam rujukan).
- `python arab.py projects/<nama>` untuk video, `python arab.py projects/<nama> 1.5 4 8` untuk lembaran stills.
- VO tidak dinormalkan dalam renderer: naikkan gain semasa encode akhir sampai lebih kurang −10 LUFS.
- Contoh: `projects/arab-1088/` (1088 Soalan Objektif Sejarah, latar putih).
