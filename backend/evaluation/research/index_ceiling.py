"""The ceiling of an own index: are the gold and evidence pages in a sitemap, or linked?

Free-search map, ticket 04 (``docs/process/wayfinder/free-search/issues/04-…``).
An own index can only return what it has crawled. Before building one (ticket
05), this measures, for the development gold programme pages and the knowledge
base's evidence URLs, whether each target is

- ``in_sitemap_bounded``: listed in a sitemap document the product's own
  ``SitemapReader`` reads under its bounds (12 documents, news/events trimmed,
  depth 3) from the institution's homepage;
- ``in_sitemap_any``: listed in any sitemap document at all - the homepage
  host's tree read without the document cap or the trim, plus the tree each
  other target host declares in its robots.txt - up to ``MAX_SITEMAP_URLS``;
- ``linked_2hops``: linked from the homepage (hop 1) or from a page the
  homepage links through a study / programme / admissions anchor (hop 2),
  reading at most ``CRAWL_BUDGET`` pages per homepage; for a target reached at
  hop 2 the row names the hop-1 page that links it (``hop1_parent``), that
  page's homepage anchor text (``hop1_anchor``) and its rank among the
  homepage's programme-ish links under ``programmeish`` (``hop1_rank`` of
  ``hop1_of``, with ``hop1_score``) - IC-2, NEXT_CYCLES_2026-10-22 §3;
- ``twin_declared``: an ``hreflang`` twin the target page declares is itself
  in a sitemap or linked (the index would hold the twin, and the twin names
  the target);

and, for each programme page read, whether its ``<title>`` or ``<h1>`` names
the ontology's localized alias of the field (``localized_aliases_in``), so a
text index would match the R5 query without a URL lexicon.

Every read goes through the production ``Fetcher``: our user agent, robots.txt
(wildcards included) and its Crawl-delay. Nothing is retried around a
refusal; a refused host is recorded as ``host_refused``. No search provider is
called. Development evidence only: the four development corpora and the
knowledge base; a heldout case is refused and a dev5 university's per-URL rows
are left out of the written report (aggregates only).

Run from ``backend``::

    python -m evaluation.research.index_ceiling --out <report.json> --markdown <tables.md>

From an agent sandbox whose only way out is an HTTPS proxy, add
``--trust-env-proxy`` (the Fetcher's explicit opt-in, as in
``scripts/verify_evidence.py``). ``--refused-from <report.json>`` re-runs only
the sites an earlier report recorded as refused (the self-hosted runner job).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import tempfile
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from lxml import html as lxml_html

from app.adapters.discovery.live_discovery import (
    MAX_SITEMAP_URLS,
    SITEMAP_FALLBACK_PATHS,
    DiscoveryTrace,
    SitemapReader,
    _resolve_loc,
    _trimmed_sitemap,
    canonical_url,
    declared_alternates,
    decode_sitemap,
    parse_sitemap,
    parse_sitemap_directives,
    registrable_domain,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.page_classifier import localized_alias_flags
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.navigation import (
    _ADMISSION_WORDS,
    _SECTION_WORDS,
    NavigationLink,
    _score,
    links_from,
    study_section_label,
)
from app.adapters.search.ontology import country_languages, localized_aliases_in
from app.adapters.url_canonical import invalid_url_reason
from app.domain.enums import DegreeLevel, FetchOutcome

from .metrics import _page_forms

DATA = Path(__file__).parent / "data"
#: The development corpora (ticket 04: "development gold"), set name -> file.
DEV_SETS = {
    "cohort": DATA / "ground_truth.reviewed11.json",
    "dev2": DATA / "dev2.draft3.json",
    "dev3": DATA / "dev3.draft3.json",
    "dev4": DATA / "dev4.draft3.json",
}
KB_FILES = (
    Path(__file__).parents[2] / "app" / "knowledge" / "kb_cs_bachelor.json",
    Path(__file__).parents[2] / "app" / "knowledge" / "kb_imported_dev.json",
)
SEED_PATH = Path(__file__).parents[2] / "app" / "catalogue" / "unimatch_top500_seed.json"

#: The heldout nine: never measured, never named in a row.
HELDOUT_CASES = frozenset("nu metu sabanci charles masaryk tum tartu polimi vilnius".split())
HELDOUT_DOMAINS = frozenset(
    "nu.edu.kz metu.edu.tr sabanciuniv.edu cuni.cz muni.cz tum.de ut.ee polimi.it vu.lt".split()
)
#: dev5 is design-blind: its universities count in aggregates, never in a row.
DEV5_DOMAINS = frozenset(
    "kbtu.edu.kz satbayev.university astanait.edu.kz hacettepe.edu.tr bilkent.edu.tr "
    "yildiz.edu.tr upol.cz zcu.cz tu-dresden.de lmu.de unipd.it uniroma1.it "
    "vilniustech.lt".split()
)

#: Pages read per homepage for the two-hop reach (the product's per-university budget).
CRAWL_BUDGET = 60
#: Sitemap documents read per host when unbounded. The product reads 12; this
#: is a safety stop, recorded when reached (``documents_capped``).
UNBOUNDED_DOCUMENTS = 150
#: How deep an index may nest when unbounded (the product stops at 3).
UNBOUNDED_DEPTH = 6

#: The knowledge base's questions as the ticket tables them.
KB_QUESTIONS = ("programme", "english", "gpa", "deadline", "tuition", "scholarship")
_FACT_QUESTION = {
    "english": "english",
    "gpa": "gpa",
    "deadline": "deadline",
    "tuition": "tuition",
    "scholarship_exists": "scholarship",
    "scholarship_international": "scholarship",
}

#: Homepage hosts that are not ``www.<domain>`` (observed by the capture
#: harness, ``evaluation.research.live``: DEV2_HOSTS / DEV4_HOSTS).
_BARE_HOSTS = frozenset(
    "ethz.ch uba.ar uct.ac.za taltech.ee ktu.edu bogazici.edu.tr itu.edu.tr".split()
)
#: Cohort homepages as the curated registry holds them (``cohort_entry``).
_REGISTRY = (
    Path(__file__).parents[2] / "app" / "adapters" / "discovery" / ("institution_registry.json")
)


# --- inputs -------------------------------------------------------------------


@dataclass
class Site:
    """One institution's homepage, the root of its sitemaps and of the two-hop crawl."""

    key: str
    homepage: str
    domain: str
    country: str
    #: dev5 / blind: aggregated, never written as a row.
    blind: bool = False


