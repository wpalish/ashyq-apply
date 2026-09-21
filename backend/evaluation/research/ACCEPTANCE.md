# V2-01 acceptance record

**The corpus is certified.** On **2026-09-21**, **Диас**, the repository owner,
reviewed all ten cases of draft7 and signed them. `ground_truth.reviewed.json`
(`2026-09-21.reviewed`, SHA-256 `726bb1226ef6a234b1e4f5086f9a0df88697e7e32d70b242da0d1898e3897797`)
carries `review.status: human_verified`, `reviewer` and `verified_on` on 10/10
cases, and `metrics.reviewed.json` is the first report in this project's history
produced **without `--allow-drafts`**. It reports `provisional: false`.

```sh
# From backend — the strict command, no flag
python -m evaluation.research --dataset evaluation/research/data/ground_truth.reviewed.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.reviewed.json
```

## What the human review changed

The review was not a rubber stamp. It rejected one case outright and corrected
another, both confirmed against primary sources before being applied in draft7:

- **Aalto** pointed at the Finnish-language tietotekniikka programme. Real page,
  true facts, wrong programme: the requested scope is an international applicant
  and that route is not open to one in English. Identity and teaching language
  moved to the English-taught Computer Engineering major.
- **HKU** was missing its offering school and carried an approximate programme
  title. Both fixed from the admissions page.

**One decision is the owner's, not the data's.** Aalto describes Computer
Engineering as combining information technology and electrical engineering, and
draft2 refused the analogous equivalence for Data Science. The owner was shown
that conflict and accepted the major as satisfying the computer-science request.
It is recorded as a decision in the Aalto case notes, with the reasoning it
overrides preserved. Revisiting it returns that case to `unknown`.

## What the baseline actually measures — read this before quoting a number

These figures measure **the current research pipeline against the frozen
capture**, not the quality of the corpus. They are the "before" picture V2-01
exists to establish, and they are poor:

| Metric | Value |
|---|---|
| Programme page recall | **1/10** |
| Programme page precision | 1/9 |
| Claim precision | **0/5** |
| Claim recall | **0/62** |
| Wrong-scope claim rate | **5/5** |
| Critical field coverage | **0/210** |
| Primary-source rate | 13/13 |
| Claim adjudication rate | 5/13 |
| Support adjudication rate | 0/13 |

The pipeline located the right programme page for one university in ten, and
**every claim it produced was out of scope** — the right fact about the wrong
population, year or programme. Coverage of critical fields is zero. This is the
number architecture changes must beat; do not present it as a product result.

Two denominators are zero (`conflict_visibility_rate`, `current_evidence_rate`,
`unsupported_claim_rate`), so no rate can be inferred from them. Support
adjudication is 0/13: nothing has been independently adjudicated for support,
and a certified corpus does not change that.

## Scope of the certification

Signed: the ten cases' source annotations as of draft7 — 62 known labels of 220,
10/10 programme identities. **Not** signed, because they were never claimed:
the 158 fields that remain UNKNOWN, any fall 2027 applicability the sources do
not state, and the pipeline's own output. The Kazakhstan intake, fees and the
general SAT/IELTS policy for several cases are still open, and a later draft that
adds them needs its own signature — certification is of a version, not of the
corpus forever.
