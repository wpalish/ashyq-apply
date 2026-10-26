# A scheduled, free re-verification of the knowledge base's evidence (no search at all)

Type: task
Status: claimed (GitHub-cron part built 2026-10-19; the self-hosted part waits on 01-Q4)
Blocked by: 01-Q4 (for the self-hosted runs only; the GitHub cron needs no answer)
Map: ../map.md · AFK task; `loop-engineering` on a workflow, not a rule. Zero queries, zero credits: it re-reads
known URLs through the production fetcher.

## Question

The product answers from the knowledge base, whose facts go stale by the academic year and whose quotes can vanish
when a page changes. `KNOWLEDGE_BASE.md` prescribes the cadence (yearly rebuild; monthly deadline checks
September–January) but every step is a manual `verify_evidence` dispatch and a hand-built drafts directory. Can the
re-verification run itself, for free, and produce the re-draft queue — so the KB stays current without a search
provider, and the universities whose hosts refuse datacenter IPs are read from the owner's computer?

## Build

1. **`scripts/verify_evidence.py --from-kb <kb.json> [--only deadline,tuition]`**: builds the check rows from the KB
   itself (programme `evidence[].url` + quote, every fact's `source_url` + `quote`, `not_applicable[].source_url` +
   quote) instead of a drafts directory; same official-domain rule (the list's `official_domain`, `official_site`,
   `extra_domains`), same report shape (`case, item, url, outcome, status_code, official, quote_found, checked_on`).
2. **Diff** `evaluation/research/expert/kb_refresh_diff.py`: previous report vs new → `quote_gone`, `http_403`,
   `http_404`, `robots_refused`, `timeout`, `moved` (redirect), unchanged; plus the KB's own staleness (`verified_on`
   > 365 d, academic year past, deadline passed) → one queue file `docs/process/KB_REFRESH_<date>.md` listing the
   entries to re-draft, by university and question, with the reason. Never edits the KB JSON (the build step does).
3. **Workflow `kb-refresh.yml`**: `schedule` monthly (weekly September–January, `--only deadline`) plus
   `workflow_dispatch` with the `runner` input (`ubuntu-latest` / `self-hosted`); artifacts: the report and the
   queue; a job summary with the counts; the public repository makes the minutes free (private would cost 2 000
   included minutes a month; one run is ≈ 15 min). A scheduled workflow on a public repository is disabled after 60
   days without commits — note it in HANDOFF §9.
4. **Skip unchanged pages** (second iteration): `source_scanner.py` already reads sitemap `lastmod` and does a
   conditional GET; reuse its reading so a monthly run re-reads only pages whose validators changed, under the 60-read
   budget per host.
5. **Tests**: `--from-kb` row construction from a fixture KB; the diff's classes; the queue file's shape; no network.

## Deliverable

The workflow, the flag, the diff tool, tests; the first run's queue file committed; a line in `KNOWLEDGE_BASE.md`
"Refresh cadence" pointing to the workflow; HANDOFF §8/§9 lines.

## Files the worker holds

`backend/scripts/verify_evidence.py` (the `--from-kb` path only), `backend/evaluation/research/expert/kb_refresh_diff.py`
(new), `.github/workflows/kb-refresh.yml` (new), `backend/tests/test_kb_refresh.py` (new), `docs/process/KNOWLEDGE_BASE.md`
(one paragraph). Disjoint from 04 (`index_ceiling.py`) and 08 (reads this ticket's reports).

## Evidence

`KNOWLEDGE_BASE.md` build steps and cadence; the CI reports under `kb_drafts.2026-10-19/batch*/evidence_check.ci-*.json`
(312 URLs, 237 ok from GitHub runners); `jobs/source_scanner.py` (Freshness 2.0); the provider survey asset (GitHub
Actions pricing: free for public repositories; 6 h job limit).

## Done when

The workflow has run once on schedule or by dispatch with a queue file in the repository; the counts per outcome
match the CI reports within noise; the owner has the queue as the next expert batch.

## Progress (2026-10-19, GitHub-cron part)

- Built: `verify_evidence.py --from-kb … [--only …]`; `kb_refresh_diff.py` (the classes above, plus
  `robots_unreachable`: robots.txt could not be read, so RFC 9309 disallows, which is a vantage-point problem and
  not a refusal); `kb_build --refresh` (re-stamps `verified_on` on what still verifies, marks the rest `review`,
  never drops or changes a value, never overwrites the built KB); `.github/workflows/kb-refresh.yml` (monthly on
  every item, weekly September–January on deadlines; artifact only, no commit); `tests/test_kb_refresh.py`.
- First run, from the agent sandbox (`--trust-env-proxy`), not yet from the workflow: 559 rows, 333 URLs,
  167 hosts. Verified 533; quote_gone 1 (NTU Singapore deadline); robots_unreachable 19 (ANU, SNU, KU Leuven,
  HKU, KAIST, NTU Taiwan CSIE: robots.txt ConnectError through the proxy); fetch_error 4 (HTTP 405 on `http://`
  URLs through the proxy); timeout 2 (UTokyo). Queue: `docs/process/KB_REFRESH_2026-10-19.md`; report:
  `backend/evaluation/research/expert/data/kb_refresh/evidence_check.kb-refresh-sandbox-2026-10-19.json`.
- TODO: `runner: self-hosted` after 01-Q4; step 4 (skip unchanged pages via `source_scanner` validators); the
  first scheduled or dispatched workflow run and its queue (the "Done when" above).