@dataclass
class Target:
    """One URL to look for, and where it is counted."""

    url: str
    site: str
    #: ``cohort`` / ``dev2`` / ``dev3`` / ``dev4`` / ``kb``.
    group: str
    #: The case id, or the KB seed id.
    case: str
    #: ``gold`` / ``related`` for a development page; the KB question(s) otherwise.
    kinds: tuple[str, ...]


def _homepage_for_domain(domain: str) -> str:
    host = domain if domain in _BARE_HOSTS else f"www.{domain}"
    return f"https://{host}/"


def _registry_homepages() -> dict[str, str]:
    try:
        rows = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        host = urlparse(row.get("homepage") or "").hostname or ""
        if host:
            out[registrable_domain(host)] = row["homepage"]
    return out


def load_dev_targets(
    sets: Iterable[str] = DEV_SETS, paths: dict[str, Path] | None = None
) -> tuple[dict[str, Site], list[Target]]:
    """The development cases' sites and their gold (or, if unknown, related) pages."""
    paths = paths or DEV_SETS
    registry = _registry_homepages()
    sites: dict[str, Site] = {}
    targets: list[Target] = []
    for set_name in sets:
        corpus = json.loads(paths[set_name].read_text(encoding="utf-8"))
        for case in corpus["cases"]:
            case_id = case["id"]
            if case_id in HELDOUT_CASES or case["domain"] in HELDOUT_DOMAINS:
                raise ValueError(f"refusing a heldout case in {paths[set_name].name}")
            domain = case["domain"]
            homepage = registry.get(domain) if set_name == "cohort" else None
            sites[case_id] = Site(
                key=case_id,
                homepage=homepage or _homepage_for_domain(domain),
                domain=domain,
                country=case.get("country") or "",
            )
            urls = [(u, "gold") for u in case.get("programme_urls") or []]
            if not urls:
                urls = [(u, "related") for u in case.get("related_programme_urls") or []]
            for url, kind in urls:
                targets.append(Target(url, case_id, set_name, case_id, (kind,)))
    return sites, targets


def _kb_urls(entry: dict[str, Any]) -> dict[str, set[str]]:
    """Question -> the entry's evidence URLs (programme, facts, not_applicable)."""
    out: dict[str, set[str]] = defaultdict(set)
    programme = entry.get("programme") or {}
    for url in programme.get("urls") or []:
        out["programme"].add(url)
    for evidence in programme.get("evidence") or []:
        if evidence.get("url"):
            out["programme"].add(evidence["url"])
    for key, facts in (entry.get("facts") or {}).items():
        question = _FACT_QUESTION.get(key)
        for fact in facts or []:
            if question and fact.get("source_url"):
                out[question].add(fact["source_url"])
    for row in entry.get("not_applicable") or []:
        question = _FACT_QUESTION.get(str(row.get("question") or ""), "")
        question = question or str(row.get("question") or "")
        if question in KB_QUESTIONS and row.get("source_url"):
            out[question].add(row["source_url"])
    return out


def load_kb_targets(
    paths: Iterable[Path] = KB_FILES, seed_path: Path = SEED_PATH
) -> tuple[dict[str, Site], list[Target]]:
    """The knowledge base's evidence URLs per entry, deduplicated across files."""
    try:
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        official = {r["seed_id"]: r.get("official_site") for r in seed["universities"]}
    except (OSError, ValueError, KeyError):
        official = {}
    sites: dict[str, Site] = {}
    urls: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        for seed_id, entry in document["entries"].items():
            domain = entry.get("official_domain") or ""
            if not domain or domain in HELDOUT_DOMAINS:
                continue
            if seed_id not in sites:
                site = official.get(seed_id)
                sites[seed_id] = Site(
                    key=seed_id,
                    homepage=site or _homepage_for_domain(domain),
                    domain=domain,
                    country=entry.get("country") or "",
                    blind=domain in DEV5_DOMAINS,
                )
            for question, found in _kb_urls(entry).items():
                for url in found:
                    urls[(seed_id, url)].add(question)
    targets = [
        Target(url, seed_id, "kb", seed_id, tuple(q for q in KB_QUESTIONS if q in questions))
        for (seed_id, url), questions in sorted(urls.items())
    ]
    return sites, targets


