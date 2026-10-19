# Heldout label audit: heldout.reviewed1 → heldout.reviewed2 (draft) — 2026-10-19

Owner decision H-2 (`HELDOUT_PREREGISTRATION_2026-10-18.md` §9). This audit checks the signed heldout labels
against the conventions the owner signed for the development corpora: ticket 02, Q1–Q8, the dev4
programme-page rulings and the ticket 19 amendment. It also checks them against the scorer changes made since
2026-10-17.

- **Nothing here is signed.** `heldout.reviewed1.json` is unchanged and stays the scoring default. The proposal is
  `backend/evaluation/research/data/heldout.reviewed2.draft.json` (`2026-10-19.heldout-reviewed2-draft`). Every case
  in it is `review.status = draft` with no reviewer.
- **Blind to pipeline output.** The auditor opened the labels, the identity bindings and the expert drafts the labels
  were built from (`expert/data/core_drafts.2026-10-17`). It also fetched the nine universities' official pages: the
  production user agent, robots.txt honoured, the agent's own outbound proxy, no bypass.
  - It opened no capture, log, scorecard, summary or run artifact, and nothing under the heldout quarantine.
  - It does not know what the pipeline answered, and no line below is motivated by it.
- **No scorer or pipeline code changed.** The bindings file is unchanged as well (rule h: no line needed, see below).

## Changes per rule

| rule | what it checks | changes |
|---|---|---|
| (a) | population from an "international / non-EU / overseas" source; descriptive strings normalised (02-Q2/Q3) | **0** |
| (b) | official university name; the scorer's name-parts and acronym rule | **0** |
| (c) | degree scope; a page naming two levels is silent | **1** |
| (d) | prose GPA → `unknown` (02-Q7) | **2** |
| (e) | per-semester fee as published, `period: semester` (02-Q4) | **0** |
| (f) | programme pages: twins and canonical variants, closest equivalents related, evidence-URL twins (02-Q8) | **8** |
| (g) | an international applicant's deadline is the international round, with population (02-Q5) | **0** |
| (h) | award bindings: alternate URL spelling on the same host (02-Q1), key alias (02-Q2) | **0** |
| (i) | labels of another programme → `not_applicable` (02-Q6) | **5** |
| | **total** | **16** |

