# G3 source-token join diagnosis 1

**SOURCE_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**. Inspected 2026-10-13 05:48:17 UTC.
Scope: root's finite diagnosis of saved focused-api2 source_unreadable failures; no broader audit.

## Concrete defect before the graph/proof adapter

At backend/app/api/routes_admissions_actions.py:1167–1197, _source_token selects columns from ProgramResultRow, ResearchRun and two aggregate subqueries, then uses implicit .join(ResearchRun) at1183 without a left anchor or an explicit predicate.

The claims subquery projects ClaimRow.run_id at1135; the conflicts subquery projects ConflictRow.run_id at1152. Both native columns are foreign keys to research_runs.id (models/research.py:160–161 and200–201). ProgramResultRow.run_id is the third such link at123–124. Thus the selected FROM set has several possible left sides for the implicit ResearchRun join. A correct single programme selection does not remove that SQLAlchemy join ambiguity.

The preview invokes this authorized evidence-token query **before** _source_bundle:
routes_admissions_actions.py:1972–1975. SQLAlchemyError is converted into the safe source_unreadable503 at2006–2007. The same token helper is used by current/Today, where the SQLAlchemy refusal becomes saved_unreadable. Root independently identified this query as the common failure origin. The saved short trace shows the public503 but does not contain the swallowed internal exception; this review did not execute/compile the query or claim a diagnostic run.

## Finite repair suggestion

For this one rows query, explicitly anchor its left side to ProgramResultRow and join ResearchRun by the native run FK:

- select_from(ProgramResultRow)
- join(ResearchRun, ResearchRun.id == ProgramResultRow.run_id)

Keep both existing explicit outer joins against ResearchRun.id, all same owner/selected-ID/decision predicates, aggregate claim/conflict filters (including literal run-wide result_id=None), field order, timestamp normalization, token domain and returned digest untouched.

This resolves the ambiguous left choice without an inner join to missing proof metadata, an empty-evidence fallback, a schema/fixture change, altered access, DML or relaxed provenance. It is a route-only query fix. The earlier metadata-only branch has no aggregate selected FROM set and is not part of this repair.

## Fixture/proof disposition

seed_source at tests/test_admissions_actions_api.py:133–189 intentionally stores a real own checklist column with omitted document scope and empty claim_ids. That means incomplete evidence; it does not itself justify source_unreadable. Existing native graph/raw-checklist/binding validation must remain intact. There is no evidence here authorizing a change to proof requirements, scope acceptance, fake official fixtures or graph labels.

## Existing evidence and next verification boundary

Saved focused run:
g3-execution/evidence/backend-focused-api2/20261013T053108459965Z

Its result records192 tests/48 failures/0 errors/0 skips, unchanged source and terminal cleanup. It is FOCUSED_DIAGNOSTIC_FAIL_NOT_FULL; the separate outer PostgreSQL phase is NOT_RUN, although the first phase's native test IDs include both migrated database fixture variants. Root attributes28 source_unreadable and10 saved_unreadable refusals to this helper; no claim is made that the remaining10 failures share this cause.

Root's next authorized native focused run can confirm own source preview/current/Today on both databases while preserving malformed/foreign/locked/refusal controls. A new source-only inspection is not a PASS or complete-product result. No new runtime, import, AST, DB, network/provider, source, Git, HANDOFF or helper operation was performed.

Current route SHA256:
31c445bb51eabc2e51f3e9d5f4a8114a748432af33a4f9a6a3b0e03b5329d983

All inspected source/evidence hashes are captured in the companion seal. All STOPs remain unchanged.

