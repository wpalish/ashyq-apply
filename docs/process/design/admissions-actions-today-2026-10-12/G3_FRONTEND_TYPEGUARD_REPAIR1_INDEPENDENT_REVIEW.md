# G3 frontend test type guard: independent finite review

Reviewer: /root/open_search_solutions. Source inspected 2026-10-13 06:20:32 UTC.
Disposition: **NO SOURCE-ONLY BLOCKER FOUND** in the exact one-line test change.
NOT_APPLIED_BY_REVIEWER / NOT_IMPORTED / NOT_AST / NOT_RUN / NOT_ACCEPTED.

## Pins and preservation

- Packet: proposals/g3-frontend-typeguard-repair1/SEAL.json.
- Seal SHA256: 4a3ee678ab40159fe21514cdd663792dcc82ad4cf7da63671341b785c6f6b5ee.
- All four declared members independently match exact SHA256 and byte counts.
- Sole allowed path: frontend/src/lib/admissionsActionsRecovery.test.ts.
- Full preimage SHA256: d3cb0183605cdedc0c86cbbd725d7f6935ff3301d96e5d116fae130037d842ef, 60646 bytes.
- Full postimage SHA256: 56b67aeb473b1cf68a5eb6b97de3790dc1c8b461f859145c4936b2e75699cfed, 60739 bytes.
- Primary still matched the preimage when inspected.
- Independently deleting the single, uniquely occurring added guard reconstructs the entire preimage exactly. This is textual preservation, without AST/import/runtime; all other tests, original assertions, imports and production files are unchanged by this packet.

## Exact change and native typing

At postimage line 408, immediately before the original line 409 accepted_at assertion:

```ts
if (selector.observed_head.origin !== 'g2') throw new Error('Expected G2 head fixture');
```

The complete finite diff and relevant local test context were read. The selector fixture at lines 402-405 is explicitly a select_active_preparation command with both origins g2 and a microsecond UTC timestamp ending in Z. The digest-equivalence assertion at 407 remains exact, and the original assertion at 409 still checks the identical transmitted Z string rather than a canonicalized replacement.

Native frontend/src/types/admissionsActions.ts declares NativeHeadV1 as G2HeadV1 | LegacyV2HeadV1 | LegacyV1HeadV1 at 85. Only G2HeadV1 carries accepted_at, with origin:'g2'. SelectActivePreparationV1 at 137-139 deliberately uses the full NativeHeadV1 union; the outer origin does not type-narrow that nested union. The added runtime discriminant properly narrows the observed head before accessing accepted_at, and fails the test if a future fixture changes to a different origin. It introduces no cast, non-null assertion, ignore, schema relaxation, conditional assertion omission or production change.

Inspected native types SHA256: 034d76ca8483553eac17039d36cd98363865ca97eafca9009c312edbaf5341dc.
Current production recovery helper SHA256: d9984a8787d63b83a36f8f7d517a243a1e3759f31ae0fa67d3eadec6a6fd97cf (hash pin only in this finite task; no wider helper re-review).

## Boundary

Only ordinary source/diff reads, hashing and exact text comparison were performed. No primary/lab/application edits, imports, AST, lint/format/test execution, database or network access, Git/HANDOFF/helper/config changes, provider or stopped-workflow operations occurred. Only this new external report and its metadata seal were written.

No further source prerequisite is proposed. Root may apply the exact postimage under its existing write-ahead and continue authorized native static/runtime gates. This report makes no TypeScript PASS, execution, full-gate or product-acceptance claim.