Label statuses across the nine cases: known 25 → 18, unknown 22 → 25, not_applicable 17 → 21. Cases with a known
programme page: 9 → 7 (metu and polimi become related-only, as dev4's boun, itu, vut and taltech).

## Changed labels

All quotes were checked word for word with `scripts/verify_evidence.py`'s own `normalise` / `quote_in` /
`title_in`. Each check ran on the readable text (`app.adapters.extraction.readable_text`) of the page, which was
fetched here. See "Quote verification" for how and what remains to run in CI.

| # | rule | case · label | before → after | evidence (verbatim) |
|---|---|---|---|---|
| 1 | c | masaryk · `scholarships.accommodation.applicability.international` | known `true` → **unknown** | fi.muni.cz/students/international-studies/admission.html.en, the label's only evidence: "The Master's Degree Programmes are open to students holding a Bachelor's or equivalent degree." The page is scoped to master's programmes; the MU accommodation page states no nationality condition. |
| 2 | d | nu · `gpa` | known "NIS Grade 12: BBB (regular admission) / ABB (grant competition); NUET 120 …" → **unknown** | Prose, as 02-Q7 (ntu "A in all subjects …"). The text stays in the note. |
| 3 | d | sabanci · `gpa` | known "70 (percent, average diploma score (Attestat))" → **unknown** | Prose, as 02-Q7 (um "65% minimum average (SHSC)"). The text stays in the note. |
| 4 | f | metu · programme page | programme `catalog.metu.edu.tr/program.php?fac_prog=571` → **related** (`programme_urls` empty, status `unknown`) | "An undergraduate program leading to a Bachelor of Science degree in Computer Engineering started in the 1977-1978 academic year." Computer Engineering is related, not CS. That was the owner's dev4 ruling for Boğaziçi and İTÜ, and ticket 19 keeps computer engineering related. |
| 5 | f | polimi · programme page | programme `…/dettaglio-corso/ingegneria-informatica` → **related**, plus its English twin `…/en/education/laurea-programmes/programme-detail/engineering-of-computing-systems` (hreflang en-US) | Title "Ingegneria Informatica" / "Engineering of Computing Systems". Ticket 19 names "Ingegneria Informatica" as computer engineering (related). Owner question 2 below. |
| 6 | f | tum · programme page | + German twin `tum.de/studium/studienangebot/detail/informatik-bachelor-of-science-bsc` | hreflang de-DE of the labelled page: "Der Bachelorstudiengang Informatik vermittelt solide theoretische, praktische und technische Fähigkeiten." |
| 7 | f | masaryk · programme page | + Czech twin `muni.cz/bakalarske-a-magisterske-studijni-programy/22955-informatika` | Same programme id 22955: "Informatika – bakalářské studium". The old spelling `…-obory/…` redirects there. |
| 8 | f | tartu · programme page | `ut.ee/en/curriculum/science-and-technology` → **`ut.ee/et/oppekavad/informaatika`** | "Õppeaste bakalaureuseõpe Õppekeel eesti keel". The labelled page is not CS: "Students can choose a combined specialisation in genetics and biotechnology, bioengineering and robotics, or chemistry and materials science." The English "Computer Science" page is the master's. Owner question 1. |
| 9 | f | tum · `ielts.overall` | + twin evidence URL `…/application-info-portal/admission-requirements/language-certificates` | The labelled URL redirects there (canonical). Same quote: "DSH-2 A DSH passed with an overall result of at least DSH-2 is considered proof of linguistic study ability for admission or enrollment to all degree programs and degrees." |
| 10 | f | tum · `ielts.subscores` | same twin | same |
| 11 | f | vilnius · `gpa` | + twin evidence URL `vu.lt/stojantiesiems/bakalauro/informatika` | The labelled URL redirects there (canonical). Same quote: "Asmenims, vidurinį išsilavinimą įgijusiems 2025 ir 2026 metais, minimalus konkursinis balas yra 4;" |
| 12 | i | tartu · `ielts.overall` | known 6.0 → **not_applicable** | Informaatika page: "eesti keele oskus vähemalt B2-tasemel". The requirement is Estonian, not English. The 6.0 belongs to the English-taught Science and Technology bachelor. |
| 13 | i | tartu · `ielts.subscores` | known {5.5 ×4} → **not_applicable** | same |
| 14 | i | tartu · `gpa` | not_applicable, evidence moves from the Science and Technology page to the Informaatika page | "Kandideerimiseks peab punktisumma olema vähemalt 66." This is a points score, not a grade average, so the label stays not_applicable. |
| 15 | i | tartu · `scholarships.tuition_fee_reduction.exists` | known `true` → **not_applicable** | The reduction is stated "For this programme" on the Science and Technology page. Informaatika: "Õppetasu tasuta" (tuition-free). |
| 16 | i | tartu · `scholarships.tuition_fee_reduction.applicability.international` | known `true` → **not_applicable** | same |

Every changed label's `notes` starts with `Label audit 2026-10-19 (H-2, unsigned), rule (x): …` and keeps the old
note after `Was:`. tartu `english_evidence.toefl_ibt.minimum`, `deadline` and `tuition` stay `unknown`:
- the Informaatika page says the 2027 terms appear by the end of December;
- its "tasuta" names no year.

## Checked and not changed

- **(a) population.**
  - No known fee, deadline or English label has an international-only source. nu, charles, sabanci and tartu
    English apply to all applicants; masaryk's deadline is the single round. Every heldout fee is `unknown` (the
    2027/28 fee is not published).
  - Award labels whose quote says "international" are a different matter: nu Abay Kunanbayev ×2, metu discount
    ×2, sabanci admission ×2, charles CSTFS applicability, tum waiver applicability.
    - The development corpora give award labels no population. The `applicability.international` key already
      states it.
    - A controlled population on a label requires the claim to record that population (D1: silence is judged).
    - So adding one here would make the heldout stricter than development. Owner question 3.
