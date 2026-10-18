# Queries, provider parameters and the search-skip defect

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5 from code and the bundle5 captures.

## Question

What exactly does discovery send to the search provider for an unseen university (query shapes, language,
operators, provider parameters), how many of the six queries reach the provider under today's defaults, and
can a local-language programme page be returned by the shapes sent?

## Answer

**Shapes (`intent.py` `queries_for`, L265–347; the degree and field are the applicant's public request words,
never a profile attribute — `_reject_applicant_data` L99):**

| family | text (bachelor, computer science, intake 2027, domain d) | pass |
|---|---|---|
| field_and_degree | `site:d "computer science" "bachelor" 2027` | 1 |
| natural_language | `{institution} bachelor's computer science programme 2027` (unquoted) | 1 |
| programmes | `site:d programmes "computer science" 2027` | 1 |
| courses | `site:d courses "computer science" 2027` | 2 |
| undergraduate | `site:d undergraduate "computer science"` | 2 |
| admissions | `site:d admissions "bachelor"` | 2 |

`_degree_aliases` renders the level as one quoted word. Serper's adapter appends `site:d` again
(`serper._with_domains`, L38–52) unless `ALIAS_QUERIES` is on, and sends only `{"q": …, "num": 10}` — no
`hl`/`gl` (language/country) parameter (`serper.py` L101–104). `ALIAS_QUERIES` (QA-1: OR-group of strong
aliases) is `False`; there is **no family in the site's language**, and the ontology's `localized_aliases`
are used only on the identity side (LI-1), never in a query.

**Passes under QB-1 (`DISCOVERY_QUERY_RESERVE = True`, `DISCOVERY_FIRST_PASS_QUERIES = 3`):** pass 1 sends
three families and reads up to 8 leads; pass 2 sends the other three only when nothing is confirmed. In the
bundle5 captures the misses all show `discovery_query_passes = [3, 3]` except: uba, puc (`[3]` — the SB-1
deadline fell in recovery), uct, khalifa, hku (`[3]`, a page confirmed after pass 1), and **uio (none)**.

**Can an English keyword query return the local-language gold pages?** Not from the captures: the provider's
result lists are not recorded ([Measurement gaps](14-measurement-gaps.md)), so "never seen" (uba, puc, uio,
kuleuven: the gold URL appears in no read, rejection or lead) cannot be split into "not returned" and
"returned below the 8 leads read". Offline check on the saved gold pages: the phrase "computer science" does
not occur in `uio_gold.html`, `uba_gold.html`, `puc_gold.html`, `kul_gold.html` (Norwegian, Spanish ×2,
Dutch texts); a quoted `"computer science"` keyword query can match them only through anchor text or
Google's own translation layer, which `site:` queries do not invoke. This is the open question for
[Approve a Serper probe budget and the query-language shape](07-serper-probe-and-query-language.md).

**Hop entry roots** (`retrieval._entry_points`, 3 hosts) are skipped under SB-1 whenever any stage offered a
programme lead (`_skip_hop_roots`), so on the misses they ran only where nothing at all was kept.

**Defect (restated from [Where the programme page is lost today](08-loss-stages-today.md), confirmed in code):**
`_add_search_results` L2985–2995 returns "all 3 programme-page slots were already filled" when
`len(selected[PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY`, counting *unconfirmed* sitemap picks; it has already
set `_search_attempted = True` (L2975), so `_search_due()` never fires again and the post-walker search is
guarded by `searched_early` (L2637–2641). On uio (sitemap stage 34 s > `SEARCH_LATEST_START_SECONDS = 33`,
three medicine/humanities picks in the slots) search never ran and recovery had nothing to read. Fix shape
(for the loop): count `self._confirmed` in that early return, and let `search_now()` run after confirm when
the early return fired — a pure bug fix under the existing paired-run protocol.

**Site search surface:** `backend/app/adapters/search/site_search.py` (a university's own search box) is
wired nowhere in discovery — the only reference is an enum value in `fusion.py` L49. It is a dormant option,
not a stage.

### Sources

- `backend/app/adapters/search/intent.py` L55–100 (flags), L219–347; `serper.py` L38–52, L95–115;
  `retrieval.py` L344–420; `backend/app/adapters/discovery/live_discovery.py` L2942–3000, L3117–3230.
- Captures: `scratchpad/runs/bundle5-*/x/*-on/*/*.raw.json` (`discovery_query_passes`, `search_limitations`).
- Pages: `scratchpad/fetched/{uio_gold,puc_gold}.html`, `scratchpad/pd_pages/{uba_gold,kul_gold}.html`.
