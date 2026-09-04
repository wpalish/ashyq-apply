# PostgreSQL backup and restore

Applicant profiles and research evidence are database state. Backups therefore
contain sensitive applicant data: encrypt them at rest, restrict access to the
operations team, keep them out of Git, and apply the same retention/deletion
policy as the live database.

## The schedule

"Use the platform's snapshots" is not a schedule, so here is one.

**Compose stack.** `scripts/backup.sh` takes one dump, verifies it by reading
its table of contents back, and deletes dumps older than `RETENTION_DAYS`
(default 30) — but only after the new one has verified, so a failed backup can
never be the reason a good one is removed. Install it as a cron job on the
host, at 02:15 UTC daily:

```cron
15 2 * * * cd /srv/ashyq-apply && RETENTION_DAYS=30 ./scripts/backup.sh >> /var/log/ashyq-backup.log 2>&1
```

Check the log after the first run. A cron job nobody has ever read the output
of is a backup nobody has ever taken.

**Fly.io.** A Fly Postgres cluster takes its own daily snapshots; set the
window and keep at least seven:

```bash
fly postgres list
fly volumes list --app <db-app>            # snapshot retention lives on the volume
fly volumes snapshots list <volume-id>     # confirm snapshots actually exist
fly volumes snapshots create <volume-id>   # one on demand, before a risky deploy
```

For a logical dump as well (a snapshot restores a whole volume; a dump lets you
restore one database into a scratch one), run the same script against a proxied
connection:

```bash
fly proxy 15432:5432 --app <db-app> &
pg_dump --format=custom --no-owner --no-privileges \
  --dbname "postgresql://<user>:<password>@localhost:15432/<db>" \
  --file "private-backups/ashyq-apply-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Retention target either way: at least 7 daily and 4 weekly restore points. A
backup is not accepted until a restore drill has succeeded against it.

## Automated backup

Use the platform's encrypted snapshots plus point-in-time/WAL recovery when the
provider offers it.

For the Compose stack by hand, create a custom-format logical backup:

```bash
mkdir -p private-backups
chmod 700 private-backups
docker compose exec -T postgres \
  pg_dump --format=custom --no-owner --no-privileges \
  --username=ashyq --dbname=ashyq_apply \
  > private-backups/ashyq-apply-$(date -u +%Y%m%dT%H%M%SZ).dump
```

`private-backups/` must be outside shared folders and is ignored by Git.

## Restore checkpoint

Restore into a new database first; never test against production:

```bash
docker compose exec postgres createdb --username=ashyq ashyq_apply_restore_check
docker compose exec -T postgres \
  pg_restore --exit-on-error --no-owner --no-privileges \
  --username=ashyq --dbname=ashyq_apply_restore_check \
  < private-backups/FILE.dump
```

Verify the Alembic revision, table counts, one synthetic probe profile and one
evidence claim. Only then schedule a production restore with an explicit outage
window and a fresh pre-restore snapshot.

The repository's destructive-safe drill creates and drops only its own random
scratch database. It dumps, restores into that scratch database, compares every
application table's row count and checks a synthetic probe row survived:

```bash
cd backend
python scripts/pg.py .venv/bin/python scripts/backup_drill.py          # Linux, macOS
python scripts/pg.py .venv/Scripts/python.exe scripts/backup_drill.py  # Windows
```

Last run: **PASS — 18 tables restored with identical row counts**, against the
bundled PostgreSQL on Windows, 4 September 2026. Reaching that took two fixes
to the drill itself: it asked for `pg_dump` by its POSIX name, so on Windows it
never found the `pg_dump.exe` sitting beside it, and it left the temporary dump
file open, so its own cleanup then failed with a permission error that hid the
first problem entirely.
