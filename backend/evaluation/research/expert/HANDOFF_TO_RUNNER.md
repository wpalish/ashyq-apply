# Handoff to the AI running research experiments

## Goal and current state

Test whether expert recovery actions can teach the **general** ASHYQ Apply research pipeline to find and verify more official facts. The present branch contains an exporter, trace validator, retrospective diagnostic and three **candidate** hypotheses. It contains **no genuine blind expert trace**, no new live end-to-end capture with Exa, and no promoted production rule. The existing ten-case dataset has 62 human-reviewed known labels; `62/62` is not a target to force by guessing or reading sealed labels.

Start from the PR/commit that introduced `backend/evaluation/research/expert/` on `origin/main`, or use this branch before merge. Re-fetch `origin/main`, inspect `AGENTS.md`, `docs/process/HANDOFF.md`, branch ownership and current CI before editing. The user's older checkout `task/1.1-research-contracts` has unrelated uncommitted work; do not stage or reset it.

## Inputs you may use before submitting a trace

Give the expert **only** a packet made by `prepare` and `ALGORITHM_CONTEXT.md` in an isolated workspace. The packet has baseline observations and public task requests. The expert must not see the repository's gold corpus, `SEARCH_PROBE.md`, scored `diagnosis.2026-09-21.json`, or `hypotheses.json` until its actions are final. The run controller may read them later for adjudication. Record packet hash and baseline pipeline SHA in each trace.

The controller must also block access to public copies of this repository and its benchmark artifacts through browsing or search results. Permit the university research sources and the configured search provider, while excluding GitHub/repo mirrors and any previously published benchmark answer pages. Record this tool policy with the raw logs. Isolation is an access control, not merely an instruction in the prompt.

The run controller can use `data/trace.schema.json` to prepare a blank output form. Validate the submitted form with the Python CLI; the JSON Schema alone cannot establish action order, matching source reads, packet identity or raw-log integrity. Do not expose any scored data while preparing that form.

The historical baseline packet at `artifacts/expert-recovery/pilot-legacy-packet.json` is ignored by Git and can be regenerated with the command in `README.md`. It belongs to a 2026-09-20 HTTP-only capture; use it only to check the protocol. For a decision about the **current** pipeline, make a fresh capture first. `evaluation.research.live` accepts `--case`, `--seconds-per-case`, `--max-pages` and `--out`; set `UNIMATCH_SEARCH_PROVIDER=exa` and make `UNIMATCH_EXA_API_KEY` available through the environment if the configured provider is to be tested. Do not put a key in Git or a prompt. Record whether a provider was actually configured; default is `none`.

From `backend`, with the provider configured outside Git, run a bounded pilot and use the printed `capture.json` path in the next command:

```sh
python -m evaluation.research.live --live --case kaist --seconds-per-case 90 --max-pages 60 --out ../artifacts/expert-recovery/live
python -m evaluation.research.expert prepare --dataset evaluation/research/data/ground_truth.reviewed.json --capture <printed-capture.json-path> --case kaist --out ../artifacts/expert-recovery/kaist-current-packet.json
```

The live harness prints the timestamped capture path and records pipeline SHA, budget and failures. Repeat for the other pilot cases, then use a full cohort run when evaluating generalization. `<printed-capture.json-path>` is a placeholder for the actual path, not a literal CLI argument. Preserve raw capture files in ignored `artifacts/`.

A completed bounded capture can already have exhausted its call or time cap. It is a diagnosis and packet source, not spare budget for more calls. To claim a transferable `same_policy` rescue, the controller must replay the pipeline to the first missed decision, record calls/time already consumed, let the expert choose the next action within the **same total cap**, and record subsequent calls/time cumulatively. If this is not possible, record the expert's extra exploration as `outside_policy` and use it only to design a later equal-budget paired experiment.

## Run loop

1. Run the current pipeline on a case under an explicit fetch/time budget; preserve raw ignored artifacts and the exact commit/configuration. Use KAIST, Toronto and Aalto as three different development cases. The old search probe saw exact programme pages at ranks 30, 4 and 17 respectively; those ranks are **not current end-to-end outcomes**.
2. Export a fresh packet, copy it with `ALGORITHM_CONTEXT.md` to a separate workspace, and start the expert from the baseline's first unresolved step. The controller independently saves every tool call/output to numbered raw logs and records calls/time already spent at that point. For each action the expert records the preceding observation, action, structured `outcome_status` (`success`, `failure`, or `blocked`), result detail, URL, stage, policy mode, elapsed time, cumulative calls/time and the raw-log hash. An action performed outside the pipeline's safe tool space or after the baseline budget is exhausted is explicitly `outside_policy`; it is useful for diagnosis but cannot be presented as equal-budget proof.
3. Validate the trace with `--logs-dir`. A shape-only pass does not establish authentic actions. The expert may propose sources/claims but may not mark them verified.
4. Only after trace submission, let the evaluator read the sealed corpus and official pages. Judge identity, source authority, excerpt, scope and year independently; keep unresolved facts UNKNOWN. Record the earliest missed stage and the repair the algorithm could actually perform.
5. Turn the repair into one rule experiment at a time. Record a frozen candidate set, equal fetch budget, paired baseline/change, provider response versions, cost, latency, recall@5/10/20, first useful evidence, correct claim recall, wrong-scope and unsupported accepted claims. Repeat live baseline and change in the same session because provider results drift.
6. Test on unseen universities, including different campus structures, languages and JS/PDF sites. Update a hypothesis to `tested` only with linked artifacts; promote only when the defined falsification test is survived without precision or scope regression. Keep negative results.

## Three candidate hypotheses to start with

- `ER-01`: bounded exploration for correct official pages below the ordinary cutoff; KAIST/Aalto show headroom, not proof of benefit under equal budget.
- `ER-02`: explicit campus identity/abstention when the request or official evidence does not resolve the campus; hostname similarity alone is unsafe.
- `ER-03`: route research by unresolved evidence obligation after programme discovery; a programme-page candidate alone cannot establish admissions, qualification, fees and scholarship claims.

Read the full guards, counterexamples, source artifacts and falsification tests in `data/hypotheses.json` **after** blind traces are submitted. Read `data/current_rules.json` at that point too: it distinguishes implemented contracts from development-set measurements. Existing `SourcePage`, `ClaimScope`, `programme_identity`, search intent/retrieval and the claim verifier are reusable; inspect their current contracts before adding a path. Do not rewrite the pipeline from the PDF or bypass `Fetcher`.

## Deliverables and acceptance

- A new bounded capture with commit/config, all failures included, and a packet that contains no copied gold fields.
- At least one authentic blind expert trace per selected failure shape, with independent raw tool logs and a valid `validate --logs-dir` result.
- Reviewer decisions tied to current official sources; no invented human signoff or changed signed labels.
- Per-hypothesis paired and held-out results, including negative results and exact budget/cost. No aggregate success claim based only on the ten development universities.
- A handoff update naming the winning or rejected rule, changed code, validation commands, PR and remaining blockers.

Stop promotion if the expert needed sealed answers, an action the pipeline cannot safely perform, an unavailable official source, a higher fetch budget than baseline, or any new unsupported/wrong-scope accepted fact. In those cases preserve the trace as a diagnostic and keep the hypothesis a candidate or reject it.
