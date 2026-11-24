#!/bin/sh
# Overnight: local same-facts rewrites -> neighbour scores with Llama 3 and 3.1 -> DiD on the neighbour gap.
set -x
P=data/decop/paraphrases_mid2023.jsonl
.venv/bin/python -I src/local_paraphrase.py --out $P
.venv/bin/python -I src/m5_neighbour.py --model mlx-community/Meta-Llama-3.1-8B-4bit --src $P:local --out results/m5_neighbour_mid2023_llama31_8b.jsonl
.venv/bin/python -I src/m5_neighbour.py --model mlx-community/Meta-Llama-3-8B-4bit --src $P:local --out results/m5_neighbour_mid2023_llama3_8b.jsonl
.venv/bin/python -I src/did_neighbour.py --l3 results/m5_neighbour_mid2023_llama3_8b.jsonl --l31 results/m5_neighbour_mid2023_llama31_8b.jsonl --out results/did_neighbour.json
echo QUEUE3 done
