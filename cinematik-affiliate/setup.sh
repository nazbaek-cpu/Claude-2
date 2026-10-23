#!/bin/bash
# Install everything cinematik-affiliate needs. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

for tool in ffmpeg ffprobe python3 curl; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

# MediaPipe needs libEGL even on CPU; the typography uses Inter
missing=()
ldconfig -p | grep -q libEGL.so.1 || missing+=(libegl1 libgles2)
[ -f /usr/share/fonts/opentype/inter/InterDisplay-Bold.otf ] || missing+=(fonts-inter)
if [ ${#missing[@]} -gt 0 ]; then
  if command -v apt-get >/dev/null && [ "$(id -u)" = 0 ]; then
    apt-get install -y -q "${missing[@]}" >/dev/null 2>&1 || { apt-get update -q >/dev/null && apt-get install -y -q "${missing[@]}" >/dev/null; }
  else
    echo "install these system packages: ${missing[*]}" >&2; exit 1
  fi
fi

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt
# OCR for "hflip": "auto"; --no-deps so its plain opencv-python never replaces opencv-contrib (guidedFilter)
.venv/bin/pip install -q --disable-pip-version-check --no-deps rapidocr-onnxruntime==1.2.3

# models (Apache-2.0): person mask for text-behind-subject, face landmarks for the beauty pass
fetch() {  # fetch <url> <dest>
  [ -s "$2" ] && return 0
  mkdir -p "$(dirname "$2")"
  curl -fsSL -o "$2.part" "$1" && mv "$2.part" "$2"
}
MP=https://storage.googleapis.com/mediapipe-models
fetch "$MP/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite" models/selfie_segmenter.tflite
fetch "$MP/face_landmarker/face_landmarker/float16/latest/face_landmarker.task" models/face_landmarker.task
# DeepFilterNet CLI for the studio voice (static binary, model embedded)
DF=tools/deep-filter
if [ ! -x "$DF" ]; then
  mkdir -p tools
  curl -fsSL -o "$DF.part" \
    "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl"
  chmod +x "$DF.part" && mv "$DF.part" "$DF"
fi
echo "setup ok"
