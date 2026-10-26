# KB gap fill, round 7: English (CS bachelor, 2026-10-20)

This round tops up the merged knowledge base (`app.knowledge.load_knowledge_base()`) for one question,
`english`: the IELTS overall and sub-score minimums, the TOEFL iBT minimum, and any other test the page
lists. The target is the CS bachelor recorded in each KB entry, for an international applicant entering in
fall 2027.

**Result: no English minimum was filled.** Of the 12 universities that could be researched from the
container, 8 publish no minimum score, or publish one only for another route. The other 4 still cannot be
read. Each draft records the question as `unknown`, with the reason as of today. The build never lets an
`unknown` overwrite a known record. Of the unknown reasons, the latest one wins.

## Method

The research was done on 2026-10-20. Web search was used only to find official URLs, never as evidence,
and no paid API was used. Every page was read with the production `Fetcher` (the `verify_evidence`
reader):

- the `ASHYQApplyBot` user agent, with no spoofing and no WAF bypass;
- robots.txt honoured, including wildcards. The KB-only robots override was not used: it covers only KB
  evidence URLs during the evidence check;
- the sandbox HTTPS proxy (`trust_env_proxy=True`), with TLS verified.

Only official domains were used, and no held-out university was opened. Before researching, the merged KB
and the topup_round3 and topup_round5 READMEs and drafts were read.

## Selection

The merged KB has 48 entries with no `english` fact:

- **24 hold `not_applicable`** and were not redone. These are Stanford, Harvard, ETH, Peking, Tsinghua,
  JHU, EPFL, Chicago, Fudan, PSL, Tokyo, KU Leuven, Amsterdam, LMU, Kyoto, Sorbonne, Paris-Saclay, UBA,
  Heidelberg, Nanjing, Copenhagen, Science Tokyo, FU Berlin and UZH. Most are taught in another language;
  the rest have no English test requirement.
  - *Copenhagen:* web search shows that ku.dk accepts Cambridge C1/C2 for the specific requirement
    "Engelsk B", but not IELTS or TOEFL. That page was not read.
  - *Kyoto iUP:* web search shows that the October 2027 guidelines give typical TOEFL/IELTS scores of
    successful applicants, not minimums. That page was not read.
- **24 are unknown.** Of these, 12 were left out because their official sites refuse the container (see
  "Needs the CI read"). The other 12 were researched, and each has a draft in `core/`.

## Files

- `core/<seed_id>.json`: one draft per researched university, in the topup_round3/round5 shape. Each
  draft's `answers` holds only `english`, with `status: unknown` and the reason.
- `evidence_check.container-2026-10-20.json`: the container pre-check, made with
  `scripts/verify_evidence.py --trust-env-proxy topup_round7`. Result: **72 rows, 0 checked, 0
  verified**. Each of the 12 drafts produces 6 rows, all `unknown` with outcome `-`, so there was no URL to
  check and nothing failed. `kb_build` skips this file because its name contains `container`.

