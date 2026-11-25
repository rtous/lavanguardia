#!/bin/sh
# M9 sentence-level extraction on local open-weight models (sequential; resumable: rerun to continue).
# Base models: raw completion with the article prefix (classic extraction). Instruct models: plain (Su) and role-play
# (Freeman, upper bound) prompts with the previous sentence. Sizes cut after the first La Contra run was clearly null.
M9=".venv/bin/python -I src/m9_decomposition.py"
LC="--inputs data/cc/lacontra_members.jsonl data/cc/lacontra_controls.jsonl --tag lacontra"
set -x
run_base() { $M9 --model mlx-community/$1 --style completion --context prefix --n 100 --k 4 $LC
             $M9 --model mlx-community/$1 --style completion --context prefix --n 100 --k 4; }
run_inst() { for S in roleplay plain; do $M9 --model mlx-community/$1 --style $S --n 60 --k 4 $LC
                                         $M9 --model mlx-community/$1 --style $S --n 60 --k 4; done; }
run_base Meta-Llama-3.1-8B-4bit
run_inst Meta-Llama-3.1-8B-Instruct-4bit
run_inst Qwen2.5-7B-Instruct-4bit
for M in gemma-2-9b-4bit Qwen2.5-7B-4bit Mistral-7B-v0.3-4bit; do run_base $M; done
echo QUEUE5 done
