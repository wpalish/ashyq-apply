# Unimatch release — 2026-10-02

## Source and checks

- PR #37 merged to `main` as `5a6edc9720964327953a1babb217d1032cdbddc7`.
- The merged tree equals the selected head `0c28884c772ab8a17dad9f3f48643ebc4b441f05`: `42406f1b6071268b50335c97743d6bf8a84187fe`.
- Both selected-head runs (`36939543613`, `36939548055`) passed all four jobs. Actual-main run `36941419007` passed frontend, security/containers, PostgreSQL and SQLite.
- Local frontend: 227 unit tests, 77 Playwright passed with one intentional desktop-only skip, six authenticated Playwright tests passed. Backend: 2,844 tests, 94.92% coverage.

## Production deployment

- Existing Fly app `ashyq-apply-alisher`, release v4, deployed at `2026-10-01T23:51:11Z` from the merged tree. The Alembic release command succeeded.
- App machine `82d1292f719138` and worker `8dd627ae93e508` remained the only runtime machines. Both started and passed Fly health checks with image `sha256:62045be818803646ab91cbd50040e3db9de0ec7fa449cd532755b51f55cbb916`.
- Public `https://ashyq-apply-alisher.fly.dev/api/health` returned HTTP 200, status/database `ok`, `demo_mode=false`, `respect_robots=true`, `browser_tier=true`.
- Public browser showed the new Unimatch title, landing image, and the authenticated profile/Find for the existing `Public search smoke (synthetic)` case. The existing run showed three NTU programmes and clearly labeled unverified and unknown fields.

## Live search limits

- The production worker's configured `exa_mcp` adapter returned three official `rug.nl` programme/admissions URLs for one bounded query. A direct replay of the canary's field-and-degree query returned five official URLs.
- The isolated, one-institution production-worker canary used the real pipeline, real sites, normal Fetcher/robots policy, and a throwaway SQLite database. Groningen was reached (1/1); programme and scholarship pages were found; 79 page reads succeeded, one failed HTTP 404; three claims were recorded with 17% verification completeness and zero structural false positives in the canary's four guarded categories.
- One of six search-identity queries reported `exa_mcp; malformed response` during the canary. Its direct replay succeeded. The provider response shape from that failed call was not captured; this is a partial provider failure, not evidence for a parser change.
- A fresh authenticated production UI run has **not** been demonstrated. The Mac locked while its confirmation dialog was being handled. Logs through 23:56 UTC contained no new `POST /api/runs`; verify the run list before retrying. Do not infer product-wide recall, complete eligibility, or funding certainty from this canary.

## Next acceptance step

After the owner unlocks the Mac, inspect the existing authenticated Chrome tab and synthetic case. Confirm whether a fourth run exists, run one new production research job if needed, wait for completion, and inspect Find, evidence and explicit failure/unknown labels. Capture any reproducible fault before changing source or making a readiness claim.
