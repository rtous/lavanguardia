#!/usr/bin/env bash
# Session 12 GPU queue, reordered 2026-11-28 ~10:40 UTC by expected value (user request): most-copied articles (M13)
# before ordinary ones (M11), Llama-3.1 before Qwen2.5. One sequential script (two 7B models do not fit on a T4).
# Pre-registered analyses are unchanged: each model's M13 primary test uses its M11 controls, computed once M11 is done.
#   nohup ./src/run_colab_session12b.sh >> logs/colab_session12.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
export HF_PRECISION=${HF_PRECISION:-int4}
ts() { date -u +%FT%TZ; }
quiet() { grep --line-buffered -v -i -e warning -e "Loading weights" -e Fetching; }
for step in "m13 meta-llama/Llama-3.1-8B-Instruct" "m13 Qwen/Qwen2.5-7B-Instruct" \
            "m11 meta-llama/Llama-3.1-8B-Instruct" "m11 Qwen/Qwen2.5-7B-Instruct"; do
  set -- $step
  echo "=== $(ts) $1 $2"
  if [ "$1" = m13 ]; then python -I src/m13_most_copied.py run --model "hf:$2" 2>&1 | quiet
  else python -I src/m11_nyt_style.py run --model "hf:$2" 2>&1 | quiet; fi
  python -I src/m11_nyt_style.py summary > /dev/null 2>&1; python -I src/m13_most_copied.py summary > /dev/null 2>&1
done
echo "=== $(ts) session 12 queue done"
