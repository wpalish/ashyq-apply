# PostgreSQL backup and restore

Applicant profiles and research evidence are database state. Backups therefore
contain sensitive applicant data: encrypt them at rest, restrict access to the
operations team, keep them out of Git, and apply the same retention/deletion
policy as the live database.

## Automated backup

Use the platform's encrypted daily PostgreSQL snapshots plus point-in-time/WAL
recovery when the provider offers it. Keep at least 7 daily and 4 weekly restore
points. A backup is not accepted until a restore drill has succeeded.

For the Compose stack, create a custom-format logical backup:

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
scratch database:

```bash
cd backend
python scripts/pg.py .venv/bin/python scripts/backup_drill.py
```
