#!/bin/sh
# Bulk collection for the pilot.  usage: src/collect.sh members|controls
# Members: published 2020-01..2023-02 (in training of models with cutoff >= 2024).
# Controls: published 2025-09..2026-03 (after training-data cutoff of Claude 4.5 family: Jul/Aug 2025).
PY=".venv/bin/python -I src/cc_fetch.py"
SECS=politica,opinion,internacional,economia,cultura,vida,deportes,local
if [ "$1" = members ]; then
  for C in CC-MAIN-2023-14 CC-MAIN-2023-50 CC-MAIN-2022-33; do
    $PY --crawl $C --sections $SECS --months 2020-01:2023-02 --per-month 1 --out data/cc/members.jsonl
  done
else
  for C in CC-MAIN-2026-12 CC-MAIN-2026-08 CC-MAIN-2026-04 CC-MAIN-2025-51; do
    $PY --crawl $C --sections $SECS --months 2025-09:2026-03 --per-month 4 --out data/cc/controls.jsonl
  done
fi
