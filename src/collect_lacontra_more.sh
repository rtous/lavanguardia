#!/bin/sh
# More La Contra controls (2025-09..2026-03) for M10 Q->A items. Separate file, so earlier experiments' inputs stay unchanged
# (duplicates of data/cc/lacontra_controls.jsonl are removed by URL when M10 loads the articles).
PY=".venv/bin/python -I src/cc_fetch.py"
for C in CC-MAIN-2026-12 CC-MAIN-2026-08 CC-MAIN-2026-04 CC-MAIN-2025-51; do
  $PY --crawl $C --sections lacontra --months 2025-09:2026-03 --per-month 30 --out data/cc/lacontra_controls_more.jsonl
done
echo "LACONTRA MORE done"
