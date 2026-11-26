#!/bin/bash
# M10 URL-ID test (url_id items only) on Gemini-API models, one after another. Resumable: rerun to retry quota errors.
# Models without free-tier access fail fast ("limit: 0") and are simply reported with 0 valid rows.
cd "$(dirname "$0")/.." || exit 1
N=${N:-60}
MODELS=${MODELS:-"gemini-2.5-flash-lite gemini-2.5-flash gemini-3-flash-preview gemini-3.5-flash-lite gemini-3.5-flash \
gemini-3.6-flash gemini-3.7-flash gemini-3.8-flash gemma-4-26b-a4b-it gemma-4-31b-it gemini-2.5-pro gemini-3.1-pro-preview \
gemini-3.1-flash-lite"}
for M in $MODELS; do
  .venv/bin/python -I src/m10_exclusive_facts.py run --model "$M" --types url_id --n "$N" --workers 2 2>&1 | grep -v -e Warning
  f="results/m10_exclusive_$M.jsonl"
  [ -f "$f" ] && echo "  $M: $(grep -c '"api_error": false' "$f") ok, $(grep -c '"api_error": true' "$f") errors"
done
.venv/bin/python -I src/m10_exclusive_facts.py summary > /dev/null
echo "M10 API done"
