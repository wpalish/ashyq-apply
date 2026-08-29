"""Country and bloc eligibility, decided by membership rather than by substring.

The extractor recognises "European Union" and "European Economic Area" as
restrictions. The assessment then asked whether the string "Germany" appears
inside the string "European Union". It does not, so a German citizen was told
they are not eligible for an EU-only award.

Substring matching is the wrong tool twice over: it says no to a real member,
and it would say yes to any country whose name happens to appear inside a
group's. Membership is a fact about the world and needs a table.
"""

from __future__ import annotations

import pytest

from app.domain.countries import (
    BLOCS,
    canonical_country,
    country_satisfies,
    describe_restriction,
)


class TestCanonicalNames:
    @pytest.mark.parametrize("raw,expected", [
        ("Germany", "DE"), ("germany", "DE"), (" GERMANY ", "DE"),
        ("Deutschland", "DE"), ("DE", "DE"), ("DEU", "DE"),
        ("The Netherlands", "NL"), ("Holland", "NL"),
        ("United Kingdom", "GB"), ("UK", "GB"), ("Great Britain", "GB"),
        ("United States", "US"), ("USA", "US"), ("U.S.A.", "US"),
        ("Kazakhstan", "KZ"), ("Republic of Kazakhstan", "KZ"),
        ("South Korea", "KR"), ("Korea, Republic of", "KR"),
        ("Czechia", "CZ"), ("Czech Republic", "CZ"),
    ])
    def test_names_and_codes_normalise(self, raw, expected):
        assert canonical_country(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", "Atlantis", "European Union", None])
    def test_a_non_country_has_no_code(self, raw):
        assert canonical_country(raw) is None


class TestMembership:
    def test_germany_is_in_the_european_union(self):
        assert country_satisfies("Germany", "European Union") is True

    def test_norway_is_in_the_eea_but_not_the_eu(self):
        assert country_satisfies("Norway", "European Economic Area") is True
        assert country_satisfies("Norway", "European Union") is False

    def test_switzerland_is_in_neither_the_eu_nor_the_eea(self):
        """Switzerland is EFTA and Schengen, and neither EU nor EEA. Treating
        "European" as one thing is exactly the error this table prevents."""
        assert country_satisfies("Switzerland", "European Economic Area") is False
        assert country_satisfies("Switzerland", "European Union") is False
        assert country_satisfies("Switzerland", "EFTA") is True
        assert country_satisfies("Switzerland", "Schengen area") is True

    def test_the_united_kingdom_left_the_eu_and_is_in_the_commonwealth(self):
        assert country_satisfies("United Kingdom", "European Union") is False
        assert country_satisfies("United Kingdom", "Commonwealth") is True

    def test_kazakhstan_is_in_none_of_them(self):
        for bloc in ("European Union", "European Economic Area", "Schengen area"):
            assert country_satisfies("Kazakhstan", bloc) is False

    @pytest.mark.parametrize("bloc", sorted(BLOCS))
    def test_every_bloc_has_members_and_they_are_all_real_countries(self, bloc):
        members = BLOCS[bloc]
        assert members, f"{bloc} has no members"
        for code in members:
            assert len(code) == 2 and code.isupper(), f"{bloc}: {code!r} is not a code"

    def test_a_country_against_a_country_is_a_direct_comparison(self):
        assert country_satisfies("Germany", "Germany") is True
        assert country_satisfies("Germany", "Deutschland") is True
        assert country_satisfies("Germany", "France") is False

    def test_an_unrecognised_group_is_unknown_not_false(self):
        """A group we cannot resolve is a question, not a refusal."""
        assert country_satisfies("Germany", "the Baltic states and friends") is None

    def test_an_unrecognised_applicant_country_is_unknown(self):
        assert country_satisfies("Atlantis", "European Union") is None
        assert country_satisfies("", "European Union") is None


class TestDescribingARestriction:
    def test_a_bloc_lists_what_it_means(self):
        text = describe_restriction("European Union")
        assert "European Union" in text
        assert "27" in text or "member" in text.lower()

    def test_a_country_describes_itself(self):
        assert "Germany" in describe_restriction("Germany")
