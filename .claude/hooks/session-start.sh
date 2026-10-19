#!/bin/bash
# Claude Code cloud sessions: install the fizik-reel pipeline deps (venv, npm, YuNet, headless Chrome).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

"$CLAUDE_PROJECT_DIR/fizik-reel/setup.sh"
