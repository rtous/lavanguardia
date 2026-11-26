#!/usr/bin/env bash
# BSC Salamandra-7B base (Apache 2.0; Spanish/Catalan; 20 Common Crawl snapshots + CATalog in pretraining) on Colab.
# Same tests and arguments as the Apertus positive control (src/run_positive_control.sh) plus the URL-number item.
# Strictly sequential, one GPU job, resumable. int8 because bf16 (15.5 GB) does not fit a 15 GB T4; the precision and
# weights commit are written to every row / evidence record (override with HF_PRECISION=bf16 on an A100).
# Log: logs/colab_salamandra.log. Drive mirror: run src/colab_sync.sh loop alongside.
set -u
cd "$(dirname "$0")/.."
export HF_PRECISION=${HF_PRECISION:-int8}
M=BSC-LT/salamandra-7b
echo "=== $(date -u +%FT%TZ) m5 random members/controls ($HF_PRECISION)"
python -I src/m5_hf.py --model $M --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_salamandra7b.jsonl
echo "=== $(date -u +%FT%TZ) m5 La Contra"
python -I src/m5_hf.py --model $M --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_salamandra7b.jsonl
echo "=== $(date -u +%FT%TZ) m10 Q->A + URL number"
python -I src/m10_exclusive_facts.py run --model hf:$M --types qa url_id --n 300 --workers 1 2>&1 | grep -v -e Warning -e Fetching
echo "=== $(date -u +%FT%TZ) SALAMANDRA done"
