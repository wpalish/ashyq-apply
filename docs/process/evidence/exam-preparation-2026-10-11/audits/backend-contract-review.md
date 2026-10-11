# Independent backend preparation contract review

**Date:** 2026-10-11. **Verdict:** `STATIC_REVIEW_QUALIFIED_FOR_LOCAL_GATES`. No confirmed production-code blocker was found in this bounded source review. **Native tests, migrations and runtime by reviewer:** `NOT_RUN`. UUID race response behavior and HTTP/account deletion of actual practice rows remain runtime qualifications described below; they are not claimed proven by static review.

This is the new exam-foundation contract review, separate from the earlier quota-stopped privacy acceptance. It does not resume that work or establish privacy acceptance, deployment, admissions/search quality or an official exam score. Reviewer `/root/audit_search_logic` wrote only this external document; root is the source/Git integration writer. No app/source/Git changes, test execution, runtime, provider/LLM/search call, protected payload/labels or heldout reads occurred.

## Exact sealed packet and source binding

Proposal root: `exam-preparation-2026-10-11/proposals/backend/`.

| Binding | SHA256 |
| --- | --- |
| `source-pins.json` | `ff1ae9b0875b02127c73d363ba86fc88b839560ef5048d501cadcfbed0b7c3fe` |
| `artifact-manifest.json` | `db6fff1f08e4a5a1e108d185e8b7274090577092fe66458be7c79d02767a5306` |
| `proposed-backend.patch` | `8eabf8f066d49542a395641a36e4508ff3bc94de1d0bede672d9022b27507a9b` |

Independently checked all **25** manifest entries for byte length and SHA256, all **15** proposed after-hashes, all **five** existing source preimages, absence of all **ten** new paths, and all **20** pinned ordinary dependencies: **zero mismatches**. The source root was `integration-2026-10-11/source`; the packet's `11091904` HEAD is parent-reported, not a Git check by this reviewer. Eight read-only `static-tree` context copies matched the owned source byte-for-byte. Native migration revision-link inspection found a single existing head `d8e412c6a901` across 19 migrations, matching the proposed migration's parent; no database migration was run.

| Proposed repository path | Read coverage | Exact after SHA256 |
| --- | --- | --- |
| `backend/app/api/routes_preparation.py` | Full 330 lines, also read in the preceding curriculum review; same pin | `f98fdd452cc4d98432c24530ac5d34558ffeecb697bf872c0dcfbc8d111944cc` |
| `backend/app/payments/preparation.py` | Full 43 lines | `03464423ce2b0a7c917a38a89e497fdf287ee589c86118ea470af9a2a2e0ac80` |
| `backend/app/models/study.py` | Full 35 lines | `7852a20d8235978e5cfaeb9828110a3df7ea79f153c47427745aac10cb3591ea` |
| `backend/migrations/versions/f1a2b3c4d511_study_attempts.py` | Full 51 lines | `04a6bfd6062e35f9dea5c3841a09e821e946f727ea66e01a78fc6f5ad0153ba6` |
| `backend/app/models/applicant.py` | Full 46 lines and full before/after diff | `5f5d98c1f4c7555ba444ed1028184fdc5e8c62f4d868d000bc014be95d429464` |
| `backend/app/models/__init__.py` | Full 99 lines and full before/after diff | `5cc3113f9c763607fff33e1e413aa6380a4992f58f2a7d8fa77bbc7db27539b7` |
| `backend/app/api/routes_billing.py` | Full 219 lines and full before/after diff | `2b758fa375fe980a4c655040f1b78685394ba8f1a1e40870db975285b205aa7a` |
| `backend/app/api/routes_profile.py` | Imports/create/list lines 1–90 and validation/export/delete lines 210–411; full before/after diff | `80c7894848d35202ab8e428e06f6991e18b10cff04627021b5a4ffdfcd1bcad0` |
| `backend/app/main.py` | Imports/startup/registration lines 1–125; middleware lines 180–314; full before/after diff | `e5e8a5a6ddcc158792658c901d59c5ceef3af546b3f9bc5845be89008e118eff` |
| `backend/tests/test_preparation_api.py` | Full 677 lines, every fixture and assertion | `9454636eff5a601b512601ecd65a75898a4849f81fb08a0b40010a4dfc4cdd46` |
| `backend/app/domain/preparation.py` | Full 213 lines in preceding curriculum review; final pin rechecked | `c66f4a31a656f2e664bf90b75e6130085ab31471335103057ca7a610c74cfcc4` |
| `backend/app/preparation/catalogue.py` | Full 375 lines in preceding curriculum review; final pin rechecked | `8ca74f40b88df74a27bc5b0d5aa52d5e60ce5b5417f4e37c049690b47d716169` |
| `backend/app/schemas/preparation.py` | Full 143 lines in preceding curriculum review; final pin rechecked | `8cae2435eda20de914313aaff734a28790dd3a0e7d2784559e00bdc4ac0500aa` |
| `backend/tests/test_preparation_domain.py` | Full 203 lines in preceding curriculum review; final pin rechecked | `6234322046285b8e283e7cc0bcc23fb8ca71283c8d39da6900c5069b96d2fa4a` |
| `backend/app/preparation/__init__.py` | One-line module docstring | `5507da4c7bd5c9a1b5bbff14d9e47aac27b7ef3398d9cba297481255046db01e` |

