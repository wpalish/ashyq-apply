# Local catalogue entry: section labels and the catalogue host's sitemap

Type: grilling
Status: open
Blocked by: 01
Map: ../map.md · HITL + domain-modeling — a bounded new route from the homepage to a local-language catalogue; the owner approves the shape before the loop builds it.

## Question

On the development sites the local-language programme page is never *listed* by any stage (uba, puc, uio,
kuleuven, psaclay-fr — [Where the programme page is lost today](08-loss-stages-today.md), class B), yet on every
one of them the homepage links the catalogue that holds it, in one or two hops and in the site's own words:
uc.cl "Carreras de pregrado" → `admision.uc.cl/carreras/` (106 programme links, the gold among them); uio.no
"Studier" → `/studier/` → "Finn studier" `/studier/program/` (428 links, the gold labelled "Informatikk:
programmering og systemarkitektur (bachelor)"); ku.dk → `/studier/bachelor`; universite-paris-saclay.fr →
`/formation/choisir-sa-formation`; kuleuven.be → `onderwijsaanbod.kuleuven.be/opleidingen/n`; tsinghua.edu.cn
"本科专业" → `/jyjx/bksjy/bkzy.htm`; u-tokyo.ac.jp "学部"; usp.br "Graduação"
(`docs/process/PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md` §2.3, hand checks on saved homepages). The navigation
fallback keeps a homepage link only when its *URL* categorises or, on a catalogue page, its label names the
field; a label "Carreras", "Studier", "Opleidingen", "本科专业" is dropped, and `categorise_url` knows no local
catalogue root. Two catalogue hosts publish their own sitemaps with the gold in them
(`admision.uc.cl/carreras-sitemap.xml`, 71 URLs; `ingresantes.exactas.uba.ar/wp-sitemap-posts-page-1.xml`, 38).
Is a bounded "local catalogue entry" route part of the design?

❓ **Q1** - **Follow a section link on its label**: a homepage or section-page link whose *label* is a
study-section or catalogue word in a language of the institution's country (a per-language, dictionary-grade
lexicon bundled like `navigation.py`'s `_SECTION_WORDS` / `_ADMISSION_WORDS`; the language comes from
`entry["country"]`, never from the applicant) becomes a catalogue lead even when its URL categorises as
nothing — at most two hops from the homepage (homepage → section → catalogue), inside `MAX_FALLBACK_PAGES = 5`
and the SB-1 budget, read and classified like any lead (a page that is not a catalogue is dropped as today,
`not_program_catalog`).

➡️ Yes. It is one or two reads on sites where today nothing is listed at all, and the confirm predicate is
unchanged, so it cannot add a wrong page by itself.

---

❓ **Q2** - **Local listing words become URL signals**: `categorise_url` learns the slug forms of the same words
as catalogue roots (`/carreras/`, `/formation(s)/`, `/corsi-di-laurea/`, `/graduacao/`, `/opleidingen/`,
`/studier/`, `/uddannelser/`, `/utbildning(ar)/`, `/studienangebot/`, `/kierunki/`, `/studijni-programy/`,
`/bolumler/`, `/oppekavad/`, `/studiju-programos/`, `/bakalavriat/` …) and the `/<word>/<slug>` form as a
programme path, extending LI-1's `_LOCALIZED_PROGRAM_SIGNALS` (eleven words today; misses `formation`,
`/studier/program/`, `/opleidingen/n/…` — [URL lexicon audit](09-url-lexicon-audit.md)).

➡️ Yes — a dictionary translation of "programmes" / "study" per language, the same for every language, so no
entry is tuned to a case.

---

❓ **Q3** - **Read the catalogue host's own sitemap**: when a page already read links a host on the *same
registrable domain* whose label or path is a catalogue word (`admision.uc.cl`, `onderwijsaanbod.kuleuven.be`,
`ingresantes.exactas.uba.ar`, `informatorects.uw.edu.pl`), `SitemapReader` reads that host's robots.txt
sitemap (or `/sitemap.xml`, `/wp-sitemap.xml`) for at most 3 documents inside `DISCOVERY_SITEMAP_ALLOWANCE`,
preferring children whose name carries a programme word in any language — the SM-1 idea, applied only to the
catalogue host.

➡️ Yes. The host is inside `same_institution`, every read goes through the Fetcher under that host's
robots.txt, and the kept URLs go through the same `keep()` and confirm as the main sitemap's.

---

❓ **Q4** - **Boundary with DI-1**: a host on *another* registrable domain (`join-tsinghua.edu.cn` from
`tsinghua.edu.cn`) stays DI-1's case (`ADMISSIONS_HOST_FROM_HOMEPAGE`, built, off) and is not this rule;
department hosts the homepage never links (`cs.kaist.ac.kr`, `csie.ntu.edu.tw`) stay with search.

➡️ Yes — same registrable domain is the line the prefilter already draws; crossing it is a separate decision
with its own precision risk.

---

❓ **Q5** - **Measurement bar** (the loop's, restated so the owner sees it): one flag (`LOCAL_CATALOGUE_ENTRY`),
paired run on all development sets with the D1 fix in both arms; required no stable programme-page loss, 0 new
wrong claims, reads per case not above today's, and the trace's `kept_by_link_text` naming the section link on
puc and uio.

➡️ Yes.

---

❓ **Q6** - **Glossary**: record *catalogue host* and *section link* once Q1–Q4 are answered.

➡️ Yes.

## Evidence

- Hand checks of the homepages and catalogue sitemaps: `docs/process/PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md`
  §2.3 item 2 and §3 Change 3 (LC-1); pages in `scratchpad/pd_pages/`.
- Why nothing lists them today: [URL lexicon audit](09-url-lexicon-audit.md) (`opleidingen/n/…`, `formation`),
  [Language alternates](13-language-alternates.md) (language switchers are not followed either).
- Code: `backend/app/adapters/discovery/live_discovery.py` `_navigation_fallback` L3688–3800
  (`kept_by_link_text` L3752), `_CATALOGUE_PATH` L1291, `looks_like_catalogue` L1352, `MAX_FALLBACK_PAGES` L206,
  `DISCOVERY_SITEMAP_ALLOWANCE` L177, `ADMISSIONS_HOST_FROM_HOMEPAGE` L275;
  `backend/app/adapters/search/navigation.py` `_SECTION_WORDS` L66, `_ADMISSION_WORDS` L94.
