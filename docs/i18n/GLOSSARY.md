# Glossary — terms that must not be translated without a person

Unimatch is built on the rule that an unknown is reported as unknown. That
rule applies to its own words too.

The terms below carry exact meanings the whole product rests on. Choosing their
Russian and Kazakh equivalents is a decision for someone who knows the
admissions vocabulary in those languages, not a lookup. Until each one is
answered, **every interface string containing it stays in English** and falls
back visibly — `frontend/src/lib/i18n.ts` has no entry for it, and
`untranslated('ru')` lists it.

A machine translation here would be indistinguishable from a reviewed one, and
an applicant would act on it.

## Open — needs a human decision

| Term | Where it appears | The question to answer |
|---|---|---|
| **claim** | Sources & conflicts, every result | A claim here is a single sourced statement with a URL, an excerpt and a date — not an assertion in the everyday sense, and not a legal claim. Russian "утверждение" reads as an opinion; "источник" is the URL, not the statement. What is the term an admissions officer would recognise? |
| **shortlist** | Navigation, screen 04 | "Список" loses that it is the *filtered* set. Kazakh needs the same distinction. Is there an established word in local admissions counselling? |
| **funding gap** | Funding comparison, scoring | The amount left unfunded after every award. Not "долг" (debt) and not "дефицит" (deficit) — the applicant does not owe it yet. |
| **full ride / fully funded** | Funding classification | The classification the product refuses to assert without proof. Whatever word is chosen must not be *stronger* than the English, or the caution is lost in translation. |
| **conditional offer** | Admissions requirements | Has an exact meaning in UK/EU admissions. A literal translation may not carry it. |
| **unknown** (as a status) | Everywhere | The product's most important word: a first-class answer, not an error. "Неизвестно" is right in isolation, but the status chips also carry NEEDS_OFFICIAL_CLARIFICATION, and the two must stay distinguishable. |
| **NEEDS_OFFICIAL_CLARIFICATION** | Status chips | See above. This is the honest "we could not confirm it" and it must not collapse into "unknown" or into "rejected". |
| **preferences & budget** | Navigation, screen 02 | "Бюджет" is fine; "preferences" in this product means weighted priorities, not settings. |
| **sources & conflicts** | Navigation, screen 06 | "Conflicts" here means two official pages disagreeing, not a dispute. |
| **export & data deletion** | Navigation, screen 09 | Legal weight: this is the GDPR-shaped right, and the wording should match what the reviewed privacy policy ends up saying. |
| **research (run)** | Navigation, screens 03-06 | The product's "research" is automated evidence collection, not academic research. Kazakh "зерттеу" carries the academic sense. |

## Provisional — results screens only (2026-10-19, gap B6)

The results screens (`frontend/src/lib/i18n.results.ts`) are what a Russian or Kazakh reader acts
on, so they carry the words below **without** a person's decision yet. Navigation keeps the English
(until 2026-10-25, see "Provisional — navigation" below), and every Open row above stays open until
someone reviews these. None of them is stronger than the
English, and the fit is never called a probability or chance (a test checks this).

| Term | Russian | Kazakh |
|---|---|---|
| claim | факт (из источника) | дерек |
| shortlist | короткий список | қысқа тізім |
| funding gap / remaining cost | остаток к оплате | төленетін қалдық |
| full ride (`FULL_RIDE_CONFIRMED` chip) | Полное покрытие | Толық қамту |
| unknown | неизвестно | белгісіз |
| NEEDS_OFFICIAL_CLARIFICATION ("Unverified") | Не подтверждено (distinct from UNVERIFIED "Не проверено") | Расталмаған (distinct from "Тексерілмеген") |
| conflict (sources disagree) | расхождение | сәйкессіздік |
| research (run) | исследование (as in existing `nav.progress`) | зерттеу (as in existing `nav.progress`) |
| match (fit) | совпадение | үйлесім |
| conditional offer / admission offer | приглашение на учёбу | оқуға шақыру |

Added by I18N-2 (2026-10-20: requirement explanations, award classifications, ranking reasons,
conflicts, the Documents screen). Also provisional; each poses the question beside it.

| Term | Russian | Kazakh | The question to answer |
|---|---|---|---|
| (budget) ceiling — "the stated ceiling" | указанный предел (бюджета) | көрсетілген шек | Is "предел" / "шек" how a family would say the most it can pay a year, or is "лимит" expected? |
| fee population ("depends on your fee population here") | категория оплаты | ақы төлеу санаты | Home / EU / international fee status: is there an established term a Kazakhstani counsellor uses? |
| full tuition (in a sentence, not the chip) | полная оплата обучения | оқу ақысын толық өтеу | Must stay visibly weaker than "Полное покрытие" / "Толық қамту"; does it? |
| test-optional | не требует тестов в обязательном порядке | тестті міндетті етпейді | Is there a shorter accepted term for US "test-optional" in either language? |
| need-based (award) | по нуждаемости | мұқтаждыққа қарай | Same word as the existing chip; does it read as "means-tested" to a family? |
| credential evaluation | оценка документов об образовании | білім туралы құжаттарды бағалау | WES/ECE evaluation; is "нострификация" ever the right word (it is a different procedure)? |
| not a contradiction / scope difference | это не противоречие | бұл қайшылық емес | Distinct from "расхождение" / "сәйкессіздік" (conflict) as the glossary requires? |
| lead time ("allow ~30 days") | заложите ~N дней | (existing `detail.docs.leadTime`) | — |

