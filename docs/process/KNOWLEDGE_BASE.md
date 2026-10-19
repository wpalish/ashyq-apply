# Verified knowledge base (bachelor's in Computer Science, top-100)

Owner decision, 2026-10-19: «база, топ-100 из каталога, только CS, поиск заморозить».
Live web search and discovery are frozen. For the bachelor's in Computer Science the product answers from
a verified knowledge base (KB) covering the top-100 catalogue universities in
`backend/evaluation/research/data/kb_top100_list.json`.

## Setting

`UNIMATCH_KNOWLEDGE_MODE` takes one of two values:

| value | behaviour |
|---|---|
| `kb` (default) | Research reads the KB files only. There is no discovery, no search provider and no page read: the fetcher is offline and the browser tier is off. |
| `live` | The web pipeline, unchanged. |

Demo mode (`UNIMATCH_DEMO_MODE=true`) ignores the setting and keeps its own fixtures, so the golden demo
test is byte-identical. Optional overrides:

- `UNIMATCH_KNOWLEDGE_BASE_PATH` (default `backend/app/knowledge/kb_cs_bachelor.json`);
- `UNIMATCH_KNOWLEDGE_IMPORTED_PATH` (default `backend/app/knowledge/kb_imported_dev.json`).

## How a run uses it (`kb` mode)

1. **Discovery** (`app.knowledge.claims.KnowledgeDiscovery`) retrieves the selected catalogue universities
   exactly as before (`app.catalogue.retrieval.retrieve`). Each one is looked up in the KB by its catalogue
   `seed_id`, or failing that by its official domain.
2. **Verification.** A university in the KB gets claims built from its facts. These use the ordinary
   `Claim` model:
   - the source is official (`official_domain=true`) and the verified quote is the excerpt;
   - confidence is 0.8, the claim builder's value for an official quoted page;
   - status is `VERIFIED_CURRENT`;
   - a current tuition fact also fills the cost table, so the scoring and ranking path is unchanged.
3. **No entry.** A university that is not in the KB (or whose entry has no verified programme page and
   no verified fact), or a profile that is not a CS bachelor, gets no
   claims. It gets one blocking question instead: "No verified data yet for …". Nothing is guessed and
   nothing is searched.
4. **Funding and documents.** The funding stage reads no scholarship page. It builds one `Scholarship`
   per award the row's KB claims name (`app.knowledge.funding.kb_scholarships`), and then the live
   path's eligibility checks, classification and funding fit run unchanged. The KB holds no amount,
   coverage, deadline or restriction, so those stay unknown, and a KB award classifies as `UNKNOWN`, or
   as `NOT_ELIGIBLE` when it is closed to international students. A stale claim names its award but
   settles nothing: its eligibility stays unknown, and the row gets a question for the scholarships
   office. A verified scholarship `not_applicable` row, or a scholarship fact whose value is
   `not_applicable`, becomes a `scholarship_exists = false` claim with no award named, but only when the
   entry names no award. Its outcome is explicit: funding fit `NOT_ELIGIBLE` with the reason "No
   institutional scholarship …". When that statement is stale, the funding fit is `UNKNOWN` and the
   reason says so. Document collection adds one honest question: document lists are not in the KB yet.

The KB fact keys map to claim types as follows:

| KB fact key | claim type |
|---|---|
| `ielts.overall` | `ielts_min_overall` |
| `ielts.subscores` | `ielts_min_subscore` |
| `english_evidence.toefl_ibt.minimum` | `toefl_min_total` |
| `english_evidence.duolingo.minimum` | `duolingo_min` |
| `gpa` | `min_gpa` |
| `deadline` | `admission_deadline` |
| `tuition` | `tuition` |
| `scholarships.<award>.exists` | `scholarship_exists` |
| `scholarships.<award>.applicability.international` | `scholarship_international_eligible` |

## Staleness

A fact is shown as stale (`POSSIBLY_STALE`, `is_stale=true`, with the reason in its notes) and never as
current when any of these holds:

- its `verified_on` is more than 365 days ago;
- its academic year is past, meaning the end year is the current year or earlier;
- its academic year is before the applicant's intake year: a 2026/27 fee is stale for a fall 2027
  intake;
- it is a deadline that has passed.

In kb mode the recheck job re-reads the KB file once a claim's verification is a year old, on the KB's
own clock. It does not use the live per-type windows.

## File format

Two files share one entry shape:

- `kb_cs_bachelor.json` (`format: kb-cs-bachelor/1`) is built from the expert batches;
- `kb_imported_dev.json` (`format: kb-imported-dev/1`) is the 21-university development import, documented
  in `KB_IMPORT_2026-10-19.md`.

Top level of the built file: `version` and `built_at`, `list_version`, `intake`, `questions`,
`stale_policy`, `evidence_reports`, `entries` (keyed by `seed_id`), `stale_facts` and `unresolved_drafts`.

Each entry has:

- `seed_id`, `source_case` and `source_batch`;
- `review_status`, which is `expert_checked` for the built file. The import's values are `human_verified`
  and `draft`.
- `verified_on` and `verified_on_basis` (`ci_evidence_check`, or
  `ci_evidence_check+sandbox_recheck` when any of its facts or programme quotes was verified by a
  recheck);
- `university`, `country`, `official_domain` and `official_domains`;
- `programme`, with `status`, `urls`, `evidence[{url, quote, accessed_on, verified_on}]`,
  `related_programme_urls` and `teaching_language_evidence`;
