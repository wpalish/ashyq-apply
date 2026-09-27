"""V2-22a — an institution is identified by evidence, or not at all.

The two failures these tests exist to prevent are the ones the phase guide
names: splitting one institution across its spellings, and merging two
because their names reduce to the same tokens.
"""

from __future__ import annotations

from app.adapters.discovery.registry_identities import institution_identities
from app.domain.dedupe import university_key
from app.domain.entity_resolution import (
    Basis,
    InstitutionIdentity,
    Resolution,
    resolve_institution,
    same_institution,
)

DELFT = InstitutionIdentity(
    key="delft",
    name="Delft University of Technology",
    country="Netherlands",
    domains=("tudelft.nl",),
    aliases=("TU Delft", "Technische Universiteit Delft"),
    source_urls=("https://www.tudelft.nl/",),
)
GRONINGEN = InstitutionIdentity(
    key="groningen",
    name="University of Groningen",
    country="Netherlands",
    domains=("rug.nl",),
)
REGISTRY = [DELFT, GRONINGEN]


class TestEvidence:
    def test_a_host_identifies_the_institution_that_served_the_page(self):
        answer = resolve_institution(REGISTRY, url="https://www.tudelft.nl/en/education/")
        assert answer.identity is DELFT
        assert answer.basis is Basis.DOMAIN
        assert answer.evidence == "tudelft.nl"

    def test_a_recorded_alias_resolves_a_spelling_the_key_would_split(self):
        """The Dutch name and the English name are one university.

        `university_key` gives them different keys, which is how the same
        institution enters a run twice.
        """
        dutch = resolve_institution(REGISTRY, name="Technische Universiteit Delft")
        assert dutch.identity is DELFT
        assert dutch.basis is Basis.ALIAS
        assert university_key("Technische Universiteit Delft", "Netherlands") != university_key(
            "Delft University of Technology", "Netherlands"
        )

    def test_the_host_decides_when_a_page_calls_itself_something_else(self):
        """A name is what a page says; a host is who served it."""
        answer = resolve_institution(
            REGISTRY, url="https://www.tudelft.nl/x", name="University of Groningen"
        )
        assert answer.identity is DELFT

    def test_an_unrecorded_name_resolves_to_nothing(self):
        answer = resolve_institution(REGISTRY, name="Delft Technical University")
        assert answer.identity is None
        assert answer.resolved is False
        assert answer.basis is Basis.UNRESOLVED
        assert "no recorded domain or alias" in answer.explain()
        assert resolve_institution(REGISTRY, url="https://www.tudelft.nl/").resolved is True

    def test_a_lookalike_host_is_not_the_institution(self):
        """`tudelft.nl.attacker.example` is a spoof, not a source."""
        answer = resolve_institution(REGISTRY, url="https://tudelft.nl.attacker.example/fees")
        assert answer.identity is None

    def test_country_narrows_a_name_match_and_never_creates_one(self):
        assert resolve_institution(REGISTRY, name="TU Delft", country="Germany").identity is None
        assert (
            resolve_institution(REGISTRY, name="TU Delft", country="Netherlands").identity is DELFT
        )


class TestAuditability:
    def test_every_answer_carries_the_evidence_that_produced_it(self):
        """The guide's requirement: a merge nobody can explain is the failure."""
        by_host = resolve_institution(REGISTRY, url="https://rug.nl/")
        assert by_host.explain() == "University of Groningen: served by rug.nl"
        by_name = resolve_institution(REGISTRY, name="TU Delft")
        assert by_name.explain() == "Delft University of Technology: recorded as 'TU Delft'"

    def test_two_unresolved_things_are_never_the_same_institution(self):
        """Without evidence there is no identity, and 'both unknown' is not a match."""
        left = resolve_institution(REGISTRY, name="Delft Technical University")
        right = resolve_institution(REGISTRY, name="Delft Technical University")
        assert left == right == Resolution(None, Basis.UNRESOLVED)
        assert same_institution(left, right) is False

    def test_two_spellings_of_one_institution_are_the_same_institution(self):
        assert same_institution(
            resolve_institution(REGISTRY, name="TU Delft"),
            resolve_institution(REGISTRY, url="https://www.tudelft.nl/"),
        )

    def test_two_institutions_in_one_country_stay_two(self):
        assert not same_institution(
            resolve_institution(REGISTRY, url="https://www.tudelft.nl/"),
            resolve_institution(REGISTRY, url="https://www.rug.nl/"),
        )


class TestWhatIsRecordedAndWhatIsNot:
    def test_an_institution_with_no_recorded_aliases_resolves_by_its_own_name(self):
        answer = resolve_institution(REGISTRY, name="University of Groningen")
        assert answer.identity is GRONINGEN

    def test_nothing_here_invents_an_alias(self):
        """Aliases are owner data, like a verified seed. This module reads
        them; it must never grow a rule that produces them."""
        assert GRONINGEN.aliases == ()
        assert GRONINGEN.names() == ("University of Groningen",)
        assert resolve_institution(REGISTRY, name="Rijksuniversiteit Groningen").identity is None


class TestTheRegistryResolvesItself:
    """V2-22b — the registry is the identity data, so it must be consistent.

    These are data tests as much as code tests: they fail when the registry
    gains a bad entry, which is the only way that kind of error surfaces
    before a run does something strange with it.
    """

    def test_every_institution_resolves_from_its_own_homepage_and_seeds(self):
        from urllib.parse import urlparse

        identities = list(institution_identities())
        assert len(identities) >= 19
        for identity in identities:
            for url in identity.source_urls:
                answer = resolve_institution(identities, url=url)
                assert answer.identity is not None, f"{url} resolves to nothing"
                assert answer.identity.key == identity.key, (
                    f"{urlparse(url).hostname} resolves to {answer.identity.name!r}, "
                    f"not to {identity.name!r}"
                )

    def test_no_two_institutions_share_a_domain(self):
        """Two entries on one domain are one university recorded twice, or a
        typo. Either way a run would treat them as two places to apply."""
        seen: dict[str, str] = {}
        for identity in institution_identities():
            for domain in identity.domains:
                assert domain not in seen or seen[domain] == identity.name, (
                    f"{domain} is claimed by both {seen.get(domain)!r} and {identity.name!r}"
                )
                seen[domain] = identity.name

    def test_every_institution_resolves_from_its_own_name(self):
        identities = list(institution_identities())
        for identity in identities:
            answer = resolve_institution(identities, name=identity.name, country=identity.country)
            assert answer.identity is not None, f"{identity.name!r} does not resolve by name"

    def test_kaist_is_reachable_through_its_school_host(self):
        """The owner's 2026-09-22 seeds put cs.kaist.ac.kr on the registry.

        Before them, KAIST's own programme pages were served by a host the
        pipeline could not attribute to KAIST at all.
        """
        answer = resolve_institution(
            list(institution_identities()), url="https://cs.kaist.ac.kr/content?menu=318"
        )
        assert answer.identity is not None
        assert answer.identity.name == "KAIST"
        assert answer.evidence == "kaist.ac.kr"


def test_a_registry_entry_with_no_url_identifies_nothing() -> None:
    """A key invented from a name would hide the data error, not fix it."""
    from app.adapters.discovery.registry_identities import _identities

    assert _identities([{"name": "Somewhere", "country": "Nowhere"}]) == []
    assert len(_identities([{"name": "S", "homepage": "https://s.example/"}])) == 1
