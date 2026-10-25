#!/usr/bin/env bash
# The merge gate: exactly the CI gates (.github/workflows/ci.yml, jobs `backend` and `frontend`) of the
# areas a branch touches, in one command, plus the container jobs (`security-and-containers`,
# `compose-stack`): for real when a Docker daemon answers, approximated without one. Run it before every
# push (GATE-1, GATE-2).
#
#   scripts/pre_merge.sh [--base REF] [--scope auto|backend|frontend|all] [--pg] [--e2e auto|always|never]
#                        [--docker auto|always|never] [--dry-run]
#
#   --base REF     what the branch is compared with (default origin/claude/greeting-16wj2z)
#   --scope        auto (default): from `git diff --name-only BASE...HEAD`
#                    backend/            -> ruff, ruff format, mypy (app tests evaluation), the suite, the golden demo
#                    frontend/           -> typecheck, lint, vitest, build, the three Playwright suites
#                    .github/workflows/, scripts/ -> YAML parse, bash -n, the workflow tests
#                    backend/ or frontend/ (that image), a Dockerfile, a .dockerignore, docker-compose*.yml,
#                    ci.yml, verify_compose.sh, image_context.py (both images) -> the container gates
#                    anything else only  -> the commit check alone
#                  all: every gate. A push that bundles several cherry-picks is `all` unless every commit is docs.
#   --pg           also CI's PostgreSQL job (off by default; CI runs it anyway)
#   --e2e          auto (default): the browser suites when frontend/ is in scope; always: also for a diff
#                  without frontend/; never: skip them (a worker whose ports are taken) - then the gate is red
#                  whenever frontend/ is in scope, because CI would run them
#   --docker       auto (default): `docker compose build` and scripts/verify_compose.sh when `docker info`
#                  reaches a daemon; without one each image's build context is staged by
#                  scripts/image_context.py (git-tracked files minus .dockerignore; every COPY source must be
#                  in it) and the image's build runs there: web `npm run build`; api/worker/migrate import
#                  app.main and app.jobs.worker, load the KB, `alembic upgrade head` on sqlite.
#                  always: insist on the daemon (red without one); never: always the approximation
#   --dry-run      print every command, run none
#   --changed FILE (tests) read the changed paths from FILE instead of git diff
#
# Stops at the first red step (exit 1). The last line on stdout is always `pre_merge: GREEN` or
# `pre_merge: RED`, and the exit status is 0 exactly when it says GREEN. The cleanup (screenshots,
# Playwright reports, the compose stack, the clean-tree check) runs on exit whenever the preconditions
# passed. Run from any worktree: the backend venv and frontend node_modules are the ones
# scripts/link_worktree_env.sh linked in.
set -uo pipefail

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || { echo "pre_merge: RED"; exit 2; }
BASE=origin/claude/greeting-16wj2z
SCOPE=auto
PG=0
E2E=auto
DOCKER=auto
DRY=0
CHANGED_FILE=
CI_PASSWORD=ci-only-not-a-secret
CI_COMPOSE="docker compose -f docker-compose.yml -f docker-compose.ci.yml"

usage() { sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'; }
# A usage error is red as well: the verdict is the last line on every exit path.
usage_error() { echo "pre_merge: $1" >&2; usage >&2; echo "pre_merge: RED"; exit 2; }
value() { [ $# -ge 2 ] && [ -n "$2" ] || usage_error "$1 needs a value"; }
while [ $# -gt 0 ]; do
  case $1 in
    --base) value "$@"; BASE=$2; shift 2 ;;
    --scope) value "$@"; SCOPE=$2; shift 2 ;;
    --pg) PG=1; shift ;;
    --e2e) value "$@"; E2E=$2; shift 2 ;;
    --docker) value "$@"; DOCKER=$2; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --changed) value "$@"; CHANGED_FILE=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage_error "unknown argument $1" ;;
  esac
done
case $SCOPE in auto|backend|frontend|all) ;; *) usage_error "--scope auto|backend|frontend|all" ;; esac
case $E2E in auto|always|never) ;; *) usage_error "--e2e auto|always|never" ;; esac
case $DOCKER in auto|always|never) ;; *) usage_error "--docker auto|always|never" ;; esac

RUN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/pre-merge-XXXXXX")
STEP_NAMES=()
STEP_CODES=()
STEP_SECS=()
NOTES=()
ARMED=0      # the cleanup touches the tree only once the clean-tree precondition has passed
COMPOSE_UP=0 # verify_compose.sh started the stack: the cleanup takes it down, as CI's always() step does
RESULT=0

record() { STEP_NAMES+=("$1"); STEP_CODES+=("$2"); STEP_SECS+=("$3"); }

