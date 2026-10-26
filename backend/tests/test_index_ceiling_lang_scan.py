"""SR2-09: the index-ceiling tool reads a page's ``<html lang>`` in linear time.

``index_ceiling.title_and_h1`` searched ``<html\\b[^>]*\\blang\\s*=\\s*["']?([A-Za-z-]+)``
over a page's first 20,000 characters. Each ``<html`` start runs ``[^>]*`` to the
next ``>`` (or the end) and backtracks, so a page of unclosed ``<html `` tags is
quadratic (the SR2-01/02 shape). ``html_lang`` must return exactly what the old
pattern's group returned, on every input, so the old pattern is kept here as the
oracle, as ``test_live_discovery_tag_scan`` does for SR2-02.
"""

from __future__ import annotations

import random
import re
import time

import pytest

from evaluation.research import index_ceiling as ic
from tests.test_live_discovery_tag_scan import FIXTURE_PAGES

OLD_HTML_LANG = re.compile(r"<html\b[^>]*\blang\s*=\s*[\"']?([A-Za-z-]+)", re.IGNORECASE)

#: Linear work on 200,000 characters takes milliseconds; the old pattern took
#: seconds at 20 kB of hostile input and grows with its square.
TIME_BOUND_S = 0.5


def old_html_lang(head: str) -> str | None:
    match = OLD_HTML_LANG.search(head)
    return match.group(1) if match else None


_TOKENS = (
    "<html",
    "<HTML",
    "<htmlx",
    "<html-",
    " lang",
    "lang",
    "LANG",
    "data-lang",
    "xml:lang",
    "lang-",
    "=",
    " = ",
    '"',
    "'",
    "en",
    "de-AT",
    "zh-Hant",
    "-",
    ">",
    "<",
    " ",
    "\n",
    "\t",
    "x",
    "1",
    "_",
    "<head>",
)


def _random_markup(rng: random.Random) -> str:
    return "".join(rng.choice(_TOKENS) for _ in range(rng.randint(0, 40)))


def test_html_lang_matches_the_old_pattern_on_generated_markup() -> None:
    rng = random.Random(20261022)
    differences = []
    for _ in range(30_000):
        text = _random_markup(rng)
        if ic.html_lang(text) != old_html_lang(text):
            differences.append(text)
    assert differences == []


@pytest.mark.parametrize(
    "text",
    [
        '<html lang="de">',
        "<html LANG=de-AT class=x>",
        '<html lang= lang="fr">',  # the old greedy scan took the rightmost lang=
        '<html data-lang="it" lang="pl">',
        '<html lang="pl" data-lang="it">',
        "<html xml:lang='nl'>",
        "<html class=x><body lang=fr>",  # outside the tag: no language
        '<html class=x><html lang="es">',  # the first tag with a lang= wins
        '<html lang="es"',  # no closing '>': read to the end
        "<htmlx lang=de>",
        "<html lang=>",
        '<html lang="-">',
        "",
    ],
)
def test_html_lang_matches_the_old_pattern_on_written_cases(text: str) -> None:
    assert ic.html_lang(text) == old_html_lang(text)


def test_html_lang_matches_the_old_pattern_on_real_pages() -> None:
    assert FIXTURE_PAGES, "the fixture and corpus pages moved"
    for path in FIXTURE_PAGES:
        head = path.read_text(encoding="utf-8", errors="replace")[:20_000]
        assert ic.html_lang(head) == old_html_lang(head), path.name


@pytest.mark.parametrize(
    "hostile",
    [
        "<html " * 40_000,
        "<html lang" * 20_000,
        "<html lang=" * 18_000,
        "<html " + " " * 200_000,
        "<html " + "lang " * 40_000,
        "<html " + "-lang=" * 33_000,
        "<html lang=" + "a" * 200_000,
        "<html lang" + " " * 200_000 + "x",
        "<html lang=" + " " * 200_000 + '"',
    ],
    ids=[
        "unclosed-html",
        "html-lang",
        "html-lang-eq",
        "spaces",
        "lang-words",
        "dash-lang-eq",
        "long-value",
        "lang-then-spaces",
        "eq-then-spaces",
    ],
)
def test_hostile_heads_finish_quickly(hostile: str) -> None:
    started = time.process_time()
    ic.html_lang(hostile)
    ic.title_and_h1(hostile)
    assert time.process_time() - started < TIME_BOUND_S


def test_title_and_h1_still_reads_the_primary_subtag() -> None:
    page = '<html lang="de-AT"><head><title>Informatik</title></head><body><h1>BSc</h1></body>'
    assert ic.title_and_h1(page) == ("Informatik", "BSc", "de")
    assert ic.title_and_h1("<p>no html tag</p>")[2] == ""
