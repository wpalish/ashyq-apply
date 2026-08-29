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

DUMP="/tmp/${PROJECT}.sql"

cleanup() {
  step "tearing down (only what this run created)"
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  # Cookie jars and the SQL dump go in the trap, not at the end of the happy
  # path: an early exit would otherwise leave the dump behind.
  rm -f "$JAR_A" "$JAR_B" "$DUMP"
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

  # --- a reference run, so the interrupted one can be compared to it -------
  step "a clean run, for comparison"
  for _ in $(seq 1 90); do
    STAGE="$(curl -fsS -b "$JAR_A" "$API/api/runs/$RUN_ID" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)"
    [ "$STAGE" = "awaiting_user_decision" ] && break
    [ "$STAGE" = "failed" ] && break
    sleep 2
  done
  check "$STAGE" "awaiting_user_decision" "the worker picked up and finished a clean run"
  CLEAN_RESULTS="$(curl -fsS -b "$JAR_A" "$API/api/runs/$RUN_ID/results" | grep -o '"id":"' | wc -l | tr -d ' ')"
  ok "clean run produced $CLEAN_RESULTS results"

  # --- now interrupt a run *while it is working* --------------------------
  # The previous version killed the worker after the run had already reached
  # awaiting_user_decision, so there was nothing in flight and nothing to
  # recover. It proved only that a finished run stays finished.
  step "kill the worker mid-run and let a new one take over"
  CRASH_RUN="$(curl -fsS -b "$JAR_A" -X POST "$API/api/runs" -H 'content-type: application/json' \
    -d "{\"profile_id\":\"$PROFILE_ID\",\"demo_mode\":true}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)"
  ok "run $CRASH_RUN enqueued for the crash test"

  MID_STAGE=""
  MID_RESULTS=0
  for _ in $(seq 1 120); do
    MID_STAGE="$(curl -fsS -b "$JAR_A" "$API/api/runs/$CRASH_RUN" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)"
    MID_RESULTS="$(curl -fsS -b "$JAR_A" "$API/api/runs/$CRASH_RUN/results" | grep -o '"id":"' | wc -l | tr -d ' ')"
    case "$MID_STAGE" in
      program_verification|funding_discovery|assessment)
        [ "${MID_RESULTS:-0}" -ge 1 ] && break ;;
      awaiting_user_decision|failed|cancelled) break ;;
    esac
    sleep 1
  done

  case "$MID_STAGE" in
    program_verification|funding_discovery|assessment)
      ok "caught the run in $MID_STAGE with $MID_RESULTS results already written"

      # SIGKILL, not stop: a graceful handler would let the worker finish and
      # the lease would be released cleanly, which is a different test.
      "${COMPOSE[@]}" kill -s SIGKILL worker >/dev/null
      ok "worker SIGKILLed"

      JOB_STATE="$("${COMPOSE[@]}" exec -T api python -c "
from app.db import SessionLocal
from app.models import Job
with SessionLocal() as s:
    j = s.query(Job).filter(Job.run_id == '$CRASH_RUN').first()
    print(f'{j.status}|{j.attempts}' if j else 'missing|0')
" 2>/dev/null | tr -d '\r')"
      ATTEMPTS_BEFORE="${JOB_STATE##*|}"
      check "${JOB_STATE%%|*}" "running" "the job is still claimed by the dead worker"

      step "wait for the lease to expire, then start a new worker"
      sleep 35
      "${COMPOSE[@]}" up -d worker >/dev/null

      FINAL_STAGE=""
      for _ in $(seq 1 120); do
        FINAL_STAGE="$(curl -fsS -b "$JAR_A" "$API/api/runs/$CRASH_RUN" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)"
        case "$FINAL_STAGE" in awaiting_user_decision|failed|cancelled) break ;; esac
        sleep 2
      done
      check "$FINAL_STAGE" "awaiting_user_decision" "the run continued to a decision point"

      AFTER="$("${COMPOSE[@]}" exec -T api python -c "
from app.db import SessionLocal
from app.models import Job, ProgramResultRow
with SessionLocal() as s:
    j = s.query(Job).filter(Job.run_id == '$CRASH_RUN').first()
    rows = s.query(ProgramResultRow).filter(ProgramResultRow.run_id == '$CRASH_RUN').all()
    keys = [r.dedupe_key for r in rows]
    print(f'{j.status}|{j.attempts}|{j.worker_id}|{len(rows)}|{len(set(keys))}')
