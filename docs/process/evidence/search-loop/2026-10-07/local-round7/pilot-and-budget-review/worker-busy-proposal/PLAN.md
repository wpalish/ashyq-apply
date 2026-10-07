# Узкий Worker checkpoint_busy — внешний proposal, до кода

PG09 независимого A закреплённым v2 вызывает actual Worker._run_job:
UniversityReadStopped(checkpoint_busy) → generic failure handler → JobStore.fail
UPDATE ждёт чужой Job row lock и выдаёт test SQLSTATE57014 через5секунд.

Proposal затрагивает только app/jobs/worker.py поверх pinned readguardv2.
В exceptException распознать только UniversityReadStopped(reason=checkpoint_busy):
логировать deferred recovery, не делать failure-writer SQL под тем же lock;
оставить job+run+facts+ledger неизменными, finally отменяет own heartbeat.
Существующий lease reaper после expiry/release затем обычный fenced claim
возобновляет САМЕ Job с новым attempt. Никакого refund/reset/new episode.
Все прочие errors/LeaseLost/cancel/business paths сохраняют прежнюю обработку.
Это исправляет typed checkpoint_busy путь, не любой DB OperationalError,
не обещает immediate backoff или durableunknown под удерживаемым lock.

Независимые controls: exact PG09 originalred не менять; новый собственный
snapshot/livedatabase тест проверяет bounded return/zeroIO/no failure-write,
priorfacts/ledger preserved, bothJob/Run locks, after release/expiry actual
reap→claim token2→sameepisodecounter cap still60; stale/cancel/othererror
unchanged. SQLite exclusive/busy проверить отдельно. Source-defaultFalse;
repo/source/Git/STOP/network не менять. Parent apply только после acceptance.
