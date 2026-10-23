# Unimatch: admissions action storage

2026-10-12T16:21:47.234703+00:00

## Confirmed locally

Two profile-owned tables now retain bounded personal action state and immutable event receipts. Additive migration d7a61e902024 has one source head. Current native controls: **38 passed, 0 failed/error/skipped, 5 warnings**, exactly19 SQLite and19 PostgreSQL nodes. They verify populated upgrade/downgrade/re-upgrade, complete row/header/receipt equality, physical constraints, atomic rollback, physical and ORM case erasure, native sole-account erasure, and retained history for shared workspace members. Native preexisting rows remain unchanged. Static Ruff, formatting and mypy402 pass. Source/helper pins and isolated runtime cleanup were verified.

## Fixed and preserved

First native run had20 failures. Migration fixture supplied only one selected result against unchanged native minimum2; now it supplies two own synthetic results. PostgreSQL serialized the same timestamp in +05:00; the test now canonicalizes the instant to UTC. Strict UTC metadata checks and every full-column assertion remain. All first failure and verbose raw evidence retained. Native Base/config/timezone were not changed.

## Remaining

The test storage writer is synthetic setup. Real G3 HTTP commands, UUID/CAS races, current/history/export/Today, browser workflow and production are not yet qualified. Initial full5537 eachDB qualifies the earlier pure/schema increment; current38 is a focused storage check, not full coverage or product acceptance. Search/expert/live/provider stopped work stays closed and search quality has no new score.
