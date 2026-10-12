# G2 root wiring and persistence peer review

Status: **STATIC REVIEW / NOT_RUN / NOT_IMPORTED**. This document reviews the five already applied root wiring files and the external backend proposal. It is not a migration, transaction, endpoint or test result. No application, Git, helper, import, browser or runtime operation was performed.

## Inspected source pins

The following application bytes were observed before the backend proposal seal:

| Applied root file | SHA-256 |
| --- | --- |
| `backend/app/main.py` | `0818c72819acb796fd17318f302406c0a0de31579fc2b9ee0db7984272cd18e9` |
| `backend/app/models/__init__.py` | `2a43f49807f6eb877a100c5f00180fc71cfb696c3b09aaf22a8efbf9b3f7c825` |
| `backend/app/models/applicant.py` | `613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28` |
| `backend/app/api/routes_profile.py` | `9bf31ed16a78383b54cc526ebb77d670a8715616e75cf405aaa5bd6c3fe34b84` |
| `backend/app/api/routes_account.py` | `969bed563403140e81eb6f675f1b1302fc63e6a8e8a19b5f009ff21d3d322a7d` |

Final external source proposal seal: `SEAL.json` SHA-256 `69d294842d5af3da3c5ee394307e061ec8f9a3a28e0ffd4db71880354a6a15da`, status `NOT_APPLIED/NOT_IMPORTED/NOT_RUN`. I compared its five proposed-source hashes against the actual external files: `api/routes_shared_route.py` `e59abe2dd3d51736f9d8a52d3272ba6921ba44e97c7e4a435e5020eaba707635`; `api/preparation_transactions.py` `adaceee999ae5631e5bd72a26fea1e7d0531244102057058a56340204b881336`; `models/shared_route.py` `82297c216c3ff6a2c07588607725be8379bd76587bbe37ec62f676024db9519f`; `schemas/shared_route.py` `9ba24abedbaef90d40fef03097176f9f6de9f803e6c895debf57ce3b5525cb1a`; migration `c3e71d902023_shared_route.py` `04ec483525d574506ad3d4dceb2c589b0ba55efc9351af8ebc5e7e77bf15360f`. All five applied root file hashes above were rechecked after this seal and were unchanged. The seal's optional package-member hash for this independently authored peer report predates this final reconciliation and is not a source-file pin; the backend author was notified to exclude it or issue a new package manifest.

## Finding

### F1 — Export could mix current and future history revisions; closed in amended draft

`export_shared_route_records` in the proposed `routes_shared_route.py:685-694` obtains the current pointer/receipt and then loads all history in separate statements. With PostgreSQL READ COMMITTED, a new save can commit between those reads: the returned `current` remains revision N while `history` includes N+1. SQLite also needs a physical snapshot proof before assuming two ordinary SELECTs are one coherent view. `routes_profile.py:290-293,343-344,406-407` embeds that result into an export described as the complete owned record. Every individual receipt can be valid while the combined export is internally inconsistent.

**Disposition:** the amended proposed helper, SHA-256 `e59abe2dd3d51736f9d8a52d3272ba6921ba44e97c7e4a435e5020eaba707635`, now validates every history receipt and requires absent/present agreement plus `current_receipt.revision == receipts[-1].revision`; otherwise it raises safe 503. This closes the observed mixed-head response in the proposal. An additive concurrent-save export control should force a save between the two reads and assert a coherent response or safe failure. No application import or runtime result is claimed.

## Static checks with no additional defect found

- **Authority and replay:** proposed `save_shared_route:607-641` checks `owned_profile` and current User/membership before the first UUID read, then repeats authority after the fresh parent/legacy wait. Accepted same UUID is returned before new subscription, source, catalogue or legacy gates. Different body with the same UUID gives 409. Exceptions roll back before fresh own UUID reconciliation. An unconfirmed commit does not trigger a new UUID or silent second allocation.
- **Legacy physical fences:** proposed `begin_fresh_preparation_write` reserves SQLite `BEGIN IMMEDIATE`; PostgreSQL uses a strong owned Profile lock followed by the existing StudySchedule child ID lock. An absent legacy insert needs the enforced Profile FK; a present child UPDATE waits on its row lock. The applied case delete takes Organization key share before the Profile lock; account delete takes User, ordered Organizations/memberships and ordered sole-owner Profiles. This is a static coordination argument, not the required two-connection proof.
- **Erase and export integration:** applied `ApplicantProfileRow` has explicit delete-orphan relationships for both G2 tables, so the ORM deletion path covers SQLite connections with FK pragma off. Case deletion adds the audit in the guarded erase transaction. Account deletion rechecks password and sole-owner membership after locks, flushes its audit in the same final erase transaction, and commits erase once. Native `test_account_flows.py:633-655` expects the account audit to survive on SQLite; FK-on organization cascade can remove it, so cross-dialect retention is not promised. The owned export includes typed current/history and counts without copying a dynamic G1 view.
- **Receipt and read visibility:** the proposed current/history reader validates full typed receipt/digests against row columns; the current pointer also requires an exact matching accepted history row and detects an absent current with remaining history. GET/history do not reallocate. Dynamic saved status first checks owned metadata and current research entitlement; a final observed lock clears premium evidence slices. Immutable receipts hold references and planning inputs, not source excerpts, claims or dynamic entitlement state.

## Bounds

This review did not execute migrations, imports, transactions, endpoint calls or tests. Physical PostgreSQL and SQLite lock behavior, commit failure, FK-off cascade and native Demo/Auth flows remain for the root's gated run. The final sealed backend source hashes were compared; F1 is closed in sealed **proposal source only**, with no application or runtime qualification.
