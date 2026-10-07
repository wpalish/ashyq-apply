# Expert-500 Phase1 V12 — closed unscored, 2026-10-05

## Exact outcome

All ten fresh algorithm baselines and ten independent expert executions completed.
There was no shared model/provider/transport stop. The frozen reporter failed
**before seal and reviewed labels**, so V12 has **no admissible recovery score**.
This is not zero of62 and does not admit50-case batches. Heldout150 and signed
reviewed8 remain untouched. The original root and all earlier trials are preserved.

Source: `92dfdb6d4f1a4595865ea756f46b176ce0f6d891`.
Tag: `expert500-phase1-v12-2026-10-05-92dfdb6`.
Trial: `c78aacedd2db9ecc82588e6a0f8eba4840186d80205720c06d82ab1ac50cf613`.
Source CI:12/12 successful,4209 tests each SQLite/PostgreSQL, SQLite94.91%.
Algorithm:353 reads58 queries total; each within60/6/120s.
Experts:83 reads25 queries total; same60/6 ceilings, default Astra reasoning,
original absolute900s guard, truthful retained prefixes and unprocessed tails.

## Reporter defect

The unchanged reporter rejects Groningen with
`Descriptive wall ledger differs from recorded case timestamps`.
The parent samples `wall_elapsed_ms`, hashes `recorded-actions.json`, then samples
`finished_at`. Groningen reports901088ms; exact ceil(finished_at-started_at)
is901093ms. The intervening file hash can take more than the reporter's1ms
agreement requirement. All nine other pairs agree exactly; cumulative meters
are arithmetically exact. This descriptive metadata mismatch is not a new source
clock, effort limit or evidence value. The originals are not amended and the
frozen reporter is not rerun or loosened.

A separate hypothetical offline check substitutes only a copied descriptive
wall value in memory and stops unconditionally at the seal boundary. All ten
raw replay checks then reach that boundary. It creates no seal, reads no
reviewed labels, writes no original, makes no source/model call and grants no
primary acceptance. Its log remains explicitly hypothetical.

## Original expert endings

| Case | Ending | Reads | Queries | Accepted / recorded source actions |
|---|---|---:|---:|---:|
| aalto | explicit_commit | 8 | 4 | 12 / 12 |
| groningen | selector_timeout | 6 | 0 | 5 / 6 |
| delft | selector_timeout | 9 | 2 | 10 / 11 |
| vienna | selector_timeout | 9 | 3 | 12 / 12 |
| warsaw | explicit_commit | 10 | 3 | 13 / 13 |
| ubc | wall_guard_checkpoint | 8 | 3 | 11 / 12 |
| ntu | explicit_commit | 7 | 2 | 9 / 9 |
| hku | explicit_commit | 7 | 4 | 11 / 11 |
| toronto | selector_timeout | 9 | 2 | 10 / 11 |
| kaist | selector_timeout | 10 | 2 | 12 / 12 |

The wall result may include postdeadline receipt delivery and mechanical
finalization. Accepted checkpoints and source policies retain their original
coordinates and timestamps; no late source is promoted.

## Already demonstrated source and orchestration findings

- Groningen's explicit fee year is in the same table row's Year cell; the
  selected fee cell context omits that sibling. A qualification-page year is
  explicit in an adjacent styled heading label but omitted from DocumentIR.
- Nineteen consecutive qualification-note retries get an inappropriate Q4
  fee-year error. Those nineteen selector turns consumed321942ms; all21
  rejected turns together consumed373375ms. No rejected fact is salvaged.
- Aalto's eight page reads are robots-disallowed with empty saved bodies.
  Four discovery queries succeeded. This is access failure, not proof of
  unpublished facts. Search snippets are not authoritative evidence.
- Completed-three workflow envelopes average55.73–60.98s per source action.
  Source work is nested inside that envelope; selector process time is not
  isolated thinking time. A separate workflow for each action obstructs use
  of60/6 ceilings before the900s hang guard.
- Existing mixed-list controller plans stop subsequent searches after
  provider402/429 but can still execute a later page read. An unapplied
  prospective patch gates every later tool, retaining the first cause.

These findings are trace diagnoses outside the primary comparison. They are
not per-reference expert-only miss assignments or a40/62 measurement.

## Immutable evidence

`backend/evaluation/research/expert/data/runs.2026-10-05/v12-unscored/manifest.json`:
`7fcf689686fccedd89a0e16674ec796a6f1ddb763132b3f83e56f107f1ccc400`.

All2881 original-root records are per-entry SHA-bound and byte-verified inside
`original-root.tar.gz`, SHA
`b27bcc0f14f78c14b19e7a850401d4516d69eb6e490792d0f175c28fb47007e3`.
Nine additional original scripts/logs/observations/plans are copied verbatim.
The completed-three audit7-record manifest is
`495bd6e89179de0969fe1ed6209b151c5521071bb08678c3b64a5087a6b471de`.

## Prospective work

Capture one UTC completion instant after action-hash I/O; derive both
completion fields from it, with a delayed-hash regression. Review the isolated
literal year-context and mixed-list STOP patches. Any change is a new source
with fresh gates, neutral/OS proofs, immutable protocol and paired trial;
never overwrite or reopen V12. Retain reviewed62/threshold40, normal effort,
60/6,900/120 and free-only constraints. Deployment intent for the owner's
screenshot is still awaiting clarification; no Fly deployment/probe occurred.
