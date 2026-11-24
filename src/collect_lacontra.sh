#!/bin/sh
# High-duplication candidate sample: La Contra interviews (widely reposted).
PY=".venv/bin/python -I src/cc_fetch.py"
for C in CC-MAIN-2023-14 CC-MAIN-2023-50 CC-MAIN-2022-33; do
  $PY --crawl $C --sections lacontra --months 2011-01:2023-02 --per-month 1 --out data/cc/lacontra_members.jsonl
done
for C in CC-MAIN-2026-12 CC-MAIN-2026-08 CC-MAIN-2026-04 CC-MAIN-2025-51; do
  $PY --crawl $C --sections lacontra --months 2025-09:2026-03 --per-month 8 --out data/cc/lacontra_controls.jsonl
done
