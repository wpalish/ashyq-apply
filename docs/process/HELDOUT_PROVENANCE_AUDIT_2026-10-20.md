# Heldout provenance audit of the language tables (HP-AUDIT), 2026-10-20

This follows LOCO-1's "flagged for the second look" (`LOCAL_LANGUAGE_LOCO_2026-10-20.md`, Verdict). LOCO-1 found two
problems:

- LI-1 (`2feafa97`) cites the quarantined analysis, and its code comment names two heldout universities.
- R1 (`d44d32d3`) added the heldout countries' languages.

So some de/it/cs/tr (and perhaps et/lt/kk/ru) rows may have been written with heldout pages in view. If so, the
heldout run cannot count as out-of-sample evidence for them.

This audit lists every such row and checks it against a source that is not a page. For each row it then re-sources
the row or proposes a flag.

**Method and limits.** Only git history was used: `git show`, `git log -S`, `git log --grep`, commit messages,
diffs and code comments.

- **Not opened:** `docs/process/DISCOVERY_ANALYSIS_2026-10-17.md`, `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`,
  `scratchpad/DEV5_BLIND`, and any heldout file, capture, log or label for nu, metu, sabanci, charles, masaryk, tum,
  tartu, polimi or vilnius. No page was fetched and no search was run.
- **Not visible from here:** which heldout pages the quarantined analysis looked at. The audit sees only what the
  commits and comments say about it.
- **How the sources were checked:** they are cited from the reference works, the same way LV-1 cited its battery
  (`tests/test_lexicon_language_coverage.py::DICTIONARY`). None was re-fetched in this session, so a reviewer may
  spot-check any of them.

## Verdict

| tier | criterion | rows | supported by a dictionary or statute | re-sourced | proposed for removal |
|---|---|---|---|---|---|
| **A** | the introducing commit cites the quarantined analysis, or its comment names a heldout university (LI-1 `2feafa97`) | **54** | 54 | 54 | **0** |
| B1 | R1 (`d44d32d3`) rows in a heldout country's language: its message says "heldout countries' languages included (16-Q5)" but names no university and cites no quarantined analysis | 42 | 42 | 42 | 0 |
| B2 | R5 (`5f401c45`) query words in those languages: headwords taken over from R1, and R5's message names development cases only | 8 | 8 | covered by B1 | 0 |
| B3 | R4 (`e2540a0e`) navigation words in those languages: same 16-Q5 note; `LOCAL_CATALOGUE_ENTRY` is **off** | 10 (grouped by language) | 10 | in this file only | 0 |
| | **total** | **114** | **114** | | **0** |

**No row lacks an independent source, so no flag was added and no behaviour changed.** Every row is either:

- a dictionary headword or degree-law term;
- its folded or inflected form (`lisansi`, `studiengange`, `kandidatprogrammet`); or
- its URL slug.

**What a dictionary source does not settle: selection.** It shows that a word is real and means what the row says.
It does not show why *this* word was picked and its neighbours were not.

- **Two Tier-A rows were chosen because of a heldout page**, by the comment's own account:
  - **A6** `studienangebot`, the path word: "TUM's sitemap lists only `/studium/studienangebot/…`".
  - **A17** `laurea-magistrale`: "Polimi's `laurea-magistrale` was not a degree slug".
- **The other 52 LI-1 rows were written in the same commit, with the quarantined analysis cited.**
- **LI-1's non-alias rows fall almost entirely in the heldout languages:**
  - de: path, filler;
  - it: path, slugs, filler;
  - cs: path, slug, filler;
  - tr: slugs, filler, ön lisans;
  - ru/kk: `bakalavr*`;
  - et/lt: `bakalaur*`.
