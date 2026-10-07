# Remaining-only controller v4

Preserve all v2 execution files and rejected never-executed v3 plan/source/red tests. V3 peer controls found that a physical page_budget_exhausted envelope with error=null could still pass as an ordinary result. V4 adds required exact page_capped consistency whenever stop_reason is page_budget_exhausted. A nonfatal search budget remains separately allowed. No app/source/limits/provider changes; only previously unstarted HKU/NTU/KAIST may run after fresh offline peer review.
