# Local-language lexicon: inventory and leave-one-language-out (LOCO-1), 2026-10-20

Research for H-C (generalisation ticket 08, steps 1–2; NEXT_CYCLES_2026-10-20 item 8 / §6 LOCO-1). The question: are
the per-language words that R5 (`local_language` query family), LX-1, R1 and the subject-title shapes carry general,
or memorised from the development cases they were built on?

- **No code changed, no default changed.** The analysis scripts stayed in the worker's session scratchpad.
- **Read:** the recorded store `recorded_search.base3.json`, the dev gold files (`ground_truth.reviewed11`,
  `dev{2,3,4}.draft3`), git history, the programme-discovery tickets, and 39 dev gold pages fetched by hand.
- **Not read:** any heldout file, capture, log or label; dev5 titles or pages (13-Q1); the quarantine files;
  `DISCOVERY_ANALYSIS_2026-10-17.md`. No search provider was called and no credit was spent.

## Verdict

**H-C is confirmed by ticket 08's rule, with one caveat on what is confirmed.** The rule sums gold-returned over the
leave-one-language-out folds. On the store it falls **20 → 15** cases (−5; 75 % survive, under the 80 % refutation
line). The page side, on hand-fetched gold pages, gives the same picture: accepted **18 → 13** (−5; 72 %).

| reading of the rule | store (query side) | gold pages (page side) | result |
|---|---|---|---|
| summed over folds: drop ≥ 2 confirms, ≥ 80 % surviving refutes | 20 → 15 (75 %) | 18 → 13 (72 %) | **confirmed** |
| per language: a single language drops ≥ 2 | max −1 (nl, pl, es, no, cs: one case each) | **es −2** (uba, puc) | confirmed on the page side only |
| dev5 titles: ≥ 4 match no word | not read (13-Q1) | — | not testable; INDEX_CEILING stand-in below |

**What the rule measures, and what it does not.** The rule shows *dependence*: these cases are reached or confirmed
only through their own language's rows. Provenance (§1) says whether those rows were *taken from* the cases.

- Memorisation in the strict sense, a row born from the case it then finds, is shown for:
  - **uio**: `informatikk` came from LX-1, motivated by uio's refusal. uio is lost on both sides.
  - **puc**: `licenciatura` (LX-1) and «ingeniería en ciencia de la computación» (R1) both came from puc's title.
    puc is lost on the page side.
  - **ucph**: `datalogi` came from LX-1, motivated by ucph. ucph survives through its English twin.
- The other dependent cases rest on words that predate the case or its labels:
  - warsaw, kuleuven, vienna, kit and rwth: the 2026-09-21 ontology seed;
  - ctu and unibo: LI-1, written before dev4 existed;
  - psaclay: the 09-21 alias `informatique` and the `licence` slug of 2026-09-25 (R1's `lang=fr` text row was
    added after psaclay's labels, but `licence` is the French degree's legal name).
- Under a strict provenance reading, the drop is uio only on the query side (1/20). On the page side it is uio and
  puc (2/18).

The finding that matters for generalisation is a related one. **The family picks one alias per language: the first
one in the file. That alias fits the case it was chosen on.**

- Spanish carries plural «ciencias de la computación» first, which is uba's title. The store's R5 query on uc.cl
  returned nothing for puc.
- M5's probe sent the singular «ciencia de la computación», which is puc's own title, and put puc's gold at
  **rank 1** with and without `hl`/`gl` (`m5-query-probe-2026-10-18.md`). tec's «tecnologías computacionales» is
  in neither form.
- So within one language, the query reaches the title shape it was written from and misses its neighbours. That is
  H-C's mechanism at the level of a single word choice, not a whole language.

**Heldout-adjacent provenance, flagged for the second look.**

