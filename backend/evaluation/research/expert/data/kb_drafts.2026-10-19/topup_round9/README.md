# KB gap fill, round 9: scholarships (CS bachelor, 2026-10-20)

This round tops up the merged knowledge base (`app.knowledge.load_knowledge_base()`) for two questions,
`scholarship_exists` and `scholarship_international`. The target is the CS bachelor recorded in each KB
entry, for an international first-year applicant (for example from Kazakhstan) entering in fall 2027.

Only institutional or government awards that a first-year international bachelor applicant can apply for
count. An award is `international` only if the page says international students are eligible. A
need-based aid policy counts if the page says it covers international students. Coverage is noted as
printed.

## Method

The research was done on 2026-10-20. Web search was used only to find official URLs, never as evidence,
and no paid API was used. Every page was read with the production `Fetcher` (the `verify_evidence`
reader):

- the `ASHYQApplyBot` user agent, with no spoofing and no WAF bypass;
- robots.txt honoured, with no override;
- the sandbox HTTPS proxy (`trust_env_proxy=True`), with TLS verified.

Only official domains were used, and no held-out university was opened. Before researching, the
topup_round3, topup_round5 and topup_round6 READMEs were read. Questions that those rounds had already
left unknown were re-checked only where a new official page was found.

## Selection

The gaps were listed from the merged KB: entries with no `scholarship_exists` fact and no scholarship
`not_applicable`, or with `scholarship_exists` known and `scholarship_international` missing. No held-out
university is in the list. These entries were skipped because their sites are already recorded as
blocking the container: Oxford (004), UCL (009), CUHK (018), Melbourne (023), Monash (031), Michigan (051),
CityUHK (052), NYU (058), KU Leuven (059), Durham (085) and Alberta (096). That leaves 8 entries.

## Files

- `core/<seed_id>.json`: one file per university with a researched answer, in the topup_round5 shape.
  `answers` holds only the two scholarship questions.
- `evidence_check.container-2026-10-20.json`: the container pre-check,
  `scripts/verify_evidence.py --trust-env-proxy topup_round9`. **Result: 6 rows checked, 6 official +
  quote_found** (`ok`, HTTP 200). The file name contains `container`, so `kb_build` skips it.

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round9`. Save its report as
`topup_round9/evidence_check.ci-<date>.json`. Until that report exists, these answers stay unknown. No KB
rebuild was done.

## Filled

| seed_id | university | question | value | coverage as printed | source |
|---|---|---|---|---|---|
| qs2027-044 | IP Paris (École Polytechnique BSc) | scholarship_exists | Need-based tuition fee waiver (École Polytechnique Bachelor of Science) | Partial: "will only partially cover fees or expenses". The amount "will depend on the family's resources". The EUR 1,500 administration fee is always due. Applied for after admission. | `programmes.polytechnique.edu/en/bachelor/costs-and-funding/scholarships-and-financial-aid` |
| qs2027-044 | IP Paris | scholarship_international | true: "All other candidates, i.e. international, European and French students not entitled to the CROUS bursary, may benefit from need-based financial aid …" | — | same page |
| qs2027-056 | Universiti Malaya | scholarship_exists / _international | **not_applicable**: "We do not offer scholarship to the Undergraduate International Students." | — | `aasd.um.edu.my/faq-ug-international-admission` |
| qs2027-091 | Copenhagen | scholarship_exists / _international | **not_applicable**: "The University of Copenhagen does not offer financial support or scholarships to foreign students." | — | `www.ku.dk/studies/admission/bachelor` (new page since round 5) |

### Notes for the reviewer

- **IP Paris, merge effect (decision needed).** `kb_build` merges `scholarship_exists` as one answer, so
  this draft replaces the base Excellence Scholarship fact. Excellence pays EUR 4,800 a year for 3 years,
  is for honours admits only, and has no stated international eligibility (re-read today: the page says
  only that the school admits students "from all over the world"). The waiver is the one École
  Polytechnique award on the page that names international students, and any admitted applicant can
  apply for it. It is not narrower, unlike the round-3 Olympiad award. But it is need-based and its size
  is not printed. If the Excellence award should stay the KB's answer, drop `core/qs2027-044.json` before
  the CI check. The existing `scholarship_international` unknown reason then stands.
- **Universiti Malaya.** The undergraduate financial-aid list (last updated 14/10/2026) has one item for
  international students, the "PTE x Universiti Malaya Scholarship 2026" (GBP 3,000 towards tuition,
  deadline 31 December 2026). Its link goes to pearsonpte.com. Pearson, the PTE test vendor, runs it, so
  it is neither institutional nor governmental and does not count. Every other item on that list is a
  Malaysian government, state, corporate or loan scheme.
- **Copenhagen.** The Danish Government Scholarship at UCPH requires admission "to a master's degree
  programme" (`ku.dk/studies/admission/scholarships-for-full-degree-students`). The Health faculty's
  2nd-year award is for students already in their second year.

## Left unknown

None of these got a file. For an `unknown` `scholarship_exists`, the builder (`propose_scholarship`)
writes the generic reason "Expert did not establish a scholarship" and drops the draft's notes, so a file
would add nothing. For IP Paris and UT Austin, a file would replace a more specific existing reason.

| seed_id | university | reason |
|---|---|---|
| qs2027-072 | UT Austin | scholarship_international: no page says international students are eligible for the incoming-freshman scholarships. Re-read today: the CNS future-students page (`cns.utexas.edu/info-admitted-students/scholarships-future-students`) says "All applicants will be considered for university-wide scholarships and CNS scholarships using the admissions application", but it does not name international students. The admitted-freshman page sends international students to Texas Global. The ISSS awards there are the ones the main session already rejected in round 6 (USD 2,000–5,000, mostly after two semesters at UT). The existing specific unknown is kept. |
| qs2027-034 | PSL (Dauphine) | No Licence award is open to a non-EU applicant on the Paris campus (round 5). The merit exemption for non-EU students is for Master 1 and 2 only, and CROUS needs French tax residence. A search found no new official page. |
| qs2027-037 | King's College London | No international undergraduate entry award was found on kcl.ac.uk. The funding pages list hardship funds, such as the International Hardship Fund of up to GBP 6,000 for students already enrolled (`self-service.kcl.ac.uk/article/KA-01819/en-us`), and a sanctuary scholarship. The Geography scholarship is for another subject and an old cycle. Same as round 5. |
| qs2027-073 | Sorbonne | No Sorbonne award for incoming international L1 students. Mobility grants are for exchange, from L2 onward. The rest is the national fee-exemption policy and state grants (round 5). A search found no new official page. |
| qs2027-076 | Paris-Saclay | The tuition-fees page (`universite-paris-saclay.fr/en/admission/tuition-fees`, re-read today) gives non-EU students "a partial exemption, which brings the differentiated registration fees in line with the fees applicable to domestic students" (resolution CA-2026-013). That is fee policy, a `tuition` matter, not an award to apply for. The 2026–2027 individual fee-waiver procedure is "published shortly". No Licence scholarship was found. |

Not researched (container-blocked, see Selection): 004, 009, 018, 023, 031, 051, 052, 058, 059, 085, 096.
