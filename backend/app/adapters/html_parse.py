"""One way to turn fetched markup into a DOM, that never raises.

lxml's BeautifulSoup builder crashes on some real pages: Toronto's
scholarships page carries an attribute with a malformed namespace, and
``bs4.builder._lxml`` fails unpacking it (``ValueError: not enough values to
unpack``). That ended the whole case in run 49. The stdlib parser is the
fallback; if it too refuses, an empty document is returned so callers see a
page with nothing on it rather than a crash.
"""

from __future__ import annotations

from bs4 import BeautifulSoup


def parse_html(markup: str) -> BeautifulSoup:
    """``markup`` as a soup: lxml, else ``html.parser``, else an empty soup."""
    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(markup, parser)
        except Exception:  # a hostile page must not end a research run
            continue
    return BeautifulSoup("", "html.parser")
