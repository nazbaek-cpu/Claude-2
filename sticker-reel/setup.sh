#!/bin/bash
# Install everything sticker-reel needs. Safe to run again.
#   PREFETCH_WHISPER=1 ./setup.sh   also downloads the Whisper model (~3 GB) now instead of on first use
set -euo pipefail
cd "$(dirname "$0")"

for tool in ffmpeg ffprobe node npm python3 curl; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt

# HyperFrames, GSAP, Twemoji icons, Fredoka + Instrument Serif fonts
npm install --no-audit --no-fund --loglevel=error

# models: YuNet face detector (MIT), BiRefNet-lite person cut-out (MIT)
fetch() {  # fetch <url> <dest>
  [ -s "$2" ] && return 0
  mkdir -p "$(dirname "$2")"
  curl -fsSL -o "$2.part" "$1" && mv "$2.part" "$2"
}
fetch "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx" models/yunet.onnx
fetch "https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/main/onnx/model.onnx" models/birefnet_lite.onnx

npx --no-install hyperframes browser ensure >/dev/null

if [ "${PREFETCH_WHISPER:-0}" = "1" ]; then
  .venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', compute_type='int8')"
fi
echo "setup ok"