The five existing-file diffs contain only import ordering plus preparation registration, optional entitlement DTO/projection, StudyAttempt registration/cascade, and case-filtered export additions. Existing create/delete, payment ordering, subscription quota consumption, startup and middleware function bodies were not changed.

Context coverage: ordinary tenancy helpers, entitlement reads, Subscription and timestamp models fully read; subscription read helpers lines 1–86; security principal/session behavior lines 110–245; account deletion lines 345–438; DB session dependency lines 150–177; native PostgreSQL/configuration fixture source lines 30–112 and 234–262. Context hashes are bound by `source-pins.json`, except unchanged account deletion (`e7ec09868bbe8c61b6ea97c05b65ca15f96843427bf09002af6bed36f4f4f1d9`) and existing parent migration (`7dd9e92fbb42fbdb3320490fe6747be011bb6e31ec72dadd1100af04815e262f`), independently hashed. No historical fixture payload was opened.

## Contracts verified in source

| Area | Actual contract and implementation | Static conclusion |
| --- | --- | --- |
| Tenant and authentication | Every case endpoint depends on `get_principal` and calls `owned_profile` before lesson/history/replay/plan operations. Ownership is by current principal organization. Foreign/missing case returns the same 404; selected result joins through that exact case's ResearchRun. | No case-ID/attempt-ID route bypass found. Public catalogue alone lacks the principal dependency, intentionally. Existing principal validates active user, membership and unexpired session. |
| Preparation entitlement | Helper queries only current organization's ACTIVE/EXHAUSTED subscriptions, requires both timestamps and `starts <= now < ends`, and ignores case quota/entitlements. Pending, cancelled, expired, missing dates, future starts and reversed ranges do not grant. | Preparation access remains available at zero research quota during the started term; no hidden activation, retirement or consumption. Payments-disabled access explicitly says development-only. |
| Research entitlement | Plan uses the existing case-full entitlement independently of learning subscription access. Locked research yields no checks/claims. | A paid practice term does not unlock a research result; a case unlock does not create a practice term. |
| Input and feedback | UUID/version/lesson/answers are bounded DTOs; full exact known-question/choice validation precedes persistence. Answer keys/explanations are absent from catalogue/lesson and returned only for a complete submission. | Invalid submissions persist no practice rows. No free-text essays/audio/official score mutation is introduced. |
| Idempotency | Uniqueness binds `(profile_id, client_attempt_id)`. Digest binds lesson/version/canonical sorted answers; the same UUID in another owned case is independent. Existing receipt is checked before entitlement, so same-payload historical retry works after expiry; a changed payload is 409. | Sequential behavior is source-consistent. Existing immutable receipt is not replaced by new answers. |
| Insertion race | `submit_attempt` catches commit IntegrityError, rolls back, refetches by case+UUID, replays matching digest or returns 409 for changed payload; unrelated integrity error rethrows if no winner exists. | Standard source closure is present. Actual racing requests and this HTTP recovery path are not proven by the proposed test assertions. |
| History and export | Progress reads only owned case attempts, latest-first with deterministic ID tie breaker; totals span all attempts, while completion is current-version submission only. Export filters the same case, serializes complete attempt receipts, and adds a count. | History remains own data after expiry. Limit changes returned rows, not aggregate totals. No subscription gate blocks own history/export. |
| Deletion | StudyAttempt has non-null profile FK with `ON DELETE CASCADE`; profile relationship uses `all, delete-orphan`, `passive_deletes=False`. Profile HTTP deletion uses ORM `session.delete(row)`; unchanged sole-owner account deletion loops profiles and deletes them through the ORM. | Practice rows follow the existing case erasure path even when SQLite FK enforcement is off. Shared-organization account deletion retains that workspace, as the existing account contract specifies. |
| Reads and audit | New GET handlers and access helper query only; ClaimOut freshness changes are projections, not persisted ClaimRow updates. New attempt POST writes StudyAttempt only; no practice answer/feedback AuditEvent is added. | **No new preparation/quota/entitlement/content writes on reads.** This is narrower than “no database writes anywhere in a GET”; see inherited auth qualification below. |
| Network and registration | Main adds the route import/router only; new preparation modules contain no fetcher/provider/LLM/job-enqueue/startResearch call. Subscription reads do not call `consume_for_case`. Main startup reconciliation and existing security middleware are unchanged; all `/api/` responses retain no-store handling. | No new search/provider/worker invocation path introduced by this foundation. Existing application startup remains a separate runtime behavior. |

