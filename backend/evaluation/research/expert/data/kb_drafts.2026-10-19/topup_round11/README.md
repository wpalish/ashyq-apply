# KB gap fill, round 11: tuition shapes with no single yearly figure (CS bachelor, 2026-10-20)

This round tops up the merged knowledge base for one question, `tuition`, at three universities that
topup_round10 left unknown because their pages print **no single yearly fee**:

- UBC prints a per-credit rate only;
- Sheffield and UT Austin print a range only.

The KB can now carry both shapes as printed, without inventing a yearly figure
(`docs/process/KNOWLEDGE_BASE.md`, "Two fee shapes with no single yearly figure"):

- **per credit:** `value: {amount, currency, period: "credit"}`. It is never multiplied out and never
  enters the yearly cost table. The Costs tab says "published per credit (no yearly figure printed)".
- **range:** `value: {min, max, currency}`. It is kept only when both bounds are printed in the quote. It
  enters the cost table only as a range, and the cost and any remaining cost use the **upper bound**
  (said on the gap).

## Method

Same as topup_round10. Pages were read on 2026-10-20 with the production `Fetcher`, as
`scripts/verify_evidence.py` builds it:

- the `UnimatchBot/0.2` user agent;
- robots.txt honoured, with no override;
- `trust_env_proxy=True` (the sandbox HTTPS proxy, TLS verified);
- no cache.

Only the pages topup_round10 had already identified were used, all of them on official domains. No web
search was used and no held-out university was opened. Quotes are copied from the readable text that
the production extractor gives. The answers hold `tuition` only (topup_round6 shape).

## Files

- `core/<seed_id>.json`: three drafts.
- `evidence_check.container-2026-10-20.json`: the container pre-check, made with
  `PYTHONPATH=. python scripts/verify_evidence.py --trust-env-proxy <this dir> --out <file>`. It has
  **3 rows: 3 official + quote_found** (`ok`, HTTP 200). The file name contains `container`, so
  `kb_build` skips it.

The CI check is still needed: run `benchmark-capture.yml` with `mode=verify_evidence` and
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round11`, then save the report as
`topup_round11/evidence_check.ci-<date>.json`. Until then these answers stay unknown. **No KB rebuild was
done.**

A dry build (in memory only, with this container report standing in for CI) gives:

| seed_id | fact value | period | year | stale |
|---|---|---|---|---|
| qs2027-046 | 1,769.40 CAD | credit | 2026/27 | yes: "academic year 2026/27 is before the fall 2027 intake's 2027/28" |
| qs2027-083 | {min 27,650, max 34,670} GBP | year | 2027/28 | no: enters the cost table as a range, upper bound 34,670 |
| qs2027-072 | {min 42,554, max 51,106} USD | year | 2026-27 | yes: listed as "published range … (not current: …)" |

## Drafted (3)

| seed_id | university | shape | as printed | source |
|---|---|---|---|---|
| qs2027-046 | UBC | per credit | Row "Science" in the column "International per-credit rate (commenced in 2026S or later)": "$1,769.40" | `vancouver.calendar.ubc.ca/fees/tuition-fees/undergraduate` |
| qs2027-083 | Sheffield | range | "For the 2027/28 academic year, the University of Sheffield will charge new full-time overseas undergraduates, tuition fees between £27,650 and £34,670 (except for Medicine and Dentistry courses, see below)." | `www.sheffield.ac.uk/new-students/tuition-fees/undergraduate-overseas` |
| qs2027-072 | UT Austin | range | "Non-Resident Tuition $42,554-$51,106" (table "Fall & Spring Semesters for Full-Time Undergraduate", "2026-27 Estimated Costs", "Based on 12-hour enrollment") | `onestop.utexas.edu/managing-costs/cost-tuition-rates/cost-of-attendance/` |

### Scope and caveats for the reviewer

- **UBC: a correction to topup_round10.** Its README gave Science as "$1,789.18". That figure is the
  **Applied Science** row. The Science row in the same column reads **$1,769.40**, and that is what is
  drafted here.
  - The column's footnote 2 concerns students "starting their degree programs in the 2026/27 academic
    year", so the year recorded is 2026/27 and the fact is stale for a fall 2027 intake. No 2027/28
    rate is published.
  - The page prints no credit load and no yearly figure, and no yearly figure was computed.
  - That the CS B.Sc. is a Faculty of Science degree comes from the KB's programme page, not from the
    fee page.
  - The quote is the Science row (seven start-cohort columns) with "Social Work", the next row's label,
    as an anchor. "Science" alone also occurs in the domestic table and in "Pharmaceutical Sciences".
- **Sheffield: a university-wide range, not a CS figure.** The population says so: "new full-time
  overseas undergraduates, every course except Medicine and Dentistry". The CS amount sits behind the
  course page's JavaScript fee look-up on `tools.sheffield.ac.uk`, whose robots.txt is unreachable. The
  range is current (2027/28). With this draft, Sheffield's cost becomes the upper bound, £34,670, with
  the range shown, and the actual CS fee can be lower.
- **UT Austin: a range across all programmes, for 2026-27.** It is kept stale and listed, never used as
  this intake's cost.
  - Fall and Spring together are recorded as one year.
  - This page does not say which rate international students pay. That they pay the non-resident rate
    is batch5's reading, noted as such.
  - The catalog's per-semester tables (topup_round10) print no period, so they were not used.

## Not drafted

KCL (qs2027-037) and Birmingham (qs2027-069) still publish the international fee only in embedded page
data, not in readable text. The evidence check cannot match a quote there, so they stay unknown, as
topup_round10 found.