- LI-1 (`2feafa97`, 2026-10-17) added the it, cs, sv, es and pt aliases, the local slugs and the title filler.
- The commit cites `DISCOVERY_ANALYSIS_2026-10-17.md` (quarantined, not opened). The code comment above
  `LOCALIZED_IDENTITY` names TUM's sitemap path and Polimi's `laurea-magistrale` as the motivating pages.
- R1 (`d44d32d3`) says it added "heldout countries' languages included (16-Q5)".
- None of this was opened here. The de/it/cs/tr rows may have been written with heldout pages in view, so the
  heldout run cannot count as out-of-sample evidence *for these rows*.

## 1. Inventory with provenance (step 1)

**Method.** Every language row was traced with `git log -S'<row text>' --reverse -- <file>`: its first commit is the
row's origin. The motivating case comes from the commit message, the code comment beside the row, or the
programme-discovery ticket it implements.

**Development label dates**, which decide whether a row could have been read off a gold title:

| set | first labelled |
|---|---|
| dev2 | 2026-10-17 20:27 |
| dev3 | 2026-10-17 22:45 |
| dev4 | 2026-10-18 08:41 (country proxies of the heldout nine) |

**Commits, in order:**

| commit | date (UTC) | rule | what it added (language rows) | cases it names |
|---|---|---|---|---|
| `119901ac` | 09-21 07:37 | V2-16 ontology seed | aliases fi tietotekniikka, de informatik, nl informatica, pl informatyka, fr informatique, ru информатика (settled, unflagged) | none |
| `ea691d92` | 09-25 22:10 | V2-30B | URL degree slugs `i-stopnia`, `licence`, `licenciatura`, `first-cycle` | warsaw ("naming the cycle reached Warsaw's page") |
| `2feafa97` | 10-17 20:57 | LI-1 | aliases it informatica, cs informatika, sv datavetenskap, es «ciencias de la computación», pt «ciência da computação»; slugs laurea(-magistrale/-triennale), (yuksek-)lisans, bakala(r/vr/ur)*, grado, magist(er/r)*, mestrado, kandidat (.se); path words studienangebot, corsi-di-laurea, carreras/grados/titulaciones, formations, utbildningar, studijni-programy; title filler (laurea, triennale, lisans(i), bakalar*, bakalavr(iat), licence, licenciatura, studium, studiengang, corso, programa, kandidatprogram…) | TUM, Polimi (heldout) in the code comment; cites the quarantined analysis |
| `d3caaf06` | 10-18 01:24 | LX-1 | aliases no informatikk, da datalogi, ca informàtica, es «ciencia de la computación»; degree words licenciatura, «grado en», «bachillerato en», bachelor-compounds | **uio** (informatikk), **ucph** (datalogi), **puc** (singular; licenciatura), **ub** (ca) — dev3 discovery analysis |
| `d44d32d3` | 10-18 10:31 | R1 | degree-word table for all 25 languages (text, by `<html lang>`); aliases es «ingeniería en ciencia(s) de la computación», pt ×2, fi tietojenkäsittelytiede, tr «bilgisayar bilimleri», et informaatika, lt/sk informatika, kk информатика, ru «компьютерные науки», ja ×2, zh ×3, ko ×2, th; localized related forms (es/ca/it/pt/de/fr/tr/lt/zh/ko); bachelor title filler (et/lt/cs/sk/pt/pl/fi/da/no/sv/nl/ru…) | psaclay-fr, uba, ucph-da, **puc**, iitd accepted offline; "heldout countries' languages included (16-Q5)" |
| `fbba05f9` | 10-18 11:59 | R2 | form filler studieprogramma/-program(met), opleiding, 专业, 学科 | **uio**, **kuleuven** titles |
| `5f401c45` | 10-18 12:29 | R5 | `_LOCAL_BACHELOR_QUERY_WORDS` for 24 languages, each a headword of R1's table | M5 probe (uba, puc, uio, kuleuven, psaclay, ucph) for es/fr/no/da/nl |
| `e2540a0e` | 10-18 12:35 | R4 | listing path `/opleidingen/<letter>/…` | **kuleuven** ("KU Leuven's catalogue codes…") |
| `c00bdbd3` | 10-20 01:33 | LV-1 | nb/nn informatikk, ca R5 word «grau en», sk inžiniersky, et integrated study, ja 学士課程, slug words (flagged ones off) | none (dictionary-cited per row) |

