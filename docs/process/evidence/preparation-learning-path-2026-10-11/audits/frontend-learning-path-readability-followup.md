# UI review follow-up — technical literals

Supplement to [sealed static review](frontend-backend-contract-review.md), without changing that receipt or the frozen UI packet. Manifest remains `a38c543e38976434476950dfdcdbab8fe219898d6d0633204cb98d9d0434739c`.

**Classification: bounded readability issue; no confirmed contract/privacy/lifecycle blocker.** Production readability acceptance should include a small display-only correction. No source or proposal edits were made by reviewer.

`PreparationScreen.tsx` currently exposes technical identifiers during normal use:

- `:290` saved marker, `:314` history row and `:388` unit label show raw version strings.
- `:323` review heading paragraph shows lesson ID and raw version even when exact lesson metadata exists.
- `:60` displays the machine access reason with underscores replaced, which is not necessarily a useful human explanation.

For normal labels use lesson title plus a friendly content revision/date when distinguishing content actually helps the learner. Keep exact ID/version in requests, immutable receipts, guards and data attributes; optional content details may expose exact version to explain historical content identity. The missing-metadata fallback at `:325,:430` must remain explicit: a stored question/choice ID is honest when text is unavailable, and should never be replaced with current-version material. A friendly entitlement reason must preserve actual allowed/expired/pending/exhausted semantics and end date.

The current UI types and API compatibility are sound. This display concern does not invalidate the pinned ownership/version/UUID/table static findings. Any follow-up bytes need their own display diff, source pins and consumed static/native controls; no changed packet/runtime PASS is inferred here.