- `facts`, holding the six questions, each a list of facts. Each fact has these fields:
  - `key`, `value` and `unit`;
  - `period`: `year` for tuition, the intake for a deadline;
  - `academic_year` and `population`;
  - `source_url`, `quote`, `source_type`, `accessed_on` and `verified_on`;
  - `verified_by`: `ci` or `recheck`, the check whose row verified it (programme evidence records
    carry it too);
  - `notes`, `stale` and `stale_reasons`;
  - `award`, for scholarship facts only;
- `unknown[{question, key, reason}]`;
- `not_applicable[{question, key, reason, source_url, quote, verified_on}]`;
- `known_fact_count`.

The applicant sees `human_verified` as "human verified". The applicant sees `draft` and `expert_checked`
as "expert-checked, quote verified".

**Merging** (`app.knowledge.load_knowledge_base`) works by `seed_id`. A fact's identity is
`(seed_id, key)`. When two facts share an identity, the more recently verified one wins, and the built
file wins a tie. A missing file is simply skipped.

## Build steps

1. **Drafts.** Expert workers write drafts into
   `backend/evaluation/research/expert/data/kb_drafts.<date>/batch<N>/{programme,core}/`, in the dev5
   formats. A programme draft is named `<case>.<n>-<role>.json`, for example `qs2027-005.0-local.json`.
   The case may contain digits and hyphens, and the role is one of `local`, `twin`,
   `site`, `department`, `language` or `related`. A core draft is `<case>.json` and holds the six
   answers. The case is a `seed_id`, or a draft carries a `seed_id` field.
2. **CI verification.** Run `benchmark-capture.yml` with `mode=verify_evidence` and
   `extra_args=evaluation/research/expert/data/kb_drafts.<date>/batch<N>` (one batch per run). The check:
   - reads the batch directory recursively;
   - accepts a host, or any subdomain of it, as official when it is in `OFFICIAL_DOMAINS` or in the
     list's `official_domain`, `official_site` or `extra_domains` for that `seed_id`;
   - stamps each row with `checked_on`.

   Download the `evidence-check-<run id>` artifact's `report.json` next to the drafts, for example as
   `batch<N>/evidence_check.ci-<date>.json`.

   **Recheck from a sandbox (optional).** GitHub-hosted runners are refused by sites that block
   datacenter addresses (HTTP 403: cam.ac.uk, harvard, jhu, ed.ac.uk, uq, …). From an agent sandbox
   whose only way out is an HTTPS proxy, re-check the rows CI did not pass:

   ```bash
   PYTHONPATH=. python scripts/verify_evidence.py --trust-env-proxy \
       --recheck evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.ci-*.json
   ```

   - `--trust-env-proxy` is an explicit opt-in: the production `Fetcher` sends through `HTTPS_PROXY`
     by host name and verifies TLS against the CA bundle in `SSL_CERT_FILE` (or `REQUESTS_CA_BUNDLE`,
     `CURL_CA_BUNDLE`; else the system store). TLS verification is never turned off. The user agent,
     robots.txt handling, extraction and quote matching are the same code as the CI check.
   - Rechecked: every row with a URL that is not `official` and `quote_found`. A `robots_disallowed`
     row is final and is not rechecked; neither is a (case, item, URL) that also has a passing row.
   - The verifier waits out a robots.txt Crawl-delay of up to 30 s per request to a host (the
     product's fetcher waits at most 10 s); a longer one keeps the outcome `robots_crawl_delay`.
   - Each report gets `batch<N>/evidence_check.recheck-<today>.json` beside it: the same row shape,
     plus `"origin": "sandbox-proxy"`.

   robots.txt (product and verifier alike): a matching Disallow, including `*` and `$` patterns, is
   final unless a matching Allow is strictly longer; a tie goes to Disallow.
3. **Build.** From `backend`, run:

   ```bash
   python -m evaluation.research.expert.kb_build \
       evaluation/research/expert/data/kb_drafts.<date> \
       --evidence evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.ci-*.json \
                  evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.recheck-*.json \
       --built-at <YYYY-MM-DD> --version <YYYY-MM-DD>.kb-cs-bachelor.<n>
   ```

   The build writes `backend/app/knowledge/kb_cs_bachelor.json`, never `backend/data`.

   A value is `known` only when a CI or recheck report row for that case, item and URL has `official`
   and `quote_found` set. For one (case, item, URL) in both, a passing row wins; when both pass, the
   CI row is used. A report whose file name contains `container` (an ad-hoc pre-check from an agent's
   container) is skipped; a recheck report is a full evidence check of the rows it holds. Anything else is listed under `unknown` with its reason. The dev5/dev4 rules still
   apply: an undated deadline and an indicative GPA stay unknown.

   The year rules do not drop a verified value silently. A CI-verified fee for another academic year, or
   one with no year stated, is kept as a **stale** fact with the published year and the reason. So is a
   CI-verified deadline of a past cycle. A fee per semester or for the whole programme (Lund) keeps its
   `period` as published. It becomes a claim that says so, and it enters the yearly cost table only when
   its period is a year.
4. **Commit.** Commit the KB file with the drafts and reports. `tests/test_knowledge_base.py` covers the
   converter, the merge, staleness and both modes.

## Refresh cadence

- **Every admissions cycle (at least yearly):** re-run the CI check on every batch and rebuild. Deadlines
  and fees go stale with the academic year. Facts older than 365 days show as stale automatically.
- **When a fact shows as stale or a page changes:** re-draft that university, re-check its batch and
  rebuild. Never edit the JSON by hand.
- **Monthly** in the September–January application season: re-run the CI check on the deadline items.