- **(b) names.**
  - All nine are the official English names: Nazarbayev University, Middle East Technical University, Sabancı
    University, Charles University, Masaryk University, Technical University of Munich, University of Tartu,
    Politecnico di Milano, Vilnius University.
  - The acronym rule covers METU and TUM (≥ 3 initials). The name-parts rule covers page titles such as
    "Masaryk University | MUNI" and "Informatics - … - TUM".
  - A page that writes only the local name ("Vilniaus universitetas", "Univerzita Karlova") does not match the
    English name. No development corpus puts a local name in the scope, so nothing is changed. If this matters, it
    is a scorer question, not a label one.
- **(c) degree.**
  - Pages naming bachelor's and master's together are silent on degree, so the bachelor label stands:
    - charles CSTFS ("Bachelor’s or Master’s Programmes");
    - tum waiver ("Bachelor’s and Master’s");
    - charles SIS (bachelor section; master's below);
    - the tartu English page.
  - Only the FI page in item 1 is master's-only.
- **(e) per semester.**
  - metu's 1,200 USD per semester and tum's 3,000 EUR per semester would carry `period: semester`. Both stay
    `unknown` for another reason: neither is the 2027/28 figure.
    - metu's published table is 2026–2027.
    - tum's tuition page announces an increase "for the winter semester 2027/28" (bachelor "2,300 euros or 3,400
      euros"), and the programme's band is not published.
- **(g) deadlines.**
  - No heldout deadline is known except masaryk's single round ("Application deadlines: 1 November 2026 – 28
    February 2027"), which has no international round.
  - nu's international round for visa-requiring countries is "To be announced later". polimi's non-EU visa date
    is the 2026/27 cycle. Both stay `unknown`.
- **(h) bindings.**
  - Every award binding URL was re-opened under its other spellings: `www.` or no `www.`, and with or without a
    trailing slash. Each lands on the bound URL, and `canonical_url` drops the slash. No second source URL is
    needed.
  - No heldout label uses `sat.minimum`, so the 02-Q2 key alias has nothing to bind.
  - The language twins of the award pages are declared by hreflang (tum DE, sabanci TR, metu TR, nu KK/RU,
    polimi IT). They have another final path segment, which ID-1 does not cover, and binding them is not a signed
    convention. Owner question 4.
  - tartu's `scholarships.tuition_fee_reduction` binding is left as is. Its labels become not_applicable (item 15).
- **Outside the nine rules (not applied).** Three `unknown` labels were set aside only because the expert's
  number was not in the excerpt. The page does state it:
  - charles Duolingo 130: SIS "- Duolingo: 130";
  - metu TOEFL iBT 75;
  - tartu TOEFL 75, which is moot after item 8.
  - They are not convention corrections, so they are not in the draft. They can be a later corpus task.

## Owner questions (also in the table below)

1. **Tartu** (items 8, 12–16). Science and Technology has no computer-science specialisation. The university's CS
   bachelor is the Estonian-taught Informaatika. The recommendation is to move the case to Informaatika. The
   alternative is to drop Tartu from the heldout CS set.
2. **Polimi** (item 5). The English twin's body also says "The Bachelor’s degree in Computer Science and Engineering
   (Ingegneria Informatica)". The ticket 19 amendment makes "Computer Science and Engineering" CS. Ticket 19 itself
   names "Ingegneria Informatica" as computer engineering, and the page's title is "Engineering of Computing
   Systems". The recommendation is related, as drafted. Choosing "programme" instead keeps both URLs in
   `programme_urls`.
3. **Population on award labels:** recommended no, as on development.
4. **Language-twin award bindings:** recommended not now. It is a new convention for every set, not a heldout
   correction.

## Quote verification

- Container pre-check: **12/12 new or moved quotes found, 54/54 corpus excerpts in the draft found** (the
  programme rows found by `title_in`, the same as in production).
  - The pre-check uses `verify_evidence`'s matching functions over pages fetched through the agent's proxy. The
    production `Fetcher` refuses that proxy by design.
  - Report: `backend/evaluation/research/expert/data/heldout_audit_drafts.2026-10-19/container_precheck.2026-10-19.tsv`.
- **To run in CI** (authoritative, production `Fetcher`): `benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/heldout_audit_drafts.2026-10-19`.
  - That directory holds 12 one-quote drafts in the dev4 format: a programme quote stands in the `title` slot, and
    an answer quote in its item.
  - Its output is the quote check alone. It holds no pipeline answer.
  - A line whose quote fails there is withdrawn before signing.

## После подписи

The agent will:
- rename the draft `heldout.reviewed2.json` (`2026-10-19.heldout-reviewed2`, `human_verified`, reviewer Диас),
  with only the signed lines;
- add a `VERSIONS.md` entry.

The main session then re-scores the frozen heldout run once, summary only (§9 H-2). No rule changes.

---

## Таблица для подписи (владелец)

Все строки — исправления меток отложенной выборки по правилам, которые уже подписаны для учебных выборок. Ответы
программы при этом никто не смотрел. Цитаты проверены по официальным страницам.

| № | Что меняется | Почему | Рекомендация |
|---|---|---|---|
| 1 | Масарик: «стипендия на жильё доступна иностранцам» → «не установлено» | Единственный источник — страница факультета только для магистратуры | **Да** |
| 2 | Назарбаев: требование к оценкам (текст про NIS BBB/ABB) → «не установлено» | Это описание словами, а не число; так же решено для NTU, UM, UCPH, MSU | **Да** |
| 3 | Сабанджи: «70 % средний балл аттестата» → «не установлено» | То же правило, что для UM («65 % minimum average») | **Да** |
| 4 | METU: Computer Engineering — не сама программа CS, а связанная | Так решено для Boğaziçi и İTÜ: найденная страница — не попадание и не ошибка | **Да** |
| 5 | Politecnico di Milano: Ingegneria Informatica — связанная, добавить её английскую страницу | По правилу «Ingegneria Informatica — компьютерная инженерия». Но в тексте английской страницы есть «Computer Science and Engineering». Если считаете это CS — скажите «программа» | **Да, связанная** |
| 6 | TUM: добавить немецкую версию страницы программы как двойника | Страница сама объявляет её своей немецкой версией | **Да** |
| 7 | Масарик: добавить чешскую версию страницы программы как двойника | Тот же номер программы 22955; старый адрес перенаправляет туда | **Да** |
| 8 | Тарту: программа Science and Technology → Informaatika (бакалавр CS, на эстонском) | В Science and Technology нет CS: генетика, биоинженерия и робототехника, химия | **Да** (иначе убрать Тарту из выборки) |
| 9–10 | TUM: у двух меток английского добавить новый адрес той же страницы | Старый адрес перенаправляет на новый, цитата та же (как с Delft) | **Да** |
| 11 | Вильнюс: у метки оценок добавить новый адрес той же страницы | То же: перенаправление, цитата та же | **Да** |
| 12–13 | Тарту: IELTS 6.0 и баллы по частям → «не применимо» | Для Informaatika нужен эстонский B2, а не английский. 6.0 относится к другой программе | **Да** (если да по строке 8) |
| 14 | Тарту: оценки — по-прежнему «не применимо», источник — страница Informaatika | Там тоже приём по баллам (не меньше 66), а не по среднему баллу | **Да** (если да по строке 8) |
| 15–16 | Тарту: скидка на обучение (есть / для иностранцев) → «не применимо» | Скидка — только для Science and Technology; Informaatika бесплатна | **Да** (если да по строке 8) |
| В1 | Ставить «для иностранцев» в метки стипендий, где на странице написано international | В учебных выборках так не делали; иначе отложенная выборка станет строже учебных | **Нет** |
| В2 | Привязывать стипендию и к её странице на другом языке | Новое правило для всех выборок, не исправление | **Не сейчас** |

Перед подписью: прогнать проверку цитат в CI (`mode=verify_evidence`, папка
`evaluation/research/expert/data/heldout_audit_drafts.2026-10-19`). Строка с ненайденной цитатой снимается.
