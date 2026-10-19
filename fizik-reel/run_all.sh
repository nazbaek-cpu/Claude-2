#!/bin/bash
# Source video -> final reel, in one command.
#
#   ./run_all.sh --drive <google-drive-link-or-id>   download the source into work/src.mp4
#   ./run_all.sh --src path/to/video.mp4             use a local file
#   ./run_all.sh                                     reuse work/src.mp4
#
# Options:
#   --draft            quick 720p preview (out/preview_720p.mp4) instead of the final render
#   --until STEP       stop after STEP (e.g. --until transcribe to plan cues.json for a new video)
#   --from STEP        skip the steps before STEP (reuse earlier outputs)
#   --retranscribe     run Whisper even if work/tr_large.json exists
#
# Steps: fetch transcribe cuts voice zoom aroll build audio render deliver
# For a new video, edit config.json and cues.json (source seconds) after the transcribe step.
set -euo pipefail
cd "$(dirname "$0")"

STEPS=(fetch transcribe cuts voice zoom aroll build audio render deliver)
SRC_ARG="" DRIVE="" DRAFT=0 UNTIL="" FROM="" RETRANSCRIBE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRC_ARG="$2"; shift 2 ;;
    --drive) DRIVE="$2"; shift 2 ;;
    --draft) DRAFT=1; shift ;;
    --until) UNTIL="$2"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    --retranscribe) RETRANSCRIBE=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
for s in "$UNTIL" "$FROM"; do
  [ -z "$s" ] || [[ " ${STEPS[*]} " == *" $s "* ]] || { echo "unknown step: $s (${STEPS[*]})" >&2; exit 2; }
done

PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
WORKERS=${WORKERS:-4}
mkdir -p work out reel/assets

started=0; [ -z "$FROM" ] && started=1
step() {  # step NAME -> 0 if it should run
  [ "$started" = 1 ] || [ "$1" = "$FROM" ] && started=1
  [ "$started" = 1 ] || return 1
  echo "== $1"
}
done_step() { [ "$1" = "$UNTIL" ] && { echo "stopped after $1"; exit 0; }; return 0; }

if step fetch; then
  if [ -n "$DRIVE" ]; then
    id=$(sed -E 's#.*/d/([^/?]+).*#\1#; s#.*[?&]id=([^&]+).*#\1#' <<<"$DRIVE")
    curl -fSL -o work/src.part "https://drive.usercontent.google.com/download?id=${id}&export=download&confirm=t"
    mv work/src.part work/src.mp4
  elif [ -n "$SRC_ARG" ]; then
    cp "$SRC_ARG" work/src.mp4
  fi
  [ -s work/src.mp4 ] || { echo "no source video: pass --src or --drive" >&2; exit 1; }
  ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact work/src.mp4
fi; done_step fetch

if step transcribe; then
  if [ "$RETRANSCRIBE" = 1 ] || [ ! -s work/tr_large.json ]; then
    $PY transcribe.py work/src.mp4 work/tr_large.json
  else
    echo "reusing work/tr_large.json (--retranscribe to redo)"
  fi
fi; done_step transcribe

if step cuts; then $PY cuts.py work/src.mp4 work/keep.json; fi; done_step cuts
if step voice; then $PY voice.py; fi; done_step voice
if step zoom; then $PY zoom.py; fi; done_step zoom

if step aroll; then
  rm -rf work/segs
  pids=()
  for ((i = 0; i < WORKERS; i++)); do $PY base.py "$i" "$WORKERS" 2>"work/base$i.log" & pids+=($!); done
  for i in "${!pids[@]}"; do wait "${pids[$i]}" || { echo "A-roll worker $i failed:" >&2; tail -5 "work/base$i.log" >&2; exit 1; }; done
  n=$($PY -c "import json; print(len(json.load(open('work/keep.json'))))")
  : > work/segs.txt
  for ((i = 0; i < n; i++)); do
    f=$(printf 'segs/s%02d.mp4' "$i")
    [ -s "work/$f" ] || { echo "missing work/$f" >&2; exit 1; }
    echo "file '$f'" >> work/segs.txt
  done
  # 1 s keyframe interval: HyperFrames seeks the A-roll per frame
  ffmpeg -v error -y -f concat -safe 0 -i work/segs.txt -c:v libx264 -preset medium -crf 14 \
    -g 30 -keyint_min 30 -pix_fmt yuv420p -movflags +faststart reel/assets/base.mp4
fi; done_step aroll

if step build; then $PY build.py; fi; done_step build

if step audio; then
  dur=$($PY -c "import json; print(json.load(open('work/edl.json'))['dur'])")
  gain=$($PY -c "import json; print(json.load(open('config.json'))['mix']['sfx_gain'])")
  $PY sfx.py work/sfx_cues.json "$dur" work/sfx.wav
  ffmpeg -v error -y -i work/voice.wav -i work/sfx.wav -filter_complex \
    "[1:a]volume=${gain}[s];[0:a][s]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]" \
    -map "[a]" -ar 48000 reel/assets/mix.wav
fi; done_step audio

RAW=out/final_raw.mp4; Q=high
[ "$DRAFT" = 1 ] && { RAW=out/preview_raw.mp4; Q=draft; }
if step render; then
  npx --no-install hyperframes lint reel || true
  npx --no-install hyperframes render reel -q "$Q" -w "$WORKERS" -o "$RAW"
fi; done_step render

if step deliver; then
  if [ "$DRAFT" = 1 ]; then
    ffmpeg -v error -y -i "$RAW" -vf scale=720:-2 -c:v libx264 -preset slow -b:v 2800k -maxrate 3500k -bufsize 6000k \
      -c:a aac -b:a 160k -movflags +faststart out/preview_720p.mp4
    OUT=out/preview_720p.mp4
    echo "preview: $OUT"
  else
    # two-pass to stay under ~30 MB for a ~60 s reel
    ffmpeg -v error -y -i "$RAW" -c:v libx264 -preset slow -b:v 3500k -pass 1 -passlogfile out/p2 -an -f mp4 /dev/null
    ffmpeg -v error -y -i "$RAW" -c:v libx264 -preset slow -b:v 3500k -maxrate 5000k -bufsize 7000k -pass 2 \
      -passlogfile out/p2 -c:a aac -b:a 192k -movflags +faststart out/final_1080p.mp4
    OUT=out/final_1080p.mp4
    echo "final: $OUT"
  fi
  ffprobe -v error -show_entries stream=codec_type,width,height:format=duration,size -of compact "$OUT"
fi
