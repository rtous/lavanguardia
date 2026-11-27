#!/usr/bin/env bash
# Mirror the whole working tree (code, .git, data/, evidence/, logs/, results/) to Google Drive, so a Colab
# disconnect loses at most one sync interval of work. Jobs keep writing to the local disk (the Drive mount buffers
# writes and can drop appends); this copies them over. rsync writes each file to a temp name and renames it, so the
# Drive copy of every file is always a complete earlier or later version, never half-written. Nothing is deleted on
# either side.
#
#   src/colab_sync.sh push            # local -> Drive, once
#   src/colab_sync.sh loop [secs]     # push every N s (default 300); run in the background for the whole session
#   src/colab_sync.sh restore         # fresh runtime: git clone from GitHub first, then run this (see below)
#   src/colab_sync.sh pull            # Drive -> local, everything (only if GitHub is NOT newer; prefer restore)
#
# WARNING (2026-11-27): Drive uploads asynchronously. When a Colab VM dies, the last ~1-2 h of writes may never reach
# Drive, and Drive keeps an older, shorter copy of each file (and a broken .git). GitHub (pushed by autosave.sh) is
# then newer. So on a fresh runtime: git clone, then `restore`, which copies only the untracked folders (data/,
# evidence/, logs/) and never overwrites a local file with an older or shorter one. Then run
# `python -I src/evidence_audit.py` to see which result rows lack their raw evidence record.
set -u
SRC=/content/lavanguardia
DST=${COLAB_STATE:-/content/drive/MyDrive/lavanguardia_work/colab_state/lavanguardia}
OPTS=(-rlt --exclude __pycache__/ --exclude .ipynb_checkpoints/)

push() { mkdir -p "$DST" && rsync "${OPTS[@]}" "$SRC/" "$DST/" && date -u +%FT%TZ > "$DST/.last_sync_utc"; }

case "${1:-push}" in
  push) push ;;
  restore)
    for d in data evidence logs; do [ -d "$DST/$d" ] && rsync "${OPTS[@]}" --update "$DST/$d/" "$SRC/$d/"; done
    # report git-tracked files whose Drive copy is shorter than the checked-out one (= Drive is stale)
    (cd "$SRC" && git ls-files results | while read -r f; do
       [ -f "$DST/$f" ] && [ "$(stat -c %s "$DST/$f")" -lt "$(stat -c %s "$f")" ] && echo "stale on Drive: $f"; done)
    echo "restored data/ evidence/ logs/ from $DST (last sync $(cat "$DST/.last_sync_utc" 2>/dev/null))" ;;
  pull) rsync "${OPTS[@]}" "$DST/" "$SRC/" && echo "restored from $DST (last sync $(cat "$DST/.last_sync_utc" 2>/dev/null))" ;;
  loop) while true; do push || echo "$(date -u +%FT%TZ) sync failed" >&2; sleep "${2:-300}"; done ;;
  *) echo "usage: $0 push|restore|pull|loop [secs]" >&2; exit 1 ;;
esac
