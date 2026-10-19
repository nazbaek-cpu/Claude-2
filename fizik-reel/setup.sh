#!/bin/bash
# Install everything the pipeline needs. Safe to run again.
#   PREFETCH_WHISPER=1 ./setup.sh   also downloads the Whisper model (~3 GB) now instead of on first use
set -euo pipefail
cd "$(dirname "$0")"

for tool in ffmpeg ffprobe node npm python3; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

# Python deps in a local venv (system Python may be externally managed)
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt

# HyperFrames, GSAP, Twemoji icons, Plus Jakarta Sans font
npm install --no-audit --no-fund --loglevel=error

# YuNet face detector for the skin retouch
YUNET=models/yunet.onnx
if [ ! -s "$YUNET" ]; then
  mkdir -p models
  curl -fsSL -o "$YUNET.part" \
    "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx"
  mv "$YUNET.part" "$YUNET"
fi

# DeepFilterNet CLI for the "studio"/"clear" voice presets (static binary, model embedded)
DF=tools/deep-filter
if [ ! -x "$DF" ]; then
  mkdir -p tools
  curl -fsSL -o "$DF.part" \
    "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl"
  chmod +x "$DF.part" && mv "$DF.part" "$DF"
fi

# Headless Chrome used by `hyperframes render`
npx --no-install hyperframes browser ensure >/dev/null

if [ "${PREFETCH_WHISPER:-0}" = "1" ]; then
  .venv/bin/python -c "import json; from faster_whisper import WhisperModel; WhisperModel(json.load(open('config.json'))['whisper_model'], device='cpu', compute_type='int8')"
fi

mkdir -p work out
echo "setup ok"
