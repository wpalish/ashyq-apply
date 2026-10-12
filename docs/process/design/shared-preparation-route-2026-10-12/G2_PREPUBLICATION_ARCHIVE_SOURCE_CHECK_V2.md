# G2 prepublication archive and source check V2

**2026-10-12 · READ ONLY · observed root HEAD `9f1819e4b3db84bf53579cad89e1aa7db15c0cb8` · no source, Git, INDEX, helper, or runtime mutation**

## Exact local qualification

| Scope | Read-only result |
| --- | --- |
| Application source | External `G2_FINAL_APP_SOURCE_PINS.json` SHA-256 `338f130327f29a36e07f563d42165a2066b7b2041b66d4de14895794bebe02cc`: **33/33** current root paths match SHA-256, 0 absent or mismatched; aggregate current size **882,761 bytes**. The pin file specifies hashes, not expected per-file sizes. |
| Archive manifest | Root `docs/process/design/shared-preparation-route-2026-10-12/INDEX.json` SHA-256 `c0467b2ef6758246d48b0935ebea7b83e7d463f838e23175897a783cf737536e`: **844 unique entries**, **844/844** present under that archive root and matching both SHA-256 and byte size. No path escape. |
| Corrected helper | Archived `g2-execution/backend-full/expected-native-source-pins.json`: **66,848 bytes**, SHA-256 `641f198e5bffbdf688c0010be7b11db47c796fe732cc5a4ee8db647dff63a7fb`; working file equals Git HEAD blob byte-for-byte. The 67,552-byte external stage helper is outside this INDEX. |
| Git tracked archive paths | **825** paths at HEAD: **824** INDEX members plus `INDEX.json` itself, which is not self-indexed. All tracked archive paths have no working-tree diff against HEAD. |
| Local-only indexed evidence | **20** INDEX members exist and hash correctly locally but are absent from Git HEAD because existing ignore rules cover `test-results/` (15), `playwright-report/` (3), and `coverage.xml` (2). A fresh clone of HEAD alone will not reconstruct those 20 members. |

The INDEX is an append manifest of the archived local evidence, not a Git portability guarantee. Its `status` text still describes an earlier static/Auth run state. Root plans a separate historical-status update; the content hash and exactness above describe only the observed INDEX bytes. This read-only qualification does not make a deployment, hosted verification, privacy/security gate, or final publication claim. Preserve the local-only evidence or explicitly package it if a portable full archive is required.

## Method and disposition

Read JSON and file bytes; verified every indexed member under the archive root by SHA-256 and size; checked exact Git HEAD tracked paths, archive working-tree diff, and the archived helper blob; separately checked all 33 source pins. Did not import the application, run tests, access network, inspect private runtime data, or modify source/Git/archive.

**Disposition:** current local archive and application-source pins exact. The prior report's single mismatch is retracted in the adjacent correction. The 20 ignored evidence members and historical INDEX status are explicit scope limits, not evidence of a changed archive file.