# --- URL forms ----------------------------------------------------------------


def page_keys(url: str) -> tuple[set[str], set[str]]:
    """``metrics._page_forms`` of the URL as production canonicalises it (``http`` -> ``https``).

    A URL that cannot be requested (a non-numeric "port") has no forms.
    """
    if invalid_url_reason(url) is not None:
        return set(), set()
    return _page_forms(canonical_url(url), None)


class FormIndex:
    """Which listed (or linked) URL a target matches, up to a canonical variant.

    The same rule as ``metrics.same_programme_page``: the forms as written,
    or one side without its intake-year segment.
    """

    def __init__(self) -> None:
        self.written: dict[str, str] = {}
        self.yearless: dict[str, str] = {}

    def add(self, url: str, where: str) -> None:
        written, yearless = page_keys(url)
        for form in written:
            self.written.setdefault(form, where)
        for form in yearless:
            self.yearless.setdefault(form, where)

    def find(self, url: str) -> str | None:
        written, yearless = page_keys(url)
        for form in written:
            if form in self.written:
                return self.written[form]
            if form in self.yearless:
                return self.yearless[form]
        for form in yearless:
            if form in self.written:
                return self.written[form]
        return None

    def __len__(self) -> int:
        return len(self.written)


# --- sitemaps -------------------------------------------------------------------


def _lastmods(text: str) -> set[str]:
    """The ``loc`` of every ``<url>`` entry that carries a ``<lastmod>``."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return set()
    out = set()
    for entry in root.iter():
        if entry.tag.rpartition("}")[2].lower() != "url":
            continue
        loc = lastmod = ""
        for child in entry:
            name = child.tag.rpartition("}")[2].lower() if isinstance(child.tag, str) else ""
            if name == "loc":
                loc = (child.text or "").strip()
            elif name == "lastmod" and (child.text or "").strip():
                lastmod = child.text or ""
        if loc and lastmod:
            out.add(loc)
    return out


@dataclass
class SitemapTree:
    """One origin's sitemaps, read without the product's document cap or trim."""

    origin: str
    declared: list[str] = field(default_factory=list)
    #: Documents in the order the reader's queue met them: (url, depth, outcome).
    documents: list[dict[str, Any]] = field(default_factory=list)
    urls_seen: int = 0
    documents_capped: bool = False
    robots_outcome: str = ""
    index: FormIndex = field(default_factory=FormIndex)
    #: The listed URLs whose ``<url>`` entry carries a ``<lastmod>`` (ticket 07).
    with_lastmod: FormIndex = field(default_factory=FormIndex)


async def read_sitemap_tree(
    fetcher: Fetcher,
    origin: str,
    *,
    max_documents: int = UNBOUNDED_DOCUMENTS,
) -> SitemapTree:
    """Every sitemap document ``origin`` declares (or, failing that, the first conventional one).

    The product's queue order (robots.txt declarations first, children appended
    as met), with no trim and no 12-document cap; stops at ``max_documents``
    or ``MAX_SITEMAP_URLS``. A document's ordinal is its place in that order.
    """
    tree = SitemapTree(origin=origin)
    robots = await fetcher.get(urljoin(origin, "/robots.txt"))
    tree.robots_outcome = _outcome(robots)
    declared = parse_sitemap_directives(robots.text) if robots.ok else []
    tree.declared = declared
    queue: list[tuple[str, int]] = [(u, 0) for u in declared]
    fallbacks: set[str] = set()
    if not queue:
        queue = [(urljoin(origin, path), 0) for path in SITEMAP_FALLBACK_PATHS]
        fallbacks = {canonical_url(u) for u, _ in queue}
    seen: set[str] = set()
    while queue:
        if len(tree.documents) >= max_documents:
            tree.documents_capped = True
            break
        url, depth = queue.pop(0)
        url = canonical_url(url)
        if url in seen or depth > UNBOUNDED_DEPTH:
            continue
        seen.add(url)
        result = await fetcher.get(url)
        record: dict[str, Any] = {
            "url": url,
            "depth": depth,
            "ordinal": len(tree.documents) + 1,
            "trimmed": _trimmed_sitemap(url),
            "outcome": _outcome(result),
            "urls": 0,
        }
        tree.documents.append(record)
        if not result.ok:
            continue
        text = decode_sitemap(result.content, url)
        children, locations = parse_sitemap(text)
        base = result.final_url or url
        if url in fallbacks and (children or locations):
            queue = [item for item in queue if canonical_url(item[0]) not in fallbacks]
            fallbacks = set()
        queue.extend((_resolve_loc(base, child), depth + 1) for child in children)
        record["urls"] = len(locations)
        for loc in _lastmods(text):
            tree.with_lastmod.add(_resolve_loc(base, loc), url)
        for location in locations:
            tree.urls_seen += 1
            tree.index.add(_resolve_loc(base, location), url)
            if tree.urls_seen >= MAX_SITEMAP_URLS:
                tree.documents_capped = True
                return tree
    return tree


async def read_bounded(fetcher: Fetcher, site: Site) -> tuple[FormIndex, DiscoveryTrace]:
    """What the product's ``SitemapReader`` keeps under its own bounds (no relevance filter)."""
    trace = DiscoveryTrace(institution=site.key, domain=site.domain)
    pages = await SitemapReader(fetcher).collect(site.homepage, site.domain, trace)
    index = FormIndex()
    for url in pages:
        index.add(url, "bounded")
    return index, trace