# run NAME DIR CMD... : one gate step; its output is shown and kept in $RUN_TMP/step-N.log.
run() {
  local name=$1 dir=$2
  shift 2
  local rel=$dir
  case $dir in "$ROOT" | "$ROOT"/*) rel=${dir#"$ROOT"}; rel=${rel#/} ;; esac
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

# check NAME FUNCTION [ARG...] : a step whose body is a shell function of this script.
check() {
  local name=$1 fn=$2
  shift 2
  echo "+ check: $name"
  if [ "$DRY" = 1 ]; then
    record "$name" dry 0
    return 0
  fi
  local start=$SECONDS code
  "$fn" "$@"
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

# ports_free [PORT...] : default the Playwright pair 5173/8099; the compose stack wants 8080/8099.
ports_free() {
  local port busy=0 who ports=("$@")
  [ ${#ports[@]} -gt 0 ] || ports=(5173 8099)
  for port in "${ports[@]}"; do
    if command -v ss >/dev/null 2>&1; then
      who=$(ss -ltnpH "sport = :$port" 2>/dev/null)
    elif command -v lsof >/dev/null 2>&1; then
      who=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null)
    else
      echo "pre_merge: neither ss nor lsof is installed; cannot check port $port" >&2
      return 1
    fi
    if [ -n "$who" ]; then
      echo "pre_merge: port $port is busy (neither Playwright nor the compose stack adopts a server):" >&2
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
  local sha bad=0 n=0 shas
  # An unknown base is red, not "no commits": an empty loop over a failed rev-list printed GREEN.
  if ! shas=$(git -C "$ROOT" rev-list "$BASE..HEAD"); then
    echo "pre_merge: cannot list $BASE..HEAD (fetch it, or pass --base)" >&2
    return 1
  fi
  for sha in $shas; do
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

# Without the docker CLI: both compose files parse and every build context has its Dockerfile.
compose_files_ok() {
  "$ROOT/backend/.venv/bin/python" - "$ROOT" <<'PY'
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
bad = 0
for name in ("docker-compose.yml", "docker-compose.ci.yml"):
    services = (yaml.safe_load((root / name).read_text()) or {}).get("services") or {}
    for service, spec in services.items():
        build = (spec or {}).get("build")
        if build is None:
            continue
        context = root / (build if isinstance(build, str) else build.get("context", "."))
        dockerfile = context / ("Dockerfile" if isinstance(build, str) else build.get("dockerfile", "Dockerfile"))
        if not dockerfile.is_file():
            print(f"{name}: service {service} builds {dockerfile}, which does not exist", file=sys.stderr)
            bad = 1
if not bad:
    print("compose files parse; every build context has its Dockerfile")
sys.exit(bad)
PY
}

docker_daemon() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }
docker_compose_cli() { command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; }
no_docker_daemon() {
  echo "pre_merge: --docker always, but no Docker daemon answers \`docker info\`" >&2
  return 1
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
  if [ "$COMPOSE_UP" = 1 ]; then
    (cd "$ROOT" && POSTGRES_PASSWORD=$CI_PASSWORD $CI_COMPOSE down -v --remove-orphans) >/dev/null 2>&1
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
IMG_API=0    # the image docker-compose.yml builds from backend/ (migrate, api, worker)
IMG_WEB=0    # the image it builds from frontend/ (web)
OTHER=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  case $path in
    backend/*) DO_BACKEND=1; IMG_API=1 ;;
    frontend/*) DO_FRONTEND=1; IMG_WEB=1 ;;
    .github/workflows/ci.yml|scripts/verify_compose.sh|scripts/image_context.py)
      DO_CI=1; CI_FILES+=("$path"); IMG_API=1; IMG_WEB=1 ;;
    .github/workflows/*|scripts/*) DO_CI=1; CI_FILES+=("$path") ;;
    docker-compose*.yml|docker-compose*.yaml|Dockerfile*|.dockerignore|*/Dockerfile*|*/.dockerignore)
      IMG_API=1; IMG_WEB=1 ;;
    *) OTHER=1 ;;
  esac
