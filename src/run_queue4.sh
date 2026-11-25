#!/bin/sh
# Replication of the neighbour-DiD (pre-registered in docs/prereg/did_neighbour_replication.md). Sequential, resumable.
set -x
R=data/cc/mid2023_rep.jsonl
[ -f $R ] || cp data/cc/mid2023.jsonl $R   # so cc_fetch skips first-run articles (they are excluded again downstream)
SECS=politica,opinion,internacional,economia,cultura,vida,deportes,local
for C in CC-MAIN-2023-50 CC-MAIN-2024-10 CC-MAIN-2023-40; do
  .venv/bin/python -I src/cc_fetch.py --crawl $C --sections $SECS --months 2023-04:2023-11 --per-month 4 --out $R
done
P=data/decop/paraphrases_mid2023_rep.jsonl
.venv/bin/python -I src/local_paraphrase.py --rep --out $P
.venv/bin/python -I src/m5_neighbour.py --model mlx-community/Meta-Llama-3.1-8B-4bit --src $P:local --out results/m5_neighbour_mid2023rep_llama31_8b.jsonl
.venv/bin/python -I src/m5_neighbour.py --model mlx-community/Meta-Llama-3-8B-4bit --src $P:local --out results/m5_neighbour_mid2023rep_llama3_8b.jsonl
.venv/bin/python -I src/did_neighbour.py --l3 results/m5_neighbour_mid2023rep_llama3_8b.jsonl --l31 results/m5_neighbour_mid2023rep_llama31_8b.jsonl --out results/did_neighbour_rep.json
echo QUEUE4 done
