# Subject match on local programme titles

Type: grilling
Status: resolved
Blocked by: 01, 03
Map: ../map.md · HITL + domain-modeling — what a programme title may contain and still name the applicant's field.

## Question

`matches_field_text` accepts an alias only when every other word in the title is filler, so three
development gold pages that *are* computer-science bachelors are refused after being read
([Classifier audit](10-classifier-audit.md)): `Informatikk: programmering og systemarkitektur` (uio),
`Bachelor in de informatica (Leuven) - Studieprogramma` (kuleuven), `Licenciatura en Ingeniería en Ciencia de
la Computación` (puc). The same function accepts the applicant's *own* words with no check on the rest, which
is how "Bachelor of Business Science specialising in Computer Science" (uct) passed. The owner has already
ruled that "Computer Science and Engineering" and "Ingegneria/Enginyeria Informàtica" are related, not
equivalent. Which title shapes are the field, and which are not?

❓ **Q1** - **Subtitle after a colon or dash is not the subject**: `Informatikk: programmering og
systemarkitektur` → subject `Informatikk`; `Bachelor in de informatica (Leuven) - Studieprogramma` → `Bachelor
in de informatica`. The head before `:` / ` - ` / ` – ` is tested; the tail is ignored.

➡️ Yes.

---

❓ **Q2** - **A location in parentheses and a form word are filler**: `(Leuven)`, `(Hons)`, `(International)`,
`Studieprogramma`, `Studiengang`, `programme` — already partly in `_LOCAL_TITLE_FILLER`; the campus guard
(CG-1) still refuses a *foreign* campus.

➡️ Yes.

---

❓ **Q3** - **Spanish/Portuguese "Ingeniería en Ciencia(s) de la Computación" is computer science** (a
`licenciatura` whose degree is "Licenciado en Ingeniería en Ciencia de la Computación"), while "Ingeniería
Informática" / "Ingegneria Informatica" / "Enginyeria Informàtica" stay computer engineering, as already
decided. Record the first as an `es` localized alias with the ontology's "not in doubt" note.

➡️ Yes — the title names the science, the engineering word names the award's faculty.

---

❓ **Q4** - **Symmetry**: the applicant's own field words get the same remaining-words test as aliases, with
"Business", "Engineering", "Economics", "Mathematics" (and the ontology's `related_not_equivalent` heads) as
*non*-filler — so "Business Science specialising in Computer Science" and "Computer Science and Engineering"
are refused as the programme page (reported as related), and "Mathematics and Computer Science" too.

➡️ Yes.

---

❓ **Q5** - **Glossary**: record *programme title*, *subject head*, *filler word*, *related field* once
Q1–Q4 are answered.

➡️ Yes.

## Answer

2026-10-18, the owner (Диас): **yes** via 02-Q7 — the recommended answers stand as written (02-Q7: the listed title shapes only).

Accepted: Q1, Q2, Q3, Q4, Q5 — each recommended answer (➡️) above is the decision.