**Per language**, the R5 query words, the page-side rows, and the cases those rows came from:

| language | R5 query: alias · bachelor word (commit) | page-side rows (commit) | source cases |
|---|---|---|---|
| de | informatik (`119901ac`) · bachelor (`5f401c45`) | compounds, Masterstudium (`d44d32d3`); studienangebot path, studium/studiengang filler (`2feafa97`); «technische informatik» related | TUM (heldout) named for the path; no dev case |
| nl | informatica (`119901ac`) · bachelor | bacheloropleiding (`d44d32d3`); studieprogramma (`fbba05f9`); `/opleidingen/<x>/` (`e2540a0e`) | kuleuven (filler, path) |
| it | informatica (`2feafa97`) · laurea | laurea / laurea magistrale text and slugs, triennale/corso filler (`2feafa97`, `d44d32d3`); «ingegneria informatica» related | Polimi (heldout) named; unibo labelled after |
| cs | informatika (`2feafa97`) · bakalářský (`5f401c45`) | bakal[ář]*, navazující (`d44d32d3`); bakala* slug, bakalarsky/studijni filler, studijni-programy path (`2feafa97`) | LI-1 (quarantined analysis); ctu/vut labelled after LI-1, before R5 |
| pl | informatyka (`119901ac`) · licencjat | licencja*, «studia pierwszego/drugiego stopnia» (`d44d32d3`); `i-stopnia` slug (`ea691d92`) | warsaw (slug) |
| fr | informatique (`119901ac`) · licence | licence under `lang=fr` (`d44d32d3`); `licence` slug (`ea691d92`) | psaclay (R1 message) |
| es | «ciencias de la computación» (`2feafa97`) · licenciatura | «ciencia de la computación», licenciatura, «grado en» (`d3caaf06`); «ingeniería en ciencia(s) de la computación» (`d44d32d3`); grado slug, carreras/grados path (`2feafa97`) | **puc**, uba |
| ca | informàtica (`d3caaf06`) · «grau en» (`c00bdbd3`) | «grau en/d'» (`d44d32d3`); grau-en slug (`c00bdbd3`) | ub |
| pt | «ciência da computação» (`2feafa97`) · bacharelado | bacharel(ado), graduação (`d44d32d3`); mestrado slug (`2feafa97`) | none named |
| da | datalogi (`d3caaf06`) · bachelor | bacheloruddannelse, kandidat→master (`d44d32d3`) | **ucph** |
| no | informatikk (`d3caaf06`) · bachelor | kandidat→master (`d44d32d3`); studieprogram filler (`fbba05f9`) | **uio** |
| nb/nn | informatikk (`c00bdbd3`, flag off) | — | none (dictionary) |
| sv | datavetenskap (`2feafa97`) · kandidatprogram | kandidat(program|examen) (`d44d32d3`); kandidat .se slug (`2feafa97`) | none named |
| fi | tietotekniikka (`119901ac`) · kandidaatti | kandidaat*, maisteri* (`d44d32d3`) | none named |
| ru / kk | информатика (`119901ac` / `d44d32d3`) · бакалавриат / бакалавр | бакалавр*, магистр* (`d44d32d3`); bakalavr(iat) slug/filler (`2feafa97`) | none named |
| tr | «bilgisayar bilimleri» (`d44d32d3`) · lisans | lisans / yüksek lisans text, slug, filler (`2feafa97`, `d44d32d3`); «bilgisayar mühendisliği» related | LI-1 (quarantined analysis) |
| et / lt / sk | informaatika / informatika / informatika (`d44d32d3`) · bakalaureus / bakalauras / bakalársky | bakalaur* (`d44d32d3`); et integrated study (`c00bdbd3`, off) | none named; dev4 taltech/ktu labelled before R1 |
| ja / zh / ko / th | 情報科学 / 计算机科学与技术 / 컴퓨터과학 / วิทยาการคอมพิวเตอร์ (`d44d32d3`) · 学士 / 本科 / 학사과정 / ปริญญาตรี | level words (`d44d32d3`); 专业/学科 filler (`fbba05f9`) | none named |

