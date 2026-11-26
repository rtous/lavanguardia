#!/usr/bin/env bash
# M11 NYT-style extraction (pre-registered: docs/prereg/m11_nyt_style.md). Sequential, one GPU job, resumable:
# rerun after a disconnect. Needs HF_TOKEN (Llama licence). Log: logs/colab_m11.log. Run src/colab_sync.sh loop alongside.
set -u
cd "$(dirname "$0")/.."
export HF_PRECISION=${HF_PRECISION:-int4}
for M in BSC-LT/salamandra-7b-instruct meta-llama/Llama-3.1-8B-Instruct Qwen/Qwen2.5-7B-Instruct; do
  echo "=== $(date -u +%FT%TZ) $M ($HF_PRECISION)"
  python -I src/m11_nyt_style.py run --model hf:$M 2>&1 | grep -v -i -e warning -e "Loading weights" -e Fetching
done
python -I src/m11_nyt_style.py summary
echo "=== $(date -u +%FT%TZ) M11 done"
