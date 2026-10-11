# Display correction — finite independent static review

**QUALIFIED_STATIC_ACCEPT_PENDING_ROOT_GATES.** The seven requested display replacements are contained in six unified diff hunks. No runtime, additional test, browser, provider or Git operation was performed. Root-owned source and sealed packets were not edited by this reviewer.

## Exact scope and result

- Display preimage `c7d8b69069f057f217fefc2977beef3cd73580dd47eba46d05ca995f5e869072` is byte-identical to the sealed UI proposal. Postimage `bc84b35a426d654bdb541cfcd303d7165cc5bc0bb8d667668ddc73fde28c1e3a` is byte-identical to current root source.
- The supplied patch reconstructs the postimage exactly in memory. The remaining component bytes are unchanged.
- Friendly access text covers the three current documented reasons, retains the actual `allowed`/development distinction and subscription end date, and does not expand entitlement.
- Saved markers and ordinary lesson/history labels omit machine IDs/version strings. Exact versions remain on learning-path rows, Start buttons, practice-unit attributes and history rows. Saved review retains its exact immutable lesson/version in the optional **Material details** disclosure.
- Archived metadata is explicitly labelled **Archived lesson**. Missing question text and stored ID/feedback fallback remain honest; current content is never substituted for retired material.
- Requests, owner/case/intent fences, UUID retry, receipt matching, incorrect-first ordering and server grading are unchanged. `PracticeSession` is byte-identical after reversing its single display line; `AttemptFeedback` is fully byte-identical.

## Concrete first finding and closure

The first read found the frozen learning-path assertion at line 355 still expecting `learningVersion` in the **Saved submission** Chip text. That contradicted the new human label; it was a static incompatibility, not an executed test failure. Original test bytes remain preserved in the sealed proposal (`9c3e215c440f2d01d09da9ebc6d91802e0dc666cd4a7353d978e0d8e203837a5`).

Root corrected exactly one assertion:

```tsx
expect(marker.closest('li')).toHaveAttribute('data-version', learningVersion);
```

The title/marker and surrounding API/accepted-history checks remain unchanged. The current test (`9eed8f46dd1959cf4a446b1c6532c71b04c978454ec015c287fc047b0b5bd5ed`) equals the sealed original after precisely this replacement; no other test bytes changed.

## Native compatibility and qualification

Existing Preparation mode headings, original starter heading, three legacy Start labels, Submit/Retry/Next labels, review region/attempt attributes and raw feedback labels are unchanged. Native Demo/Auth expectations consume API versions and data attributes rather than the removed ordinary version copy. The exact current native inputs are pinned in the seal; their runtime assertions were not executed by this reviewer.

Optional Material details keeps historical version text available. A JSDOM text-content assertion against that text does not prove its browser visibility before opening the disclosure. This review confirms the static display delta and single test-contract alignment only. The sealed proposal's earlier 68 selected PASS do not transfer to these changed bytes; fresh whole frontend and native gates remain root's responsibility. No full-course, official-score, admission, search-quality, publication or deployment conclusion follows.
