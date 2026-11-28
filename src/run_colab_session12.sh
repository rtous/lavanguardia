#!/usr/bin/env bash
# Session 12 GPU queue (2026-11-28), one sequential script (no pgrep waits; CLAUDE.md). Runs alongside the custody
# Strictly sequential: two models do NOT fit on the T4 (Salamandra int4 alone takes 8.5 GB; OOM on 2026-11-28).
#   FETCH_PID=<pid of src/fw2_top_check.py> nohup ./src/run_colab_session12.sh >> logs/colab_session12.log 2>&1 &
# 1. wait for the FineWeb-2 re-fetch; check that it reproduced the committed top-20 list; put the text hash in the
#    M13 prereg and commit it BEFORE any M13 query;
# 2. M13 Salamandra; (custody re-run 2 dropped, see below); 4. M11 run 1 Qwen (continue); 5. M13 Qwen;
# 6. Llama-3.1 (M11 + M13) only if an HF token is present; 7. summaries.
set -u
cd "$(dirname "$0")/.."
export HF_PRECISION=${HF_PRECISION:-int4}
ts() { date -u +%FT%TZ; }
quiet() { grep --line-buffered -v -i -e warning -e "Loading weights" -e Fetching; }

if [ -n "${FETCH_PID:-}" ]; then while kill -0 "$FETCH_PID" 2>/dev/null; do sleep 30; done; fi
if ! git diff --quiet -- results/fw2_most_copied_checked.json results/fw2_most_copied.md; then
  echo "$(ts) STOP: re-fetch did not reproduce the committed most-copied list"; git diff --stat; exit 1; fi
[ -s data/fw2_top_text.json ] || { echo "$(ts) STOP: no data/fw2_top_text.json"; exit 1; }
H=$(sha256sum data/fw2_top_text.json | cut -d' ' -f1)
sed -i "s/TEXT_SHA256_PLACEHOLDER/$H/" docs/prereg/m13_most_copied.md
sed -i "s/^TEXT_SHA256 = None.*/TEXT_SHA256 = \"$H\"  # pre-registered (docs\/prereg\/m13_most_copied.md)/" src/m13_most_copied.py
git add docs/prereg/m13_most_copied.md src/m13_most_copied.py src/run_colab_session12.sh src/autosave.sh
git diff --cached --quiet || git commit -qm "Pre-register M13 (NYT-style extraction of the 20 most-copied LV articles), text sha256 $H

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && echo "$(ts) M13 prereg committed $(git rev-parse --short HEAD)"

echo "=== $(ts) M13 salamandra"
python -I src/m13_most_copied.py run --model hf:BSC-LT/salamandra-7b-instruct 2>&1 | quiet

# Custody re-run 2 (amendment 2) STOPPED 2026-11-28 10:30 UTC at the user's decision (Salamandra at 10/200, Qwen not
# started): results are unchanged by a re-run, so the rows without raw records are reported with the gap note instead.
echo "=== $(ts) M11 run 1 Qwen (continue)"
python -I src/m11_nyt_style.py run --model hf:Qwen/Qwen2.5-7B-Instruct 2>&1 | quiet
echo "=== $(ts) M13 Qwen"
python -I src/m13_most_copied.py run --model hf:Qwen/Qwen2.5-7B-Instruct 2>&1 | quiet

if [ -s /root/.cache/huggingface/token ] || [ -n "${HF_TOKEN:-}" ]; then
  echo "=== $(ts) M11 run 1 Llama"; python -I src/m11_nyt_style.py run --model hf:meta-llama/Llama-3.1-8B-Instruct 2>&1 | quiet
  echo "=== $(ts) M13 Llama"; python -I src/m13_most_copied.py run --model hf:meta-llama/Llama-3.1-8B-Instruct 2>&1 | quiet
else echo "$(ts) no HF token: Llama skipped"; fi

python -I src/m11_nyt_style.py summary > /dev/null; python -I src/m13_most_copied.py summary > /dev/null
echo "=== $(ts) session 12 queue done"
