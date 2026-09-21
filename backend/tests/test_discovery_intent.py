"""V2-11 — what discovery is allowed to tell a search engine.

The phase guide lists what must never appear in a query: applicant name,
exact scores, exact GPA, budget, family contribution, email, phone,
transcript content. There is one test per item, each feeding a fully
populated profile through the sanctioned conversion and asserting the
rendered queries contain none of it.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.adapters.search.intent import (
    ALLOWED_POPULATION_MARKERS,
    DEFAULT_QUERY_BUDGET,
    DiscoveryIntent,
    QueryPrivacyError,
    queries_for,
    redacted_audit_record,
)
from app.domain.enums import DegreeLevel

NU = {"institution": "Nazarbayev University", "domain": "nu.edu.kz"}


def an_intent(**kw) -> DiscoveryIntent:
    return DiscoveryIntent(
        **{**NU, "degree": DegreeLevel.BACHELOR, "field": "computer science", **kw}
    )


def rendered(intent: DiscoveryIntent) -> str:
    """Every query this intent would produce, as one searchable blob."""
    return " ".join(q.text for q in queries_for(intent, budget=99)).lower()


class TestNoApplicantDataSurvivesTheConversion:
    """One test per forbidden item in the phase guide's list."""

    def test_the_applicant_name_does_not_reach_a_query(self, profile):
        intent = DiscoveryIntent.from_profile(profile, **NU)

        assert "test applicant" not in rendered(intent)
        assert profile.display_name.lower() not in rendered(intent)

    def test_exact_test_scores_do_not_reach_a_query(self, profile):
        text = rendered(DiscoveryIntent.from_profile(profile, **NU))

        assert "1400" not in text  # SAT total
        assert "760" not in text  # SAT maths
        assert "7.0" not in text and "6.0" not in text  # IELTS overall and writing

    def test_the_exact_gpa_does_not_reach_a_query(self, profile):
        text = rendered(DiscoveryIntent.from_profile(profile, **NU))

        assert "4.8" not in text
        assert "5-point" not in text

    def test_the_budget_and_family_contribution_do_not_reach_a_query(self, profile):
        text = rendered(DiscoveryIntent.from_profile(profile, **NU))

        assert "6000" not in text

    def test_contact_details_cannot_be_put_in_an_intent(self):
        with pytest.raises(QueryPrivacyError, match="email"):
            an_intent(field="cs applicant@example.com")

    def test_a_phone_number_cannot_be_put_in_an_intent(self):
        with pytest.raises(QueryPrivacyError, match="long number"):
            an_intent(institution="Nazarbayev University 87071234455")

    def test_transcript_content_cannot_be_smuggled_through_an_allowed_field(self):
        """The signature stops a profile object; this stops a formatted string."""
        with pytest.raises(QueryPrivacyError, match="grade"):
            an_intent(field="computer science gpa 4.8")

    def test_a_currency_amount_is_refused_wherever_it_appears(self):
        for value in ("computer science under $20000", "computer science 15000 KZT"):
            with pytest.raises(QueryPrivacyError):
                an_intent(field=value)

    def test_citizenship_is_not_forwarded_even_though_the_profile_has_it(self, profile):
        """A country in a query must describe a page's audience, not this person."""
        assert profile.context.citizenship == "Kazakhstan"

        intent = DiscoveryIntent.from_profile(profile, **NU)

        assert intent.population_marker == ""
        assert "kazakhstan" not in rendered(intent)

    def test_the_whole_profile_leaves_only_three_values_behind(self, profile):
        """Whatever else the profile grows, the conversion keeps reading three fields."""
        intent = DiscoveryIntent.from_profile(profile, **NU, include_intake=True)

        assert intent.degree == DegreeLevel.BACHELOR
        assert intent.field == "computer science"
        assert intent.intake_year == 2027
        assert set(DiscoveryIntent.__dataclass_fields__) == {
            "institution",
            "domain",
            "degree",
            "field",
            "intake_year",
            "population_marker",
        }


