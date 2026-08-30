"""What "official" means, and why the string test was not it.

`is_official_domain` decides whether a claim is stamped VERIFIED_CURRENT or
left UNVERIFIED, and only the first kind counts toward completeness. It tested
membership with `in` — a plain substring search over the whole URL — which is
wrong in both directions at once.

**Too narrow, and it cost the product its numbers.** The registry stores a
homepage, and the candidate's domain is that homepage's netloc: `www.utoronto.ca`.
Toronto publishes undergraduate admissions on `future.utoronto.ca`, and
`"www.utoronto.ca" in "https://future.utoronto.ca/..."` is False. So every claim
found there was UNVERIFIED, and Toronto's canary row reads *nine claims, 0.0
completeness* — nine facts read correctly off the university's own site and
discarded by a string comparison. Hong Kong and British Columbia fail the same
way for the same reason.

**Too wide, and it is a security defect.** `"utoronto.ca" in
"https://utoronto.ca.attacker.example/fees"` is True, so a lookalike host
anybody can register produces claims stamped as verified against the real
university. The same is true of `notutoronto.ca`.

The registrable domain is what "the same institution" means, the Public Suffix
List is what computes it, and this repository already carries both — the
crawler uses them to stay on the institution's own site. The claim stamp uses
them too now.
"""
from __future__ import annotations

import pytest

from app.adapters.extraction import is_official_domain


class TestASubdomainIsStillTheInstitution:
    @pytest.mark.parametrize(
        "url",
        [
            "https://future.utoronto.ca/program/computer-science",
            "https://www.utoronto.ca/admissions",
            "https://utoronto.ca/fees",
        ],
    )
    def test_any_host_under_the_registrable_domain_counts(self, url: str):
        assert is_official_domain(url, ["www.utoronto.ca"]) is True

    def test_the_registry_may_hold_the_bare_domain_or_a_full_homepage(self):
        """Callers hold whichever the registry gave them, and the answer must
        not depend on which."""
        page = "https://you.ubc.ca/tuition"
        for domain in ("ubc.ca", "www.ubc.ca", "https://www.ubc.ca/"):
            assert is_official_domain(page, [domain]) is True, domain

    def test_a_multi_part_suffix_is_not_mistaken_for_the_registrable_domain(self):
        """`ox.ac.uk` and `cam.ac.uk` are two institutions, not one `ac.uk`."""
        assert is_official_domain("https://www.ox.ac.uk/admissions", ["ox.ac.uk"])
        assert not is_official_domain("https://www.cam.ac.uk/admissions", ["ox.ac.uk"])


class TestALookalikeIsNotTheInstitution:
    @pytest.mark.parametrize(
        "url",
        [
            "https://utoronto.ca.attacker.example/fees",
            "https://notutoronto.ca/fees",
            "https://utoronto.ca.evil.test/deadline",
            "https://fake-utoronto.ca/deadline",
        ],
    )
    def test_a_host_that_merely_contains_the_domain_is_refused(self, url: str):
        """The dangerous direction. A claim stamped VERIFIED_CURRENT from a
        host anybody can register is a deadline an applicant will act on."""
        assert is_official_domain(url, ["utoronto.ca"]) is False

    def test_the_domain_appearing_in_a_path_or_query_is_not_the_host(self):
        assert is_official_domain(
            "https://rankings.example.com/compare?a=utoronto.ca", ["utoronto.ca"]
        ) is False
        assert is_official_domain(
            "https://rankings.example.com/utoronto.ca/fees", ["utoronto.ca"]
        ) is False


class TestKnowingTheInstitutionBeatsGuessingFromTheSuffix:
    def test_an_unrelated_academic_domain_is_not_this_institution(self):
        """The `.edu`/`.ac.uk` heuristic answers "is this some university",
        which is a different question from "is this the university whose
        programme we are verifying". When the institution is known, the
        heuristic must not overrule it: a fee on `otherplace.edu` is not
        evidence about Toronto."""
        assert is_official_domain("https://otherplace.edu/fees", ["utoronto.ca"]) is False

    def test_the_suffix_heuristic_still_applies_when_no_domain_is_known(self):
        """Kept deliberately. Some callers have no candidate domain to compare
        against, and for them "an academic domain" is the only signal there is.
        Removing it would silently downgrade claims that are in fact official."""
        assert is_official_domain("https://www.asu.edu/x") is True
        assert is_official_domain("https://www.ox.ac.uk/y") is True
        assert is_official_domain("https://rankings.example.com/z") is False

    def test_an_empty_domain_list_is_the_same_as_none(self):
        """`[candidate.domain]` is `[""]` when discovery never learned one."""
        assert is_official_domain("https://www.asu.edu/x", [""]) is True
        assert is_official_domain("https://rankings.example.com/z", [""]) is False


class TestItAnswersFalseRatherThanGuessing:
    @pytest.mark.parametrize(
        "url",
        ["", "not a url", "https://", "https://[bad::ipv6/x"],
    )
    def test_a_url_it_cannot_parse_is_not_official(self, url: str):
        assert is_official_domain(url, ["utoronto.ca"]) is False
