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
4. **Funding.** The funding stage reads no scholarship page. It builds one `Scholarship`
   per award the row's KB claims name (`app.knowledge.funding.kb_scholarships`), and then the live
   path's eligibility checks, classification and funding fit run unchanged. The KB holds no amount,
   coverage, deadline or restriction, so those stay unknown, and a KB award classifies as `UNKNOWN`, or
   as `NOT_ELIGIBLE` when it is closed to international students. A stale claim names its award but
   settles nothing: its eligibility stays unknown, and the row gets a question for the scholarships
   office. A verified scholarship `not_applicable` row, or a scholarship fact whose value is
   `not_applicable`, becomes a `scholarship_exists = false` claim with no award named, but only when the
   entry names no award. Its outcome is explicit: funding fit `NOT_ELIGIBLE` with the reason "No
   institutional scholarship …". When that statement is stale, the funding fit is `UNKNOWN` and the
   reason says so.
5. **Documents.** After the applicant approves a row, the document stage reads no page. When the entry
   holds verified `documents` facts (see "Application documents" below), it builds the same
   `DocumentChecklist` a live read builds (`app.knowledge.documents.kb_checklist`) and stores it on the
   row, with one `required_document` claim per item merged as live document claims are. Otherwise the row
   gets one honest question: "The verified knowledge base does not hold document lists yet …".

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
| `documents.<kind>` | `required_document`, built by the document stage only (not a verification claim) |

## Application documents

The question `documents` (`app.knowledge.QUESTIONS`, after the six core ones) holds one fact per document
an official page lists for an international applicant. Unknown stays unknown: only a document the page
names, quoted word for word and found by the evidence check, is a fact; nothing is inferred.

