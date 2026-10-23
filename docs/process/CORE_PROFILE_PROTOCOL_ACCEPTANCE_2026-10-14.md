# Profile protocol — current local qualification

> 15 October update: N10/N11 adjacent profile lifecycle failures were independently reproduced and repaired on executable9ca4d307. Current FE944 and real nativeDemo7/Auth7 qualify those transitions. See [N10/N11 qualification](PROFILE_LIFECYCLE_N10_N11_2026-10-15.md). Earlier gate records below keep their original scope; complete product/release acceptance remains OPEN.


Executable: `5364dab9665f5934fe21abcd19e2c1bb447daff4`; 14 October 2026. Root only.

## What works

Existing profile save/validation excludes server metadata and uses an actual captured revision. A stale whole-profile save cannot overwrite another client. Save/startRun/explicit persisted rerank share the write path; nonpersisted rerank retains its default. Current normalization/ACK publishes before optional metadata. Failed/conflicted/unknown save does not start research.

An original UUID/body/base remains in bounded owner/tab journal16 before dispatch. Real network status0/408/5xx remains unknown. Create/update/persisted-rerank replays immutable acceptance in existing audit metadata, with current owned profile and original accepted revision, no copied profile body. Changed binding/actor refuses, deleted create cannot resurrect a case, account erase retires profile command namespace even with SQLiteFK-off. Legacy opaque audit semantics and prior migration assertions remain intact; no published migration rewrite.

Conflict comparison preserves current typing, distinguishes missing/null and atomic arrays, and applies only to draft. Explicit new Save uses reviewed revision/new UUID. Original conflict stays conflict with reviewed annotation. Mutable latest_draft is separate from immutable intent and survives immediate reload while conflict GET is pending. Accepted-but-newer-current reconciliation remains recoverable across reload and blocks replacement create/cleanup. Save feedback uses current clean accepted receipt, never labels newer typing saved.

## Evidence

- Full current SQLite: **5871 PASS**, **94.19%**, floor92 unchanged.
- Full current private PostgreSQL: **5871 PASS**, **94.19%**.
- Current frontend: **905 PASS**, types/lint/build PASS; nine pre-existing lint warnings. Backend ruff/format/mypy420 PASS.
- Current actual browser/server: **Demo4 + Auth4 PASS**, 501 same primary/lab/before/after consumers. Core profile/research/two programmes/documents/applications/declaration/correction/Today/reload/second-login/second-context/export/delete; independent/same-field conflict, newer typing during delayed GET, draft-only merge, dropped real committed create ACK/reload/exact UUID+body replay/no duplicate; widths320/768/1024/1440.
- Real dual-DB SQL-entry barriers and authentic actor/namespace erasure/migration tests. Network OS/driver guards, exact consumer hashes, owned DB/process cleanup qualify both full phases; no source/config/Git mutation under lock.
- All first failures preserved: old overwrite4, API0 misclassification, missing replay feedback, legacy migration/opaque-audit compatibility12, immediate reload typing1. OFF is not relabelled PASS.

Original logs/hash indices: `evidence/core-legacy-races-2026-10-14/checkpoint-c-final`. Earlier checkpoints preserve failures/preimages/grants. No private DB/cookies/dependency binaries/trace archives are published. Full test logs still contain earlier mocked read-hook TypeErrors caught by test boundaries; that fixture audit is open, not a confirmed current native-browser defect.

## Remaining scope

N01/N02 previously locally qualified; profile N09 current locally qualified in this report. N03/N04/N07 result writers, notes/rejection outcomes; N05 freshness mutation projection; N06 deadline timezone semantics; N08 export errors remain OPEN. Scholarship/recovery/history UX and semantic line review remain incomplete. Proposed D writer matrix and E findings are read-only, not implementation.

This is a local increment. Product is **not release accepted**: live search quality/DoD and stopped evaluation queues are not resumed, heldout150 unchanged. Stacked Draft88/base87 is not main/production; hostedCI, deployment, operator/consent/backup/ingress and published signed-in smoke are separate gates. IELTS/SAT remain optional tools; official programme requirements remain authoritative.
