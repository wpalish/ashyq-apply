#!/usr/bin/env bash
# Give a git worktree the main checkout's backend/.venv and frontend/node_modules as symlinks.
# Both are untracked: never `git add -A` in a worktree that has them.
#   scripts/link_worktree_env.sh /path/to/worktree
set -euo pipefail
MAIN=$(git -C "$(dirname "$0")" worktree list --porcelain | awk 'NR==1{print $2}')
WT=${1:?usage: link_worktree_env.sh WORKTREE}
for p in backend/.venv frontend/node_modules; do
  [ -e "$WT/$p" ] || ln -s "$MAIN/$p" "$WT/$p"
done
echo "linked backend/.venv and frontend/node_modules into $WT"
