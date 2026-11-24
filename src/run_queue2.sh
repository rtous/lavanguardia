#!/bin/sh
# Sequential GPU queue (no pgrep waits): neighbour tests, XGLM reference, Llama 3 vs 3.1 scores.
set -x
for spec in "mlx-community/gemma-2-9b-4bit:gemma2_9b" "mlx-community/Qwen2.5-7B-4bit:qwen25_7b" "mlx-community/Meta-Llama-3.1-8B-4bit:llama31_8b" "mlx-community/Mistral-7B-v0.3-4bit:mistral7b_v03"; do
  M=${spec%%:*}; T=${spec##*:}
  .venv/bin/python -I src/m5_neighbour.py --model $M --out results/m5_neighbour_$T.jsonl
done
echo NEIGHBOUR done
.venv/bin/python -I src/m5_hf.py --model facebook/xglm-2.9B --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_xglm29.jsonl
.venv/bin/python -I src/m5_hf.py --model facebook/xglm-2.9B --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_xglm29.jsonl
echo XGLM done
L3=mlx-community/Meta-Llama-3-8B-4bit; L31=mlx-community/Meta-Llama-3.1-8B-4bit
.venv/bin/python -I src/m5_logprob.py --model $L31 --inputs data/cc/mid2023.jsonl:member --out results/m5_mid2023_llama31_8b.jsonl
.venv/bin/python -I src/m5_logprob.py --model $L3 --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_llama3_8b.jsonl
.venv/bin/python -I src/m5_logprob.py --model $L3 --inputs data/cc/mid2023.jsonl:member --out results/m5_mid2023_llama3_8b.jsonl
echo DID scoring done
