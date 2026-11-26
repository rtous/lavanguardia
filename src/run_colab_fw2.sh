#!/usr/bin/env bash
# Colab: finish the FineWeb-2 Spanish scan, then recompute the overlap and the Apertus positive control.
# Sequential (one job). Outputs are copied to Google Drive every 5 min and at the end, because the Colab disk is
# wiped when the runtime is recycled. Resumable: rerun after a disconnect (copy the Drive files back first, see
# docs/colab_handoff.md). Log: logs/colab_fw2.log
set -u
cd "$(dirname "$0")/.."
D=${DRIVE_OUT:-/content/drive/MyDrive/lavanguardia_work/colab_results}
mkdir -p "$D/results" "$D/logs" logs
DONE=logs/colab_fw2.done; rm -f "$DONE"

sync_out() {
  cp -p results/dataset_presence*.json* results/positive_control_apertus.json "$D/results/" 2>/dev/null
  cp -p logs/colab_fw2.log "$D/logs/" 2>/dev/null
}
( while [ ! -f "$DONE" ]; do sync_out; sleep 300; done ) &

echo "=== $(date -u +%FT%TZ) FineWeb-2 spa_Latn scan (resume)"
python -I src/dataset_presence.py --config spa_Latn --shards 999 || echo "scan exited with error $?"
echo "=== $(date -u +%FT%TZ) overlap"
python -I src/presence_overlap.py
echo "=== $(date -u +%FT%TZ) positive control (Apertus)"
python -I src/positive_control_apertus.py
touch "$DONE"; sync_out
echo "=== $(date -u +%FT%TZ) COLAB_FW2 done"
