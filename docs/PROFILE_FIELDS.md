# What each profile field actually does

An external audit found roughly twenty fields the form collected, validated,
stored and exported — and that nothing ever read. That is worse than not
asking: an applicant who answers a question reasonably assumes the answer
changed the result.

Every field is now in exactly one of three states, and this table is the
record. A field with no honest use was removed from the form rather than left
in place to imply a tailoring that never happened.

- **Scored** — it changes a number in the preference score.
- **Context** — it appears in an explanation or raises a question for the
  admissions office, and is deliberately never scored, because scoring it
  would mean inventing a judgement no source supports.
- **Removed** — the form no longer asks. The field remains in the schema
  (`extra="forbid"` means profiles saved earlier would fail to load without
  it) and is written by nothing.

## Preferences

| Field | State | What it does | Test |
|---|---|---|---|
| `preferred_countries`, `excluded_countries` | Scored | Country preference component | `test_an_excluded_country_scores_zero_on_country_preference` |
| `city_size` | Scored | City fit, graded against the registry's `city_size` | `test_every_component_names_its_weight_and_its_reason` |
| `climate` | Scored | Climate fit | as above |
| `acceptable_workload` | Scored | Workload fit | as above |
| `university_size` | Scored | University size component, graded against the registry's `size` on a small/medium/large ladder | `test_university_size_moves_the_score` |
| `campus_type` | Scored | Campus type component. Campus has no ordering, so it matches or it does not — a known mismatch grades as *weak*, never as the *acceptable* that means "no preference stated" | `test_a_campus_mismatch_is_not_dressed_up_as_acceptable` |
| `target_ranking_band` | Scored | Programme standing component | `test_every_component_names_its_weight_and_its_reason` |
| `values_internships` | Scored | Weights the careers component | existing scoring tests |
| `values_coop` | Context | Raises "does this programme offer a co-op or placement year?" when the careers text does not say | `test_the_run_raises_the_questions_the_pages_do_not_answer` |
| `needs_work_during_study` | Context | Raises the work-hours question when no official statement was found | as above |
| `research_interests` | Context | Raises "which groups work on X?" per interest the pages never mention | as above |
| `safety_priority` | **Removed** | No official page this product reads publishes a comparable safety figure. Scoring it would have been a number with nothing behind it | — |
| `diversity_priority` | **Removed** | Same: no comparable published figure | — |
| `housing_guarantee_priority` | **Removed** | Housing guarantees are published inconsistently and were never read | — |

## Academics

| Field | State | What it does | Test |
|---|---|---|---|
| `gpa`, `ielts`, `toefl`, `sat`, subject grades | Scored | Eligibility checks against published minimums | `test_eligibility.py` |
| `class_rank`, `class_size` | Context | Stated in the academic-fit explanation for a human to weigh; never scored, because no university in the registry publishes a rank threshold | `test_class_rank_is_stated_in_the_explanation_without_becoming_a_score` |
| `second_citizenship` | Scored | Checked against scholarship citizenship restrictions alongside the primary one | `test_a_second_citizenship_counts` |

## Funding

| Field | State | What it does | Test |
|---|---|---|---|
| `max_annual_budget`, `max_acceptable_gap` | Scored | Affordability, converted into the cost's currency | `test_a_tenge_ceiling_is_converted_before_it_is_compared` |
| `budget_currency` | Scored | The currency both sides of that comparison are put into | as above |
| `max_family_contribution` | Context | Stated in the affordability explanation | `test_max_family_contribution_appears_in_the_affordability_explanation` |
| `funding_criticality` | Scored | Scales the weight of the funding and affordability components (nice_to_have 0.5, important 0.75, decisive 1.0) | `test_funding_criticality_changes_the_weight_of_funding` |
| `requires_full_ride` | Scored | An award that is not a full ride stops counting as this programme's funding, and says why on its own row | `test_requires_full_ride_marks_an_award_that_is_not_one` |
| `accepts_full_tuition` | Scored | Same, for tuition-only awards | `award_meets_shape` tests |
| `accepts_partial` | Scored | Same, for partial awards | `test_refusing_partial_awards_is_honoured` |
| `willing_to_submit_need_documents` | Scored | A need-based award is not counted for an applicant who will not submit financial documents | `test_refusing_to_submit_documents_makes_a_need_based_award_unusable` |
| `must_cover_housing` / `_meals` / `_health_insurance` / `_books` / `_travel` | Context | An award that explicitly excludes a required category says so in its reason and raises an open question. Silence on the page is unknown, never a refusal | `test_a_must_cover_category_that_an_award_excludes_raises_a_question` |

## Two limits worth knowing

**The registry's vocabulary is narrower than the form's.** Every bundled and
live institution is `size` medium or large, and `campus` urban or campus. So a
preference for a *small* university can never score *strong* — the best
available is *good* against a medium — and *suburban* can only ever be a
mismatch. That is a gap in the data, not in the scoring: it closes when the
registry grows, and until then the component is honest about what it found.

**Missing attributes cost a little.** A registry entry with no `size` or
`campus` scores as missing data, which charges the standard 0.03 penalty per
absent field (capped at 0.25 across the whole profile). Every entry shipped
today fills both, so this only bites when a new institution is added with the
fields left blank — worth watching as the registry grows.

## The rule this table encodes

A preference may change a score only when the registry or an official page
publishes something comparable. Where it does not, the honest options are a
question or no question at all — never a number. That is the same rule the
rest of the product follows for tuition, deadlines and eligibility.