class TestTheCountryMarkerIsNarrow:
    def test_an_allowed_marker_produces_a_requirements_query(self):
        intent = an_intent(population_marker="Kazakhstan")

        families = {q.family for q in queries_for(intent, budget=99)}

        assert "country_requirements" in families

    def test_a_marker_that_describes_a_person_rather_than_a_page_is_refused(self):
        """No digits in this value, so it can only fail on the allowlist itself."""
        with pytest.raises(QueryPrivacyError, match="is not one of"):
            an_intent(population_marker="Kazakhstani applicants from Almaty")

    def test_the_allowed_set_is_short_and_explicit(self):
        assert set(ALLOWED_POPULATION_MARKERS) == {"international", "Kazakhstan"}

    def test_no_marker_means_no_country_or_scholarship_query(self):
        families = {q.family for q in queries_for(an_intent(), budget=99)}

        assert "country_requirements" not in families
        assert "scholarships" not in families


class TestQueriesAreBoundedAndOrdered:
    def test_the_budget_is_enforced(self):
        assert len(queries_for(an_intent(population_marker="international"), budget=2)) == 2

    def test_the_default_budget_is_bounded(self):
        """§4: do not explode aliases into unlimited queries."""
        intent = an_intent(population_marker="international")

        assert len(queries_for(intent)) == DEFAULT_QUERY_BUDGET
        assert len(queries_for(intent, budget=99)) > DEFAULT_QUERY_BUDGET

    def test_the_most_specific_query_comes_first(self):
        """A caller that can afford one query gets the one most likely to land."""
        first = queries_for(an_intent())[0]

        assert first.family == "field_and_degree"
        assert first.text == 'site:nu.edu.kz "computer science" "bachelor"'

    def test_a_budget_below_one_is_refused(self):
        with pytest.raises(ValueError, match="at least 1"):
            queries_for(an_intent(), budget=0)

    def test_families_can_be_selected_and_a_typo_is_caught(self):
        selected = queries_for(an_intent(), families=["admissions"])

        assert [q.family for q in selected] == ["admissions"]
        with pytest.raises(ValueError, match="Unknown query families"):
            queries_for(an_intent(), families=["addmissions"])

    def test_every_operator_query_names_the_domain_and_the_plain_one_names_the_institution(self):
        """The restriction itself is enforced by the provider's domain filter.

        `discover_candidates` always passes `domains=[intent.domain]`, and a
        test in `test_hybrid_retrieval` pins that. This one checks that no
        query wanders off to some *other* institution in its text: an operator
        query says the domain, and the natural-language one says the
        institution by name.
        """
        for query in queries_for(an_intent(population_marker="international"), budget=99):
            if query.family == "natural_language":
                assert query.text.startswith("Nazarbayev University ")
            else:
                assert query.text.startswith("site:nu.edu.kz ")

    def test_the_plain_query_carries_no_search_operators(self):
        """Its whole reason to exist: a neural index reads meaning, not syntax."""
        plain = next(
            q for q in queries_for(an_intent(), budget=99) if q.family == "natural_language"
        )

        assert "site:" not in plain.text
        assert '"' not in plain.text

    def test_the_intake_year_appears_only_when_asked_for(self):
        assert "2027" in rendered(an_intent(intake_year=2027))
        assert "2027" not in rendered(an_intent())
        assert "2027" not in rendered(an_intent(intake_year=2027).without_intake())


class TestTheIntentRefusesToBeEmpty:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"institution": " "}, "institution"),
            ({"domain": ""}, "domain"),
            ({"field": ""}, "field of study"),
            ({"intake_year": 1200}, "plausible intake year"),
        ],
    )
    def test_a_missing_or_implausible_dimension_is_refused(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            an_intent(**kwargs)


class TestTheAuditRecordIsRedacted:
    def test_it_does_not_store_the_query_text(self):
        """Keeping full queries in our logs recreates the trail we avoid leaving."""
        intent = an_intent(intake_year=2027, population_marker="international")
        query = queries_for(intent)[0]

        record = redacted_audit_record(intent, query, provider="fake", result_count=3)

        assert query.text not in str(record)
        assert not any("site:" in str(v) for v in dataclasses.asdict(record).values())

    def test_it_keeps_what_telemetry_needs(self):
        intent = an_intent(intake_year=2027)
        query = queries_for(intent)[0]

        record = redacted_audit_record(intent, query, provider="fake", result_count=3)

        assert record.family == "field_and_degree"
        assert record.provider == "fake"
        assert record.result_count == 3
        assert record.institution == "Nazarbayev University"
        assert record.degree == "bachelor"
        assert record.intake_year == 2027
