# What counts as the programme page found

Type: grilling
Status: resolved
Blocked by: 01
Map: ../map.md · HITL + domain-modeling — this decision names terms for `GLOSSARY.md` and fixes the scorer's rule.

## Question

DoD target 3 says "the programme page is found", and the scorer (`evaluation/research/metrics.py`,
`programme_page_recall`) decides it by comparing canonical URLs with the gold list. On the development sets the
pipeline confirmed a page that *is* the programme but not the labelled URL in five cases: UCPH (English twin
`/studies/bachelor/computer-science` of the Danish gold, declared by `hreflang`), Paris-Saclay (English twin
of the French `licence`), Imperial (`/2027/computing-beng` beside `/computing-beng/`), UM (sibling
specialisations of one "Bachelor of Computer Science (X)"), Auckland (the CS-major plan page beside the BSc
page). Two others are the opposite risk: UCT confirmed "Bachelor of Business Science specialising in Computer
Science" and Chula a BSc in a different faculty than the labelled ICE programme. The owner already accepted
twins once (Warsaw `programmes-first` beside `programmes-all`, reviewed10). What is the general rule?

❓ **Q1** - **Language twin**: a page the confirmed page declares as its own alternate
(`<link rel="alternate" hreflang=…>`, same registrable domain) *is* the same programme page. Discovery records
the twin; the scorer accepts either URL.

➡️ Yes. The page itself asserts the identity; nothing is inferred.

---

❓ **Q2** - **Canonical variant**: the same path with or without an intake-year segment (`/2027/`), a language
query (`?lang=en`), a trailing slash or `index.html` is the same page.

➡️ Yes for year segment, trailing slash and `index.html`; for `?lang=` yes only when the page's `<html lang>`
confirms the language (today the scorer keeps the query because it can identify a programme, e.g. `?p7_code=`).

---

❓ **Q3** - **Sibling specialisation** ("Bachelor of Computer Science (Software Engineering)" vs "(Data
Science)"): *not* the labelled programme and *not* a false positive — report as **related programme** and
count neither as hit nor as wrong. Same for a **major page** (Auckland's CS-major plan vs the BSc page) and for
another computer-science bachelor of the same institution in a different faculty (Chula).

➡️ Yes. The applicant asked for "computer science, bachelor"; a sibling answers the question but the gold's
one URL is one expert's choice. A third outcome keeps the metric honest without punishing a right answer.

---

❓ **Q4** - **Business/joint degrees "specialising in" the field** (UCT's Business Science) are **wrong page**:
the degree title names another subject first.

➡️ Yes — `matches_field_text` already refuses a title whose extra words name another subject; "Business
Science" should be such a word (it is not today because "business" and "science" are short/common).

---

❓ **Q5** - **Glossary terms** to record once Q1–Q4 are answered: *programme page*, *programme twin*,
*canonical variant*, *related programme*, *wrong page*, *programme identity*. An ADR is **not** warranted
(reversible; not surprising once the glossary says it).

➡️ Yes.

## Evidence

- Twins and variants: [Language alternates](13-language-alternates.md), [Measurement gaps](14-measurement-gaps.md).
- Cases: `scratchpad/runs/bundle5-dev3/x/{ucph,um,auckland,chula,imperial}-on/*/*.json` (`programme_urls`),
  `scratchpad/runs/bundle5-dev2/x/{psaclay,uct}-on/*/*.json`; gold `evaluation/research/data/dev{2,3}.draft1.json`.
- Prior owner decision on twins: `ground_truth.reviewed10.json`, Warsaw `programme_urls` (three URLs).

## Answer

2026-10-18, the owner (Диас): **yes** via 02-Q1 — the recommended answers stand as written.

Accepted: Q1, Q2, Q3, Q4, Q5 — each recommended answer (➡️) above is the decision.
