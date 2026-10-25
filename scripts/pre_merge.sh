#!/usr/bin/env bash
# The merge gate: exactly the CI gates (.github/workflows/ci.yml, jobs `backend` and `frontend`) of the
# areas a branch touches, in one command. Run it before every push (GATE-1).
#
#   scripts/pre_merge.sh [--base REF] [--scope auto|backend|frontend|all] [--pg] [--e2e auto|always|never] [--dry-run]
#
#   --base REF     what the branch is compared with (default origin/claude/greeting-16wj2z)
#   --scope        auto (default): from `git diff --name-only BASE...HEAD`
#                    backend/            -> ruff, ruff format, mypy (app tests evaluation), the suite, the golden demo
#                    frontend/           -> typecheck, lint, vitest, build, the three Playwright suites
#                    .github/workflows/, scripts/ -> YAML parse, bash -n, the workflow tests
#                    anything else only  -> the commit check alone
#                  all: every gate. A push that bundles several cherry-picks is `all` unless every commit is docs.
#   --pg           also CI's PostgreSQL job (off by default; CI runs it anyway)
#   --e2e          auto (default): the browser suites when frontend/ is in scope; always: also for a diff
#                  without frontend/; never: skip them (a worker whose ports are taken) - then the gate is red
#                  whenever frontend/ is in scope, because CI would run them
#   --dry-run      print every command, run none
#   --changed FILE (tests) read the changed paths from FILE instead of git diff
#
# Stops at the first red step (exit 1). The cleanup (screenshots, Playwright reports, the clean-tree check)
# runs on exit whenever the preconditions passed. Run from any worktree: the backend venv and frontend
# node_modules are the ones scripts/link_worktree_env.sh linked in.
set -uo pipefail

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || exit 2
BASE=origin/claude/greeting-16wj2z
SCOPE=auto
PG=0
E2E=auto
DRY=0
CHANGED_FILE=

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }
while [ $# -gt 0 ]; do
  case $1 in
    --base) BASE=${2:?--base needs a ref}; shift 2 ;;
    --scope) SCOPE=${2:?--scope needs a value}; shift 2 ;;
    --pg) PG=1; shift ;;
    --e2e) E2E=${2:?--e2e needs a value}; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --changed) CHANGED_FILE=${2:?--changed needs a file}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "pre_merge: unknown argument $1" >&2; usage >&2; exit 2 ;;
  esac
done
case $SCOPE in auto|backend|frontend|all) ;; *) echo "pre_merge: --scope auto|backend|frontend|all" >&2; exit 2 ;; esac
case $E2E in auto|always|never) ;; *) echo "pre_merge: --e2e auto|always|never" >&2; exit 2 ;; esac

RUN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/pre-merge-XXXXXX")
STEP_NAMES=()
STEP_CODES=()
STEP_SECS=()
NOTES=()
ARMED=0      # the cleanup touches the tree only once the clean-tree precondition has passed
RESULT=0

record() { STEP_NAMES+=("$1"); STEP_CODES+=("$2"); STEP_SECS+=("$3"); }

