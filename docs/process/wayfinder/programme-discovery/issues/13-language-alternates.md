# Language alternates: page-level hreflang versus sitemaps

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5 from saved sitemaps, pages and code.

## Question

A local-language programme page usually has an English twin. Where do the development sites declare it — in
the sitemap (`xhtml:link rel="alternate"`), on the page (`<link rel="alternate" hreflang>`), or only in a
language switcher — and what does the pipeline do with each?

## Answer

**Sitemaps: no alternates anywhere.** Nine saved development sitemap documents (uio index + three faculty
sitemaps, uc.cl, admision.uc.cl ×2, exactas and ingresantes at UBA, UNSW's undergraduate sitemap) contain
**zero** `xhtml:link` or `hreflang` attributes (`grep -c`). `parse_sitemap` (`live_discovery.py` L2095–2116) reads `loc` only, which is
therefore not a loss today; a sitemap-level twin map is not an available shortcut on these sites.

**Pages: hreflang where the CMS writes it, one direction.** `english_alternate` (L1457–1489) follows a page's
`<link rel="alternate" hreflang="en…">` only when (a) the page's own `<html lang>` is set and is not English,
(b) the target is on the same registrable domain. On the hand-fetched gold pages it finds a twin on **ucph-da**
(`hreflang="en-GB"` → `/studies/bachelor/computer-science`) and **psaclay-fr** (→ the English `licence` page);
**uio, kuleuven, uba, puc declare none** (their English pages, if any, are reached through a language
switcher link, not an alternate). The English twin is queued as the next confirm read (`_queue_english_alternate`)
or recovery read, and when accepted it is the page reported; **the local page it came from is not recorded**,
so a gold that lists the local URL scores a miss (ucph before dev3.draft1 added the English URL;
[Measurement gaps](14-measurement-gaps.md)).

**Direction.** The rule is local→English only. The reverse (an English page declaring a local twin) is not
followed and not recorded; the Danish gold for UCPH would have been reachable from the English page's
`hreflang="da-DK"` in one read, and recorded as the same programme under
[What counts as the programme page found](03-programme-identity-equivalence.md) Q1.

**Language switchers.** uio, kuleuven, uba, puc, tsinghua, utokyo, ntutw homepages carry "English" /
"EN" switcher links (checked with `scratchpad/pd_tools/links.py` by the parallel analyst; same observation
here on `wf_pages/utokyo_home.html`: `/en/index.html`). Nothing in discovery follows a switcher; the
navigation fallback scores link URLs by shape and link text by field words, and "English" is neither. A
"read the English homepage once when the homepage is not English" step would be one read and give the walker
and navigation an English link set — a design option for the frontier, not yet a ticket (see map fog).

**What this means for the heldout countries (public facts only):** Czech, German, Turkish, Estonian, Italian
and Lithuanian universities publish local-first sites; whether their programme pages declare hreflang twins
is exactly what the dev4 proxies ([Country-proxy development split](04-dev4-country-proxy-split.md)) will
show without opening the nine.

### Sources

- `backend/app/adapters/discovery/live_discovery.py` L1457–1503 (`english_alternate`, `_attributes`),
  L2095–2126 (`parse_sitemap`), L2762–2785 (`_queue_english_alternate`), L3464–3471 (recovery twin).
- Sitemaps: `scratchpad/pd_pages/{uio_sm0,uio_sm1,uio_sm2,uc_sitemap,admision_uc_carreras_sm,exactas_sitemap,ingresantes_pages_sm}.xml`,
  `scratchpad/fetched/{unsw_sm.html,uio_smi.xml}`.
- Pages: `scratchpad/wf_tools/classifier_audit.py` `twin` column.