A CI run is optional, because no draft is `known`. If one is run, use `benchmark-capture.yml` with
`mode=verify_evidence` and
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round7`. It would only re-confirm
the unknown rows.

## Per university

| seed_id | university | result | reason (details in the draft) |
|---|---|---|---|
| qs2027-004 | Oxford | unknown (access) | Both www.ox.ac.uk pages tried answer HTTP 403: the English language requirements page and the CS course page. The department site only defers to the University's requirements. **Needs the CI read.** |
| qs2027-010 | NUS | unknown (access) | The nus.edu.sg/oam international-qualifications and English pages return HTTP 200 with an empty body (bot wall). The CS page at comp.nus.edu.sg states no score. **Needs the CI read.** |
| qs2027-015 | UPenn | unknown (no minimum) | admissions.upenn.edu gives only "Competitive applicants tend to have" levels: TOEFL 5 on the new scale or 100 on the old scale, and Duolingo 130. |
| qs2027-017 | Yale | unknown (no minimum) | A test is required. admissions.yale.edu/standardized-testing gives only "most competitive applicants" benchmarks: TOEFL 5 on the new scale or 100 on the old scale. |
| qs2027-042 | Yonsei | unknown (no score) | The 2027 guide covers Spring (March 2027) entry, cycle_stated "2027학년도 3월 신입학". It asks for one language proof ("택1": Korean or English test, language-school certificate, or English-medium classes) with no threshold. No Fall 2027 guide has been published. |
| qs2027-045 | Northwestern | unknown (no minimum; re-check blocked) | Rounds 2 and 3 found a test required with "no minimum score". Today the robots.txt of admissions.northwestern.edu and catalogs.northwestern.edu was unreachable (ConnectError), which counts as disallowed. |
| qs2027-049 | UCLA | unknown (no minimum) | admission.ucla.edu gives "competitive" scores only: TOEFL 5 (sub-scores 5) or above 100 (sub-scores above 24), IELTS 7.5, DET 135. A UC-wide minimum would sit on universityofcalifornia.edu, which is not a ucla.edu official domain, so it was not used. |
| qs2027-052 | CityUHK | unknown (access) | Every www.cityu.edu.hk admo and international page returns HTTP 200 with an empty body, and www.admo.cityu.edu.hk does not resolve. **Needs the CI read** of `/admo/admissions/non-jupas-year-1-admission`. |
| qs2027-053 | Korea University | unknown (no minimum for the route) | The Fall 2026 guide (cycle_stated "Fall 2026") accepts TOEFL iBT or IELTS Academic as one alternative, with no score. Its IELTS 7.0 / TOEFL 100 figure is for major assignment in the Global Open Major, not for CS. The 2027 guides at the same path answer 404. |
| qs2027-054 | NTU | unknown (programme language not confirmed) | csie.ntu.edu.tw is readable now, but no page states the bachelor's teaching language. oiasystem.ntu.edu.tw is disallowed by robots.txt. The 2027 guidelines set B2 English for English-taught programmes and A2 Chinese for Chinese-taught ones. |
| qs2027-074 | UIUC | unknown (no minimum) | A test is required ("This requirement cannot be waived"), but "You don't need a set score to be admitted". The published minimums apply to transfer applicants only. |
| qs2027-095 | Osaka | unknown (not readable) | The programme is Japanese-taught, with April 2027 entry. The FAQ says some faculties set a TOEFL score as an application condition. The AY2027 guidelines PDF is 5.3 MB, over the Fetcher's 5 MB limit (`too_large`), and the text layer of the 入学者選抜要項 PDF is garbled. |

## Needs the CI read (left out: the official site refuses this container)

These have no draft in this round. They need a read from CI, or from a reader the site does not refuse.

| seed_id | university | known block |
|---|---|---|
| qs2027-009 | UCL | Cloudflare 403 on www.ucl.ac.uk |
| qs2027-011 | HKU | admissions.hku.hk unreachable |
| qs2027-018 | CUHK | admission.cuhk.edu.hk has an incomplete TLS chain |
| qs2027-023 | Melbourne | Cloudflare / Incapsula bot challenge |
| qs2027-027 | Princeton | refused from the container; round 3 found a test required but no threshold |
| qs2027-031 | Monash | handbook English level only in embedded JSON; monash.edu refused |
| qs2027-043 | Columbia | HTTP 403 (CloudFront) |
| qs2027-051 | Michigan | Cloudflare 403 |
| qs2027-058 | NYU | HTTP 403 on every admissions page |
| qs2027-065 | KAIST | admission.kaist.ac.kr robots.txt unreachable |
| qs2027-085 | Durham | HTTP 403 (CloudFront) |
| qs2027-096 | Alberta | AWS WAF challenge / 403 |

KU Leuven (qs2027-059) was also on the refused list, but its KB entry already holds `not_applicable`
(Dutch-taught). Oxford, NUS and CityUHK, in the table above, are also access cases. They have unknown
drafts because they were re-tried today.
