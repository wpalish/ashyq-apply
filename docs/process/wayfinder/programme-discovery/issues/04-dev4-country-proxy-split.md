# Country-proxy development split (dev4)

Type: grilling
Status: resolved
Blocked by: 01
Map: ../map.md · HITL — a labelling commission and a budget; the owner decides.

## Question

Every local-language rule this design needs (query language, URL lexicon, subject-title shapes, twin
following) must be tuned on development cases, and the heldout nine are the only cases in Czech, German,
Turkish, Estonian, Italian, Lithuanian and Kazakh sites. The development sets today cover Spanish ×4,
Norwegian, Danish, Dutch, French, German-Swiss, Russian, Japanese, Chinese ×2, Thai — none of the heldout
languages except Kazakh (kaznu, access-blocked) and German (ETH, whose English pages are complete). Should a
fourth development split be built from *other* universities in the heldout countries?

❓ **Q1** - **Build dev4**: 8–10 universities, one or two per heldout country, none of the nine, chosen for the
same site shapes (local-language catalogue with English twins, opaque admission-system URLs, Crawl-delay
hosts). Candidates the agent would propose, subject to the owner's veto: Czech Technical University (CTU),
Brno University of Technology; RWTH Aachen or KIT; University of Bologna or Sapienza; TalTech; Kaunas
University of Technology; Boğaziçi or Bilkent, Istanbul Technical University; KBTU or Satbayev University.

➡️ Yes — dev4 with these ten; the agent fetches robots and homepages first and drops any that is access-blocked
from the runner (an access-blocked proxy teaches nothing).

---

❓ **Q2** - **Label only the programme page** (URL, verbatim title, declared twin URL, degree, language of
instruction) — not the six core questions. One expert sub-agent per university, quote-verified by
`scripts/verify_evidence.py`, owner signs one 10-row table.

➡️ Yes. Discovery tuning needs one label per case; core labels cost an hour each and belong to Track A.

---

❓ **Q3** - **Scoring rule for dev4**: programme-page recall with the identity rule of
[What counts as the programme page found](03-programme-identity-equivalence.md); paired runs on dev4 join the
three sets, with the same "no stable loss on any set" bar.

➡️ Yes.

---

❓ **Q4** - **Stop rule against leakage**: no dev4 university shares a registrable domain or a parent
institution with any of the nine; nobody opens a heldout page to pick dev4 cases.

➡️ Yes.

## Evidence

- Language coverage of the development sets: `evaluation/research/data/dev{2,3}.draft1.json` (`country`,
  programme URLs), `docs/process/DISCOVERY_ANALYSIS_2026-10-17.md` §3 (dev2 design table).
- Local-language failures that motivate it: [Where the programme page is lost today](08-loss-stages-today.md)
  class B; [Classifier audit](10-classifier-audit.md).

## Answer

2026-10-18, the owner (Диас): **yes** via 02-Q2 — the recommended answers stand as written.

Accepted: Q1, Q2, Q3, Q4 — each recommended answer (➡️) above is the decision.
