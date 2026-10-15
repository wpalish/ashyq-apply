# G3 storage source proposal 1

**SEALED EXTERNAL PROPOSAL — NOT_APPLIED / NOT_IMPORTED / NOT_COLLECTED / NOT_RUN.**

Root is the sole application, lab, Git, HANDOFF, helper and runtime writer. This package contains exactly the five source paths authorized in `G3_STORAGE_SOURCE_GRANT.json`. No migration, database operation, app import or test collection was performed by the authors. Source-only syntax/AST and bounded Ruff **format** receipts are retained; they are not runtime acceptance.

## Exact implementation

| Path | Change |
| --- | --- |
| `backend/app/models/admissions_actions.py` | Two native `Base` classes: `AdmissionsActionsCurrentRow` and `AdmissionsActionsEventRow`; explicit receipt ID/time, bounded revisions, exact schema, closed 12 kinds, profile-only CASCADE FK and own revision/UUID uniqueness. JSON/PG JSONB; no clock/UUID defaults or onupdate. |
| `backend/app/models/applicant.py` | Only one TYPE_CHECKING import containing the two classes and two delete-orphan relationships with `passive_deletes=False`. |
| `backend/app/models/__init__.py` | Only the two explicit model imports/exports. |
| `backend/migrations/versions/d7a61e902024_admissions_actions.py` | Additive two-table migration, down revision `c3e71d902023`, root assigned after its saved fresh one-head receipt. Downgrade drops only the two new tables. |
| `backend/tests/test_admissions_actions_concurrency.py` | Migrated SQLite/private PostgreSQL controls using actual native fixtures and no-lifespan client; no public G3 writer or API race proof. |

The composite profile/revision uniqueness provides the ordered history index. No native data, sidecar, source, entitlement or actor backfill; no User/Organization/result/source or current-to-event FK. Earlier event/actor JSON remains independent of source removal or a deleted member while its own Profile survives. Existing registrations reconstruct exact preimages when the permitted additions are removed (`REGISTRATION_RECONCILIATION.json`).

## Meaningful proposed controls

Seven test functions, including 13 parameterized physical rejection cases: **19 syntactic cases per database / 38 intended cases**, not collected or executed by the authors. The native fixture remains parameterized for both SQLite and PostgreSQL; PostgreSQL is not skipped for the SQLite-only extra branch.

1. Populate native parent with marked calendar, learning sidecar and G2 current/history; perform real parent→new-head, downgrade and re-upgrade. Native rows remain byte-equivalent; new storage begins empty and has no backfill.
2. Persist six actual pure G3 transitions: application, binding, personal document report, applicant submission declaration, correction and rebind. Fresh Sessions check full headers, canonical payloads, timestamps, state/receipt/request hashes, affected associations and full typed history. The original report survives rebind with the separate previous-binding annotation and `not_performed` official provenance.
3. Execute actual SQL constraints: both PKs, own event revision/UUID uniqueness, both revision zero/overflow cases, both schema checks, closed kind and both parent FKs. PostgreSQL overflow may raise native `DataError` before the check. Rollback preserves native rows and the old pair.
4. Permit the same client UUID/revision for a distinct owned Profile without changing the first Profile's bytes.
5. Flush an actual current UPDATE, then fail a duplicate event insert; rollback restores the old complete current/history pair in a fresh Session.
6. FK-on Core DELETE and native case DELETE preserve sibling full rows; isolated SQLite also exercises the native ORM path with FK temporarily OFF, restores the policy, and checks no orphan.
7. Sequential native authenticated account deletion erases sole case rows while retaining the shared case, all G3 headers/payloads and original pseudonymous ActorRef after the leaving User is gone. Assertions use fresh Sessions and actual password/session/membership seams.

## Acceptance boundaries

SQL constraints protect storage structure. Finite typed JSON, duplicated column/body equality, full history/self-hashes and original immutable ACK are enforced by the existing pure contract and future readers/writers. SQL/ORM alone is not cryptographic immutability. Synthetic test setup is not a G3 CAS, replay, fence, write-versus-delete or public API implementation.

G3 API/export/Today/UI, physical G3 writer races and release are the next bounded root stages. This packet changes no entitlement, provider, Fetcher, score, quota, official fact, source authority, security-controller or old STOP policy. Root's earlier pure-stage qualification does not qualify this new storage migration or these unexecuted tests.

## Producer evidence and review

- `FORMAT4_RESULT.json` / `FORMAT4.log`: external-only AST plus Ruff format of the four model/registration/migration paths.
- `FORMAT_TEST_RESULT.json` / `FORMAT_TEST.log`: external-only AST plus Ruff format of the finished test path; AST unchanged.
- Both operations used the existing approved interpreter, native 100-column Ruff config, OS network denial and the existing nontruncating shared lock. No app import/test run/database action.
- Four reviewed source SHA values remained unchanged while the fifth test file was completed. Source-only root/peer review found no concrete defect in those four; this is not a database PASS. Author's full test source read found no concrete fixture/API mapping blocker; runtime remains unknown.
- Native grant pins and all two preimages remain byte-exact, all three new primary paths remain absent. `FINAL_SOURCE_PINS.json`, original blobs, five diffs, dependency receipts and this seal retain the exact provenance. Independently mutable peer reports are not seal members.

The first seal freezes the proposal only. Root independently verifies, applies and runs its prepared finite storage gates. No application, lab, helper, Git, HANDOFF or runtime bytes were changed by this author or its test-only child.
