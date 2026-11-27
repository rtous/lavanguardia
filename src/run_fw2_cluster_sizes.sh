#!/usr/bin/env bash
# Copy counts of every LV page in FineWeb-2 (Catalan, then Spanish), then the top list. Sequential, resumable.
set -u
cd "$(dirname "$0")/.."
export FW2_TMP=${FW2_TMP:-/content/fw2_tmp}  # outside the repo: colab_sync.sh must not mirror multi-GB shards
for L in cat_Latn spa_Latn; do python -I src/fw2_cluster_sizes.py scan --lang $L --workers 3; done
python -I src/fw2_cluster_sizes.py top --n 20
echo "=== $(date -u +%FT%TZ) fw2 cluster sizes done"
