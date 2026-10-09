# DRAFT — applied-source security documentation reconciliation

Verdict: READY_FOR_ROOT_REVIEW, documentation only. No publication, full/browser,
production, legal or search-quality acceptance. Source c7b41fcf42c2fb84e877a8cb8b1349eedb79941f;
exact recovery 19-file map 17f6e7218364288374abfdec72d63ddba1c3dde0aa1bef21f478766d337be017.
The immutable provider STOP remains 65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d.

Only three proposed documentation paths: SECURITY.md, docs/legal/RELEASE_READINESS.md,
and the browser paragraph in docs/legal/PRIVACY_POLICY_RU.md. Policy version
2026-10-09.draft1, operator placeholders and DRAFT status remain. Primary files
were neither edited nor imported. No tests, DB, runner, ports, browser, network,
provider/model, labels, scoring or Git mutation occurred.

| Source finding | Documentation change and boundary |
|---|---|
| config.py136–148 and routes_social.py1028–1037 now authorize global moderation by provisioned user IDs, empty default | Applied control; not a confirmation that an operator has identified/provisioned a real moderator |
| main.py167–185,189–239 applies no-store to returned API responses and early refusals | Applied control; static cache unchanged; not old-cache deletion or a guarantee for server-generated unhandled exceptions/deployed proxies |
| applicantStorage.ts23–96 and AuthGate.ts29–71,107–110 bind user/org, clear recognized applicant keys, revalidate/unmount stale private trees | Applied cooperative browser isolation; server authorization remains essential. Shared-cookie requests already in flight, XSS, encryption and exports are not solved |
| client.ts136–169,178–243 and store.tsx465–512 fence async owner/generation transitions | Narrow prevention of stale action/response adoption; not a claim of an atomic server session-owner handshake |
| store.tsx541–552 recovers authorized server list only when no explicit pointer; routes_cases.py27–62 sorts tenant-owned cases newest first; newCase633–652 invalidates intent/releases loading | Same-owner recovery applied with latest run/readers, no create/research/retry. Current native full/browser acceptance pending |
| ExportScreen.tsx24,86–119,162–190 and store.tsx813–844 support no-run saved cases and acknowledge deletion before success/reset | Case control, not account-wide export/delete, backup cleanup or historical-marks sweep |
| routes_profile.py266–372 exports profile/runs/results/claims/conflicts/entity-filtered audit;376–399 deletes primary case and writes an audit event | Avoid both overclaim and underdescription of export. Inherited endpoint note369–371 promising complete/all deletion is queued copy-gap; no app edit bundled |
| routes_account.py149–220 returns detail only; mail.py42–51 console logs recipient/message; reset redemption223–260 reads then marks token | Correct SECURITY's stale nonproduction API-link claim. Console-mail/log PII and concurrent reset audit stay open |
| LegalScreen.tsx26–42,88–100,158–163 and CONSENT_SPEC_RU.md retain operator/minor/consent gaps | Do not treat a policy page, checkbox, version string or tested UI as server consent. Actual operator metadata remains unconfirmed |

Source references are relative to the pinned primary checkout:
- backend/app/config.py:136; backend/app/api/routes_social.py:1028; backend/app/main.py:167.
- frontend/src/lib/applicantStorage.ts:23; frontend/src/AuthGate.tsx:29;
  frontend/src/api/client.ts:136; frontend/src/lib/store.tsx:465.
- frontend/src/screens/ExportScreen.tsx:86; frontend/src/screens/DocumentsScreen.tsx:25;
  backend/app/api/routes_cases.py:27; backend/app/api/routes_profile.py:266.
- backend/app/api/routes_account.py:149; backend/app/mail.py:42;
  frontend/src/screens/LegalScreen.tsx:26; docs/legal/operator-facts.json:1.

History: predecessor c976074b SECURITY is saved byte-for-byte; RELEASE_READINESS
did not exist there (exact read failure saved). The original current pre-fix readiness
text is retained verbatim inside a clearly historical details block. First a0fc
full FAILED history and unchanged auth E2E are not relabelled green. Current recovery
full/browser remain pending; root must append actual final source/gate/UI receipts.
No native totals were inferred or added. Same-owner mocked recovery is not a live
server-auth, tenant-security or data-rights proof.

Remaining launch conditions: operator identity/contact, actual DB/backup/log countries
and recipients, versioned consent/age/representative contract, retention/right workflows,
PII/log access/cleanup, concurrent reset check, separate nginx deployed-header check,
real production/restore/incident/support evidence. No universal legal deadline or
jurisdiction is invented from app region ams. Existing official references are retained;
this source-only review did not re-browse legal sources. Parent separately reported its
fresh law review; this packet does not invent a new applicability decision.

Validation is saved-only: exact current 19 source pins, supplemental source/document
pins, immutable STOP before/after, exact policy version and narrow browser-only policy
delta, original readiness-history containment and all local relative Markdown links.
No test suite was run or needed for reversible documentation edits.
