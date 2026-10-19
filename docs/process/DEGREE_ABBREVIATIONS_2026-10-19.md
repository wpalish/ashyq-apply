# Degree abbreviations: reference table and dev audit (DA-2, 2026-10-19)

Worker, 2026-10-19. Question: tec's English programme page ("B.S. in Computer Science and Technology",
`/en/engineering-and-sciences/bs-in-computer-science-and-technology`) reads no degree level, because neither
"B.S." nor the slug `bs` is in the degree tables. Should the tables learn more abbreviations?

**The bar (set before the audit; against overfitting).** A word joins the tables only if (a) it is a standard,
dictionary-grade abbreviation of a degree at one level, and (b) the dev evidence shows it on **at least two dev
sets** (cohort, dev2, dev3, dev4).

**Verdict: no abbreviation passes both.** "B.S." and "Bc." pass (a) but each is seen on one set only. The flag this
ticket planned (`DEGREE_ABBREVIATIONS_V2`) was **not created**: it would have had nothing to switch on. No code
changed; the tables are as they were.

Development cases only: **no heldout file, capture, log or label was opened; dev5 was not touched; no search
provider was called.**

## 1. Reference table (written before any table was touched)

What a standard reference gives each abbreviation, per level and language, and what today's tables read. "Text"
is `page_classifier.degree_levels_named("<abbr> in Computer Science")` (the base table plus LX-1's and R1's words);
"slug" is `live_discovery.degree_level_named("…/study/<slug>-computer-science")`.

Sources (dictionary grade, per language):
- **en (US):** Merriam-Webster and the Chicago Manual of Style §10.20 (academic degrees): B.A., B.S., M.A., M.S.,
  M.B.A., Ph.D., LL.B., LL.M.
- **en (UK/IE/HK/AU/NZ):** QAA, *Frameworks for Higher Education Qualifications* (FHEQ) qualification titles: BA,
  BSc, BEng, LLB (level 6); MEng, MSci, MComp (integrated masters, level 7); MA, MSc, MRes, MPhil, LLM (level 7);
  PhD, DPhil (level 8).
