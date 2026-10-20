# H-C: local-language discovery — is the lexicon general or memorised? Leave-one-country-out on R5 / LX-1 / subject shapes

Type: research
Status: resolved for steps 1–2 (LOCO-1, 2026-10-20); steps 3–4 wait for dev5 (13-Q1) and a key (01-Q6)
Blocked by: —
Map: ../map.md · AFK, offline first (recorded provider result lists in the dev4 base3 captures, dev5 draft titles);
one live probe only with the owner's ≤ 300-credit yes (01-Q6). Becomes a task (LQ-2) only if H-C is confirmed.

## Question

R5 (the `local_language` query family), LX-1 (URL lexicon) and the subject-title shapes (programme-discovery tickets
09, 10, 19) carry per-language words. dev4's gold was returned by the `local_language` family in 5 of 5 labelled
cases; on the nine the gold is never returned by any family in 4–6 of 9 and 16–18 reads per column are refused
`subject_mismatch`. **If the words were taken from dev4's own programme titles (Informatika, Informatik, Informatica,
Informaatika, Bilgisayar Mühendisliği…), the family finds dev4 and nothing else in the same language.** Test it
without the nine: hide one development country's words and measure that country.

## Test

1. **Inventory** (`app/adapters/search/intent.py`, the R5 lexicon; `live_discovery.py` LX-1 and the subject shapes;
   `page_classifier.py` subject words): per language, every word/shape and the development case that motivated it
   (from the loop report and the programme-discovery tickets). Table: language → words → source cases.
