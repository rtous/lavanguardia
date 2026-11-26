#!/bin/bash
# M10 La Contra Q->A items on local models, strictly sequential. Resumable.
cd "$(dirname "$0")/.." || exit 1
for M in mlx-community/gemma-2-9b-4bit mlx-community/Meta-Llama-3.1-8B-4bit \
         mlx-community/Qwen2.5-7B-Instruct-4bit mlx-community/Meta-Llama-3.1-8B-Instruct-4bit; do
  .venv/bin/python -I src/m10_exclusive_facts.py run --model "$M" --types qa --n 300 2>&1 | grep -v -e Warning -e Fetching
done
echo "QA LOCAL done"
