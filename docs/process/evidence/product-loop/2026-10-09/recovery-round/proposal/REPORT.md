# Find recovery and Documents hint — external proposal

Prepared 2026-10-09. Status: READY_FOR_INDEPENDENT_REVIEW, NOT_APPLIED. Parent owns primary changes and native gates. This packet modifies exactly two UI files and two existing test files; no styles, helpers, backend, schema, storage or routes.

The native defect is reproducible: ShortlistScreen originally does not read `run`, so zero returned rows always offer Start research even for an existing stopped run. App.tsx:435 already supplies onProgress as navigation to Progress. HomeScreen.tsx:10–13 and DocumentsScreen use stale/cancelled/stage/job attention before active state.

The proposal reuses those state predicates. With an existing run and zero returned results it presents the run's attention/progress/review notice and an optional **View research progress** callback. No run retains the existing Start route. With returned results, only active/attention runs show the same notice above existing rows. It is based on all results, not locally filtered rows. No mutation or effect is introduced: filters, sort, comparison selection, unsaved notes, choices, unknown values and catalogue remain in their existing code paths. Progress is called only by explicit click; callback absence does not produce an inert button. The text explicitly treats zero results as unknown, not proof that no programmes match.

ResultDetail.tsx's no-checklist text now names **Chosen by you** and **Considering** in Plan. Both are accepted by the native collection contract: routes_research.py:480–503 and runner.py:1409–1419 select approved/maybe. The hint directs to existing Plan collection without demanding another approval or adding collection actions. Returned checklist display is unchanged and the hint states that collection does not establish application readiness.

Validation on owned frontend copies, installed dependency links, owned cache, denied sockets/listen/HTTP/fetch/DNS:

- Final actual components: **54 PASS**, no errors/skips; **35 existing cases** remain passing and **19 appended cases** cover state/callback and retention semantics.
- Same final tests on base UI: **38 PASS /16 expected RED**, zero errors/skips; all 35 old cases pass. The three new green controls preserve no-run Start, locally filtered-zero behaviour and returned checklist rendering.
- TypeScript `--noEmit` and selected four-file ESLint: exit0. AST compatibility confirms all **27 old test templates** unchanged; native rows/filters/clearFilters/decideRow/renderTable, six other ResultDetail functions and real checklist return body unchanged.
- Six denied-transport process receipts record zero attempts. All **98 primary frontend file hashes**, selected base dependencies and provider STOP remain unchanged before/after.

History retained: first ON53PASS/1RED and OFF37PASS/17RED. The shared failure was a new test expecting plural “results” when the unchanged native counter correctly uses singular “result” for total1. Original test bytes, logs and JUnit are preserved; only the new expected literal was corrected. The new checklist fixture was also filled with its native required fields. App proposal stayed unchanged across attempts.

Limitations: these are frontend mock/API tests, not runtime research, provider availability or quality evidence. Primary apply, native doctor/core/full, server, browser/viewport/reload, auth, backend/API/SQL, production and deployment are NOT_RUN by B. Existing catalogue mount reads the mocked catalogue once; no real request occurs. Runtime copies/cache/dependencies are excluded from the sealed plaintext selection. No blind expert, gold, scorer or labels were opened. Shared runner lock observed by root does not affect this isolated noports proof; root waits for its own gates.

Authoritative source pins: proposed-source-pins.json; base contract pins: base-source-pins.json; complete command/result provenance: execution.json, focused-results.json, correction-history.json. recovery.patch is the exact four-file diff.
