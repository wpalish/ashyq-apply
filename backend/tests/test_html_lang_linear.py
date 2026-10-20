"""A page's ``<html lang>`` is read in linear time (security review 2026-10-22, SR2-01).

Every university page is attacker-controlled. ``page_language`` and
``is_host_root`` searched ``<html[^>]*\\blang\\s*=…`` over up to 200,000
characters (``is_host_root``: the whole page); a page of unclosed ``<html``
tags made that search restart ``[^>]*`` at every one, which took about a
minute on the event loop for 200 kB. The funding stage reads every page's
language (ES-2, AW-2 on by default), so one hostile page stalled every case of
the worker. ``html_lang_attr`` gives the same answer from one pass per tag;
these tests pin the agreement with the old search and the time bound.
"""

from __future__ import annotations

import random
import re
import time

import pytest

from app.adapters.page_classifier import html_lang_attr, is_host_root, page_language

#: The search ``page_language`` and ``is_host_root`` used before, as the reference.
_OLD = re.compile(r"<html[^>]*\blang\s*=\s*[\"']?([a-z]{2})", re.I)


def _old(html: str) -> str | None:
    found = _OLD.search(html)
    return found.group(1) if found else None


@pytest.mark.parametrize(
    "html",
    [
        '<!doctype html><html lang="de"><head>',
        "<html lang=en-GB>",
        "<HTML LANG='FR'>",
        '<html xml:lang="en" lang="de">',
        '<html class="x" data-lang="es">',
        "<htmllang=de>",
        "<html lang=de",
        '<html class="a"><html lang="it">',
        '<html <html lang="pt">',
        "<html lang=lang=de>",
        "<html lang = 'nl' >",
        "<html>",
        "",
        '<body><p>lang="de"</p>',
        "<html\nlang\n=\n'pl'>",
        "<html lang=d>",
        '<html lang="1x"><html lang="sv">',
    ],
)
def test_the_same_answer_as_the_old_search(html: str) -> None:
    assert html_lang_attr(html) == _old(html)


def test_the_same_answer_on_random_markup() -> None:
    rng = random.Random(20261022)
    pieces = [
        "<html",
        "<HTML",
        ">",
        " ",
        "lang",
        "LANG",
        "=",
        '"',
        "'",
        "de",
        "e",
        "x",
        "-",
        "\n",
        "<",
    ]
    for _ in range(4000):
        html = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 40)))
        assert html_lang_attr(html) == _old(html), html


@pytest.mark.parametrize(
    "hostile",
    [
        "<html " * 40_000,
        "<html lang" * 20_000,
        "<html lang = " * 15_000,
        "<html" + " lang" * 50_000,
    ],
)
def test_a_hostile_page_is_read_in_bounded_time(hostile: str) -> None:
    started = time.perf_counter()
    page_language(hostile)
    is_host_root("https://uni.example/cs/", hostile * 10)
    assert time.perf_counter() - started < 1.0


def test_page_language_still_reads_the_primary_subtag() -> None:
    assert page_language('<html lang="de-AT">') == "de"
    assert page_language("<html>") == ""
    assert is_host_root("https://uni.example/cs/", '<html lang="cs">')
    assert not is_host_root("https://uni.example/cs/", '<html lang="en">')
