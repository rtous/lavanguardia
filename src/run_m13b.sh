#!/usr/bin/env bash
# M13b (docs/prereg/m13b_garnier_dense.md). Keys from .env.  nohup ./src/run_m13b.sh claude|gemini >> logs/m13b_<m>.log 2>&1 &
set -u; cd "$(dirname "$0")/.."; [ -r .env ] && { set -a; . ./.env; set +a; }
case "${1:-}" in claude) M=claude-opus-4-5-20251101 ;; gemini) M=gemini-3.1-flash-lite ;; *) echo "usage: $0 claude|gemini"; exit 1 ;; esac
echo "=== $(date -u +%FT%TZ) M13b $M"; python -I src/m13b_garnier.py run --model "$M"; python -I src/m13b_garnier.py summary > /dev/null
N=$(wc -l < "results/m13b_garnier_${M}.jsonl"); [ "$N" -ge 76 ] && echo "=== $(date -u +%FT%TZ) M13b $M done" || echo "=== $(date -u +%FT%TZ) M13b $M stopped, incomplete ($N/76)"
