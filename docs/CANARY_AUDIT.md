# Live canary truth audit

Every material claim the system made in a live run, checked by hand against the
page it came from. Run on 2026-08-28 against `rug.nl` and `tudelft.nl` in live
mode (no fixtures), with `candidate_limit=2`.

**Release blocker: zero known false-positive material claims.** Currently met
for these two institutions.

## Run summary

| | |
|---|---|
| Pages fetched | 10 (1 unreadable) |
| Fetch tiers | http 12, browser 0, pdf 0 |
| Material claims produced | 2 |
| False positives | **0** |
| Universities reported eligible | 0 — both `NEEDS_OFFICIAL_CLARIFICATION` |

## Claim-by-claim

### 1. `scholarship_exists` — Justus & Louise van Effen Excellence Scholarships

| Check | Result |
|---|---|
| **Claimed** | An award named "Justus & Louise van Effen Excellence Scholarships" exists |
| **Source** | `tudelft.nl/en/education/study-programme-orientation/practical-matters/scholarships/justus-louise-van-effen-excellence-scholarships` |
| **Quoted** | "Justus & Louise van Effen Excellence Scholarships At TU Delft a number of scholarships are available for excellent international applicants." |
| **Quote is on the page** | ✅ verbatim, from the content region |
| **Source type appropriate** | ✅ `scholarship_administrator`, page classified `scholarship_award` |
| **Programme / degree / intake match** | Award page, not programme-scoped — n/a for existence |
| **False positive?** | **No.** The award is real and the page is its own page. |
| **Left unknown** | amount, coverage, deadline, international eligibility, `available_this_intake` |

Degree applicability was assessed separately and correctly:

| Applicant | Verdict | Evidence quoted from the page |
|---|---|---|
| bachelor | **no** | "You are not eligible for the Justus & Louise van Effen Excellence Scholarships if: You are a TU Delft bachelor's student…" |
| master | **yes** | "You are an international student applying for a TU Delft MSc programme…" |

This is the FP-6 fix working on the real page: the award is not offered to the
demo applicant, and the system says so with the university's own words.

### 2. `scholarship_exists` — Costas Lemos Innovation Programme Scholarship

| Check | Result |
|---|---|
| **Claimed** | An award named "Costas Lemos Innovation Programme Scholarship" exists |
| **Source** | `tudelft.nl/en/delft-university-fund/we-support/support-innovative-education/clip-scholarship` |
| **Quoted** | "Costas Lemos Innovation Programme Scholarship The Costas Lemos Innovation Programme (CLIP) Scholarships have been established to equip excellent Greek students…" |
| **Quote is on the page** | ✅ verbatim |
| **Source type appropriate** | ✅ `scholarship_administrator`, page classified `scholarship_award` |
| **False positive?** | **No.** |
| **Left unknown** | amount, coverage, deadline, international eligibility |

Degree applicability:

| Applicant | Verdict | Why |
|---|---|---|
| bachelor | **no** | "The scholarships are available to students entering the academic year 2026 for one of the following specific TU Delft Master of Science Programmes" |
| master | **yes** | same sentence |