- **LI-1 predates dev4** (the heldout countries' proxies, labelled 2026-10-18 08:41). So when LI-1 was written, no
  development case could have motivated its rows in those languages. Only the heldout trace could.

The heldout look of 2026-10-19 therefore cannot count as out-of-sample for LI-1's rows in de, it, cs, tr, ru/kk or
et/lt. Tier B is weaker: R1 and R4 name no case. 16-Q5 required them to be written dictionary-grade for every language
at once, and they are. 16-Q5 also put the heldout languages in that one commit on purpose. Its "no alias … after a
heldout look" binds later looks. Still, R1 and R4 were written the day after the first heldout look (2026-10-17), so
they are not blind to it in principle. Nothing in git ties any B row to a heldout page.

## What the owner should decide

| # | decision | recommendation |
|---|---|---|
| D1 | Accept the 114 dictionary/statute sources as the rows' provenance from now on (comments and `ontology.json` `source` fields re-pointed here) | **Yes.** Every row has one, and none was unsupported. |
| D2 | How to read the heldout second look (2026-10-19) for the heldout languages | Report the heldout cases in de/it/cs/tr/kk(ru)/et/lt as **in-sample-adjacent** wherever an LI-1 row decided them. Count only the other cases as out-of-sample. |
| D3 | Whether to measure the two heldout-chosen rows (A6, A17) with a removal replay | Optional. Both are dictionary words, so the rule here put no flag on them. If you want the number, a default-on negatable flag (`--no-li1-heldout-chosen-rows`) can be added in one change and replayed on dev4 + dev5 (aggregates only on dev5). |
| D4 | Where the out-of-sample evidence for these languages should come from | **dev5**, which is design-blind and already covers the heldout countries' languages: tud and lmu (de), unipd and sapienza (it), upol and zcu (cs), hacettepe, bilkent and ytu (tr), kbtu, satbayev and aitu (kk/ru), vilniustech (lt). dev5 is design-blind (ticket 13), so no row here was written from its pages or labels. Estonian has no dev5 case (only taltech, in dev4), so et stays unmeasured out of sample. |
| D5 | Out of scope here (not language tables), but the same kind of finding | PG-1's exclusion `news-single-view` (on by default) and CU-1's http/https identity (on) are motivated by heldout URLs. SO-1 and SM-1 (off) cite heldout timings. Their comments are now generic. Their *rows* belong in ticket 12's seen-site ledger, not in this audit. |

## Changes made (comments and annotations only)

| file | change |
|---|---|
| `app/adapters/discovery/live_discovery.py` | LI-1's comment: TUM and Polimi are replaced by generic shapes ("a German catalogue path `/studium/studienangebot/<programme-slug>`", "an Italian `laurea-magistrale` slug"), and the quarantined citation is replaced by a pointer here. `_LOCALIZED_PROGRAM_SIGNALS`, the slug tables and `_LOCAL_TITLE_FILLER` now carry their dictionary or statute sources. `_LOCALIZED_DEGREE_FILLER` points to R1's cited table. SO-1, SM-1, PG-1 and CU-1 no longer name METU, NU, Charles or TUM. |
| `app/adapters/page_classifier.py` | `_LOCALIZED_DEGREE_WORDS`: the degree laws for the heldout-language rows. PG-1's comment no longer names TUM or its host. |
| `app/adapters/search/ontology.json` | `"source"` on the 5 LI-1 aliases and on R1's 5 aliases and 4 related forms in heldout languages, in LV-1's existing field. The vocabulary is unchanged, so `version` is unchanged. |
| `app/adapters/search/intent.py`, `retrieval.py`, `extraction.py` | The names TUM, Charles (and its hosts) and Masaryk are replaced by generic shapes. |
| `tests/test_discovery_strong_aliases.py`, `test_live_discovery_localized_identity.py`, `test_local_language_queries.py` | Docstrings no longer cite the quarantined analysis or name TUM; the R5 test's German domain is `kit.edu` (dev4) instead of `tum.de`. |

Git history (the LI-1 commit message and the old comments) cannot be rewritten and still names both universities.
This file is now the provenance of record.

## Tier A: LI-1 (`2feafa97`, 2026-10-17 20:57)

- **Heldout reference, every row:** the commit cites `DISCOVERY_ANALYSIS_2026-10-17.md` §0 #4, §1.2, §4 rule 4
  (quarantined).
- **Comment above `LOCALIZED_IDENTITY`:** it named TUM (sitemap path, subject «Informatik») and Polimi
  (`laurea-magistrale`).
- **"Named" in the table below:** the row is the one the comment ties to a heldout page.
- **"cited":** the row shares the commit's citation only.
- **Every row is in force today:** `LOCALIZED_IDENTITY = True`, so the flagged ontology entries are read.

| # | row | file / table | heldout reference | independent source | action |
|---|---|---|---|---|---|
| A1 | it `informatica` | `ontology.json` localized_aliases | cited | Vocabolario Treccani s.v. informatica; DM 16 marzo 2007, classe L-31 | re-sourced (`source`) |
| A2 | cs `informatika` | `ontology.json` | cited | Slovník spisovného jazyka českého (ÚJČ AV ČR) s.v. informatika | re-sourced |
| A3 | sv `datavetenskap` | `ontology.json` | cited | Svensk ordbok (Svenska Akademien) s.v. datavetenskap | re-sourced |
| A4 | es `ciencias de la computación` | `ontology.json` | cited | RAE, DLE s.v. computación (= informática); the phrase is the field's name, not a DLE lemma (headword-level support) | re-sourced |
| A5 | pt `ciência da computação` | `ontology.json` | cited | Resolução CNE/CES nº 5/2016 (DCN, bacharelado em Ciência da Computação) | re-sourced |
| A6 | `studienangebot` (path) | `live_discovery._LOCALIZED_PROGRAM_SIGNALS` | **named: TUM's sitemap path** | Duden s.v. Studienangebot | re-sourced; selection heldout-chosen (D3) |
| A7 | `studiengaenge` (path) | same | cited | Duden s.v. Studiengang (ASCII fold of «Studiengänge») | re-sourced |
| A8 | `studiengange` (path) | same | cited | as A7 (umlaut dropped) | re-sourced |
| A9 | `corsi-di-laurea` (path) | same | cited | DM 270/2004 art. 3 («corsi di laurea») | re-sourced |
| A10 | `corso-di-laurea` (path) | same | cited | as A9 | re-sourced |
| A11 | `carreras` (path) | same | cited | RAE, DLE s.v. carrera (the studies that qualify for a profession) | re-sourced |
| A12 | `grados` (path) | same | cited | Real Decreto 822/2021 («títulos de Grado») | re-sourced |
| A13 | `titulaciones` (path) | same | cited | Real Decreto 822/2021 («titulaciones»); RAE, DLE s.v. titulación | re-sourced |
| A14 | `formations` (path) | same | cited | Larousse s.v. formation | re-sourced |
| A15 | `utbildningar` (path) | same | cited | Svensk ordbok s.v. utbildning | re-sourced |
| A16 | `studijni-programy` (path) | same | cited | Act No. 111/1998 Coll. §44 («studijní program») | re-sourced |
| A17 | `laurea-magistrale` → master | `_LOCALIZED_DEGREE_COMPOUNDS` | **named: Polimi** | DM 270/2004 art. 3 (laurea magistrale) | re-sourced; selection heldout-chosen (D3) |
| A18 | `yuksek-?lisans` → master | same | cited | Law No. 2547 art. 3; YÖK Lisansüstü Eğitim ve Öğretim Yönetmeliği (yüksek lisans) | re-sourced |
| A19 | `laurea-triennale` → bachelor | same | cited | Treccani s.v. laurea (laurea triennale, first level); DM 270/2004 art. 3 | re-sourced |
| A20 | `laurea` → bachelor | `_LOCALIZED_DEGREE_SLUGS` | cited | DM 270/2004 art. 3 | re-sourced |
| A21 | `lisans` → bachelor | same | cited | Law No. 2547 art. 3 (lisans) | re-sourced |
| A22 | `bakala(r\|vr\|ur)*` → bachelor | same | cited | cs Act No. 111/1998 Coll. §45 (bakalář); ru/kk Federal Law 273-FZ art. 69 and RK Law On Education art. 36 (бакалавр, transliterated); et Kõrgharidusseadus (bakalaureus); lt Law on Higher Education and Research art. 47 (bakalauras) | re-sourced |
| A23 | `grado` → bachelor | same | cited | Real Decreto 822/2021 art. 14 (Grado) | re-sourced |
| A24 | `magist(er\|r)*` → master | same | cited | cs Act No. 111/1998 Coll. §46 (magisterský); pl Act of 20 July 2018 (magister); ru/kk 273-FZ (магистр, transliterated); es RAE, DLE s.v. magíster | re-sourced |
| A25 | `mestrado` → master | same | cited | Decreto-Lei 74/2006 (grau de mestre) | re-sourced |
| A26 | `master-s` → master | same | cited | English «master's degree» (Merriam-Webster s.v. master's degree) | re-sourced |
| A27 | `kandidat*` → bachelor on `.se` | `_SWEDISH_KANDIDAT` | cited | Högskoleförordningen (1993:100) bilaga 2 (kandidatexamen) | re-sourced |
| A28 | `on-lisans` removed before matching | `_TURKISH_ASSOCIATE` | cited | Law No. 2547 art. 3 (ön lisans) | re-sourced |
| A29 | `laurea` | `_LOCAL_TITLE_FILLER` | cited | DM 270/2004 art. 3 | re-sourced |
| A30 | `triennale` | same | cited | Treccani s.v. triennale / laurea | re-sourced |
| A31 | `lisans` | same | cited | Law No. 2547 art. 3 | re-sourced |
| A32 | `lisansi` | same | cited | inflected «lisansı» of A31 (TDK s.v. lisans), ı folded | re-sourced |
| A33 | `programi` | same | cited | inflected «programı», TDK s.v. program, ı folded | re-sourced |
| A34 | `bakalar` | same | cited | Act No. 111/1998 Coll. §45 (bakalář, folded) | re-sourced |
| A35 | `bakalarsky` | same | cited | as A34 («bakalářský studijní program») | re-sourced |
| A36 | `bakalarske` | same | cited | as A34 (neuter form) | re-sourced |
| A37 | `bakalarska` | same | cited | as A34 (feminine form) | re-sourced |
| A38 | `bakalavr` | same | cited | Federal Law 273-FZ art. 10; RK Law On Education art. 36 (бакалавр, transliterated) | re-sourced |
| A39 | `bakalavriat` | same | cited | as A38 (бакалавриат) | re-sourced |
| A40 | `grado` | same | cited | Real Decreto 822/2021 | re-sourced |
| A41 | `licence` | same | cited | Code de l'éducation art. D612-32-2 | re-sourced |
| A42 | `licenciatura` | same | cited | RAE, DLE s.v. licenciatura | re-sourced |
| A43 | `bachelorstudium` | same | cited | Duden s.v. Bachelorstudium | re-sourced |
| A44 | `bachelorstudiengang` | same | cited | Duden s.v. Bachelorstudiengang | re-sourced |
| A45 | `studiengang` | same | cited | Duden s.v. Studiengang | re-sourced |
| A46 | `studium` | same | cited | Duden s.v. Studium | re-sourced |
| A47 | `corso` | same | cited | Treccani s.v. corso (corso di laurea); DM 270/2004 | re-sourced |
| A48 | `programa` | same | cited | RAE, DLE s.v. programa | re-sourced |
| A49 | `programma` | same | cited | Treccani s.v. programma | re-sourced |
| A50 | `programm` | same | cited | Duden s.v. Programm | re-sourced |
| A51 | `studijni` | same | cited | Act No. 111/1998 Coll. §44 (studijní) | re-sourced |
| A52 | `studijny` | same | cited | Act No. 131/2002 Coll. §51 (študijný) | re-sourced |
| A53 | `kandidatprogram` | same | cited | Högskoleförordningen bilaga 2 (kandidatexamen); Svensk ordbok s.v. kandidat | re-sourced |
| A54 | `kandidatprogrammet` | same | cited | definite form of A53 | re-sourced |

