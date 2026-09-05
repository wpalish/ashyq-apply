# Glossary — terms that must not be translated without a person

ASHYQ Apply is built on the rule that an unknown is reported as unknown. That
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