# --- two hops from the homepage -------------------------------------------------

_PROGRAMMEISH_WORDS = tuple(dict.fromkeys((*_SECTION_WORDS, *_ADMISSION_WORDS)))
_PATH_WORD = re.compile(
    r"(?<![a-z])(?:stud(?:y|ies|ium|ieren|ier)|program(?:me)?s?|courses?|degrees?|"
    r"undergraduate|bachelors?|admissions?|apply|education|academics?|"
    r"formations?|opleidingen|onderwijs|carreras|grados?|cursos|corsi|studia|"
    r"kierunki|uddannelser|utbildning|koulutu\w*|lisans|bakalar\w*|ensino|"
    r"graduacao|pregrado|licence|laurea)(?![a-z])"
)


def programmeish(link_text: str, url: str, intent: DiscoveryIntent) -> int:
    """How strongly a homepage link names a study, programme or admissions section (0 = not)."""
    link = NavigationLink(url=url, text=link_text, parent_url="")
    score, _ = _score(link, intent)
    text = link_text.casefold()
    path = urlparse(url).path.casefold()
    if study_section_label(link_text, intent.languages, str(intent.degree)) is not None:
        score += 3
    if any(word in text for word in _PROGRAMMEISH_WORDS):
        score += 2
    if _PATH_WORD.search(path):
        score += 1
    return score


@dataclass(frozen=True)
class Hop1Link:
    """A homepage link the two-hop crawl queued: what it said and where it ranked."""

    #: The link's text as the homepage writes it (whitespace collapsed, capped).
    anchor: str
    #: 1-based place among the distinct programme-ish homepage links, best first.
    rank: int
    #: Its ``programmeish`` score.
    score: int
    #: How many distinct programme-ish links the homepage has (the queue length).
    of: int


#: Longest anchor text a report row keeps.
ANCHOR_CHARS = 200


@dataclass
class Crawl:
    homepage_outcome: str = ""
    #: Why the homepage was refused (403 / robots / timeout), or "".
    homepage_refusal: str = ""
    final_homepage: str = ""
    pages_read: int = 0
    #: Hop at which each linked URL was first met (1 = on the homepage).
    hops: dict[str, int] = field(default_factory=dict)
    index: FormIndex = field(default_factory=FormIndex)
    #: IC-2: a URL linked from a hop-1 page -> the first hop-1 page (in read
    #: order, so the best ranked) that links it.
    parents: FormIndex = field(default_factory=FormIndex)
    #: IC-2: each hop-1 page queued for reading -> its homepage anchor text and
    #: its rank under ``programmeish`` (1 = read first; distinct URLs).
    hop1: dict[str, Hop1Link] = field(default_factory=dict)


def safe_links(html: str, base: str) -> tuple[NavigationLink, ...]:
    """``links_from``. Kept as a name for the callers below.

    Real pages carry hrefs that once made ``links_from`` raise (2026-10-19: a
    host ending in a zero-width space; ``tel:``-like text after a colon read as
    a port). The product now drops those anchors itself (``page_link``).
    """
    return links_from(html, base)


async def crawl_two_hops(fetcher: Fetcher, site: Site, *, budget: int = CRAWL_BUDGET) -> Crawl:
    """Read the homepage, then its programme-ish links, best first, at most ``budget`` pages."""
    crawl = Crawl()
    homepage = await fetcher.get(site.homepage)
    if not homepage.ok and not _refusal_of(homepage):
        bare = f"https://{site.domain}/"
        if canonical_url(bare) != canonical_url(site.homepage):
            homepage = await fetcher.get(bare)
    crawl.homepage_outcome = _outcome(homepage)
    crawl.homepage_refusal = _refusal_of(homepage)
    crawl.pages_read = 1
    if not homepage.ok or not homepage.text:
        return crawl
    base = homepage.final_url or site.homepage
    crawl.final_homepage = base
    crawl.index.add(base, "hop0")
    intent = DiscoveryIntent(
        # The domain, not the case / seed id: the intent's applicant-data
        # guard refuses an id-shaped string ("qs2027-001").
        institution=site.domain,
        domain=site.domain,
        degree=DegreeLevel.BACHELOR,
        field="computer science",
        institution_country=site.country,
    )
    first = safe_links(homepage.text, base)
    ranked: list[tuple[int, str, str]] = []
    for link in first:
        crawl.index.add(link.url, "hop1")
        crawl.hops.setdefault(link.url, 1)
        score = programmeish(link.text, link.url, intent)
        if score > 0:
            ranked.append((score, link.url, link.text))
    # The sort key is unchanged by IC-2 (score, then URL); the stable sort keeps
    # the homepage's order among one URL's anchors, and the first is recorded.
    ranked.sort(key=lambda row: (-row[0], row[1]))
    distinct = list(dict.fromkeys(url for _, url, _ in ranked))
    for score, url, text in ranked:
        if url not in crawl.hop1:
            crawl.hop1[url] = Hop1Link(
                anchor=" ".join(text.split())[:ANCHOR_CHARS],
                rank=len(crawl.hop1) + 1,
                score=score,
                of=len(distinct),
            )
    for _, url, _ in ranked:
        if crawl.pages_read >= budget:
            break
        page = await fetcher.get(url)
        crawl.pages_read += 1
        if not page.ok or not page.text:
            continue
        for link in safe_links(page.text, page.final_url or url):
            crawl.index.add(link.url, "hop2")
            crawl.parents.add(link.url, url)
            crawl.hops.setdefault(link.url, 2)
    return crawl


