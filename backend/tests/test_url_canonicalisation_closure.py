"""Canonicalising a URL must not produce one the same code rejects.

    canonical_url("https://[2001:db8::1]/programmes")
    -> 'https://2001:db8::1/programmes'
    url_problem(that)
    -> 'host or port is malformed'

The brackets around an IPv6 literal are part of the syntax, not decoration.
Dropping them turned a valid URL into one whose colons read as a port, so a
page reached by IPv6 was canonicalised into something that could never be
fetched again — and the two functions disagreed about the same address.

`url_problem` was also accepting things that cannot resolve: invalid percent
escapes, underscores in host labels, labels starting or ending with a hyphen,
empty labels from a doubled dot, and labels past the 63-character limit. None
of them is a host, and treating them as one means the fetcher tries.

The properties below are what "closed" means, and they are checked over a
corpus that includes real internationalised university domains, because the
cheap way to satisfy every rule here is to refuse everything.
"""
from __future__ import annotations

import pytest

from app.adapters.discovery.url_signals import canonical_url, same_institution, url_problem

#: Real, and must keep working. Refusing these to satisfy the rules would be a
#: regression dressed as a fix.
VALID = [
    "https://www.rug.nl/bachelors/computing-science",
    "https://future.utoronto.ca/program/computer-science",
    "http://example.edu:8080/programmes",
    "https://example.edu:443/programmes",
    "https://[2001:db8::1]/programmes",
    "https://[2001:db8::1]:8443/programmes",
    "https://xn--bcher-kva.example/programmes",
    "https://www.uni-münchen.de/studium",
    "https://éducation.example.fr/programmes",
    "https://a.example.edu/x",
    "https://sub.domain.deep.example.ac.uk/programmes?year=2027",
    "https://example.edu/programmes%20and%20fees",
    "https://example.edu/caf%C3%A9",
]

INVALID = [
    "https://example.edu/%ZZ",
    "https://example.edu/%",
    "https://example.edu/%A",
    "https://exa_mple.edu/x",
    "https://-bad.example.edu/x",
    "https://bad-.example.edu/x",
    "https://example..edu/x",
    "https://" + "a" * 64 + ".edu/x",
    "https://example.edu:bad/x",
    "https://example.edu:99999/x",
    "https://[bad::ipv6/x",
    "https:///x",
    "javascript:alert(1)",
]


class TestCanonicalisationIsClosed:
    @pytest.mark.parametrize("url", VALID)
    def test_a_canonicalised_url_is_still_accepted(self, url: str):
        """The property the IPv6 bug broke: canonicalising must not turn an
        accepted URL into a rejected one."""
        canonical = canonical_url(url)
        assert canonical, f"{url} canonicalised to nothing"
        assert url_problem(canonical) is None, (
            f"{url} -> {canonical} which is rejected as {url_problem(canonical)!r}"
        )

    @pytest.mark.parametrize("url", VALID)
    def test_canonicalisation_is_idempotent(self, url: str):
        once = canonical_url(url)
        assert canonical_url(once) == once, f"{url}: {once} -> {canonical_url(once)}"

    @pytest.mark.parametrize("url", VALID + INVALID)
    def test_nothing_raises(self, url: str):
        canonical_url(url)
        url_problem(url)
        same_institution(url, "example.edu")

    def test_an_ipv6_literal_keeps_its_brackets(self):
        assert canonical_url("https://[2001:db8::1]/programmes") == (
            "https://[2001:db8::1]/programmes"
        )

    def test_an_ipv6_literal_keeps_a_real_port_and_drops_a_default(self):
        assert canonical_url("https://[2001:db8::1]:8443/x") == "https://[2001:db8::1]:8443/x"
        assert canonical_url("https://[2001:db8::1]:443/x") == "https://[2001:db8::1]/x"


class TestHostsThatCannotResolveAreRefused:
    @pytest.mark.parametrize("url", INVALID)
    def test_they_are_named_as_a_problem(self, url: str):
        assert url_problem(url), f"{url!r} was accepted"

    @pytest.mark.parametrize("url", INVALID)
    def test_they_are_never_the_same_institution(self, url: str):
        assert same_institution(url, "example.edu") is False


class TestRealDomainsStillWork:
    @pytest.mark.parametrize("url", VALID)
    def test_they_are_accepted(self, url: str):
        assert url_problem(url) is None, f"{url}: {url_problem(url)}"

    def test_a_unicode_host_survives_canonicalisation(self):
        """A German university's own domain. Refusing non-ASCII hosts would be
        the easy way to pass every rule above and would be wrong."""
        assert canonical_url("https://www.uni-münchen.de/studium")

    def test_percent_encoding_that_is_valid_is_kept(self):
        assert url_problem("https://example.edu/caf%C3%A9") is None


class TestTheSsrfInvariantsStillHold:
    @pytest.mark.parametrize(
        "url",
        [
            "https://user:password@example.edu/x",
            "https://exa\x00mple.edu/x",
            "https://exam\nple.edu/x",
        ],
    )
    def test_credentials_and_control_characters(self, url: str):
        """Userinfo is stripped rather than carried into a fetch; control
        characters are refused rather than cleaned."""
        canonical = canonical_url(url)
        assert "password" not in canonical
        assert "\x00" not in canonical and "\n" not in canonical
