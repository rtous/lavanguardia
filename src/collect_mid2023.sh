#!/bin/sh
# Articles published Apr-Nov 2023: after Llama 3's cutoff (Mar 2023), before Llama 3.1's (Dec 2023).
PY=".venv/bin/python -I src/cc_fetch.py"
SECS=politica,opinion,internacional,economia,cultura,vida,deportes,local
for C in CC-MAIN-2023-50 CC-MAIN-2024-10 CC-MAIN-2023-40; do
  $PY --crawl $C --sections $SECS --months 2023-04:2023-11 --per-month 2 --out data/cc/mid2023.jsonl
done
