# Classifier audit on hand-fetched development gold programme pages

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5, offline in the backend venv on pages fetched by hand.

## Question

When discovery *does* read the gold programme page, does today's confirm predicate (`classify_page` →
`profile_rejects`, `live_discovery.py` L1609–1648) accept it? Which refusals are lexicon (fixable by
vocabulary), which are subject-title shape (a policy), and which are the page's own identity being absent
from its text? What does the dormant LX-1 lexicon change?

## Answer

Script: `scratchpad/wf_tools/classifier_audit.py` (and `lx1_audit.py` with `LEXICON_V2 = True`), on 22 saved
pages: `scratchpad/funnel_pages/*`, `scratchpad/fetched/*`, `scratchpad/pd_pages/*`, `scratchpad/evpages/*`.
Two saved Imperial pages are CloudFront 403 shells (919 bytes), so Imperial is **not testable** here; 20 pages
are.

**Accepted today (10):** delft, ntu, ubc (`Computer Science (BSc)`), auckland plan (`Bachelor of Science major
in Computer Science`), um (`BACHELOR OF COMPUTER SCIENCE (COMPUTER SYSTEM …)`), ucph English twin, psaclay
English twin (`Informatique`), ethz, tcd, uppsala.

**Refused today (10), by cause:**

| cause | pages | mechanism | LX-1 on |
|---|---|---|---|
| **Lexicon: no degree word** | iitd `BTech in CSE – Computer Science and Engineering`; uba `Licenciatura en Ciencias de la Computación`; puc `Licenciatura en Ingeniería en Ciencia de la Computación` | `_DEGREE_WORDS` (page_classifier.py L214–219) knows bachelor/bsc/ba/beng/llb/undergraduate only → `_program_name` finds no degree → `UNKNOWN` | iitd **ACCEPT**, uba **ACCEPT**, puc → `program_detail` but refused on subject (next row) |
| **Subject-title shape** | puc (`Ingeniería en` before the alias); uio `Informatikk: programmering og systemarkitektur` (subtitle after a colon); kuleuven `Bachelor in de informatica (Leuven) - Studieprogramma` (location + form word) | `matches_field_text` accepts an alias only when every other title word is filler (`_TITLE_FILLER`, `_LOCAL_TITLE_FILLER`); "ingeniería", "programmering", "systemarkitektur", "leuven", "studieprogramma" are not | unchanged — a policy, see [Subject match on local programme titles](19-subject-title-shapes.md) |
| **Local alias not in the default set** | ucph Danish `Bachelor i datalogi` | `datalogi` is flagged `LEXICON_V2` in `ontology.json`; today the page's declared English twin rescues it (LI-1), and the twin is accepted | **ACCEPT** directly |
| **Structural label** | auckland BSc page `Bachelor of Science BSc` | the page names the degree, not the major; the CS plan page is the one with the subject | unchanged — identity decision ([What counts as the programme page found](03-programme-identity-equivalence.md)) |
| **Identity absent from the text** | kaist `content?menu=188` (title is the School's Korean strapline; no h1; body 1 135 chars); ub JSP (a Catalan timetable, "Assignatures : Itinerari recomanat") | nothing a lexicon can do; kaist needs link-text identity or a different page of the same programme, ub's gold is a plan page | unchanged |
| **Wrong level read** | psaclay French `licence` page | `_degree_level` reads *master* from the body (the page lists the follow-on masters); the English twin is accepted instead | unchanged (twin route works) |

**Policy observation (for ticket 19):** `matches_field_text` returns `True` as soon as the applicant's *own*
field words are a subset of the title words, without checking the remaining words (L1376–1380) — so "BTech in
CSE – Computer Science and Engineering" and "Bachelor of Business Science specialising in Computer Science"
both pass the subject test today, while "Bachelor in de informatica (Leuven)" fails because *aliases* are
held to the filler rule. The asymmetry is the root of both the UCT false positive and the kuleuven refusal;
the ontology lists "computer science and engineering" under `related_not_equivalent`, which this path never
consults.

**Twin signal:** `english_alternate` found a declared English twin on ucph-da and psaclay-fr only; uio,
kuleuven, uba, puc declare none (their English pages, where they exist, are not linked as alternates).

### Sources

- `backend/app/adapters/page_classifier.py` L214–235 (`_DEGREE_WORDS`, `_LEXICON_V2_DEGREE_WORDS`), L585–
  858 (`classify_page`), L974–1030 (`_program_name`, `_program_name_from_context`).
- `backend/app/adapters/discovery/live_discovery.py` L1360–1456 (`matches_field_text`, localized variant,
  `_LOCAL_TITLE_FILLER`), L1457–1490 (`english_alternate`), L1609–1648 (`profile_rejects`).
- `backend/app/adapters/search/ontology.json` (`computer_science.localized_aliases`, flags).
- Scripts and raw output: `scratchpad/wf_tools/{classifier_audit,lx1_audit,unknown_debug}.py`.