The first alias reads as the field's dictionary name in every language. Nine languages share one cognate stem,
*informati-*: de, nl, it, cs, lt, sk, pl, fr, et, no, ru/kk. The bachelor word is the language-specific part. Rows
that came from a case are few: uio, ucph, puc, ub, kuleuven and warsaw.

## 2. Leave-one-language-out on the store (step 2, query side)

**Method.** `recorded_search.base3.json` holds 174 entries, one per family per case, from the four dev runs of
2026-10-18 22:30 (head `1093faaa`).

- For each case whose country publishes in another language, the local family's language rows are removed.
- With the rows removed the family is not built: `local_language_terms` returns `None`. No other language's query
  for these institutions is recorded, so the "remaining languages' words" variant cannot be replayed.
- Gold matching uses `same_programme_page` against the dev gold files.
- Rank is the position of the first gold URL in each family's top 10.

| case | set | language | R5 query (recorded) | families that returned the gold (rank) | returned with own words | without own words |
|---|---|---|---|---|---|---|
| aalto | cohort | fi/sv | `site:aalto.fi tietotekniikka kandidaatti` | field_and_degree 1, programmes 4, undergraduate 4 | yes | yes |
| delft | cohort | nl | `site:tudelft.nl informatica bachelor` | field_and_degree 1, local_language 1 | yes | yes |
| groningen | cohort | nl | `site:rug.nl informatica bachelor` | field_and_degree 1, local_language 1, natural_language 1 | yes | yes |
| hku | cohort | zh | `site:hku.hk 计算机科学与技术 本科` | natural_language 1, undergraduate 2, field_and_degree 3, programmes 3, courses 5 | yes | yes |
| kaist | cohort | ko | `site:kaist.ac.kr 컴퓨터과학 학사과정` | — | no | no |
| vienna | cohort | de | `site:univie.ac.at informatik bachelor` | field_and_degree 1, local_language 1 | yes | yes |
| **warsaw** | cohort | pl | `site:uw.edu.pl informatyka licencjat` | **local_language 2 only** | yes | **no** |
| ethz | dev2 | de/fr/it | `site:ethz.ch informatik bachelor` | field_and_degree 1 | yes | yes |
| kaznu | dev2 | kk/ru | `site:kaznu.kz информатика бакалавр` | — | no | no |
| psaclay | dev2 | fr | `site:universite-paris-saclay.fr informatique licence` | — | no | no |
| tec | dev2 | es | `site:tec.mx "ciencias de la computación" licenciatura` | — | no | no |
| tsinghua | dev2 | zh | `site:tsinghua.edu.cn 计算机科学与技术 本科` | — | no | no |
| **uba** | dev2 | es | `site:uba.ar "ciencias de la computación" licenciatura` | **local_language 2 only** | yes | **no** |
| uppsala | dev2 | sv | `site:uu.se datavetenskap kandidatprogram` | field_and_degree 1 | yes | yes |
| chula | dev3 | th | `site:chula.ac.th วิทยาการคอมพิวเตอร์ ปริญญาตรี` | field_and_degree 1 | yes | yes |
| **kuleuven** | dev3 | nl/fr/de | `site:kuleuven.be informatica bachelor` | **local_language 2 only** | yes | **no** |
| msu | dev3 | ru | `site:msu.ru информатика бакалавриат` | — | no | no |
| ntutw | dev3 | zh | `site:ntu.edu.tw 计算机科学与技术 本科` | — | no | no |
| puc | dev3 | es | `site:uc.cl "ciencias de la computación" licenciatura` | — | no | no |
| ub | dev3 | es/ca | `site:ub.edu "ciencias de la computación" licenciatura` | field_and_degree 1, natural_language 1, programmes 2 | yes | yes |
| ucph | dev3 | da | `site:ku.dk datalogi bachelor` | local_language 1, field_and_degree 2 | yes | yes |
| **uio** | dev3 | no | `site:uio.no informatikk bachelor` | **local_language 1 only** | yes | **no** |
| usp | dev3 | pt | `site:usp.br "ciência da computação" bacharelado` | field_and_degree 1, local_language 3 | yes | yes |
| **ctu** | dev4 | cs | `site:cvut.cz informatika bakalářský` | **local_language 5 only** | yes | **no** |
| kit | dev4 | de | `site:kit.edu informatik bachelor` | local_language 1, natural_language 1, field_and_degree 3 | yes | yes |
| ktu | dev4 | lt | `site:ktu.edu informatika bakalauras` | local_language 1, natural_language 1, field_and_degree 2 | yes | yes |
| rwth | dev4 | de | `site:rwth-aachen.de informatik bachelor` | field_and_degree 1, local_language 1, natural_language 1 | yes | yes |
| unibo | dev4 | it | `site:unibo.it informatica laurea` | local_language 1, natural_language 2 | yes | yes |
| utokyo, boun, itu, taltech, vut | dev3/dev4 | ja, tr, tr, et, cs | (sent) | no gold (unknown / related only) | — | — |

