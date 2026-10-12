# G2 recovery helper preparation: finite independent review

**2026-10-12 · READ_ONLY_SOURCE_REVIEW · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Scope is only G2_RECOVERY_HELPER_PREPARATION.json, the three declared old/new external script pairs and their saved diffs. Mutable final15 application/test drafts were not read. Root is the sole source/helper/runtime writer. This review is a helper binding check, not a full gate, application qualification or native E2E result.

## Reconciliation

All six actual old/new script SHA-256 values match the prepared receipt. Each actual full-file old/new diff was regenerated using ordinary read-only diff and is exactly equal to the corresponding saved diff, including the headers. Observed at **2026-10-12 04:18:30 UTC**.

| Pair | Exact sole change | Preserved boundary |
| --- | --- | --- |
| g2-execution/run_static_persistence7.py → run_static_persistence8.py | Line3 output prefix evidence/static-persistence7 → evidence/static-persistence8. | Source root, retained source pin inventory, shared nontruncating lock, seven command order/argv, deny-network sandbox, timeouts, before/after equality and fail/incomplete result logic are byte-identical. |
| g2-execution/run_native_pair.py → run_native_recovery_pair.py | Line9 subprocess target e2e/run-native.py → e2e/run-native-recovery.py. | demo→auth order, interpreter, cwd, shared lock, early nonzero stop and finally unlock are byte-identical. |
| g2-execution/e2e/run-native.py → run-native-recovery.py | Added lines129–138: demo-only network_fault_control metadata. | All runtime/asset paths, native config selection, source/environment/foreign-port guards, loopback-only sandbox, ports5229/8139, dispatch, auth settings, harness copy, native worker/lifespan and owned process cleanup are otherwise byte-identical. |

The additive Demo field explicitly describes **one owned real loopback shared-route PUT**, forwarding to the actual API and suppressing only UI response delivery after observing the accepted receipt. It says no fabricated response/receipt and no automatic client PUT retry. Auth and existing diagnostic metadata are unchanged. The existing mock_routes_or_apis=false is read here as “no fabricated route/API responses”; the adjacent explicit fault description prevents presenting Demo delivery as entirely unintercepted.

This metadata is prepared descriptive intent, not an observation of the native test running: the launcher writes run.json before dispatch. Final15's sealed native test and the future real run must confirm the forwarded actual PUT, accepted server receipt and abort order. No runtime success is inferred from these booleans, old helper gates or the receipt's application_changed=false field. This review did not audit an entire application tree or execute any helper.

## Finding/disposition

**No additional actionable helper-binding defect found within this finite diff.** The intended three deltas are exact; no guard/port/dispatch/source/cleanup widening was found. Final15 source/helper/Panel tests remain a separate pending review and runtime remains root-only. Nothing was imported or executed; no network/provider/auth-data/label/STOP work occurred.

## Exact observed pins

All paths below are relative to product-platform/2026-10-12.

| Input | SHA-256 |
| --- | --- |
| G2_RECOVERY_HELPER_PREPARATION.json | 472497b58b819017823e114e287cd19a29547cfb05d6dabafdd943cafda86244 |
| run_static_persistence8.py.diff | 9bb67a83af1f01fa0cf02b85c8995d1cad4a64e64c85cbc4cdb9c6f98b23a6e5 |
| run_native_recovery_pair.py.diff | 78a42eaa9b54ec2013099ab8d7d94b5ff096ce8b028c9cdd11cb3bfc5e42e298 |
| run-native-recovery.py.diff | 1d842a11d90ae3bb8f3445fabb8b2f22290f353ba0b5d70952065c82a60787f7 |
| g2-execution/run_static_persistence7.py | e724a2760d18d8cfb90b797db74aa350c9c2289b4ccf51d23f1a4c84b47561ee |
| g2-execution/run_static_persistence8.py | 4ed451adbe48cfbe9715be150218c597bba6d9dbd501730f199132b65d28dcb3 |
| g2-execution/run_native_pair.py | 3aaa42e04a852b49ac7503dea4789a21890d3971c60fc62d539638439a4527a6 |
| g2-execution/run_native_recovery_pair.py | 649d32308280f8a9e28d6dacd5640ebe263a0147422416ec5bc0a2fc68985d8c |
| g2-execution/e2e/run-native.py | 70f5536b7eb896939297a19cbb18ad8093f2e6fe8f5d845f319c4013bce70a50 |
| g2-execution/e2e/run-native-recovery.py | 7011d9f13b731f3bfc2a8600122b6c268f9648465ce4463501e5e369f1338473 |

Prior helper files and prepared receipt/diffs were preserved; only this separate external review was created.

