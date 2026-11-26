#!/usr/bin/env bash
# Mirror the whole working tree (code, .git, data/, evidence/, logs/, results/) to Google Drive, so a Colab
# disconnect loses at most one sync interval of work. Jobs keep writing to the local disk (the Drive mount buffers
# writes and can drop appends); this copies them over. rsync writes each file to a temp name and renames it, so the
# Drive copy of every file is always a complete earlier or later version, never half-written. Nothing is deleted on
# either side.
#
#   src/colab_sync.sh push            # local -> Drive, once
#   src/colab_sync.sh loop [secs]     # push every N s (default 300); run in the background for the whole session
#   src/colab_sync.sh pull            # Drive -> local (fresh runtime: mount Drive, then run the one-liner below)
#
# Fresh runtime, before the repo exists locally:
#   rsync -rlt /content/drive/MyDrive/lavanguardia_work/colab_state/lavanguardia/ /content/lavanguardia/
set -u
SRC=/content/lavanguardia
DST=${COLAB_STATE:-/content/drive/MyDrive/lavanguardia_work/colab_state/lavanguardia}
OPTS=(-rlt --exclude __pycache__/ --exclude .ipynb_checkpoints/)

push() { mkdir -p "$DST" && rsync "${OPTS[@]}" "$SRC/" "$DST/" && date -u +%FT%TZ > "$DST/.last_sync_utc"; }

case "${1:-push}" in
  push) push ;;
  pull) rsync "${OPTS[@]}" "$DST/" "$SRC/" && echo "restored from $DST (last sync $(cat "$DST/.last_sync_utc" 2>/dev/null))" ;;
  loop) while true; do push || echo "$(date -u +%FT%TZ) sync failed" >&2; sleep "${2:-300}"; done ;;
  *) echo "usage: $0 push|pull|loop [secs]" >&2; exit 1 ;;
esac