# --- the target page itself -------------------------------------------------------

# SR2-09: the page's <html lang>, in linear time. The pattern this replaces,
# ``<html\b[^>]*\blang\s*=\s*["']?([A-Za-z-]+)`` searched from every ``<html``
# start to the next ``>`` and backtracked, quadratic on a page of unclosed
# ``<html `` tags. Its answer is the first ``<html`` tag (up to its ``>``, or the
# end) holding a ``lang=`` at all, and in it the *rightmost* ``lang=`` (the
# greedy ``[^>]*`` backtracks from the right). ``html_lang`` returns exactly that:
# each tag is consumed possessively once, and every ``lang=`` start in it is
# tried once, with a zero-width match so overlapping starts are all seen.
_HTML_OPEN_TAG = re.compile(r"<html\b[^>]*+", re.IGNORECASE)
_LANG_AT = re.compile(r"(?=\blang\s*=\s*[\"']?([A-Za-z-]+))", re.IGNORECASE)


def html_lang(head: str) -> str | None:
    """The raw ``lang`` value of the page's ``<html>`` tag, as the SR2-09 pattern found it."""
    for tag in _HTML_OPEN_TAG.finditer(head):
        last = None
        for match in _LANG_AT.finditer(tag.group(0)):
            last = match
        if last is not None:
            return last.group(1)
    return None


_UNSPACED = re.compile("[฀-๿ᄀ-ᇿ぀-ヿ㐀-䶿一-鿿가-힯]")


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def names_alias(text: str, alias: str) -> bool:
    """Whether ``text`` names ``alias`` as whole words (as a substring in an unspaced script)."""
    haystack, needle = _fold(text), _fold(alias)
    if not needle:
        return False
    if _UNSPACED.search(needle):
        return needle in haystack
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


def title_and_h1(html: str) -> tuple[str, str, str]:
    """A page's ``<title>``, first ``<h1>`` and ``<html lang>`` (primary subtag)."""
    lang = html_lang(html[:20_000])
    language = lang.split("-")[0].lower() if lang else ""
    try:
        tree = lxml_html.fromstring(html)
    except (ValueError, lxml_html.etree.ParserError):
        return "", "", language
    title = " ".join((tree.findtext(".//title") or "").split())
    h1s = tree.xpath("//h1")
    h1 = " ".join(h1s[0].text_content().split()) if h1s else ""
    return title, h1, language


def alias_match(title: str, h1: str, page_language: str, country: str) -> dict[str, Any]:
    """R5's test: does the title or h1 carry the field's localized alias?

    The page's own ``<html lang>`` first; a page that declares English or no
    language is tested in its country's languages (the R5 query's).
    """
    flags = localized_alias_flags()
    languages = [page_language] if page_language and page_language != "en" else []
    languages += [code for code in country_languages(country) if code != "en"]
    for language in dict.fromkeys(languages):
        aliases = localized_aliases_in("computer science", language, flags=flags)
        hit = next((a for a in aliases if names_alias(title, a) or names_alias(h1, a)), None)
        if hit:
            return {"language": language, "alias": hit, "match": True}
    return {"language": languages[0] if languages else "", "alias": "", "match": False}


# --- one run ----------------------------------------------------------------------


def _outcome(result: FetchResult) -> str:
    code = f" {result.status_code}" if result.status_code else ""
    return f"{result.outcome.value}{code}"


def _refusal_of(result: FetchResult) -> str:
    """403 / 401, robots.txt, or a timeout: the reads an own index could not make."""
    if result.outcome == FetchOutcome.HTTP_ERROR and result.status_code in (401, 403):
        return f"http {result.status_code}"
    if result.outcome == FetchOutcome.ROBOTS_DISALLOWED:
        return "robots"
    if result.outcome == FetchOutcome.ROBOTS_CRAWL_DELAY:
        return "crawl-delay"
    if result.outcome == FetchOutcome.TIMEOUT:
        return "timeout"
    return ""


