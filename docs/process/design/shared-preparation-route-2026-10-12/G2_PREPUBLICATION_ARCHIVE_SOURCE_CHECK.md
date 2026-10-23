# G2 prepublication source and archive-index check

**2026-10-12 · READ ONLY · ONE ARCHIVE MISMATCH · NO SOURCE/INDEX EDIT**

Inspected current root `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials` against external `G2_FINAL_APP_SOURCE_PINS.json` SHA-256 `338f130327f29a36e07f563d42165a2066b7b2041b66d4de14895794bebe02cc` and current root `docs/process/design/shared-preparation-route-2026-10-12/INDEX.json` SHA-256 `c0467b2ef6758246d48b0935ebea7b83e7d463f838e23175897a783cf737536e`. Read source files and external archive bytes only; no imports, tests, runtime, Git, network or mutations.

## Exact result

| Scope | Current read-only result |
| --- | --- |
| Application source pins | **33/33** existing root files match their listed SHA-256 values; no missing file or hash mismatch. The pin file lists SHA only, so no expected per-file size comparison is possible. Current actual aggregate of these 33 files is **882,761 bytes**. |
| Archive index | **844 unique entries**, none missing. **843/844** match both indexed SHA-256 and byte size. Exactly one listed external file differs. |

The sole mismatch is relative to external stage `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12`:

| Entry | Indexed | Current actual |
| --- | --- | --- |
| `g2-execution/backend-full/expected-native-source-pins.json` | SHA-256 `641f198e5bffbdf688c0010be7b11db47c796fe732cc5a4ee8db647dff63a7fb`; **66,848 bytes** | SHA-256 `0c13a397c86d053c84de2efb8438dd7b3060e4d6719c4c872ff8fd1464a87794`; **67,552 bytes** |

The current index's `status` string also describes an earlier point where `static13/Auth4NOT_RUN`. Fresh completed static13 and Auth4 terminal receipts are separate evidence. Treat this 844-entry index as a historical snapshot until root creates and verifies a corrected final archive index/receipt; do not present it as an exact current archive manifest. The mismatch does not change the verified 33 application-source pin hashes or retroactively invalidate completed local test receipts.

**Disposition:** application source pins clear; **archive index exactness open** on the single external entry and status wording. Root remains the sole archive/application writer. This report preserves the observed old index and does not repair it.