**Not a row:** the subject «Informatik» that the comment mentions. The `de informatik` alias dates from the 2026-09-21
ontology seed (`119901ac`), before any heldout look. LI-1 changed the mechanism (a localized alias may be the subject)
and added no German alias.

## Tier B1: R1 (`d44d32d3`, 2026-10-18 10:31), heldout-country languages

**Heldout reference:** the commit message says "heldout countries' languages included (16-Q5)". It names no
university and does not cite the quarantined analysis. Its code comments name only development cases (UBA, PUC,
Paris-Saclay, IIT Delhi). `LOCALIZED_PAGE_IDENTITY = True` today.

| # | row | file / table | independent source | action |
|---|---|---|---|---|
| B1-1 | tr alias `bilgisayar bilimleri` | `ontology.json` | TDK Güncel Türkçe Sözlük s.v. bilgisayar, bilim; YÖK programme-name list | re-sourced (`source`) |
| B1-2 | et alias `informaatika` | `ontology.json` | Eesti keele seletav sõnaraamat (EKI) s.v. informaatika | re-sourced |
| B1-3 | lt alias `informatika` | `ontology.json` | Dabartinės lietuvių kalbos žodynas s.v. informatika; Studijų krypčių sąrašas | re-sourced |
| B1-4 | kk alias `информатика` | `ontology.json` | Қазақ әдеби тілінің сөздігі (2011) s.v. информатика | re-sourced |
| B1-5 | ru alias `компьютерные науки` | `ontology.json` | Minobrnauki Order No. 1061 (2013), direction 02.03.01 «Математика и компьютерные науки» | re-sourced |
| B1-6 | it related `ingegneria informatica` | `ontology.json` related | Treccani s.v. ingegneria; DM 16 marzo 2007 classe L-8 | re-sourced |
| B1-7 | de related `technische informatik` | `ontology.json` related | Duden s.v. Informatik (branch «technische Informatik») | re-sourced |
| B1-8 | tr related `bilgisayar mühendisliği` | `ontology.json` related | TDK s.v. mühendislik; YÖK programme-name list | re-sourced |
| B1-9 | lt related `informatikos inžinerija` | `ontology.json` related | Studijų krypčių sąrašas (study field) | re-sourced |
| B1-10 | de master compounds (Masterstudium, Masterstudiengang, Masterprogramm) | `page_classifier._LOCALIZED_DEGREE_WORDS` | KMK Ländergemeinsame Strukturvorgaben; Duden s.v. Masterstudium | re-sourced (comment) |
| B1-11 | it `laurea magistrale` / `laurea specialistica` → master | same | DM 270/2004 art. 3; DM 509/1999 art. 3 | re-sourced |
| B1-12 | tr `yüksek lisans` → master | same | YÖK graduate regulation; Law No. 2547 | re-sourced |
| B1-13 | `magist(er\|r)…`, cs `navazující` → master | same | Act No. 111/1998 Coll. §46; Kõrgharidusseadus (magistriõpe); Lithuanian law art. 47 (magistrantūra) | re-sourced |
| B1-14 | `магистр…` → master (ru/kk) | same | Federal Law 273-FZ art. 10; RK Law On Education art. 36 | re-sourced |
| B1-15 | it `laurea` → bachelor | same | DM 270/2004 art. 3 | re-sourced |
| B1-16 | tr `lisans` → bachelor (not after yüksek/ön) | same | Law No. 2547 art. 3 | re-sourced |
| B1-17 | cs/sk `bakalář…` → bachelor | same | Act No. 111/1998 Coll. §45; Act No. 131/2002 Coll. §52 | re-sourced |
| B1-18 | et/lt `bakalaur…` → bachelor | same | Kõrgharidusseadus; Lithuanian law art. 47 | re-sourced |
| B1-19 | ru/kk `бакалавр…` → bachelor | same | Federal Law 273-FZ art. 10; RK Law On Education art. 36 | re-sourced |
| B1-20 … B1-33 | filler `lisansı`, `programı` (tr); `bakalaureus`, `bakalaureuse`, `bakalaureuseõpe` (et); `bakalauras`, `bakalauro` (lt); `bakalářský`, `bakalářské`, `bakalářského` (cs); `bachelorstudium` (de); `бакалавриат`, `бакалавр`, `бакалавра` (ru/kk) — 14 rows | `live_discovery._LOCALIZED_DEGREE_FILLER` | inflected forms of B1-16 … B1-19 and B1-10 (same laws) | re-sourced (comment points to B1-10 … B1-19) |
| B1-34 … B1-42 | `languages.json`: Czechia, Czech Republic → cs; Estonia → et; Germany → de; Italy → it; Kazakhstan → kk, ru; Lithuania → lt; Turkey, Türkiye → tr — 9 rows | `languages.json` | the state languages: cs Act No. 500/2004 Coll. §16; et Keeleseadus §1; de VwVfG §23; it Law 482/1999 art. 1; kk/ru Constitution of Kazakhstan art. 7; lt Constitution art. 14; tr Constitution art. 3 | sourced here (the JSON has no comment field; left unchanged) |

