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
  opt() { $PY -c "import sys, project; c = project.read(sys.argv[1]); sys.exit(0 if eval(sys.argv[2]) else 1)" "$PRJ" "$1"; }
  if opt 'c.get("speed")'; then $PY speed.py "$PRJ"; fi
  if opt 'c.get("voice", {}).get("studio", True)'; then $PY voice.py "$PRJ"; fi
  $PY sfx.py "$PRJ"
}
if $PY -c "import sys, project; sys.exit(0 if project.read(sys.argv[1]).get('type') == 'explainer' else 1)" "$PRJ"; then
  # no-face motion-graphics reel on a voiceover: studio voice, then explainer.py (builds its own SFX)
  [ "${1:-}" = "--transcribe" ] && { $PY transcribe.py "$PRJ"; exit 0; }
  if $PY -c "import sys, project; sys.exit(0 if project.read(sys.argv[1]).get('speed') else 1)" "$PRJ"; then $PY speed.py "$PRJ"; fi
  $PY voice.py "$PRJ"
  $PY explainer.py "$PRJ" "$@"; exit 0
fi
case "${1:-}" in
  --transcribe) $PY transcribe.py "$PRJ"; exit 0 ;;
  --limit) prep; $PY render.py "$PRJ" --limit "$2" --out "$PRJ/out/preview.mp4"; exit 0 ;;
  "") ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac
prep
$PY render.py "$PRJ"
