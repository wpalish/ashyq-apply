# G3 API finite static repair 1

Status: SOURCE_ONLY, NOT_APPLIED, NOT_IMPORTED, NOT_RUN, NOT_ACCEPTED.

Raw first native Ruff failure is retained byte-exact at `inputs/ruff.log`: eight reported errors (one import-order issue, one C416 and six B023 captures). Root authorized only the two manifest paths.

The export validation receives `list(events)` instead of the equivalent item-for-item list comprehension. In the foreign/missing-owner API control lambda, method/case/suffix/body are explicitly captured using defaults. In the history-page control lambda, offset/limit are explicitly captured using defaults. Imports, endpoints, values, test functions, parameters, all assertions and control flow remain unchanged. Inverse replacement was verified byte-exact for both complete files.

The I001 import formatting is intentionally left to root's permitted native formatter. No Ruff/formatter/typecheck/AST/app import/test collection/execution/DB/network or primary/lab/helper/Git/HANDOFF change was performed by the author. This proposal is not a passing static or runtime result. Original sealed API/source/tests packets remain immutable. Root is sole source writer and gate operator.