## Tier B2: R5 (`5f401c45`) query words in those languages

These are the query headwords of B1: it `laurea`, de `bachelor`, cs `bakalářský`, et `bakalaureus`, lt `bakalauras`,
ru `бакалавриат`, kk `бакалавр` and tr `lisans`, in `page_classifier._LOCAL_BACHELOR_QUERY_WORDS`.

- R5's commit names only the M5 probe's development cases (uba, puc, uio, kuleuven, psaclay, ucph), for es, fr, no, da
  and nl.
- **Sources:** B1-15, B1-10 (KMK), B1-17, B1-18 and B1-19, and B1-16.
- **Action:** none. They are covered by B1's citations.

## Tier B3: R4 (`e2540a0e`) navigation words in those languages (rule off)

- **Heldout reference:** the commit message says "heldout countries' languages included, same shape for all". It names
  no university and does not cite the quarantined analysis.
- **Off by default:** `LOCAL_CATALOGUE_ENTRY = False`, so none of these words is read at the defaults the heldout look
  scored.
- **Action:** each group is sourced here only.

| # | language | rows (`navigation._LOCAL_CATALOGUE_WORDS` + `_LOCAL_SECTION_WORDS`) | independent source |
|---|---|---|---|
| B3-1 | de | studienangebot(e), studiengänge, studienfächer; studium, studieren, studium und lehre | Duden s.v. Studienangebot, Studiengang, Studienfach, Studium |
| B3-2 | it | corsi di laurea, corsi di studio, offerta formativa, lauree, corsi; didattica, studiare | DM 270/2004 (corsi di laurea, corsi di studio, offerta formativa); Treccani s.v. didattica |
| B3-3 | cs | studijní programy, studijní obory, nabídka studia; studium, studovat, vzdělávání | Act No. 111/1998 Coll. §44 (studijní program, obor); SSJČ s.v. studium, vzdělávání |
| B3-4 | tr | bölümler, programlar, lisans programları, akademik programlar; akademik, eğitim, öğrenim | TDK s.v. bölüm, program, eğitim, öğrenim; Law No. 2547 art. 3 |
| B3-5 | et | õppekavad, erialad; õppimine, õpingud, õppetöö | Kõrgharidusseadus (õppekava); EKI s.v. eriala, õpingud |
| B3-6 | lt | studijų programos, programos; studijos, studijuok | Lithuanian Law on Higher Education and Research (studijų programa); DLKŽ s.v. studijos |
| B3-7 | ru | образовательные программы, направления подготовки, специальности, программы обучения, бакалавриат; образование, обучение, учёба | Federal Law 273-FZ art. 2, 10 (образовательная программа, направление подготовки, специальность) |
| B3-8 | kk | білім беру бағдарламалары, оқу бағдарламалары, мамандықтар, бакалавриат; білім беру, оқу, білім | RK Law On Education (білім беру бағдарламасы, мамандық) |
| B3-9 | it/tr/cs/et/lt/ru/kk | level words (`_LEVEL_WORDS`): laurea (triennale/magistrale), magistrale, bakalářské, бакалавриат, lisans, yüksek lisans, magistratura, магистратура, magistrantūra, magistriõpe, dottorato, аспирантура, докторантура, doktora, doktorantūra, doktoriõpe | the degree laws of B1-11 … B1-19, plus each law's doctoral cycle |
| B3-10 | de/it/cs/tr/et/lt/ru | URL roots in `live_discovery._LOCAL_CATALOGUE_ROOT` and `_LOCAL_LISTING_SIGNALS` (studienangebot, studiengaenge, corsi(-di-laurea\|-di-studio), offerta-formativa, studijni-programy, bolumler, programlar, lisans-programlari, oppekavad, studiju-programos, obrazovatelnye-programmy, bakalavriat, programmy, programy, programos) | slugs of B3-1 … B3-8 |

## Searched and found outside the language tables

Two greps were run: `git log --grep` over the lexicon files, for each heldout name and for the quarantined analysis;
and the current `app/**/*.py` comments.

- **Cite the quarantined analysis and add no language row:** SO-1 (`23f71b26`), SM-1 (`0305b0fb`), QA-1 (`c30697da`)
  and PG-1 (`ae3ce135`). QA-1's `informatics` alias dates from the 2026-09-21 seed (`119901ac`).
- **Named heldout universities in comments, now generic:** SO-1, SM-1, PG-1, CU-1 (METU, NU, Charles, TUM), HP-1
  (Charles hosts) and EX-1 (Masaryk).
- **The plan citations stay in SO-1, SM-1, PG-1 and QA-1:** they are not language rows. D5 hands those rules to ticket
  12.
- **ER-05 (`39624680`):** "nothing read from benchmark or held-out pages". Not flagged.
- **Out of scope:** tests outside the lexicon suites still use heldout domains as test data (for example
  `nu.edu.kz` in `test_search_provider.py`). No language row depends on them.
