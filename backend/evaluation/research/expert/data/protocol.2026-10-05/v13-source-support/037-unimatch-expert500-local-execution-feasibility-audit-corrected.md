# Corrected source-only local execution / startup audit

This separate note supersedes the first brief's workflow snapshot attribution.
The first brief remains byte-identical and must not be used as primary comparison
or coherent source-snapshot evidence. No model, network/provider/Fetcher,
credential, label, corpus, helper entry point or OS probe was invoked.

## Distinct verified workflow snapshots

| Snapshot | Original path | SHA256 |
| --- | --- | --- |
| pre_cache | `/tmp/unimatch-expert500-v13-workflow-pre-cache.yml` | `dc585a6a0d8149b2cefc8527b0cc8d579569385cc25939f0ec080efc8d2b5c00` |
| current | `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/.github/workflows/benchmark-capture.yml` | `81e37ba2ca56f968bf04052c12421b4b399b7139ddf2f1eaebc55f708af364f9` |

The preserved first brief is `/tmp/unimatch-expert500-local-execution-feasibility-audit.md`, SHA256
`d678f7d08e2aa1fbd85bf2ec70c9080d67801ae1b14b15d99135a03f3811bbe3`. Its footer recorded the intermediate cached workflow
`3be119392da90baed37d4be72bc08878a37d2da29fcb6503049df9911abcff1d`, while its
workflow line references described the earlier pre-cache text. That attribution
was mixed. Both the first brief and this explicit correction are retained.

## Historical observations: pre-cache dc585a only

- Lines7–9 describe the old proxy-only agent container. They are a recorded
  historical connectivity limitation, not verification of a blocker on the
  present desktop. Lines22–25 already allow a self-hosted ordinary runner.
- Lines450–457 select Python3.12, cache pip downloads, create a fresh venv and
  install requirements for each action. Root supplied old job observations:
  expert37339132790 venv2s/pip16s and baseline37337773502 venv4s/pip15s.
  Root's53–55s total overhead includes other setup/transport/poll work; the
  cached environment can target the sampled expert18s portion, not all55s.
- Controller CLI execution/restored raw logs are579–594; always-upload is605–611.

## Current prospective workflow: 81e37 only

- Lines451–479 bind resolved interpreter/platform/runner image/workspace plus
  exact source SHA and requirements hashes. Restore covers only backend/.venv,
  with no prefix fallback. Miss commands480–483 remain the prior venv/install.
- Lines484–495 verify the base interpreter, log installed distribution name/
  version pairs and their digest, and run pip check. Save496–501 occurs before
  source execution. The dependency manifest discloses resolved package identity
  even where requirements contain >= ranges.
- The unchanged stock controller execution/restoration is now623–638;
  always-upload649–656. No one-action dispatch, source STOP, counters, caps,
  cold Fetcher, model effort or guard contract is altered by that setup cache.

## Local seams and remaining identity obligations

The frozen V12 parent1613–1635 explicitly creates `actions: [item]` and1644–1665
calls one GH workflow. This is the transport/provenance choice. Stock
controller.run994–1024/CLI1201–1211 and live.capture_one246–295/child832–860 already
have local entry points. Fetcher499–525/854–866 and network_policy108–144 retain
robots/pacing/checked DNS/IP/redirect policy in either runtime. No code inspected
requires a GH-only Fetcher. Current desktop egress/provider feasibility was not
probed. The public local venv config is CPython3.12.13/macOS arm64, distinct from
GH ubuntu-latest; a local replacement must bind one declared ordinary environment
for both fresh arms and cannot claim the old GH environment unchanged.

A new local transport would need authentic per-dispatch receipts/full raw hashes,
real counters, both original budgets, durable refusal/integrity STOP, isolated
model access, and corresponding report replay. The frozen report requires original
GH run/dispatch identity at351–422/523–629; local receipts cannot impersonate it.
Keep fresh Fetcher/robots/provider lifetime per action when preserving current
semantics: keeping one persistent instance is a separate behavior change.

The present narrow installed-environment cache retains that GH transport and its
receipts. Setup precedes the algorithm's capture_one active clock but consumes
expert900s absolute wall time. Reduced setup introduces no extra allowance or
clock reset. Queue/setup components beyond the sampled install, download and
polling latency remain unmeasured here. No IP/account/provider/proxy workaround
or current connectivity claim is proposed.

The adjacent JSON records exact snapshot-specific structural references and
before/after original byte checks. This is a prospective audit, not a score,
label, new source observation or primary comparison evidence.