**Per language**, cases with gold returned, with and without the language's own words:

| language | nl | de | pl | es | no | cs | fi | zh | sv | th | da | pt | lt | it | ko | kk | fr | ru | **total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| with own words | 3 | 4 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | **20** |
| without | 2 | 4 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | **15** |

How to read the store table:

- The local family returned the gold in **14 of the 28 cases** with gold that it ran on. In 5 of them it was the
  only family that did: warsaw, uba, kuleuven, uio, ctu.
- It returned nothing for 8 cases with gold: kaist, kaznu, psaclay, tec, tsinghua, msu, ntutw, puc.
- psaclay is a hit in M5's probe (rank 1 with `hl`/`gl`) but a miss in this store, under the same query text 10
  hours later. Provider variance is of the same size as one LOCO case.
- dev4's "local_language 5 of 5" (STAGE_SUMMARY_DEV) is reproduced: ctu, kit, ktu, rwth, unibo. Only ctu depends on
  it; the other four are also returned by an English family.
- No language has two cases that depend on it, so a per-language "≥ 2" cannot happen on the store. German, the only
  language with four cases, loses none.

## 3. Leave-one-language-out on hand-fetched gold pages (step 2, page side)

**How the pages were read:**

| item | value |
|---|---|
| reader | production `app.adapters.fetching.Fetcher`: robots.txt first and honoured, Crawl-delay honoured, own `USER_AGENT` with contact `loco-1 hand-check`, `use_cache=False`, no override |
| route | direct first: every host but `www.ub.edu` refused (robots.txt `ConnectError`, which counts as a full disallow), then `trust_env_proxy=True` |
| when | 2026-10-20 |
| not read | hku ×2 (robots unreachable / network), tec (403), kuleuven (network, as TW-1), ub English (403), chula math (robots unreachable) |
| extra page | psaclay's declared `hreflang="en"` alternate, which LI-1 (iii) would read |