# run NAME DIR CMD... : one gate step; its output is shown and kept in $RUN_TMP/step-N.log.
run() {
  local name=$1 dir=$2
  shift 2
  local rel=${dir#"$ROOT"}
  rel=${rel#/}
  echo "+ (${rel:-.}) $*"
  if [ "$DRY" = 1 ]; then
    record "$name" dry 0
    return 0
  fi
  local log="$RUN_TMP/step-${#STEP_NAMES[@]}.log" start=$SECONDS code
  (cd "$dir" && "$@") 2>&1 | tee "$log"
  code=${PIPESTATUS[0]}
  LAST_LOG=$log
  record "$name" "$code" $((SECONDS - start))
  if [ "$code" -ne 0 ]; then
    echo "pre_merge: step '$name' is red (exit $code)" >&2
    RESULT=1
    exit 1
  fi
}

# check NAME FUNCTION : a step whose body is a shell function of this script.
check() {
  local name=$1 fn=$2
  echo "+ check: $name"
  if [ "$DRY" = 1 ]; then
    record "$name" dry 0
    return 0
  fi
  local start=$SECONDS code
  "$fn"
  code=$?
  record "$name" "$code" $((SECONDS - start))
  if [ "$code" -ne 0 ]; then
    echo "pre_merge: check '$name' is red" >&2
    RESULT=1
    exit 1
  fi
}

# What `git status --porcelain` shows minus the two symlinks link_worktree_env.sh makes in a worktree.
dirty() {
  git -C "$ROOT" status --porcelain | while IFS= read -r line; do
    path=${line:3}
    if [ "${line:0:2}" = "??" ] && { [ "$path" = backend/.venv ] || [ "$path" = frontend/node_modules ]; } \
      && [ -L "$ROOT/$path" ]; then
      continue
    fi
    printf '%s\n' "$line"
  done
}

tree_clean() {
  local d
  d=$(dirty)
  [ -z "$d" ] && return 0
  echo "pre_merge: the tree is not clean:" >&2
  printf '%s\n' "$d" >&2
  return 1
}

ports_free() {
  local port busy=0 who
  for port in 5173 8099; do
    if command -v ss >/dev/null 2>&1; then
      who=$(ss -ltnpH "sport = :$port" 2>/dev/null)
    elif command -v lsof >/dev/null 2>&1; then
      who=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null)
    else
      echo "pre_merge: neither ss nor lsof is installed; cannot check port $port" >&2
      return 1
    fi
    if [ -n "$who" ]; then
      echo "pre_merge: port $port is busy (the Playwright configs refuse to adopt a server):" >&2
      printf '%s\n' "$who" >&2
      busy=1
    fi
  done
  return $busy
}

demo_order() {
  "$ROOT/backend/.venv/bin/python" - "$LAST_LOG" "$DEMO_DB" <<'PY'
import sqlite3
import sys

lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
rule = next(i for i, line in enumerate(lines) if line.startswith("-" * 40))
first = lines[rule + 1]
ubc = sqlite3.connect(sys.argv[2]).execute(
    "select bucket from program_results where university = 'University of British Columbia'"
).fetchall()
print(f"first row: {first.split('  ')[0]}; UBC bucket: {ubc}")
ok = first.startswith("University of Groningen") and ubc == [("OUT_OF_BUDGET",)]
if not ok:
    print("brief 5.7 order broken: want Groningen first and UBC in OUT_OF_BUDGET", file=sys.stderr)
sys.exit(0 if ok else 1)
PY
}

commits_ok() {
  local sha bad=0 n=0
  for sha in $(git -C "$ROOT" rev-list "$BASE..HEAD"); do
    n=$((n + 1))
    if ! git -C "$ROOT" log -1 --format=%B "$sha" | grep -q '^Agent: '; then
      echo "pre_merge: $(git -C "$ROOT" log -1 --format='%h %s' "$sha") has no Agent: trailer" >&2
      bad=1
    fi
    if git -C "$ROOT" log -1 --format=%s "$sha" | grep -q '^wip:'; then
      echo "pre_merge: $(git -C "$ROOT" log -1 --format='%h %s' "$sha") is a wip: commit" >&2
      bad=1
    fi
  done
  echo "commits in $BASE..HEAD: $n"
  return $bad
}

summary() {
  local i
  echo
  echo "pre_merge summary (base $BASE, scope $SCOPE, e2e $E2E$([ "$DRY" = 1 ] && echo ', dry run'))"
  printf '| %-46s | %-4s | %7s |\n' step exit seconds
  printf '|%s|%s|%s|\n' "------------------------------------------------" "------" "---------"
  for i in "${!STEP_NAMES[@]}"; do
    printf '| %-46s | %-4s | %7s |\n' "${STEP_NAMES[$i]}" "${STEP_CODES[$i]}" "${STEP_SECS[$i]}"
  done
  for i in "${!NOTES[@]}"; do echo "note: ${NOTES[$i]}"; done
  if [ "$RESULT" -eq 0 ]; then echo "pre_merge: GREEN"; else echo "pre_merge: RED"; fi
}

finish() {
  local code=$?
  [ "$code" -ne 0 ] && RESULT=1
  if [ "$ARMED" = 1 ] && [ "$DRY" = 0 ]; then
    # 6. Cleanup: what a Playwright run leaves behind, then the tree must be as clean as it started.
    git -C "$ROOT" checkout -- docs/screenshots 2>/dev/null
    rm -rf "$ROOT"/frontend/playwright-report* "$ROOT"/frontend/test-results*
    local start=$SECONDS
    if tree_clean; then record "cleanup: tree clean again" 0 $((SECONDS - start))
    else record "cleanup: tree clean again" 1 $((SECONDS - start)); RESULT=1; fi
  fi
  pkill -f -- "-D $RUN_TMP/" 2>/dev/null
  rm -rf -- "$RUN_TMP"
  summary
  trap - EXIT
  exit "$RESULT"
}
trap finish EXIT
trap 'exit 130' INT TERM

# 2. Scope.
if [ -n "$CHANGED_FILE" ]; then
  CHANGED=$(cat "$CHANGED_FILE")
elif [ "$SCOPE" = auto ]; then
  if ! CHANGED=$(git -C "$ROOT" diff --name-only "$BASE...HEAD"); then
    echo "pre_merge: cannot diff against $BASE (fetch it, or pass --base)" >&2
    exit 1
  fi
else
  CHANGED=
fi
DO_BACKEND=0
DO_FRONTEND=0
DO_CI=0
CI_FILES=()
OTHER=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  case $path in
    backend/*) DO_BACKEND=1 ;;
    frontend/*) DO_FRONTEND=1 ;;
    .github/workflows/*|scripts/*) DO_CI=1; CI_FILES+=("$path") ;;
    *) OTHER=1 ;;
  esac
done <<<"$CHANGED"
case $SCOPE in
  backend) DO_BACKEND=1 ;;
  frontend) DO_FRONTEND=1 ;;
  all)
    DO_BACKEND=1; DO_FRONTEND=1; DO_CI=1
    CI_FILES=()
    while IFS= read -r path; do CI_FILES+=("$path"); done < <(
      cd "$ROOT" && ls .github/workflows/*.yml .github/workflows/*.yaml scripts/*.sh 2>/dev/null)
    ;;
esac
DO_E2E=0
if [ "$E2E" = always ] || { [ "$E2E" = auto ] && [ "$DO_FRONTEND" = 1 ]; }; then DO_E2E=1; fi
if [ "$DO_BACKEND$DO_FRONTEND$DO_CI$DO_E2E" = 0000 ]; then
  if [ "$OTHER" = 1 ]; then NOTES+=("docs only (no backend/, frontend/, workflow or script path): the commit check alone")
  else NOTES+=("no path changed against $BASE: the commit check alone"); fi
fi
echo "pre_merge: scope backend=$DO_BACKEND frontend=$DO_FRONTEND workflows/scripts=$DO_CI e2e=$DO_E2E"

# 1. Preconditions (none for a docs-only diff: nothing runs that could dirty the tree).
if [ "$DO_BACKEND$DO_FRONTEND$DO_CI$DO_E2E" != 0000 ]; then
  check "precondition: tree clean" tree_clean
  [ "$DRY" = 0 ] && ARMED=1
  [ "$DO_E2E" = 1 ] && check "precondition: ports 5173/8099 free" ports_free
  run "clean_test_tmp" "$ROOT" scripts/clean_test_tmp.sh
fi

B="$ROOT/backend"
F="$ROOT/frontend"

# Workflows and scripts: parse what changed, run the workflow tests (the full suite covers them otherwise).
if [ "$DO_CI" = 1 ]; then
  for path in "${CI_FILES[@]}"; do
    [ -f "$ROOT/$path" ] || continue
    case $path in
      *.yml|*.yaml) run "yaml: $path" "$ROOT" backend/.venv/bin/python -c \
        "import sys, yaml; yaml.safe_load(open(sys.argv[1]))" "$path" ;;
      *.sh) run "bash -n: $path" "$ROOT" bash -n "$path" ;;
    esac
  done
  if [ "$DO_BACKEND" = 0 ]; then
    run "workflow tests" "$ROOT" scripts/run_suite.sh tests/test_workflow_runners.py \
      tests/test_expert_workflow.py tests/test_pre_merge_script.py
  fi
fi

# 3. Backend: ci.yml job `backend` (sqlite leg), then optionally its postgresql leg.
if [ "$DO_BACKEND" = 1 ]; then
  run "ruff check" "$B" .venv/bin/ruff check app tests evaluation
  run "ruff format --check" "$B" .venv/bin/ruff format --check app tests evaluation
  run "mypy" "$B" .venv/bin/mypy app tests evaluation
  # run_suite.sh clears addopts, so the coverage bar is passed explicitly.
  run "backend suite (sqlite, coverage)" "$ROOT" env "UNIMATCH_DATABASE_URL=sqlite:///$RUN_TMP/unimatch-ci.db" \
    scripts/run_suite.sh --cov=app --cov-fail-under=92 -n 4 tests
  if [ "$PG" = 1 ]; then
    run "backend suite (postgresql)" "$B" .venv/bin/python scripts/pg.py .venv/bin/pytest -q -n 4 tests
  fi

  # 4. The golden demo on a throwaway database: brief 5.7, Groningen first and UBC in OUT_OF_BUDGET.
  DEMO_DB="$RUN_TMP/demo.db"
  run "demo: alembic upgrade head" "$B" env "UNIMATCH_DATABASE_URL=sqlite:///$DEMO_DB" UNIMATCH_DEMO_MODE=true \
    .venv/bin/alembic upgrade head
  run "demo: seed_demo.py" "$B" env "UNIMATCH_DATABASE_URL=sqlite:///$DEMO_DB" UNIMATCH_DEMO_MODE=true \
    UNIMATCH_ENABLE_BROWSER_TIER=false .venv/bin/python seed_demo.py
  check "demo: brief 5.7 order" demo_order
fi

# 5. Frontend: ci.yml job `frontend`, the browser suites in CI's order, one at a time.
if [ "$DO_FRONTEND" = 1 ]; then
  run "typecheck" "$F" npm run typecheck
  run "lint" "$F" npm run lint
  run "vitest" "$F" npm test -- --run
  run "build (bundle budget)" "$F" npm run build
fi
if [ "$DO_E2E" = 1 ]; then
  check "ports free before e2e" ports_free
  run "e2e (demo)" "$F" npm run e2e
  check "ports free before e2e:auth" ports_free
  run "e2e:auth" "$F" npm run e2e:auth
  check "ports free before e2e:kb" ports_free
  run "e2e:kb" "$F" npm run e2e:kb
elif [ "$DO_FRONTEND" = 1 ] && [ "$E2E" = never ]; then
  echo "pre_merge: the three Playwright suites were SKIPPED (--e2e never); CI runs them, so this gate is red."
  NOTES+=("Playwright suites skipped by --e2e never: red, because frontend/ is in scope")
  record "e2e suites" skipped 0
  RESULT=1
fi

# 7. Commits: every commit since the base carries an Agent: trailer and none is a wip: commit.
echo "+ git log --format=%B $BASE..HEAD"
check "commits: Agent: trailer, no wip:" commits_ok

exit "$RESULT"
