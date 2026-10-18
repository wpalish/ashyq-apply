# Commission the dev4 programme-page labels

Type: task
Status: open
Blocked by: 04
Map: ../map.md · HITL task — the owner approves the list and signs the table; agents run the experts and the checks.

## Question

Nothing to decide: once [Country-proxy development split (dev4)](04-dev4-country-proxy-split.md) is answered,
the labels have to exist before any local-language rule can be measured. Checklist for the owner and the
agent that runs it:

1. **Owner**: approve or edit the ten candidate universities (one or two per heldout country, none of the
   nine, no shared registrable domain or parent institution with any of them).
2. **Agent**: access probe from the GitHub runner (robots.txt, homepage, one programme catalogue page) for
   each; drop any host that refuses the runner (403, robots unreachable, challenge) — record the probe.
3. **Agent**: one expert sub-agent per university with the Track A protocol (`SEARCH_FINISH_PLAN_V2.md` §4),
   restricted to the programme page: URL, verbatim title, declared twin URL(s), degree, language of
   instruction, `how_found`; official domains only, no bypass, no heldout artefact in its context.
4. **Agent**: `scripts/verify_evidence.py` on every quote; a failed quote stays `unknown`.
5. **Owner**: sign one table (≤ 10 rows, programme page only) — `evaluation/research/data/dev4.draft1.json`
   in the `Case` schema (`programme_urls` holds the local page and the twin, per ticket 03's rule).
6. **Agent**: add `DEV4` to `live.py` (`--case` and `DEV2_DOMAINS`-style domain map), the identity bindings
   file, and a scorecard line; no discovery code change in this step.

## Answer

(open — recorded when the labels are signed: file name, row count, hosts dropped and why)
