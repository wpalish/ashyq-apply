# KB top-up for the 21 imported universities (core answers)

Expert top-up of `backend/app/knowledge/kb_imported_dev.json` (rows with `status: import_existing` in
`backend/evaluation/research/data/kb_top100_list.json`), researched 2026-10-19 without live search
(official domains only, robots.txt honoured, production `ASHYQApplyBot` user agent, no bypass).

## File shape

One file per seed id (`<seed_id>.json`), in the dev5/batch core format, with two extra keys:

- `questions_researched`: the questions this top-up answers (only questions **missing** from
  `kb_imported_dev.json`).
- `questions_already_known_not_researched`: questions that were already known in the KB. These are
  **omitted** from `answers` (not re-researched, not marked `not_researched`), so the evidence check
  only sees the new items.

`programme.page_url` is copied from the KB for context; programme pages were not re-researched
(see `../programme/README.md`).

Statuses: `known` (value + verbatim quote + URL), `not_applicable` (quote shows the question does not
apply, e.g. a Dutch/German/Danish/French/Spanish-taught programme has no English test, or admission
has no grade minimum), `unknown` (reason in `notes`, including access failures).

## Container evidence check

`evidence_check.container-2026-10-19.json`: every known / not_applicable item re-read from the
saved page (curl with the production UA after a robots.txt check) and matched with
`verify_evidence.quote_in` offline. 45 rows; 41 official + quote found. The 4 others are expected:

| case | item | why |
|---|---|---|
| qs2027-014 Tsinghua | english, tuition | `international.join-tsinghua.edu.cn` is not a suffix of the listed `tsinghua.edu.cn`; it is Tsinghua's international admissions site (linked from www.tsinghua.edu.cn/en/Admissions.htm via apply.join-tsinghua.edu.cn) - add `join-tsinghua.edu.cn` to `extra_domains`. Quotes found. |
| qs2027-046 UBC | tuition | value is in the page's inline cost-estimator script, not readable text |
| qs2027-091 UCPH | tuition | value is in the page's inline programme-fee script, not readable text |

## Access failures (recorded as unknown, not bypassed)

- HKU `admissions.hku.hk`: TLS verify fails (curl 60); `www.admissions.hku.hk`: connection reset (curl 35).
- KAIST `admission.kaist.ac.kr`: TLS verify fails (curl 60).
- UBA `www.uba.ar/internacionales/...`: timeout (curl 28).
- KU Leuven `www.kuleuven.be`: intermittent connection resets, read after retries;
  `/opleidingen/bachelor-informatica*` is disallowed by robots.txt (not read).
