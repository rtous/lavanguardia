#!/bin/bash
# Collect other outlets' (date, ID) pairs + test titles from Common Crawl, one outlet after another. Resumable.
cd "$(dirname "$0")/.." || exit 1
for O in elperiodico elconfidencial elespanol; do
  .venv/bin/python -I src/m10_outlet_ids.py --outlet "$O" --per-month 2 2>&1 | grep -v -e "retry"
done
echo "OUTLETS done"
