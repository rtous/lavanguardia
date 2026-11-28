#!/usr/bin/env bash
# M13 on API models (docs/prereg/m13_amendment1_api_20261128.md). Keys from .env (gitignored, chmod 600):
#   ANTHROPIC_API_KEY=...   GEMINI_API_KEY=...
#   nohup ./src/run_colab_m13_api.sh claude >> logs/m13_claude.log 2>&1 &
#   nohup ./src/run_colab_m13_api.sh gemini >> logs/m13_gemini.log 2>&1 &
# Resumable (skips finished windows). No GPU: runs alongside the GPU queue.
set -u
cd "$(dirname "$0")/.."
[ -r .env ] && { set -a; . ./.env; set +a; }
case "${1:-}" in
  claude) M=claude-opus-4-5-20251101 ;;
  gemini) M=gemini-3.1-flash-lite ;;
  *) echo "usage: $0 claude|gemini" >&2; exit 1 ;;
esac
echo "=== $(date -u +%FT%TZ) M13 $M"
python -I src/m13_most_copied.py run --model "$M"
python -I src/m13_most_copied.py summary > /dev/null
echo "=== $(date -u +%FT%TZ) M13 $M done"
