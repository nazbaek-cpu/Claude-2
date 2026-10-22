#!/bin/bash
# Voiceover + face photos + scenes.json -> 9:16 reel.
#
#   ./run.sh projects/<name>                 everything, final 1080p -> projects/<name>/out/final_1080p.mp4
#   ./run.sh projects/<name> --draft         quick 720p preview      -> projects/<name>/out/preview_720p.mp4
#   ./run.sh projects/<name> --until script  only write build/script.txt (variables filled) to paste into your TTS
#   ./run.sh projects/<name> --from compose  reuse earlier steps (e.g. after editing scenes.json)
#   --retranscribe                           run Whisper again even if build/whisper.json exists
#
# Steps: script stickers align vo music compose render deliver
set -euo pipefail
cd "$(dirname "$0")"

STEPS=(script stickers align vo music compose render deliver)
[ $# -ge 1 ] || { sed -n '2,10p' "$0"; exit 2; }
PRJ="${1%/}"; shift
DRAFT=0 UNTIL="" FROM="" RETR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --draft) DRAFT=1; shift ;;
    --until) UNTIL="$2"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    --retranscribe) RETR="--retranscribe"; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
for s in "$UNTIL" "$FROM"; do
  [ -z "$s" ] || [[ " ${STEPS[*]} " == *" $s "* ]] || { echo "unknown step: $s (${STEPS[*]})" >&2; exit 2; }
done
[ -f "$PRJ/project.json" ] || { echo "no project.json in $PRJ" >&2; exit 1; }

PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
mkdir -p "$PRJ/build" "$PRJ/out"
started=0; [ -z "$FROM" ] && started=1
step() { [ "$started" = 1 ] || [ "$1" = "$FROM" ] && started=1; [ "$started" = 1 ] || return 1; echo "== $1"; }
done_step() { [ "$1" = "$UNTIL" ] && { echo "stopped after $1"; exit 0; }; return 0; }

if step script; then
  $PY -c "import sys; from common import Project; p = Project(sys.argv[1]); open(p.p('build', 'script.txt'), 'w').write(p.script() + '\n')" "$PRJ"
  echo "script with variables filled: $PRJ/build/script.txt"
fi; done_step script
if step stickers; then $PY stickers.py "$PRJ" --previews; fi; done_step stickers
if step align; then $PY align.py "$PRJ" $RETR; fi; done_step align
if step vo; then $PY vo.py "$PRJ"; fi; done_step vo
if step music; then $PY music.py "$PRJ"; fi; done_step music
if step compose; then $PY compose.py "$PRJ"; fi; done_step compose

RAW="$PRJ/out/final_raw.mp4"; Q=high
[ "$DRAFT" = 1 ] && { RAW="$PRJ/out/preview_raw.mp4"; Q=draft; }
if step render; then
  npx --no-install hyperframes lint "$PRJ/build/reel" || true
  npx --no-install hyperframes render "$PRJ/build/reel" -q "$Q" -w "${WORKERS:-4}" -o "$RAW"
fi; done_step render

if step deliver; then
  if [ "$DRAFT" = 1 ]; then
    OUT="$PRJ/out/preview_720p.mp4"
    ffmpeg -v error -y -i "$RAW" -vf scale=720:-2 -c:v libx264 -preset slow -b:v 2800k -maxrate 3500k -bufsize 6000k \
      -c:a aac -b:a 160k -movflags +faststart "$OUT"
  else
    OUT="$PRJ/out/final_1080p.mp4"
    ffmpeg -v error -y -i "$RAW" -c:v libx264 -preset slow -b:v 3500k -pass 1 -passlogfile "$PRJ/out/p2" -an -f mp4 /dev/null
    ffmpeg -v error -y -i "$RAW" -c:v libx264 -preset slow -b:v 3500k -maxrate 5000k -bufsize 7000k -pass 2 \
      -passlogfile "$PRJ/out/p2" -c:a aac -b:a 192k -movflags +faststart "$OUT"
  fi
  ffprobe -v error -show_entries stream=codec_type,width,height:format=duration,size -of compact "$OUT"
  echo "done: $OUT"
fi