- **en (IN):** UGC, *Specification of Degrees* (Gazette notification, 2014 and later): B.Tech., B.E., B.Sc. (first
  degree); M.Tech., M.E., M.Sc. (master's).
- **de:** KMK, *Ländergemeinsame Strukturvorgaben* (degree designations): B.A., B.Sc., B.Eng., LL.B. / M.A., M.Sc.,
  M.Eng., LL.M.; legacy Dipl.-Ing. (second-cycle equivalent).
- **cs/sk:** Czech Act No. 111/1998 Coll. §45–§46 and Slovak Act No. 131/2002 Coll. §52–§53: Bc. (bakalář), Mgr. and
  Ing. (magistr / inženýr, second cycle), Ph.D.
- **pl:** Act of 20 July 2018 (*Prawo o szkolnictwie wyższym i nauce*), professional titles: lic. (licencjat), inż.
  (inżynier) — first cycle; mgr (magister) — second cycle.
- **es (LatAm):** RAE, *Diccionario panhispánico de dudas*, abbreviations list: Lic. (licenciado/a), Ing.
  (ingeniero/a). In Spanish "Ing." is a professional title borne by holders of a first degree; in Czech and Slovak it
  is a second-cycle degree — one abbreviation, two levels.

| abbreviation | level | standard? (source) | today: text | today: slug | hazards |
|---|---|---|---|---|---|
| B.A. / BA | bachelor | yes (MW, QAA, KMK) | bachelor | `ba` bachelor | — |
| **B.S.** / BS | bachelor | yes (MW, CMOS) | **none** | **`bs` none** | "BS" = British Standard ("BS 7799", "BS EN ISO 9001"), company names ("BS Group"), slug `bs` in non-degree paths |
| B.Sc. / BSc / BSc (Hons) | bachelor | yes (QAA, UGC, KMK) | bachelor | `bsc` bachelor | — |
| BEng | bachelor | yes (QAA) | bachelor | `beng` bachelor | — |
| **B.Eng.** (dotted) | bachelor | yes (KMK) | **none** | `b-eng` none | — |
| **B.E.** | bachelor | yes (UGC) | **none** | `be` none | slug `be` is the English verb ("be-inspired") and Lithuanian "be" ("without") |
| B.Tech. / BTech | bachelor | yes (UGC) | bachelor (LX-1) | `btech`, `b-tech` bachelor | — |
| LLB | bachelor | yes (QAA) | bachelor | `llb` bachelor | — |
| **LL.B.** (dotted) | bachelor | yes (MW, KMK) | **none** | — | — |
| **Bc.** | bachelor | yes (CZ/SK law) | **none** | `bc` none | slug `bc` = "British Columbia", "BC" = "before Christ" |
| **lic.** / **Lic.** | bachelor | yes (PL law; RAE) | **none** | `lic` none | "Lic." also "licence/licensed" in English |
| **inż.** | bachelor (PL engineer) | yes (PL law) | **none** | — | — |
| **Ing.** | bachelor (es) / master (cs, sk) | yes, but level depends on language | **none** | — | one abbreviation, two levels: not addable without a language gate |
| BCompSc, BComp, BCS, BIT, BASc | bachelor | **no**: institution-specific award names (Canada, Australia, Singapore); BCS also British Computer Society, BIT also "bit" | none | none | fails (a) |
| M.A. / MA | master | yes | master | `ma` master | — |
| **M.S.** / MS | master | yes (MW, CMOS) | **none** | **`ms` none** | "Ms" honorific (slug `ms-<name>`), MS = multiple sclerosis, Microsoft |
| M.Sc. / MSc | master | yes | master | `msc` master | — |
| **M.Eng.** / **MEng** | master | yes (QAA, KMK) | **none** (BEng is read, MEng is not) | `meng` master | — |
| **M.E.** | master | yes (UGC) | **none** | `me` none | slug/word "me" |
| M.Tech. / MTech | master | yes (UGC) | master (LX-1) | `mtech` master | — |
| **MSci**, **MComp**, **MRes** | master | yes (QAA) | **none** | `msci` master; `mcomp`, `mres` none | — |
| MPhil | master | yes (QAA) | master | `mphil` none | — |
| LLM | master | yes (QAA) | master | `llm` master | — |
| **LL.M.** (dotted) | master | yes (MW, KMK) | **none** | — | — |
| **Mgr.** / **mgr** | master | yes (CZ/SK/PL law) | **none** | `mgr` none | — |
| **Dipl.-Ing.** | master | yes (KMK, legacy) | **none** | — | — |
| MBA | master | yes | master | `mba` master | — |
| Ph.D. / PhD | phd | yes | phd | `phd` phd | — |
| **DPhil** | phd | yes (QAA) | **none** | `dphil` phd | — |

Bold: a standard abbreviation today's tables do not read — the candidates the audit had to look for.

## 2. Dev audit

Searched, per dev set: every string of every non-heldout case in the gold files
(`ground_truth.reviewed11.json`, `dev2/dev3/dev4.draft3.json`: programme URLs, evidence URLs, excerpts, scope
programme names, notes); every URL and every label under 300 characters in the replay artifacts
`rp-base2-{cohort,dev2,dev3,dev4}` (`<case>.json`, `<case>.raw.json`: programme and ranked URLs, aliases,
`lead_found_by`, search results, walker candidates and outcomes, page diagnostics, rejected samples); and every
result URL in `recorded_search.base3.json` for those sets. Text forms were matched case-sensitively on a token
boundary, slugs on a `/`, `-`, `_` or `.` boundary. A hit "counts" only when today's tables miss it at the
abbreviation's level.

| candidate | sets where seen (cases) | degree use? | (a) | (b) |
|---|---|---|---|---|
| B.S. / `bs` | dev2 (tec) | yes | yes | **no (1 set)** |
| Bc. (text) | dev4 (ctu, vut) | yes | yes | **no (1 set)** |
| `bc` (slug) | dev4 (ctu: `/cs/bc-specializace-software`, `/cs/bc-minor-software`) | yes | yes | **no (1 set)** |
| BCS (text, slug) | cohort (toronto gold "First incoming BCS cohort"; ubc `/bcs-program-second-degree`) | yes | **no** | no (1 set) |
| BIT (text) | dev4 (vut gold: "Informační technologie (BIT)" — the programme's code) | programme code | **no** | no (1 set) |
| MEng (text) | dev3 (imperial result label "…(MEng)"; the slug `meng` is already read) | yes | yes | **no (1 set)** |
| `be` (slug) | cohort (aalto), dev2 (psaclay, tec, uct), dev3 (imperial), dev4 (ktu) | **never**: "be-inspired", "be-proud", "can-…-be-validated", Lithuanian "be" | — | **negative evidence, 4 sets** |
| `ms` (slug) | cohort (kaist: `/url_teams/ms-eunbin-carroll-lee/`) | **never**: the honorific "Ms" | — | negative evidence |
| B.Eng., B.E., LL.B., Lic./lic., inż., Ing., M.S., M.Eng., M.E., MSci (text), MComp, MRes, LL.M., Mgr., Dipl.-Ing., DPhil (text), BCompSc, BComp, BASc | none | — | — | no (0 sets) |

Already read today and seen (no action): B.Sc. (dev4 kit, rwth), B.Tech (dev3 iitd), BEng (dev3 imperial), slugs
`bsc`, `msc`, `beng`, `meng`, `msci`, `btech`, `b-tech`, `mtech`, `bachelor-of-science`, `bachelor-of-engineering`
(all four sets).

**Conclusion.** No standard abbreviation the tables miss appears on two dev sets. B.S. — the ticket's motivating
case — is tec's alone; Bc. is the two Czech dev4 cases' alone. The only abbreviation-shaped slugs seen on several
sets (`be`, and `ms` once) are never degrees there: they are the evidence *against* a loose slug table.

## 3. What was not done, and what would change the verdict

- No word, slug or flag was added; `DEGREE_ABBREVIATIONS_V2` does not exist. tec's English twin keeps reading
  IRRELEVANT on its own head (pinned by `test_tecs_english_twin_names_no_level_the_tables_know`).
- `tests/test_degree_abbreviations.py` fences the negatives a future addition must keep (British Standards, company
  names, the "Ms" and "be" slugs) and pins the table rows above that are read today.
- Re-open when a second dev set shows B.S./`bs` (US, Korean, Mexican, Philippine or Middle-Eastern universities use
  it as the standard title), or Bc. (any other Czech or Slovak case). Then: "B.S." as a dotted, case-sensitive token
  followed by "in"/"of" (never bare "BS"), and `bs` only as a slug segment followed by `-in-`/`-of-`.
- Separate observation, not acted on (not a new word): `_DEGREE_SLUGS` matches on `/` and `-` only, so
  `BSc_TI_…pdf` (cohort delft), `MSc_Computer_Science_STO.pdf` (dev3 ucph) and `btech_links/` (dev3 iitd) read no
  level. All three are study-guide PDFs or link pages, not gold programme pages.

Scripts: session scratchpad `da2/audit.py`, `da2/loose.py`, `da2/store.py`, `da2/today.py`; nothing from them is
committed.
