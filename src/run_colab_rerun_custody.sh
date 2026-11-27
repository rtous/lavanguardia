#!/usr/bin/env bash
# Chain-of-custody re-run (docs/prereg/amendment_rerun_custody_20261127.md). Two independent queues, each sequential:
#   ./src/run_colab_rerun_custody.sh api   # M12 on both Gemini models (needs GEMINI_API_KEY in the env)
#   ./src/run_colab_rerun_custody.sh gpu   # M11 Salamandra, the 117 articles run 1 did (T4, int4)
# Resumable: rerun the same command after a disconnect. Logs: logs/rerun_custody_{api,gpu}.log
set -u
cd "$(dirname "$0")/.."
case "${1:-}" in
  api) for M in gemini-3.5-flash-lite gemini-3.1-flash-lite; do
         echo "=== $(date -u +%FT%TZ) M12 rerun $M"; python -I src/m12_url_reverse.py run --model $M --rerun; done
       python -I src/m12_url_reverse.py compare; echo "=== $(date -u +%FT%TZ) API rerun done" ;;
  gpu) export HF_PRECISION=${HF_PRECISION:-int4}
       echo "=== $(date -u +%FT%TZ) M11 rerun salamandra ($HF_PRECISION)"
       python -I src/m11_nyt_style.py run --model hf:BSC-LT/salamandra-7b-instruct --rerun 2>&1 \
         | grep -v -i -e warning -e "Loading weights" -e Fetching
       python -I src/m11_nyt_style.py compare; echo "=== $(date -u +%FT%TZ) GPU rerun done" ;;
  *) echo "usage: $0 api|gpu" >&2; exit 1 ;;
esac
