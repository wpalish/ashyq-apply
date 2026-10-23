# Rejected production read-budget candidate b603fe6a

This is an immutable review checkpoint, not applied production code. Exact author manifest b603fe6a75660679e39b1b59545e21aae3aac79793ef2ae5d84c1ec6dc483a31 and patch c09219f02f30a89ec083484868586264f91cabb89eb8cb7e80c0e30221b8b0f7 were rejected by A/root after independent actual SQLite controls.

First-namespace race: stale guard-off settings replacement removes committed count60, then the on runner admits original get61 and persists count1. Duplicate same Job/worker/attempt is synthetic; ordinary worker reachability is unproved. This still prevents a universal durable-cap claim. Busy real verification caller: zero original get and unchanged prior ClaimRow/ProgramResult, but OperationalError escapes and durable unknown is absent. A deliberate cap red is retained; it is not a green result. Author70 tests and other independent6 controls pass.

The earlier author SQLite no-write-lock proposal (two get/count1), failed fixtures and raw logs are also preserved. Local SQLite runtime DB/WAL/SHM, pytest runtime trees and cache files are excluded. Known configured secrets scanned with zero matches; no live/provider/model calls. PG concurrency, hard120s, durable queries, guard intent and genuine fenced capture remain open. A separately pinned v2 must be reviewed before repository source changes.
