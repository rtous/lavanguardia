#!/bin/sh
# Larger drift reference: XGLM-2.9B (Meta, multilingual, CC100-XL = Common Crawl 2013-2020). Waits for MLX runs.
while pgrep -f run_m5_models.sh >/dev/null; do sleep 30; done
.venv/bin/python -I src/m5_hf.py --model facebook/xglm-2.9B --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_xglm29.jsonl
.venv/bin/python -I src/m5_hf.py --model facebook/xglm-2.9B --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_xglm29.jsonl
echo XGLM done
