#!/usr/bin/env bash
# Prove the container stack actually serves, rather than merely building.
#
#   ./scripts/verify_compose.sh
#
# Checks, in order: every service reaches its expected state, the API answers
# a health probe, the worker consumes a job, and a demo run reaches
# awaiting_user_decision through web -> api -> worker. Exits non-zero on the
# first failure, so it is usable as a release gate.
set -euo pipefail
cd "$(dirname "$0")/.."

API="http://localhost:${API_PORT:-8099}"
WEB="http://localhost:${WEB_PORT:-8080}"
COMPOSE="${COMPOSE:-docker compose}"

fail() { echo "FAIL: $*" >&2; $COMPOSE ps; exit 1; }

echo "==> building and starting"
$COMPOSE up --build -d

echo "==> waiting for the migration job to finish"
for _ in $(seq 1 60); do
  state=$($COMPOSE ps --format '{{.Service}} {{.State}}' | awk '$1=="migrate"{print $2}')
  [ "$state" = "exited" ] && break
  sleep 2
done
$COMPOSE ps migrate | grep -q "Exit 0\|exited (0)" || fail "the migrate job did not exit cleanly"

echo "==> waiting for the API to report healthy"
for _ in $(seq 1 60); do
  body=$(curl -fsS "$API/api/health" 2>/dev/null || true)
  case "$body" in *'"status"'*) break ;; esac
  sleep 2
done
[ -n "${body:-}" ] || fail "the API never answered $API/api/health"
echo "$body"

echo "==> the web container must be up, which requires the API to be healthy"
$COMPOSE ps web | grep -qi "up\|running" || fail "web is not running"

echo "==> registering an account (auth is on in this stack)"
email="verify-$(date +%s)@example.test"
jar=$(mktemp)
curl -fsS -c "$jar" -X POST "$API/api/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"correct horse battery staple\",\"display_name\":\"Verify\",\"organization_name\":\"Verify\"}" \
  >/dev/null || fail "registration failed"

echo "==> starting a demo run and waiting for the worker to finish it"
# The bundled synthetic applicant lives in the image, not behind an endpoint,
# so ask the API container to print it rather than duplicating it here.
demo_profile=$($COMPOSE exec -T api python -c \
  "from app.corpus.demo_profile import DEMO_PROFILE; import json; print(json.dumps(DEMO_PROFILE.model_dump(mode='json')))")
profile=$(curl -fsS -b "$jar" -X POST "$API/api/profiles" \
  -H 'Content-Type: application/json' -d "$demo_profile" \
  | sed -n 's/.*"id":"\([0-9a-f]*\)".*/\1/p')
[ -n "$profile" ] || fail "could not create an applicant profile"

run=$(curl -fsS -b "$jar" -X POST "$API/api/runs" -H 'Content-Type: application/json' \
  -d "{\"profile_id\":\"$profile\",\"demo_mode\":true}" | sed -n 's/.*"id":"\([0-9a-f]*\)".*/\1/p')
[ -n "$run" ] || fail "the API did not accept a run"

for _ in $(seq 1 60); do
  stage=$(curl -fsS -b "$jar" "$API/api/runs/$run" | sed -n 's/.*"stage":"\([a-z_]*\)".*/\1/p')
  [ "$stage" = "awaiting_user_decision" ] && break
  [ "$stage" = "failed" ] && fail "the run failed inside the container stack"
  sleep 3
done
[ "$stage" = "awaiting_user_decision" ] || fail "the worker never finished the run (stage=$stage)"

echo "==> serving the built frontend"
curl -fsS "$WEB" | grep -qi "<title" || fail "the web container did not serve the app"

echo
echo "PASS: web -> api -> worker completed a demo run in containers."
echo "Tear down with: $COMPOSE down -v"
