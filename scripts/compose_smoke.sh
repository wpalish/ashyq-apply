#!/usr/bin/env bash
# Production-shaped runtime check for the compose stack.
#
# Builds and starts the stack on a throwaway project name and throwaway
# volumes, then exercises the things that only a running stack can show:
# health, the one-shot migration, a real research run picked up by the worker,
# recovery from a killed worker, restart survival, tenant isolation, security
# headers, and a backup/restore drill. It removes only what it created.
#
#   ./scripts/compose_smoke.sh
#
# Requires a container runtime. It is written to be run by CI, and by anyone
# with Docker locally; it is NOT a substitute for having run it.
set -euo pipefail

PROJECT="ashyq-smoke-$$"
export POSTGRES_PASSWORD="smoke-$(head -c 18 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')"
export API_PORT="${API_PORT:-18099}"
export WEB_PORT="${WEB_PORT:-18080}"
export UNIMATCH_DEMO_MODE=true
API="http://127.0.0.1:${API_PORT}"
COMPOSE=(docker compose -p "$PROJECT")
JAR_A="$(mktemp)"; JAR_B="$(mktemp)"
FAILED=0

step()  { printf '\n=== %s\n' "$1"; }
ok()    { printf '  ok   %s\n' "$1"; }
bad()   { printf '  FAIL %s\n' "$1"; FAILED=1; }
check() { if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (expected $2, got $1)"; fi; }

cleanup() {
  step "tearing down (only what this run created)"
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -f "$JAR_A" "$JAR_B"
}
trap cleanup EXIT

step "config and build"
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build

step "start"
"${COMPOSE[@]}" up -d

step "wait for health"
for _ in $(seq 1 60); do
  if curl -fsS "$API/api/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
check "$(curl -s -o /dev/null -w '%{http_code}' "$API/api/health")" "200" "API is healthy"

step "the one-shot migration ran to completion"
MIGRATE_EXIT="$("${COMPOSE[@]}" ps -a --format json migrate | tr ',' '\n' | grep -o '"ExitCode":[0-9-]*' | head -1 | cut -d: -f2 || echo "?")"
check "${MIGRATE_EXIT:-?}" "0" "migration job exited cleanly"

step "register, create a case, run demo research"
curl -fsS -c "$JAR_A" -X POST "$API/api/auth/register" -H 'content-type: application/json' \
  -d '{"email":"smoke-a@example.test","password":"correct horse battery smoke a","display_name":"Smoke A","organization_name":"Smoke A Org"}' >/dev/null
ok "registered tenant A"
# The demo profile lives in the image, so ask the running API for it rather
# than keeping a second copy in this script that could drift from the schema.
PROFILE_JSON="$("${COMPOSE[@]}" exec -T api python -c \
  'from app.corpus.demo_profile import DEMO_PROFILE; import json; print(json.dumps(DEMO_PROFILE.model_dump(mode="json")))')"
PROFILE_ID="$(printf '%s' "$PROFILE_JSON" \
  | curl -fsS -b "$JAR_A" "$API/api/profiles" -X POST -H 'content-type: application/json' --data-binary @- \
  | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || true)"
if [ -z "${PROFILE_ID:-}" ]; then
  bad "could not create an applicant case (see the API log)"
else
  ok "applicant case $PROFILE_ID"
  RUN_ID="$(curl -fsS -b "$JAR_A" -X POST "$API/api/runs" -H 'content-type: application/json' \
    -d "{\"profile_id\":\"$PROFILE_ID\",\"demo_mode\":true}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)"
  ok "run $RUN_ID enqueued"
  for _ in $(seq 1 90); do
    STAGE="$(curl -fsS -b "$JAR_A" "$API/api/runs/$RUN_ID" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)"
    [ "$STAGE" = "awaiting_user_decision" ] && break
    [ "$STAGE" = "failed" ] && break
    sleep 2
  done
  check "$STAGE" "awaiting_user_decision" "the worker picked up and finished the run"
  RESULTS_BEFORE="$(curl -fsS -b "$JAR_A" "$API/api/runs/$RUN_ID/results" | grep -o '"id":"' | wc -l | tr -d ' ')"
  ok "$RESULTS_BEFORE results, sources and documents available"

  step "kill the worker and let a new one take over"
  "${COMPOSE[@]}" kill -s SIGKILL worker >/dev/null
  "${COMPOSE[@]}" up -d worker >/dev/null
  sleep 10
  RESULTS_AFTER="$(curl -fsS -b "$JAR_A" "$API/api/runs/$RUN_ID/results" | grep -o '"id":"' | wc -l | tr -d ' ')"
  check "$RESULTS_AFTER" "$RESULTS_BEFORE" "no duplicate results after worker recovery"

  step "restart the API and confirm the session and data survive"
  "${COMPOSE[@]}" restart api >/dev/null
  for _ in $(seq 1 30); do curl -fsS "$API/api/health" >/dev/null 2>&1 && break; sleep 2; done
  check "$(curl -s -o /dev/null -w '%{http_code}' -b "$JAR_A" "$API/api/runs/$RUN_ID")" "200" "run still readable after restart"

  step "tenant isolation with a second user"
  curl -fsS -c "$JAR_B" -X POST "$API/api/auth/register" -H 'content-type: application/json' \
    -d '{"email":"smoke-b@example.test","password":"correct horse battery smoke b","display_name":"Smoke B","organization_name":"Smoke B Org"}' >/dev/null
  check "$(curl -s -o /dev/null -w '%{http_code}' -b "$JAR_B" "$API/api/runs/$RUN_ID")" "404" "tenant B cannot read tenant A's run"
  check "$(curl -s -o /dev/null -w '%{http_code}' -b "$JAR_B" "$API/api/profiles/$PROFILE_ID")" "404" "tenant B cannot read tenant A's case"
fi

step "security headers and cookie flags"
HEADERS="$(curl -fsSI "$API/api/health")"
for header in "x-content-type-options" "x-frame-options" "referrer-policy"; do
  if grep -qi "^$header:" <<<"$HEADERS"; then ok "$header present"; else bad "$header missing"; fi
done
if grep -qi "httponly" <<<"$(curl -fsSI -X POST "$API/api/auth/logout" -b "$JAR_A")"; then
  ok "session cookie is HttpOnly"
else
  bad "session cookie is not HttpOnly"
fi

step "backup and restore drill"
"${COMPOSE[@]}" exec -T postgres pg_dump -U ashyq ashyq_apply > /tmp/"$PROJECT".sql
if [ -s /tmp/"$PROJECT".sql ]; then ok "dump taken ($(wc -c < /tmp/"$PROJECT".sql) bytes)"; else bad "dump is empty"; fi
"${COMPOSE[@]}" exec -T postgres psql -U ashyq -d postgres -c 'CREATE DATABASE restore_check;' >/dev/null
"${COMPOSE[@]}" exec -T postgres psql -U ashyq -d restore_check < /tmp/"$PROJECT".sql >/dev/null 2>&1
RESTORED="$("${COMPOSE[@]}" exec -T postgres psql -U ashyq -d restore_check -tAc 'select count(*) from research_runs;' | tr -d ' \r')"
if [ "${RESTORED:-0}" -ge 1 ]; then ok "restored database contains $RESTORED run(s)"; else bad "restore produced no rows"; fi
rm -f /tmp/"$PROJECT".sql

step "result"
if [ "$FAILED" = "0" ]; then echo "  PASS: the production-shaped stack works"; else echo "  FAIL: see the lines above"; fi
exit "$FAILED"
