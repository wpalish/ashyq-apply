# Draft4: exact Aalto identity and scoped Groningen qualification

AI-prepared source annotations accessed 2026-09-21; **0/10 human verified**.
Frozen draft1/2/3 and capture are unchanged. This adds four known fields (one
previous UNKNOWN resolved, three new fields): **56/215 known/total labels**,
**9/10 programme identities**. No pipeline change or new live canary occurred.

## Source decisions

- [Aalto official programme page](https://www.aalto.fi/fi/koulutustarjonta/tietotekniikka-tekniikan-kandidaatti-ja-diplomi-insinoori)
  identifies Tietotekniikka as the bachelor CS major. Programme existence and
  primary Finnish teaching language are annotated. Some instruction is English
  or Swedish; English at master level is not an English-taught bachelor route.
  The cohort has no English-only filter (Warsaw/Vienna already retain local-language
  routes). Identity scoring does not establish 2027 intake availability. The page's
  2026 application window is not copied into the requested fall 2027 deadline.
  Data Science remains a distinct programme; its fees are not reused.
- [Groningen Kazakhstan requirements](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-entry-requirements/bachelorlinkscountry/kazakhstan?lang=en)
  establishes NIS Grade 12 diploma-level equivalence and a mathematics requirement
  in the FSE Computing Science row. Separate qualification-scoped fields preserve
  the generic country-credential UNKNOWN. Neither field guarantees admission.
  Different-school curricula require individual assessment and course descriptions;
  all applications remain individually assessed, with possible additional conditions.
  Do not transfer mathematics grades or levels from other faculties. Ordinary
  Attestat eligibility and fall 2027 applicability remain unresolved.

Delft's main admission page remained inaccessible; OCW supports programme existence
but does not settle the exact admissions-page identity. UBC's static country selector
returned no Kazakhstan results. No third-party or other-university rules were used.

## Replay

From `backend`:

```sh
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft4.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft4.json --allow-drafts
```

Same capture: programme precision **1/8**, recall and recall@5/10/20 **1/9**;
claim precision **0/5**, recall **0/56**, critical coverage **0/206**. The larger
denominators reflect annotation changes, not a pipeline regression. Operations,
support adjudication and scholarship measurements are unchanged. No percentage
improvement is claimed. Generic unresolved family fields still need inventory review.

Use [the draft4 worksheet](REVIEW_WORKSHEET_DRAFT4.md) for all 56 known fields.
Next: resolve Delft identity, remaining qualification/intake/fee/SAT gaps, exact
award/document aliases and independent evidence adjudication. Obtain ten actual
human signoffs in a new accepted version before strict acceptance and V2-10.