def _origin(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


class Ceiling:
    """Shared state of one measuring run: one sitemap tree per origin, one crawl per site."""

    def __init__(self, fetcher: Fetcher, *, max_documents: int = UNBOUNDED_DOCUMENTS) -> None:
        self.fetcher = fetcher
        self.max_documents = max_documents
        self._trees: dict[str, asyncio.Task[SitemapTree]] = {}
        self._pages: dict[str, asyncio.Task[FetchResult]] = {}

    def tree(self, origin: str) -> asyncio.Task[SitemapTree]:
        if origin not in self._trees:
            self._trees[origin] = asyncio.ensure_future(
                read_sitemap_tree(self.fetcher, origin, max_documents=self.max_documents)
            )
        return self._trees[origin]

    def page(self, url: str) -> asyncio.Task[FetchResult]:
        if url not in self._pages:
            self._pages[url] = asyncio.ensure_future(self.fetcher.get(url))
        return self._pages[url]

    async def measure_site(self, site: Site, targets: list[Target]) -> dict[str, Any]:
        """Every column for one site's targets."""
        own_tree = await self.tree(_origin(site.homepage))
        bounded, trace = await read_bounded(self.fetcher, site)
        crawl = await crawl_two_hops(self.fetcher, site)
        homepage_refusal = crawl.homepage_refusal and f"homepage {crawl.homepage_refusal}"
        rows = []
        for target in targets:
            page = await self.page(target.url)
            final = page.final_url or target.url
            forms = [target.url] + (
                [final] if canonical_url(final) != canonical_url(target.url) else []
            )
            trees = [own_tree]
            for url in forms:
                origin = _origin(canonical_url(url))
                if origin != own_tree.origin:
                    trees.append(await self.tree(origin))
            listed_in = next(
                (doc for tree in trees for url in forms if (doc := tree.index.find(url))), None
            )
            document = next(
                (
                    d
                    for tree in trees
                    for d in tree.documents
                    if listed_in is not None and d["url"] == listed_in
                ),
                None,
            )
            linked = next((crawl.index.find(url) for url in forms if crawl.index.find(url)), None)
            parent = (
                next((p for url in forms if (p := crawl.parents.find(url))), None)
                if linked == "hop2"
                else None
            )
            via = crawl.hop1.get(parent) if parent else None
            row: dict[str, Any] = {
                "url": target.url,
                "group": target.group,
                "case": target.case,
                "kinds": list(target.kinds),
                "final_url": final if final != target.url else "",
                "read_outcome": _outcome(page),
                "in_sitemap_bounded": any(bounded.find(url) for url in forms),
                "in_sitemap_any": listed_in is not None,
                "sitemap_document": listed_in or "",
                "document_ordinal": document["ordinal"] if document else None,
                "document_depth": document["depth"] if document else None,
                "document_trimmed": bool(document and document["trimmed"]),
                "document_read_bounded": bool(listed_in and listed_in in trace.sitemaps_read),
                "lastmod": any(tree.with_lastmod.find(url) for tree in trees for url in forms)
                if listed_in
                else None,
                "linked_hop": {"hop0": 0, "hop1": 1, "hop2": 2}.get(linked or ""),
                # IC-2: for a target reached at hop 2, the hop-1 page that links
                # it, that page's homepage anchor and its programmeish rank.
                "hop1_parent": parent,
                "hop1_anchor": via.anchor if via else None,
                "hop1_rank": via.rank if via else None,
                "hop1_score": via.score if via else None,
                "hop1_of": via.of if via else None,
                "twins": [],
                "twin_declared": False,
                "host_refused": _refusal_of(page) or homepage_refusal,
            }
            if page.ok and page.text and not page.is_pdf:
                try:
                    twins = declared_alternates(final, page.text, site.domain)
                except Exception:  # a malformed alternate href: no twin recorded
                    twins = []
                row["twins"] = twins
                twin_trees = list(trees)
                for twin in twins:
                    origin = _origin(twin)
                    if all(t.origin != origin for t in twin_trees):
                        twin_trees.append(await self.tree(origin))
                row["twin_declared"] = any(
                    bounded.find(twin)
                    or crawl.index.find(twin)
                    or any(t.index.find(twin) for t in twin_trees)
                    for twin in twins
                )
                if target.group != "kb" or "programme" in target.kinds:
                    title, h1, language = title_and_h1(page.text)
                    row.update(
                        title=title[:200],
                        h1=h1[:200],
                        html_lang=language,
                        title_alias=alias_match(title, h1, language, site.country),
                    )
            rows.append(row)
        return {
            "site": site.key,
            "blind": site.blind,
            "homepage": site.homepage,
            "homepage_outcome": crawl.homepage_outcome,
            "homepage_refusal": crawl.homepage_refusal,
            "crawl_pages_read": crawl.pages_read,
            "linked_urls": len(crawl.index),
            "robots_outcome": own_tree.robots_outcome,
            "sitemaps_declared": len(own_tree.declared),
            "unbounded_documents": len(own_tree.documents),
            "unbounded_documents_capped": own_tree.documents_capped,
            #: Every sitemap document the Fetcher did not read, on the homepage
            #: host and the targets' hosts (too_large past MAX_BYTES, a .gz
            #: refused as unparseable, a 404 on a conventional guess...).
            "sitemap_documents_failed": [
                {"url": doc["url"], "outcome": doc["outcome"]}
                for origin in dict.fromkeys(
                    [own_tree.origin, *(_origin(canonical_url(t.url)) for t in targets)]
                )
                if origin in self._trees
                and self._trees[origin].done()
                and self._trees[origin].exception() is None
                for doc in self._trees[origin].result().documents
                if not doc["outcome"].startswith(("ok", "cached"))
            ],
            "unbounded_urls_seen": own_tree.urls_seen,
            "bounded_documents_read": len(trace.sitemaps_read),
            "bounded_urls_seen": trace.sitemap_urls_seen,
            "bounded_urls_kept": len(bounded),
            "rows": rows,
        }


def guard_reads(fetcher: Fetcher) -> None:
    """Turn an exception from one read into a failed result, so one URL cannot end the run.

    A homepage link carrying a zero-width space made httpx raise ``InvalidURL``
    out of ``Fetcher.get`` (2026-10-19 sandbox run). The Fetcher itself is not
    changed; the read is recorded as not fetched.
    """
    original = fetcher.get

    async def get(url: str, **kwargs: Any) -> FetchResult:
        try:
            return await original(url, **kwargs)
        except Exception as exc:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.UNPARSEABLE,
                error=f"not fetched: {type(exc).__name__}: {exc}"[:300],
                final_url=url,
            )

    fetcher.get = get  # type: ignore[method-assign]


