# dev5 programme-page labels (four expert workers in parallel, one country group each)

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK experts → owner signs `dev5.draft1.json`. Runs beside 02; the survivors list from 02's probe
trims the table before signature, not before the experts start.

## Goal

One signed label per dev5 case, exactly as dev4's draft1 (programme-discovery ticket 04 Q2 and ticket 03's identity
rule): the programme page URL (local), its verbatim title, the declared twin URL(s) (hreflang or language switcher,
both directions), degree, language of instruction, `how_found`, and — when the university has no exact bachelor CS
programme — the closest official programme as `related_programme_urls` (Computer Engineering, Informatics,
Information Technology are `related`, per the owner's dev4 decision). Request in every case: bachelor, computer
science or nearest official equivalent, autumn 2027 intake, international applicant.

## Four parallel workers (disjoint cases, one draft file each)

| worker | cases | languages | notes |
|---|---|---|---|
| 03-KZ | kbtu, satbayev, aitu | kk / ru / en | kbtu and satbayev may leave dev5 after 02's runner probe; label them anyway from the agent's container through the proxy if their pages open there, mark `access_notes` |
| 03-TR | hacettepe, bilkent, ytu | tr / en | Computer Engineering is the Turkish form (dev4: boun, itu → `related`); record whether an exact CS programme exists |
| 03-CZDE | upol, zcu, tud, lmu | cs / de / en | catalogue URLs often opaque (dev4 vut `program/10326`); record the local section labels on the homepage path |
| 03-ITLT | unipd, sapienza, vilniustech | it / lt / en | Italian `corsi.` hosts and JavaScript course lists (dev4 unibo); Lithuanian `stojantiesiems.`-style admission hosts (dev4 ktu) |

## Protocol (Track A, `SEARCH_FINISH_PLAN_V2.md` §4, restricted to the programme page)

Official domains only; no robots bypass, no UA spoofing, no proxy *other than the agent's own egress*; nothing from
the gold files, the hypotheses register, previous reports or any heldout artefact in the expert's context; the
`university-admissions-research` skill. Output per case in
`backend/evaluation/research/expert/data/programme_drafts_dev5.2026-10-19/<case>.json`, the shape of
`programme_drafts_dev4.2026-10-18`. Every quote verbatim ≤ 300 chars; `accessed_on`; `how_found` as the link path or
the query that found it.

## Verification and signing

The main session dispatches `benchmark-capture.yml` `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/programme_drafts_dev5.2026-10-19` (production `Fetcher` on the runner).
A quote the runner cannot find stays `unknown`. A worker (whichever finishes last) assembles `dev5.draft1.json`
(`Case` schema, `dataset_version: 2026-10-19.dev5-draft1`, `review.status: draft`) with a converter in the shape of
`expert/core_drafts_dev4.py` (programme rows only), and writes `docs/process/SIGN_DEV5_2026-10-19.md` — the dev4
signing table's form (university, local page, title, twin, degree, language, how found, access probe), the dropped
candidates and the leakage table from 02, and the questions the owner must answer (exact-vs-related, twin acceptance).
The owner signs in `OWNER_QUESTIONS.md` (round 2); the signed file is dev5.draft1 with `human_verified`.

## Files the workers hold

`backend/evaluation/research/expert/data/programme_drafts_dev5.2026-10-19/*` (one file per case — disjoint),
`backend/evaluation/research/data/dev5.draft1.json` (assembler only), `docs/process/SIGN_DEV5_2026-10-19.md`
(assembler only), a `core_drafts_dev5.py` converter (assembler only). Nothing else.

## Evidence

- `SIGN_DEV4_2026-10-18.md` (table form, owner decisions on `related`); programme-discovery tickets
  [03](../../programme-discovery/issues/03-programme-identity-equivalence.md) (what counts as found),
  [04](../../programme-discovery/issues/04-dev4-country-proxy-split.md), [15](../../programme-discovery/issues/15-commission-dev4-labels.md).

## Done when

`dev5.draft1.json` validates against `schema.json`; every `known` programme row has a runner-verified quote; the signing
table is in `OWNER_QUESTIONS.md` round 2 with a recommendation per row. Flag: none. Loop id: **G-03**.
