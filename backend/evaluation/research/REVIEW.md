# Human review queue — V2-01

Status: **0/10 human verified**. Prepared by gpt-6-astra; no human signature is implied.

For each case, open the primary sources and confirm programme identity and requested scope.
Complete requirements, fees, award applicability/coverage and document labels in `data/ground_truth.json`.
Do not copy missing values from pipeline predictions. Retain UNKNOWN where the official source is insufficient.
Record minimal quotes, population/intake/year scope, reviewer identity and review date; increment the dataset version.
Resolve the site-architecture tags against observed sources before using them as validated strata.

| Case | Exact URL status | Known labels / total | Official review sources |
|---|---|---|---|
| University of Groningen | known | 3/16 | [source](https://www.rug.nl/bachelors/computing-science/?lang=en) |
| Delft University of Technology | unknown | 1/16 | [source](https://ocw.tudelft.nl/programs/bachelor/computer-science-engineering/) |
| Aalto University | unknown | 1/16 | [source](https://www.aalto.fi/en/study-options/data-science-bachelor-of-science-and-master-of-science-technology) |
| University of Vienna | known | 1/16 | [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science) |
| University of Warsaw | known | 1/16 | [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/) |
| University of British Columbia | known | 1/16 | [source](https://you.ubc.ca/programs/computer-science-vancouver-bsc/) |
| University of Toronto | unknown | 1/16 | [source](https://future.utoronto.ca/data-computer-science) |
| University of Hong Kong | known | 1/16 | [source](https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science) |
| Nanyang Technological University | known | 1/16 | [source](https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science) |
| KAIST | unknown | 1/16 | [source](https://cs.kaist.ac.kr/content?menu=318) |

Acceptance requires all ten cases reviewed, not merely ten signatures on empty records.
Specifically resolve four unknown exact programme URLs, requirement scope, award identity and independently adjudicated evidence support/currentness/conflicts.
After review, run the offline scorer **without** `--allow-drafts` and inspect each metric denominator.
Only after V2-01 acceptance proceed to V2-10 (provider-neutral SearchProvider).

## Scope pitfalls confirmed during preparation

- Groningen's linked [English requirements](https://www.rug.nl/fse/education/admission-and-application/apply-bsc/language?lang=en)
  are explicitly for 2026–2027: IELTS Academic overall and each component are 6.5.
  Do not silently apply that academic year to the requested fall 2027 intake.
- Vienna's programme page currently lists a 2026 entrance-exam cycle, German as an
  admission requirement and a EUR 50 administration charge. That charge is not
  tuition; the dates are not a confirmed fall 2027 deadline. Check its separate
  [tuition page](https://studieren.univie.ac.at/en/tuition-fee/) for population rules.
- UBC's programme page exposes selectable qualification requirements; its static
  view showed IB requirements. Do not label those as Kazakhstan national-school
  credentials. Follow the qualification selector and the separate
  [English admission standard](https://you.ubc.ca/applying-ubc/requirements/english-language-competency/).

These preparation notes were checked on 2026-09-20 and are not human signoffs or
additional scored labels. They explain why an apparently relevant page is not
enough to populate the requested scope.

## Candidates for the next reviewed dataset version

These inputs have now been incorporated into the separate AI-prepared
[draft2 candidate](REVIEW_DRAFT2.md), with remaining scope gaps kept UNKNOWN.
Draft1 remains frozen; neither candidate has human certification.

These additional sources were found after freezing draft1's baseline. They are
review inputs, not retroactive changes to its denominator.

- Toronto: the official [Computer Science programme page](https://future.utoronto.ca/program/computer-science)
  lists BCS majors/specialists at Mississauga, Scarborough and St. George, with
  different OUAC codes and default Ontario qualifications. The departmental
  [BCS announcement](https://web.cs.toronto.edu/bachelor-of-computer-science)
  should be checked alongside it for the September 2027 transition. Select and
  record campus/programme scope before accepting interchangeable programme URLs.
- KAIST: the [undergraduate roadmap](https://cs.kaist.ac.kr/content?menu=320)
  provides a Computing major curriculum and distinguishes major/double-major/minor
  credits. Its note dates the roadmap to 2025. It is not a fall 2027 international
  admissions or scholarship policy; use the linked admissions source for those.
- Delft: the main bachelor programme URL could not be read with the research
  browser in this session. The OCW page establishes curriculum context but should
  not be substituted for an admissions page. Resolve it using an accessible
  official source and record the final canonical URL.