## Precise qualifications sent to root/author

1. **Race coverage gap, not a confirmed app defect:** `test_grading_replay_conflict_and_progress_are_case_scoped` proves sequential replay/conflict. `test_migration_schema_and_unique_payload_binding` inserts a duplicate directly and expects a DB IntegrityError. Neither puts two API submissions past the initial lookup or exercises the handler's rollback/refetch winner path at `routes_preparation.py:151`. Do not describe those assertions as actual concurrent HTTP proof. Runtime race qualification must distinguish same canonical payload (same receipt/one row) from changed payload (winner plus 409/one row), with SQLite and real private PostgreSQL behavior retained. A source claim of database uniqueness alone does not prove the response path.
2. **Inherited auth writes are intentionally separate:** `get_optional_principal` may create the development principal, delete an expired AuthSession or refresh `last_seen_at` on a GET. These unchanged security operations predate the proposal. The new learning reads do not modify subscriptions, practice progress, profiles, research or entitlements. No legacy authentication change is requested, and no broader zero-write GET claim is made.
3. **Deletion coverage is currently ORM-level for new rows:** the new test directly deletes the profile ORM object, including SQLite FK-off behavior. Source inspection shows HTTP profile deletion and sole-owner account deletion use the same ORM mechanism, but the new test does not itself call those two HTTP paths with a StudyAttempt. Existing native deletion assertions remain unchanged. Their later execution is a separate lifecycle gate, not an assertion that this reviewer has already observed the new rows disappear through HTTP.

These qualifications were reported before native execution. No hidden skip, fixture substitution, source weakening, invented empty data or new provider permission is recommended.

## Prepared controls and minimum local-gate requirements

Full test source has been inspected. Static parametrization is **46 API cases × SQLite/PostgreSQL = expected 92**, plus **30** pure domain cases (preceding curriculum review), expected **122** total. This is a source calculation, not pytest collection or PASS. The API controls cover: public metadata and absent answer keys; zero quota ACTIVE/EXHAUSTED access; invalid/unstarted terms without subscription mutation; explicit development mode; foreign/missing cases; invalid answers/version/UUID/extra text; grading/sequential replay/conflict/history; expired-term replay/new denial; independent case UUIDs; preserved source quote/scope/ID-or-URL references; stale/conflicted/unknown plan; locked and foreign results; ORM deletion with SQLite FK off; migration FK/uniqueness; progress aggregate/limit; exact start/end boundary; downgrade/up with existing profile retained; auth-enabled unauthenticated refusal; foreign organization subscription denial.

The fixtures run real registered routes and migrated engines, without entering lifespan/startup reconciliation. Their Python socket/DNS assertions preserve AF_UNIX and record attempted IP activity; they **do not themselves fence libpq or descendants**. The existing reviewed outer network guard, owned Unix PostgreSQL, synthetic settings/env/export/cache, runner lock, source/evidence binding and cleanup are required. A skipped PostgreSQL parameter is not a PostgreSQL result.

Before acceptance root must apply only the exact matching preimages/new paths, bind new source pins, run unchanged prepared modules with real migrated SQLite and private Unix PostgreSQL, retain actual collection/results/zero skips/guard and cleanup evidence, then satisfy required unchanged backend native/full coverage gates and frontend lifecycle/DTO integration gates. Keep UUID race response and HTTP/account deletion qualifications explicit until actual controls establish them. No additional broad audit was started by this reviewer. Author-reported Ruff/format/focused mypy success is static evidence, not a replacement for these native gates.

**Search quality remains `NOT_MEASURED`; stopped-provider and closed-evaluation boundaries remain unchanged.** This review does not make a complete-course, official-score, admission or production-readiness claim.
