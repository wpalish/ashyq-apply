# A model as a URL hint, never as evidence: the offline audit and the design note

Type: research
Status: open
Blocked by: 01-Q6
Map: ../map.md · AFK — a hand audit on the 44 development cases (no code, no credits: the owner's existing chat
subscription or a local model on his computer) and a design note. Nothing is built in this map.

## Question

The owner asked whether "just asking a chat assistant" could replace search. Alone it cannot be what the product
promises: a value with a source URL, a verbatim quote and a date, checked by our own fetcher (the knowledge-base
rule, `verify_evidence`); a model's answer has none of these, its training data is months to years old against a
yearly admissions cycle, and it invents URLs that look official. **As a hint it is a different thing**: a URL
proposer behind the fusion seam, whose every URL is fetched through `Fetcher`, classified, confirmed and quote-checked
exactly as a search result is, and which costs one read per URL. Is that read worth spending — how often is the
proposed URL the gold page or its twin, and how often is it a 404 or another university's page?

## Audit (by hand; results in a table, no model name in the repository)

For each of the 44 cases the prompt carries only the `DiscoveryIntent` words — institution name, official domain,
"computer science", "bachelor", intake year, institution country — and asks for the official programme page URL and
the admissions-requirements URL (two URLs). Score each URL: `exact` (gold or twin, `same_programme_page`), `related`
(a sibling programme on the label's list), `catalogue` (a listing that links the gold within one hop), `wrong_page`
(official domain, not the programme), `off_domain`, `404`. Repeat once a week later to see variance. Also ask for the
six core values for five cases and check them against the signed gold with quotes — expected to show why the model
alone cannot be trusted (stale year, wrong population), recorded as numbers not opinions.

## Design note (what 10 decides on)

- `Generator.MODEL_HINT` in `fusion.py`, weight ≤ the sitemap's 0.6 (an unranked guess), at most 3 URLs per
  institution, off-domain URLs dropped before any fetch (`same_institution`), entering `discover_candidates`'
  candidate set like any generator; the 60-request budget counts their reads.
- Privacy: the prompt is the `DiscoveryIntent` (which rejects applicant data by construction) — a row for the §6.4
  table saying so; D9 holds: a zero-retention provider with `UNIMATCH_LLM_DATA_POLICY_ACK`, or a local model on the
  owner's computer for the build job only (05's index builder could take hints offline).
- Cost per university at a free tier or a local model; latency; a hint cache keyed by (domain, field, level, year)
  so the same question is never asked twice.
- The bar before building: `exact + catalogue` ≥ 50 % of cases on the audit, `off_domain + 404` ≤ 20 %, and a paired
  arm showing gold-returned up with wrong pages not up.

## Deliverable

`docs/process/MODEL_HINT_AUDIT_2026-10-xx.md`: the audit table per set, the variance between the two runs, the
five-case value check, and the design note with the bar. The decision whether to build is 10's.

## Files the worker holds

The new doc only. Read-only: `intent.py`, `fusion.py`, `retrieval.py`, `SPEC_matching_v2.md` §6.4, the gold files.

## Evidence

DoD change log 2026-10-18 (18-Q2 (c): a model extractor only paired with a rule that reaches the pages — a hint *is*
a reach rule); `base.py` ("a search result is a discovery hint, never evidence"); `KNOWLEDGE_BASE.md` (what a fact
needs: URL, quote, date, official domain).

## Done when

The doc is committed with the numbers; 10 has the row.
