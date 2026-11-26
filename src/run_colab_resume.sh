#!/usr/bin/env bash
# Resume everything still pending after a Colab disconnect, in order, one GPU job at a time. Safe to rerun at any
# point: every step skips work already saved (rewrites by article, scores by article, m10 items by item id).
#   1. Drive mirror (src/colab_sync.sh loop) - started first so new work is saved every 5 min
#   2. Llama 3 vs 3.1 neighbour replication (src/run_colab_queue4.sh; prereg deviations already committed)
#   3. Salamandra-7B Q->A + URL number (src/run_colab_salamandra.sh; probabilities already done, they are skipped)
# Needs HF_TOKEN in the environment (Llama licence granted to account rtous). See docs/colab_handoff.md.
set -u
cd "$(dirname "$0")/.."
[ -n "${HF_TOKEN:-}" ] || { echo "HF_TOKEN not set (Colab: os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN'))"; exit 1; }
mkdir -p logs
nohup ./src/colab_sync.sh loop 300 >> logs/colab_sync.log 2>&1 &
echo "=== $(date -u +%FT%TZ) resume: Llama replication" | tee -a logs/colab_queue4.log
./src/run_colab_queue4.sh >> logs/colab_queue4.log 2>&1 || echo "queue4 stopped with error, see logs/colab_queue4.log"
echo "=== $(date -u +%FT%TZ) resume: Salamandra" | tee -a logs/colab_salamandra.log
./src/run_colab_salamandra.sh >> logs/colab_salamandra.log 2>&1
./src/colab_sync.sh push
echo "=== $(date -u +%FT%TZ) RESUME done"
