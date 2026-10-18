# Sitemap keep rule: evidence sum or structure first

Type: grilling
Status: open
Blocked by: 01
Map: ../map.md · HITL — a precision-vs-recall rule the owner approves before the loop builds it.

## Question

The sitemap stage's `keep()` discards a URL the moment it carries no structural programme word
(`/programmes/`, `/bachelors/`, `opleidingen`, …), *before* adding the subject and level bonuses
([URL lexicon audit](09-url-lexicon-audit.md)). Seven of the 39 development gold URLs name the subject in the
slug (six of them the level too) and are dropped for that reason: `study.um.edu.my/bachelor-of-computer-
science-<x>` ×4, `ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/`,
`aufnahmeverfahren.univie.ac.at/en/computer-science`, `…/formation/licence/informatique`. The confirm stage
reads every kept candidate through the classifier, so a wrongly kept URL costs a read, not a wrong page.

❓ **Q1** - **Keep on evidence sum**: a URL is kept for the programme category when `matches_field +
matches_degree > 0` even if the structural score is 0 — but only when the slug names the subject *and* the
level (both bonuses positive), or the subject as an exact field slug (`exact_field_slug`), so a bare
`/en/computer-science` on an admissions host still qualifies while `/research/computer-science-lab` does not
(no level, excluded path words aside).

➡️ Yes.

---

❓ **Q2** - **Cap**: evidence-only picks fill at most 10 of the 40 per-category slots and never displace a
URL with a structural score, so a site with hundreds of `bachelor-of-<x>` slugs cannot push the structural
picks out; the confirm order stays score-descending, so these picks are read only when the structural ones
are refused.

➡️ Yes.

---

❓ **Q3** - **Measurement bar** (the loop's, restated so the owner sees it): paired run on all development
sets; required no stable programme-page loss anywhere and `+1` on um or uba (dev gold) with reads not above
today's; the rule ships behind a flag until then.

➡️ Yes.
