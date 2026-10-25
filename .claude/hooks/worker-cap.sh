#!/bin/bash
# PreToolUse(Agent): at most 4 worktree workers at once (LOOP_PROTOCOL). Merged worktrees are
# removed, so the live worktree count is the live worker count. Exit 2 blocks the launch.
set -uo pipefail
input=$(cat)
isolation=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("isolation",""))' 2>/dev/null)
[ "$isolation" = "worktree" ] || exit 0
live=$(ls -d "$CLAUDE_PROJECT_DIR"/.claude/worktrees/agent-* 2>/dev/null | wc -l)
if [ "$live" -ge 4 ]; then
  echo "Worker cap: $live worktree workers are live (max 4). Merge or remove a finished worktree first (git worktree remove), or resume an existing worker with SendMessage." >&2
  exit 2
fi
exit 0
