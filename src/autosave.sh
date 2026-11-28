#!/usr/bin/env bash
# Periodic autosave for unattended Colab sessions: commit new experiment result rows, push to GitHub, mirror to Drive.
# The token is read from the environment (GH_TOKEN) and used only on the push command line: it is never written to
# .git/config (which the Drive mirror copies). Only results/ files of running experiments are committed; data/,
# evidence/ and .env stay out (gitignored).
#   GH_TOKEN=... nohup ./src/autosave.sh 600 >> logs/autosave.log 2>&1 &
#
# Raw evidence (2026-11-28): evidence/ is its own git repo, pushed to the PRIVATE repo rtous/lavanguardia-evidence
# (EVIDENCE_REMOTE), because Drive alone lost raw records twice (docs/evidence_gaps.md). Tokens: GH_TOKEN in the env,
# or the file /root/.gh_token (chmod 600; written from Colab Secrets, see docs/colab_handoff.md). Never committed.
set -u
cd "$(dirname "$0")/.."
INTERVAL=${1:-600}
EVIDENCE_REMOTE=${EVIDENCE_REMOTE:-github.com/rtous/lavanguardia-evidence.git}
push_evidence() {
  [ -d evidence ] && [ -n "${GH_TOKEN:-}" ] || return 0
  ( cd evidence
    [ -d .git ] || { git init -q -b main && git config user.name "$(git -C .. config user.name || echo autosave)" \
                     && git config user.email "$(git -C .. config user.email || echo autosave@localhost)"; }
    git add -A && { git diff --cached --quiet || git commit -qm "Evidence snapshot $(date -u +%FT%TZ)"; }
    git -c credential.helper= push -q "https://rtous:${GH_TOKEN}@${EVIDENCE_REMOTE}" main 2>&1 | sed 's/gh[a-z]_[A-Za-z0-9_]*/***/g'
    [ "${PIPESTATUS[0]}" -eq 0 ] && echo "$(date -u +%FT%TZ) evidence pushed ($(cat */calls.jsonl 2>/dev/null | wc -l) records)" )
}
while true; do
  [ -r /root/.gh_token ] && GH_TOKEN=$(tr -d ' \n' < /root/.gh_token)  # re-read each loop: the token can be added later
  for f in results/m11_nyt_style_*.jsonl results/m11_*summary*.json results/m12_url_reverse_*.jsonl results/m12_url_reverse_summary.json \
           results/rerun_custody/*.jsonl results/rerun_custody/*.json \
           results/rerun_custody2/*.jsonl results/rerun_custody2/*.json results/m13_most_copied_*.jsonl results/m13_*summary*.json; do
    [ -e "$f" ] && git add "$f"  # one by one: a pattern matching nothing would make git add skip all
  done
  if ! git diff --cached --quiet; then
    git commit -qm "Autosave: M11/M12/M13 results $(date -u +%FT%TZ)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && echo "$(date -u +%FT%TZ) committed"
  fi
  if [ -n "${GH_TOKEN:-}" ] && [ -n "$(git log origin/main..main --oneline 2>/dev/null)" ]; then
    git -c credential.helper= push -q "https://rtous:${GH_TOKEN}@github.com/rtous/lavanguardia.git" main 2>&1 | sed 's/ghp_[A-Za-z0-9_]*/***/g'
    [ "${PIPESTATUS[0]}" -eq 0 ] && git update-ref refs/remotes/origin/main main && echo "$(date -u +%FT%TZ) pushed"
  fi
  push_evidence
  ./src/colab_sync.sh push && echo "$(date -u +%FT%TZ) drive synced"
  sleep "$INTERVAL"
done