- `key` is `documents.<kind>`, and `kind` is one of `app.knowledge.documents.DOCUMENT_KINDS`. Most kinds
  map to a name of the live document reader (`web_documents._DOC_RULES`), so the owner and the flags
  (translation, notarisation, apostille, lead time) are the live ones: `transcript`, `secondary_diploma`,
  `translation`, `apostille`, `credential_evaluation`, `passport`, `photo`, `personal_statement`,
  `motivation_letter`, `essay`, `recommendation_letter`, `academic_reference`, `cv`, `portfolio`,
  `financial_proof`. Three kinds have no live rule and no lead time: `english_test_report` ("English
  language test report", third party), `entrance_test` ("Admission test result", third party) and
  `application_form` ("Application form", applicant).
- `value` is `{kind, requirement, condition}`. `requirement` is `required`, `optional` or `conditional`; a
  conditional item must carry the page's condition.
- `population`, `academic_year` (only when the page states one), `source_url`, `quote`, `accessed_on`,
  `verified_on`, `verified_by`, `stale` and `stale_reasons`, as for every fact.
- `cycle_stated` (optional): the application cycle or intake exactly as the page prints it ("2026
  Admission Information on Chinese-taught Undergraduate Programs", "Spring 2027", "Last Update:
  02/12/2021"). When the draft also says `cycle_is_intake: false` (the expert judged it is not the KB's
  intake), the fact is stale with the reason `document list published for "<cycle_stated>", not the
  <intake> intake`. No year is inferred from it: `academic_year` stays null unless the page states one.
  The reason is not one of the intake-relative "is before the … intake's" reasons, so the runtime
  (`carried_stale_reasons`) and the refresh keep it for every applicant's intake: the list is for the
  printed cycle, whatever intake is asked about, and is shown as `POSSIBLY_STALE` ("listed so you can
  prepare, not as confirmed").

**Checklist (kb mode).** Each fact becomes a `DocumentItem` (purpose admission) with the live name, owner
and flags, `required` true only for `required`, and `format_notes` saying "Optional, as published." or
"Required only when: <condition>.". The action split and the numbered steps are the live ones
(`web_documents.populate_actions`). Each item's claim is official, quoted, confidence 0.8; a stale fact
(the staleness rules below) is `POSSIBLY_STALE`, its item says "Possibly outdated: …", and a non-blocking
question asks whether the list is still the one for the intake. A drafted item the evidence check did not
verify is not listed; a non-blocking question says the list may be incomplete. Completeness is `official`
when every item is current and nothing drafted is missing, else `partial`.

**Draft format.** A core draft's `answers.documents` is `{status, population, academic_year, cycle_stated?,
cycle_is_intake?, notes, items: [{kind, requirement, condition?, cycle_stated?, cycle_is_intake?, url, quote,
notes?, population?, academic_year?}]}`. An item's own `cycle_stated` / `cycle_is_intake` win over the
answer's (a list read from two pages, only one of them another cycle's). The evidence check
checks every item as its own row, item `documents.<kind>`; an answer with `status: unknown` is one
`documents` row with no URL. An item whose kind is not in the vocabulary, a repeated kind, a conditional
item without its condition, a missing quote or an unverified row is listed under `unknown`
(`question: documents`, `key: documents.<kind>`) with the reason. The pilot is
`kb_drafts.2026-10-19/topup_documents1/` (8 universities, see its README).

## Staleness

A fact is shown as stale (`POSSIBLY_STALE`, `is_stale=true`, with the reason in its notes) and never as
current when any of these holds:

- its `verified_on` is more than 365 days ago;
- its academic year is past, meaning the end year is the current year or earlier;
- its academic year is before the applicant's intake year: a 2026/27 fee is stale for a fall 2027
  intake;
- it is a deadline that has passed;
- it is a document list the expert marked as another cycle's (`cycle_is_intake: false`, see
  "Application documents"), for every intake.

In kb mode the recheck job re-reads the KB file once a claim's verification is a year old, on the KB's
own clock. It does not use the live per-type windows.

## File format

Two files share one entry shape:

- `kb_cs_bachelor.json` (`format: kb-cs-bachelor/1`) is built from the expert batches;
- `kb_imported_dev.json` (`format: kb-imported-dev/1`) is the 21-university development import, documented
  in `KB_IMPORT_2026-10-19.md`.

Top level of the built file: `version` and `built_at`, `list_version`, `intake`, `questions`,
`stale_policy`, `evidence_reports`, `robots_override_excluded`, `robots_override_facts`, `entries`
(keyed by `seed_id`), `stale_facts` and `unresolved_drafts`.

Each entry has:

- `seed_id`, `source_case` and `source_batch`, plus `source_batches` when the entry merges drafts from
  several dirs (see "Top-up dirs" under Build steps);
- `review_status`, which is `expert_checked` for the built file. The import's values are `human_verified`
  and `draft`.
- `verified_on` and `verified_on_basis` (`ci_evidence_check`, plus `+sandbox_recheck` when any of its
  facts or programme quotes was verified by a recheck and `+robots_override` when any was verified only
  by the robots override);
- `university`, `country`, `official_domain` and `official_domains`;
- `programme`, with `status`, `urls`, `evidence[{url, quote, accessed_on, verified_on}]`,
  `related_programme_urls` and `teaching_language_evidence`;
- `facts`, holding the six questions and `documents`, each a list of facts. Each fact has these fields:
  - `key`, `value` and `unit`;
  - `period`: `year` for tuition, the intake for a deadline;
  - `academic_year` and `population`;
  - `source_url`, `quote`, `source_type`, `accessed_on` and `verified_on`;
  - `verified_by`: `ci`, `recheck` or `robots_override`, the check whose row verified it (programme
    evidence records carry it too); a `robots_override` record also has `robots_override: true`;
  - `notes`, `stale` and `stale_reasons`;
  - `award`, for scholarship facts only;
  - `source_batch`, only on a record merged in from a later dir than the entry's `source_batch`;
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

   **Robots override, KB evidence only (owner, 2026-10-19, expires at product launch).** AGENTS.md §6
   allows one exception: the KB evidence check may read the specific KB evidence URLs robots.txt
   refused, once per check. Never in the product, discovery, the live pipeline, benchmarks or crawls.

   ```bash
   PYTHONPATH=. python scripts/verify_evidence.py --trust-env-proxy \
       --robots-override-kb evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.ci-*.json
   ```

   - Scope: only rows whose CI outcome is `robots_disallowed` (a disallowing robots.txt, or one that
     could not be read, which RFC 9309 treats as a full disallow). A (case, item, URL) that also has a
     passing row, and any heldout case, is left out.
   - The production `Fetcher` with `kb_evidence_robots_override_urls` set to exactly those URLs: the same
     user agent (no spoofing), the host's Crawl-delay still honoured (up to 30 s, as above), one request
     per URL with no retry around a 403, 429, 5xx or block, no proxy rotation. A redirect to any other
     URL is still refused. The parameter's default is empty, and then the fetcher behaves exactly as
     before; nothing else passes it.
   - Each report gets `batch<N>/evidence_check.robots-override-<today>.json` beside it. Every row has
     `"robots_override": true` and `robots_override_used` (whether robots.txt actually refused the read;
     when it did, `robots_refusal` holds robots' reason). From the sandbox, robots.txt often answers
     where it did not answer CI, and then the read needed no override.
3. **Build.** From `backend`, run:

   ```bash
   python -m evaluation.research.expert.kb_build \
       evaluation/research/expert/data/kb_drafts.<date> \
       --evidence evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.ci-*.json \
                  evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.recheck-*.json \
                  evaluation/research/expert/data/kb_drafts.<date>/batch*/evidence_check.robots-override-*.json \
       --built-at <YYYY-MM-DD> --version <YYYY-MM-DD>.kb-cs-bachelor.<n>
   ```

   (`batch*` also matches nothing under `topup_imported/`: list its CI and recheck reports too, and
   those of every other `topup*` dir.)

   **Top-up dirs: answer-level merge.** The build reads `batch*` then `topup*` dirs in name order. A
   top-up core draft may hold only the answers it filled (`topup_round2`). When one `seed_id` has core
   drafts in several dirs, the first is the base and the later ones are merged into it, never swapped
   in:
   - The unit of the merge is a question. English is the exception: each test (IELTS overall, IELTS
     sub-scores, TOEFL, Duolingo) merges on its own fact key, because one English answer nests them all
     under one quote.
   - `documents` merges as one unit, like the other questions.
   - A draft that answers only `documents` (`topup_documents1`) is never the base, although its dir name
     sorts before `topup_imported`: the base is the first draft that answers a core question.
   - A later draft replaces a unit only when it is `known` or `not_applicable` there. Its `unknown`
     never overwrites a known or not-applicable record. With nothing known on either side, the
     unknown reason of the latest draft that answered the question wins.
   - Each draft is verified against the reports **in its own dir** only. The reports carry no quote, so
     a batch row for the same URL must not verify a top-up's different quote. A top-up the CI has not
     checked yet stays unknown. A report kept outside every `batch*`/`topup*` dir is read for all of
     them. A `seed_id` with a single draft is built exactly as before.
   - Provenance: the entry's `source_batch` is the base dir, and `source_batches` lists every dir merged.
     A fact, `not_applicable` or `unknown` record taken from a later dir carries its own `source_batch`.
   - Programme pages are the union over dirs, and a page a top-up restates counts once.

   The build writes `backend/app/knowledge/kb_cs_bachelor.json`, never `backend/data`.

   A value is `known` only when a CI or recheck report row for that case, item and URL has `official`
   and `quote_found` set. For one (case, item, URL) in both, a passing row wins; when both pass, the
   CI row is used. A report whose file name contains `container` (an ad-hoc pre-check from an agent's
   container) is skipped; a recheck report is a full evidence check of the rows it holds. Anything else is listed under `unknown` with its reason. The dev5/dev4 rules still
   apply: an undated deadline and an indicative GPA stay unknown.

   **Robots-override evidence.** A robots-override report (`robots-override` in its file name, or rows
   with `"robots_override": true`) is evidence too, ranked last: for one (case, item, URL) a passing CI
   row wins, then a recheck row, then an override row. An override row with
   `robots_override_used: false` (robots.txt allowed the read after all) counts as a recheck. A record
   verified only by a used override row gets `verified_by: "robots_override"` and
   `robots_override: true` (facts, programme evidence and `not_applicable` alike), its entry's
   `verified_on_basis` gains `+robots_override`, and it is listed at the top level under
   `robots_override_facts` (`seed_id`, `source`, `question`, `key`, `url`). `robots_override_excluded`
   says whether the build left them out.

   **Launch day (the exception expires).** Rebuild with the same command plus
   `--exclude-robots-override`: every override row is dropped and its records fall back to what the
   other checks say (usually `unknown` with the CI reason), so `robots_override_facts` is `[]`. Then stop
   running `--robots-override-kb`, and remove the exception from AGENTS.md §6 and the
   `kb_evidence_robots_override_urls` path from the `Fetcher` and the verifier.

   **"No institutional scholarship."** An expert `scholarship_exists` of `not_applicable` with a URL and
   a quote ("We do not offer any scholarships for bachelor's studies.") becomes one `not_applicable`
   record, `question: "scholarship_exists"`, `key: "scholarships"`, verified like any fact (unverified,
   it is `unknown`). The runtime turns it into the explicit "No institutional scholarship" outcome. The
   dataset converters (dev4/dev5) still write no scholarship keys for it.

   The year rules do not drop a verified value silently. A CI-verified fee for another academic year, or
   one with no year stated, is kept as a **stale** fact with the published year and the reason. So is a
   CI-verified deadline of a past cycle. A fee per semester or for the whole programme (Lund) keeps its
   `period` as published. It becomes a claim that says so, and it enters the yearly cost table only when
   its period is a year.
   **Two pending owner decisions (both off by default; add the flag to the build command to switch one
   on).** Each keeps a CI-verified value that the year rules above set aside. The value is shown as
   current with a `caveat`, and never as fully verified. Only a build with a flag on writes the top-level
   `owner_flags` and `caveat_facts`. A default build is byte-identical to one made before the flags existed.

   - `--yearless-deadlines-with-caveat` (`KB_YEARLESS_DEADLINES_WITH_CAVEAT`). A verified deadline whose
     quote prints the day and month but no year is kept. Its year is inferred from the intake's
     application cycle. For a fall (autumn) Y intake, August–December means Y−1 and January–July means Y.
     A fall start falls in Aug–Oct of Y and applications close before it. An Aug–Dec day can precede that
     start only in Y−1, and a Jan–Jul day in Y−1 would close a year early (the previous cycle). The
     August boundary errs towards "passed". The fact carries `value` (the inferred date), `year_inferred`
     and `caveat: "year not printed on the page; assumed current application cycle"`. It turns stale
     once that date passes. The flag refuses, and the reason is appended to the `unknown` record as
     "Year not inferred: …", in any of these cases:
     - the quote does not print that day and month;
     - the quote names another intake or round (early decision/action, round 2, semester 2, spring,
       summer, Sommersemester, mid-year, transfer, ED/EA);
     - the quote prints a year other than Y−1 or Y;
     - the expert's year differs from the inferred one, or the expert marks it as another cycle;
     - the intake is not a fall intake.
   - `--standing-fee-policy-current` (`KB_STANDING_FEE_POLICY_CURRENT`, NEXT_CYCLES Q7). A verified
     fee whose academic year is "not stated" is shown as current when its university is in
     `STANDING_FEE_POLICIES`. That is an explicit list of 13 standing fee policies: ETH, EPFL, FU Berlin,
     Heidelberg, UZH, KTH, Lund, IP Paris, Osaka, Nanjing, UCLA, Kyoto, ISCT. The fact carries
     `caveat: "fee policy page; no academic year printed"` and `standing_policy: true`, and its
     `academic_year` is cleared. Any published year text moves to `academic_year_stated`. It enters the
     yearly cost table only when its period is a year. A per-semester or whole-programme fee is listed
     on the Costs tab as "published per …", like any other.

   The claim notes carry the caveat as "Caveat: …." (`app.knowledge.CAVEAT_MARK`). The API keys it as
   `caveat_message` (`caveat.yearInferred`, `caveat.feePolicy`). The result detail shows the chip
   "Current, with caveat" instead of "Verified", and adds the caveat line beside the claim and the
   headline deadline (en/ru/kk).
4. **Commit.** Commit the KB file with the drafts and reports. `tests/test_knowledge_base.py` covers the
   converter, the merge, staleness and both modes.

## Refresh cadence

- **Every admissions cycle (at least yearly):** re-run the CI check on every batch and rebuild. Deadlines
  and fees go stale with the academic year. Facts older than 365 days show as stale automatically.
- **When a fact shows as stale or a page changes:** re-draft that university, re-check its batch and
  rebuild. Never edit the JSON by hand.
- **Monthly** in the September–January application season: re-run the CI check on the deadline items.

**Scheduled refresh (`.github/workflows/kb-refresh.yml`, free-search ticket 07).** Monthly on every item,
and weekly on deadlines from September to January, the workflow re-verifies the KB itself with no drafts
directory and no search: `scripts/verify_evidence.py --from-kb app/knowledge/kb_cs_bachelor.json
app/knowledge/kb_imported_dev.json [--only deadline,tuition]` turns every programme evidence record, fact
and `not_applicable` statement into one check row (same official-domain rule and report shape, plus
`seed_id`, `key`, `source`, `quote`, `final_url`; a document fact's item is its key `documents.<kind>`, and
`--only documents` keeps them all). `python -m evaluation.research.expert.kb_refresh_diff`
classifies each row (`verified`, `quote_gone`, `moved`, `http_404`, `not_official`, `http_403`,
`robots_refused`, `robots_unreachable`, `timeout`, `fetch_error`), compares it with the previous checks (`unchanged`,
`newly_verified`, `lost`, `new`), adds the KB's own staleness and writes the re-draft queue
`KB_REFRESH_<date>.md`. `python -m evaluation.research.expert.kb_build --refresh <kb.json> --evidence
<report.json> --out <copy.json>` writes a re-stamped copy: a record that still verifies gets the check's
date as `verified_on`; any other keeps its value and its old date and gets `review: {needed, class, …}`
and a line in `review_queue`. It never overwrites the built KB, and the workflow never commits: the
report, the queue and both copies come back as the `kb-refresh-<run id>` artifact, and a person decides.
The queue's "blocked" rows (403, robots.txt, time-outs) say nothing about the page; recheck them from the
sandbox with `--trust-env-proxy`. Running the workflow on the owner's computer (`runner: self-hosted`)
waits on owner question 01-Q4.
