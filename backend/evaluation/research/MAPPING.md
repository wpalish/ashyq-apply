# Offline award and document identity mapping

`map_claims.py` consumes the saved canary `.raw.json` claim array. It never reads
expected labels or imports the production app. `identity_bindings.draft1.json`
is an AI-prepared, deliberately small source/name registry, not human verification.
It contains identifiers only: no expected amounts, eligibility or evidence verdicts.

Matching requires the exact subject and source URL. Host case, trailing slash and
fragment normalize; path case and query parameters remain significant. There is
no fuzzy name match or university-wide alias. Duplicate source/subject bindings
fail validation. Different explicit aliases may point to one identity only after
review; an index/FAQ must not be made an alias for a named award.

From `backend`, inspect predictions without changing a capture:

```sh
python -m evaluation.research.map_claims --raw ../artifacts/<run>/ntu.raw.json --bindings evaluation/research/data/identity_bindings.draft1.json --university "<observed canary institution>" --out ../artifacts/ntu-mapping.json
```

For a separately saved, directly scoreable replay, also supply
`--capture evaluation/research/baseline/capture.json --case-id ntu` and choose a
new output path. The raw canary institution must match the supplied name and any
existing evidence scope for that case. Only that observation's predictions change.
Other cases, errors, operation counters, pipeline SHA and capture time are retained.
Support/currentness/conflict verdicts on the replaced predictions return to
unadjudicated; previous human verdicts are not transferred to newly mapped facts.
Replay metadata records raw/binding/mapper/parent hashes and mapping counts. The
mapper refuses to overwrite an input. Hashes identify inputs; they do not certify
their correctness. Do not publish full quotations from private raw artifacts.

## Value and scope limits

- Award existence becomes a boolean only after consistent exact identity binding.
  It does not establish international, programme or intake applicability.
- Coverage tables split into category fields. `mandatory_fees` becomes `fees`,
  `health_insurance` becomes `insurance`. `personal` remains `personal`, not all
  living expenses. Values stay `yes/no/partial`; explicit `unknown` becomes null
  so it cannot count as answered coverage. No amount or full-ride
  coverage is inferred. Unknown categories or malformed values preserve the entire
  claim as unmapped instead of silently dropping fields.
- Other award values remain unchanged: a citizenship restriction list, degree
  verdict, application mode or renewal sentence is not silently rewritten into a
  more specific expected answer. Exact scoring may reject these different shapes.
- Documents require a source/name binding that explicitly includes admission,
  programme or scholarship purpose. Required-document claims emit `.required`;
  a valid essay word limit emits `.maximum_words`. Referee role, translation,
  notarisation and other conditions are not fabricated from document identity.
- Original programme/intake/year and evidence access date are preserved. No scope
  comes from the registry. Production `verified` status/confidence never sets
  human support/currentness/conflict adjudication. Quotes at the production
  600-character cap are conservatively marked truncated.

The frozen draft1/draft2 labels contain some compound document values, while this
mapper emits atomic document fields. [Draft3](REVIEW_DRAFT3.md) aligns explicit
document requirements and word limits without discarding conditional alternatives.
It is not human reviewed; the applicable field inventory still needs acceptance.
Do not overwrite old artifacts or add expected conditions to outputs
to make scores improve. Unmapped and unmatched predictions remain visible through
the mapping report and scorer's adjudication rate.

## Observed baseline limitation

The saved NTU sidecar contains ten raw claims, including six scholarship claims
about `FAQs on scholarships` and `Tuition Grants`, not the named Nanyang Global
award. These names are deliberately not registered as aliases for that award.
There is no new retrieval-quality claim and no replacement of the frozen baseline.
Real document mapping is also not measured by the current discovery canary:
production document collection occurs after shortlist approval.

Next: independently review the registry, align a new version's atomic labels,
then score separately saved replays with full evidence adjudication. V2-01 still
requires ten actual human-reviewed cases before acceptance.
