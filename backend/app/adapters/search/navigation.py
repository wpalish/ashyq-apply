"""One hop through a site's own navigation, for pages a search index cannot see.

KAIST's computer science programme lives at ``cs.kaist.ac.kr/content?menu=188``.
No query shape reaches it — not English, not Korean, not restricted to the
subdomain — because there is not one word in that URL to match. The department
root, however, comes back first or second in almost every query, and the target
is linked directly from its navigation.

That is the general shape, not a KAIST quirk. A search index finds what is
linkable and word-bearing, so it reliably finds *entry points*. Structural
traversal does not care about words in a URL. The two fail differently, which
is why fusion has several generators, and why the answer to an opaque site is
one hop rather than better queries.

The link *text* carries the meaning the URL lost. ``matches_field_text`` in
``live_discovery`` was written for the same reason — Toronto's programme sits
at ``/data-computer-science`` behind the words "Data & Computer Science" — and
is reused here rather than reimplemented.

This module reads HTML it is handed. It fetches nothing: the entry point comes
through ``Fetcher`` like every other page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from lxml import html as lxml_html

from app.adapters.discovery.live_discovery import (
    canonical_url,
    degree_level_named,
    is_excluded_path,
    matches_field_text,
    same_institution,
)
from app.adapters.search.fusion import Generator, SourcedCandidate
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.ontology import retrieval_candidates

#: Most links to read from one page. A university front page can carry several
#: hundred; past this the page is a directory and the hop is the wrong tool.
MAX_LINKS_PER_PAGE = 400

#: Most candidates one hop may contribute. The hop is a supplement to search,
#: not a crawl, and an unbounded one would drown fusion in navigation chrome.
DEFAULT_HOP_LIMIT = 10

_SPACE = re.compile(r"\s+")

#: A staff or faculty listing is not a programme. ``live_discovery`` already
#: rejects research groups, labs and institutes; people pages belong with them
#: and are rejected here rather than there, because that module's rule is used
#: by the existing pipeline and widening it is a separate change.
_NOT_A_PROGRAMME_LINK = re.compile(
    r"/(people|faculty|staff|directory|professors?|members?|alumni)(/|$)", re.IGNORECASE
)

#: Words that name a study section, in the languages this corpus meets. A
#: navigation label is often the only place the meaning survives, and on a
#: Korean or Finnish site it survives in Korean or Finnish. Verified against
#: the pages they were read from; nothing here is guessed.
_SECTION_WORDS = (
    # English
    "education",
    "study",
    "studies",
    "academics",
    "programme",
    "program",
    "curriculum",
    "undergraduate",
    "bachelor",
    # Korean: 교육 education, 교과과정 curriculum. Note the absence of a bare
    # 학부 ("undergraduate"): CJK has no word boundaries, so as a substring it
    # also matched 학부발전기금 (development fund), 학부장 인사말 (the dean's
    # greeting) and 학부동아리 (student clubs) on KAIST's real navigation.
    "교육",
    "교과과정",
)


@dataclass(frozen=True, slots=True)
class NavigationLink:
    url: str
    text: str
    #: The page this link was found on. §11 wants a parent for every candidate.
    parent_url: str


def _clean(raw: str) -> str:
    return _SPACE.sub(" ", raw or "").strip()


def _names(term: str, haystack: str) -> bool:
    """Whether ``haystack`` names ``term`` as a word, not as a fragment.

    Substring matching put four faculty pages above the programme on KAIST's
    real navigation, because ``facultyInteractiveComputing`` contains
    ``computing``. A URL is split on its own separators and on camelCase, so a
    term has to be a segment rather than a coincidence.
    """
    words = re.split(
        r"[^0-9a-z\u0400-\u04ff\uac00-\ud7a3]+",
        re.sub(r"(?<=[a-z])(?=[A-Z])", " ", haystack).lower(),
    )
    wanted = [w for w in re.split(r"[^0-9a-z]+", term.lower()) if w]
    return bool(wanted) and all(w in words for w in wanted)


def links_from(html: str, base_url: str) -> tuple[NavigationLink, ...]:
    """Every same-institution link on the page, with its text, deduplicated.

    Off-domain links are dropped with the same registrable-domain comparison
    discovery uses, so a hop can never wander onto a partner site. Excluded
    paths — news, events, vacancies, media — go too: a hop is for finding a
    programme, and following the news feed is how a bounded step becomes a
    crawl.
    """
    try:
        tree = lxml_html.fromstring(html)
    except (ValueError, lxml_html.etree.ParserError):
        # Malformed or empty markup yields no links rather than an exception:
        # one unparseable page must not end a discovery run.
        return ()

    seen: set[str] = set()
    links: list[NavigationLink] = []
    anchors = sorted(tree.iter("a"), key=lambda a: not (a.get("href") or "").startswith("https"))
    for anchor in anchors:
        if len(links) >= MAX_LINKS_PER_PAGE:
            break
        href = (anchor.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue
        url = canonical_url(urljoin(base_url, href))
        if not url:
            continue
        if not same_institution(url, base_url) or is_excluded_path(url):
            continue
        if _NOT_A_PROGRAMME_LINK.search(url):
            continue
        # http:// and https:// of one page are one page. ``canonical_url``
        # keeps the scheme, correctly for the pipeline at large, but a site
        # that links itself both ways would otherwise spend two candidate
        # slots on the same document.
        identity = url.split("://", 1)[-1]
        if identity in seen:
            continue
        seen.add(identity)
        # A real parser, because the labels here decide the ranking. A regex
        # over anchors read KAIST's ``navi="교육"`` attributes as if they were
        # link text and ranked four staff pages above the programme.
        links.append(
            NavigationLink(url=url, text=_clean(anchor.text_content()), parent_url=base_url)
        )
    return tuple(links)


def _score(link: NavigationLink, intent: DiscoveryIntent) -> tuple[int, list[str]]:
    """How strongly this link looks like the requested programme, and why."""
    terms = retrieval_candidates(intent.field)
    strong = [t.term for t in terms if t.is_match]
    related = [t.term for t in terms if not t.is_match]

    text = link.text.lower()
    url = link.url.lower()
    score = 0
    signals: list[str] = []

    if matches_field_text(link.text, strong):
        score += 6
        signals.append("field_in_link_text")
    elif any(_names(term, url) for term in strong):
        score += 4
        signals.append("field_in_url")
    elif matches_field_text(link.text, related) or any(_names(t, url) for t in related):
        # The neighbourhood, which V2-12 says is a candidate and never a match.
        score += 1
        signals.append("related_field_only")

    named = degree_level_named(link.url) or degree_level_named(f"/{text}/")
    if named == str(intent.degree):
        score += 3
        signals.append("degree_matches")
    elif named is not None:
        # An outright rejection, not a penalty — the same rule V2-13's
        # prefilter applies. A master's page is not a weak bachelor lead, and
        # a strong field match in its link text must not buy it a place.
        return 0, ["other_degree_level"]

    if any(word in text or _names(word, url) for word in _SECTION_WORDS):
        score += 2
        signals.append("education_section")

    return score, signals


def navigation_candidates(
    html: str,
    base_url: str,
    intent: DiscoveryIntent,
    *,
    limit: int = DEFAULT_HOP_LIMIT,
) -> tuple[SourcedCandidate, ...]:
    """Links worth following from this page, best first, as fusion input.

    Emitted under ``CATALOGUE_WALKER`` so V2-16 merges them with search results
    and keeps both attributions when the two generators agree — which is the
    strongest signal fusion can produce and the reason to have both.
    """
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")

    scored = []
    for link in links_from(html, base_url):
        score, signals = _score(link, intent)
        if score <= 0:
            # A link with nothing to recommend it is navigation chrome. Keeping
            # it would hand fusion a hundred rows of footer.
            continue
        scored.append((score, link, signals))

    scored.sort(key=lambda row: (-row[0], row[1].url))
    return tuple(
        SourcedCandidate(
            url=link.url,
            generator=Generator.CATALOGUE_WALKER,
            rank=rank,
            title=link.text,
        )
        for rank, (_, link, _signals) in enumerate(scored[:limit], start=1)
    )
