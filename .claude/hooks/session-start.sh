#!/bin/bash
# Claude Code cloud sessions: install the pipeline deps (venvs, npm, models, headless Chrome).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

"$CLAUDE_PROJECT_DIR/fizik-reel/setup.sh"
"$CLAUDE_PROJECT_DIR/sticker-reel/setup.sh"
"$CLAUDE_PROJECT_DIR/cinematik-affiliate/setup.sh"
