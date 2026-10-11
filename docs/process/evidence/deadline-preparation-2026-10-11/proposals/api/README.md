# Native study-schedule API controls — external proposal

Status: **NOT_RUN**. Only Python AST parsing was performed; no application import,
provider, server, database, Git operation or native runner was started by the author.
Root is the sole source writer and gate executor.

Proposed path: `files/backend/tests/test_study_schedule_api.py`.
SHA256: `52204a8c5c897b3a327d1f74a6e8225a84614c89e519c31ef31a124650b7b194`.
12 test functions, 20 parametrized scenarios and **40 expected native cases**
after the inherited SQLite/PostgreSQL parametrization; 81 static assertion nodes.
These counts are predictions from AST, not a collected or passed test receipt.

## Prerequisites

- Root applies the schedule schema/domain proposal and registers the schedule
  API/model plus the migration `a9e5c14d2021` after `f1a2b3c4d511`.
- Existing `tests.test_preparation_api.prep_lab`, `grant`, and `url` remain present.
  `pytest_plugins` registers `prep_lab`; fixture variables are not imported into
  the test module, avoiding the prior F811 import/argument collision.
- The native fixture uses migrated synthetic databases and an owned private
  PostgreSQL cluster; root's outer isolation/network/cleanup guards still apply.
  TestClient intentionally does not enter application lifespan.
- Root runs the actual native static gates; external package classification may
  require native import ordering/formatting. No static gate PASS is claimed here.

## Contracts exercised

Owned GET/PUT and foreign-or-missing 404; independent owned-case revisions;
ACTIVE/EXHAUSTED term with zero research quota; absent/expired/future/pending/
cancelled/incomplete terms; retained expired history with write402;
first-create1/update2/completion3 and stale409; structural completion reset422;
future baseline and arbitrary completion422; exact exported personal settings;
unchanged full academic payload, profile.updated_at, subscription/quota, research,
jobs, orders, entitlements, attempts and audit counts; actual profile HTTP deletion
with SQLite foreign_keys off; migrated unique profile/FK cascade/check constraint;
real downgrade/up preserving the existing profile and preparation-attempt table.

Dates derive from `utcnow()` in UTC: first sitting +60 days, entered deadline
+90, personal buffers5/2/7 days. Baseline date is today; it need not be before
the calendar start. Revision/completion assertions use actual returned task IDs.
Changing structural settings invalidates old task IDs; the test explicitly
requires422 before a cleared save, then uses a task from the new returned calendar.

## Qualifications

These are synthetic local native HTTP contracts. Sequential stale/replay controls
do not prove concurrent HTTP isolation, a real paid account, institutional score
receipt, exam booking, score improvement, complete curriculum or production.
GET recomputes dated calendar status without writing preparation/quota state;
inherited authentication may still have its existing identity/session effects.
The test author also reviewed persistence seams; this is not a blind acceptance.

`source-pins.json` records the exact proposed test and native dependency bytes
captured for preparation. Root must rebind final integrated bytes and receipts.
Follow-up static review now binds the sealed schema/domain/test proposal and
confirms subtraction-underflow validation; see `audits/backend-schedule-review.md`.
No API-test runtime or native whole-tree static receipt is claimed here.
