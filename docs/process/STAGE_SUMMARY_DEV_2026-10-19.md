# Stage summary, development reference (2026-10-19)

The four base3 development sets, aggregated by `evaluation.research.stage_summary` (heldout
pre-registration §9, H-1). This is the comparison reference for the one stage-level look at the
heldout run. The main session runs that look; the worker that built the tool never saw heldout data.

- Captures: the base3 paired runs. All four sets are on pipeline `1093faaa`, with today's defaults in both
  arms. Columns are arm and repetition (`off#1`, `off#2`, `on#1`, `on#2`). Every number is a count summed
  over the set's cases, unless its row says mean or max per case.
- Corpora: cohort `ground_truth.reviewed11`, dev2 `dev2.draft3`, dev3 `dev3.draft3`, dev4 `dev4.draft3`.
- Command, one set at a time:
  `python -m evaluation.research.stage_summary <captures_dir> --dataset <corpus.json> [--out file]`.
- The tool prints aggregates only. Before it prints or writes anything, it checks its own output for any
  case id (as a whole word), university name or case domain from the corpus, and for `http` or `www.`
  anywhere. If it finds one, it exits with status 2 and emits nothing. Refusal reasons become a fixed
  vocabulary (`subject_mismatch`, `reads_as:<page type>`, and so on; anything else is `other`), and award
  names are dropped from claim types (`scholarships.*.exists`). `http_error` is spelt `web_error`.

How to read some rows:

- `search_results_on_official_domain`: result URLs on the case's corpus domain or one of its subdomains.
- `confirmed_pages_*` count pages, and `case_outcome:*` counts cases (the scorer's verdict).
- `gold_returned_by_search` and `gold_read` are cumulative: a case whose gold was read also counts as
  returned if search returned it. `furthest:*` is the scorecard's `gold_seen` stage.
- `*_html_lang` is the page's recorded `<html lang>`. The base3 captures record none, so the rows read
  `unrecorded`. `*_url_hint` is the `?lang=` parameter or a leading language segment of the URL.
- `lead_rejected_sample:*` counts the trace's rejected sample. `leads_rejected_total` is the trace's total.
- Evidence stages come from page types. `requirements` covers admissions, programme detail, intake,
  credential and documents pages. `costs` covers costs pages. `scholarships` covers scholarship index,
  award and FAQ pages. Every other page type is `other`.
- `wrong scope by dimension`: each wrong-scope claim, broken down by the dimensions on which it failed
  `metrics.dimension_matches` against the label's evidence scopes. One claim can fail on several
  dimensions. The development sets have no wrong-scope claim, so the table reads `(none)`.

## cohort

### discovery funnel

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| case_outcome:hit | 5 | 5 | 5 | 5 |
| case_outcome:missed | 3 | 4 | 2 | 3 |
| case_outcome:related | 1 | 1 | 1 | 1 |
| case_outcome:wrong | 1 | 0 | 2 | 1 |
| cases | 10 | 10 | 10 | 10 |
| cases_with_trace | 10 | 10 | 10 | 10 |
| confirmed_pages_hit | 5 | 5 | 5 | 5 |
| confirmed_pages_related | 2 | 2 | 2 | 2 |
| confirmed_pages_wrong | 4 | 3 | 5 | 4 |
| discovery_queries | 36 | 39 | 33 | 36 |
| discovery_queries:admissions | 1 | 1 | 0 | 1 |
| discovery_queries:courses | 3 | 4 | 2 | 3 |
| discovery_queries:field_and_degree | 9 | 9 | 9 | 9 |
| discovery_queries:local_language | 7 | 7 | 7 | 7 |
| discovery_queries:natural_language | 9 | 9 | 9 | 9 |
| discovery_queries:programmes | 4 | 5 | 4 | 4 |
| discovery_queries:undergraduate | 3 | 4 | 2 | 3 |
| identity_recovery_leads_checked | 60 | 71 | 48 | 59 |
| identity_recovery_leads_confirmed | 5 | 4 | 6 | 6 |
| programme_candidates_read | 30 | 31 | 30 | 24 |
| programme_pages_confirmed | 10 | 9 | 11 | 10 |
| reads_in_discovery | 169 | 171 | 158 | 163 |
| search_calls_total | 39 | 39 | 40 | 39 |
| search_results_on_official_domain | 360 | 390 | 330 | 350 |
| search_results_returned | 360 | 390 | 330 | 360 |
| seeds | 36 | 36 | 36 | 36 |
| sitemap_urls_kept | 226 | 226 | 226 | 226 |
| sitemap_urls_seen | 15185 | 15185 | 15185 | 15185 |
| sitemaps_read | 12 | 12 | 12 | 12 |

### gold programme page

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| cases_with_gold | 10 | 10 | 10 | 10 |
| furthest:confirmed | 5 | 5 | 5 | 5 |
| furthest:listed | 1 | 1 | 1 | 1 |
| furthest:never | 0 | 0 | 0 | 0 |
| furthest:read | 0 | 0 | 0 | 0 |
| furthest:rejected | 3 | 3 | 2 | 3 |
| furthest:returned | 1 | 1 | 2 | 1 |
| gold_confirmed | 5 | 5 | 5 | 5 |
| gold_never_seen | 0 | 0 | 0 | 0 |
| gold_read | 5 | 5 | 5 | 5 |
| gold_returned_by_search | 8 | 8 | 8 | 8 |
| returned_by_family:courses | 0 | 1 | 0 | 0 |
| returned_by_family:field_and_degree | 6 | 6 | 6 | 6 |
| returned_by_family:local_language | 4 | 4 | 4 | 4 |
| returned_by_family:natural_language | 2 | 2 | 2 | 2 |
| returned_by_family:programmes | 3 | 4 | 3 | 3 |
| returned_by_family:undergraduate | 2 | 3 | 1 | 2 |

### refusals

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| budget_refused:funding:award | 2 | 7 | 8 | 8 |
| budget_refused:funding:core | 1 | 1 | 1 | 1 |
| budget_refused:verify:question_extra | 2 | 0 | 2 | 0 |
| budget_refused:verify:question_open | 0 | 0 | 2 | 0 |
| lead_rejected_sample:degree_level_other | 40 | 40 | 40 | 40 |
| lead_rejected_sample:front_page | 1 | 0 | 1 | 1 |
| lead_rejected_sample:navigation_lead_no_subject | 27 | 27 | 27 | 14 |
| lead_rejected_sample:off_domain | 1 | 1 | 1 | 1 |
| lead_rejected_sample:reads_as:irrelevant | 0 | 1 | 0 | 0 |
| lead_rejected_sample:reads_as:program_catalog | 1 | 1 | 1 | 1 |
| lead_rejected_sample:reads_as:unknown | 11 | 13 | 10 | 11 |
| lead_rejected_sample:search_lead_unresolved:robots_disallowed | 10 | 13 | 10 | 10 |
| lead_rejected_sample:search_lead_unresolved:web_error | 7 | 6 | 3 | 7 |
| lead_rejected_sample:sitemap_news_not_read | 3 | 3 | 3 | 3 |
| lead_rejected_sample:subject_mismatch | 6 | 6 | 6 | 0 |
| leads_rejected_total | 225 | 229 | 220 | 206 |
| page_outcome:classifier_rejected | 60 | 65 | 60 | 63 |
| page_outcome:fetch_failed | 23 | 29 | 40 | 31 |
| page_outcome:fetched_ok | 66 | 62 | 64 | 63 |
| page_outcome:no_pattern_match | 44 | 45 | 43 | 44 |
| read_refused:front_page | 1 | 0 | 1 | 1 |
| read_refused:reads_as:irrelevant | 0 | 1 | 0 | 0 |
| read_refused:reads_as:program_catalog | 1 | 1 | 1 | 1 |
| read_refused:reads_as:unknown | 11 | 13 | 10 | 11 |
| read_refused:subject_mismatch | 6 | 6 | 6 | 0 |
| read_refused:subject_related_programme | 1 | 1 | 1 | 1 |

### languages

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| confirmed_html_lang:unrecorded | 10 | 9 | 11 | 10 |
| confirmed_url_hint:en | 4 | 4 | 4 | 4 |
| confirmed_url_hint:none | 6 | 5 | 7 | 6 |
| gold_returned_html_lang:unrecorded | 18 | 21 | 17 | 18 |
| gold_returned_url_hint:en | 10 | 10 | 10 | 10 |
| gold_returned_url_hint:none | 7 | 10 | 6 | 7 |
| gold_returned_url_hint:pl | 1 | 1 | 1 | 1 |

### evidence

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| pages:costs | 28 | 29 | 28 | 28 |
| pages:other | 64 | 75 | 83 | 76 |
| pages:requirements | 52 | 50 | 52 | 52 |
| pages:scholarships | 49 | 47 | 44 | 45 |
| pages_fetched_ok:costs | 1 | 2 | 1 | 1 |
| pages_fetched_ok:other | 6 | 6 | 7 | 6 |
| pages_fetched_ok:requirements | 30 | 28 | 31 | 30 |
| pages_fetched_ok:scholarships | 29 | 26 | 25 | 26 |
| reads_by_kind:award | 29 | 39 | 40 | 38 |
| reads_by_kind:core | 51 | 53 | 54 | 52 |
| reads_by_kind:discovery | 97 | 99 | 86 | 91 |
| reads_by_kind:question_extra | 19 | 21 | 20 | 20 |
| reads_by_kind:question_open | 8 | 8 | 6 | 8 |
| reads_by_kind:sitemap | 49 | 49 | 49 | 49 |
| reads_by_kind:walker | 23 | 23 | 23 | 23 |
| reads_by_phase:discovery | 169 | 171 | 158 | 163 |
| reads_by_phase:funding | 45 | 57 | 57 | 55 |
| reads_by_phase:verify | 62 | 64 | 63 | 63 |

### claims

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| by_type:deadline | 8 | 8 | 7 | 8 |
| by_type:english_evidence.duolingo.minimum | 1 | 1 | 1 | 1 |
| by_type:english_evidence.sat.minimum | 6 | 6 | 6 | 6 |
| by_type:english_evidence.toefl_ibt.minimum | 9 | 9 | 9 | 9 |
| by_type:ielts.overall | 10 | 10 | 10 | 10 |
| by_type:ielts.subscores | 7 | 7 | 7 | 7 |
| by_type:intake | 1 | 1 | 1 | 1 |
| by_type:intake.open | 1 | 1 | 0 | 1 |
| by_type:programme.exists | 10 | 9 | 10 | 10 |
| by_type:programme.faculty | 1 | 1 | 1 | 1 |
| by_type:programme.language | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.applicability.application_mode | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.applicability.degree | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.applicability.international | 3 | 3 | 3 | 3 |
| by_type:scholarships.*.applicability.nationality | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.bond | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.coverage.living | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.duration | 2 | 2 | 2 | 2 |
| by_type:scholarships.*.exists | 3 | 3 | 3 | 3 |
| by_type:scholarships.*.renewal | 2 | 2 | 2 | 2 |
| by_type:tuition | 4 | 5 | 4 | 4 |
| by_type:unmapped.credential_evaluation_required | 1 | 1 | 1 | 1 |
| by_type:unmapped.english_test_waiver | 2 | 2 | 2 | 2 |
| by_type:unmapped.entrance_exam_required | 4 | 4 | 4 | 4 |
| by_type:unmapped.gpa_scale | 1 | 1 | 1 | 1 |
| by_type:unmapped.ielts_accepted_types | 10 | 10 | 10 | 10 |
| by_type:unmapped.interview_required | 3 | 3 | 3 | 3 |
| by_type:unmapped.min_gpa | 1 | 1 | 1 | 1 |
| by_type:unmapped.scholarship_application_mode | 2 | 0 | 0 | 0 |
| by_type:unmapped.scholarship_bond | 2 | 0 | 0 | 0 |
| by_type:unmapped.scholarship_coverage | 2 | 2 | 2 | 2 |
| by_type:unmapped.scholarship_duration | 2 | 0 | 0 | 0 |
| by_type:unmapped.scholarship_exists | 12 | 8 | 8 | 9 |
| by_type:unmapped.scholarship_living_allowance | 2 | 0 | 0 | 0 |
| by_type:unmapped.scholarship_program_restriction | 2 | 2 | 3 | 3 |
| by_type:unmapped.scholarship_renewal_requirement | 2 | 0 | 0 | 0 |
| claims | 128 | 114 | 113 | 116 |
| known_labels | 83 | 83 | 83 | 83 |
| matched_to_label | 53 | 52 | 52 | 53 |
| verdict:correct | 45 | 44 | 44 | 45 |
| verdict:other_scope | 4 | 4 | 4 | 4 |
| verdict:partial | 4 | 4 | 4 | 4 |
| verdict:unlabelled | 75 | 62 | 61 | 63 |

### wrong scope by dimension

(none)

### budget and time

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| queries_per_case:max | 6.0 | 6.0 | 5.0 | 6.0 |
| queries_per_case:mean | 3.9 | 3.9 | 4.0 | 3.9 |
| queries_total | 39 | 39 | 40 | 39 |
| reads_per_case:max | 51.0 | 57.0 | 57.0 | 57.0 |
| reads_per_case:mean | 27.6 | 29.2 | 27.8 | 28.1 |
| reads_total | 276 | 292 | 278 | 281 |
| seconds_per_case:max | 110.6 | 110.5 | 110.5 | 110.5 |
| seconds_per_case:mean | 57.3 | 57.6 | 55.7 | 55.2 |

## dev2

### discovery funnel

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| case_outcome:hit | 6 | 7 | 7 | 7 |
| case_outcome:missed | 2 | 2 | 2 | 2 |
| case_outcome:related | 0 | 1 | 0 | 0 |
| case_outcome:wrong | 2 | 0 | 1 | 1 |
| cases | 10 | 10 | 10 | 10 |
| cases_with_trace | 10 | 10 | 10 | 10 |
| confirmed_pages_hit | 6 | 7 | 7 | 7 |
| confirmed_pages_related | 1 | 3 | 1 | 2 |
| confirmed_pages_wrong | 2 | 0 | 1 | 1 |
| discovery_queries | 36 | 36 | 36 | 36 |
| discovery_queries:courses | 2 | 2 | 2 | 2 |
| discovery_queries:field_and_degree | 10 | 10 | 10 | 10 |
| discovery_queries:local_language | 7 | 7 | 7 | 7 |
| discovery_queries:natural_language | 10 | 10 | 10 | 10 |
| discovery_queries:programmes | 5 | 5 | 5 | 5 |
| discovery_queries:undergraduate | 2 | 2 | 2 | 2 |
| identity_recovery_leads_checked | 47 | 49 | 49 | 51 |
| identity_recovery_leads_confirmed | 7 | 7 | 7 | 7 |
| programme_candidates_read | 32 | 44 | 42 | 42 |
| programme_pages_confirmed | 8 | 9 | 8 | 9 |
| reads_in_discovery | 195 | 210 | 212 | 212 |
| search_calls_total | 52 | 51 | 51 | 51 |
| search_results_on_official_domain | 360 | 353 | 350 | 343 |
| search_results_returned | 360 | 353 | 350 | 344 |
| seeds | 0 | 0 | 0 | 0 |
| sitemap_urls_kept | 180 | 288 | 288 | 288 |
| sitemap_urls_seen | 81641 | 84060 | 84060 | 84060 |
| sitemaps_read | 13 | 25 | 25 | 25 |

### gold programme page

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| cases_with_gold | 10 | 10 | 10 | 10 |
| furthest:confirmed | 6 | 7 | 7 | 7 |
| furthest:listed | 0 | 0 | 0 | 0 |
| furthest:never | 1 | 1 | 1 | 1 |
| furthest:read | 0 | 0 | 0 | 0 |
| furthest:rejected | 1 | 1 | 1 | 1 |
| furthest:returned | 2 | 1 | 1 | 1 |
| gold_confirmed | 6 | 7 | 7 | 7 |
| gold_never_seen | 1 | 1 | 1 | 1 |
| gold_read | 7 | 8 | 8 | 8 |
| gold_returned_by_search | 7 | 7 | 7 | 7 |
| returned_by_family:field_and_degree | 5 | 5 | 5 | 5 |
| returned_by_family:local_language | 3 | 3 | 3 | 3 |
| returned_by_family:natural_language | 2 | 2 | 2 | 2 |
| returned_by_family:programmes | 3 | 3 | 2 | 3 |

### refusals

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| lead_rejected_sample:degree_level:master | 1 | 1 | 1 | 1 |
| lead_rejected_sample:degree_level_other | 54 | 60 | 60 | 60 |
| lead_rejected_sample:navigation_lead_no_subject | 40 | 40 | 40 | 40 |
| lead_rejected_sample:reads_as:general_admissions | 1 | 0 | 0 | 0 |
| lead_rejected_sample:reads_as:irrelevant | 2 | 3 | 3 | 2 |
| lead_rejected_sample:reads_as:navigation | 0 | 1 | 1 | 1 |
| lead_rejected_sample:reads_as:program_catalog | 1 | 2 | 2 | 2 |
| lead_rejected_sample:reads_as:unknown | 12 | 22 | 21 | 21 |
| lead_rejected_sample:search_lead_unresolved:robots_disallowed | 1 | 1 | 1 | 1 |
| lead_rejected_sample:search_lead_unresolved:too_large | 2 | 1 | 2 | 3 |
| lead_rejected_sample:search_lead_unresolved:web_error | 1 | 0 | 1 | 1 |
| lead_rejected_sample:sitemap_news_not_read | 3 | 3 | 3 | 3 |
| lead_rejected_sample:subject_mismatch | 4 | 3 | 3 | 3 |
| lead_rejected_sample:subject_related_programme | 1 | 1 | 1 | 1 |
| leads_rejected_total | 430 | 445 | 446 | 446 |
| page_outcome:classifier_rejected | 14 | 17 | 16 | 17 |
| page_outcome:fetch_failed | 3 | 0 | 0 | 0 |
| page_outcome:fetched_ok | 39 | 49 | 43 | 49 |
| page_outcome:no_pattern_match | 22 | 27 | 25 | 27 |
| read_refused:degree_level:master | 1 | 1 | 1 | 1 |
| read_refused:reads_as:general_admissions | 1 | 0 | 0 | 0 |
| read_refused:reads_as:irrelevant | 2 | 3 | 3 | 2 |
| read_refused:reads_as:navigation | 0 | 1 | 1 | 1 |
| read_refused:reads_as:program_catalog | 1 | 2 | 2 | 2 |
| read_refused:reads_as:unknown | 14 | 24 | 23 | 24 |
| read_refused:subject_mismatch | 5 | 5 | 4 | 4 |
| read_refused:subject_related_programme | 1 | 1 | 1 | 1 |

### languages

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| confirmed_html_lang:unrecorded | 8 | 9 | 8 | 9 |
| confirmed_url_hint:en | 4 | 4 | 4 | 4 |
| confirmed_url_hint:none | 4 | 5 | 4 | 5 |
| gold_returned_html_lang:unrecorded | 13 | 13 | 12 | 13 |
| gold_returned_url_hint:de | 1 | 1 | 1 | 1 |
| gold_returned_url_hint:en | 3 | 3 | 3 | 3 |
| gold_returned_url_hint:none | 9 | 9 | 8 | 9 |

### evidence

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| pages:costs | 9 | 11 | 9 | 11 |
| pages:other | 26 | 32 | 30 | 34 |
| pages:requirements | 29 | 34 | 29 | 32 |
| pages:scholarships | 14 | 16 | 16 | 16 |
| pages_fetched_ok:other | 9 | 13 | 11 | 15 |
| pages_fetched_ok:requirements | 19 | 24 | 20 | 22 |
| pages_fetched_ok:scholarships | 11 | 12 | 12 | 12 |
| reads_by_kind:award | 18 | 18 | 20 | 18 |
| reads_by_kind:core | 36 | 41 | 41 | 41 |
| reads_by_kind:discovery | 110 | 109 | 115 | 114 |
| reads_by_kind:question_extra | 5 | 7 | 7 | 7 |
| reads_by_kind:question_open | 3 | 5 | 5 | 5 |
| reads_by_kind:sitemap | 57 | 68 | 68 | 68 |
| reads_by_kind:walker | 28 | 33 | 29 | 30 |
| reads_by_phase:discovery | 195 | 210 | 212 | 212 |
| reads_by_phase:funding | 30 | 32 | 34 | 32 |
| reads_by_phase:verify | 32 | 39 | 39 | 39 |

### claims

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| by_type:deadline | 1 | 2 | 2 | 2 |
| by_type:english_evidence.duolingo.minimum | 1 | 1 | 1 | 1 |
| by_type:english_evidence.toefl_ibt.minimum | 2 | 3 | 3 | 3 |
| by_type:ielts.overall | 2 | 3 | 3 | 3 |
| by_type:ielts.subscores | 2 | 2 | 2 | 2 |
| by_type:intake | 2 | 3 | 2 | 3 |
| by_type:programme.exists | 8 | 9 | 8 | 9 |
| by_type:scholarships.*.applicability.international | 1 | 1 | 1 | 1 |
| by_type:scholarships.*.exists | 1 | 1 | 1 | 1 |
| by_type:tuition | 1 | 1 | 1 | 1 |
| by_type:unmapped.english_test_waiver | 1 | 1 | 1 | 1 |
| by_type:unmapped.ielts_accepted_types | 1 | 2 | 2 | 2 |
| by_type:unmapped.scholarship_exists | 5 | 6 | 6 | 6 |
| by_type:unmapped.scholarship_program_restriction | 5 | 6 | 6 | 6 |
| claims | 33 | 41 | 39 | 41 |
| known_labels | 28 | 28 | 28 | 28 |
| matched_to_label | 11 | 12 | 12 | 12 |
| verdict:correct | 11 | 12 | 12 | 12 |
| verdict:unlabelled | 22 | 29 | 27 | 29 |

### wrong scope by dimension

(none)

### budget and time

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| queries_per_case:max | 6.0 | 6.0 | 6.0 | 6.0 |
| queries_per_case:mean | 5.2 | 5.1 | 5.1 | 5.1 |
| queries_total | 52 | 51 | 51 | 51 |
| reads_per_case:max | 49.0 | 51.0 | 51.0 | 51.0 |
| reads_per_case:mean | 25.7 | 28.1 | 28.5 | 28.3 |
| reads_total | 257 | 281 | 285 | 283 |
| seconds_per_case:max | 105.0 | 91.1 | 93.6 | 92.1 |
| seconds_per_case:mean | 65.8 | 63.2 | 62.0 | 61.1 |

## dev3

### discovery funnel

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| case_outcome:hit | 9 | 9 | 9 | 9 |
| case_outcome:missed | 3 | 5 | 4 | 4 |
| case_outcome:related | 1 | 0 | 1 | 0 |
| case_outcome:unadjudicated | 1 | 1 | 1 | 1 |
| case_outcome:wrong | 1 | 0 | 0 | 1 |
| cases | 15 | 15 | 15 | 15 |
| cases_with_trace | 15 | 15 | 15 | 15 |
| confirmed_pages_hit | 9 | 9 | 9 | 9 |
| confirmed_pages_related | 4 | 3 | 4 | 4 |
| confirmed_pages_wrong | 1 | 0 | 1 | 1 |
| discovery_queries | 54 | 63 | 57 | 60 |
| discovery_queries:admissions | 0 | 1 | 0 | 1 |
| discovery_queries:courses | 3 | 6 | 4 | 5 |
| discovery_queries:field_and_degree | 15 | 15 | 15 | 15 |
| discovery_queries:local_language | 10 | 10 | 10 | 10 |
| discovery_queries:natural_language | 15 | 15 | 15 | 15 |
| discovery_queries:programmes | 8 | 10 | 9 | 9 |
| discovery_queries:undergraduate | 3 | 6 | 4 | 5 |
| identity_recovery_leads_checked | 86 | 114 | 93 | 105 |
| identity_recovery_leads_confirmed | 9 | 7 | 9 | 8 |
| programme_candidates_read | 83 | 79 | 74 | 78 |
| programme_pages_confirmed | 11 | 9 | 11 | 10 |
| reads_in_discovery | 332 | 339 | 326 | 294 |
| search_calls_total | 72 | 71 | 72 | 71 |
| search_results_on_official_domain | 539 | 629 | 569 | 589 |
| search_results_returned | 540 | 630 | 570 | 590 |
| seeds | 0 | 0 | 0 | 0 |
| sitemap_urls_kept | 912 | 912 | 912 | 866 |
| sitemap_urls_seen | 135901 | 135901 | 135901 | 126461 |
| sitemaps_read | 41 | 44 | 44 | 30 |

### gold programme page

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| cases_with_gold | 14 | 14 | 14 | 14 |
| furthest:confirmed | 9 | 9 | 9 | 9 |
| furthest:listed | 0 | 0 | 0 | 0 |
| furthest:never | 2 | 3 | 2 | 2 |
| furthest:no_gold | 1 | 1 | 1 | 1 |
| furthest:read | 0 | 0 | 0 | 0 |
| furthest:rejected | 1 | 1 | 1 | 1 |
| furthest:returned | 2 | 1 | 2 | 2 |
| gold_confirmed | 9 | 9 | 9 | 9 |
| gold_never_seen | 2 | 3 | 2 | 2 |
| gold_read | 9 | 9 | 9 | 9 |
| gold_returned_by_search | 11 | 10 | 11 | 11 |
| returned_by_family:courses | 0 | 0 | 1 | 0 |
| returned_by_family:field_and_degree | 7 | 7 | 6 | 6 |
| returned_by_family:local_language | 5 | 5 | 5 | 5 |
| returned_by_family:natural_language | 2 | 2 | 2 | 2 |
| returned_by_family:programmes | 5 | 5 | 5 | 5 |
| returned_by_family:undergraduate | 0 | 0 | 0 | 1 |

### refusals

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| budget_refused:discovery:sitemap | 0 | 1 | 2 | 4 |
| budget_refused:funding:award | 1 | 0 | 1 | 1 |
| budget_refused:funding:core | 1 | 0 | 1 | 0 |
| budget_refused:verify:core | 1 | 0 | 1 | 0 |
| budget_refused:verify:question_extra | 1 | 1 | 1 | 1 |
| budget_refused:verify:question_open | 1 | 0 | 0 | 0 |
| lead_rejected_sample:campus_abroad | 1 | 0 | 1 | 0 |
| lead_rejected_sample:degree_level:master | 0 | 2 | 1 | 2 |
| lead_rejected_sample:degree_level:phd | 1 | 0 | 1 | 0 |
| lead_rejected_sample:degree_level_other | 156 | 156 | 156 | 156 |
| lead_rejected_sample:navigation_lead_no_subject | 1 | 0 | 0 | 0 |
| lead_rejected_sample:reads_as:general_admissions | 1 | 2 | 1 | 1 |
| lead_rejected_sample:reads_as:irrelevant | 1 | 0 | 0 | 0 |
| lead_rejected_sample:reads_as:navigation | 1 | 1 | 1 | 1 |
| lead_rejected_sample:reads_as:program_catalog | 3 | 3 | 2 | 1 |
| lead_rejected_sample:reads_as:unknown | 27 | 24 | 19 | 25 |
| lead_rejected_sample:search_lead_unresolved:blocked | 0 | 1 | 2 | 0 |
| lead_rejected_sample:search_lead_unresolved:robots_disallowed | 2 | 10 | 10 | 10 |
| lead_rejected_sample:search_lead_unresolved:too_large | 2 | 1 | 1 | 1 |
| lead_rejected_sample:search_lead_unresolved:web_error | 7 | 7 | 7 | 7 |
| lead_rejected_sample:sitemap_news_not_read | 41 | 41 | 41 | 7 |
| lead_rejected_sample:subject_mismatch | 4 | 4 | 3 | 3 |
| lead_rejected_sample:subject_related_programme | 1 | 1 | 1 | 1 |
| leads_rejected_total | 847 | 852 | 844 | 813 |
| page_outcome:classifier_rejected | 41 | 43 | 44 | 45 |
| page_outcome:fetch_failed | 15 | 6 | 12 | 7 |
| page_outcome:fetched_ok | 45 | 42 | 43 | 47 |
| page_outcome:no_pattern_match | 31 | 32 | 33 | 30 |
| page_outcome:unreadable | 1 | 1 | 1 | 1 |
| read_refused:campus_abroad | 1 | 0 | 1 | 0 |
| read_refused:degree_level:master | 0 | 2 | 1 | 2 |
| read_refused:degree_level:phd | 2 | 1 | 2 | 1 |
| read_refused:reads_as:costs | 1 | 1 | 1 | 1 |
| read_refused:reads_as:general_admissions | 2 | 3 | 2 | 2 |
| read_refused:reads_as:irrelevant | 1 | 0 | 0 | 0 |
| read_refused:reads_as:navigation | 1 | 1 | 1 | 1 |
| read_refused:reads_as:program_catalog | 3 | 3 | 3 | 2 |
| read_refused:reads_as:unknown | 34 | 31 | 26 | 33 |
| read_refused:subject_mismatch | 23 | 24 | 22 | 21 |
| read_refused:subject_related_programme | 4 | 4 | 4 | 5 |

### languages

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| confirmed_html_lang:unrecorded | 11 | 9 | 11 | 10 |
| confirmed_url_hint:en | 2 | 2 | 2 | 2 |
| confirmed_url_hint:none | 9 | 7 | 9 | 8 |
| gold_returned_html_lang:unrecorded | 23 | 23 | 23 | 23 |
| gold_returned_url_hint:en | 6 | 7 | 6 | 5 |
| gold_returned_url_hint:none | 16 | 15 | 16 | 17 |
| gold_returned_url_hint:th | 1 | 1 | 1 | 1 |

### evidence

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| pages:costs | 8 | 9 | 8 | 11 |
| pages:other | 54 | 48 | 54 | 51 |
| pages:requirements | 38 | 32 | 37 | 31 |
| pages:scholarships | 33 | 35 | 34 | 37 |
| pages_fetched_ok:other | 6 | 6 | 6 | 8 |
| pages_fetched_ok:requirements | 24 | 19 | 21 | 19 |
| pages_fetched_ok:scholarships | 15 | 17 | 16 | 20 |
| reads_by_kind:award | 27 | 28 | 27 | 34 |
| reads_by_kind:core | 72 | 57 | 56 | 56 |
| reads_by_kind:discovery | 209 | 214 | 200 | 202 |
| reads_by_kind:question_extra | 8 | 8 | 8 | 6 |
| reads_by_kind:question_open | 12 | 15 | 18 | 15 |
| reads_by_kind:sitemap | 108 | 107 | 109 | 89 |
| reads_by_kind:walker | 15 | 18 | 17 | 3 |
| reads_by_phase:discovery | 332 | 339 | 326 | 294 |
| reads_by_phase:funding | 45 | 43 | 42 | 50 |
| reads_by_phase:verify | 74 | 65 | 67 | 61 |

### claims

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| by_type:deadline | 2 | 2 | 2 | 2 |
| by_type:english_evidence.duolingo.minimum | 1 | 1 | 1 | 1 |
| by_type:english_evidence.toefl_ibt.minimum | 2 | 3 | 2 | 3 |
| by_type:ielts.overall | 3 | 4 | 3 | 4 |
| by_type:ielts.subscores | 2 | 3 | 2 | 3 |
| by_type:intake.open | 1 | 1 | 1 | 1 |
| by_type:programme.exists | 11 | 9 | 10 | 10 |
| by_type:programme.language | 1 | 1 | 1 | 1 |
| by_type:sat.minimum | 1 | 1 | 1 | 1 |
| by_type:scholarships.*.applicability.degree | 1 | 1 | 1 | 1 |
| by_type:scholarships.*.applicability.international | 1 | 1 | 1 | 1 |
| by_type:scholarships.*.exists | 1 | 1 | 1 | 1 |
| by_type:tuition | 1 | 1 | 1 | 1 |
| by_type:unmapped.credential_evaluation_required | 1 | 1 | 1 | 1 |
| by_type:unmapped.english_test_waiver | 2 | 2 | 2 | 2 |
| by_type:unmapped.ielts_accepted_types | 4 | 4 | 4 | 4 |
| by_type:unmapped.interview_required | 1 | 1 | 1 | 1 |
| by_type:unmapped.scholarship_exists | 36 | 37 | 36 | 38 |
| by_type:unmapped.scholarship_international_eligible | 1 | 1 | 1 | 1 |
| by_type:unmapped.scholarship_need_based | 1 | 1 | 1 | 1 |
| by_type:unmapped.scholarship_program_restriction | 2 | 2 | 2 | 2 |
| claims | 76 | 78 | 75 | 80 |
| known_labels | 26 | 26 | 26 | 26 |
| matched_to_label | 11 | 13 | 11 | 13 |
| verdict:correct | 11 | 13 | 11 | 13 |
| verdict:unlabelled | 65 | 65 | 64 | 67 |

### wrong scope by dimension

(none)

### budget and time

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| queries_per_case:max | 6.0 | 6.0 | 6.0 | 6.0 |
| queries_per_case:mean | 4.8 | 4.7 | 4.8 | 4.7 |
| queries_total | 72 | 71 | 72 | 71 |
| reads_per_case:max | 54.0 | 54.0 | 56.0 | 56.0 |
| reads_per_case:mean | 30.1 | 29.8 | 29.0 | 27.0 |
| reads_total | 451 | 447 | 435 | 405 |
| seconds_per_case:max | 106.4 | 96.9 | 103.3 | 96.3 |
| seconds_per_case:mean | 65.1 | 60.5 | 62.0 | 57.8 |

## dev4

### discovery funnel

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| case_outcome:hit | 3 | 3 | 4 | 4 |
| case_outcome:missed | 4 | 5 | 3 | 3 |
| case_outcome:related | 2 | 1 | 2 | 2 |
| cases | 9 | 9 | 9 | 9 |
| cases_with_trace | 9 | 9 | 9 | 9 |
| confirmed_pages_hit | 3 | 3 | 4 | 4 |
| confirmed_pages_related | 2 | 1 | 3 | 3 |
| confirmed_pages_wrong | 0 | 0 | 0 | 0 |
| discovery_queries | 36 | 36 | 33 | 33 |
| discovery_queries:courses | 3 | 3 | 2 | 2 |
| discovery_queries:field_and_degree | 9 | 9 | 9 | 9 |
| discovery_queries:local_language | 9 | 9 | 9 | 9 |
| discovery_queries:natural_language | 9 | 9 | 9 | 9 |
| discovery_queries:programmes | 3 | 3 | 2 | 2 |
| discovery_queries:undergraduate | 3 | 3 | 2 | 2 |
| identity_recovery_leads_checked | 58 | 61 | 48 | 50 |
| identity_recovery_leads_confirmed | 5 | 4 | 6 | 6 |
| programme_candidates_read | 41 | 40 | 39 | 41 |
| programme_pages_confirmed | 5 | 4 | 6 | 6 |
| reads_in_discovery | 192 | 186 | 182 | 190 |
| search_calls_total | 43 | 43 | 43 | 43 |
| search_results_on_official_domain | 360 | 360 | 330 | 330 |
| search_results_returned | 360 | 360 | 330 | 330 |
| seeds | 0 | 0 | 0 | 0 |
| sitemap_urls_kept | 138 | 138 | 138 | 138 |
| sitemap_urls_seen | 21426 | 21426 | 21426 | 21426 |
| sitemaps_read | 25 | 25 | 25 | 25 |

### gold programme page

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| cases_with_gold | 5 | 5 | 5 | 5 |
| furthest:confirmed | 3 | 3 | 4 | 4 |
| furthest:listed | 0 | 0 | 0 | 0 |
| furthest:never | 0 | 0 | 0 | 0 |
| furthest:no_gold | 4 | 4 | 4 | 4 |
| furthest:read | 0 | 0 | 0 | 0 |
| furthest:rejected | 0 | 1 | 0 | 0 |
| furthest:returned | 2 | 1 | 1 | 1 |
| gold_confirmed | 3 | 3 | 4 | 4 |
| gold_never_seen | 0 | 0 | 0 | 0 |
| gold_read | 3 | 3 | 4 | 4 |
| gold_returned_by_search | 5 | 5 | 5 | 5 |
| returned_by_family:field_and_degree | 3 | 4 | 4 | 3 |
| returned_by_family:local_language | 5 | 5 | 5 | 5 |
| returned_by_family:natural_language | 3 | 4 | 4 | 4 |

### refusals

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| budget_refused:discovery:sitemap | 1 | 1 | 0 | 0 |
| budget_refused:funding:award | 0 | 0 | 0 | 2 |
| budget_refused:funding:core | 0 | 1 | 0 | 1 |
| lead_rejected_sample:alternate_variant | 3 | 3 | 0 | 0 |
| lead_rejected_sample:degree_level:master | 2 | 1 | 2 | 1 |
| lead_rejected_sample:degree_level_other | 34 | 34 | 34 | 34 |
| lead_rejected_sample:reads_as:costs | 1 | 1 | 1 | 1 |
| lead_rejected_sample:reads_as:navigation | 2 | 4 | 2 | 4 |
| lead_rejected_sample:reads_as:program_catalog | 7 | 6 | 7 | 5 |
| lead_rejected_sample:reads_as:unknown | 15 | 13 | 12 | 13 |
| lead_rejected_sample:search_lead_unresolved:robots_crawl_delay | 1 | 1 | 1 | 1 |
| lead_rejected_sample:search_lead_unresolved:timeout | 0 | 4 | 0 | 0 |
| lead_rejected_sample:sitemap_news_not_read | 28 | 28 | 28 | 28 |
| lead_rejected_sample:subject_mismatch | 3 | 6 | 4 | 6 |
| lead_rejected_sample:subject_related_programme | 0 | 0 | 1 | 1 |
| leads_rejected_total | 99 | 103 | 96 | 98 |
| page_outcome:classifier_rejected | 27 | 26 | 27 | 25 |
| page_outcome:fetch_failed | 5 | 8 | 5 | 7 |
| page_outcome:fetched_ok | 21 | 20 | 25 | 25 |
| page_outcome:no_pattern_match | 14 | 14 | 14 | 14 |
| read_refused:alternate_variant | 3 | 3 | 0 | 0 |
| read_refused:degree_level:master | 2 | 1 | 2 | 1 |
| read_refused:reads_as:costs | 1 | 1 | 1 | 1 |
| read_refused:reads_as:navigation | 2 | 4 | 2 | 4 |
| read_refused:reads_as:program_catalog | 7 | 6 | 7 | 5 |
| read_refused:reads_as:unknown | 18 | 15 | 16 | 17 |
| read_refused:subject_mismatch | 3 | 6 | 4 | 6 |
| read_refused:subject_related_programme | 0 | 0 | 1 | 1 |

### languages

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| confirmed_html_lang:unrecorded | 5 | 4 | 6 | 6 |
| confirmed_url_hint:cs | 0 | 0 | 1 | 1 |
| confirmed_url_hint:en | 1 | 1 | 1 | 1 |
| confirmed_url_hint:none | 4 | 3 | 4 | 4 |
| gold_returned_html_lang:unrecorded | 13 | 15 | 15 | 14 |
| gold_returned_url_hint:cs | 1 | 1 | 1 | 1 |
| gold_returned_url_hint:de | 1 | 1 | 1 | 1 |
| gold_returned_url_hint:en | 1 | 1 | 1 | 1 |
| gold_returned_url_hint:none | 10 | 12 | 12 | 11 |

### evidence

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| pages:costs | 3 | 2 | 4 | 4 |
| pages:other | 39 | 41 | 38 | 38 |
| pages:requirements | 15 | 15 | 18 | 18 |
| pages:scholarships | 10 | 10 | 11 | 11 |
| pages_fetched_ok:other | 2 | 1 | 2 | 2 |
| pages_fetched_ok:requirements | 11 | 11 | 14 | 14 |
| pages_fetched_ok:scholarships | 8 | 8 | 9 | 9 |
| reads_by_kind:award | 34 | 34 | 34 | 35 |
| reads_by_kind:core | 28 | 24 | 32 | 32 |
| reads_by_kind:discovery | 121 | 116 | 112 | 120 |
| reads_by_kind:question_extra | 2 | 2 | 2 | 2 |
| reads_by_kind:question_open | 3 | 4 | 3 | 3 |
| reads_by_kind:sitemap | 60 | 60 | 59 | 59 |
| reads_by_kind:walker | 11 | 10 | 11 | 11 |
| reads_by_phase:discovery | 192 | 186 | 182 | 190 |
| reads_by_phase:funding | 41 | 40 | 44 | 44 |
| reads_by_phase:verify | 26 | 24 | 27 | 28 |

### claims

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| by_type:english_evidence.toefl_ibt.minimum | 3 | 3 | 3 | 3 |
| by_type:ielts.overall | 1 | 1 | 1 | 1 |
| by_type:ielts.subscores | 1 | 1 | 1 | 1 |
| by_type:intake.open | 1 | 1 | 1 | 1 |
| by_type:programme.exists | 4 | 4 | 5 | 5 |
| by_type:unmapped.english_test_waiver | 1 | 1 | 1 | 1 |
| by_type:unmapped.ielts_accepted_types | 1 | 1 | 1 | 1 |
| by_type:unmapped.scholarship_duration | 0 | 0 | 1 | 1 |
| by_type:unmapped.scholarship_exists | 1 | 1 | 2 | 2 |
| by_type:unmapped.scholarship_program_restriction | 0 | 0 | 1 | 1 |
| claims | 13 | 13 | 17 | 17 |
| known_labels | 20 | 20 | 20 | 20 |
| matched_to_label | 8 | 8 | 9 | 9 |
| verdict:correct | 8 | 8 | 9 | 9 |
| verdict:unlabelled | 5 | 5 | 8 | 8 |

### wrong scope by dimension

(none)

### budget and time

| row | off#1 | off#2 | on#1 | on#2 |
|---|---:|---:|---:|---:|
| queries_per_case:max | 5.0 | 5.0 | 5.0 | 5.0 |
| queries_per_case:mean | 4.8 | 4.8 | 4.8 | 4.8 |
| queries_total | 43 | 43 | 43 | 43 |
| reads_per_case:max | 51.0 | 51.0 | 51.0 | 52.0 |
| reads_per_case:mean | 28.8 | 27.8 | 28.1 | 29.1 |
| reads_total | 259 | 250 | 253 | 262 |
| seconds_per_case:max | 108.6 | 104.8 | 108.6 | 108.4 |
| seconds_per_case:mean | 64.5 | 65.3 | 59.7 | 61.0 |