The page also restricts by nationality ("hold either a Greek passport or Greek
residence"). The system does **not** currently extract that — a recall gap
recorded below, not a false claim.

## What the run did not claim, and why

Each of these is reported to the user with its reason rather than guessed at.

| Not claimed | Reason given |
|---|---|
| Any programme exists at Groningen | No official programme page was located by discovery |
| Any programme exists at TU Delft | The located page classified as `program_catalog`; a catalogue does not confirm a programme |
| Any admission requirement | No accepted page class was reached for the requested programme |
| Any intake status | No page stated an application window for the cycle asked about |
| Any cost figure at either university | Both fee pages are JavaScript fee calculators; the figures are not in the served HTML |
| Any award from the Delft scholarships index | Classified `scholarship_index` — an index is not an award |
| Any award from the Delft scholarship FAQ | Classified `scholarship_faq` |
| Any award from "Scholarships from other providers" | Classified `scholarship_index` — a plural heading with a scope phrase |

## Before / after

The same run before P0:

| | Before | After |
|---|---|---|
| False-positive material claims | **6+** | **0** |
| Fabricated 404s from bad URL joins | 6 per institution | 0 |
| Synthetic sentences shown as quotes | yes | none |
| MSc award offered to a bachelor applicant | yes | no |
| Run aborted by a PII-guard false positive | yes | no |

## Known recall gaps (not blockers, but recorded)

1. Nationality restrictions in prose ("hold a Greek passport") are not extracted.
2. Live discovery finds landing pages more reliably than programme pages, so
   both institutions report `NEEDS_OFFICIAL_CLARIFICATION` for the programme.
3. Fee calculators yield no figures; a Playwright escalation does not help
   because the numbers are behind a form, not merely rendered late.
4. Only two of the five canary institutions have been audited this cycle.
   Aalto, Vienna and Warsaw remain outstanding.

## Method

```bash
cd backend
UNIMATCH_DEMO_MODE=false PYTHONPATH="$(pwd)" \
  ./.venv/bin/python /tmp/canary.py "University of Groningen" "Delft University of Technology"
```

The script prints every claim with its type, value, status, source specificity,
URL and quoted excerpt. Each row above was then opened in a browser and checked
against the live page.

---

# Registry expansion — nine institutions, 2026-09-05

Phase 6.3 of the audit fix plan: widen live coverage beyond the original ten,
with priority on Central Asia and the destinations Kazakh applicants actually
apply to. Every institution below was canaried the day it was added.

## What was added, and what it reaches

| Institution | Country | Access | Programme page | Scholarship page | Pages ok/fail | Claims | False positives |
|---|---|---|---|---|---|---|---|
| Nazarbayev University | Kazakhstan | REACHED | **yes** | **yes** | 35/0 | 0 | 0 |
| Middle East Technical University | Turkey | REACHED | no | no | 9/3 | 0 | 0 |
| Sabanci University | Turkey | REACHED | no | no | 6/3 | 0 | 0 |
| Charles University | Czech Republic | REACHED | no | no | 5/3 | 1 | 0 |
| Masaryk University | Czech Republic | REACHED | no | **yes** | 8/0 | 0 | 0 |
| Technical University of Munich | Germany | REACHED | **yes** | **yes** | 21/0 | 0 | 0 |
| University of Tartu | Estonia | REACHED | no | **yes** | 18/1 | 2 | 0 |
| Politecnico di Milano | Italy | REACHED | no | no | 9/0 | 0 | 0 |
| Vilnius University | Lithuania | REACHED | no | no | 11/0 | 0 | 0 |

Nine reached, none blocked, **zero false positives**. Programme pages: 2 of 9,
which is better than the 1 in 10 the original registry manages but is the same
weakness, not a solved problem. Scholarship pages: 4 of 9.

All 52 seeds in the enlarged registry resolve (`--check-seeds`), including the
33 that were already there.

## How the seeds were chosen

Each candidate URL was fetched and passed through the product's own
`classify_page`. Only URLs the classifier recognised as the category they are
filed under were kept; a category with no such page has **no seed** rather than
a plausible-looking one. A seed that resolves to a landing page spends the
fetch budget and returns nothing, which is worse than having none.

`rankings` and `attributes` are absent from all nine entries. The original ten
carry QS positions and campus attributes that a person checked. Filling those
in from memory would put unsourced values on screen, which is the single thing
this product refuses to do; the preference components that read them will
report the data as missing, which is true.

## Evaluated and not added

| Institution | Why not |
|---|---|
| Jagiellonian University | `robots.txt` disallows the English site. Refusal is final: nothing here retries with another agent or a different path |
| Koç University | The homepage returns an HTTP error to an ordinary client |
| American University of Central Asia | Homepage classifies as navigation; no admissions, costs or scholarship page could be verified |
| University of Central Asia | The admissions link on its own homepage 404s |
| Universiti Malaya | Its study portal classifies as `irrelevant` — no page could be verified |
| Boğaziçi University, ELTE, TalTech | No verifiable English-language seed pages reachable from the homepage |

Six institutions were rejected to add nine. That ratio is the honest cost of
"verified seeds" meaning something.

## Two defects in the canary itself

Running it is what found them. Both were in the script, not the product.

1. **The canary could not run at all.** It created its applicant profile
   without an organization, relying on a `dev-org` column default that Phase 4
   removed on purpose. Every run since had died on a NOT NULL constraint — in
   its own throwaway database, so nothing else noticed.

2. **`--only` narrowed the report but not the run.** Discovery still read the
   whole registry, so asking about one institution ran the first N in file
   order and then reported the institution you asked about as `NOT_ATTEMPTED` —
   an answer that looks like a finding about the university and is really a
   finding about the tool.

## A release gate that could not pass

Charles University was reported with **one false positive**, the first this
project has ever recorded. It was not one.

The check demands that a decided admission requirement name its source. It read
that source from `check.requirement.claim_type` and `check.requirement.source_url`
— but `RequirementCheck.requirement` is the requirement's *name*, a plain
string, and the provenance lives in `claim_ids`. No string has those
attributes, so the branch could never pass: any decided requirement was a false
positive. Its skip list was dead too, naming statuses (`"unknown"`,
`"needs_clarification"`) that `EligibilityStatus` has never defined.

It went unseen because for ten institutions no live requirement was ever
decided — everything came back `NEEDS_OFFICIAL_CLARIFICATION` — so the branch
was never reached. Charles University reached it, and the gate accused the
product of something it had not done. The requirement did name its source:
`https://cuni.cz/UKEN-329.html`.

A release gate that cannot pass is worse than no gate, because the instinct on
a red gate is to change the product. Both bugs are fixed and
`tests/test_canary_checks.py` now holds the check to its own contract —
including that a requirement with no claim behind it is still caught.
