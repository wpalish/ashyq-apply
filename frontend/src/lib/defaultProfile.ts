/**
 * The starting profile shown in the form.
 *
 * Synthetic throughout — this is a demo seed, not a real applicant. It is
 * chosen to land on the interesting boundaries so the product's refusals are
 * visible immediately: an IELTS writing band below several per-section
 * minimums, a GPA on a scale nobody publishes against, and a budget far below
 * every unfunded cost of attendance.
 */

export const DEFAULT_PROFILE = {
  display_name: 'Demo Applicant (synthetic)',
  context: {
    level: 'bachelor',
    intended_fields: ['computer science'],
    intake_term: 'fall',
    intake_year: 2027,
    citizenship: 'Kazakhstan',
    country_of_residence: 'Kazakhstan',
    education_country: 'Kazakhstan',
    education_system: 'Kazakhstan national secondary (attestat)',
    curriculum_type: 'national',
    graduation_date: '2027-05-25',
    second_citizenship: null,
  },
  academics: {
    gpa: {
      raw_value: 4.8,
      raw_scale_max: 5.0,
      raw_scale_label: 'KZ 5-point',
      converted_value: null,
      converted_scale_label: null,
      method: null,
      method_source: null,
      status: 'applicant_confirmed',
    },
    subject_grades: [],
    class_rank: 3,
    class_size: 112,
    sat: {
      total: 1400, math: 760, reading_writing: 640,
      dates: { taken_on: '2026-05-02', planned_retake_on: '2026-10-03' },
      status: 'applicant_confirmed',
    },
    act: { composite: null, english: null, math: null, reading: null, science: null,
           dates: { taken_on: null, planned_retake_on: null }, status: 'applicant_confirmed' },
    ielts: {
      overall: 7.0, listening: 7.5, reading: 7.5, writing: 6.0, speaking: 7.0,
      test_type: 'academic',
      dates: { taken_on: '2026-04-18', planned_retake_on: null },
      status: 'applicant_confirmed',
    },
    toefl: { total: null, reading: null, listening: null, speaking: null, writing: null,
             dates: { taken_on: null, planned_retake_on: null }, status: 'applicant_confirmed' },
    duolingo: null,
    other_tests: [],
    curriculum_results: [],
    planned_retakes: ['SAT on 2026-10-03 targeting 1500'],
  },
  activities: [
    {
      name: 'Regional Informatics Olympiad team',
      category: 'academic', role: 'team captain',
      duration_months: 24, hours_per_week: 8, weeks_per_year: 36,
      responsibility_level: 'leader',
      measurable_outcome: 'Led a four-person team to 2nd place at the national round in 2026.',
      impact_on_others: 'Ran weekly training for 15 younger students.',
      evidence_links: [],
    },
    {
      name: 'Volunteer coding club',
      category: 'community', role: 'founder and instructor',
      duration_months: 18, hours_per_week: 4, weeks_per_year: 40,
      responsibility_level: 'founder',
      measurable_outcome: 'Taught Python to 60 students across three cohorts.',
      impact_on_others: 'Six participants entered regional competitions.',
      evidence_links: [],
    },
  ],
  achievements: [
    { name: 'National Informatics Olympiad', level: 'national', year: 2026,
      placement: '2nd place (team)',
      selection_criterion: 'Top 40 of 900 regional qualifiers.', evidence_links: [] },
    { name: 'City science fair', level: 'city', year: 2024, placement: '1st place',
      selection_criterion: null, evidence_links: [] },
  ],
  preferences: {
    preferred_countries: ['Netherlands', 'Germany', 'Canada', 'Finland', 'Belgium'],
    excluded_countries: [],
    city_size: 'medium', climate: 'temperate', university_size: 'large',
    campus_type: 'campus', acceptable_workload: 'demanding', target_ranking_band: 'top_300',
    research_interests: ['machine learning'],
    values_internships: true, values_coop: false,
    needs_work_during_study: true, needs_post_study_work: true,
    safety_priority: 'high', diversity_priority: 'medium', housing_guarantee_priority: 'high',
  },
  funding: {
    requires_full_ride: false, accepts_full_tuition: true, accepts_partial: true,
    max_annual_budget: 6000, max_family_contribution: 5000, max_acceptable_gap: 6000,
    budget_currency: 'USD', willing_to_submit_need_documents: true,
    must_cover_housing: true, must_cover_meals: true, must_cover_health_insurance: false,
    must_cover_books: false, must_cover_travel: false, funding_criticality: 'decisive',
  },
  weights: {
    academic_fit: 1.0, funding_fit: 1.5, extracurricular_alignment: 0.6, program_quality: 0.8,
    country_preference: 1.0, city_fit: 0.4, climate_fit: 0.3, workload_fit: 0.3,
    career_outcomes: 0.7, post_study_work: 0.5,
  },
} as const;
