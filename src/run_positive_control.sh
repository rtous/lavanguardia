#!/bin/bash
# Positive control on Apertus-8B base (published training data), strictly sequential. Resumable.
cd "$(dirname "$0")/.." || exit 1
M=mlx-community/Apertus-8B-2509-4bit
.venv/bin/python -I src/m5_logprob.py --model $M --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_apertus8b.jsonl
.venv/bin/python -I src/m5_logprob.py --model $M --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_apertus8b.jsonl
.venv/bin/python -I src/m10_exclusive_facts.py run --model $M --types qa --n 300 2>&1 | grep -v -e Warning -e Fetching
.venv/bin/python -I src/positive_control_apertus.py > /dev/null
echo "POSITIVE CONTROL done"
