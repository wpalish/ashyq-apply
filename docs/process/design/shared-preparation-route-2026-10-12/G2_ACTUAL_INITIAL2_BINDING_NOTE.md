# G2 initial2 additive binding note

Status: **ONE_PATH_REBIND_RECONCILED / NO_BLOCKER_FOUND / NOT_RUN_BY_REVIEWER**.

This note supplements `G2_ACTUAL_INITIAL_BINDING_REVIEW.md`; the original initial1 pins remain historical and unchanged. Root-reported motivation: terminal initial1 Ruff SIM102 on the nested SAT-sum guard; format, mypy and focus had not run at that initial1 failure. This reviewer did not execute or score either iteration.

Base: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/`.
Initial2 source commit from metadata: `d9adec6b3403070bcc8dd0e854a889009c4bd32b`.

| Artifact | SHA-256 |
| --- | --- |
| `INITIAL_SOURCE_COPY.initial2.json` | `9a1833553080a8dfc41fcbb886087d093f7796b96549e7144e136eef1f1c0f6e` |
| `FINITE_REBINDING.initial2.json` | `46497fbfd0892cc2867eee430571a07dd70e841c5005dc6e1f8b0a69c7a448ab` |
| Active `backend-full/expected-native-source-pins.json` | `641f198e5bffbdf688c0010be7b11db47c796fe732cc5a4ee8db647dff63a7fb` |
| `run_backend_static_initial2.py` | `69842b6432032e9b02e5b9a0a226d710e1990575aed9fef530ec57d2944b0909` |
| Preserved `expected-native-source-pins.initial1.json` | `e2e62a31edba2b7cd154ce1ab3d201e732f9a4cd68bc994157f8fc43a9fe26c3` |
| Preserved `rejected/static1-source/backend/app/schemas/shared_route.py` | `42a97317d9ca7e418f54136cf29deed713083bdc4ce687d0566d81255e5eb5cb` |
| New `source/backend/app/schemas/shared_route.py` | `36a0f1127dfdfa1a32bdc5424888d180a4cb571d42322ef878c62b941dddc286` |

Actual lab and root-owned schema bytes agree with the new hash. Direct source diff contains only replacement of the nested conditional with the conjunction of the same three non-null tests and the same SAT section-sum comparison. The same ValueError and return remain; static inspection finds no behavior change.

Metadata comparison: 762 source entries remain, no added/removed path, exactly the schema hash changed. Active expected map retains 582 entries, no additions/removals, and the same sole hash change. Consequently the 759 G1 predecessor values remain unchanged. The allocator and test bytes retain their initial1 hashes (`da57a45f…` and `8588134b…`; full hashes in the original review).

Direct launcher diff is only output namespace `backend-static-initial1` → `backend-static-initial2`; same three commands, shared lock, network policy, source pins and NOT_FULL result semantics. The runner remains `be4a3f8a645166ab7f5e495f92d47407b74aea0eb5a7603ca26907923f200db6`; guard/asset/default scope is not widened.

No blocker found in this one-path source/metadata rebind. No fresh PASS, helper execution, runtime preflight, full gate or product acceptance is claimed. Future or concurrent root gate outcomes require their own source-bound receipts.
