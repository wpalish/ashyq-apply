# Private admissions portfolio — future bounded plan

2026-10-12. **DESIGN ONLY / NOT_APPLIED / NOT_RUN.** Prepared by root while the G1 PostgreSQL runtime owns its frozen source. This document is not a source proposal, implementation or release acceptance.

## Actual seam

Existing `ApplicantProfileIn` already contains up to 30 `Activity` and 30 `Achievement` entries. Activity records name/category/role, optional duration and workload, responsibility, outcomes and up to five evidence links. Achievement records name/level/year/placement/selection criterion and evidence links. Neither array has stable item IDs or a versioned private workflow. Public SocialProfile must not be used to store an admissions document or private portfolio.

Keep the one existing case/profile authority. The first useful private workspace adds applicant-owned item identity, factual personal annotations, dated versions and explicit references to those existing inputs. It does not create a second applicant profile, duplicate ranking/scoring or declare a university's requirement from an optional activity.

## Finite first increment

- Bounded `PortfolioItem` records under one case: stable server ID, origin `applicant_entered` or `explicit_profile_import`, kind `activity/achievement/project`, entered title/role/start/end or year, description, applicant-reported measurable outcome, optional evidence URLs, current revision and immutable accepted event references.
- Private draft state and provenance. Verification remains `applicant_reported/not_independently_verified`; opening an evidence URL, uploading nothing or saving a record never authenticates the achievement. Do not generate fictitious achievements, certificates, quantities, hours or results.
- Dates, numeric fields and text are strict, finite and bounded; missing dates/outcomes stay missing. Describe subjective impact separately from recorded measurable outcome. Do not call the user a founder or award winner unless that is their entered claim, with visible provenance.
- Explicit import preview uses the exact current owned profile's two arrays. A source fingerprint plus array kind/index and semantic digest identifies the chosen source observation. Equal names do not merge records. Changed/reordered arrays invalidate an in-flight preview; already accepted history survives. Same-UUID replay is resolved before mutable source checks.
- Import creates a new personal record only after ACK. A changed portfolio item does not silently overwrite `ApplicantProfileIn`, official tests, source claims or admission checks. Show the imported source observation and the later personal edit separately; any future write-back to the profile needs its own explicit conflict contract.
- One case-owned current/event persistence seam, UUID/digest/CAS atomicity, immutable accepted receipts and history pagination, following the reviewed G2/G3 pattern. Case membership/ownership first; foreign/missing IDs uniformly 404. Accepted history remains readable after subscription expiry; no research unit, learning attempt or payment is consumed.
- No public sharing, social publication, portal credentials, attachment bytes, private document URLs, background URL fetching, AI essay generation, LLM feedback or outbound applicant data. Evidence links are applicant input, bounded public absolute http(s) destinations without credentials/private tokens; scheme safety is separate from truth or official provenance.
- Own export includes current items, their origin references and accepted event history. ORM case deletion cascades only that case's records. New local drafts use owner+case namespace/epoch; matching ACK retires only that case's indexed state. Historical unindexed legacy browser data cannot be claimed fully purged without an exact attribution method.

This first increment is a private factual workspace. Essay editor, application-specific prompt/word limits, secure attachments, reviewer workflow and automated form filling are separate work. Mandatory university requirements stay in authorized official evidence; portfolio recommendations stay optional unless a current exact source establishes a particular requirement.

## Integration order and likely finite paths

After G1 release, G2 common workload, G3 durable application actions/Today and the bounded content/diagnostic foundations: new `schemas/private_portfolio.py`, `domain/private_portfolio.py`, `models/private_portfolio.py`, `api/routes_private_portfolio.py`, one additive migration and meaningful domain/API controls. Mechanical wiring: `main.py`, model registration, applicant ORM relationships, existing profile export, typed frontend client/types/localized messages and one private Portfolio screen/controls. Preserve existing hash routes and deep links, public social contracts, profile arrays and provider/privacy boundaries. Exact preimages and path allowlist must be chosen in a new HANDOFF write-ahead before code.

## Future acceptance controls — NOT_RUN

1. Exact same UUID/digest replay, UUID conflict, real SQLite/PG concurrent CAS loser and current/event rollback; old receipts survive edits.
2. Own/cross-case/tenant membership, safe export/delete cascade and sibling-case preservation; no public route exposes portfolio records.
3. Profile import detects reorder/change, duplicate names remain distinct, no GET auto-import or automatic profile/source/ranking update; unknown delivery retains original UUID/input.
4. Dates/numbers/URL bounds, missing factual fields, unsafe/private link rejection and no URL fetch; entered evidence never becomes verified fact.
5. Expiry preserves personal history while existing paid learning stays gated; no quota/payment/research mutations.
6. Real API create/edit/reload/second clean browser, 409 draft retention, owner/case A→B→A and delete ACK late-response fences; RU/EN/KK and readable 320/768/1024/1440 screenshots.

Pedagogical signoffs, real operator/legal/storage/retention facts, production release and fresh search quality remain independent acceptance items. This plan supplies none of those facts and does not reopen any stopped workflow.
