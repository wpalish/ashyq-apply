"""SR2-02: the ``<html>``/``<link>`` tag and attribute scans are linear.

Discovery reads ``<html lang>`` and ``<link rel="alternate" hreflang>`` on
every page it reads for identity, from up to 200,000 characters the page's
author controls. The original patterns were quadratic on hostile input (one
50,000-character attribute name took about 35 s). The replacements must
finish such input quickly *and* return exactly what the originals returned on
every other input, so the originals are kept here as the oracle.
"""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    _attributes,
    _html_tag,
    _link_tags,
    declared_alternates,
    english_alternate,
    local_alternate,
)

# The patterns as they were before SR2-02: the oracle for equivalence.
OLD_HTML_TAG = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
OLD_LINK_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
OLD_ATTRIBUTE = re.compile(r"""([a-zA-Z_:][-\w:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE_PAGES = sorted(
    [
        *(BACKEND / "tests" / "fixtures").rglob("*.htm*"),
        *(BACKEND / "app" / "corpus").rglob("*.htm*"),
    ]
)

#: Generous for a linear scan of 200,000 characters (a few milliseconds), and
#: two orders of magnitude below what the quadratic patterns took.
TIME_BOUND_S = 0.5

URL = "https://www.uni.de/studium/informatik"
DOMAIN = "uni.de"


def old_html_tag(head: str) -> str | None:
    match = OLD_HTML_TAG.search(head)
    return match.group(0) if match else None


def old_attribute_groups(tag: str) -> list[tuple[str | None, ...]]:
    return [m.groups() for m in OLD_ATTRIBUTE.finditer(tag)]


def new_attribute_groups(tag: str) -> list[tuple[str | None, ...]]:
    return [m.groups() for m in live_discovery._ATTRIBUTE.finditer(tag)]


def old_attributes(tag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in OLD_ATTRIBUTE.finditer(tag):
        value = next((g for g in m.groups()[1:] if g is not None), "")
        out.setdefault(m.group(1).lower(), value)
    return out


def assert_same(text: str) -> None:
    """Every scan over ``text`` agrees with the original patterns."""
    assert _link_tags(text) == OLD_LINK_TAG.findall(text), text
    assert _html_tag(text) == old_html_tag(text), text
    assert new_attribute_groups(text) == old_attribute_groups(text), text
    assert _attributes(text) == old_attributes(text), text


def timed(call, *args):
    start = time.perf_counter()
    result = call(*args)
    return result, time.perf_counter() - start


# --- hostile inputs -------------------------------------------------------

HOSTILE_ATTRIBUTE_TEXT = {
    "50,000-character attribute name": "<link " + "a" * 50_000 + ">",
    "name after 50,000 non-starters": "<link " + "1" * 50_000 + "a" * 50_000 + ">",
    "50,000 dashes": "<link " + "-" * 50_000 + ">",
    "50,000 colons": "<link " + ":" * 50_000 + ">",
    "50,000 non-ASCII letters": "<link " + "é" * 50_000 + ">",
    "names split by whitespace, no '='": "<link " + ("abcdefgh" + " " * 8) * 12_000 + ">",
    "'=' with no value": "<link " + "a=" * 50_000 + ">",
    "names before one unclosed quote": "<link " + "a" * 50_000 + '="' + "b" * 50_000 + ">",
}

HOSTILE_HEADS = {
    "200,000 characters of '<link' with no '>'": "<link" * 40_000,
    "200,000 characters of '<html' with no '>'": "<html" * 40_000,
    "'<link ' runs with no '>'": "<link " * 33_000,
    "'<html lang=de ' runs with no '>'": "<html lang=de " * 14_000,
    "one '<link' then 200,000 characters": "<link " + "x" * 199_990,
    "a long name inside <html>": '<html lang="de" ' + "a" * 150_000 + ">",
}


@pytest.mark.parametrize("text", HOSTILE_ATTRIBUTE_TEXT.values(), ids=HOSTILE_ATTRIBUTE_TEXT.keys())
def test_hostile_attribute_text_is_read_in_linear_time(text):
    _, elapsed = timed(_attributes, text)
    assert elapsed < TIME_BOUND_S


@pytest.mark.parametrize("head", HOSTILE_HEADS.values(), ids=HOSTILE_HEADS.keys())
def test_hostile_heads_are_scanned_in_linear_time(head):
    _, elapsed = timed(_link_tags, head)
    assert elapsed < TIME_BOUND_S
    _, elapsed = timed(_html_tag, head)
    assert elapsed < TIME_BOUND_S


HOSTILE_PAGES = {
    # The three inputs SECURITY_REVIEW_2026-10-22 SR2-02 names ...
    "review: '<html ' x 40,000": "<html " * 40_000,
    "review: '<link ' x 40,000": "<link " * 40_000,
    "review: 200,000-character name in <link>": '<html lang="de"><link ' + "a" * 200_000 + ">",
    # ... whose <link> is cut off by the 200,000-character head, so these two
    # fit inside it and the attribute scan really runs, on a German page and on
    # an English one (which local_alternate reads) ...
    "150,000-character name in <link>": '<html lang="de"><link ' + "a" * 150_000 + ">",
    "150,000-character name in <link>, English page": '<html lang="en"><link '
    + "a" * 150_000
    + ">",
    # ... and a long name in the <html> tag itself, before unterminated links.
    "long <html> attribute, then open <link>s": '<html lang="de" '
    + "a" * 50_000
    + "><head>"
    + "<link " * 25_000,
}


@pytest.mark.parametrize("html", HOSTILE_PAGES.values(), ids=HOSTILE_PAGES.keys())
def test_identity_reads_finish_on_a_hostile_page(html):
    """The identity reads themselves, end to end, as discovery calls them."""
    _, elapsed = timed(english_alternate, URL, html, DOMAIN)
    assert elapsed < TIME_BOUND_S
    _, elapsed = timed(local_alternate, URL, html, DOMAIN, "Germany")
    assert elapsed < TIME_BOUND_S
    _, elapsed = timed(declared_alternates, URL, html, DOMAIN)
    assert elapsed < TIME_BOUND_S


@pytest.mark.parametrize("text", HOSTILE_ATTRIBUTE_TEXT.values(), ids=HOSTILE_ATTRIBUTE_TEXT.keys())
def test_hostile_attribute_text_still_means_what_it_meant(text):
    # Shortened so the quadratic oracle stays fast; the shape is the same.
    short = text[:3_000] + text[-3:]
    assert_same(short)


# --- equivalence on realistic tags ----------------------------------------

TAG_NAMES = ["link", "LINK", "Link", "html", "HTML", "Html", "linked", "html5", "meta", "a"]
ATTRIBUTE_NAMES = [
    "rel",
    "REL",
    "href",
    "hreflang",
    "HrefLang",
    "lang",
    "xml:lang",
    "data-x",
    "data-hreflang",
    "_private",
    ":colon",
    "a.b",
    "x-1",
    "1rel",
    "-rel",
    ".lang",
    "é-lang",
    "langé",
    "dir",
    "type",
    "media",
    "sizes",
    "crossorigin",
]
VALUES = [
    "alternate",
    "canonical",
    "stylesheet",
    "en",
    "en-GB",
    "de-DE",
    "x-default",
    "https://www.uni.de/en/studies/informatics",
    "/en/studies?x=1&amp;y=2",
    "",
    "a b",
    "a>b",
    "a<b",
    "a=b",
    "it's",
    'say "hi"',
    "é",
    "\t",
]
SEPARATORS = [" ", "  ", "\n", "\t", "\r\n", "", "/", " / "]
EQUALS = ["=", " = ", "=\n", "\t=", " ="]


def realistic_attribute(rng: random.Random) -> str:
    name = rng.choice(ATTRIBUTE_NAMES)
    roll = rng.random()
    if roll < 0.08:
        return name  # a bare boolean attribute
    value = rng.choice(VALUES)
    eq = rng.choice(EQUALS)
    roll = rng.random()
    if roll < 0.45:
        return f'{name}{eq}"{value}"'
    if roll < 0.7:
        return f"{name}{eq}'{value}'"
    if roll < 0.9:
        return f"{name}{eq}{value}"
    # Malformed: an unclosed or mismatched quote, a missing value.
    return rng.choice(
        [f'{name}{eq}"{value}', f"{name}{eq}'{value}\"", f"{name}{eq}", f"{name}{eq}>"]
    )


def realistic_tag(rng: random.Random) -> str:
    parts = [f"<{rng.choice(TAG_NAMES)}"]
    for _ in range(rng.randint(0, 6)):
        parts.append(rng.choice(SEPARATORS))
        parts.append(realistic_attribute(rng))
    parts.append(rng.choice(["", " ", "/", " /"]))
    if rng.random() < 0.9:
        parts.append(">")  # one in ten tags is left open
    return "".join(parts)


SOUP = [*"aZz_:-.9é \t\n=\"'<>/", "<link", "<html", "rel", "lang", "href", '="', "='"]


def soup(rng: random.Random) -> str:
    return "".join(rng.choice(SOUP) for _ in range(rng.randint(0, 48)))


REALISTIC_TAGS = 60_000
SOUP_STRINGS = 20_000
HEADS = 1_000


def test_the_new_patterns_match_the_originals_on_realistic_tags():
    rng = random.Random(20261022)
    for _ in range(REALISTIC_TAGS):
        assert_same(realistic_tag(rng))


def test_the_new_patterns_match_the_originals_on_random_markup():
    rng = random.Random(2_02)
    for _ in range(SOUP_STRINGS):
        assert_same(soup(rng))


def test_the_new_patterns_match_the_originals_on_whole_heads():
    """Many tags in one text: the scans resume where the originals resumed."""
    rng = random.Random(7)
    for _ in range(HEADS):
        head = "".join(
            rng.choice([realistic_tag(rng), soup(rng), "<title>x</title>", "\n"])
            for _ in range(rng.randint(1, 30))
        )
        assert_same(head)
        for tag in OLD_LINK_TAG.findall(head):
            assert _attributes(tag) == old_attributes(tag)


def test_the_fixture_pages_are_read_exactly_as_before():
    assert len(FIXTURE_PAGES) > 100
    tags_checked = 0
    for page in FIXTURE_PAGES:
        html = page.read_text(encoding="utf-8", errors="replace")
        head = html[:200_000]
        assert _link_tags(head) == OLD_LINK_TAG.findall(head), page
        assert _html_tag(head) == old_html_tag(head), page
        # Every tag on the page, not only <html> and <link>: a wider corpus
        # of real attribute syntax for the attribute scan.
        for tag in re.findall(r"<[a-zA-Z][^<>]*>", html):
            assert new_attribute_groups(tag) == old_attribute_groups(tag), (page, tag)
            tags_checked += 1
    assert tags_checked > 10_000