Added by I18N-3 (2026-10-20: the Documents screen's 18 document names, `msg.document.<kind>`, and its
four note sentences, `msg.document.note.*`). The names are our vocabulary, not a university's words.
Also provisional; each poses the question beside it.

| Term | Russian | Kazakh | The question to answer |
|---|---|---|---|
| (full academic) transcript | выписка оценок (транскрипт) | бағалардың транскрипті | Do Kazakhstani applicants say "транскрипт", or "приложение к аттестату" / "аттестатқа қосымша" for a school record? |
| secondary school diploma | аттестат о среднем образовании | орта білім туралы аттестат | Right for a Kazakhstani school leaver; is a separate word needed for a foreign high-school diploma? |
| certified (copy, translation) | заверенная копия / заверенный перевод | куәландырылған көшірме / аударма | "Certified" by whom: a school, a notary or a sworn translator? The English does not say, and neither may the translation. |
| notarised copy (flag `needs_notarization`) | нотариальное заверение | нотариат куәландыруы | Same word as the existing `documents.notarisation` chip; is it distinct enough from "certified" above? |
| apostille (certification) | заверение апостилем | апостильмен куәландыру | Is "апостилирование" the term an applicant would search for? |
| course-by-course credential evaluation (WES/ECE) | попредметная оценка документов об образовании | білім туралы құжаттарды пән бойынша бағалау | Not "нострификация" (a different procedure); does "попредметная" read as WES's course-by-course report? |
| personal statement | личное заявление | жеке мәлімдеме | UK/US sense (an essay about oneself), not an application form; is "личное эссе" clearer, and then how is it told apart from "Personal Essay" (личное эссе / жеке эссе)? |
| statement of motivation | мотивационное письмо | мотивациялық хат | The established term; does it collide with "personal statement" for a reader? |
| academic reference | рекомендация от преподавателя | оқытушының ұсынымы | A reference from a teacher; distinct from "letter of recommendation" (рекомендательное письмо / ұсыным хат)? |
| proof of financial resources | подтверждение наличия финансовых средств | қаржы қаражатының бар екенін растау | Is "справка о финансовой состоятельности" what a bank or embassy would call it? |
| "as published" (optional / conditional notes) | как опубликовано | жарияланғандай | Same as `detail.docs.condition`; does it read as "as the university states it", not "as printed by us"? |
| possibly outdated | возможно, устарело | ескірген болуы мүмкін | Must stay weaker than "не актуально" / "өзекті емес" (the stale chip); does it? |

## Provisional — navigation (2026-10-25)

The header's "Explore" menu and the sidebar name every screen at once, and a Russian or Kazakh reader
met six English labels there. They now carry the provisional words above (owner request, 2026-10-25),
**without** a person's decision: the Open rows for shortlist, preferences & budget, sources & conflicts,
export & data deletion and research stay open, and a reviewer may change any of these.

| Key | English | Russian | Kazakh | Note |
|---|---|---|---|---|
| `nav.preferences` | Preferences & budget | Приоритеты и бюджет | Басымдықтар және бюджет | "Preferences" here are weighted priorities, not settings, so not "настройки" / "баптаулар". |
| `nav.shortlist` | University shortlist | Короткий список университетов | Университеттердің қысқа тізімі | Same word as the results screens. |
| `nav.funding` | Funding comparison | Сравнение финансирования | Қаржыландыруды салыстыру | No glossary term (not "funding gap"). |
| `nav.sources` | Sources & conflicts | Источники и расхождения | Дереккөздер және сәйкессіздіктер | "Conflict" = two official pages disagreeing: расхождение / сәйкессіздік, as on the results screens. |
| `nav.export` | Export & data deletion | Экспорт и удаление данных | Деректерді экспорттау және жою | Must follow the reviewed privacy policy's wording once it exists. |
| `nav.group.research` | Research | Исследование | Зерттеу | As in the existing `nav.progress`. |
| `topbar.explore` | Explore | Разделы | Бөлімдер | The menu of screens ("sections"), not a verb: "Исследовать" would collide with research. |

## Settled

Ordinary interface words with no product-specific meaning — Save, Cancel,
Light, Dark, Language, Applicant — are translated in `i18n.ts` and need no
review beyond ordinary proofreading.

## How to close one

1. Decide the term with someone who advises applicants in that language.
2. Add the key to the `RU` or `KK` dictionary in `frontend/src/lib/i18n.ts`.
3. Move the row from **Open** to **Settled** here, naming who decided it.

`frontend/src/lib/i18n.test.ts` asserts that this file and the dictionaries do
not drift apart: a term listed as open must not quietly acquire a translation
without this document being updated with it.
