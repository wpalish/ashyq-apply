# G3 storage UUID-column repair 1

**SEALED EXTERNAL TEST-ONLY PROPOSAL — NOT_APPLIED / NOT_IMPORTED / NOT_COLLECTED / NOT_RUN.**

The first five-file seal was written just before root identified this concrete source mapping defect. First packet, its original `2600ce96…` test blob and all four reviewed non-test postimages remain immutable. This separately authorized exact-one overlay is the test postimage to apply together with the first packet's four application postimages.

Native `WriteUuid` retains a typed `UUID`; the new storage column is `String(36)`. Exactly three test setup assignments now use `str(...)`: `event_values(receipt)` and both deliberate UUID-collision assignments. Canonical strings therefore bind to the physical column and compare to freshly read String values. Typed receipt-to-receipt UUID assertions remain unchanged. No assertion, function, fixture, guard, test count, model, migration or runtime contract was removed or weakened.

Producer checks: external source AST parse and exact three textual substitutions only. Seven functions / 19 syntactic cases per database / 38 intended cases remain NOT_COLLECTED and NOT_RUN. No Ruff/app import, database, test execution, network, primary/lab/helper, Git or HANDOFF actions occurred during this repair. Root is the sole application and runtime writer. Source review is not SQLite/PostgreSQL acceptance.
