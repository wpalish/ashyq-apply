# Phase1 V3: explicit incremental fact submissions

Status: source preparation; the fresh ten-case paired pilot has not started.
This document is a protocol description, not a search-quality result.

## Reason for this repair

The sealed V2 pilot produced eight final-selector timeouts. Its expert score was
1/62 against the unchanged reviewed corpus; the algorithm scored4/62. Those
negative results and their original seal remain in the V2 evidence bundle.
Rewriting that evidence or extending the120-second allowance would not establish
an eligible expert comparison.

## New submission contract

`expert/journal.py` adds a separate strict protocol, leaving the V1/V2 compact
contract unchanged. Every completed selector object carries the exact SHA256 of
the accepted journal and a small delta of at most16 facts and7 question findings.
It may choose one next controlled action in the same object. Fact IDs and
explicitly submitted findings are immutable. Unknown questions can be omitted;
mechanical expansion reports them as unresolved without inferring absence.

Candidate construction is pure. The parent validates the complete trace against
the recorded controller outputs, then `expert/citations.py` verifies every fact's
official source, raw hash, exact quotation, text/IR/PDF coordinates and visible
scope contradictions. OTHER and unreferenced facts receive the same checks.
Only after those checks does a hash-bound commit marker accept the checkpoint.
A failed later delta or timeout preserves earlier explicit submissions for
audit; it does not establish a clean completed run.

The optional final model object commits the existing journal by hash, with empty
delta lists. It need not reproduce the accumulated quotations. Closing the
research budget also mechanically closes already explicit checkpoint submissions;
the result records `budget_checkpoint` separately from `explicit_commit`.
Selector failures, rejected checkpoints and budget overruns remain visible and
make protocol admission false. Partial timeout text never becomes evidence.

## Blinding and budget

Each fresh tool-free selector gets public identity/request/caps, public ontology,
the accepted current-case ledger, a compact current-case action index and at most
two recent saved-source views. Fresh baseline ranked URLs, facts and telemetry
are excluded from the selector packet. Stored views can be requested explicitly.
No V1/V2 answer, missed route, case diagnosis or signed label enters a prompt.

Real macOS access denial covers the repository, gold/history/memory/attachments,
other expert workspaces, earlier workspaces, and external parent protocol/test
files. The existing bundled Codex CLI and ordinary existing login are used;
no token is read by the research protocol.

Limits stay60 cold Fetcher.get attempts,6 provider searches and120000ms of active
work per case. The source-action deadline is95000ms of that same cumulative clock;
this leaves time to submit the latest observed evidence. At least3000ms is
reserved for mechanical closing validation, not granted as a fresh allowance.
Prompt, selector, source, view, parsing, journal and trace work are metered.
GitHub queue/install/control transport, provisioning and audit-envelope copies
are reported separately. Cancellation or closing overshoot is retained exactly
and makes the run ineligible. Provider429 stops the batch without retry.

## Required verification and measurement

Before source reads: full repository gates, independently mocked journal/citation
and parent-cycle checks, a neutral completed tool-free model turn, a frozen
source revision and hashed actual parent scripts/modules. The unchanged app tree
must still equal the previously verified production source.

The fresh run consists of ten new strict main-algorithm baselines and ten
independent experts, at most three simultaneous. Replay every accepted delta
from its original completed tool-free selector stream, revalidate raw source
bytes and bind final snapshots, proofs, meter ledgers and workflow source IDs.
Seal all ten before loading the unchanged62 reviewed labels. Report that result
before any50-case batch; admission still requires a clean complete protocol and
at least40/62 recovered facts. HELDOUT facts, production deployment, ranking and
signed corpus changes are outside this protocol repair.
