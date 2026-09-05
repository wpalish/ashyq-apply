# ADR 0003 — A non-compensatory ranking, with coverage kept separate

**Status:** accepted
**Date:** 2026-09-05

## Context

The v1 shortlist score was a weighted sum of thirteen components, divided by
their maximum and then multiplied by a penalty for missing data. On the demo
profile — a family with a stated 6,000 USD ceiling who called funding
`decisive` — the list opened with the University of British Columbia and its
21,471 USD annual shortfall.

Nothing was broken. A sum did exactly what a sum does: Affordability scored 0,
and Funding 1.5, Academic 1.0 and Country 1.0 paid for it. Every axis in an
additive model is for sale, and the axes the applicant cares most about are
the ones with the most buyers.

Three further defects came out of the same audit:

* Climate, city, size, campus and workload together carried about 1.7 % of the
  scale, so changing a preference moved almost nothing. The preference screen
  was, in effect, decoration.
* The missing-data penalty (`total × (1 − 0.03·n)`) punished universities whose
  websites parse badly rather than universities that fit badly.
* Preference labels were computed during verification and frozen onto the row,
  so changing a preference meant crawling twenty universities again.

## Decision

**1. A weighted geometric mean over the axes we know.**

```
fit = exp( Σ w_i · ln(max(u_i, ε)) / Σ w_i ),  ε = 0.02
```

A near-zero axis pulls the whole product down and no amount of excellence
elsewhere buys it back. `ε` is a floor for the logarithm, not a softener: an
axis at 0.02 is a near-veto that still yields a finite number, whereas `ln 0`
would make every hopeless row equally and uselessly bad.

**2. Missing data is a second metric, not a penalty.**

```
coverage = Σ w known / Σ w (known ∪ unknown)
sort_key = fit · coverage^γ,  γ = 0.5
```

An unverified axis leaves the fit entirely and lowers coverage instead. A
verified answer still outranks a guessy one — that is what `γ` is for — but a
thin website no longer reads as a worse university. `NOT_APPLICABLE` (the
applicant said "any") enters neither: no preference is not a missing answer.

γ = 0.5 costs a half-verified row about 29 % of its fit. The value is a config
knob (`UNIMATCH_RANKING_GAMMA`) precisely because it is a judgement call, and
it is revisited after the first demos.

**3. Weights come from an ordering, not from sliders.**

Six groups, ranked; rank-order centroid turns the positions into weights
(0.408, 0.242, 0.158, 0.103, 0.061, 0.028 for six). Nobody moved the twelve
0–3 sliders, and asking someone to invent a number for "how much does climate
matter, out of three" was never going to produce one. The sliders survive in an
advanced mode behind `weights_override`.

**4. Buckets, and a balanced shortlist.**

`WELL_PLACED` · `PLAUSIBLE` · `AMBITIOUS` · `OUT_OF_BUDGET` ·
`NEEDS_CLARIFICATION` · `EXCLUDED`, with quotas (10 rows, ≥2 well placed, ≥4
plausible, ≤3 ambitious, ≤3 per country). A top ten of ten ambitious options
is a list nobody can act on. The names are deliberately not "safety / match /
reach": *safety* reads as a promise, and this product does not make one.

## Consequences

* On the demo profile the list now opens with Groningen, and UBC sits in
  `OUT_OF_BUDGET` — the same evidence, ordered by what the family said matters.
* Preference labels are derived from stored `catalog_attributes` on every
  assessment, so `POST /api/runs/{id}/rerank` re-orders a finished run without
  a single fetch.
* Fit is a mean, so dropping a known axis moves it. The invariant that holds is
  the one that matters: an axis we could not verify is never *scored against*
  the row, and it can only lower coverage. A test pins exactly that, rather
  than an equality the arithmetic cannot give.
* Extracurricular alignment leaves the university ranking entirely. It scored
  the applicant, so it was identical on every row and separated nothing; it
  still moves `STRONGER_FIT` vs `PLAUSIBLE_FIT`, and through that the bucket.
* v1 stays in the code behind `UNIMATCH_RANKING_VERSION=1`, byte for byte, so
  the change can be rolled back without a migration. It goes two releases after
  this one, by a separate decision.

## Alternatives considered

**Keep the sum, raise the preference weights.** Does not fix compensation: it
only changes the price of buying an axis back.

**Hard-filter on affordability.** Rejected. A shortfall is a fact about a
budget, not a published requirement the applicant fails, and the family may
have plans we do not know about. `OUT_OF_BUDGET` lists the row with its number
instead of hiding it.

**Impute unknown axes at the mean, so an unknown provably cannot move fit.**
Rejected: an imputed value is a guess wearing a number's clothes, which is the
one thing this product does not do. Coverage says "we do not know" out loud.
