# Watak perempuan: Kak Kira (lembaran rujukan baru)

Watak perempuan **utama** untuk video animasi kartun: guna lembaran ini, bukan lembaran 8 emosi yang lama.
Lembaran asal (1536x1024, "Lembaran Rujukan Watak Mascot · Kak Kira – Pose, Aksi & Ekspresi") ialah milik
pengguna. Gambar ini **tidak** disimpan dalam repo awam ini; minta pengguna muat naik semula kalau sesi baru tak ada fail itu.

## Isi

| Jalur | Fail (dalam `input/kira/`) | Guna |
|---|---|---|
| 10 pose badan penuh | `sapa`, `idea`, `ketawa`, `sedih`, `terkejut`, `stres`, `berfikir`, `bangga`, `menerang`, `gembira` | item `doodle` (watak berdiri, tukar pose ikut ayat) |
| 10 ekspresi muka | `muka/gembira`, `muka/teruja`, `muka/ketawa`, `muka/sedih`, `muka/terkejut`, `muka/risau`, `muka/berfikir`, `muka/bangga`, `muka/marah`, `muka/ingin_tahu` | item `sticker` (muka kecil sebagai reaksi, contoh di sebelah tajuk) |

Padanan pose ikut jenis ayat:

| Ayat | Pose |
|---|---|
| Hook, sapa penonton, CTA | `sapa` |
| Penyelesaian, "sebab tu…" | `idea` |
| Masalah, risau | `berfikir`, `stres` |
| Akibat buruk | `sedih`, `terkejut` |
| Terangkan isi / ciri produk | `menerang` |
| Hasil baik, "boleh jawab semua" | `bangga`, `gembira` |

## Cara potong

Watak dalam lembaran ini tak tersusun sekata, jadi pose dipotong dengan `poses.py --auto`: setiap watak dikesan ikut bentuk,
dan mentol, awan atau tanda soal ikut watak yang paling dekat. Muka tersusun sekata tapi tudungnya bersentuhan, jadi guna grid.
Tajuk jalur dan label di bawah setiap watak dibuang dulu.

```bash
SHEET=input-upload/kak-kira.png; OUT=projects/<nama>/input/kira
python - "$SHEET" /dev/shm/kira_bands <<'EOF'
import os, sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert("RGB"); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
paper = im.getpixel((5, 5))
a = im.copy(); ImageDraw.Draw(a).rectangle((0, 0, 566, 190), fill=paper)        # tajuk "10 Pose & Aksi"
a.crop((0, 150, 1536, 536)).save(f"{out}/pose.png")                               # sampai kaki, tanpa label
b = im.crop((16, 688, 1520, 918)); ImageDraw.Draw(b).rectangle((0, 0, 440, 10), fill=paper)   # dalam kotak muka
b.save(f"{out}/muka.png")
EOF
python poses.py /dev/shm/kira_bands/pose.png $OUT --auto 10 \
  --names sapa,idea,ketawa,sedih,terkejut,stres,berfikir,bangga,menerang,gembira
python poses.py /dev/shm/kira_bands/muka.png $OUT/muka --grid 10x1 --icons \
  --names gembira,teruja,ketawa,sedih,terkejut,risau,berfikir,bangga,marah,ingin_tahu
```

Semua 10 pose dipotong dengan saiz kanvas yang sama dan diletak ikut kaki, jadi watak tak melompat bila pose bertukar.
Item `doodle` biasa: `"x": 280, "y": 1250, "h": 520`, dengan `"enter": "slide"` pada babak pertama dan CTA.
