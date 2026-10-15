# Next finite core increment: read age and actual research inputs

Current source4d006602. Today FE848/82 exact local gates; integration not yet run. Existing old live/provider/model/security/heldout/main/prod boundaries unchanged, root solo.

## Reuse and minimum storage decision

ResearchRun already has settings_snapshot; runner.run_to_decision replaces this JSON and _save preserves durable budget ledger under the existing fenced heartbeat transaction. Reuse a closed dedicated profile_input_observation_v1 namespace with explicit preservation in this lifecycle. No new SQL column/migration/third action-progress model. New start_run creates a pending marker without inventing an observed input. Existing runs with missing/corrupt namespace remain unknown; never backfill them from today's profile.

At actual runner checkpoint, normalize actual self.profile through ApplicantProfileIn and hash section JSON locally (context, academics, activities, achievements, preferences, funding, weights, weights_override). Exclude only explicitly local display_name and envelope identifiers/timestamps. Never log profile values/digests or send them outward. The first worker observation replaces a genuine pending marker. Further distinct observed input while retaining the run marks mixed permanently and keeps changed-section union; A→B→A cannot claim current solely on matching digest. Preserve metadata in run_to_decision snapshot rebuild/read-ledger merging. _save writes it only inside the existing heartbeat lease fence/transaction; lost lease rolls back, refusal/cancellation unchanged. Legacy missing/corrupt metadata is not rewritten. Pure domain module performs no I/O.

Read-only RunView companion field reports unknown/pending/current/changed/mixed and named changed sections, plus read timestamp, without profile values/digests in normal UI. It compares current normalized saved owned profile to actual observed metadata. Unknown historical run remains accessible. No automatic re-run, reset, ranking mutation or provider call. Retry that uses changed inputs retains mixed review state. Re-rank adjusts stored ordering but does not silently certify current requirements.

## Source-age projection

Reuse existing age_days/is_stale/apply_freshness with one authorized read timestamp. Original stored ProgramResult/Claim/receipts/bindings/ranking remain exact; project a detached ProgramResult read subtype with explicit freshness/read-assessment status. Recompute ClaimOut age/is_stale and only VERIFIED_CURRENT→POSSIBLY_STALE at native windows, preserve conflicts/SUPERSEDED. Review summary/detail/claims/shortlist/exports consumers individually: response projection is current observation, personal full export remains original history plus explicitly named read context. Do not overwrite payload or enqueue reextract/network. Existing G1/preparation native freshness behavior already recomputes age and remains unchanged.

## Tentative finite paths before exact grant

backend/app/domain/profile_input_provenance.py (new); backend/app/domain/result_read.py (new); backend/app/schemas/research_read.py (new); backend/app/api/routes_research.py; backend/app/api/routes_results.py; backend/app/pipeline/runner.py; backend/tests/test_research_input_provenance.py (new); backend/tests/test_result_read_freshness.py (new). Inspect actual read consumers before final path grant. Frontend typed RunView/read qualifiers + common case-bound notice follow after accepted backend; frontend/src/types.ts is a consumed native contract file and requires fresh actual consumer/full map qualification.

## Meaningful acceptance

Pure section normalization/display-name exclusion, old malformed namespace unknown/no overwrite; genuine pending actual A observed; changed B→A retained mixed; unchanged current vs edited named sections; lease-loss rollback of profile observation and budget ledger/partial programme observation; no raw/outbound PII; native authorized API GET/results projection at exact age boundary and CONFLICTING/SUPERSEDED; unchanged stored payload/receipt bytes and no DML/fetch/rerank from reads; old run no backfill; ownership/expiry/history/export. Native explicit SQLite/PG fixtures where persistence matters, fresh static/mypy and both full92 gates after backend changes. No source/config/Git changes during owned frozen run; all first failures retained.

After this: fresh native Demo/Auth browser→API→DB core scenario with two chosen programmes, manual and source-bound document, application, Today/exact editor, report/context/history, reload/second login/second browser, export/delete, CAS and lost response/cap64; four widths320/768/1024/1440. Optional course tests separate. Search quality/release remain unaccepted until authorized gates; do not present FE848 or old full5807 as product acceptance.
