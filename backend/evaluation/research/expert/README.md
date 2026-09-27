# Expert recovery protocol

This package is offline evaluation tooling. It changes no production discovery or claim decision. It turns a failed bounded run into a blinded task for an expert, validates a recorded-action trace, and keeps scored diagnosis separate from the expert's workspace.

## Existing evidence and its limits

- `data/ground_truth.reviewed.json`: signed development corpus, 62 known labels across ten cases. It is sealed during expert navigation.
- `baseline/capture.json`: bounded HTTP-only pipeline capture from 2026-09-20, before the later search/scope work. Its short excerpts are not source proof.
- `baseline/search_probe.exa.hop.json`: 2026-09-21 search probe. It reports candidate positions, not successful fetches or accepted claims. The live provider has run-to-run variance.
- `expert/data/diagnosis.2026-09-21.json`: retrospective comparison of those artifacts. Its `legacy_stage` is only as specific as the old capture permits. It is not a new end-to-end result.
- `expert/data/hypotheses.json`: candidate rules and falsification tests. None is promoted by this package.
- `expert/data/current_rules.json`: existing code contracts and development-set observations, with limits. This prevents rediscovering a shipped signal as a new fix.
- `expert/data/trace.schema.json`: machine-readable JSON Schema for the submitted trace. The Python validator adds packet linkage, action order, source-read and raw-log checks.

## Make a blinded packet

From `backend`, with the project Python environment:

```sh
python -m evaluation.research.expert prepare \
  --dataset evaluation/research/data/ground_truth.reviewed.json \
  --capture evaluation/research/baseline/capture.json \
  --case kaist --case toronto --case aalto \
  --out ../artifacts/expert-recovery/pilot-legacy-packet.json
```

The packet copies only `id`, `university`, `domain`, and `request` from each gold case. It adds the independent baseline's ranked/returned URLs, failure, counts, limited telemetry and the bounded-run budget. A URL present in the baseline may coincide with a signed URL; the exporter never reads the signed URL field. Tests pin this allowlist. `dataset_sha256` and `capture_sha256` identify the sealed inputs without revealing answers.

For an actual blind run, first produce a **fresh** bounded capture from the current pipeline, then use that capture in `prepare`. The historical packet is a protocol example, not a current product measurement. Copy only the resulting packet and `ALGORITHM_CONTEXT.md` into a separate workspace. Do not mount the repository or grant the expert access to `ground_truth.reviewed.json`, the scored diagnosis, `SEARCH_PROBE.md`, or the hypothesis registry before its trace is submitted. A prompt alone cannot enforce blinding.

## Record and validate actions

Each trace contains chronological actions with the observation that preceded the action and the earlier step it came from (`null` for the initial packet), tool, URL, structured success/failure/blocked status, result detail, stage, elapsed time, cumulative Fetcher calls and elapsed time, cost when measured, policy mode, and a relative raw-log path plus SHA-256. The trace records the counts already spent at the intervention point. A `same_policy` action cannot exceed the packet's call/time caps; the disabled browser tier cannot be marked `same_policy`. `other` tools are automatically `outside_policy`. A proposal cites one or more action numbers, including a successful same-policy `Fetcher` or enabled browser read of the exact source URL, and remains `unreviewed`; the trace cannot claim a human signoff. Preserve failed tool calls. Do not record hidden chain of thought.

```sh
python -m evaluation.research.expert validate \
  --packet ../artifacts/expert-recovery/pilot-legacy-packet.json \
  --trace ../artifacts/expert-recovery/traces/kaist.json \
  --logs-dir ../artifacts/expert-recovery/logs
```

Without `--logs-dir`, validation checks schema and packet linkage only and prints that limitation. With it, every raw log must exist and match its hash. This verifies stored bytes, not whether a human or AI fabricated those bytes; the run controller must capture tool outputs independently. Keep raw pages/logs in ignored `artifacts/`, remove applicant PII, and preserve provider request accounting. Any page used as claim evidence must have been fetched through `Fetcher` and must pass the normal identity, scope, authority and freshness checks. External browser or search actions can inform a hypothesis but are `outside_policy` until the production action space supports them.

## Reproduce retrospective diagnosis

```sh
python -m evaluation.research.expert diagnose \
  --dataset evaluation/research/data/ground_truth.reviewed.json \
  --capture evaluation/research/baseline/capture.json \
  --probe evaluation/research/baseline/search_probe.exa.hop.json \
  --registry evaluation/research/expert/data/hypotheses.json \
  --out evaluation/research/expert/data/diagnosis.2026-09-21.json
```

Run this scored command only in the evaluator workspace **after** the expert trace is final. Do not export the scored diagnosis to the blind expert. The output is deterministic on the committed inputs.

## Promotion rule

`candidate` means a plausible repair, not a measured improvement. To move to `tested`, link a paired experiment under equal fetch budget and a separate held-out set. To move to `promoted`, show reproducible end-to-end improvement with no loss of correct sources and no added unsupported or wrong-scope accepted claims. Preserve failed trials and provider drift. Do not tune or report success on the same ten cases alone. See `HANDOFF_TO_RUNNER.md` for the complete transfer contract.
