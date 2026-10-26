#!/usr/bin/env bash
# Prove the container stack actually serves, rather than merely building.
#
#   ./scripts/verify_compose.sh
#
# Checks, in order: every service reaches its expected state, the API answers
# a health probe, the worker consumes a job, a demo run reaches
# awaiting_user_decision through web -> api -> worker, and then a kb-mode run
# (the launch path, CS-1) does too without reading a single page: two
# universities with verified data and one without, which must answer
# "No verified data yet". Exits non-zero on the first failure, so it is usable
# as a release gate. CI (the compose-stack job) adds docker-compose.ci.yml:
#
#   COMPOSE="docker compose -f docker-compose.yml -f docker-compose.ci.yml" \
#     POSTGRES_PASSWORD=ci-only-not-a-secret scripts/verify_compose.sh
#
# Needs docker compose, curl and python3 (to read JSON) on the host.
set -euo pipefail
cd "$(dirname "$0")/.."

API="http://localhost:${API_PORT:-8099}"
WEB="http://localhost:${WEB_PORT:-8080}"
COMPOSE="${COMPOSE:-docker compose}"

fail() { echo "FAIL: $*" >&2; $COMPOSE ps --all; exit 1; }
# json <expr>: a Python expression over the JSON document on stdin, bound to d.
json() { python3 -c "import json, os, sys; d = json.load(sys.stdin); print($1)"; }

echo "==> building and starting"
$COMPOSE up --build -d

echo "==> waiting for the migration job to finish"
# --all: a finished one-shot job is hidden from a plain `compose ps`.
state=""
for _ in $(seq 1 60); do
  state=$($COMPOSE ps --all --format '{{.Service}} {{.State}} {{.ExitCode}}' \
    | awk '$1=="migrate"{print $2, $3}')
  case "$state" in exited*) break ;; esac
  sleep 2
done
[ "$state" = "exited 0" ] || fail "the migrate job did not exit cleanly (state=$state)"

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
  -H 'Content-Type: application/json' -d "$demo_profile" | json 'd["id"]')
[ -n "$profile" ] || fail "could not create an applicant profile"

# demo_mode is explicit: since CS-1 the stack's own default is kb mode.
run=$(curl -fsS -b "$jar" -X POST "$API/api/runs" -H 'Content-Type: application/json' \
  -d "{\"profile_id\":\"$profile\",\"demo_mode\":true}" | json 'd["id"]')
[ -n "$run" ] || fail "the API did not accept a run"

for _ in $(seq 1 60); do
  # The run's own stage. A sed over the body matched the last "stage" key,
  # which is the final entry of the `stages` list ("completed"), not this.
  stage=$(curl -fsS -b "$jar" "$API/api/runs/$run" | json 'd["stage"]')
  [ "$stage" = "awaiting_user_decision" ] && break
  [ "$stage" = "failed" ] && fail "the run failed inside the container stack"
  sleep 3
done
[ "$stage" = "awaiting_user_decision" ] || fail "the worker never finished the run (stage=$stage)"

echo "==> serving the built frontend"
curl -fsS "$WEB" | grep -qi "<title" || fail "the web container did not serve the app"

# ---------------------------------------------------------------- kb mode (CS-1)
# The launch path: the server's own default mode, not a per-run demo choice.

echo "==> kb mode: the server reports the knowledge base as its reach"
caps=$(curl -fsS -b "$jar" "$API/api/capabilities")
[ "$(echo "$caps" | json 'd["knowledge_mode"]')" = "kb" ] \
  || fail "capabilities.knowledge_mode is not kb (is UNIMATCH_DEMO_MODE on?)"
[ "$(echo "$caps" | json 'd["live_coverage"].get("mode")')" = "kb" ] \
  || fail "capabilities.live_coverage.mode is not kb"
echo "$caps" | json '"live_coverage: " + d["live_coverage"]["recall_note"]'

echo "==> kb mode: two universities with verified data and one without"
verified=$(curl -fsS -b "$jar" "$API/api/universities?verified=true&limit=2" \
  | json '" ".join(u["id"] for u in d["items"] if (u["knowledge"] or {}).get("in_kb"))')
