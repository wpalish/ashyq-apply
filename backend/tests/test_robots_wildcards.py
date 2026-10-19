"""robots.txt wildcard rules are matched in bounded time (security review 2026-10-19, SR-01).

robots.txt comes from the site being read, so it is attacker-controlled. The
first wildcard matcher compiled a rule to a regular expression, and a rule of
many stars (``/*a*a*a*a*a*a*a*a*b``) backtracked exponentially on an ordinary
URL, blocking the event loop. The matcher now finds literal segments with
``str.find``; these tests pin both its speed and its agreement with the
regular-expression reading on ordinary rules.
"""

from __future__ import annotations

import random
import re
import time

import pytest

from app.adapters import fetching
from app.adapters.fetching import USER_AGENT, robots_rule_matches


def _regex_reading(path: str, target: str) -> bool:
    """The previous matcher, kept here as the reference on harmless rules."""
    anchored = path.endswith("$")
    pattern = ".*".join(re.escape(part) for part in path.rstrip("$").split("*"))
    return re.match(pattern + ("$" if anchored else ""), target) is not None


@pytest.mark.parametrize(
    ("path", "target", "expected"),
    [
        ("/private/", "/private/fees", True),
        ("/private/", "/public", False),
        ("/*.pdf$", "/files/report.pdf", True),
        ("/*.pdf$", "/files/report.pdf?x=1", False),
        ("/*?*tag=*", "/search?q=x&tag=cs", True),
        ("/*?*tag=*", "/search?q=x", False),
        ("/fish*", "/fish.html", True),
        ("/fish$", "/fish", True),
        ("/fish$", "/fishes", False),
        ("/*", "/anything", True),
        ("$", "/", False),
        ("/a*b*c$", "/abcbc", True),
        ("/a*bc$", "/abcbd", False),
    ],
)
def test_rule_matching_follows_rfc_9309(path, target, expected):
    assert robots_rule_matches(path, target) is expected
    assert _regex_reading(path, target) is expected


def test_the_matcher_agrees_with_the_regex_reading_on_random_rules():
    rng = random.Random(20261019)
    alphabet = "/ab*?.$"
    for _ in range(4000):
        path = "/" + "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
        target = "/" + "".join(rng.choice("/ab?.$") for _ in range(rng.randint(0, 10)))
        assert robots_rule_matches(path, target) is _regex_reading(path, target), (path, target)


def test_a_many_star_rule_is_decided_quickly():
    parser = fetching._FractionalCrawlDelayParser()
    parser.parse(["User-agent: *", "Disallow: /" + "*a" * 40 + "*b"])
    url = "https://example.edu/" + "a" * 5000
    started = time.perf_counter()
    assert not parser.disallows(USER_AGENT, url)
    assert parser.disallows(USER_AGENT, url + "b")
    # The regex reading needed over a minute for 8 stars on 60 characters.
    assert time.perf_counter() - started < 1.0
