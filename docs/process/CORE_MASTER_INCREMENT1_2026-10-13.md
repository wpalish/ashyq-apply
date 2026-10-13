# Unimatch core — increment 1

Status: implemented, locally checked, **WIP / full gate not accepted**.

Baseline: `892fc5e5` on `task/admissions-actions-today`; root only.

The live discovery path records public programme-page metadata immediately after existing Fetcher / redirect-site / page-type / requested degree and subject checks, before subsequent awaits. The runner saves it through the existing cancellation and job-attempt fence. Ordinary enrichment timeout retains the observation without inventing requirements, claims, compatibility or an assessed result. Owned RunView and profile export read the same bounded projection; invalid storage is explicitly unavailable. Null old rows stay readable. The progress screen shows saved pages separately from results, with EN/RU/KK wording. Additive migration `e8b72e902025` follows `d7a61e902024`.

## Evidence

- Seven native static/frontend phases passed: mypy408, frontend732 tests in66 files, build; existing9 lint warnings. Frontend bytes remain exact after the later test-URL-only repair. Current backend static must be rerun on repaired test bytes.
- Focused1: 287 passed /6 failed, all6 new HTTP tests used a nonexistent route prefix. Corrected to actual `/api/runs`; original raw evidence retained.
- Full2 SQLite-default phase: **5763 passed /2 failed /0 errors /0 skipped**, coverage94.32577085208166%. Native fixtures include SQLite and PostgreSQL. New observation tests all passed.
- Remaining2 failures are existing historical G3 migration tests: native seed uses the current ResearchRun mapper after rollback to a schema lacking programme_observations. This is an explicit fixture compatibility repair, not permission to skip or weaken migration checks.
- Guard evidence: outside attempts0, startup failures0,13 receipts,1732 owned private PG connection events, app not preimported, source unchanged during the gate, IPv6 restored, owned shutdown/runtime removal confirmed. PostgreSQL-default full phase did not run after failure.

## Boundary

Search quality NOT_MEASURED; live/provider/heldout/model/security stops unchanged. Main, release, deployment, production, user DB, paid operations and containers untouched. The catalogue wrapper still has its old300-second timeout; the quality protocol120-second budget remains a distinct unresolved gate. G3 remains the chosen single source of durable action progress. Commands/recovery forms, document/application completion, Today navigation, stale profile/source findings and integrated Demo/Auth acceptance remain work to do.

Raw originals and helper provenance: `docs/process/evidence/core-completion-2026-10-13/checkpoint1/INDEX.json`. This is a checkpoint, not product acceptance.