**The test.** Each page went through `classify_page` + `profile_rejects(page, "bachelor", ["computer science"],
url, country)`, first with today's defaults, then with every page-side row of the country's languages (plus the
page's own `<html lang>`) removed. The removed rows are:

- the ontology's localized aliases and related forms in those languages;
- the R1 and LX-1 degree-word rows that read those languages' level words;
- the local slug rows (`_LOCALIZED_DEGREE_COMPOUNDS`, `_LOCALIZED_DEGREE_SLUGS`, Swedish `kandidat`);
- the local title filler (`_LOCAL_TITLE_FILLER`, `_LOCALIZED_DEGREE_FILLER`, `_SUBJECT_FORM_FILLER`);
- CH-1's degree-field labels.

The English base tables stay. A case counts as accepted if any of its gold pages (local or English twin) is
accepted.

| case | language removed | local gold page: defaults → removed | English gold twin: defaults → removed | case accepted: defaults → removed |
|---|---|---|---|---|
| groningen | nl | — | ACC → ACC (×2) | yes → yes |
| delft | nl | — | ACC → ACC | yes → yes |
| aalto | fi+sv | — | refused (subject «Computer Engineering…») both | no → no |
| vienna | de | «Informatik (Bachelorstudium)» ACC → **refused** (level lost: unknown page) | ACC → ACC | yes → yes |
| warsaw | pl | «Informatyka, stacjonarne, pierwszego stopnia» refused both | ACC → ACC (×2) | yes → yes |
| kaist | ko | refused both | — | no → no |
| ethz | de+fr+it | — | ACC → ACC | yes → yes |
| **psaclay** | fr | «Informatique» ACC → **refused** (level) | the declared EN alternate is titled «Informatique» too: ACC → **refused** (subject) | **yes → no** |
| uppsala | sv | — | ACC → ACC | yes → yes |
| tsinghua | zh | — | refused both (division list) | no → no |
| **uba** | es | «Licenciatura en Ciencias de la Computación» ACC → **refused** (level) | none | **yes → no** |
| kaznu | kk+ru | «Компьютерные науки» ACC → **refused** (subject) | ACC → ACC | yes → yes |
| ntutw | zh | refused both | — | no → no |
| ucph | da | «Bachelor i datalogi» ACC → **refused** (subject) | ACC → ACC | yes → yes |
| msu | ru | refused both | — | no → no |
| **puc** | es | «Licenciatura en Ingeniería en Ciencia de la Computación» ×2 ACC → **refused** (level) | none | **yes → no** |
| **uio** | no+nb+nn | «Informatikk: programmering og systemarkitektur» ACC → **refused** (subject) | none | **yes → no** |
| usp | pt | `bcc.ime.usp.br` refused both | ACC → ACC | yes → yes |
| ub | es+ca | Catalan plan page refused both (no identity) | not read (403) | no → no |
| chula | th | — | ICE page refused both | no → no |
| ctu | cs | «Informatika» ACC → **refused** (level) | ACC → ACC | yes → yes |
| rwth | de | «Informatik B.Sc.» ACC → **refused** (subject) | «Computer Science B.Sc.» ACC → ACC; the Studiencenter page «Bachelor Informatik» ACC → refused | yes → yes |
| kit | de | «… Informatik Bachelor of Science» ACC → **refused** (subject) | ACC → ACC | yes → yes |
| **unibo** | it | «Informatica» ACC → **refused** (level) | «Computer Science» (`/1cycle/`) ACC → **refused**: its level comes from «laurea» | **yes → no** |
| ktu | lt | «Informatika» ACC → **refused** (level) | ACC → ACC | yes → yes |

**Totals: accepted 18 → 13.** By language: es 2 → 0, fr 1 → 0, no 1 → 0, it 1 → 0; every other language is
unchanged.

Of the 13 cases that survive:

- 4 have English-only gold: groningen, delft, ethz, uppsala.
- 9 survive **only through an English gold twin**: vienna, warsaw, kaznu, ucph, usp, ctu, rwth, kit, ktu.
- Every local-language gold page accepted at defaults is refused once its language's rows are gone: 12 of 12.
- One of the five losses is dev4 (the country proxies of the heldout nine): unibo, whose English page also needs the
  Italian level word «laurea». The other four (psaclay, uba, puc, uio) are dev2/dev3.

**Control: LV-1's synthetic battery** (`tests/test_lexicon_language_coverage.py` pages, today's defaults), run
through the same removal:

