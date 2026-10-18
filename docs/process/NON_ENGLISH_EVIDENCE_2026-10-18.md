# Non-English evidence pages behind the target-4 questions (finish-algorithm 07)

Date 2026-10-18 · research only, no product code · ticket
[07](wayfinder/finish-algorithm/issues/07-non-english-evidence-count.md), feeds HITL
[08](wayfinder/finish-algorithm/issues/08-non-english-evidence-route.md).

**Scope and evidence policy.** Gold: `ground_truth.reviewed10.json` (cohort), `dev2.draft1.json`,
`dev3.draft1.json`, `dev4.draft1.json`; every `known` label whose key is one of the six core questions
(the scorecard's `CORE_QUESTIONS` patterns). dev4 has **no** known core label (ticket 09 not landed); the 12
unadjudicated cases enter only through the draft labels already in dev2/dev3 (ticket 10 not signed). The
heldout nine were excluded by name in the label script; no heldout file, capture, log, label or page was opened,
and no word in §4 comes from a heldout page. Captures read: `scratchpad/runs/base2-{cohort,dev2,dev3}/x/`
(page outcomes, logs, `programme_url_aliases`).

**How the pages were fetched.** The production `Fetcher` cannot reach the web from this sandbox: it pins resolved
IPs and connects directly, and every robots.txt request ends in `ConnectError` (→ RFC 9309 "disallowed"; the
same trap as HANDOFF L1136). The 60 unique gold evidence URLs (85 known core labels) were therefore fetched once
by hand through the sandbox's HTTPS proxy with the production User-Agent string, after an explicit robots.txt
check (`urllib.robotparser`; 404 = allowed; unreachable robots = not fetched), 1 s per host, no retries, no
challenge solving. Pages, `<html lang>` and `<link rel="alternate" hreflang>` are in
`scratchpad/non_english_pages/` (`hand.json` maps URL → file); scripts in `scratchpad/ne07/`. Not fetched:
kaist ×2, hku ×2, chula ×2 (robots.txt unreachable from the sandbox; all English pages), kaznu ×2 (robots.txt
answers 302 to itself → treated as disallowed), tec ×3 (Incapsula 403 to the sandbox; CI reads tec.mx normally).

## 1. The table — every known core question whose gold evidence is not English

Language is the page's `<html lang>`; for PDFs, the text's language. "Twin" = an English page that carries the
same fact: **H** declared by `hreflang`, **S** only a language-switcher link, **P** a `/ru/`→`/en/` path twin
the pipeline already reads. "Read today" = the evidence URL (or its twin) appears in any base2 capture.

| # | case · set | label key (question) | evidence URL | lang | twin declared? | twin holds gold? | read today | route |
|---|---|---|---|---|---|---|---|---|
| 1 | warsaw · cohort | `scholarships.rektora.applicability.international` (schol_intl) | `monitor.uw.edu.pl/…/M.2021.215.Obw.18.pdf` | pl (PDF) | no (PDF). The award page `bpm.uw.edu.pl/en/rectors-scholarship/` is English (`hreflang` pl/en) | **no** — the English page names no nationality condition; "student cudzoziemiec" is only in the Polish regulation § clause | no | (iii), behind reachability (other host) |
| 2 | tec · dev2 | `english_evidence.toefl_ibt.minimum` = 72 (english) | `tec.mx/es/ingenieria-y-ciencias/ingenieria-en-tecnologias-computacionales` | es (URL `/es/`; page 403 to sandbox) | **H** — the English page declares `hreflang` en/es, x-default = this Spanish page | **yes** — "At least 72 points on the TOEFL iBT, or 40 points on the EUC…" | English twin read 4/4, discovery rejects it "reads as irrelevant, not a programme page" | **(i) already happens**; loss is the classifier |
| 3 | tec · dev2 | `scholarships.beca_al_talento_academico.exists` (scholarship) | `tec.mx/es/profesional/becas` | es (URL; 403) | not checked (403) | **yes, in English already in gold**: the regulation PDF `…reglamento_becas_preparatoria_profesional_eng.pdf` (the gold's own schol_intl evidence) says "Academic Talent. Designed to attract students…" | no | (i)-equivalent (English PDF on the same domain), behind reachability |
| 4–5 | uba · dev2 | `scholarships.beca_de_ayuda_economica.exists`, `.applicability.international` = false | `extension.uba.ar/noticias/beca-de-ayuda-economica-sarmiento/` | es-AR | **no** (no hreflang, no English link) | — | no | exists: (ii) ("Beca"); international=false: (iii) ("Ser argentino/a nativo/a o por opción, o extranjero/a con residencia permanente") |
| 6–7 | kaznu · dev2 | `scholarships.award.exists`, `.applicability.international` = false | `welcome.kaznu.kz/ru/admissions/foreign/foreign_rules/`, `welcome.kaznu.kz/ru/19388/page` | ru (URL `/ru/`) | **P** — `/en/19388/page` is read in CI 4/4 (page type `costs`, 1 447 chars, "no cost figures could be extracted"); hreflang not verifiable from the sandbox | unverified (robots.txt loop from here); needs one CI read of `/en/19388/page` + `/en/admissions/foreign/foreign_rules/` | twin read, not its evidence sibling | (i) candidate, unverified |
| 8 | utokyo · dev3 | `deadline` = 2026-12-07 | `u-tokyo.ac.jp/content/400291798.pdf` | ja (PDF) | no (PDF) | — | no | (iii): "出願期間 2026年12月1日(火)～12月7日(月)" appears beside a second window "2026年11月9日(月)～11月13日(金)"; the gold one is 第1種 (私費留学生) |
| 9–10 | utokyo · dev3 | `scholarships.award.exists`, `.applicability.international` | `u-tokyo.ac.jp/ja/admissions/tuition-fees/h01_02_03.html` | ja | **S** only — "English" → `/en/prospective-students/exemptions.html` (no hreflang) | **yes** for exists — "This system provides full or partial exemption from admission/tuition fees…"; international: the same eligibility table, no nationality condition (as in ja) | no | (i′) switcher twin, behind reachability |
| 11 | msu · dev3 | `gpa` (free text) | `cpk.msu.ru/files/2026/minimum.pdf` | ru (PDF) | no | — | no | none (B7 free-text label: no reader emits it in any language) |
| 12 | msu · dev3 | `scholarships.state_funded.exists` | `pk.cs.msu.ru/auslander_budget` | ru | **no** | — | no | (iii) — a state-funded place ("на бюджетной основе"), not a named award; a keyword table would not call it a scholarship |
| 13 | msu · dev3 | `scholarships.state_funded.applicability.international` | `cpk.msu.ru/files/2026/rules.pdf` | ru (PDF, 97 k chars) | no | — | no | (iii) |
| 14 | puc · dev3 | `deadline` = 2026-10-28 | `admision.uc.cl/vias-de-admision/admision-especial-y-complementaria/calendario/` | es | **no** | — | no | (ii) with risk — "Segundo período de postulación 28 de septiembre al 28 de octubre del 2026"; the first period "24 de agosto al 24 de septiembre" is on the same page |
| 15 | usp · dev3 | `scholarships.papfe.exists` | `prip.usp.br/…/PAPFE2026_EDITAL.pdf` | pt (PDF) | no | — | no | (ii) ("Programa de Apoio…", "auxílios financeiros") |
| 16 | usp · dev3 | `scholarships.papfe.applicability.international` | same PDF | pt (PDF) | no | — | no | (iii) — "Todos os estudantes regularmente matriculados…" is eligibility by enrolment, read as international only by inference |

Not counted, although CORE_GAP §1 filed them under A6: tec `…applicability.international` (gold evidence is an
**English** PDF), warsaw `rektora.exists` (`bpm.uw.edu.pl/en/…`, `lang="en"`), the three tsinghua labels (English
text with no `lang` attribute; their loss is the other registrable domain). Every other fetched known core
evidence page in cohort/dev2/dev3 declares `lang="en…"` (kaist, hku, chula not fetched; their URLs and gold
excerpts are English); ucph `gpa` is on the English `ku.dk/studies/…` page (it declares
`da-dk` as its twin, not the other way round).

## 2. Totals

| | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| known core questions (scorecard denominator) | 28 | 21 | 28 | 0 | 77 |
| **questions behind non-English evidence** | **1** (warsaw) | **6** (tec 2, uba 2, kaznu 2) | **9** (utokyo 3, msu 3, puc 1, usp 2) | 0 (no core labels) | **16** (≈21 %) |
| … whose evidence page (or twin) any run reads today | 0 | 3 (tec toefl twin; kaznu twin ×2) | 0 | — | 3 |
| reachable by (i) — twin declared and holds the value | 0 | 1 confirmed (tec toefl, H) + 1 via an English PDF already in gold (tec beca) + 2 unverified (kaznu, P) | 2 (utokyo exists + intl, switcher only — **not** hreflang) | — | 2 by hreflang/English PDF, +2 by switcher, +2 unverified |
| reachable by (ii) cleanly | 0 | 1 (uba exists) | 1 (usp exists) + 1 risky (puc deadline) | — | 2 (+1 risky) |
| left for (iii) | 1 (warsaw intl) | 1 (uba intl) | 5 (utokyo deadline, msu exists, msu intl, usp intl; puc deadline if (ii) is not trusted) | — | 7–8 |
| none (free-text label) | 0 | 0 | 1 (msu gpa) | — | 1 |

**The fact that decides 08: language is the first loss for at most 3 of the 16.** For 13 questions the evidence
page is never fetched in any of the base2 repetitions (`extension.uba.ar`, `admision.uc.cl`, `monitor.uw.edu.pl`,
`prip.usp.br`, `cpk.msu.ru`, `pk.cs.msu.ru`, the utokyo PDF and `h01_02_03` occur in no capture or log); the
loss there is reachability (other host, PDF, unknown programme), and no reader in any language changes it. Of the
3 that are read: tec toefl is already read **in English** and lost to the classifier ("irrelevant"), and kaznu's
English twin is read and lost to the costs reader. **Upper bound of (ii) or (iii) on today's captures: 0
questions.**

### Month names, decimal commas and other traps for (ii) — from these pages

- **Month names.** puc: "28 de septiembre al 28 de octubre del 2026 hasta las 13:00 horas"; usp: "22 de dezembro de
  2023"; msu: "31 августа", "c 20 июня по 30 августа" (genitive forms, not the nominative a dictionary lists).
  utokyo uses no month names but `2026年12月1日(火)～12月7日(月)` — the second date omits the year, and a weekday
  in parentheses sits inside the range (the same "(11AM)" problem ntutw has in English).
- **Several windows on one page.** puc has a first and a second "período de postulación"; utokyo has two
  categories with two windows. An English-style "first deadline after the keyword" rule picks the wrong one
  (Sept 24 at puc) — a new wrong claim, which the bar forbids.
- **Decimal comma and thousands dot.** usp "R$850,00"; warsaw regulation "skala … 6,0 lub 5,5" (a grade scale, not
  money); puc "$69.140" and "$101.430" (CLP thousands with a dot — read as 69.14 by an English number parser).
- **Restrictions are clauses, not keywords.** uba "Ser argentino/a nativo/a o por opción, o extranjero/a con
  residencia permanente"; kaznu "на платной основе за исключением студентов, поступающих на основании
  межправительственных соглашений"; warsaw "może otrzymać student cudzoziemiec, o ile spełnia warunki…". The
  international-eligibility question needs the clause's polarity, which a keyword table does not give.
- **The classifier comes first.** A Spanish programme page reads as `unknown` (tec, CORE_GAP §2), so (ii) also
  needs classifier words, or the readers never run.

## 3. Cost per route

| route | files touched | flag (proposed) | paired runs | expected gain on dev sets today | notes |
|---|---|---|---|---|---|
| (i) English twin of a question/award page | `adapters/discovery/live_discovery.py` (reuse `english_alternate`), `adapters/requirements/web_requirements.py`, `adapters/scholarship/web_scholarships.py` (queue the twin of a non-English question page as the next read) | `--evidence-english-twin` (loop id EV-T1) | 1 × 4 sets (~25 min each) | **0** today (no non-English question page is read); +2 utokyo only if switcher links were followed too, which `english_alternate` does not do | zero new words; 1 extra read per non-English page within 60 requests |
| (ii) per-language keyword tables | `adapters/extraction.py`, `adapters/structured_extraction.py`, `adapters/requirements/web_requirements.py`, `adapters/scholarship/web_scholarships.py`, `adapters/applicability.py`, `adapters/page_classifier.py`, one new word module + tests | `--local-language-keywords` (EV-L1), flag-off | 1 dev4-only design check (16-Q5) + 1 × 4 sets regression | **0** today; at most 2–3 once the pages are reached (uba exists, usp exists, puc deadline with wrong-claim risk) | month-name and decimal-comma parsing per language; the polarity of restriction clauses stays unread |
| (iii) model extractor (D9, proposer only; classifier/verifier still confirm) | new `adapters/llm_extraction.py` + wiring in the evidence stage; privacy-table row in SPEC §6.4 | `--model-extractor` (EV-M1) | 1 × 4 sets, then heldout look under ticket 21 | **0** today (same reachability); up to 7–8 once reached | see the next lines |

**(iii) privacy rows (`SPEC_matching_v2.md` §6.4).** The request carries public official page text plus the six
question names, and, for scope, only `preferences_only` fields — level, field (ISCED), intake. No row of the table
covers "public page text", so the owner must add one ("official page text and question schema: ✓ in both
modes"). No `profile_aware` field is needed: citizenship, GPA, test scores and budget never enter, because the
extractor proposes what the page says and the scorer applies it to the applicant afterwards.

**(iii) price per university** (provider's public list price, cached 2026-10-06; per million tokens): the six
questions read ≈ 6–10 evidence pages, ≈ 30–50 k input tokens (≈ 80 k when a regulation PDF such as msu
`rules.pdf` or the warsaw regulation, ~97 k chars each, is read) and ≈ 3 k output tokens.
Smallest current tier ($0.10 in / $0.50 out): **≈ $0.005–0.01 per university**. Mid tier ($2 / $10): **≈ $0.09–0.19
per university**. A paired run on the four development sets (44 universities × 2 repetitions, on arm only) costs
≈ $1 at the small tier, ≈ $8–17 at the mid tier.

## 4. Words for (ii), dictionary grade (16-Q5)

Only as dictionary translations; nothing here comes from a heldout page. Heldout-country languages (cs, de, tr, et,
it, lt, kk) are marked †. IELTS, TOEFL, Duolingo, SAT are proper nouns in every language.

| lang | deadline | tuition | scholarship | international / foreign |
|---|---|---|---|---|
| es | fecha límite, plazo, período de postulación, inscripción hasta | arancel, matrícula, colegiatura | beca | extranjero/a, estudiantes internacionales |
| pt | prazo, data limite, inscrições até | mensalidade, taxa de matrícula | bolsa, auxílio | estrangeiro/a, estudantes internacionais |
| ru / kk† (ru-language pages) | срок подачи, приём документов до | стоимость обучения, плата за обучение | стипендия, грант | иностранные граждане |
| pl | termin, termin składania | czesne, opłata za studia | stypendium | cudzoziemiec, cudzoziemcy |
| ja | 出願期間, 締切 | 授業料 | 奨学金, 授業料免除 | 留学生, 外国人 |
| da / no / sv | ansøgningsfrist / søknadsfrist / sista ansökningsdag | studieafgift / semesteravgift / studieavgift | stipendium | internationale studerende / internasjonale studenter / internationella studenter |
| de† | Bewerbungsfrist | Studiengebühren | Stipendium | internationale Studierende |
| cs† | termín podání přihlášek | školné | stipendium | zahraniční studenti |
| tr† | son başvuru tarihi | öğrenim ücreti | burs | uluslararası öğrenciler |
| et† | tähtaeg, avalduste esitamise tähtaeg | õppemaks | stipendium | välisüliõpilased |
| it† | scadenza | tasse universitarie, retta | borsa di studio | studenti internazionali |
| lt† | terminas, prašymų pateikimo terminas | studijų kaina | stipendija | užsienio studentai |
| kk† (kk-language pages) | құжат қабылдау мерзімі | оқу ақысы | стипендия, грант | шетел азаматтары |

Month names would need a table per language (incl. Russian/Polish/Czech/Lithuanian genitive forms), and a number
reader per locale (decimal comma, thousands dot or space).

## 5. Recommendation for 08

1. **Do not build (ii) or (iii) now.** On today's captures neither can gain a question: 13 of the 16 pages are
   never fetched, and the 3 that are read are already English twins. Record the 16 in the residue ledger
   (ticket 16) as "non-English evidence page", with reachability named as the first loss for 13.
2. **Route (i) is the cheapest and partly runs already** (tec, kaznu). The two concrete leftovers belong to other
   tickets, not to a language rule: tec toefl is a classifier rejection of an English page that states
   "72 points on the TOEFL iBT" (C1, worker A/B or ticket 05 territory); kaznu needs one CI read to say whether
   `/en/19388/page` and `/en/admissions/foreign/foreign_rules/` carry the "paid basis except intergovernmental
   agreements" fact (the sandbox cannot read kaznu's robots.txt).
3. **Revisit only if** dev4 core labels (ticket 09) show readable local evidence pages that the pipeline reaches.
   Then pick (iii) over (ii): 7–8 of the 16 need clause polarity or picking one window among several, which
   keywords cannot do without new wrong claims, and (iii) costs ≈ $0.01 per university at the smallest tier.

## Files

- `scratchpad/non_english_pages/` — hand-fetched pages (`<sha1[:10]>.{html,pdf,txt}`), untrusted data.
- `scratchpad/ne07/labels.py` (known core labels and evidence URLs, heldout excluded by name), `handfetch.py`
  (robots-checked fetch, production UA), `hand.json` (URL → status, lang, hreflang), `dump_text.py`,
  `grep_pages.py`, `fetch.py` (the production-Fetcher attempt that shows the sandbox `ConnectError`).