" 2>/dev/null | tr -d '\r')"
      IFS='|' read -r F_STATUS F_ATTEMPTS F_WORKER F_ROWS F_UNIQUE <<<"$AFTER"
      check "$F_STATUS" "succeeded" "the job reached succeeded, not stuck or dead"
      check "$F_UNIQUE" "$F_ROWS" "no duplicate results after recovery"
      check "$F_ROWS" "$CLEAN_RESULTS" "the interrupted run produced what a clean run does"
      check "$F_WORKER" "None" "the lease was released"
      if [ "${F_ATTEMPTS:-0}" -gt "${ATTEMPTS_BEFORE:-0}" ]; then
        ok "attempts rose from $ATTEMPTS_BEFORE to $F_ATTEMPTS: the job was re-claimed"
      else
        bad "attempts stayed at $F_ATTEMPTS; a claim always increments it"
      fi
      ;;
    *)
      bad "never caught the run in flight (stage=$MID_STAGE, results=$MID_RESULTS); \
in-flight crash recovery was NOT exercised"
      ;;
  esac

  step "a cancelled run must not report success"
  CANCEL_RUN="$(curl -fsS -b "$JAR_A" -X POST "$API/api/runs" -H 'content-type: application/json' \
    -d "{\"profile_id\":\"$PROFILE_ID\",\"demo_mode\":true}" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)"
  sleep 2
  curl -fsS -b "$JAR_A" -X POST "$API/api/runs/$CANCEL_RUN/cancel" >/dev/null || true
  sleep 8
  CANCEL_JOB="$("${COMPOSE[@]}" exec -T api python -c "
from app.db import SessionLocal
from app.models import Job
with SessionLocal() as s:
    j = s.query(Job).filter(Job.run_id == '$CANCEL_RUN').first()
    print(j.status if j else 'missing')
" 2>/dev/null | tr -d '\r')"
  if [ "$CANCEL_JOB" = "succeeded" ]; then
    bad "a cancelled run reported its job as succeeded"
  else
    ok "cancelled run's job is $CANCEL_JOB, not succeeded"
  fi

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
"${COMPOSE[@]}" exec -T postgres pg_dump -U ashyq ashyq_apply > "$DUMP"
if [ -s "$DUMP" ]; then ok "dump taken ($(wc -c < "$DUMP") bytes)"; else bad "dump is empty"; fi
"${COMPOSE[@]}" exec -T postgres psql -U ashyq -d postgres -c 'CREATE DATABASE restore_check;' >/dev/null
"${COMPOSE[@]}" exec -T postgres psql -U ashyq -d restore_check < "$DUMP" >/dev/null 2>&1

# Row counts for every table, not just one: a restore that brings back the runs
# and loses their claims is a restore that lost the evidence.
TABLES="research_runs program_results claims conflicts jobs applicant_profiles users organizations"
for table in $TABLES; do
  SRC="$("${COMPOSE[@]}" exec -T postgres psql -U ashyq -d ashyq_apply -tAc \
    "select count(*) from $table;" 2>/dev/null | tr -d ' \r')"
  DST="$("${COMPOSE[@]}" exec -T postgres psql -U ashyq -d restore_check -tAc \
    "select count(*) from $table;" 2>/dev/null | tr -d ' \r')"
  check "${DST:-missing}" "${SRC:-missing}" "restored $table row count ($SRC)"
done

# And one payload, so "the rows are there" is not the whole claim.
SRC_PAYLOAD="$("${COMPOSE[@]}" exec -T postgres psql -U ashyq -d ashyq_apply -tAc \
  "select md5(string_agg(dedupe_key, ',' order by dedupe_key)) from program_results;" \
  2>/dev/null | tr -d ' \r')"
DST_PAYLOAD="$("${COMPOSE[@]}" exec -T postgres psql -U ashyq -d restore_check -tAc \
  "select md5(string_agg(dedupe_key, ',' order by dedupe_key)) from program_results;" \
  2>/dev/null | tr -d ' \r')"
check "${DST_PAYLOAD:-missing}" "${SRC_PAYLOAD:-missing}" "restored result keys are identical"

step "result"
if [ "$FAILED" = "0" ]; then echo "  PASS: the production-shaped stack works"; else echo "  FAIL: see the lines above"; fi
exit "$FAILED"