| check | result |
|---|---|
| accepted at defaults | 24 of 25 (ja «情報科学 学士課程» is LV-1's flagged-off gap) |
| refused once the language's own rows are removed | 24 of 24, so the removal reaches every language's rows |
| still accepted when an unrelated language (th, or de for th) is removed | 24 of 24, so the removal does not leak across languages |

Norwegian needed nb, nn and no removed together: the nn page is otherwise read through the `no` alias, which is the
same word.

## 4. dev5 titles (step 3)

Not read (13-Q1). The stand-in is INDEX_CEILING_2026-10-19's title/h1 test on **development** pages. Every dev gold
page in a local language with a local title named the alias. Every miss was one of:

- an English twin;
- another field's title (vut «Informační technologie», boun «Bilgisayar Mühendisliği»);
- a generic title (itu).

By language: cs 1/4, de 3/5, es 3/3, et 2/2, fr 1/1, it 1/2, lt 1/2, no 1/1, th 0/2, tr 0/4, zh 0/1.

That is in-sample, and says nothing about the ≥ 4-titles criterion on dev5. The criterion stays **not testable**
until dev5 opens.

## 5. LQ-2 proposal (only because H-C is confirmed; regime C, live-only)

**Rule.** `LOCAL_QUERY_FROM_PAGE_EVIDENCE` (harness `--local-query-from-evidence`, default off, a `NEGATABLE_RULES`
entry): the one `local_language` query takes its subject words from the site itself before the bundled lexicon.

**Where the words come from, in order:**

1. The link text, in the page's `<html lang>`, of a homepage or catalogue link whose target R4/LL-1 already
   classifies as a programme listing or programme page and whose text names a localized alias's head. Take the
   whole label, e.g. «Licenciatura en Ciencia de la Computación» rather than the lexicon's plural.
2. The seed row's native name (`Candidate`'s registry name in the institution's language), as a second phrase of
   the same query.
3. Today's alias and R1 bachelor word, as the fallback when neither exists.

**Constraints:**

- Still one query of the six, first pass, same `hl`/`gl`. The 60-request and 6-query budgets are unchanged.
- No applicant attribute. Every word is the institution's own text, checked by `_reject_applicant_data` as today.
- The phrase is capped at 8 words, quoted, with digits and personal names refused.

**Files:**

- `app/adapters/search/intent.py`: `LocalQueryTerms` gains an optional `phrase`, and `queries_for` renders it.
- `app/adapters/discovery/live_discovery.py`: the hook where the plan is built (`queries_for(intent)`, ~L5838).
  It runs after the homepage and navigation read, which precede search by default (`SEARCH_BEFORE_NAVIGATION`
  off).

**Why this shape:**

- It removes the single-alias choice that §1–§2 show is title-specific: puc's singular against uba's plural, and tec
  in neither form.
- It needs no new language row, so the next country's words cannot be memorised in advance.

**Bar (ticket 08):**

- dev4 + dev5 gold-returned unchanged or up;
- no stable loss on cohort/dev2/dev3;
- 0 new wrong pages;
- the seen-site guard (ticket 13).

**Measurement:**

- Not replayable. A new query text is a recorded-store miss (regime C).
- It is built and measured only when a search key exists (Q6 / R1 free tiers), on `query_probe` for dev4+dev5
  first: puc, tec, psaclay, kaist, kaznu, msu, ntutw, tsinghua are the eight the family misses today.
- Before any key exists, the offline half can run (regime A): the phrase each dev homepage would yield, per case,
  from captures already on disk.
