#!/bin/bash
# M10 pilot on local open-weight models, strictly sequential (one GPU job at a time). Resumable: rerun to continue.
cd "$(dirname "$0")/.." || exit 1
N=${N:-60}
for M in mlx-community/Meta-Llama-3.1-8B-Instruct-4bit mlx-community/Qwen2.5-7B-Instruct-4bit \
         mlx-community/gemma-2-9b-4bit mlx-community/Meta-Llama-3.1-8B-4bit; do
  .venv/bin/python -I src/m10_exclusive_facts.py run --model "$M" --n "$N" 2>&1 | grep -v -e Warning -e Fetching
done
.venv/bin/python -I src/m10_exclusive_facts.py summary
echo "M10 LOCAL done"
