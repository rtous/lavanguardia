#!/bin/sh
# Score random + La Contra samples with several open-weight base models (local, MLX), sequentially.
for spec in "mlx-community/Meta-Llama-3.1-8B-4bit:llama31_8b" "mlx-community/Mistral-7B-v0.3-4bit:mistral7b_v03" "mlx-community/gemma-2-9b-4bit:gemma2_9b"; do
  M=${spec%%:*}; T=${spec##*:}
  echo "== $T start $(date)"
  .venv/bin/python -I src/m5_logprob.py --model $M --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_$T.jsonl > logs/m5_$T.log 2>&1 || echo "FAILED $T random"
  .venv/bin/python -I src/m5_logprob.py --model $M --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_$T.jsonl >> logs/m5_$T.log 2>&1 || echo "FAILED $T lacontra"
  echo "== $T done $(date) $(wc -l < results/m5_$T.jsonl) rows"
done
