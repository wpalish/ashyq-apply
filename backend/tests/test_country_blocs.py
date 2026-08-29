"""Bloc membership, one test per member.

The Commonwealth listed 15 of its 56 members. Cyprus, Malta and Brunei are
members and the table said they were not — and because a recognised country
absent from a bloc answered `False` rather than `None`, that was not a gap, it
was a confident wrong answer. A Cypriot applicant was told they did not qualify
for a Commonwealth award.

Rwanda, Mozambique, Gabon and Togo were not recognised as countries at all.

Enumerating every member is the only honest way to test this: a spot check of
three names is what left the other 38 missing.
"""
from __future__ import annotations

import pytest

from app.domain.countries import (
    BLOCS,
    MEMBERSHIP_AS_OF,
    canonical_country,
    country_satisfies,
    describe_restriction,
)

EU = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark",
    "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
    "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
]
EFTA = ["Iceland", "Liechtenstein", "Norway", "Switzerland"]
EEA = [*EU, "Iceland", "Liechtenstein", "Norway"]
SCHENGEN = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Czechia", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Iceland", "Italy",
    "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Norway", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain",
    "Sweden", "Switzerland",
]
NORDIC = ["Denmark", "Finland", "Iceland", "Norway", "Sweden"]
ASEAN = [
    "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia", "Myanmar",
    "Philippines", "Singapore", "Thailand", "Vietnam",
]
COMMONWEALTH = [
    "Antigua and Barbuda", "Australia", "The Bahamas", "Bangladesh", "Barbados",
    "Belize", "Botswana", "Brunei", "Cameroon", "Canada", "Cyprus", "Dominica",
    "Eswatini", "Fiji", "Gabon", "The Gambia", "Ghana", "Grenada", "Guyana",
    "India", "Jamaica", "Kenya", "Kiribati", "Lesotho", "Malawi", "Malaysia",
    "Maldives", "Malta", "Mauritius", "Mozambique", "Namibia", "Nauru",
    "New Zealand", "Nigeria", "Pakistan", "Papua New Guinea", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines",
    "Samoa", "Seychelles", "Sierra Leone", "Singapore", "Solomon Islands",
    "South Africa", "Sri Lanka", "Tanzania", "Togo", "Tonga",
    "Trinidad and Tobago", "Tuvalu", "Uganda", "United Kingdom", "Vanuatu",
    "Zambia",
]

MEMBERSHIPS = {
    "European Union": EU,
    "European Economic Area": EEA,
    "EFTA": EFTA,
    "Schengen area": SCHENGEN,
    "Nordic countries": NORDIC,
    "Commonwealth": COMMONWEALTH,
    "ASEAN": ASEAN,
}

#: Recognised countries that belong to none of the blocs above. Their answer
#: must be a confident False, not an absence.
OUTSIDERS = ["Kazakhstan", "Brazil", "Japan", "United States", "Egypt", "Turkey"]


@pytest.mark.parametrize(
    "bloc,country",
    [(bloc, c) for bloc, members in MEMBERSHIPS.items() for c in members],
    ids=lambda v: v if isinstance(v, str) else str(v),
)
def test_every_member_is_recognised_as_one(bloc: str, country: str):
    assert canonical_country(country) is not None, f"{country!r} is not a known country"
    assert country_satisfies(country, bloc) is True, f"{country} should be in {bloc}"


@pytest.mark.parametrize("bloc", sorted(MEMBERSHIPS))
def test_the_membership_count_matches(bloc: str):
    """Counting catches a member added to the test and not to the data, which
    a per-name test alone would not."""
    assert len(BLOCS[bloc].members) == len(set(MEMBERSHIPS[bloc])), bloc


@pytest.mark.parametrize("country", OUTSIDERS)
@pytest.mark.parametrize("bloc", sorted(MEMBERSHIPS))
def test_a_country_outside_a_bloc_is_a_confident_no(bloc: str, country: str):
    assert country_satisfies(country, bloc) is False


class TestTheThreeAnswers:
    def test_an_unknown_country_is_unknown_not_refused(self):
        """The distinction the whole model rests on. Refusing an applicant
        because a name was not recognised is the failure this must not have."""
        assert country_satisfies("Wakanda", "European Union") is None
        assert country_satisfies(None, "European Union") is None

    def test_an_unresolved_group_is_unknown_not_refused(self):
        assert country_satisfies("Kazakhstan", "developing countries") is None
        assert country_satisfies("Germany", "the Global South") is None

    def test_an_incomplete_bloc_cannot_answer_no(self):
        """A list that is not known to be complete may confirm a member and
        must not deny one. The Commonwealth held 15 of 56 names and answered
        False for Cyprus with total confidence."""
        for bloc in BLOCS.values():
            if not bloc.complete:
                assert bloc.members, bloc.name

    def test_every_bloc_cites_where_its_membership_came_from(self):
        for bloc in BLOCS.values():
            assert bloc.source.startswith("https://"), bloc.name
            assert bloc.as_of, bloc.name

    def test_the_as_of_date_is_stated_to_the_reader(self):
        assert MEMBERSHIP_AS_OF in describe_restriction("European Union")


class TestNamesPeopleActuallyWrite:
    @pytest.mark.parametrize(
        "written,expected",
        [
            ("UK", "GB"), ("U.K.", "GB"), ("Great Britain", "GB"),
            ("United Kingdom of Great Britain and Northern Ireland", "GB"),
            ("USA", "US"), ("U.S.A.", "US"), ("the United States", "US"),
            ("Czech Republic", "CZ"), ("Czechia", "CZ"),
            ("Holland", "NL"), ("The Netherlands", "NL"),
            ("Korea, Republic of", "KR"), ("South Korea", "KR"),
            ("Republic of Türkiye", "TR"), ("Turkey", "TR"),
            ("Brunei Darussalam", "BN"), ("Viet Nam", "VN"),
            ("Cabo Verde", "CV"), ("Ivory Coast", "CI"),
            ("Eswatini", "SZ"), ("Swaziland", "SZ"),
            ("Burma", "MM"), ("Myanmar", "MM"),
            ("kazakhstan", "KZ"), ("  Kazakhstan  ", "KZ"),
        ],
    )
    def test_an_alias_resolves(self, written: str, expected: str):
        assert canonical_country(written) == expected

    def test_a_bloc_name_is_not_a_country(self):
        """"European Union" as a country of citizenship is a category error,
        and answering it as though it were a country would be worse."""
        assert canonical_country("European Union") is None
        assert canonical_country("Commonwealth") is None