2. **Offline LOCO on recorded result lists**: for each dev4 case (base3 captures record each family's top-10 URLs),
   recompute which family *would* have returned the gold if the query had been built without that case's country
   words (i.e. the English families only, or the local family with the remaining languages' words). Count
   gold-returned per country with and without its own words.
3. **dev5 titles offline** (from 03's drafts as they land — no run): for each dev5 gold title, does any R5 word / LX-1
   slug / subject shape match it? Which refusal would the confirm predicate give (`subject_mismatch`,
   `degree_level_other`)? Same table as programme-discovery ticket 10, per dev5 case.
4. **Live probe** (only with 01-Q6 yes; `mode=query_probe`, `--cases <dev4+dev5 ids>`, ≤ 300 credits): the
   `local_language` family with (a) today's words, (b) the words of the *other* development countries only, (c) a
   query built from the page's own evidence — the homepage's local section label for study programmes and the seed
   row's name; record gold-in-top-10 per variant per case. (c) is the LQ-2 shape.

## Deliverable

`docs/process/LOCAL_LANGUAGE_LOCO_2026-10-19.md`: the inventory, the LOCO table (gold-returned per country, own
words in / out), the dev5 title audit, the probe table if run. Verdict: **H-C confirmed** if gold-returned drops by
≥ 2 cases when a country's own words are removed, or if ≥ 4 of the dev5 titles match no word or shape; **refuted**
if the family still returns ≥ 80 % of the gold without the country's own words.

If confirmed, propose **LQ-2** (`LOCAL_QUERY_FROM_PAGE_EVIDENCE`, `--local-query-from-evidence`): the local family's
query terms come from the site itself (homepage section labels for programmes in the page's language, the
catalogue's own listing words, the seed row's native name), the lexicon only as a fallback; one query of the six, no
applicant attribute. Bar: gold-returned on dev4 + dev5 unchanged or up, no stable loss on cohort/dev2/dev3, and the
seen-site guard (13). Files it would touch: `intent.py`, `live_discovery.py` (local query hook).

## Files the worker holds

`scratchpad/g08/*`, the new doc. No code change in this ticket.

## Evidence

- `HELDOUT_STAGE_SUMMARY_2026-10-19.md` `returned_by_family:*`, `read_refused:subject_mismatch 16–18`;
  `STAGE_SUMMARY_DEV_2026-10-19.md` dev4 `returned_by_family:local_language 5`; programme-discovery tickets
  [07](../../programme-discovery/issues/07-serper-probe-and-query-language.md), [09](../../programme-discovery/issues/09-url-lexicon-audit.md),
  [10](../../programme-discovery/issues/10-classifier-audit.md), [19](../../programme-discovery/issues/19-subject-title-shapes.md);
  the loop report R5 line (gains uba, iitd).

## Done when

The doc is committed; the Answer gives the verdict, the per-country LOCO numbers and, if confirmed, the LQ-2 proposal
with its bar. Loop id: **G-08** (LQ-2 if built).

## Answer — steps 1–2 (LOCO-1, 2026-10-20)

Source: [LOCAL_LANGUAGE_LOCO_2026-10-20.md](../../../LOCAL_LANGUAGE_LOCO_2026-10-20.md) (NEXT_CYCLES_2026-10-20 item 8; the
deliverable is dated the day it was done, not 10-19).

- **Inputs.** The recorded store `recorded_search.base3.json` and 39 dev gold pages read by hand through the
  production Fetcher (robots honoured, own UA, `trust_env_proxy=True` after a direct refusal).
- **Not read.** No dev5 title, no heldout file, no search call.

**Verdict: H-C confirmed by this ticket's rule.** Gold-returned, summed over the leave-one-language-out folds:

| | own words in | own words out | drop | survive |
|---|---|---|---|---|
| store (query side) | 20 | 15 | −5: warsaw pl, uba es, kuleuven nl, uio no, ctu cs | 75 %, below the 80 % refutation line |
| gold pages (page side) | 18 | 13 | −5: psaclay fr, uba es, puc es, uio no, unibo it | 72 % |

- **Per language.** The store drop is at most −1, since no dev language has two cases that depend on it. German loses
  0 of 4. The page side drops es −2.
- **Control.** LV-1's battery, run through the same removal, refuses 24 of 24 once a language's own rows are gone
  and still accepts 24 of 24 when an unrelated language is removed.
- **Survivors.** Every local-language gold page accepted today (12 of 12) is refused without its language's rows.
  Of the 13 page-side survivors, 9 survive only through an English gold twin.
- **dev5 criterion.** Not testable (13-Q1). INDEX_CEILING's dev title test stands in, in-sample.

**What is confirmed: dependence, not wholesale memorisation.** `git log -S` provenance shows:

- Strictly memorised rows (a row born from the case it finds):
  - uio: `informatikk` (LX-1);
  - puc: `licenciatura` and «ingeniería en ciencia de la computación» (LX-1 / R1);
  - ucph: `datalogi`;
  - ub: ca `informàtica`;
  - kuleuven: `studieprogramma` and `/opleidingen/<x>/`.
- Strict-provenance LOCO drops only uio on the store (1/20), and uio + puc on the pages (2/18).
- The rest are dictionary headwords that predate the case: the ontology seed of 09-21, and LI-1 before dev4 existed.
- The concrete generalisation defect is that **R5 sends one alias per language, the first in the file**. Spanish
  plural (uba's title) leaves puc unreturned on the store, while M5's singular (puc's title) put puc at rank 1.
- **Flag for the second look.** LI-1 (`2feafa97`) cites the quarantined 10-17 analysis, and its comment names TUM and
  Polimi. R1 (`d44d32d3`) included heldout countries' languages. The de/it/cs/tr rows may have been written with
  heldout pages in view.

**LQ-2 proposed** (`LOCAL_QUERY_FROM_PAGE_EVIDENCE`, `--local-query-from-evidence`, off; regime C, live-only, built
when a key exists).

- **Query words.** The local query's subject phrase comes from the site's own programme-link text in its
  `<html lang>`, then the seed row's native name. The lexicon is the fallback.
- **Budget.** One query of the six, same `hl`/`gl`, no applicant attribute.
- **Files.** `intent.py` and the plan hook in `live_discovery.py`.
- **Bar.** dev4 + dev5 gold-returned unchanged or up; no stable loss on cohort/dev2/dev3; 0 new wrong pages; the
  seen-site guard (13).
- **First probe.** puc, tec, psaclay, kaist, kaznu, msu, ntutw and tsinghua (`query_probe`).
