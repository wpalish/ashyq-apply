# Fresh paired runs, 2026-10-05 / 06

The `baseline/metrics*.json` files re-score one frozen capture (2026-09-20). The
runs here are **live** runs of the code as it stood on each date: ten cohort
universities (three for the documents rules), four repetitions in ABBA order
(rule off / on / on / off), provider `exa_mcp`, budget 6 queries / 60 reads /
120 s per university. Each was captured by `.github/workflows/benchmark-capture.yml`
(mode `expert_paired`); the run id is the first line of each `.md`.

All are scored here against the signed corpus **reviewed9** (73 known labels),
with `python -m evaluation.research.scorecard <unpacked artifact>`. A run
scored at the time against draft8 or reviewed8 may read slightly differently;
the artifact is the record and re-scores the same way.

| File | Rule (flag) | Stable gains | Stable losses | Decision |
|---|---|---|---|---|
| bl1 | BL-1 shared query budget | 0 (7-query cases 10 → 0) | 0 | on |
| dl2b, dl2c | DL-2 deadlines | see files | 0 | on |
| ty1, ay1b, ay1c | TY-1 fee-row year, AY-1 applicant year | Groningen tuition (ay1c) | 0 | on |
| doc2, doc3, doc3b, doc3c, doc2b | DOC-3 documents page, DOC-2 document rules (documents stage on) | Groningen transcript ×2 (doc3c), secondary diploma ×2 (doc2b) | 0 | on |
| eu1 | EU-1 euro grouping | 0 | 0 | off (no page reaches it) |
| sr1 | SR-1 rate-limit retry | 0 (rate-limit failures 8 → 4) | 0 | on |
| df1, df1b | DF-1 year-column fee tables | Delft tuition (df1b, after the cost-adapter year fix) | 0 | on |
| rl1 | RL-1 route and deadline links (run 37545452839) | Delft IELTS, UBC deadline | 0 | on (owner delegation) |
| — | LG-1 lone language label (Vienna) | not run | — | dropped: the verbatim check needs title and label in one excerpt |
| control-twopass | none: all defaults, two-pass order (run 37540385440) | baseline 20/73 known, 10/60 core, precision 1.0 | — | new baseline |

The two-pass control shows KAIST at 0/11 for an access reason only the
runner has: `admission.kaist.ac.kr` answers neither robots.txt nor pages
from GitHub (ConnectTimeout), while the production probe from Fly reads it
(`access_probe_fly.md`).

The earlier runs (doc2, doc3, doc3b, df1) exposed bugs that were fixed before
the decision; they are kept because the fix is justified by them.