async def measure(
    fetcher: Fetcher,
    sites: dict[str, Site],
    targets: list[Target],
    *,
    concurrency: int = 6,
    max_documents: int = UNBOUNDED_DOCUMENTS,
    progress: bool = False,
) -> list[dict[str, Any]]:
    """One record per site, sites measured ``concurrency`` at a time."""
    guard_reads(fetcher)
    ceiling = Ceiling(fetcher, max_documents=max_documents)
    by_site: dict[str, list[Target]] = defaultdict(list)
    for target in targets:
        by_site[target.site].append(target)
    gate = asyncio.Semaphore(concurrency)

    async def one(key: str) -> dict[str, Any]:
        async with gate:
            try:
                record = await ceiling.measure_site(sites[key], by_site[key])
            except Exception as exc:  # one site's failure must not end the run
                record = {
                    "site": key,
                    "blind": sites[key].blind,
                    "homepage": sites[key].homepage,
                    "homepage_outcome": f"not measured: {type(exc).__name__}",
                    "homepage_refusal": "",
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                    "rows": [],
                }
            if progress:
                found = sum(
                    1 for r in record["rows"] if r["in_sitemap_any"] or r["linked_hop"] is not None
                )
                print(
                    f"{key}\t{found}/{len(record['rows'])}\t{record['homepage_outcome']}",
                    flush=True,
                )
            return record

    return list(await asyncio.gather(*(one(key) for key in by_site)))


# --- tables -------------------------------------------------------------------------

COLUMNS = (
    "in_sitemap_bounded",
    "in_sitemap_any",
    "linked_2hops",
    "twin_declared",
    "ceiling",
    "ceiling_any",
    "host_refused",
)


def _flags(row: dict[str, Any]) -> dict[str, bool]:
    linked = row["linked_hop"] is not None
    return {
        "in_sitemap_bounded": row["in_sitemap_bounded"],
        "in_sitemap_any": row["in_sitemap_any"],
        "linked_2hops": linked,
        "twin_declared": row["twin_declared"],
        "ceiling": row["in_sitemap_bounded"] or linked,
        "ceiling_any": row["in_sitemap_any"] or linked or row["twin_declared"],
        "host_refused": bool(row["host_refused"]),
    }


