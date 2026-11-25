#!/bin/sh
# M9 sentence-level extraction on local open-weight models (sequential; resumable: rerun to continue).
# Base models: raw completion with the article prefix (classic extraction). Instruct models: plain (Su) and role-play
# (Freeman, upper bound) prompts with the previous sentence.
M9=".venv/bin/python -I src/m9_decomposition.py"
LC="--inputs data/cc/lacontra_members.jsonl data/cc/lacontra_controls.jsonl --tag lacontra"
set -x
for M in Meta-Llama-3.1-8B-4bit gemma-2-9b-4bit Qwen2.5-7B-4bit Mistral-7B-v0.3-4bit; do
  $M9 --model mlx-community/$M --style completion --context prefix --n 212 --k 5 $LC
  $M9 --model mlx-community/$M --style completion --context prefix --n 150 --k 5
done
for M in Meta-Llama-3.1-8B-Instruct-4bit Qwen2.5-7B-Instruct-4bit; do
  for S in plain roleplay; do
    $M9 --model mlx-community/$M --style $S --n 212 --k 5 $LC
    $M9 --model mlx-community/$M --style $S --n 60 --k 4
  done
done
echo QUEUE5 done
