# G3 Today test-only repair 1

Status: SEALED_SOURCE_ONLY_NOT_APPLIED_NOT_IMPORTED_NOT_RUN_NOT_ACCEPTED.

Exact allowed path: `backend/tests/test_today.py`. The immutable original preimage is `cf5f797832b342f8cf375a5520872f6993390eea5e5d1032b7f3aedab4a81c2b`; postimage is `c01bb4683ba1deb4dfb6479b989ad8017adecb805ff61a727137414a7e39660e`. Source1/core/read-tests packets remain unchanged.

Four fixture/control lookups at original lines 97, 184, 258, 377 supplied a profile ID to `Session.get`, which looks up the generated `StudyScheduleRow.id`. The native schedule writer sets `profile_id` and generates a distinct row ID. Each expression is replaced by an explicit own `profile_id` filtered query with `.one()`; there is no fallback and missing/duplicate rows still fail the control.

Only those four expressions differ. Imports, native writer/model/configuration, all test functions, assertions, parameter values, and control scenarios are preserved exactly. The postimage round-trip replacement was verified byte-exact against the preimage. No AST, formatter, linter, import, test collection/execution, application/DB/runtime, primary/lab/Git/HANDOFF or network action was performed. Root is the sole application and gate writer.
