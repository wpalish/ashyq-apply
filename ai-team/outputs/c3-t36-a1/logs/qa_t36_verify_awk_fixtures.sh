#!/usr/bin/env bash
# T36 VERIFY: validate the exact awk publication-gate from scripts/verify_compose.sh
# against docker-compose-config-shaped fixtures (offline; no docker daemon).
set -u

AWK_PROG='/^  api:$/ { in_api = 1; next }
  /^  [^ ]/ { in_api = 0 }
  in_api && /published:/ && /8099/ { print }'

header='name: ashyq-apply
services:'

expose_only="$header
  api:
    build:
      context: ./backend
    expose:
      - \"8099\"
    networks:
      default: null
networks:
  default:
    name: ashyq-apply_default"

published_8099="$header
  api:
    build:
      context: ./backend
    expose:
      - \"8099\"
    ports:
      - target: 8099
        published: \"8099\"
        protocol: tcp
        mode: host
networks:
  default:
    name: ashyq-apply_default"

loopback_8099="$header
  api:
    build:
      context: ./backend
    ports:
      - target: 8099
        published: \"8099\"
        host_ip: 127.0.0.1
        protocol: tcp
        mode: host
networks:
  default:
    name: ashyq-apply_default"

web_publishes_8080="$header
  api:
    build:
      context: ./backend
    expose:
      - \"8099\"
  web:
    build:
      context: ./frontend
    ports:
      - target: 8080
        published: \"8080\"
        protocol: tcp
        mode: host
networks:
  default:
    name: ashyq-apply_default"

host_remap_8099="$header
  api:
    build:
      context: ./backend
    ports:
      - target: 8099
        published: \"9099\"
        protocol: tcp
        mode: host
networks:
  default:
    name: ashyq-apply_default"

check() {
  local label="$1" fixture="$2" expect="$3"
  local out
  out=$(printf '%s\n' "$fixture" | awk "$AWK_PROG")
  local flagged="no"
  [ -n "$out" ] && flagged="yes"
  local verdict=PASS
  [ "$flagged" != "$expect" ] && verdict=FAIL
  printf '[%s] %-28s flagged=%s expected_flagged=%s' "$verdict" "$label" "$flagged" "$expect"
  [ -n "$out" ] && printf '  (%s)' "$(printf '%s' "$out" | tr -s ' ')"
  printf '\n'
}

check "expose-only api"            "$expose_only"     "no"
check "api published 8099"         "$published_8099"  "yes"
check "api loopback 8099"          "$loopback_8099"   "yes"
check "web publishes 8080"         "$web_publishes_8080" "no"
check "host remap 9099->8099"      "$host_remap_8099" "no"
