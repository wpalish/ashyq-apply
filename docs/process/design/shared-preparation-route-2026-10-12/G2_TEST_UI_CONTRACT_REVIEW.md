# G2 sealed tests and applied UI contract review

Status: **READ ONLY / SOURCE ONLY / NOT_RUN**. This report sits outside every sealed source and test packet. It does not amend an application file, a proposal, Git, HANDOFF, import or runtime state.

## Exact inspected pins

- Sealed backend tests: `proposals/g2-tests/SEAL.json` SHA-256 `c179e6c442aff7d4754bc44acad7b76d4580dbbe84b333cd8d42e3d60acb13b0`; `test_shared_route_api.py` `dadff091663ff0e27a386667efc2499e845ebdf51caadfc9db819fff3d0aacd7`; `test_preparation_write_concurrency.py` `f6a10320113a7bfe30dfea42fd70c8d229f8da0463cd349edc66bf481167ab25`. The packet itself says NOT_APPLIED/NOT_IMPORTED/NOT_RUN.
- Applied frontend: `frontend/src/screens/SharedRoutePanel.tsx` `fdc16aedc9af24f0db7072797cf2ff713b57020744baf733a976dabca29ccca6`; its test `38fc84d0c783c5289eed6ad52b73a6062c632f086cf86953224f329ef6260142`; `PreparationScreen.tsx` `3de3a2a2ed36dc7e2cc840e947b2c4c91a21c5729af468ed8c40611bb85c41fb`; client `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789`.
- Native access source: `backend/app/api/routes_preparation.py:486-498` checks active preparation access for exact lesson GET; `:563-590` checks own profile and exact attempt UUID for saved attempt review GET without a preparation-term gate. `PreparationScreen.tsx:212-230,243-248,366-380` already opens own review from Progress without the term flag.

## F1 — Applied G2 UI disables an owned saved review after expiry

`SharedRoutePanel.tsx:533-535` passes `allowed && status.preparation_access === 'active'` to the whole saved allocation. At `:563-566` that one flag disables **both** `lesson` and `attempt_review` buttons, even when the exact action has current `content_status='available'`. Once a preparation term expires, the shared route therefore cannot open an applicant's own saved attempt review, although its native GET remains authorized and the same Preparation screen's Progress view allows that review. The lesson disable is correct; the review disable is a UI contract error.

**Narrow source correction for root:** use the exact slot kind and current content status at the saved-action button. A saved available `attempt_review` should remain clickable for the own read-only review when the term is expired/unknown; an exact `lesson` remains disabled without active preparation. Keep preview, new save, retry of a new unaccepted intent and lesson start under the existing access gates. Continue passing the exact ref to `onTarget`; `PreparationScreen.openLearningTarget` already routes an attempt review to the owned review GET. An unavailable/unknown exact review remains disabled.

## F2 — Current assertions do not exercise the split access rule

The applied `SharedRoutePanel.test.tsx:246-279` constructs one expired saved **lesson** slot and correctly asserts “Open exact lesson” disabled. Its title says “without opening content,” which is broader than the native read contract. The sealed backend `test_shared_route_api.py:293-327` expires preparation and checks replay/current/402 new write, but creates no own review there. The sealed `:637-660` checks an old own review GET while access is active. Neither assertion set proves **expired own attempt review GET 200 plus exact lesson GET 402**, or the panel's matching review-button behavior.

**Finite additive controls for root:** in an own case, save one exact review action while access is active; expire the preparation term; assert shared current/history retain that exact review slot and its `content_status='available'`, own `/attempts/{uuid}/review` returns the unchanged receipt, and exact `/lessons/{id}?version=...` returns 402. In the panel test, include both saved slot kinds with current status available and expired access; assert review button enabled and passes the exact attempt UUID/lesson/version to `onTarget`, lesson button disabled, no preview/save. These controls can be additive; preserve the existing lesson assertion and sealed originals.

## Other static bindings

The sealed backend tests bind owner before UUID/history, same-UUID replay before new term/source policy, physical current/history CAS, absent/present legacy rows, delete rollback and no export DML. The applied UI's request shapes and exact review callback match the native owner-scoped client methods. I found no second concrete assertion/body binding error in the inspected paths. This is not a claim that tests pass: collection, import, migrations, SQL concurrency, UI typecheck and native Demo/Auth remain unexecuted in this review.
