# Unimatch search release — 2026-10-02

## Published source and infrastructure

- PR #39: https://github.com/wpalish/ashyq-apply/pull/39
- Tested head: `dbbf396a9c8e1b6bce67875cfb50a80c771248af`.
- Squash main: `1aa188edd74735b09ef5ca7052dc4d0106c897d7`; identical Git tree `6534f52fe6186a598ff39ad6391b042e0dd6943c`.
- Exact-head CI: push36970326234 and PR36970328805, all8 jobs succeeded. Postmerge run: https://github.com/wpalish/ashyq-apply/actions/runs/36972183803
- Existing Fly app `ashyq-apply-alisher`, release **v5 complete**; same API `82d1292f719138` and worker `8dd627ae93e508`, both started/healthy.
- Immutable image `sha256:ce0acb2a05da09bda5cc248846d5895137a20d80e52eb7ac2e405aa7a877aa89` on both processes. No additional permanent machines.
- Release migration `d8e412c6a901`; public health/database ok, demo_mode false, respect_robots true.
- Site: https://ashyq-apply-alisher.fly.dev/

## What changed

A local catalogue contains501 university identities (500 imported observations plus the preserved curated institution absent from that snapshot). Name/alias/city/country/region search and pagination do not depend on an external provider. Up to5 selected identities can enter the bounded live research pipeline. Seed prices, ranks, requirements and website guesses stay provenance-labelled; they are never promoted to verified admissions/funding Claims.

The observed Groningen crawl fault is fixed: sitemap attempts are capped even on failures; an oversized map stops map traversal and allows existing navigation/search. The discovery deadline is300s per institution. A future deadline or optional-test policy alone cannot mark academic eligibility MET.

## Tests

- Ruff check/format and mypy324 files: pass.
- Backend: **2873 passed**, coverage **94.89%** (floor92 unchanged).
- Frontend: typecheck/lint/build pass; **232 tests**.
- Browser: **79 passed,1 intentional skip**, auth **6 passed**.
- Demo: Groningen first/PLAUSIBLE; UBC OUT_OF_BUDGET. Single migration head.
- Tests cover repeated imports, preservation/history, checked-domain precedence, identity acronym guards, regional filters, tenant access, selected-run routing, provider outage with zero invented claims, case-switch selection reset and no-profile browsing.

## Public acceptance (real network, synthetic applicant only)

Normal public registration/profile creation returned201. The browser signed into this isolated synthetic workspace; no user credentials or real applicant records were changed.

Public authenticated catalogue probes:

| Query | Result | Observed response time |
|---|---:|---:|
| All |501 identities,500 imported snapshots|0.470s|
| MIT |2 name/alias matches, including MIT|0.227s|
| Canada |17 universities, all Canadian|0.215s|
| Nanyang |1 university|0.284s|
| Deliberately nonexistent name |0|0.216s|

These are individual acceptance measurements, not latency guarantees.

From the published **Find** UI, selected NTU and clicked **Research selected (1)**. The request persisted the selected local identity and demo_mode=false; the real worker completed run `9307186a015a43529cdd4ec2c6d98e19` from **06:12:54 to06:15:31 UTC** (about157s). Final state awaiting_user_decision, job succeeded,21 verification/funding page checks,0 unreadable pages,51 Claim records and3 programme results:

- Bachelor of Computing (Hons) in Computer Science.
- Bachelor of Science in Mathematical and Computer Sciences.
- BSc in Mathematical Sciences.

Browser verification: automatic progress transition;3 result cards; results restored after reload; official programme URL and17 Claims per result in Sources & evidence; unknown entry requirements/costs/deadlines remain visibly unknown. Saving the Computer Science result displayed Saved and the Saved tab filtered to that one result. This saves a research option, not an application.

## Honest limits

- Catalogue inclusion is preliminary discovery, not confirmation of a requested intake/programme or an admissions recommendation.
- This public NTU run has **33.3% decision-field completeness** per programme,31 unknown diagnostics and43 interpretation/scope/budget diagnostics (including repeats across programmes). Its51 records include scholarship facts repeated for the3 programme assessments; they are not51 distinct admissions requirements.
- All3 results correctly remain NEEDS_OFFICIAL_CLARIFICATION; tuition, eligibility and personalised funding remain unknown. Scholarship existence/conditional benefits do not imply an award to the applicant. A historical curriculum page does not prove the requested intake is open.
- The separate postrepair Groningen capture read70 pages successfully, retained3 Claims and17% completeness. MIT official homepage identity was verified separately. Neither proves full official-data coverage across501 institutions.
- Boundaries, source access and extraction limits are surfaced; no guarantee of complete admission data or admission chances is made.

## Operations

The public smoke account is clearly synthetic and isolated. Do not contact it or treat it as a student lead. Retain the run as release evidence; do not resubmit it during a handoff. Production search is deployed; subsequent work should start from a specific reproduced extraction or runtime defect, preserving the ranking/privacy/source invariants.
