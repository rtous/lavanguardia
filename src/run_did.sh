#!/bin/sh
# Scores needed for the Llama 3 vs 3.1 difference-in-differences. Waits for the GPU queue and the mid-2023 collection.
while pgrep -f "run_m5_models.sh|run_xglm.sh|collect_mid2023.sh" >/dev/null; do sleep 30; done
L3=mlx-community/Meta-Llama-3-8B-4bit; L31=mlx-community/Meta-Llama-3.1-8B-4bit
.venv/bin/python -I src/m5_logprob.py --model $L31 --inputs data/cc/mid2023.jsonl:member --out results/m5_mid2023_llama31_8b.jsonl
.venv/bin/python -I src/m5_logprob.py --model $L3 --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_llama3_8b.jsonl
.venv/bin/python -I src/m5_logprob.py --model $L3 --inputs data/cc/mid2023.jsonl:member --out results/m5_mid2023_llama3_8b.jsonl
echo DID scoring done
