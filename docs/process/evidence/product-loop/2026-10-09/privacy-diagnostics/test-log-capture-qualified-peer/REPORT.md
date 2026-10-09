# Saved-only review: logging capture repair

**QUALIFIED_ACCEPT** for exactly two test files, `756bdd3f…` and `00679ceb…`. No application/config/migration change is proposed. All 19 root originals and the READY hash `179eff40…` match; all 242 opaque app-file hashes match primary, OFF and ON. All 34 current source pins and immutable STOP match.

The first native core failure is a test-capture state failure: the original ordinary ValueError rethrow and audit assertions pass, but no pipeline Traceback is captured. Alembic invokes `fileConfig` with its default `disable_existing_loggers=True`, while its configured logger keys omit the named application loggers. The native disabled boolean was not retained, so this is a source-backed cause qualified by a synthetic predisabled-state replay, not a new actual migration experiment. Original failure seal `cdc2f531…` is immutable; the separate clarification `bfe73ed1…` gives JsonFormatter lines 87–88.

Root's saved OFF/ON runs have the same 29 ordered unique IDs: OFF **28 PASS / 1 P6 FAIL**; ON **29 PASS / 0 FAIL**, one warning each. These are 6 diagnostic groups + 2 owned-SQLite persistence cases + 21 existing parameterized hop cases. DNS/connect/listen/child guard counts are zero. Ruff/format for two files pass; mypy reports success with two annotation-unchecked notes.

The scoped fixture explicitly enables named logger capture and restores it through monkeypatch/caplog teardown. P1/P2/P4 now require a real fetch WARNING. Both in-memory and actual SQLite/API P5 require pipeline **and** worker ERROR records naming QueryPrivacyError with no traceback. Every previous privacy/controlflow/persistence/API assertion remains. P6 replaces its weak any-Traceback check with one exact pipeline ERROR, the same ValueError in `exc_info`, and a JSON-formatted Traceback. Existing hop bodies and all unchanged definitions remain exact.

This accepts the test-only repair for fresh native verification. It does **not** fix or certify migration logging policy, PostgreSQL, production logging, privacy completeness or launch readiness. The first native queue remains failed core 7/8; full was NOT_RUN. No tests/runtime/Git/network/DB operations were performed by this peer.

Peer metadata history: the first undelivered subgroup classifier was incorrect; exact saved XML classnames now independently yield 6+2+21. Its initial files remain intact at `a-log-capture-repair-review`; no source, raw outcome or verdict changed, and no replay was rerun.
