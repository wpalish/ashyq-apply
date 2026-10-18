# Approve a Serper probe budget and the query-language shape

Type: grilling
Status: open
Blocked by: 02, 11
Map: ../map.md · HITL — spends the owner's credits and fixes the shape of the local-language query family.

## Question

Research shows discovery sends six English operator queries and gives Serper no language/country parameter
([Queries, provider parameters and the search-skip defect](11-queries-and-search-skip.md)); six development
programme pages exist only in the local language and were never returned (uba, puc, uio, kuleuven, tec-es,
tsinghua-cn). Whether a keyword engine *can* return them with a local-language or alias query cannot be known
from the captures (the trace does not record the provider's result list). The owner holds the key; probing
costs credits.

❓ **Q1** - **Budget**: up to 300 Serper credits for a one-off probe script run on the GitHub runner, after
[Record provider results and persist the trace at checkpoints](17-record-provider-results.md) lands, so every
result list is kept. Each development local-language case gets at most five query shapes.

➡️ Yes — 300 of the 50 000 credits; one afternoon.

---

❓ **Q2** - **Shapes to probe** (public institution/field/degree words only, I3): (a) today's
`site:{domain} "computer science" "bachelor"`; (b) QA-1 OR-group of strong aliases; (c) the ontology's
localized alias in the site's language with the local degree word (`site:uio.no informatikk bachelor`;
`site:uc.cl "ciencia de la computación" licenciatura`); (d) shape (c) plus Serper `hl`/`gl` set to the site's
language/country; (e) the unquoted natural-language family in the local language.

➡️ Yes — all five, and the decision rule is "a shape that returns the gold (or its twin) in the top 10 for
≥ 4 of the 6 cases becomes a flagged query family; the family count stays at six (QB-1's 3 + 3 reserve)".

---

❓ **Q3** - **Which family gives way, and where the new one sits**: a local-language family must be in the
*first* pass — on puc and uba only pass 1 was ever sent (`discovery_query_passes = [3]`; the SB-1 deadline fell
in recovery — [Queries, provider parameters and the search-skip defect](11-queries-and-search-skip.md)), so a
family in the reserve would never reach the sites that need it. It takes the third first-pass slot;
`programmes` moves to the reserve ahead of `courses`; `admissions` (`site:{domain} admissions "bachelor"`),
which never confirmed a page in the development captures and whose job the topic search does better, is
dropped. Six families stay six; institutions in English-speaking countries keep today's plan byte for byte.

➡️ Yes.

## Evidence

- Query families: `backend/app/adapters/search/intent.py` `queries_for` (L265–347); Serper payload has only
  `q` and `num` (`serper.py` L101–104); `ALIAS_QUERIES = False` (intent.py L83).
- Cases never returned: [Where the programme page is lost today](08-loss-stages-today.md), class B.