def per_set(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per development set: cases whose gold page (any of them) meets each column."""
    cases: dict[tuple[str, str], dict[str, bool]] = {}
    alias: dict[tuple[str, str], bool | None] = {}
    for record in records:
        for row in record["rows"]:
            if row["group"] == "kb" or "gold" not in row["kinds"]:
                continue
            key = (row["group"], row["case"])
            flags = _flags(row)
            seen = cases.setdefault(key, dict.fromkeys(COLUMNS, False))
            for column in COLUMNS:
                seen[column] = seen[column] or flags[column]
            if "title_alias" in row:
                alias[key] = bool(alias.get(key)) or row["title_alias"]["match"]
    out: dict[str, dict[str, Any]] = {}
    for (group, case), flags in sorted(cases.items()):
        table = out.setdefault(group, {"cases_with_gold": 0, **dict.fromkeys(COLUMNS, 0)})
        table["cases_with_gold"] += 1
        for column in COLUMNS:
            table[column] += int(flags[column])
        if case in NON_ENGLISH_CASES:
            table["title_alias_tested"] = table.get("title_alias_tested", 0) + int(
                (group, case) in alias
            )
            table["title_alias_match"] = table.get("title_alias_match", 0) + int(
                bool(alias.get((group, case)))
            )
    return out


def per_question(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Per KB question (and all distinct URLs): URLs meeting each column."""
    out: dict[str, dict[str, int]] = {}
    for record in records:
        for row in record["rows"]:
            if row["group"] != "kb":
                continue
            flags = _flags(row)
            for question in (*row["kinds"], "all"):
                table = out.setdefault(question, {"urls": 0, **dict.fromkeys(COLUMNS, 0)})
                table["urls"] += 1
                for column in COLUMNS:
                    table[column] += int(flags[column])
            if "title_alias" in row:
                table = out["programme"]
                table["title_alias_match"] = table.get("title_alias_match", 0) + int(
                    row["title_alias"]["match"]
                )
    return out


#: Ticket 04's non-English development cases (title test).
NON_ENGLISH_CASES = frozenset(
    "psaclay kuleuven uio uba puc tec tsinghua ub chula ctu vut rwth kit unibo taltech ktu boun "
    "itu".split()
)


def markdown(records: list[dict[str, Any]]) -> str:
    """The two tables, the unreachable list and the per-language title rate."""
    lines = ["## Development gold, per set (cases)", ""]
    header = ["set", "cases_with_gold", *COLUMNS, "title_alias_match"]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for group, table in per_set(records).items():
        alias = (
            f"{table['title_alias_match']}/{table['title_alias_tested']}"
            if "title_alias_tested" in table
            else "-"
        )
        values = [group, str(table["cases_with_gold"]), *(str(table[c]) for c in COLUMNS), alias]
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", "## Knowledge base, per question (distinct URLs)", ""]
    header = ["question", "urls", *COLUMNS]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    questions = per_question(records)
    for question in (*KB_QUESTIONS, "all"):
        if question in questions:
            table = questions[question]
            lines.append(
                "| "
                + " | ".join([question, str(table["urls"]), *(str(table[c]) for c in COLUMNS)])
                + " |"
            )
    lines += ["", "## Gold pages in no sitemap and not linked within two hops", ""]
    for record in records:
        for row in record["rows"]:
            if row["group"] == "kb" or record["blind"]:
                continue
            if not row["in_sitemap_any"] and row["linked_hop"] is None:
                refused = f"; refused: {row['host_refused']}" if row["host_refused"] else ""
                lines.append(
                    f"- {row['group']} `{row['case']}` ({'/'.join(row['kinds'])}) {row['url']}"
                    f" - read {row['read_outcome']}{refused}"
                )
    hop2 = [
        row
        for record in records
        if not record["blind"]
        for row in record["rows"]
        if row["group"] != "kb" and row["linked_hop"] == 2
    ]
    if hop2:
        lines += [
            "",
            "## Development pages reached at hop 2: the hop-1 page, its anchor and rank",
            "",
            "| set | case | kind | page | hop-1 page | homepage anchor | rank / queue | score |",
            "|---|---|---|---|---|---|---:|---:|",
        ]
        for row in hop2:
            anchor = (row.get("hop1_anchor") or "").replace("|", "\\|")
            rank = (
                f"{row['hop1_rank']} / {row['hop1_of']}"
                if row.get("hop1_rank") is not None
                else "-"
            )
            score = row.get("hop1_score")
            lines.append(
                f"| {row['group']} | {row['case']} | {'/'.join(row['kinds'])} | {row['url']}"
                f" | {row.get('hop1_parent') or '-'} | {anchor or '-'} | {rank}"
                f" | {score if score is not None else '-'} |"
            )
    unread = [
        (record["site"], doc)
        for record in records
        if not record["blind"]
        for doc in record.get("sitemap_documents_failed", [])
        if not doc["outcome"].endswith(" 404")
    ]
    if unread:
        lines += ["", "## Sitemap documents the Fetcher did not read (404s left out)", ""]
        lines += [f"- `{site}` {doc['url']} - {doc['outcome']}" for site, doc in unread]
    failed = [r for r in records if r.get("error") and not r["blind"]]
    if failed:
        lines += ["", "## Sites not measured", ""]
        lines += [f"- `{r['site']}`: {r['error']}" for r in failed]
    lines += ["", "## Title / h1 alias match per language (development gold pages read)", ""]
    by_language: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for record in records:
        for row in record["rows"]:
            if row["group"] == "kb" or row["case"] not in NON_ENGLISH_CASES:
                continue
            if "title_alias" not in row:
                continue
            language = row["title_alias"]["language"] or "?"
            by_language[language][1] += 1
            by_language[language][0] += int(row["title_alias"]["match"])
    lines += ["| language | pages read | title/h1 names the alias |", "|---|---:|---:|"]
    for language, (hit, total) in sorted(by_language.items()):
        lines.append(f"| {language} | {total} | {hit} |")
    return "\n".join(lines) + "\n"


def written(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The report as written: a blind (dev5) university keeps its counts, loses its rows."""
    out = []
    for record in records:
        if record["blind"]:
            record = {**record, "rows": [], "homepage": "", "site": "blind"}
        out.append(record)
    return out


def refused_sites(report: list[dict[str, Any]]) -> set[str]:
    """The sites an earlier report recorded as refused (homepage or any target)."""
    return {
        record["site"]
        for record in report
        if record["site"] != "blind"
        and (any(row["host_refused"] for row in record["rows"]) or record.get("homepage_refusal"))
    }


async def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    sites: dict[str, Site] = {}
    targets: list[Target] = []
    if args.sets:
        dev_sites, dev_targets = load_dev_targets(args.sets)
        sites.update(dev_sites)
        targets += dev_targets
    if args.kb:
        kb_sites, kb_targets = load_kb_targets()
        sites.update(kb_sites)
        targets += kb_targets
    if args.cases:
        targets = [t for t in targets if t.case in set(args.cases)]
    if args.refused_from:
        keep = refused_sites(json.loads(Path(args.refused_from).read_text(encoding="utf-8")))
        targets = [t for t in targets if t.site in keep]
    with tempfile.TemporaryDirectory() as cache:
        fetcher = Fetcher(
            Path(cache),
            timeout=args.timeout,
            trust_env_proxy=args.trust_env_proxy,
        )
        async with fetcher:
            return await measure(
                fetcher,
                sites,
                targets,
                concurrency=args.concurrency,
                max_documents=args.max_documents,
                progress=True,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sets", nargs="*", default=list(DEV_SETS), choices=list(DEV_SETS))
    parser.add_argument("--no-kb", dest="kb", action="store_false")
    parser.add_argument("--cases", nargs="*", help="only these case ids / KB seed ids")
    parser.add_argument("--out", type=Path, required=True, help="the JSON report")
    parser.add_argument("--markdown", type=Path, help="the tables, as Markdown")
    parser.add_argument("--trust-env-proxy", action="store_true")
    parser.add_argument("--refused-from", help="only the sites this earlier report saw refused")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--max-documents", type=int, default=UNBOUNDED_DOCUMENTS)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    records = asyncio.run(run(args))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(written(records), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tables = markdown(records)
    if args.markdown:
        args.markdown.write_text(tables, encoding="utf-8")
    print(tables)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
