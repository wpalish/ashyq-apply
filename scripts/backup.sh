#!/usr/bin/env bash
# Take one verified PostgreSQL backup of the Compose stack, then prune old ones.
#
#   ./scripts/backup.sh
#
# Written to be run from cron, so it is quiet on success, loud on failure, and
# safe to run twice in the same minute. The dump is verified by reading its
# table of contents back: a file that pg_restore cannot list is not a backup,
# and finding that out during an incident is finding out too late.
#
# The dump contains every applicant's profile, evidence and decisions. It is
# written with owner-only permissions into a directory Git ignores; where it
# goes next is the operator's problem to solve deliberately - encrypted, off
# this host, with the same deletion policy as the live database.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-private-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE="${COMPOSE:-docker compose}"
PG_SERVICE="${PG_SERVICE:-postgres}"
PG_USER="${PG_USER:-ashyq}"
PG_DATABASE="${PG_DATABASE:-ashyq_apply}"

fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$BACKUP_DIR/ashyq-apply-$stamp.dump"

# --format=custom so pg_restore can select objects and refuse a partial file;
# --no-owner/--no-privileges so the dump restores into a differently named role.
$COMPOSE exec -T "$PG_SERVICE" \
  pg_dump --format=custom --no-owner --no-privileges \
  --username="$PG_USER" --dbname="$PG_DATABASE" \
  > "$target" || fail "pg_dump did not complete; $target is not a backup"

chmod 600 "$target"
[ -s "$target" ] || fail "$target is empty"

# Read it back. A dump that cannot be listed cannot be restored.
$COMPOSE exec -T "$PG_SERVICE" pg_restore --list /dev/stdin < "$target" > /dev/null \
  || fail "$target is not a readable custom-format dump"

# Prune only this script's own files, and only after the new one is verified:
# a failed backup must never be the reason an old good one is deleted.
find "$BACKUP_DIR" -maxdepth 1 -name 'ashyq-apply-*.dump' -type f \
  -mtime "+$RETENTION_DAYS" -delete

kept=$(find "$BACKUP_DIR" -maxdepth 1 -name 'ashyq-apply-*.dump' -type f | wc -l)
echo "OK: $target ($(wc -c < "$target") bytes), $kept kept, retention ${RETENTION_DAYS}d"
