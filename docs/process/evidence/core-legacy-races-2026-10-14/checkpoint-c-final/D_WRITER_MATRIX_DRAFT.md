# D writer matrix (read-only preparation; NOT APPLIED)

- ProgramResultRow: identity id + run_id, owner via ResearchRun.profile->organization; no row revision today. Scalar decision/reason/notes/date plus same JSON fields. Source rankings and assessment coexist with personal fields.
- API set_decision routes_results287-324: full JSON read-modify-write + four personal scalars + audit, commit; no row lock/CAS. decision.notes nonempty may replace notes captured from older UI.
- API set_notes routes_results334-367: full JSON read-modify-write + notes scalar + audit, commit; no row lock/CAS.
- API rerank routes_results630-703: reads every row, modifies fit/ranking, store_result full JSON/score/bucket; persisted variant shares profile CAS/audit transaction; nonpersisted still writes results. No result CAS.
- ResearchRunner._persist_result runner1616-1662: query dedupe key, update existing via _update_result; new row insert/flush/evidence. Keep unique(run,dedupe) and run deletion/lease protections.
- ResearchRunner._update_result runner1664-1685: carries personal scalars from its loaded row into derived result; can be stale. store_result replaces JSON + ranking sort fields. Called in verification/scoring/refresh/partial reread/document paths.
- store_result runner2091-2108: shared full JSON/score/bucket setter; transient unit rows also use it; no transaction ownership itself.
- Worker constructs runner with actual profile and lease; runner._save heartbeat CAS rolls back whole current transaction on lease loss. No late parent mutex may be added under existing job/run locks.
- source_scanner.reextract_page invokes the same runner; source_scanner payload assignments322/330 are ClaimRow, not ProgramResultRow.
- Readers: results/detail through result_read(now), summary/export/shortlist read stored row/scalars, G3 owned target reads. Mutation responses currently historical raw result; fixing read transport must keep free/full access.
- Store decide/saveNotes currently independent async whole-row replacement; one resultVersion increment per arrival is not server order. saveNotes/decide catch -> fulfilled void. Shortlist note/rejection closes unconditionally; note text replaced on reopen.

Proposal under review: additive ORM version_id_col on result rows to guard every ORM writer (including background), API fresh write + current authorized row/revision, immutable note/decision command acceptance in existing audit metadata, row-aware read DTO revision/freshness, common per-row client order, typed accepted/failure/unknown/conflict and retained original intent/text. Preserve field intent separation (decision must not carry an old note implicitly). No source grant yet; profile N09 full gate first. Need controlled true-native races and original assertions.
