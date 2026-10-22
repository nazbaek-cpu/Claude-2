#!/bin/bash
# Talking-head footage + project.json -> cinematic 9:16 affiliate video.
#
#   ./run.sh projects/<name> --transcribe    Whisper -> build/subs_draft.json (copy into project.json "subs")
#   ./run.sh projects/<name>                 SFX + render                -> projects/<name>/out/final.mp4
#   ./run.sh projects/<name> --limit 8       render only the first 8 s   -> projects/<name>/out/preview.mp4
set -euo pipefail
cd "$(dirname "$0")"

[ $# -ge 1 ] || { sed -n '2,7p' "$0"; exit 2; }
PRJ="${1%/}"; shift
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
[ -f "$PRJ/project.json" ] || { echo "no project.json in $PRJ" >&2; exit 1; }

prep() {  # pause/tempo pass (only when project.json has "speed"), studio voice, then the SFX track
  if grep -q '"speed"' "$PRJ/project.json"; then $PY speed.py "$PRJ"; fi
  if ! grep -q '"studio": false' "$PRJ/project.json"; then $PY voice.py "$PRJ"; fi
  $PY sfx.py "$PRJ"
}
case "${1:-}" in
  --transcribe) $PY transcribe.py "$PRJ"; exit 0 ;;
  --limit) prep; $PY render.py "$PRJ" --limit "$2" --out "$PRJ/out/preview.mp4"; exit 0 ;;
  "") ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac
prep
$PY render.py "$PRJ"
