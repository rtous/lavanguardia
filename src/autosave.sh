#!/usr/bin/env bash
# Periodic autosave for unattended Colab sessions: commit new experiment result rows, push to GitHub, mirror to Drive.
# The token is read from the environment (GH_TOKEN) and used only on the push command line: it is never written to
# .git/config (which the Drive mirror copies). Only results/ files of running experiments are committed; data/,
# evidence/ and .env stay out (gitignored).
#   GH_TOKEN=... nohup ./src/autosave.sh 600 >> logs/autosave.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
INTERVAL=${1:-600}
while true; do
  for f in results/m11_nyt_style_*.jsonl results/m11_*summary*.json results/m12_url_reverse_*.jsonl results/m12_url_reverse_summary.json \
           results/rerun_custody/*.jsonl results/rerun_custody/*.json; do
    [ -e "$f" ] && git add "$f"  # one by one: a pattern matching nothing would make git add skip all
  done
  if ! git diff --cached --quiet; then
    git commit -qm "Autosave: M11/M12 results $(date -u +%FT%TZ)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && echo "$(date -u +%FT%TZ) committed"
  fi
  if [ -n "${GH_TOKEN:-}" ] && [ -n "$(git log origin/main..main --oneline 2>/dev/null)" ]; then
    git -c credential.helper= push -q "https://rtous:${GH_TOKEN}@github.com/rtous/lavanguardia.git" main 2>&1 | sed 's/ghp_[A-Za-z0-9_]*/***/g'
    [ "${PIPESTATUS[0]}" -eq 0 ] && git update-ref refs/remotes/origin/main main && echo "$(date -u +%FT%TZ) pushed"
  fi
  ./src/colab_sync.sh push && echo "$(date -u +%FT%TZ) drive synced"
  sleep "$INTERVAL"
done
