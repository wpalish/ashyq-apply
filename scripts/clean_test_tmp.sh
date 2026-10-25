#!/usr/bin/env bash
# Remove what crashed test runs leave in /tmp: pgserver clusters (unimatch-pg-*) and pytest's
# basetemp folders. Only stale ones go: a cluster older than 10 minutes that no running postgres
# uses, a pytest folder older than 20 minutes. A postgres whose parent has exited (orphaned by a
# killed xdist worker) and that has run for 30+ minutes is stopped first. Safe to run any time.
set -uo pipefail
TMP=${TMPDIR:-/tmp}

# Orphaned test postgres servers: parent is init (1), running for over 30 minutes.
ps -eo pid=,ppid=,etimes=,args= | awk -v t="$TMP/unimatch-pg-" \
  '$2 == 1 && $3 > 1800 && index($0, t) {print $1}' | xargs -r kill 2>/dev/null
sleep 1

in_use=$(ps -eo args= | grep -oE "$TMP/(unimatch-suite-[A-Za-z0-9]+/)?unimatch-pg-[A-Za-z0-9_]+" | sort -u)
removed=0
for d in "$TMP"/unimatch-pg-* "$TMP"/unimatch-suite-*/unimatch-pg-*; do
  [ -d "$d" ] || continue
  grep -qxF "$d" <<<"$in_use" && continue
  [ -n "$(find "$d" -maxdepth 0 -mmin +10)" ] || continue
  rm -rf -- "$d" && removed=$((removed + 1))
done
for base in "$TMP"/pytest-of-*; do
  [ -d "$base" ] || continue
  find "$base" -mindepth 1 -maxdepth 1 -name 'pytest-[0-9]*' -mmin +20 -exec rm -rf -- {} + 2>/dev/null
done
echo "clean_test_tmp: removed $removed stale pg clusters; free $(df -h "$TMP" | awk 'NR==2{print $4}')"
