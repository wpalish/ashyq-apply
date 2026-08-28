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