done <<<"$CHANGED"
case $SCOPE in
  backend) DO_BACKEND=1; IMG_API=1 ;;
  frontend) DO_FRONTEND=1; IMG_WEB=1 ;;
  all)
    DO_BACKEND=1; DO_FRONTEND=1; DO_CI=1; IMG_API=1; IMG_WEB=1
    CI_FILES=()
    while IFS= read -r path; do CI_FILES+=("$path"); done < <(
      cd "$ROOT" && ls .github/workflows/*.yml .github/workflows/*.yaml scripts/*.sh scripts/*.py 2>/dev/null)
    ;;
esac
DO_E2E=0
if [ "$E2E" = always ] || { [ "$E2E" = auto ] && [ "$DO_FRONTEND" = 1 ]; }; then DO_E2E=1; fi
DO_IMAGES=0
[ "$IMG_API$IMG_WEB" != 00 ] && DO_IMAGES=1
# The real container jobs need a daemon; the docker CLI alone (this sandbox has one) is not enough.
REAL_DOCKER=0
if [ "$DO_IMAGES" = 1 ]; then
  case $DOCKER in
    always) REAL_DOCKER=1 ;;
    auto) docker_daemon && REAL_DOCKER=1 ;;
  esac
fi
if [ "$DO_BACKEND$DO_FRONTEND$DO_CI$DO_E2E$DO_IMAGES" = 00000 ]; then
  if [ "$OTHER" = 1 ]; then NOTES+=("docs only (no backend/, frontend/, workflow, script or container path): the commit check alone")
  else NOTES+=("no path changed against $BASE: the commit check alone"); fi
fi
echo "pre_merge: scope backend=$DO_BACKEND frontend=$DO_FRONTEND workflows/scripts=$DO_CI e2e=$DO_E2E" \
  "images=api:$IMG_API,web:$IMG_WEB docker=$([ "$REAL_DOCKER" = 1 ] && echo daemon || echo offline)"

# 1. Preconditions (none for a docs-only diff: nothing runs that could dirty the tree).
if [ "$DO_BACKEND$DO_FRONTEND$DO_CI$DO_E2E$DO_IMAGES" != 00000 ]; then
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
      scripts/*.py) run "py_compile: $path" "$ROOT" backend/.venv/bin/python -m py_compile "$path" ;;
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

# 6. Containers: ci.yml jobs `security-and-containers` (compose config, compose build) and `compose-stack`
#    (verify_compose.sh with the CI override, then down). backend/tests/test_pre_merge_script.py fails when
#    either job gains a step this block does not mirror or approximate.
if [ "$DO_IMAGES" = 1 ]; then
  if docker_compose_cli || [ "$REAL_DOCKER" = 1 ]; then
    # `compose config` needs the CLI, not a daemon.
    run "compose: config --quiet" "$ROOT" env "POSTGRES_PASSWORD=$CI_PASSWORD" docker compose config --quiet
    run "compose: config --quiet (CI override)" "$ROOT" env "POSTGRES_PASSWORD=$CI_PASSWORD" \
      $CI_COMPOSE config --quiet
  else
    check "compose: files parse, build contexts exist (no docker CLI)" compose_files_ok
  fi
  if [ "$REAL_DOCKER" = 1 ]; then
    [ "$DRY" = 1 ] || docker_daemon || check "docker daemon (--docker always)" no_docker_daemon
    run "compose: build" "$ROOT" env "POSTGRES_PASSWORD=$CI_PASSWORD" docker compose build
    check "ports 8080/8099 free before the compose stack" ports_free 8080 8099
    [ "$DRY" = 0 ] && COMPOSE_UP=1
    run "compose-stack: verify_compose.sh" "$ROOT" env "POSTGRES_PASSWORD=$CI_PASSWORD" "COMPOSE=$CI_COMPOSE" \
      bash scripts/verify_compose.sh
  else
    # No daemon: each image's build in a copy of exactly its build context (GATE-2; 146a4e8e was GREEN
    # here while CI's `npm run build` inside the web image failed on a file .dockerignore dropped).
    NOTES+=("no Docker daemon: docker compose build / verify_compose.sh approximated by staging each build context (scripts/image_context.py); CI runs the real ones")
    if [ "$IMG_WEB" = 1 ]; then
      WEB_CTX="$RUN_TMP/image-web"
      run "image web: stage frontend/ context" "$ROOT" backend/.venv/bin/python scripts/image_context.py \
        stage frontend "$WEB_CTX" --link node_modules=frontend/node_modules
      # frontend/Dockerfile builder stage: `npm ci` (node_modules linked instead), then this.
      run "image web: npm run build" "$WEB_CTX" npm run build
    fi
    if [ "$IMG_API" = 1 ]; then
      API_CTX="$RUN_TMP/image-api"
      # docker-compose.yml's backend-env, minus PostgreSQL (CI's postgresql leg covers that dialect).
      API_ENV=(UNIMATCH_ENVIRONMENT=staging "UNIMATCH_DATABASE_URL=sqlite:///$RUN_TMP/image-api.db"
        UNIMATCH_AUTO_MIGRATE=false UNIMATCH_DEMO_MODE=false UNIMATCH_KNOWLEDGE_MODE=kb
        UNIMATCH_SEARCH_PROVIDER=none UNIMATCH_AUTH_ENABLED=true UNIMATCH_COOKIE_SECURE=false
        PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1)
      run "image api: stage backend/ context" "$ROOT" backend/.venv/bin/python scripts/image_context.py \
        stage backend "$API_CTX"
      # The api/worker commands, and what verify_compose.sh imports and serves (the demo profile, the KB);
      # the code must come from the staged copy, not from backend/.
      run "image api: import app.main, app.jobs.worker" "$API_CTX" env "${API_ENV[@]}" "$B/.venv/bin/python" -c \
        "import os, app.main, app.jobs.worker, app.corpus.demo_profile; from app.knowledge import load_knowledge_base as kb; assert app.main.__file__.startswith(os.getcwd() + os.sep), app.main.__file__; n = len(kb().entries); assert n, 'no knowledge base in the image'; print('imports from', os.path.dirname(app.main.__file__), '- KB entries:', n)"
      run "image migrate: alembic upgrade head" "$API_CTX" env "${API_ENV[@]}" "$B/.venv/bin/python" -m alembic \
        upgrade head
    fi
  fi
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
