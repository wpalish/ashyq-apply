"""Native compiler proofs cannot be replaced by authentic numeric quotations."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.document_ir import build_document_ir
from app.research.compiler import COMPILER_VERSION, compile_document, proof_for
from app.research.contracts import PublicScope, QuestionGroup, QuestionState, ResearchQuestion
from app.research.evidence import PublicEvidenceStore, project

NOW = datetime(2026, 10, 10, tzinfo=UTC)
UNTIL = NOW + timedelta(days=14)
URL = "https://example.edu/admissions"
SCOPE = PublicScope(
    university="Example",
    cycle="2027",
    academic_year="2027",
    programme="Computer Science",
    degree="bachelor",
    population="international",
    qualification="attestat",
)


def compile_html(html, scope=SCOPE):
    doc = build_document_ir(html, URL)
    return doc, compile_document(doc, scope, NOW, UNTIL)


def test_real_native_ielts_table_preserves_overall_and_all_band_floor():
    doc, rules = compile_html(
        "<table><tr><th>Test</th><th>Minimum score</th></tr><tr><th>IELTS Academic</th><td>6.5, with no part less than 6.0</td></tr></table>"
    )
    assert {r.question for r in rules} == {"english.overall", "english.bands"}
    overall = next(r for r in rules if r.question == "english.overall")
    bands = next(r for r in rules if r.question == "english.bands")
    assert overall.value == 6.5
    assert bands.value == {"listening": 6.0, "reading": 6.0, "writing": 6.0, "speaking": 6.0}
    assert all(e.row is not None and e.column is not None for e in overall.evidence)
    assert all(r.id.startswith(COMPILER_VERSION + ":") for r in rules)
    assert all(proof_for({URL: doc}, {URL: SCOPE}, NOW, UNTIL)(r) for r in rules)


def test_actual_native_column_bands_are_not_reduced_to_one_number():
    _, rules = compile_html(
        "<table><tr><th>Test</th><th>Overall</th><th>Writing</th><th>Speaking</th></tr><tr><th>IELTS Academic</th><td>6.5</td><td>6.0</td><td>7.0</td></tr></table>"
    )
    assert not any(r.question == "english.bands" for r in rules)
    assert next(r for r in rules if r.question == "english.bands.partial").value == {
        "speaking": 7.0,
        "writing": 6.0,
    }


def test_unsupported_ielts_row_or_mixed_population_never_inherits_scope():
    _, rules = compile_html(
        "<table><tr><th>Test</th><th>Overall</th></tr><tr><th>IELTS Academic domestic students</th><td>6.5</td></tr><tr><th>IELTS Academic international and domestic students</th><td>7.0</td></tr></table>"
    )
    assert rules == []


def test_masters_row_excluded_for_verified_bachelor_page():
    _, rules = compile_html(
        "<table><tr><th>Test</th><th>Overall</th></tr><tr><th>IELTS Academic master's programmes</th><td>6.5</td></tr></table>"
    )
    assert rules == []


def test_compound_row_programme_is_not_silently_overridden_by_page_scope():
    _, rules = compile_html(
        "<table><tr><th>Test</th><th>Overall</th></tr><tr><th>IELTS Academic - Chemistry</th><td>6.5</td></tr></table>"
    )
    assert rules == []


def test_academic_credentials_subjects_grades_and_route_beyond_gpa():
    _, rules = compile_html(
        "<p>Required qualification: Attestat.</p><p>Required subjects: Mathematics, Physics.</p><p>Minimum GPA: 3.2 out of 4.0 is required.</p><p>Admission route: foundation programme.</p>"
    )
    values = {r.question: r.value for r in rules}
    assert values["academic.qualification"] == {"credential": "attestat", "required": True}
    assert values["academic.subjects"] == {"required": ["Mathematics", "Physics"]}
    assert values["academic.grades"] == {"kind": "gpa", "minimum": 3.2, "scale": 4.0}
    assert values["academic.route"] == {"route": "foundation programme"}


def test_explicit_other_credential_and_equivalence_not_assumed():
    _, rules = compile_html(
        "<p>Required qualification: International Baccalaureate Diploma.</p><p>Applicants must hold a qualification equivalent to Attestat.</p><p>Required qualification: NIS Grade 12 Certificate.</p>"
    )
    assert rules == []


def test_explicit_nis_certificate_supported_without_cross_credential_equivalence():
    scope = SCOPE.model_copy(update={"qualification": "NIS"})
    _, rules = compile_html("<p>Required qualification: NIS Grade 12 Certificate.</p>", scope)
    assert rules[0].value == {"credential": "NIS", "required": True}
    assert compile_html("<p>NIS research laboratory: GPA 3.2.</p>", scope)[1] == []


def test_explicit_ib_name_is_credential_not_international_population_marker():
    scope = SCOPE.model_copy(update={"qualification": "IB"})
    _, rules = compile_html(
        "<p>Required qualification: International Baccalaureate Diploma.</p>", scope
    )
    assert rules[0].value == {"credential": "IB", "required": True}


def test_subject_negation_cannot_become_required_subject_name():
    assert compile_html("<p>Required subjects: Mathematics is not required.</p>")[1] == []


def test_deadline_retains_cycle_and_round_without_invented_timezone():
    _, rules = compile_html("<p>Application deadline: 2027-01-15 (regular round).</p>")
    assert rules[0].question == "admission.deadline"
    assert rules[0].value == {
        "date": "2027-01-15",
        "cycle": "2027",
        "round": "regular round",
        "time": None,
        "timezone": None,
    }


@pytest.mark.parametrize(
    "text",
    [
        "Application deadline: 2027-02-30.",
        "Application deadline: January 15.",
        "Application deadline: 2027-01-15 or 2027-02-01.",
    ],
)
def test_invalid_incomplete_or_alternative_deadline_withheld(text):
    assert compile_html(f"<p>{text}</p>")[1] == []


def test_tuition_schema_requires_amount_currency_period_year():
    _, rules = compile_html("<p>Tuition fee: CAD 24,500.50 per academic year for 2027.</p>")
    assert rules[0].question == "tuition.schedule"
    assert rules[0].value == {
        "amount": 24500.5,
        "currency": "CAD",
        "period": "academic year",
        "year": "2027",
        "category": "tuition",
        "mandatory_fees_included": None,
    }


def test_intake_and_fee_academic_year_remain_separate_source_dimensions():
    scope = SCOPE.model_copy(update={"cycle": "Fall 2027", "academic_year": "2027/28"})
    _, rules = compile_html(
        "<h1>Fall 2027</h1><p>Tuition: EUR 12500 per academic year for 2027/28.</p>", scope
    )
    assert rules[0].value["year"] == "2027/28"
    assert rules[0].scope.cycle == "Fall 2027"
    no_year = scope.model_copy(update={"academic_year": None})
    assert (
        compile_html("<p>Tuition: EUR 12500 per academic year for 2027/28.</p>", no_year)[1] == []
    )


@pytest.mark.parametrize(
    "text",
    [
        "Tuition: $24500 per year for 2027.",
        "Tuition: CAD 24500 for 2027.",
        "Tuition: CAD 24500 per year.",
        "Tuition: CAD 24500 per year for 2026.",
        "Tuition: CAD 24,50 per year for 2027.",
        "Tuition: CAD 24500 per year for 2027 plus mandatory fees.",
    ],
)
def test_ambiguous_or_incomplete_fee_schedule_withheld(text):
    assert compile_html(f"<p>{text}</p>")[1] == []


def test_native_normalized_academic_year_matches_source_spelling_without_cycle_inference():
    scope = SCOPE.model_copy(update={"cycle": "Fall 2027", "academic_year": "2027/28"})
    _, rules = compile_html("<p>Tuition: EUR 12500 per academic year for 2027-2028.</p>", scope)
    assert rules[0].value["year"] == "2027-2028"


def test_waiver_exception_preserved_and_requires_independent_local_resolution():
    doc, rules = compile_html(
        "<p>IELTS overall 6.5.</p><p>Except applicants eligible for an English-language waiver.</p>"
    )
    assert len(rules) == 1 and rules[0].exceptions
    question = ResearchQuestion(
        id="english", group=QuestionGroup.ENGLISH, scope=SCOPE, required=("english.overall",)
    )
    kwargs = {"proof": proof_for({URL: doc}, {URL: SCOPE}, NOW, UNTIL)}
    assert project(question, rules, {URL: doc}, {URL}, NOW, **kwargs).state == QuestionState.PENDING
    assert (
        project(
            question, rules, {URL: doc}, {URL}, NOW, condition_applies=lambda _: False, **kwargs
        ).state
        == QuestionState.ANSWERED
    )
    assert (
        project(
            question, rules, {URL: doc}, {URL}, NOW, condition_applies=lambda _: True, **kwargs
        ).state
        == QuestionState.PENDING
    )


def test_negative_exemption_not_silently_lost_outside_numeric_table():
    _, rules = compile_html(
        "<table><tr><th>Test</th><th>Minimum score</th></tr><tr><th>IELTS Academic</th><td>6.5, with no part less than 6.0</td></tr></table><p>IELTS is not required for students with an English-language school qualification.</p>"
    )
    assert rules and all(r.exceptions for r in rules)


@pytest.mark.parametrize(
    "update",
    [
        {"value": 9.5},
        {"question": "academic.grades"},
        {"conditions": ()},
        {"valid_until": UNTIL + timedelta(days=1)},
        {"scope": SCOPE.model_copy(update={"campus": "other"})},
    ],
)
def test_deterministic_proof_rejects_forged_value_key_scope_validity_or_removed_conditions(update):
    doc, rules = compile_html(
        "<p>IELTS overall 6.5.</p><p>If applicants do not qualify for another route.</p>"
    )
    proof = proof_for({URL: doc}, {URL: SCOPE}, NOW, UNTIL)
    assert proof(rules[0])
    assert not proof(rules[0].model_copy(update=update))


def test_proof_requires_verified_source_scope_and_exact_source_binding():
    doc, rules = compile_html("<p>IELTS overall 6.5.</p>")
    assert not proof_for({URL: doc}, {}, NOW, UNTIL)(rules[0])
    assert not proof_for({"https://other.edu/": doc}, {"https://other.edu/": SCOPE}, NOW, UNTIL)(
        rules[0]
    )
    altered = deepcopy(doc)
    altered.title = "Changed source"
    assert not proof_for({URL: altered}, {URL: SCOPE}, NOW, UNTIL)(rules[0])


def test_cache_contains_candidates_not_proof_and_recompiled_scope_still_required(tmp_path):
    doc, rules = compile_html("<p>IELTS overall 6.5.</p>")
    store = PublicEvidenceStore(tmp_path)
    store.save("Example", "2027", rules)
    cached = store.load("Example", "2027", {URL: doc}, {URL}, NOW)
    assert cached == rules
    assert proof_for({URL: doc}, {URL: SCOPE}, NOW, UNTIL)(cached[0])
    assert not proof_for(
        {URL: doc}, {URL: SCOPE.model_copy(update={"campus": "other"})}, NOW, UNTIL
    )(cached[0])


def test_no_invented_waiver_scholarship_or_options_from_absence():
    _, rules = compile_html("<p>IELTS overall 6.5.</p>")
    assert {r.question for r in rules} == {"english.overall"}


def test_invalid_compiler_clock_rejected():
    doc = build_document_ir("<p>IELTS overall 6.5.</p>", URL)
    with pytest.raises(ValueError):
        compile_document(doc, SCOPE, NOW.replace(tzinfo=None), UNTIL)
    with pytest.raises(ValueError):
        compile_document(doc, SCOPE, NOW, NOW)


def test_cache_is_immutable_and_invalidates_source_scope_clocks_and_version(monkeypatch):
    import app.research.compiler as compiler

    doc, first = compile_html("<p>Minimum GPA: 3.2 out of 4.0 is required.</p>")
    first[0].value["minimum"] = 9.9
    assert compile_document(doc, SCOPE, NOW, UNTIL)[0].value["minimum"] == 3.2
    changed = build_document_ir("<p>Minimum GPA: 3.5 out of 4.0 is required.</p>", URL)
    assert compile_document(changed, SCOPE, NOW, UNTIL)[0].value["minimum"] == 3.5
    scope = SCOPE.model_copy(update={"campus": "other"})
    assert compile_document(doc, scope, NOW, UNTIL)[0].scope.campus == "other"
    later = compile_document(doc, SCOPE, NOW, UNTIL + timedelta(days=1))[0]
    assert later.valid_until == UNTIL + timedelta(days=1)
    monkeypatch.setattr(compiler, "COMPILER_VERSION", "native-policy-test-version")
    assert compile_document(doc, SCOPE, NOW, UNTIL)[0].id.startswith("native-policy-test-version:")


def test_cache_entry_count_is_bounded():
    import app.research.compiler as compiler

    for index in range(compiler._MAX_CACHE_ENTRIES + 2):
        compile_html(f"<p>Unsupported paragraph {index}</p>")
    assert len(compiler._COMPILED) <= compiler._MAX_CACHE_ENTRIES
