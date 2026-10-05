# Phase1 V2: sealed ten-case live evidence

The algorithm scored4/62 and the experts1/62. Two experts submitted final
answers; eight timed out. `protocol_eligible` and `protocol_gate` are false.
No50-case batches, HELDOUT fact checks or production changes followed.

The Russian comparison is
`docs/process/EXPERT500_PHASE1_V2_2026-10-04.md`.
All10 baseline and55 expert controller workflows use
`9421884465cbc986ce0ab017102126731fe2589d`.
The underlying application tree is equal to main@b672349.
The pre-expert parent-script review checkpoint is2830929.

## What is preserved

- `submission-seal.json`: immutable pre-score hashes, created before the
  reviewed labels were read at2026-10-04T04:06:35.538898+00:00.
- Ten packets, original per-case expert results/traces, baseline results and
  OS isolation proofs. Trace hashes and recorded raw-log hashes are retained.
- Original compact submissions and exact per-fact citation proofs for the two
  experts that completed submission. Incomplete selectors are not predictions.
- Combined captures, strict scores, lossless value projections, comparison,
  workflow URLs, original and pre-expert trial manifests.
- Exact parent scripts and mock-only cycle/integrity tests. Their measured
  protocol hashes are in `trial.json.expert_protocol` and the seal. The older
  top-level trial files describe the pre-baseline preparation and are preserved.
- `export-evidence.py.txt` and this README describe the post-score export;
  they were not executed by expert selectors or used to choose source actions.

`manifest.json` hashes the bounded exported files. It contains no raw HTML/PDF,
credentials or real applicant profile. Submitted quotes remain unreviewed
proposals except for the exact-value adjudication recorded by the frozen scorer.
Expert precision1/2 includes a prose-versus-canonical-value mismatch for
`programme.admission_route`; it is not a semantic error-rate estimate.

## Source proof recovery

Actual source payloads are retained locally in ignored
`artifacts/expert-500/phase1-v2-2026-10-04/`.
Actions recovery artifacts are named `expert-recovery-RUN_ID` with14-day
retention. Each final resumed controller artifact includes the earlier raw
logs without replaying source requests. Use `workflow-runs.json` to identify
the last controller run for each university. For example, KAIST's final run:

```sh
gh run download 37175914811 --repo wpalish/ashyq-apply \
  --name expert-recovery-37175914811 --dir /tmp/kaist-phase1-v2-recovery
```

Validate the trace with the original public packet and the recovered `logs`
directory using `evaluation.research.expert.models.validate_trace`. The
committed trace alone cannot replace the raw-payload quotation check. The
saved `compact-report.py.txt` revalidates all facts and fixed provenance before
opening labels; original local paths in result records require a recovery
mapping when running on another machine. No fresh university requests are
needed for this audit.