# shellcheck disable=SC2086  # split on purpose: one id per word
set -- $verified
[ "$#" -eq 2 ] || fail "GET /api/universities?verified=true did not return two KB universities"
kb_a=$1
kb_b=$2
# A catalogue row the KB holds no verified data for. The KB is a small slice
# of the catalogue, so the first hundred rows hold one.
non_kb_id=$(curl -fsS -b "$jar" "$API/api/universities?limit=100" \
  | json 'next((u["id"] for u in d["items"] if not (u["knowledge"] or {}).get("in_kb")), "")')
[ -n "$non_kb_id" ] || fail "no catalogue university without verified data was found"
echo "verified data: $kb_a $kb_b; none: $non_kb_id"

echo "==> kb mode: a run on the server's default mode"
kb_run=$(curl -fsS -b "$jar" -X POST "$API/api/runs" -H 'Content-Type: application/json' \
  -d "{\"profile_id\":\"$profile\",\"university_ids\":[\"$kb_a\",\"$kb_b\",\"$non_kb_id\"]}" \
  | json 'd["id"]')
[ -n "$kb_run" ] || fail "the API did not accept a kb-mode run"

stage=""
for _ in $(seq 1 60); do
  stage=$(curl -fsS -b "$jar" "$API/api/runs/$kb_run" | json 'd["stage"]')
  [ "$stage" = "awaiting_user_decision" ] && break
  [ "$stage" = "failed" ] && fail "the kb-mode run failed inside the container stack"
  sleep 3
done
[ "$stage" = "awaiting_user_decision" ] || fail "the worker never finished the kb-mode run (stage=$stage)"

echo "==> kb mode: no page was read"
view=$(curl -fsS -b "$jar" "$API/api/runs/$kb_run")
[ "$(echo "$view" | json 'd["demo_mode"]')" = "False" ] || fail "the kb-mode run ran as a demo run"
[ "$(echo "$view" | json 'd["settings"].get("knowledge_mode")')" = "kb" ] \
  || fail "the run's settings.knowledge_mode is not kb"
[ "$(echo "$view" | json 'd["pages_checked"]')" = "0" ] || fail "the kb-mode run checked pages"
[ "$(echo "$view" | json 'sum(int(v) for v in d["fetch_tiers"].values())')" = "0" ] \
  || fail "the kb-mode run used a fetch tier: $(echo "$view" | json 'd["fetch_tiers"]')"
echo "$view" | json '"pages_checked=%s fetch_tiers=%s knowledge_base=%s" % (d["pages_checked"], d["fetch_tiers"], d["settings"].get("knowledge_base"))'

echo "==> kb mode: the university without verified data says so"
non_kb_name=$(curl -fsS -b "$jar" "$API/api/universities?limit=100" \
  | NON_KB="$non_kb_id" json 'next(u["name"] for u in d["items"] if u["id"] == os.environ["NON_KB"])')
questions=$(curl -fsS -b "$jar" "$API/api/runs/$kb_run/questions")
answer=$(echo "$questions" \
  | NAME="$non_kb_name" json 'next((q["question"] for q in d if q["university"] == os.environ["NAME"] and q.get("blocking") and q["question"].startswith("No verified data yet")), "")')
[ -n "$answer" ] || fail "no blocking 'No verified data yet' question for $non_kb_name"
echo "$answer"
# ...and only that one: the two KB universities answer from verified data.
without=$(echo "$questions" \
  | json 'sorted({q["university"] for q in d if q["question"].startswith("No verified data yet")})')
[ "$(echo "$questions" | json 'len({q["university"] for q in d if q["question"].startswith("No verified data yet")})')" = "1" ] \
  || fail "a KB university also answered 'No verified data yet': $without"

echo
echo "PASS: web -> api -> worker completed a demo run in containers."
echo "PASS: the stack completed a kb-mode run with no page read."
echo "Tear down with: $COMPOSE down -v"
