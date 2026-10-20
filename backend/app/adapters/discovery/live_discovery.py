"""Live candidate discovery against real university websites.

Discovery is **sitemap-first**. A university's own sitemap is a machine-readable
statement of what it publishes, which is a far better guide than guessing at
navigation: the previous heuristic followed the global menu and reached landing
pages, so live runs confirmed almost nothing.

The order is:

1. **Manual seeds** from the registry, where a human has verified which page is
   the programme catalogue, the admissions page, the fee page and so on.
2. **Sitemaps**, found through robots.txt hints and the conventional locations,
   including sitemap indexes and gzipped sitemaps.
3. **Navigation**, only as a fallback when neither produced anything.

Two rules hold throughout, and the tests pin both:

* A manual seed says *where to look*. It is never itself evidence of a
  requirement — the page still has to be fetched and classified, and the
  classifier decides. A seed that turns out to be a landing page yields
  nothing.
* Nothing off the institution's own registrable domain is followed.

Everything is bounded: how many sitemaps are read, how many URLs are kept, how
large a sitemap may be. Discovery on a large university site must not become a
crawl of it.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import statistics
import time
import unicodedata
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from html import unescape as html_unescape
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast
from urllib.parse import unquote, urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from app.adapters import fetching as _fetching
from app.adapters import page_classifier as _page_classifier
from app.adapters.base import Candidate, CandidateProgram, PageOutcome, RequirementsLead
from app.adapters.fetching import Fetcher, FetchResult, reading_as, same_source_site
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import (
    PageClassification,
    PageType,
    classify_page,
)
from app.adapters.search import intent as _intent_module
from app.adapters.search.ontology import (
    canonical_field,
    country_languages,
    load_ontology,
    localized_aliases,
    localized_aliases_in,
    localized_related_terms,
)
from app.adapters.url_canonical import page_link, strip_invisible_host
from app.domain.enums import DegreeLevel, FetchOutcome
from app.domain.site_identity import hosts_share_site
from app.domain.site_identity import registrable_domain as site_domain
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RankingEntry

if TYPE_CHECKING:  # pragma: no cover - the seam is only needed as an annotation
    from app.adapters.search.base import SearchProvider
    from app.adapters.search.navigation import SectionLabel

log = logging.getLogger("unimatch.discovery")

REGISTRY_PATH = Path(__file__).parent / "institution_registry.json"

# --- bounds ---------------------------------------------------------------
#: Sitemap documents read per institution, including nested index children.
MAX_SITEMAP_DOCUMENTS = 12
#: URLs read from all sitemaps combined. Scanning is cheap — the documents are
#: already fetched — so this is generous.
MAX_SITEMAP_URLS = 200_000
#: Candidate URLs *kept* per category. The live canary caught the reason these
#: are separate: with one combined bound, rug.nl filled the budget with 20,000
#: news articles from a research institute and the sitemap walk stopped before
#: reaching a single programme page. Relevance has to be decided per URL as it
#: is read, not after a prefix of the site has been collected.
MAX_CANDIDATES_PER_CATEGORY = 40
#: How deep a sitemap index may nest before we stop following it.
MAX_SITEMAP_DEPTH = 3
#: Candidate pages actually fetched per category.
MAX_PAGES_PER_CATEGORY = 3
#: Links scanned on a page during the navigation fallback.
MAX_LINKS_SCANNED = 400
#: Programme candidates fetched and classified before giving up on finding a
#: real programme page. Costs little: the pipeline fetches these pages anyway
#: and the fetcher caches, so a confirmed candidate is free downstream.
MAX_PROGRAM_CANDIDATES_CHECKED = 8
#: WF-17 trace bounds: provider queries kept per institution (six are allowed;
#: the rest is headroom for recovery passes), URLs kept per query, and pages
#: read kept with their verdicts.
SEARCH_RESULTS_TRACE_CAP = 24
SEARCH_RESULTS_PER_QUERY = 10
PAGES_READ_TRACE_CAP = 200
#: QB-1b: identity-recovery reads left to QB-1's first pass when a programme
#: page was already confirmed before it (walker, registry or sitemap). Recovery
#: then only looks for a twin or sibling of that page; Groningen's ``?lang=en``
#: twin was the first check in every run, and checks 4-8 were staff pages.
PRECONFIRMED_RECOVERY_CHECKS = 3
#: Whether step 7 re-judges the programme pages the search provider added.
#: Off: run 35721950650 measured recall 1/10 against 4/10 without it, and
#: precision fell too, so it removed correct pages rather than junk. Turn it
#: on only together with a capture that shows what it does.
CONFIRM_SEARCH_PROGRAMMES = False
#: Bounded content verification with backfill, unlike the older prune-only
#: experiment. Programme variants and unresolved degrees are rejected, and
#: matching catalogue links share the same candidate-read bound.
RECOVER_SEARCH_CANDIDATES = True
#: Whether search runs *before* the navigation fallback, and the fallback is
#: skipped when search found a programme page. Off: appending search after the
#: other generators is the measured default, and interleaving once cost whole
#: cases. Run 26 lost Groningen to ~50 navigation reads of faculty home pages
#: before search found the programme at once; this exists so that trade is
#: measured rather than argued. The benchmark harness flips it per capture.
SEARCH_BEFORE_NAVIGATION = False
#: Plan rule SO-1 (discovery analysis 2026-10-17 §0 #2, §1.4), off until a
#: paired run passes. Search costs no page read, yet it ran after sitemaps,
#: navigation, confirm and the walker; on a slow host the clock ended first
#: (one host: Crawl-delay 10 s, every read ~10 s, ``search_calls = 0`` in 8/8
#: repetitions). On: search runs before navigation and confirm when sitemaps
#: produced no programme candidate, or when the host is slow — robots.txt asks
#: a crawl delay of at least SLOW_HOST_SECONDS, or the median of the first
#: three reads is at least that long. A slow host also reads at most
#: SLOW_HOST_SITEMAP_DOCUMENTS sitemap documents and skips the walker. Order
#: only: the confirm predicate is unchanged. The trace records ``stage_order``.
#: The benchmark harness flips it per capture (``--cost-aware-search-order``).
COST_AWARE_SEARCH_ORDER = False
#: SO-1: a crawl delay or a median read at least this long makes a host slow.
SLOW_HOST_SECONDS = 5.0
#: SO-1: sitemap documents a slow host is asked for, robots.txt not counted.
SLOW_HOST_SITEMAP_DOCUMENTS = 3
#: SO-1: reads timed for the median.
SLOW_HOST_SAMPLE_READS = 3
#: SO-1's clock, a module attribute so a test can replace it.
_clock = time.monotonic
#: Plan rule SB-1 (structural analysis 2026-10-18 §2 F3, §3 change 1), off
#: until a paired run passes. Discovery had no stage budget and no stop
#: condition: 51 % of the clock went before the first query, ten of 35 cases
#: never reached the verify stage (UBC spent 78 s on navigation before its
#: first query, Imperial 96 s on confirm and walker reads, UNSW 111 s on
#: twelve reads), and after the walker confirmed Groningen's and TCD's pages
#: the run still read more navigation and walker pages. On: discovery stops
#: at DISCOVERY_DEADLINE_SECONDS or DISCOVERY_READ_CAP reads, whichever comes
#: first, and returns what it has confirmed, so the verify stage always runs.
#: A stage checks the budget before each read; no read is interrupted. Once
#: a programme page is confirmed the walker, the navigation fallback, the hop
#: roots and identity recovery stop, and no second query pass is sent; hop
#: roots are not opened while any programme candidate exists. A host whose
#: robots.txt or first sitemap document takes more than SLOW_HOST_SECONDS
#: (or that asks such a crawl delay) is searched right after its first
#: sitemap document, reads at most SLOW_HOST_SITEMAP_DOCUMENTS sitemap
#: documents and skips the walker (SO-1's order code). The trace records
#: ``stage_budget``: seconds and reads per stage and ``t_first_query``.
#: The benchmark harness flips it per capture (``--stage-budgets``).
STAGE_BUDGETS = True
#: SB-1: seconds of one institution's discovery, from its start.
DISCOVERY_DEADLINE_SECONDS = 55.0
#: SB-1: network reads one institution's discovery may make (of the case's 60).
DISCOVERY_READ_CAP = 28
#: SB-1: the stages the budget attributes seconds and reads to.
BUDGET_STAGES = ("sitemap", "navigation", "walker", "confirm", "search", "recovery")
#: SB-1b (wrong-claims analysis 2026-10-18 §3): SB-1 lost UCPH, and one
#: repetition each of Chula and Auckland, to one mechanism. Thirteen sitemap
#: reads spent 13 of the 28 reads, the walker spent the rest, and search —
#: the stage that confirmed all three pages in the off arm — was skipped for
#: the read cap although a query costs no read; or the first query left at
#: 34 s and slow provider answers let the deadline fall before the first
#: recovery read. Under STAGE_BUDGETS only: the read cap never skips search;
#: sitemap reads (robots.txt and the documents) are counted against their own
#: allowance, not the read cap; the first pass's identity recovery has a
#: reserve of RECOVERY_RESERVE_READS reads past a spent read cap, and past the
#: deadline when the deadline fell before any recovery read; and when nothing
#: is confirmed at SEARCH_LATEST_START_SECONDS, sitemaps, navigation and the
#: walker are cut and search starts.
#: SB-1b: the latest start of the first query while nothing is confirmed
#: (0.6 of DISCOVERY_DEADLINE_SECONDS).
SEARCH_LATEST_START_SECONDS = 33.0
#: SB-1b: sitemap reads of one institution, robots.txt included; the
#: document cap already bounds them, this keeps them off the read cap.
DISCOVERY_SITEMAP_ALLOWANCE = MAX_SITEMAP_DOCUMENTS + 1
#: SB-1b: identity-recovery reads the first search pass may make past a
#: spent budget (QB-1b's PRECONFIRMED_RECOVERY_CHECKS).
RECOVERY_RESERVE_READS = PRECONFIRMED_RECOVERY_CHECKS
#: Plan rule PL-1 (programme-page misses on the 2026-10-18 clean baseline),
#: off until a paired run passes. In five development misses the provider
#: *returned* the programme page and identity recovery never read it, for one
#: of two bookkeeping reasons, never for its ranking or its predicate:
#: (a) links followed from a refused search result (``search-catalogue``
#: leads, queued ahead of the rest) spent the MAX_PROGRAM_CANDIDATES_CHECKED
#: checks the provider's own results share with them — a course page's four
#: course links took checks 5-8 while the programme page was the next
#: provider result (CTU 2/4, IIT Delhi 1/4); (b) SB-1b's reserve past the
#: deadline opens only when the deadline fell before any recovery read, so a
#: first pass that started at 50 s read one or two leads and stopped one
#: short of the page (UiO, UBA 1/4 each). On: (a) followed links get their
#: own MAX_PROGRAM_CANDIDATES_CHECKED checks and no longer use the provider
#: results' ones, and (b) past the deadline the first pass may read until it
#: has made RECOVERY_RESERVE_READS recovery reads in all, in time or not.
#: Both only let recovery read *after* the point where it stops today; the
#: order of reads, the confirm predicate and the single stop at the first
#: confirmed page are unchanged, and every read still goes through the
#: Fetcher, the read ledger and the case time budget (TB-1). The benchmark
#: harness flips it per capture (``--provider-lead-floor``).
PROVIDER_LEAD_FLOOR = False
#: PL-1(a): who queued a recovery lead taken from a refused result's own links.
SEARCH_CATALOGUE_LEAD = "search-catalogue"
#: Replay plan 2026-10-19 UA-1 (loop id CA-1b), on by default: when no
#: read of the institution's own entry points succeeded — robots.txt, every
#: sitemap probe, the homepage and the rest of the navigation fallback all
#: failed (a cache hit is a success) — identity recovery may still read search
#: leads but confirms none of them as *the* programme page. An accepted lead
#: is kept as ``DiscoveryTrace.unresolved_access``, discovery ends with the
#: programme unresolved and ``trace.errors`` says why (ENTRY_UNREADABLE_LINE).
#: The condition is a count — zero successful entry reads — and names no host,
#: path or word, so it cannot fire on a site that answers. The benchmark
#: harness flips it per capture (``--abstain-on-unreadable-entry``).
ABSTAIN_ON_UNREADABLE_ENTRY = True
#: UA-1: the one trace line an abstention adds.
ENTRY_UNREADABLE_LINE = "entry hosts unreadable: no programme page confirmed"
#: Experiment ER-04, off until measured: a search candidate on a host that
#: already refused this run's fetcher outright (401/403, robots.txt
#: unreachable, stalled) does not take one of the programme-page slots.
#: The 2026-09-27 Toronto trace spent all three slots on future.utoronto.ca
#: after that host had answered 403 to every read; a reachable campus host
#: was never tried. The benchmark harness flips it per capture.
SKIP_REFUSED_SEARCH_HOSTS = False
#: Experiment ER-07, off until measured: one of the programme-page slots is
#: kept for the best candidate the navigation hop found. Search results fill
#: the others. ER-05 (2026-09-27) found hop candidates are appended after
#: search and never reach a slot, so KAIST's undergraduate-admission page,
#: linked from the department's own navigation, was never opened.
NAVIGATION_SLOT = False
#: Experiment ER-09 (expert trace 2026-10-04), on since paired runs 37240128388
#: and 37242447357 (owner approved 2026-10-05); False turns it off.
#: When the applicant named a subject, the navigation fallback takes a link as
#: a programme lead only if its URL or its own text names that subject.
#: Groningen's bachelor hub links brochures, open days, campus tours and
#: "webklassen" under the same path as its programmes; they filled every
#: programme slot, the confirm stage spent its reads rejecting them, and the
#: run timed out before reaching /bachelors/computing-science.
NAVIGATION_FIELD_LEADS = True
#: Pages walked during the navigation fallback. Universities routinely nest
#: "Degree programmes" -> "Bachelor programmes" -> a programme, so one hop is
#: not enough; an unbounded walk would be a crawl.
MAX_FALLBACK_PAGES = 5
#: Plan v3 rule R4 (LC-1, ticket 20; owner decisions Q1–Q5), off until a paired
#: run passes. On the development sites the local-language programme page was
#: never *listed* by any stage (puc, uio, uba, kuleuven, psaclay-fr), yet each
#: homepage links the catalogue that holds it in one or two hops and in its own
#: words: uc.cl "Carreras de pregrado" -> ``admision.uc.cl/carreras``, uio.no
#: "Studier" -> "Finn studier" ``/studier/program/``, kuleuven.be
#: ``onderwijsaanbod.``. The navigation fallback kept a homepage link only when
#: its URL categorised, and ``categorise_url`` knew no local catalogue root.
#: On, three things, one flag (20 Q5):
#: (i) a link on the homepage, or on a page reached from it this way, whose
#: label is a study-section or catalogue word in a language of the
#: institution's country (``navigation.study_section_label``; the country is
#: the institution's, never the applicant's) becomes a catalogue lead whatever
#: its URL says, at most LOCAL_SECTION_MAX_HOPS hops from the homepage and
#: LOCAL_SECTION_LINKS_PER_PAGE per page, behind the leads today's walk already
#: queues and inside MAX_FALLBACK_PAGES and the SB-1 budget; a page reached
#: only by its label is read and classified first, and one that reads as news,
#: admissions, fees or the like is dropped (``not_program_catalog``);
#: (ii) local listing words are URL signals (``_LOCAL_LISTING_SIGNALS``):
#: ``/carreras/``, ``/formation/``, ``/studier/``, ``/opleidingen/n`` … as
#: catalogue roots and ``/<word>/<slug>`` as programme paths;
#: (iii) a link from such a page to another host on the institution's own
#: registrable domain whose label or path is a catalogue word (a catalogue
#: host) has that host's own sitemap read — robots.txt, else ``/sitemap.xml``
#: or ``/wp-sitemap.xml`` — for at most CATALOGUE_HOST_SITEMAP_DOCUMENTS
#: documents, programme-named children first, inside the SB-1 sitemap
#: allowance; its URLs pass the same ``keep()`` and the same confirm as the
#: main sitemap's. A host on another registrable domain stays DI-1's case
#: (20 Q4). The confirm predicate is unchanged. The trace records the section
#: links in ``kept_by_link_text`` and the host in ``catalogue_host``. The
#: benchmark harness flips it per capture (``--local-catalogue-entry``).
LOCAL_CATALOGUE_ENTRY = False
#: R4: hops from the homepage a section link may lead (homepage -> section ->
#: catalogue); a label on the second page is the last one followed.
LOCAL_SECTION_MAX_HOPS = 2
#: R4: section links taken from one page, catalogue words before section words.
LOCAL_SECTION_LINKS_PER_PAGE = 2
#: R4: the score a section link competes with for the catalogue slots.
LOCAL_SECTION_LINK_SCORE = 4
#: R4: sitemap documents read on the one catalogue host, robots.txt aside.
CATALOGUE_HOST_SITEMAP_DOCUMENTS = 3
#: R4: where a catalogue host's sitemap is looked for when robots.txt names none.
CATALOGUE_HOST_SITEMAP_PATHS = ("/sitemap.xml", "/wp-sitemap.xml")
#: R4: a catalogue host's sitemap child that names a study offer, in any language.
_CATALOGUE_HOST_CHILD_FIRST = re.compile(
    r"(?<![a-z])(?:program|carrera|grado|stud(?:y|ies|ier|ium|ien)|course|curso|corsi|degree"
    r"|formation|opleiding|uddannelse|utbildning|koulutus|kierunk|bolum|oppekava|curricul)"
)
#: R4: a catalogue host's sitemap child that lists another level's programmes
#: (``magister-sitemap.xml``, ``programas_postgrado-sitemap.xml``); skipped for
#: a bachelor's request.
_GRADUATE_SITEMAP_NAME = re.compile(
    r"(?<![a-z])(?:pos|post)[-_]?grad|magist|maestr|master|mestrad|doctor|doktor|phd"
)

#: Rule NS-1 "homepage hop reads" (NO_SEARCH_FLOOR_2026-10-21 §5), off until
#: the no-search paired runs pass. With no search provider, the navigation
#: fallback read the homepage and stopped: it queues a homepage link only when
#: ``categorise_url`` names its URL, and the best study link often leads to
#: another host on the institution's own registrable domain with a URL that
#: names nothing, so 46–53 of the 60 reads went unspent. On: once the homepage
#: was read, today's queue is empty and no programme page is selected, the
#: homepage's links are ranked by the product's own link score
#: (``navigation._score``, + 3 for a ``study_section_label``, + 2 for a
#: ``_SECTION_WORDS`` / ``_ADMISSION_WORDS`` entry in the label) whatever their
#: URL's category; links on any host of the institution's registrable domain,
#: not excluded and naming no other degree level, are kept with a score above
#: 0, and the best HOMEPAGE_HOP_READ_CAP (ties by URL) are read as section
#: pages: a field-named link on them is a programme lead and a catalogue-shaped
#: one queues as today; one that reads as news, admissions or fees is dropped.
#: The hop reads have their own cap beside MAX_FALLBACK_PAGES and stay inside
#: the SB-1 budget, the 60-read ledger and the 120 s case clock; a refused
#: read is not retried. Structural only: no word is added. The trace records
#: ``homepage_hop_reads``. The benchmark harness flips it per capture
#: (``--homepage-hop-reads``). On by default since the 2026-10-20 no-search replay
#: with PC-1 (dev3 3→5, dev4 0→1 in both on columns; 0 wrong; knockout and the
#: recorded guard unchanged).
HOMEPAGE_HOP_READS = True
#: NS-1: homepage links read as hop pages, at most.
HOMEPAGE_HOP_READ_CAP = 5

#: Ticket PC-1 (NEXT_CYCLES_2026-10-22 §3, menu entry (D)), off until the
#: no-search paired runs pass. The clock that kept NS-1 off, read from
#: thirteen dev3 no-search captures of 2026-10-20: the homepage host's one
#: declared sitemap document took 19.6–21.4 s against the fetcher's 20 s
#: exchange deadline. In seven columns it overran, the fetcher's stall memory
#: closed the host for the run, the navigation fallback's homepage read was
#: refused without a request, and the case ended at 22 s with 57 of its 60
#: reads unused; in the six where it arrived in time, navigation ran. The size of
#: the document (247 URLs) and the slow-host verdict (the walker skipped) cut
#: nothing; the SB-1 deadline never fell. With no provider configured nothing
#: else bounds the stage either: SB-1b ends it at SEARCH_LATEST_START_SECONDS
#: only to start search, so the stage ran to the 55 s deadline on hosts with
#: many documents. On, with no search provider configured, one flag:
#: (i) no sitemap document starts once discovery has run
#: SITEMAP_STAGE_MAX_SECONDS, the time SB-1b ends the stage when a provider
#: is configured; (ii) a sitemap document whose exchange overruns the
#: fetcher's deadline ends the sitemap stage and is skipped alone
#: (``Fetcher.mark_stall_local``): its host is not recorded as stalled, so
#: navigation still reads the homepage. No read is interrupted; robots,
#: pacing, the privacy guard, the 60-read ledger and the 120 s case clock
#: apply as before. Structural only (a time and the scope of one verdict); no
#: word is added. With a provider configured nothing changes. The benchmark
#: harness flips it per capture (``--sitemap-stage-cap``). On by default since
#: the 2026-10-20 no-search replay with NS-1b (same result as NS-1b's line).
SITEMAP_STAGE_CAP = True
#: Ticket SG-1 (NEXT_CYCLES_2026-10-22 §3), off until the no-search paired
#: runs pass. When robots.txt names no sitemap, discovery guesses the
#: conventional locations (SITEMAP_FALLBACK_PATHS), one read each; on a host
#: that asks a crawl delay every guess costs that delay, so four guesses cost
#: 6–8 s on most such hosts and ~30 s on a Crawl-delay 10 host. On: when
#: robots.txt names no sitemap and the host asks a crawl delay of at least
#: SLOW_HOST_SECONDS, only the first location (``/sitemap.xml``) is guessed;
#: on any host, guessing stops after SITEMAP_GUESS_MAX_404 consecutive guesses
#: answered 404. A declared sitemap and the children of a guess that answered
#: are read as before. Structural only: no path and no word is added. The trace
#: records an ``SG-1:`` line in ``errors`` when a guess is skipped. The
#: benchmark harness flips it per capture (``--sitemap-guess-cap``).
SITEMAP_GUESS_RULE = False
#: SG-1: conventional locations guessed at most (today's four; all of them).
SITEMAP_GUESS_CAP = 4
#: SG-1: locations guessed on a host that asks a crawl delay ≥ SLOW_HOST_SECONDS.
SITEMAP_GUESS_SLOW_HOST_CAP = 1
#: SG-1: consecutive 404 guesses after which no further location is guessed.
SITEMAP_GUESS_MAX_404 = 2
#: PC-1: discovery seconds after which no sitemap document starts.
SITEMAP_STAGE_MAX_SECONDS = SEARCH_LATEST_START_SECONDS
#: PC-1: the trace line a stalled sitemap document adds.
SITEMAP_STALL_LINE = "PC-1: a sitemap document stalled; the sitemap stage ends, the host stays open"

#: Plan rule SM-1 (discovery analysis 2026-10-17 §0 #1, §1.3–§1.5), off until a
#: paired run passes. The sitemap stage read index children in file order under
#: the MAX_SITEMAP_DOCUMENTS cap and probed every conventional location even
#: after one answered: an index that lists post-sitemap1..24 before its page
#: and programme sitemaps had eleven post sitemaps (75 s) use the cap, and the
#: programme sitemap was never read; hosts at Crawl-delay 10 spent three reads
#: (30 s) on guaranteed 404s after /sitemap.xml had answered. On:
#: the probing stops at the first conventional location that parses to a
#: sitemap, and an index's children are read programme/study/course/page
#: first and news/post/event last, the last group skipped when the first
#: group alone fills the remaining cap. Read order only — every URL still
#: passes ``keep()`` and the confirm classifier. The benchmark harness flips it
#: per capture (``--sitemap-child-priority``).
SITEMAP_CHILD_PRIORITY = False
#: SM-1: an index child whose name says it lists programmes or static pages.
_SITEMAP_CHILD_FIRST = re.compile(r"program|programme|stud(?:y|ies)|course|degree|page|curricul")
#: SM-1: an index child whose name says it lists dated or taxonomy content.
#: Matched as a whole name token, so ``postgraduate`` is not ``post``.
_SITEMAP_CHILD_LAST = re.compile(
    r"(?<![a-z])(?:posts?|news|events?|announce\w*|blogs?|press|media|calendars?|tags?|authors?)"
    r"(?![a-z])"
)

#: Plan rule SM-2 (read budget analysis 2026-10-18 §3, §4 step 1.3), off until
#: a paired run passes. Chula spent 13 of its 60 reads on sitemaps and seven of
#: them were waste: two conventional locations probed after /sitemap.xml had
#: answered (both 404), and clipping x2, event-calendar, gallery and highlight
#: children, which list press cuttings, events and photos, never a programme.
#: SM-1 only reorders such children and skips them when programme sitemaps
#: alone fill the cap, and its news words do not cover gallery, clipping or
#: highlight. On: (i) the probing stops at the first conventional location
#: that parses to a sitemap (SM-1's rule, shared); (ii) a sitemap document,
#: declared or an index child, whose path or query names news, events,
#: galleries, media, blogs, press, clippings, highlights, posts or the like as
#: a whole word, and no programme word (``_SITEMAP_CHILD_FIRST``), is not read
#: and does not count against the document cap. The trace records each one.
#: The benchmark harness flips it per capture (``--sitemap-trim``).
SITEMAP_TRIM = True
#: SM-2: a sitemap document that lists dated, press or media content.
_SITEMAP_TRIM_NAME = re.compile(
    r"(?<![a-z])(?:posts?|news\w*|events?|calendars?|galler(?:y|ies)|media|blogs?|press"
    r"|clippings?|highlights?|photos?|videos?|stories|announce\w*|articles?|podcasts?"
    r"|tags?|authors?)(?![a-z])"
)


def _trimmed_sitemap(url: str) -> bool:
    """SM-2: whether a sitemap document lists news, events or media and no programmes."""
    parts = urlparse(url)
    name = f"{parts.path} {parts.query}".lower()
    return bool(_SITEMAP_TRIM_NAME.search(name)) and not _SITEMAP_CHILD_FIRST.search(name)


#: Plan rule LI-1, off until a paired run passed. Provenance: every LI-1 row
#: is re-sourced to a dictionary or a degree law, row by row, in
#: ``docs/process/HELDOUT_PROVENANCE_AUDIT_2026-10-20.md``. URL scoring and
#: field matching were English-only: a German catalogue path of the shape
#: ``/studium/studienangebot/<programme-slug>`` scored zero, the page subject
#: "Informatik" was rejected although the ontology records ``informatik`` as
#: computer science, an Italian ``laurea-magistrale`` slug was not a degree
#: slug, and nothing followed a local-language page to its English twin. On:
#: (i) ``with_strong_aliases``
#: also returns the ontology's localized aliases (including the entries marked
#: ``"flag": "LOCALIZED_IDENTITY"``), a few local programme-path words score as
#: programme pages, and ``degree_level_named`` knows the local degree words
#: whose level is certain (``_LOCALIZED_DEGREE_SLUGS``); (ii)
#: ``matches_field_text`` accepts a localized alias as the subject under the
#: same filler rule, so "Informatik" is computer science and
#: "Wirtschaftsinformatik" is not; (iii) a programme candidate read on the
#: institution's domain whose ``<html lang>`` is not English and that carries
#: ``<link rel="alternate" hreflang="en…">`` on the same registrable domain has
#: that alternate read once — through the Fetcher, inside the same read cap —
#: and classified like any page, beside the original. The benchmark harness
#: flips it per capture (``--localized-identity``).
#: On since paired runs 39068981447 (cohort, no change) and 39068982766 (dev2:
#: Paris-Saclay's licence informatique page found in every on repetition, never
#: off); owner delegation 2026-10-17. False turns it off.
LOCALIZED_IDENTITY = True
#: Plan v3 rule R2 (ST-1, stage 4(b); tickets 19 Q1-Q4, 03 Q3-Q4, 16 Q6), off
#: until a paired run passes. ``matches_field_text`` tested every word of a
#: programme title, so "Informatikk: programmering og systemarkitektur" (uio)
#: and "Bachelor in de informatica (Leuven) - Studieprogramma" (kuleuven) were
#: refused for their subtitle and place, while the applicant's *own* words
#: were accepted with no look at the rest, which is how "Business Science
#: specialising in Computer Science" (uct) and "Mathematics and Computer
#: Science" (imperial) passed. On: (i) only the **subject head** is tested,
#: the text before a ``:`` / `` - `` / `` – `` subtitle (a head of degree or
#: form words only gives way to the next part); (ii) a bracketed place
#: (``_title_places``: the seed rows' cities and countries; CG-1 still refuses
#: a foreign campus), a bracketed single form word ("(Hons)", "(International)"),
#: a form word (``_SUBJECT_FORM_FILLER``: "Studieprogramma", "专业", "学科", …)
#: and an award name ("Bachelor of Science", "Bachelor of Engineering") are
#: filler; (iii) a **related field** (``_RELATED_FIELD_WORDS`` and the
#: ontology's ``related_not_equivalent`` heads) joined to the field in one of
#: the listed shapes — before it ("Business Science specialising in …",
#: "Mathematics and …") or after it with "and" ("… and Economics") — makes
#: the title a related programme, for aliases and the applicant's own words
#: alike; "<field> and Engineering" is the field itself (19-Q4 as amended:
#: Delft's and IIT Delhi's "Computer Science and Engineering"). ``profile_rejects`` refuses such a page with a related verdict and
#: discovery records it as ``DiscoveryTrace.related_programmes`` (16-Q6); the
#: product payload does not change. R2b (paired runs 39126143581-39126149746):
#: a related verdict in the confirm stage, before anything is confirmed, gives
#: the next read to the field's own page beside it (``_queue_field_sibling``:
#: Imperial's ``computing-beng`` beside ``mathematics-computer-science-beng``),
#: and the evidence stage makes no English or deadline claim from a page only
#: topic search reached that is silent on its degree (UCT's language page).
#: The benchmark harness flips it per capture (``--subject-title-shapes``).
#: On by default since the R2b paired runs; False turns it off.
SUBJECT_TITLE_SHAPES = (
    True  # on: R2b runs 39129349634 / 351411 / 352826 / 354412 (imperial, uio, unsw, kit; 0 losses)
)
#: Plan rule DI-1 (evidence analysis 2026-10-17 §0 #5, §4 rank 5), off until a
#: paired run passes. Institution identity was one registrable domain, and
#: every official-domain reader — ``same_institution`` here and in the walker
#: (``off_domain``), ``is_official_domain``, ``verification_domains``, topic and
#: award search — rejected a university whose international admissions run on a
#: second one: Tsinghua publishes its deadline, fees and freshman scholarships on
#: ``international.join-tsinghua.edu.cn``, which ``www.tsinghua.edu.cn`` links
#: from its own admissions navigation (3 dev2 questions lost). On: discovery
#: reads the registry homepage once after the sitemaps (the disk cache serves
#: the navigation fallback's read of it), and when the homepage's header or
#: main navigation has links whose text names admissions
#: (``_ADMISSIONS_LINK_TEXT``) pointing to exactly ONE other registrable domain,
#: that domain becomes ``Candidate.extra_domains`` for the rest of the run;
#: every reader accepts it through ``Candidate.official_domains``. Never a known
#: third party (``_ADMISSIONS_HOST_DENYLIST``: application portals, social
#: networks, search engines, shorteners), never a government portal unless the
#: link text names the university; two candidate domains are ambiguous and add
#: none. Pages on the added domain are classified and extracted as usual. The
#: trace records the domain and the link that justified it
#: (``admissions_host``). The benchmark harness flips it per capture
#: (``--admissions-host-from-homepage``). False turns it off.
ADMISSIONS_HOST_FROM_HOMEPAGE = False
#: Plan rule CG-1 (wrong-claims analysis 2026-10-18 R-D2), off until a paired
#: run passes. UNSW's identity recovery confirmed "Bachelor of Science in
#: Computer Science (Bengaluru)" (``…-bengaluru``) for a Sydney request: the
#: ontology says YES to the subject, and no stage looks at the campus. On, the
#: shared confirm predicate (``profile_rejects``: confirm stage, added search
#: programmes, identity recovery, catalogue walker) refuses a page whose title,
#: subject or URL names a branch-campus place (``_BRANCH_CAMPUS_PLACES``) that
#: lies in another country than the institution's: a parenthesised place
#: ("(Bengaluru)"), "Malaysia campus", "campus Dubai", a trailing "– Dubai", a
#: URL segment that is the place or ends in ``-place``. The applicant's request
#: names no campus (the profile has no campus field), so a foreign campus is
#: never the one asked about. A domestic second campus is never refused (UBC
#: Okanagan and Vancouver are both in Canada, and Okanagan is not a branch
#: place); nor is a page when the institution's country is unknown. The
#: benchmark harness flips it per capture (``--campus-guard``). On by
#: default; False changes nothing.
CAMPUS_GUARD = True
#: CG-1: places where universities run branch campuses abroad, and the country
#: each lies in. A place is a refusal only outside its own country.
_BRANCH_CAMPUS_PLACES: dict[str, str] = {
    "bengaluru": "india",
    "bangalore": "india",
    "mumbai": "india",
    "gift city": "india",
    "india": "india",
    "malaysia": "malaysia",
    "kuala lumpur": "malaysia",
    "johor": "malaysia",
    "sarawak": "malaysia",
    "dubai": "united arab emirates",
    "abu dhabi": "united arab emirates",
    "ras al khaimah": "united arab emirates",
    "sharjah": "united arab emirates",
    "uae": "united arab emirates",
    "qatar": "qatar",
    "doha": "qatar",
    "singapore": "singapore",
    "china": "china",
    "ningbo": "china",
    "suzhou": "china",
    "shenzhen": "china",
    "vietnam": "vietnam",
    "hanoi": "vietnam",
    "ho chi minh city": "vietnam",
    "mauritius": "mauritius",
    "sri lanka": "sri lanka",
    "tashkent": "uzbekistan",
    "indonesia": "indonesia",
    "jakarta": "indonesia",
}
#: CG-1: the institution's country as the registry may spell it, folded to the
#: spelling ``_BRANCH_CAMPUS_PLACES`` uses.
_CAMPUS_COUNTRY_ALIASES: dict[str, str] = {
    "uae": "united arab emirates",
    "people's republic of china": "china",
    "prc": "china",
    "viet nam": "vietnam",
}
_CAMPUS_PLACE = "|".join(
    re.escape(place).replace(r"\ ", r"[\s-]+")
    for place in sorted(_BRANCH_CAMPUS_PLACES, key=len, reverse=True)
)
_CAMPUS_IN_TITLE = re.compile(
    rf"\(\s*(?:campus\s+)?({_CAMPUS_PLACE})(?:\s+campus)?\s*\)"
    rf"|\b({_CAMPUS_PLACE})\s+campus\b"
    rf"|\bcampus\s+(?:in\s+)?({_CAMPUS_PLACE})\b"
    rf"|\s[-–—|,]\s*({_CAMPUS_PLACE})\s*$",
    re.IGNORECASE,
)
_CAMPUS_IN_SEGMENT = re.compile(rf"(?:^|[-_])({_CAMPUS_PLACE})(?:[-_]campus)?$", re.IGNORECASE)


def foreign_campus_named(title: str, url: str, country: str) -> str | None:
    """CG-1: the branch-campus place a page's title or URL names abroad, or ``None``.

    ``country`` is the institution's country; empty means unknown, and then
    nothing is refused. A place in the institution's own country is not a
    refusal: that is a domestic campus, or the country's own name.
    """
    home = re.sub(r"\s+", " ", (country or "").strip().lower())
    home = _CAMPUS_COUNTRY_ALIASES.get(home, home)
    if not home:
        return None
    found: list[str] = []
    for match in _CAMPUS_IN_TITLE.finditer(title or ""):
        found.extend(group for group in match.groups() if group)
    for segment in urlparse(url or "").path.lower().split("/"):
        hit = _CAMPUS_IN_SEGMENT.search(segment.removesuffix(".html"))
        if hit:
            found.append(hit.group(1))
    for place in found:
        key = re.sub(r"[\s-]+", " ", place.lower())
        if _BRANCH_CAMPUS_PLACES.get(key, home) != home:
            return key
    return None


#: DI-1: navigation text that names admissions, in English and a few local words.
_ADMISSIONS_LINK_TEXT = re.compile(
    r"\badmissions?\b|\bapply\b|\binternational\s+(?:students?|admissions?)\b"
    r"|\bprospective\s+students?\b|\bundergraduate\s+admissions?\b"
    r"|\badmisi(?:o|ó)n(?:es)?\b|招生|入学",
    re.IGNORECASE,
)
#: DI-1: registrable domains that are never an institution's admissions site.
#: ``google.*`` is matched by its first label, every country suffix included.
_ADMISSIONS_HOST_DENYLIST = frozenset(
    {
        "commonapp.org",
        "uni-assist.de",
        "studyinfo.fi",
        "universityadmissions.se",
        "antagning.se",
        "parcoursup.fr",
        "ucas.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "youtube.com",
        "linkedin.com",
        "wikipedia.org",
        "bit.ly",
    }
)
#: DI-1: host labels that mark a government portal.
_GOVERNMENT_LABELS = frozenset({"gov", "gouv", "gob", "govt", "government"})
#: DI-1: link text that says the page is the university's own admissions.
_NAMES_UNIVERSITY = re.compile(r"universit|institut|college|大学", re.IGNORECASE)
#: DI-1: an ancestor id/class that marks a site header or main navigation.
_NAVIGATION_REGION = re.compile(r"nav|menu|header|masthead|topbar", re.IGNORECASE)
#: DI-1: extra registrable domains one homepage may add.
MAX_EXTRA_DOMAINS = 1

#: LI-1: programme-path words of non-English catalogues, scored like the
#: existing ``opleidingen|studiengang`` rule. Only words that name a study
#: offer, each a dictionary or degree-law word (sources re-checked in
#: HELDOUT_PROVENANCE_AUDIT_2026-10-20): "studienangebot", "studiengaenge" /
#: "studiengange" (de, Duden s.v. Studienangebot, Studiengang; ASCII folds of
#: "Studiengänge"); "corsi-di-laurea" / "corso-di-laurea" (it, DM 270/2004
#: art. 3, "corsi di laurea"); "carreras" (es, RAE DLE s.v. carrera, the
#: studies that qualify for a profession), "grados" and "titulaciones" (es,
#: Real Decreto 822/2021, "títulos de Grado", "titulaciones"); "formations"
#: (fr, Larousse s.v. formation); "utbildningar" (sv, Svensk ordbok s.v.
#: utbildning); "studijni-programy" (cs, Act No. 111/1998 Coll. §44,
#: "studijní program").
_LOCALIZED_PROGRAM_SIGNALS: tuple[tuple[str, int], ...] = (
    (
        r"/(studienangebot|studiengaenge|studiengange|corsi-di-laurea|corso-di-laurea"
        r"|carreras|grados|titulaciones|formations|utbildningar|studijni-programy)/[a-z-]{4,}",
        3,
    ),
)
#: HP-AUDIT D3 (``HELDOUT_PICKED_ROWS`` off): the same rule without
#: "studienangebot", the one path word a heldout page picked (audit row A6).
_LOCALIZED_PROGRAM_SIGNALS_WITHOUT_HELDOUT_PICKED: tuple[tuple[str, int], ...] = (
    (
        r"/(studiengaenge|studiengange|corsi-di-laurea|corso-di-laurea"
        r"|carreras|grados|titulaciones|formations|utbildningar|studijni-programy)/[a-z-]{4,}",
        3,
    ),
)
#: LI-1: degree words whose level is certain, as URL slugs (accents folded),
#: matched on a segment boundary like ``_DEGREE_SLUGS``. Each is a degree-law
#: or dictionary word (re-checked in HELDOUT_PROVENANCE_AUDIT_2026-10-20):
#: it laurea, laurea magistrale (DM 270/2004 art. 3), laurea triennale
#: (Treccani s.v. laurea); tr lisans, yüksek lisans, ön lisans (Law No. 2547
#: art. 3; YÖK Lisansüstü Eğitim ve Öğretim Yönetmeliği); cs bakalář,
#: magisterský (Act No. 111/1998 Coll. §45-§46), ru/kk бакалавр, магистр as
#: transliterated (Federal Law 273-FZ art. 69; RK Law On Education art. 36),
#: et/lt bakalaureus, bakalauras (Kõrgharidusseadus; Lithuanian Law on Higher
#: Education and Research art. 47); es grado (Real Decreto 822/2021 art. 14);
#: pt mestrado (Decreto-Lei 74/2006 art. 15); sv kandidatexamen
#: (Högskoleförordningen 1993:100 bilaga 2). Compounds are checked
#: first, so ``laurea-magistrale`` (master) is never read as ``laurea``
#: (bachelor) and ``yuksek-lisans`` (master) never as ``lisans`` (bachelor).
#: ``on-lisans`` (Turkish associate degree) is removed before matching rather
#: than given a level the enum does not have. ``kandidat`` is a bachelor only
#: in Swedish (a Danish ``kandidat`` is a master's), so it counts only on a
#: ``.se`` host.
_LOCALIZED_DEGREE_COMPOUNDS: tuple[tuple[str, str], ...] = (
    ("master", r"laurea-magistrale"),
    ("master", r"yuksek-?lisans"),
    ("bachelor", r"laurea-triennale"),
)
#: HP-AUDIT D3: the compound a heldout page picked (audit row A17). With
#: ``HELDOUT_PICKED_ROWS`` off it is left out, so a ``laurea-magistrale`` slug
#: falls through to ``laurea`` (bachelor) exactly as it would had the row
#: never been written.
_HELDOUT_PICKED_COMPOUND = ("master", r"laurea-magistrale")
#: HP-AUDIT D3 (``docs/process/HELDOUT_PROVENANCE_AUDIT_2026-10-20.md``): two
#: LI-1 rows are dictionary words, but they were *selected* because a heldout
#: page needed them, by LI-1's own comment: the German path word
#: "studienangebot" in ``_LOCALIZED_PROGRAM_SIGNALS`` (row A6) and the Italian
#: compound ``laurea-magistrale`` in ``_LOCALIZED_DEGREE_COMPOUNDS`` (row A17).
#: On (default, byte-identical to before the flag): both rows are read. Off (a
#: removal replay, ``--no-heldout-picked-rows``): both are left out, every
#: other LI-1 row unchanged. Read only where LI-1's tables are read, so it does
#: nothing while ``LOCALIZED_IDENTITY`` is off.
HELDOUT_PICKED_ROWS = True


def localized_program_signals() -> tuple[tuple[str, int], ...]:
    """LI-1's local programme-path rules, with or without the heldout-picked word (D3)."""
    if HELDOUT_PICKED_ROWS:
        return _LOCALIZED_PROGRAM_SIGNALS
    return _LOCALIZED_PROGRAM_SIGNALS_WITHOUT_HELDOUT_PICKED


def _localized_degree_compounds() -> tuple[tuple[str, str], ...]:
    """LI-1's compound degree slugs, with or without the heldout-picked compound (D3)."""
    if HELDOUT_PICKED_ROWS:
        return _LOCALIZED_DEGREE_COMPOUNDS
    return tuple(row for row in _LOCALIZED_DEGREE_COMPOUNDS if row != _HELDOUT_PICKED_COMPOUND)


_LOCALIZED_DEGREE_SLUGS: tuple[tuple[str, str], ...] = (
    ("bachelor", r"laurea"),
    ("bachelor", r"lisans"),
    ("bachelor", r"bakala(?:r|vr|ur)[a-z]*"),
    ("bachelor", r"grado"),
    ("master", r"magist(?:er|r)[a-z]*"),
    ("master", r"mestrado"),
    ("master", r"master-s"),
    # LV-1, languages no development set speaks. ca: "grau-en-…", the slug of
    # "Grau en …" (Reial Decret 822/2021 art. 14; "grau" alone is German
    # "grey" and Portuguese "degree"). sk: "inžiniersky" second cycle (Act No.
    # 131/2002 Coll. §53); Czech writes "inženýrský", Polish "inżynierskie".
    ("bachelor", r"grau-en"),
    ("master", r"inziniersk[a-z]*"),
)
#: LV-1 (``page_classifier.LEXICON_LANGUAGE_COVERAGE``): the slug forms of
#: level words the lexicon battery found unread, for languages a development
#: set speaks, read after every other slug table while the flag is on. One
#: dictionary per row: fi Government Decree on University Degrees 794/2004
#: (kandidaatin / maisterin tutkinto); pl Act of 20 July 2018 art. 64
#: (studia pierwszego / drugiego stopnia; licencjat, inżynier as the titles);
#: pt (BR) Houaiss s.v. "bacharelado" (a first degree); es RAE, DLE s.v.
#: "maestría"; da Bekendtgørelse om bachelor- og kandidatuddannelser
#: (kandidatuddannelse, a master's); et Kõrgharidusseadus (integreeritud õpe,
#: a master's); de/nl/da/no/sv compounds as R1's text table already reads them
#: (Bachelorstudiengang, bacheloropleiding, masterprogram). ja/zh/ko/th write
#: their slugs in English, which ``_DEGREE_SLUGS`` already reads.
_LV1_DEGREE_SLUGS: tuple[tuple[str, str], ...] = (
    ("master", r"integreeritud-ope[a-z]*"),
    (
        "bachelor",
        r"bachelor(?:program(?:me|ma|met)?|programm|opleiding|studium|studiengang|studier?"
        r"|grad(?:en)?|uddannelse(?:n)?)",
    ),
    (
        "master",
        r"master(?:program(?:me|ma|met)?|programm|opleiding|studium|studiengang|studier?"
        r"|grad(?:en)?|uddannelse(?:n)?)",
    ),
    ("bachelor", r"kandidaat(?:ti|in)[a-z]*"),
    ("master", r"maisteri[a-z]*"),
    ("bachelor", r"pierwszego-stopnia"),
    ("bachelor", r"licencjat[a-z]*"),
    ("bachelor", r"studia-inzynierskie"),
    ("master", r"drugiego-stopnia"),
    ("bachelor", r"bacharel(?:ado)?"),
    ("master", r"maestrias?"),
    ("master", r"kandidatuddannelse[a-z]*"),
)
_SWEDISH_KANDIDAT = r"kandidat[a-z]*"
_TURKISH_ASSOCIATE = re.compile(r"(^|[/-])on-?lisans(?=[/-]|$)")

#: Conventional sitemap locations, tried when robots.txt names none.
SITEMAP_FALLBACK_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap/sitemap.xml",
)

#: Historical suffix coverage pinned by test_claim_verifier. Actual host
#: identity now uses the shared bundled PSL, including private hosting suffixes.
MULTIPART_SUFFIXES = frozenset(
    {
        "ac.uk",
        "ac.nz",
        "ac.jp",
        "ac.kr",
        "ac.at",
        "ac.be",
        "ac.il",
        "ac.in",
        "ac.za",
        "ac.th",
        "ac.id",
        "ac.ir",
        "ac.cy",
        "ac.rs",
        "ac.ma",
        "edu.au",
        "edu.sg",
        "edu.hk",
        "edu.kz",
        "edu.cn",
        "edu.tw",
        "edu.my",
        "edu.pl",
        "edu.tr",
        "edu.mx",
        "edu.br",
        "edu.ar",
        "edu.co",
        "edu.pe",
        "edu.vn",
        "edu.ph",
        "edu.sa",
        "edu.eg",
        "edu.lb",
        "edu.jo",
        "edu.kw",
        "edu.pk",
        "co.uk",
        "org.uk",
        "gov.uk",
        "com.au",
        "net.au",
        "org.au",
        "com.br",
        "com.sg",
        "com.hk",
        "com.tr",
        "com.mx",
        "co.jp",
        "co.nz",
        "co.za",
        "or.jp",
        "ne.jp",
        "go.jp",
        "re.kr",
        "or.kr",
        "go.kr",
    }
)


class PageCategory:
    """What a discovered URL is expected to be. Deliberately a plain namespace
    rather than an enum: this module may not import the classifier's vocabulary,
    and these are *expectations* about a URL, not verdicts about a page."""

    PROGRAM_CATALOG = "program_catalog"
    PROGRAM_PAGE = "program_page"
    ADMISSIONS = "admissions"
    COSTS = "costs"
    SCHOLARSHIPS = "scholarships"
    DOCUMENTS = "documents"

    ALL = (PROGRAM_CATALOG, PROGRAM_PAGE, ADMISSIONS, COSTS, SCHOLARSHIPS, DOCUMENTS)


#: Path and slug signals per category, with a weight. A URL scores against each
#: category and is filed under its best match, if any match at all.
_URL_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    PageCategory.PROGRAM_PAGE: (
        (r"/(bsc|msc|ba|ma|beng|meng|llb|llm)[-/]", 5),
        (r"/(bachelors?|masters?|undergraduate)/[a-z-]{4,}", 5),
        (r"/(programmes?|programs?|degrees?|courses?|studies)/[a-z-]{4,}", 4),
        # The same hyphenated compounds the catalogue rule allows: Vienna
        # publishes at /bachelordiploma-programmes/<programme>, which no rule
        # expecting a bare "/programmes/" segment ever matched.
        (r"/[a-z0-9]+-(programmes?|programs?|degrees?|courses?)/[a-z][a-z0-9-]{3,}", 4),
        (r"/study/[a-z-]{4,}", 3),
        (r"/(opleidingen|studiengang|koulutus|kierunki)/[a-z-]{4,}", 3),
    ),
    PageCategory.PROGRAM_CATALOG: (
        # The segment has to *end* with the listing word, so "degree-programmes"
        # and "degrees-programs" count while "degree-ceremony-photos" and
        # "programme-news" do not. Universities name these pages "degree
        # programmes" far more often than "programmes", and requiring the bare
        # word left the walk stranded on the intermediate page at Vienna,
        # Warsaw and UBC.
        (r"/[a-z0-9-]*(programmes?|programs?|degrees?|courses?|studies)/?$", 5),
        (r"/(bachelors?|masters?|undergraduate|postgraduate)/?$", 5),
        (r"/(study|studies|education)/(programmes?|programs?|degrees?)/?$", 4),
        (r"/(course|programme|program)[-_]?(search|finder|list|catalog(ue)?)", 4),
    ),
    PageCategory.ADMISSIONS: (
        (r"/(admission|admissions|apply|application)", 4),
        (r"/(entry|admission)[-_]requirements", 5),
        (r"/how[-_]to[-_]apply", 5),
        (r"/international[-_]?(students?|applicants?|admissions?)", 3),
        (r"/(toelating|zulassung|haku|rekrutacja)", 3),
    ),
    PageCategory.COSTS: (
        (r"/(tuition|fees?|cost|costs)", 4),
        (r"/tuition[-_]?fees?", 5),
        (r"/cost[-_]of[-_](attendance|living|study)", 5),
        (r"/(collegegeld|studiengebuehren|lukuvuosimaksut|czesne)", 4),
    ),
    PageCategory.SCHOLARSHIPS: (
        (r"/(scholarship|scholarships|bursary|bursaries|grants?)", 4),
        (r"/(financial[-_]aid|funding|fellowships?)", 4),
        (r"/(beurzen|stipendien|apurahat|stypendia)", 4),
    ),
    PageCategory.DOCUMENTS: (
        (r"/(required[-_]documents|documents[-_]required|document[-_]checklist)", 5),
        (r"/(supporting[-_]documents|what[-_]to[-_]submit)", 4),
    ),
}

#: R4 (``LOCAL_CATALOGUE_ENTRY``, 20 Q2): the slug forms of the local listing
#: words, a dictionary translation of "programmes / studies" per language, the
#: same for every language. A segment that *is* the word is a catalogue root,
#: one below it a programme path. Words LI-1's ``_LOCALIZED_PROGRAM_SIGNALS``
#: or the English rules already score as programme paths are left out of the
#: programme rule, so no path is counted twice for one word.
_LOCAL_CATALOGUE_ROOT = (
    r"/(?:carreras(?:-de-(?:grado|pregrado))?|grados|titulaciones|pregrado|oferta-academica"
    r"|estudios|graus|estudis|formations?|choisir-sa-formation|offre-de-formation"
    r"|corsi(?:-di-(?:laurea|studio))?|offerta-formativa|graduacao|cursos(?:-de-graduacao)?"
    r"|licenciaturas|opleidingen|bacheloropleidingen|onderwijsaanbod|studier|studieprogrammer"
    r"|studietilbud|uddannelser|bacheloruddannelser|utbildning(?:ar)?|studienangebot"
    r"|studiengaenge|studiengange|koulutukset|koulutusohjelmat|kierunki(?:-studiow)?"
    r"|studijni-programy|studijne-programy|bolumler|programlar|lisans-programlari|oppekavad"
    r"|studiju-programos|obrazovanie|obrazovatelnye-programmy|bakalavriat|programmy)/?$"
    r"|/opleidingen/[a-z]/?$"
)
_LOCAL_LISTING_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    PageCategory.PROGRAM_CATALOG: ((_LOCAL_CATALOGUE_ROOT, 4),),
    PageCategory.PROGRAM_PAGE: (
        (
            r"/(?:formation|carrera|uddannelser?|cursos|programy|bolumler|oppekavad"
            r"|studiju-programos|programos|bakalavriat|graduacao|studieprogrammer|utbildning"
            r"|studier/program|koulutukset)/[a-z0-9][a-z0-9-]{3,}",
            3,
        ),
        # KU Leuven's catalogue codes its programmes under a language letter:
        # /opleidingen/n/SC_51016742.htm.
        (r"/opleidingen/[a-z]/[^/]{4,}", 3),
    ),
}
_LOCAL_CATALOGUE_PATH = re.compile(_LOCAL_CATALOGUE_ROOT, re.IGNORECASE)
#: R4: ``www.``, ``www5.``: the main site's host under another name, not a
#: catalogue host.
_WWW_PREFIX = re.compile(r"^www\d*\.")

#: Slug fragments that make a page an event, a newsletter or an announcement
#: whatever path it sits under. The live canary found these *inside* programme
#: paths, where a whole-segment exclusion never sees them: rug.nl returned
#: "bachelor-open-day", "onlinebachelorweek" and "student-for-a-day" as the
#: applicant's three programme pages, and aalto.fi returned two newsletters.
_NOT_A_PAGE_ABOUT_STUDYING = re.compile(
    r"(open[-_]?day|openday|info(rmation)?[-_]?(session|day|evening)|student[-_]for[-_]a[-_]day"
    r"|bachelor[-_]?week|master[-_]?week|onlinebachelor|onlinemaster"
    r"|newsletter|nyhetsbrev|uutiskirje|webinar|open[-_]house|taster"
    r"|campus[-_]?tour|university[-_]?tour|virtual[-_]?tour|webklas|proefstuderen"
    r"|summer[-_]school|orientation|graduation|ceremony)",
    re.IGNORECASE,
)

#: URLs that are never worth fetching, whatever else they score.
_URL_EXCLUSIONS = re.compile(
    r"/(news|nieuws|actueel|press|blog|events?|agenda|calendar|vacature|vacanc"
    r"|jobs?|careers?|alumni|donate|shop|library|contact|privacy|cookie|search"
    r"|login|signin|account|basket|cart|rss|feed|tag|author|archive)(/|$)"
    # One course's page is never a programme: Warsaw's catalogue answered a
    # computer science search with "Introduction to computer science I" (run 54).
    r"|/courses?/(view|details?)(/|$)"
    r"|\.(jpg|jpeg|png|gif|svg|webp|css|js|zip|mp4|mp3|docx?|xlsx?|pptx?)$",
    re.IGNORECASE,
)

#: PG-1 (``page_classifier.PROGRAMME_PAGE_GUARD``) only: research output and
#: article pages the list above misses. A Serper run read a research portal's
#: ``/en/publications/…`` and a ``…/news-single-view-start/article/…`` page as
#: programme leads; KAIST read a ``/clippings/`` page.
_PG1_URL_EXCLUSIONS = re.compile(
    r"/(publications?|article|clippings)(/|$)|news-single-view", re.IGNORECASE
)


#: Mobility pages speak for exchange, double-degree and partner-university
#: students, never for a degree applicant: PUC's
#: ``/come-to-uc/double-degree-international-students/application-calendar-…``
#: page gave its partner-university deadline (2024-10-01) as the admission one.
_MOBILITY_URL_EXCLUSIONS = re.compile(
    r"/[^/]*(?:(?<![a-z])exchange|study[-_]?abroad|mobility|double[-_]?degree"
    r"|partner[-_]?universit(?:y|ies))[^/]*(?:/|$)",
    re.IGNORECASE,
)


def _url_excluded(path: str) -> bool:
    """Whether a URL path is never worth fetching (PG-1 widens the list)."""
    if _URL_EXCLUSIONS.search(path) or _MOBILITY_URL_EXCLUSIONS.search(path):
        return True
    if not _page_classifier.PROGRAMME_PAGE_GUARD:
        return False
    if _PG1_URL_EXCLUSIONS.search(path):
        return True
    return _page_classifier.LEXICON_V2 and bool(_LX1_URL_EXCLUSIONS.search(path))


#: LX-1 (``page_classifier.LEXICON_V2``), beside PG-1's list: publication
#: paths in Spanish, Dutch and Norwegian (PUC's ``/publicaciones/`` page was
#: reported as the programme in all four dev3 repetitions).
_LX1_URL_EXCLUSIONS = re.compile(
    rf"/({_page_classifier.LEXICON_V2_PUBLICATION_PATH})(/|$)", re.IGNORECASE
)


#: A programme page for the wrong level is not a match for this applicant.
#: How a catalogue writes a degree level in a URL.
#:
#: The cycle forms matter as much as the words. Warsaw's catalogue writes its
#: bachelor as ``IN/S1-INF`` and its master as ``IN/S2-INF``, and with only the
#: word list a master's page reached the top of a bachelor search — the right
#: fact about the wrong population, which is exactly what the prefilter exists
#: to stop. ``S1``/``S2`` is Bologna cycle numbering, not a Warsaw quirk: it is
#: ``studia pierwszego/drugiego stopnia`` in Polish, ``I``/``II stopnia`` in
#: prose, "first cycle"/"second cycle" in English. A numeric convention defeats
#: a word list wherever it is used.
#:
#: Every slug here is matched on a path-segment boundary by
#: :func:`degree_level_named`, which is what makes a two-character slug like
#: ``s1`` safe to list.
_DEGREE_SLUGS: dict[str, tuple[str, ...]] = {
    "bachelor": (
        "bsc",
        "ba",
        "beng",
        "llb",
        "bachelor",
        "bachelors",
        "undergraduate",
        # Bologna first cycle
        "s1",
        "1st-cycle",
        "first-cycle",
        "i-stopnia",
        "licence",
        "licenciatura",
    ),
    "master": (
        "msc",
        "ma",
        "meng",
        "llm",
        "mba",
        "master",
        "masters",
        "graduate",
        "postgraduate",
        # Bologna second cycle
        "s2",
        "2nd-cycle",
        "second-cycle",
        "ii-stopnia",
        "magister",
        "mastere",
    ),
    "phd": ("phd", "doctoral", "doctorate", "dphil", "s3", "3rd-cycle", "third-cycle"),
    "foundation": ("foundation", "pre-bachelor", "preparatory"),
}


def registrable_domain(host_or_url: str) -> str:
    """The domain that owns a host, so "same site" is not a guess.

    ``www.rug.nl`` and ``rug.nl`` are the same institution; ``rug.nl`` and
    ``someoneelse.nl`` are not. Multi-part suffixes matter here: naively taking
    the last two labels would make every ``ac.uk`` site look like one domain.

    A full URL is accepted as well as a bare host. Callers hold homepages more
    often than hostnames, and the failure mode of not accepting one is silent:
    every comparison would answer "different institution" and discovery would
    quietly find nothing.
    """
    return site_domain(host_or_url)


def same_institution(url: str, domain: str) -> bool:
    """Whether a URL belongs to the institution that owns ``domain``."""
    try:
        scheme = urlparse(url).scheme
    except ValueError:
        return False
    if scheme not in ("http", "https"):
        return False
    return hosts_share_site(url, domain)


def on_institution_site(url: str, domain: str, extra_domains: Sequence[str] = ()) -> bool:
    """``same_institution`` for the domain or any DI-1 admissions domain."""
    return same_institution(url, domain) or any(
        same_institution(url, extra) for extra in extra_domains if extra
    )


def _in_navigation(anchor: Any) -> bool:
    """Whether a link sits in the page's header or main navigation (DI-1)."""
    for parent in anchor.parents:
        name = parent.name
        if name in ("nav", "header"):
            return True
        if name in (None, "[document]", "html", "body"):
            continue
        role = str(parent.get("role") or "").lower()
        if role in ("navigation", "banner", "menubar", "menu"):
            return True
        classes = parent.get("class") or []
        if isinstance(classes, str):
            classes = [classes]
        marks = " ".join([str(parent.get("id") or ""), *map(str, classes)])
        if marks.strip() and _NAVIGATION_REGION.search(marks):
            return True
    return False


def _third_party(registrable: str) -> bool:
    """Whether a registrable domain is on DI-1's never-an-admissions-site list."""
    return registrable in _ADMISSIONS_HOST_DENYLIST or registrable.split(".", 1)[0] == "google"


def admissions_host_from_homepage(html: str, base: str, domain: str) -> dict[str, object]:
    """DI-1: the one other registrable domain a homepage names as its admissions.

    Returns the trace record: ``{"domain", "link", "text"}`` when exactly one
    domain qualifies, ``{"rejected": ..., "domains": [...]}`` when several do,
    and ``{}`` when none does. Only links in the header or main navigation
    count, only when their own text names admissions, never a denylisted third
    party, and a government portal only when the text names the university.
    """
    own = registrable_domain(domain)
    found: dict[str, tuple[str, str]] = {}
    for anchor in parse_html(html).find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        link = page_link(base, str(anchor["href"]))
        if link is None:
            continue
        url = link.split("#")[0]
        try:
            parsed = urlparse(url)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not host:
            continue
        registrable = registrable_domain(host)
        if not registrable or registrable == own or same_institution(url, domain):
            continue
        text = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:160]
        if not _ADMISSIONS_LINK_TEXT.search(text) or not _in_navigation(anchor):
            continue
        if _third_party(registrable):
            continue
        if _GOVERNMENT_LABELS & set(host.split(".")) and not _NAMES_UNIVERSITY.search(text):
            continue
        found.setdefault(registrable, (canonical_url(url), text))
    if len(found) > MAX_EXTRA_DOMAINS:
        return {"rejected": "ambiguous: several admissions domains", "domains": sorted(found)}
    if not found:
        return {}
    extra, (link, text) = next(iter(found.items()))
    return {"domain": extra, "link": link, "text": text}


#: Query parameters that identify a referral rather than select content.
#: Matched against the parameter name — an earlier version matched the whole
#: "key=value" pair, so "utm_source=x" was kept and the same page was
#: discovered twice under two URLs.
_TRACKING_PARAM = re.compile(
    r"^(utm_[a-z_]*|fbclid|gclid|msclkid|dclid|mc_[a-z]+|ref|referrer|source"
    r"|igshid|_ga|yclid)$",
    re.IGNORECASE,
)


#: Plan rule CU-1, on since paired runs 39067189351 (cohort) and 39067190840
#: (dev2): identical labels, dev2 reads 345/342 -> 326/323; owner delegation
#: 2026-10-17. False turns it off. ``canonical_url``
#: writes ``http://`` of a page on its default port as ``https://``, so the two
#: schemes of one institution page are one URL everywhere the pipeline
#: deduplicates. One navigation offered ``http://…/undergraduate-programs``
#: and ``https://…/undergraduate-programs`` and the run read both, 10 s each
#: under Crawl-delay 10. ``navigation.py`` already merged the two locally (see
#: ``scheme_free_identity``); this applies the same identity pipeline-wide and
#: picks the secure scheme as the one to read, the one navigation prefers too.
#: A URL on an explicit non-default port keeps its scheme: ``http://h:8080`` and
#: ``https://h:8080`` are different services.
CANONICAL_HTTP_HTTPS = True


def scheme_free_identity(url: str) -> str:
    """One page's identity regardless of ``http``/``https``: the URL without its scheme."""
    return url.split("://", 1)[-1]


def canonical_url(url: str) -> str:
    """A stable form, so the same page is not discovered twice.

    Drops the fragment and tracking parameters, lowercases the host, removes a
    default port and a trailing slash. Query parameters that select content are
    kept — dropping them would merge genuinely different pages. Under CU-1 an
    ``http`` URL on the default port is written as ``https``.

    Never raises: invisible format characters are removed from the host first
    (usp's zero-width space), and a URL that still cannot be parsed — a phone
    number where the port goes, a port past 65535 — comes back as given
    (stripped), for the caller's validity rule to drop.
    """
    raw = url.strip()
    try:
        parts = urlparse(strip_invisible_host(raw))
        port = parts.port
    except ValueError:
        return raw
    if not parts.scheme or not parts.netloc:
        return raw

    host = (parts.hostname or "").lower()
    if port and not (
        (parts.scheme == "http" and port == 80) or (parts.scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    kept = [
        pair
        for pair in parts.query.split("&")
        if pair and not _TRACKING_PARAM.match(pair.split("=", 1)[0])
    ]
    scheme = parts.scheme
    if CANONICAL_HTTP_HTTPS and scheme == "http" and port in (None, 80):
        scheme = "https"
    return urlunparse((scheme, host, path, "", "&".join(sorted(kept)), ""))


#: Paths that are about research rather than about studying a programme. A
#: research group's "BSc and MSc projects" page matched the ``/bsc|msc/`` rule
#: and was offered as the applicant's programme; a degree marker in a slug says
#: nothing about whether the page is a degree.
_NOT_A_PROGRAMME_PATH = re.compile(
    r"/(research|onderzoek|forschung|labs?|groups?|institutes?|centres?|centers?)/"
    r"|(projects?|thesis|theses|guidelines|internships?|vacancies|supervisors?)(/|$)",
    re.IGNORECASE,
)

#: A path segment that makes the page about money rather than about a course.
_FUNDING_SEGMENT = re.compile(
    r"/(scholarships?|bursary|bursaries|grants?|financial[-_]aid|funding|fellowships?"
    r"|beurzen|stipendien|apurahat|stypendia)(/|$)",
    re.IGNORECASE,
)


#: Plan rule SR-1 (dev3 discovery analysis 2026-10-18, Imperial and UNSW,
#: fix B), off until a paired run passes. ``matches_field`` scored each word
#: of the field as a *substring* of the path, so "science" gave +8 to every
#: ``*-science`` URL ("natural-sciences", "materials-science") while
#: "computer" missed "computing"; Imperial's gold ``/2027/computing-beng``
#: sat at rank 35 of 40 behind two tuition-fee tables and the eight confirm
#: reads (~5.8 s each) went to the wrong pages. With SR-1 on:
#:
#: * the field bonus (8 per word of the requested field) is earned only when
#:   the path carries the field phrase or one of the ontology's strong (or,
#:   under LI-1, localized) aliases as consecutive whole slug words; a
#:   generic word on its own ("science", "engineering") earns nothing;
#: * a path with a fee, tuition, cost or scholarship segment never scores as
#:   a programme page or catalogue;
#: * degree slug tokens (bsc, beng, btech, ba, bs, meng) are title filler.
#:
#: The benchmark harness flips it per capture (``--field-slug-scoring``).
FIELD_SLUG_SCORING = False
#: SR-1: degree tokens that name a form, never a subject.
_DEGREE_SLUG_FILLER = frozenset({"bsc", "beng", "btech", "ba", "bs", "meng"})
#: IM-1: a UK integrated master's (MEng, MSci, MMath, MPhys, MChem) is entered
#: from school like a bachelor's and awards a master's. Imperial lists
#: ``/undergraduate/2027/mathematics-computer-science-meng`` beside the BEng;
#: ``degree_level_named`` read "undergraduate" before "meng" and called it a
#: bachelor page, so discovery confirmed it for a bachelor applicant and every
#: claim read from it was scored out of scope (paired run 39098958849). On: a
#: URL or page title that names an integrated master's and no bachelor form
#: reads as master for programme confirmation, and among programme candidates
#: that score the same, a URL whose last segment is exactly the requested field
#: ("computing-beng") is read before a joint one
#: ("mathematics-computer-science-beng"). The page classifier's own level
#: reading is untouched, so a UK undergraduate admissions page that mentions
#: MEng courses is not refused by the requirements reader. True by default.
INTEGRATED_MASTERS_LEVEL = True
#: IM-1: slug words that name an integrated master's.
_INTEGRATED_MASTER_SLUGS = frozenset({"meng", "msci", "mmath", "mphys", "mchem"})
#: IM-1: slug words that name a bachelor's form ("undergraduate" names an
#: entry route, which an integrated master's shares, not an award).
_BACHELOR_FORM_SLUGS = frozenset({"bsc", "beng", "ba", "bs", "llb", "bachelor", "bachelors"})
#: CC-1 (MISS_STAGES_2026-10-19 §3.3): a course is never a programme lead. A
#: catalogue or listing links its individual courses beside its programmes;
#: iitd's ``all-courses`` listing queued ``col100-…``, ``col703-…`` and
#: ``col863-…`` as follow-ups ahead of the ranked results and took three of the
#: four checks between the gold and the read cap. On: ``catalog_walker.score_link``
#: (shared by the walker and recovery's listing follow-up) hard-rejects a link
#: whose label or last path segment starts with a course code (one token of 2-4
#: letters directly followed by 3-4 digits), or whose path has a ``course`` /
#: ``courses`` segment followed by an identifier (a number other than a year, a
#: course code) or ``view``. A ``/courses/<programme-slug>/`` path matches neither.
#: On by default; the harness flips it per capture (``--course-lead-guard``).
COURSE_LEAD_GUARD = True
_INTEGRATED_MASTER_TEXT = re.compile(
    r"\b(?:m\.?eng|m\.?sci|m\.?math|m\.?phys|m\.?chem)\b|\bintegrated\s+master(?:'?s)?\b",
    re.IGNORECASE,
)
_BACHELOR_FORM_TEXT = re.compile(
    r"\b(?:b\.?sc|b\.?eng|b\.?a|llb|bachelor(?:'?s)?)\b", re.IGNORECASE
)


def _slug_words(url: str) -> set[str]:
    """IM-1: the words of a URL's path, split on any non-letter."""
    path = _fold(unquote(urlparse(url).path or ""))
    return {w for w in re.split(r"[^a-z]+", path) if w}


def names_integrated_master(text: str) -> bool:
    """IM-1: whether a title names an integrated master's and no bachelor form.

    "Mathematics and Computer Science MEng" does; "Physics BSc/MSci" and
    "Computing BEng" do not.
    """
    text = text or ""
    return bool(_INTEGRATED_MASTER_TEXT.search(text)) and not _BACHELOR_FORM_TEXT.search(text)


def url_names_integrated_master(url: str) -> bool:
    """IM-1: whether a URL's path names an integrated master's and no bachelor form."""
    words = _slug_words(url)
    named = bool(words & _INTEGRATED_MASTER_SLUGS) or (
        "integrated" in words and bool(words & {"master", "masters"})
    )
    return named and not words & _BACHELOR_FORM_SLUGS


def _integrated_master_page(page: PageClassification, url: str) -> bool:
    """IM-1: a page whose URL, title or subject names only an integrated master's."""
    names = [page.title or "", page.subject or ""]
    if any(_BACHELOR_FORM_TEXT.search(name) for name in names):
        return False
    if url and _slug_words(url) & _BACHELOR_FORM_SLUGS:
        return False
    return any(names_integrated_master(name) for name in names) or (
        bool(url) and url_names_integrated_master(url)
    )


#: Plan rule CH-1 (replay plan 2026-10-19 §5.1, loop id CA-1a; generalisation
#: ticket 09), on by default since the rp-bundle2 replay (2026-10-19). Without
#: it a programme page is confirmed
#: when its *body* names the level and the subject, so a department page
#: whose text lists the bachelor's it teaches, or a lab's course list, can be
#: confirmed as the programme. On: a candidate page passes only when its
#: **head** — ``<title>`` or first ``h1`` — carries the identity: (1) the head
#: names the requested subject; (2) the requested level is named in the head,
#: in the URL's degree slug or in a labelled field of the page, never only in
#: running text; (3) a head that names an organisational unit
#: (``_UNIT_WORDS``) and no degree is refused as a unit. The benchmark
#: harness switches it off per capture (``--no-confirm-head-identity``).
CONFIRM_REQUIRES_HEAD_IDENTITY = True
#: CH-1: the nouns that name an organisational unit — department, faculty,
#: school, institute, laboratory, centre, group, chair — per language of
#: ``languages.json`` plus English. Written from a dictionary before any
#: development page was read (generalisation 16-Q5, the overfitting guard),
#: the same eight concepts in every language; no word comes from a page. A
#: trailing ``*`` marks a stem that takes inflectional endings ("wydział*"
#: reads "wydziału"). Words in ja/zh/ko/th are matched inside the text, the
#: rest as whole words; table and head are folded alike (``_fold``). Left out on purpose: words that name
#: the programme itself in their system (ja/zh "学科", ko "학과", zh "专业",
#: tr "program"), a level word (ja "学部" is R1's bachelor's word), words that
#: also name the university or something else (ko "대학", zh "系", de/et
#: "labor", en "college", tr "kürsü"), and kk "топ" (three letters, also "top").
_UNIT_WORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "department",
        "dept",
        "faculty",
        "school",
        "institute",
        "lab",
        "labs",
        "laboratory",
        "laboratories",
        "centre",
        "center",
        "group",
        "chair",
    ),
    "ca": (
        "departament",
        "facultat",
        "escola",
        "institut",
        "laboratori",
        "centre",
        "grup",
        "càtedra",
    ),
    "cs": ("katedr*", "oddělení", "fakulta", "škola", "ústav*", "laboratoř*", "centrum", "skupina"),
    "da": (
        "institut",
        "afdeling",
        "fakultet",
        "fakultetet",
        "skole",
        "laboratorium",
        "center",
        "gruppe",
        "forskningsgruppe",
        "professorat",
    ),
    "de": (
        "abteilung",
        "departement",
        "fachbereich",
        "fachgebiet",
        "fakultät",
        "schule",
        "institut",
        "laboratorium",
        "zentrum",
        "gruppe",
        "arbeitsgruppe",
        "forschungsgruppe",
        "lehrstuhl",
        "professur",
    ),
    "es": (
        "departamento",
        "facultad",
        "escuela",
        "instituto",
        "laboratorio",
        "centro",
        "grupo",
        "cátedra",
    ),
    "et": (
        "osakond",
        "teaduskond",
        "kool",
        "instituut",
        "laboratoorium",
        "keskus",
        "rühm",
        "uurimisrühm",
        "õppetool",
    ),
    "fi": (
        "laitos",
        "tiedekunta",
        "korkeakoulu",
        "instituutti",
        "laboratorio",
        "keskus",
        "ryhmä",
        "tutkimusryhmä",
        "professuuri",
    ),
    "fr": (
        "département",
        "faculté",
        "école",
        "institut",
        "laboratoire",
        "centre",
        "groupe",
        "chaire",
    ),
    "it": (
        "dipartimento",
        "facoltà",
        "scuola",
        "istituto",
        "laboratorio",
        "centro",
        "gruppo",
        "cattedra",
    ),
    "ja": ("研究科", "研究所", "研究室", "実験室", "センター", "講座"),
    "kk": ("кафедр*", "факультет*", "мектеп*", "институт*", "зертхана*", "орталық*", "бөлім*"),
    "ko": ("학부", "연구소", "연구실", "실험실", "센터"),
    "lt": (
        "katedr*",
        "skyrius",
        "fakultetas",
        "mokykla",
        "institutas",
        "laboratorija",
        "centras",
        "grupė",
    ),
    "nb": (
        "institutt",
        "avdeling",
        "fakultet",
        "skole",
        "laboratorium",
        "senter",
        "gruppe",
        "forskningsgruppe",
        "professorat",
    ),
    "nl": (
        "departement",
        "afdeling",
        "vakgroep",
        "faculteit",
        "school",
        "instituut",
        "laboratorium",
        "centrum",
        "groep",
        "onderzoeksgroep",
        "leerstoel",
    ),
    "nn": (
        "institutt",
        "avdeling",
        "fakultet",
        "skule",
        "laboratorium",
        "senter",
        "gruppe",
        "forskingsgruppe",
        "professorat",
    ),
    "no": (
        "institutt",
        "avdeling",
        "fakultet",
        "skole",
        "laboratorium",
        "senter",
        "gruppe",
        "forskningsgruppe",
        "professorat",
    ),
    "pl": (
        "katedr*",
        "zakład*",
        "wydział*",
        "szkoł*",
        "instytut*",
        "laboratorium",
        "pracowni*",
        "centrum",
        "grup*",
        "zespoł*",
    ),
    "pt": (
        "departamento",
        "faculdade",
        "escola",
        "instituto",
        "laboratório",
        "centro",
        "grupo",
        "cátedra",
    ),
    "ru": (
        "кафедр*",
        "отделени*",
        "департамент*",
        "факультет*",
        "школа*",
        "институт*",
        "лаборатори*",
        "центр",
        "центра",
        "центре",
        "групп*",
    ),
    "sk": (
        "katedr*",
        "oddelenie",
        "fakulta",
        "škola",
        "ústav*",
        "laboratórium",
        "centrum",
        "skupina",
    ),
    "sv": (
        "institution",
        "institutionen",
        "avdelning",
        "avdelningen",
        "fakultet",
        "fakulteten",
        "skola",
        "skolan",
        "institut",
        "laboratorium",
        "centrum",
        "grupp",
        "forskargrupp",
        "forskningsgrupp",
        "professur",
    ),
    "th": ("ภาควิชา", "คณะ", "โรงเรียน", "สถาบัน", "ห้องปฏิบัติการ", "ศูนย์", "กลุ่มวิจัย"),
    "tr": (
        "bölüm*",
        "anabilim dalı*",
        "fakülte*",
        "okul*",
        "yüksekokul*",
        "enstitü*",
        "laboratuvar*",
        "merkez*",
        "grup*",
        "grub*",
    ),
    "zh": (
        "学院",
        "學院",
        "研究所",
        "研究院",
        "实验室",
        "實驗室",
        "中心",
        "教研室",
        "课题组",
        "課題組",
        "研究组",
        "研究組",
    ),
}
#: CH-1: the languages whose words are matched inside the text (no spaces
#: between words), not as whole words.
_UNSPACED_UNIT_LANGUAGES = frozenset({"ja", "zh", "ko", "th"})
#: CH-1: what separates a title's parts ("Computing Science | Bachelor's
#: degree programmes | University of Groningen").
_TITLE_SEPARATOR = re.compile(r"\s*[|｜•·»]\s*|\s+[-–—:]\s+|\s*[:：]\s+")
#: CH-1: the verdict for a page whose head names a unit, pinned by tests;
#: ``{}`` is the unit word as the head spells it, folded.
HEAD_UNIT_VERDICT = "page head names a unit ({}), not a programme"


@lru_cache(maxsize=4)
def _unit_word_pattern(table: tuple[tuple[str, tuple[str, ...]], ...]) -> re.Pattern[str] | None:
    """CH-1: one pattern for every word of ``table``, folded like the head."""
    alternatives: list[str] = []
    for language, words in table:
        for word in words:
            endings = r"\w*" if word.endswith("*") else ""
            folded = _fold(word.rstrip("*"))
            spelled = r"\s+".join(re.escape(part) for part in folded.split())
            if language in _UNSPACED_UNIT_LANGUAGES:
                alternatives.append(spelled)
            else:
                alternatives.append(rf"(?<!\w){spelled}{endings}(?!\w)")
    if not alternatives:
        return None
    return re.compile("|".join(sorted(set(alternatives), key=len, reverse=True)))


def _title_parts(title: str) -> list[str]:
    """CH-1: a title's parts, the site's name among them."""
    return [part.strip() for part in _TITLE_SEPARATOR.split(title or "") if part.strip()]


def head_unit_word(page: PageClassification) -> str | None:
    """CH-1: the unit word the page's head names, if it names one.

    The head is what the page says it is: its first ``h1`` and its title's
    first part. The rest of a title is the site ("… | School of Information
    Technology | University of X") and names a unit on every page.
    """
    pattern = _unit_word_pattern(tuple(sorted(_UNIT_WORDS.items())))
    if pattern is None:
        return None
    parts = _title_parts(page.title or "")
    for text in (page.heading, parts[0] if parts else ""):
        found = pattern.search(_fold(text or ""))
        if found:
            return " ".join(found.group(0).split())
    return None


def head_identity_rejects(
    page: PageClassification, requested_level: str, fields: list[str], *, url: str = ""
) -> str | None:
    """CH-1: why the page's head does not carry the programme's identity, or ``None``.

    Asked under ``CONFIRM_REQUIRES_HEAD_IDENTITY`` of a page every other
    check accepted. In order: (3) a head that names a unit and no degree is
    the unit's page; (2) the requested level must be named in the head, the
    URL's degree slug or a labelled field — a level only in running text is
    not enough; (1) the head — the ``h1``, the title or one of its parts —
    must name the requested subject by today's predicate
    (``matches_field_text``), not by a subject read anywhere on the page.
    """
    head = " ".join(part for part in (page.title or "", page.heading or "") if part)
    levels = _page_classifier.degree_levels_named(head)
    unit = head_unit_word(page)
    if unit is not None and not levels:
        return HEAD_UNIT_VERDICT.format(unit)
    if (
        requested_level not in levels
        and not (url and degree_level_named(url) == requested_level)
        and page.labelled_degree_level != requested_level
    ):
        return f"page head names no {requested_level} level, nor do the URL or a label"
    parts = [page.heading or "", page.title or "", *_title_parts(page.title or "")]
    if not any(part and matches_field_text(part, fields) for part in parts):
        return f"page head does not name the requested subject {fields!r}"
    return None


def exact_field_slug(url: str, fields: list[str]) -> bool:
    """IM-1: whether a URL's last segment names one requested field and nothing else.

    "computing-beng" is Computer Science exactly (a strong alias and a degree
    token); "mathematics-computer-science-beng" is a joint programme. Used only
    to order candidates that score the same; it never changes a score.
    """
    segments = [s for s in (urlparse(url).path or "").split("/") if s]
    if not segments:
        return False
    filler = _TITLE_FILLER | _DEGREE_SLUG_FILLER | _INTEGRATED_MASTER_SLUGS | _BACHELOR_FORM_SLUGS
    words = [
        w
        for w in re.split(r"[^a-z]+", _fold(unquote(segments[-1])))
        if w and w not in filler and w != "hons"
    ]
    if not words:
        return False
    return any(
        words == [w for w in re.split(r"[^a-z]+", _fold(name)) if w]
        for name in with_strong_aliases(fields)
    )


def _prefer_exact_field(ranked: list[tuple[int, str]], fields: list[str]) -> list[tuple[int, str]]:
    """IM-1: within one score, the exact-field URL first; otherwise order kept."""
    if not INTEGRATED_MASTERS_LEVEL or not fields:
        return ranked
    return sorted(ranked, key=lambda pair: (-pair[0], not exact_field_slug(pair[1], fields)))


#: Plan rule SP-1 (G-07 gold knockout 2026-10-19 §3, candidate ticket 2), on
#: by default since the rp-bundle2 replay (2026-10-19). A page whose head names only *part* of a programme —
#: one study year ("L2 …") or a process (application, admission, enrolment,
#: fees, deadlines) — is a sub-page of the programme, not its page, yet its
#: body names the level and the subject and it is confirmed. On: a page whose
#: head (CH-1's head: the first ``h1`` and the title's first part) names a
#: part word (``_SUBPAGE_YEAR_WORDS``, ``_SUBPAGE_PROCESS_WORDS``) before any
#: programme title of its own is refused with ``SUBPAGE_HEAD_VERDICT``, an
#: identity refusal; and when its URL sits under another lead's path in the
#: same candidate set, that parent lead is read next (a reorder of leads in
#: hand, never a new search). The benchmark harness switches it off per
#: capture (``--no-reject-subpage-head``).
CONFIRM_REJECTS_SUBPAGE_HEAD = True
#: SP-2 (NEXT_CYCLES_2026-10-19 §1.4, candidate 2): a page SP-1 refuses
#: because its head names a *process* of the programme (application,
#: admission, enrolment, fees, deadlines; ``_SUBPAGE_PROCESS_WORDS``, no new
#: word) is not the programme page, but it is where the programme's English
#: minima and application deadline are written. On, the first such page
#: discovery read (a year page never) is handed to the evidence stage as
#: ``Candidate.requirements_leads``; the requirements adapter reads it after
#: QR-1's question links and before any topic query, inside a free question
#: link slot (``_MAX_QUESTION_LINKS``) and the read budgets in force, for the
#: deadline and, while no IELTS minimum is read, English. Its claims take the
#: programme's scope only when the page's ``h1`` names the requested level
#: and subject (:func:`head_names_programme`). No query is sent, no
#: discovery read added; with SP-1 off nothing is refused, so nothing is
#: handed on. Off by default; the harness flips it per capture
#: (``--subpage-requirements-lead``). False changes nothing.
SUBPAGE_REQUIREMENTS_LEAD = False
#: SP-1: the words that name one study year, per language of
#: ``languages.json`` plus English. Written from a dictionary before any
#: development page was read (generalisation 16-Q5, the overfitting guard).
#: ``#`` stands for one digit 1-9 ("year #" reads "Year 2", never
#: "Year 2026"); a trailing ``*`` marks a stem that takes endings; a space
#: also matches a hyphen ("first-year"). Table and head are folded alike
#: (``_fold``); words in ja/zh/ko/th are matched inside the text, the rest as
#: whole words. Left out on purpose: the French master's years M1/M2 (an M2
#: *parcours* page is often the programme page itself), a bare "semester"
#: (a term, not a year), zh "大一" (also inside "北大一流"), and a bare
#: "курс" / "kursas" / "curso" (also "course").
_SUBPAGE_YEAR_WORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "year #",
        "#st year",
        "#nd year",
        "#rd year",
        "#th year",
        "first year",
        "second year",
        "third year",
        "fourth year",
        "year one",
        "year two",
        "year three",
        "year four",
        "freshman",
        "freshmen",
        "sophomore",
        "junior year",
        "senior year",
    ),
    "ca": (
        "primer curs",
        "segon curs",
        "tercer curs",
        "quart curs",
        "#r curs",
        "#n curs",
        "#t curs",
    ),
    "cs": ("#. ročník", "první ročník", "druhý ročník", "třetí ročník", "čtvrtý ročník"),
    "da": ("#. år", "første år", "andet år", "tredje år", "#. studieår", "første studieår"),
    "de": (
        "#. studienjahr",
        "studienjahr #",
        "erstes studienjahr",
        "zweites studienjahr",
        "drittes studienjahr",
        "#. jahr",
        "erstes jahr",
        "zweites jahr",
        "drittes jahr",
    ),
    "es": (
        "primer curso",
        "segundo curso",
        "tercer curso",
        "cuarto curso",
        "#º curso",
        "#er curso",
        "primer año",
        "segundo año",
        "tercer año",
        "cuarto año",
        "#º año",
        "#er año",
    ),
    "et": (
        "#. kursus",
        "esimene kursus",
        "teine kursus",
        "kolmas kursus",
        "#. õppeaasta",
        "esimene õppeaasta",
        "teine õppeaasta",
        "kolmas õppeaasta",
    ),
    "fi": (
        "#. vuosi",
        "ensimmäinen vuosi",
        "toinen vuosi",
        "kolmas vuosi",
        "#. vuosikurssi",
        "ensimmäinen vuosikurssi",
        "ensimmäinen opiskeluvuosi",
    ),
    "fr": (
        "l#",
        "licence #",
        "#re année",
        "#ère année",
        "#er année",
        "#e année",
        "#ème année",
        "#eme année",
        "première année",
        "deuxième année",
        "seconde année",
        "troisième année",
        "année #",
    ),
    "it": ("primo anno", "secondo anno", "terzo anno", "#° anno", "#º anno", "anno #"),
    "ja": ("#年次", "#年生", "第#学年", "初年次"),
    "kk": ("# курс", "бірінші курс", "екінші курс", "үшінші курс", "төртінші курс"),
    "ko": ("#학년", "신입생"),
    "lt": ("# kursas", "pirmas kursas", "antras kursas", "trečias kursas", "pirmasis kursas"),
    "nb": (
        "#. år",
        "første år",
        "andre år",
        "tredje år",
        "#. studieår",
        "første studieår",
        "#. årskurs",
    ),
    "nl": ("eerste jaar", "tweede jaar", "derde jaar", "jaar #", "#e jaar", "propedeu*"),
    "nn": ("#. år", "fyrste år", "andre år", "tredje år", "#. studieår", "fyrste studieår"),
    "no": (
        "#. år",
        "første år",
        "andre år",
        "tredje år",
        "#. studieår",
        "første studieår",
        "#. årskurs",
    ),
    "pl": ("rok #", "# rok", "pierwszy rok", "drugi rok", "trzeci rok", "czwarty rok"),
    "pt": ("primeiro ano", "segundo ano", "terceiro ano", "quarto ano", "#º ano", "#o ano"),
    "ru": (
        "# курс",
        "первый курс",
        "второй курс",
        "третий курс",
        "четвертый курс",
        "# год обучения",
    ),
    "sk": ("#. ročník", "prvý ročník", "druhý ročník", "tretí ročník", "štvrtý ročník"),
    "sv": ("årskurs #", "år #", "första året", "andra året", "tredje året", "första år"),
    "th": ("ชั้นปีที่ #", "ปีที่ #", "ปี #"),
    "tr": ("#. sınıf", "birinci sınıf", "ikinci sınıf", "üçüncü sınıf", "dördüncü sınıf"),
    "zh": (
        "一年级",
        "一年級",
        "二年级",
        "二年級",
        "三年级",
        "三年級",
        "四年级",
        "四年級",
        "第一学年",
        "第一學年",
        "#年级",
        "#年級",
    ),
}
#: SP-1: the words that name a process of a programme — application, how to
#: apply, admission(s), enrolment, fees, procedure, deadlines — per language
#: of ``languages.json`` plus English, from the same dictionary pass and with
#: the same notation. A word that also names a field or a course is listed only
#: in a collocation that has the process sense: en "application" ("Computer
#: Science and Applications", "Application Development") only as "application
#: for/to/process/procedure/form/deadline" or "online application", en
#: "procedure" ("Criminal Law and Procedure") only as "procedure(s) for", and
#: fr/it/es/pt/ca "procédure/procedura/procedimiento/procedimento/procediment"
#: only followed by "de"/"di". Left out: the software sense of "application" in
#: every language, de "Verfahren" ("Verfahrenstechnik"; "Bewerbungsverfahren"
#: is in through "bewerbung*"), cs/sk "řízení"/"konanie" alone ("Řízení
#: podniku" is a programme), ko "지원" (also "support") and "전형" (also inside
#: "전형적"), and bare "termin*" stems (en "terminology").
_SUBPAGE_PROCESS_WORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "application for",
        "applications for",
        "application to",
        "application process",
        "application procedure",
        "application form",
        "application deadline*",
        "online application",
        "how to apply",
        "apply",
        "admission",
        "admissions",
        "enrolment",
        "enrollment",
        "enrol",
        "enroll",
        "registration",
        "fees",
        "fee",
        "tuition",
        "procedure for",
        "procedures for",
        "deadline",
        "deadlines",
        "entry requirements",
    ),
    "ca": (
        "admissió",
        "admissions",
        "preinscripció",
        "sol·licitud*",
        "sol·licitar",
        "matrícula",
        "inscripció",
        "taxes",
        "terminis",
        "procediment de",
    ),
    "cs": (
        "přijímací*",
        "přijetí",
        "přihlášk*",
        "uchazeč*",
        "zápis*",
        "poplat*",
        "školné",
        "termín",
        "termíny",
        "termínů",
    ),
    "da": (
        "ansøg*",
        "optagelse*",
        "indskrivning",
        "tilmelding",
        "studieafgift*",
        "gebyr*",
        "frist*",
        "sådan søger du",
    ),
    "de": (
        "bewerbung*",
        "bewerben",
        "zulassung*",
        "einschreibung*",
        "immatrikulation*",
        "anmeldung*",
        "studiengebühr*",
        "gebühren",
        "semesterbeitrag",
        "fristen",
    ),
    "es": (
        "admisión",
        "admisiones",
        "solicitud",
        "solicitudes",
        "solicitar",
        "inscripción",
        "preinscripción",
        "matrícula",
        "matriculación",
        "tasas",
        "aranceles",
        "plazo",
        "plazos",
        "procedimiento de",
    ),
    "et": (
        "vastuvõtt",
        "vastuvõtu*",
        "sisseastu*",
        "kandideeri*",
        "avaldus",
        "õppemaks*",
        "tähtaeg",
        "tähtaj*",
        "registreeri*",
    ),
    "fi": (
        "haku",
        "hakeminen",
        "hakemus",
        "hakuaika",
        "opiskelijavalinta*",
        "valintaperuste*",
        "sisäänpääsy*",
        "ilmoittautum*",
        "lukuvuosimaksu*",
        "määräaika*",
    ),
    "fr": (
        "candidature*",
        "candidater",
        "admission*",
        "inscription*",
        "inscrire",
        "frais",
        "procédure de",
        "procédures de",
        "date limite",
        "dates limites",
    ),
    "it": (
        "ammission*",
        "iscrizion*",
        "iscriversi",
        "immatricolazion*",
        "candidatur*",
        "bando",
        "bandi",
        "tasse",
        "scadenz*",
        "procedura di",
        "procedure di",
    ),
    "ja": ("入試", "入学試験", "出願", "募集要項", "学費", "授業料", "入学手続", "手続き", "締切"),
    "kk": ("қабылдау*", "өтінім*", "тіркеу*", "оқу ақысы", "төлем*", "мерзім*", "талапкер*"),
    "ko": ("입학", "모집", "원서", "입시", "등록금", "등록", "마감"),
    "lt": (
        "priėmim*",
        "stojant*",
        "stojim*",
        "prašym*",
        "registracij*",
        "mokesči*",
        "mokestis",
        "studijų kaina",
        "terminai",
        "procedūr*",
    ),
    "nb": ("søknad*", "søke", "søker", "søkere", "opptak*", "registrering", "avgift*", "frist*"),
    "nl": (
        "aanmeld*",
        "toelating*",
        "inschrijv*",
        "collegegeld*",
        "studiekosten",
        "deadline*",
        "procedure",
        "procedures",
    ),
    "nn": ("søknad*", "søkje", "søkjar*", "opptak*", "registrering", "avgift*", "frist*"),
    "no": ("søknad*", "søke", "søker", "søkere", "opptak*", "registrering", "avgift*", "frist*"),
    "pl": ("rekrutacj*", "kandydat*", "zapis*", "opłat*", "czesne", "terminy", "procedur*"),
    "pt": (
        "candidatura*",
        "candidatar",
        "admissão",
        "admissões",
        "ingresso",
        "inscrição",
        "inscrições",
        "matrícula*",
        "propina*",
        "mensalidade*",
        "prazo*",
        "procedimento de",
        "procedimentos de",
    ),
    "ru": (
        "приём",
        "приёмн*",
        "поступлени*",
        "поступающ*",
        "абитуриент*",
        "заявлени*",
        "зачислени*",
        "стоимость обучения",
        "оплат*",
        "сроки",
    ),
    "sk": (
        "prijímac*",
        "prijatie",
        "prihlášk*",
        "uchádzač*",
        "zápis*",
        "poplat*",
        "školné",
        "termín",
        "termíny",
    ),
    "sv": (
        "ansökan",
        "ansök*",
        "så söker du",
        "antagning*",
        "anmälan",
        "registrering",
        "studieavgift*",
        "avgift*",
    ),
    "th": (
        "รับสมัคร",
        "การสมัคร",
        "สมัครเรียน",
        "การรับเข้า",
        "ค่าธรรมเนียม",
        "ค่าเล่าเรียน",
        "ลงทะเบียน",
        "กำหนดการ",
    ),
    "tr": ("başvuru*", "kabul*", "kayıt*", "ücret*", "harç*", "prosedür*"),
    "zh": (
        "招生",
        "报名",
        "報名",
        "报考",
        "報考",
        "申请",
        "申請",
        "录取",
        "錄取",
        "入学",
        "入學",
        "注册",
        "註冊",
        "学费",
        "學費",
        "截止日期",
    ),
}
#: SP-1: the verdict for a page whose head names part of a programme, pinned
#: by tests; ``{}`` is the part word as the head spells it, folded. It starts
#: "page head ", so it is an identity refusal (``_IDENTITY_REFUSAL_PREFIXES``).
SUBPAGE_HEAD_VERDICT = "page head names part of a programme ({}), not the programme page"
_SUBPAGE_VERDICT_PREFIX = SUBPAGE_HEAD_VERDICT.split("{}", 1)[0]
#: SP-1: a path segment that only names a language ("en", "pt-br"); a lead
#: whose path is nothing else is a front page, not a parent programme lead.
_LANGUAGE_SEGMENT = re.compile(r"^[a-z]{2}(?:[-_][a-z]{2})?$")


@lru_cache(maxsize=8)
def _subpage_word_pattern(table: tuple[tuple[str, tuple[str, ...]], ...]) -> re.Pattern[str]:
    """SP-1: one pattern for every word of ``table``, folded like the head."""
    alternatives: list[str] = []
    for language, words in table:
        for word in words:
            endings = r"\w*" if word.endswith("*") else ""
            spelled = r"[\s-]+".join(
                r"[1-9](?!\d)".join(re.escape(piece) for piece in part.split("#"))
                for part in _fold(word.rstrip("*")).split()
            )
            if language in _UNSPACED_UNIT_LANGUAGES:
                alternatives.append(spelled)
            else:
                alternatives.append(rf"(?<!\w){spelled}{endings}(?!\w)")
    return re.compile("|".join(sorted(set(alternatives), key=len, reverse=True)))


def _subpage_word_in(text: str, fields: list[str]) -> str | None:
    """SP-1: the part word ``text`` opens on, before any programme title of its own.

    A head that names one study year or a process before it names a level or
    the subject ("L2 Informatique", "Application for the B.Sc. …") is that
    part's page. A head that names the programme first and the part after it
    ("Bachelor of Science in Computer Science — Admission requirements") is
    the programme's own page with a subtitle, and so is a head that names two
    or more years ("L1 L2 L3"): together they span the programme.
    """
    folded = _fold(text)
    if not folded.strip():
        return None
    year_pattern = _subpage_word_pattern(tuple(sorted(_SUBPAGE_YEAR_WORDS.items())))
    years = list(year_pattern.finditer(folded))
    if len({" ".join(found.group(0).split()) for found in years}) > 1:
        years = []
    process = _subpage_word_pattern(tuple(sorted(_SUBPAGE_PROCESS_WORDS.items())))
    found = min((*years, *process.finditer(folded)), key=lambda match: match.start(), default=None)
    if found is None:
        return None
    before = text[: found.start()] if len(folded) == len(text) else folded[: found.start()]
    if _page_classifier.degree_levels_named(before) or matches_field_text(before, fields):
        return None
    return " ".join(found.group(0).split())


def head_subpage_rejects(page: PageClassification, fields: list[str]) -> str | None:
    """SP-1: ``SUBPAGE_HEAD_VERDICT`` when the page's head names part of a programme.

    The head is CH-1's: the page's first ``h1`` and its title's first part
    (the rest of a title is the site). Either one naming only a part of the
    programme (``_subpage_word_in``) makes the page a sub-page.
    """
    parts = _title_parts(page.title or "")
    for text in (page.heading or "", parts[0] if parts else ""):
        word = _subpage_word_in(text, fields)
        if word is not None:
            return SUBPAGE_HEAD_VERDICT.format(word)
    return None


def is_subpage_refusal(verdict: str | None) -> bool:
    """SP-1: whether a ``profile_rejects`` verdict refused a sub-page head."""
    return bool(verdict) and (verdict or "").startswith(_SUBPAGE_VERDICT_PREFIX)


_SUBPAGE_VERDICT_WORD = re.compile(re.escape(_SUBPAGE_VERDICT_PREFIX) + r"(.+?)\), not ")


def is_process_subpage_refusal(verdict: str | None) -> bool:
    """SP-2: whether an SP-1 verdict refused a head for a process word, not a year."""
    if not is_subpage_refusal(verdict):
        return False
    found = _SUBPAGE_VERDICT_WORD.match(verdict or "")
    if found is None:
        return False
    process = _subpage_word_pattern(tuple(sorted(_SUBPAGE_PROCESS_WORDS.items())))
    return process.fullmatch(found.group(1)) is not None


def head_names_programme(page: PageClassification, level: str, fields: list[str]) -> bool:
    """SP-2: whether the page's ``h1`` names the requested level and subject."""
    heading = page.heading or ""
    return level in _page_classifier.degree_levels_named(heading) and matches_field_text(
        heading, fields
    )


def _path_segments(url: str) -> tuple[str, list[str]]:
    """SP-1: a URL's host (no ``www.``) and its non-empty path segments."""
    parts = urlparse(url)
    host = parts.netloc.lower().removeprefix("www.")
    return host, [segment for segment in (parts.path or "").split("/") if segment]


def subpage_parent_lead(subpage: Sequence[str], leads: Sequence[str]) -> str | None:
    """SP-1: the lead whose path sits above the sub-page's, nearest first, or ``None``.

    ``subpage`` is the URL read and the URL it ended at; ``leads`` the unread
    leads of the same candidate set, in order. A parent is on the same host
    and its path segments are a proper prefix of the sub-page's; a path of
    language segments only ("/en/") is a front page, never a parent.
    """
    best: tuple[int, int, str] | None = None
    for url in subpage:
        host, segments = _path_segments(url)
        for index, lead in enumerate(leads):
            lead_host, lead_segments = _path_segments(lead)
            if lead_host != host or not 0 < len(lead_segments) < len(segments):
                continue
            if segments[: len(lead_segments)] != lead_segments:
                continue
            if all(_LANGUAGE_SEGMENT.match(segment) for segment in lead_segments):
                continue
            rank = (-len(lead_segments), index, lead)
            if best is None or rank < best:
                best = rank
    return None if best is None else best[2]


#: SR-1: slug words that make a path segment a page about money.
_FEE_SLUG_WORDS = frozenset(
    {"tuition", "fee", "fees", "scholarship", "scholarships", "bursary", "bursaries"}
)
#: SR-1: a segment about costs ("costs", "cost-of-living"), but not a subject
#: that merely contains the word ("cost-engineering").
_COST_SEGMENT = re.compile(r"^(?:costs?|cost[-_]of[-_].*|costs?[-_]and[-_].*)$")


def _is_fee_path(path: str) -> bool:
    """SR-1: whether a path has a fee, tuition, cost or scholarship segment."""
    for segment in path.lower().split("/"):
        if _COST_SEGMENT.match(segment):
            return True
        if _FEE_SLUG_WORDS.intersection(re.split(r"[-_.]+", segment)):
            return True
    return False


#: Plan v3 change #2(b) (loss stages v3 2026-10-18 §3.1, §5 #2), off until a
#: paired run passes. ``_is_fee_path`` was consulted only under SR-1
#: (``FIELD_SLUG_SCORING``) and R3's evidence-only path, so Imperial's
#: ``…/2027/tuition-fees---2027/group-7---mathematics-and-computer-science/
#: standard-courses/home`` scored ``program_page`` 11 and its two
#: ``…/2027/entry-requirements---2027/mathematics-and-computer-science-for-ai``
#: sub-pages 7 — above or level with ``/2027/computing-beng`` (7) — and four of
#: the first seven confirm reads (≈22 s of a 55 s clock) went to them. On: a
#: path with a fee, tuition, cost or scholarship segment (``_is_fee_path``) or
#: an entry-requirements segment (``_is_entry_requirements_path``) never scores
#: as a programme page or catalogue, whatever SR-1 and R3 say; the URL keeps
#: its service category (costs, admissions). Fewer reads, same predicate. The
#: benchmark harness flips it per capture (``--fee-subpage-exclusion``). On
#: by default; False changes nothing.
FEE_SUBPAGE_EXCLUSION = (
    True  # on: runs 39134950075 / 951928 / 954132 / 956132 (0 losses, fewer reads)
)
#: Change #2(b): a path segment naming entry requirements, with or without an
#: intake year ("entry-requirements---2027"), or a requirements sub-page
#: ("standard-requirement"). Not a subject that merely contains the words.
_ENTRY_REQUIREMENTS_SEGMENT = re.compile(
    r"^(?:(?:entry|admission)[-_]+requirements?(?:[-_]+(?:19|20)\d{2})?"
    r"|standard[-_]+requirements?)(?:\.[a-z]+)?$"
)


def _is_entry_requirements_path(path: str) -> bool:
    """Change #2(b): whether a path has an entry-requirements segment."""
    return any(_ENTRY_REQUIREMENTS_SEGMENT.match(s) for s in path.lower().split("/") if s)


def _is_fee_or_entry_subpage(path: str) -> bool:
    """Change #2(b): a fee or entry-requirements path, under FEE_SUBPAGE_EXCLUSION."""
    return FEE_SUBPAGE_EXCLUSION and (_is_fee_path(path) or _is_entry_requirements_path(path))


def score_url(url: str, category: str) -> int:
    """How strongly a URL looks like it belongs to a category. 0 means no."""
    path = (urlparse(url).path or "").lower()
    if _url_excluded(path) or _NOT_A_PAGE_ABOUT_STUDYING.search(path):
        return 0
    if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG) and (
        _FUNDING_SEGMENT.search(path)
        or _NOT_A_PROGRAMME_PATH.search(path)
        or (FIELD_SLUG_SCORING and _is_fee_path(path))
        or _is_fee_or_entry_subpage(path)
    ):
        # NTU offered a scholarship page as the applicant's programme (the
        # "undergraduate" in the path outscored the "scholarships" beside it),
        # and rug.nl offered a research group's "BSc and MSc projects" page.
        # Neither is a programme, whatever else the path says.
        return 0
    signals = _URL_SIGNALS[category]
    if LOCALIZED_IDENTITY and category == PageCategory.PROGRAM_PAGE:
        signals = (*signals, *localized_program_signals())
    if LOCAL_CATALOGUE_ENTRY and category in _LOCAL_LISTING_SIGNALS:
        signals = (*signals, *_LOCAL_LISTING_SIGNALS[category])
    return sum(weight for pattern, weight in signals if re.search(pattern, path))


#: Plan rule UC-1 (evidence analysis 2026-10-17, §0 cause 4, §4 rank 4): the
#: ``/(bachelors?|masters?|undergraduate)/<slug>`` programme rule filed TCD's
#: ``/courses/undergraduate/fees`` as a programme lead (programme 9 against
#: costs 4), and with no level check on service categories
#: ``/courses/postgraduate/how-to-apply`` became the bachelor applicant's
#: admissions page in 12 of 12 repetitions. With UC-1 on, a URL whose last
#: path segment is a service word (fees, tuition, how-to-apply, apply,
#: admission(s), entry-requirements, scholarships, funding, deadlines, dates)
#: is filed under that service whatever level segment precedes it, and the
#: service categories (admissions, costs, scholarships) get the programme
#: categories' degree guard: a URL, or a navigation link text, naming another
#: level never fills the slot, and one naming the requested level gets the
#: degree bonus. Discovery only picks entry pages; the adapters still classify
#: what they read. Off by default; the benchmark harness flips it per capture
#: (``--service-page-priority``).
SERVICE_PAGE_PRIORITY = False
_SERVICE_SEGMENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (PageCategory.COSTS, re.compile(r"^(?:tuition|fees?|tuition[-_]fees?)$")),
    (
        PageCategory.ADMISSIONS,
        re.compile(
            r"^(?:how[-_]to[-_]apply|apply|admissions?|(?:entry|admission)[-_]requirements"
            r"|(?:application[-_])?deadlines|(?:key[-_])?dates|dates[-_]and[-_]deadlines)$"
        ),
    ),
    (PageCategory.SCHOLARSHIPS, re.compile(r"^(?:scholarships?|funding)$")),
)
SERVICE_CATEGORIES = (PageCategory.ADMISSIONS, PageCategory.COSTS, PageCategory.SCHOLARSHIPS)
#: Link text naming a level other than the requested one (UC-1 navigation guard).
_OTHER_LEVEL_LABEL: dict[str, re.Pattern[str]] = {
    "bachelor": re.compile(
        r"\b(?:msc|master'?s?|phd|doctoral|doctorate|postgraduate|graduate)\b", re.I
    ),
    "master": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|phd|doctoral|doctorate)\b", re.I),
    "phd": re.compile(r"\b(?:undergraduate|bachelor'?s?|bsc|msc|master'?s?)\b", re.I),
}


def service_category(url: str) -> str | None:
    """UC-1: the service a URL's last path segment names, if it names one."""
    path = (urlparse(url).path or "").lower()
    if _url_excluded(path) or _NOT_A_PAGE_ABOUT_STUDYING.search(path):
        return None
    segments = [s for s in path.split("/") if s]
    if not segments:
        return None
    last = re.sub(r"\.(?:html?|php|aspx?)$", "", segments[-1])
    for category, pattern in _SERVICE_SEGMENTS:
        if pattern.match(last):
            return category
    return None


def label_names_other_level(label: str, degree: str) -> bool:
    """UC-1: whether a link's text names a level the applicant did not ask for."""
    pattern = _OTHER_LEVEL_LABEL.get(str(degree))
    return bool(pattern and pattern.search(label))


def categorise_url(url: str) -> tuple[str | None, int]:
    """The category a URL best fits, and its score."""
    best: tuple[str | None, int] = (None, 0)
    for category in PageCategory.ALL:
        score = score_url(url, category)
        if score > best[1]:
            best = (category, score)
    if SERVICE_PAGE_PRIORITY:
        service = service_category(url)
        if service is not None:
            return service, max(score_url(url, service), 4)
    return best


def matches_field(url: str, fields: list[str]) -> int:
    """Extra weight when a URL names one of the applicant's subjects.

    Weighted heavily on purpose. Every bachelor programme URL on a site scores
    the same on structure, so with a small bonus the three slots went to
    whichever programmes sorted first — Delft answered a computer science
    applicant with aerospace engineering, applied mathematics and applied
    physics. Subject match has to dominate structural match.
    """
    path = (urlparse(url).path or "").lower()
    if FIELD_SLUG_SCORING:
        return _field_slug_bonus(path, fields)
    bonus = 0
    for field_name in fields:
        # One field counts once, under whichever of its names the path uses.
        best = 0
        local = {_fold(n) for n in _localized_names(field_name)}
        for name in with_strong_aliases([field_name]):
            if _fold(name) in local:
                # LI-1: a localized alias counts as a whole slug word, so
                # "informatik" scores and "wirtschaftsinformatik" does not.
                best = max(best, 8 * _whole_words_in_path(name, path))
                continue
            words = {w for w in re.split(r"[^a-z]+", name.lower()) if len(w) > 3}
            best = max(best, 8 * sum(1 for w in words if w in path))
        bonus += best
    return bonus


def _field_slug_bonus(path: str, fields: list[str]) -> int:
    """``matches_field`` under SR-1: a whole phrase in the slug, or nothing.

    Each requested field earns 8 per word of its own name, once, when the
    path's slug words carry that name or any of its strong (or localized)
    aliases as consecutive whole words. "computing-beng" therefore counts as
    fully as "computer-science", and "materials-science" not at all.
    """
    slug = _folded_words(unquote(path))
    bonus = 0
    for field_name in fields:
        weight = 8 * max(len(_folded_words(field_name)), 1)
        for name in with_strong_aliases([field_name]):
            if _phrase_in_slug(_folded_words(name), slug):
                bonus += weight
                break
    return bonus


def _phrase_in_slug(phrase: list[str], slug: list[str]) -> bool:
    """SR-1: whether ``phrase`` occurs in ``slug`` as consecutive whole words."""
    if not phrase:
        return False
    width = len(phrase)
    return any(slug[i : i + width] == phrase for i in range(len(slug) - width + 1))


def _whole_words_in_path(name: str, path: str) -> int:
    """How many of a name's words a URL path carries as whole slug words (LI-1)."""
    folded = _fold(unquote(path))
    return sum(
        1
        for w in set(_folded_words(name))
        if re.search(rf"(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])", folded)
    )


def _fold(text: str) -> str:
    """Casefold and strip accents, as the ontology does for lookup (LI-1)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _folded_words(text: str) -> list[str]:
    """Words longer than three letters in any script, accents folded (LI-1)."""
    return [w for w in re.split(r"[\W\d_]+", _fold(text)) if len(w) > 3]


def _localized_names(field_name: str) -> tuple[str, ...]:
    """The ontology's localized aliases of a field while LI-1 is on, else none.

    Entries flagged ``LEXICON_V2`` join only while LX-1 is on as well; under
    R1 (``LOCALIZED_PAGE_IDENTITY``) those and R1's own entries join (16-Q4).
    """
    if not LOCALIZED_IDENTITY:
        return ()
    return localized_aliases(
        field_name, include_flagged=True, flags=_page_classifier.localized_alias_flags()
    )


@lru_cache(maxsize=64)
def _strong_aliases(field_name: str) -> tuple[str, ...]:
    key = canonical_field(field_name)
    if key is None:
        return ()
    concept = load_ontology().fields.get(key) or {}
    return tuple(concept.get("strong_aliases") or ())


def with_strong_aliases(fields: list[str]) -> list[str]:
    """The applicant's fields plus the ontology's strong aliases for each.

    Groningen calls its programme "Computing Science"; the ontology records that
    as the same field as "Computer Science", and discovery compared the words
    literally, so the programme page never scored as the applicant's subject.
    Only strong aliases: a related concept is never a match. Under LI-1 the
    localized aliases follow them: a strong alias in another language.
    """
    out: list[str] = []
    for field_name in fields:
        for name in (field_name, *_strong_aliases(field_name), *_localized_names(field_name)):
            if name.lower() not in (o.lower() for o in out):
                out.append(name)
    return out


def degree_level_named(url: str) -> str | None:
    """The degree level a URL names in its path, if it names one at all."""
    path = (urlparse(url).path or "").lower()
    if INTEGRATED_MASTERS_LEVEL and url_names_integrated_master(url):
        # IM-1: "/undergraduate/…-meng" names the entry route and the award;
        # the award is the level.
        return "master"
    if LOCALIZED_IDENTITY:
        found = _localized_degree_level(url, path)
    else:
        found = next(
            (
                level
                for level, slugs in _DEGREE_SLUGS.items()
                if any(re.search(rf"(^|[/-]){re.escape(slug)}([/-]|$)", path) for slug in slugs)
            ),
            None,
        )
    if found is None and (_page_classifier.LEXICON_V2 or _page_classifier.LOCALIZED_PAGE_IDENTITY):
        for level, pattern in _LX1_DEGREE_SLUGS:
            if re.search(rf"(^|[/-]){pattern}([/-]|$)", path):
                return level
    return found


#: LX-1 (``page_classifier.LEXICON_V2``, and R1 which absorbs it): IIT Delhi's
#: ``/b-tech-program/``.
_LX1_DEGREE_SLUGS: tuple[tuple[str, str], ...] = (
    ("bachelor", r"b-?tech"),
    ("master", r"m-?tech"),
)


def _localized_degree_level(url: str, path: str) -> str | None:
    """``degree_level_named`` under LI-1: local degree words join the table."""
    path = _TURKISH_ASSOCIATE.sub(r"\1", _fold(unquote(path)))

    def named(pattern: str) -> bool:
        return re.search(rf"(^|[/-]){pattern}([/-]|$)", path) is not None

    for level, pattern in _localized_degree_compounds():
        if named(pattern):
            return level
    for level, slugs in _DEGREE_SLUGS.items():
        if any(named(re.escape(slug)) for slug in slugs):
            return level
    for level, pattern in _LOCALIZED_DEGREE_SLUGS:
        if named(pattern):
            return level
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".se") and named(_SWEDISH_KANDIDAT):
        return "bachelor"
    if _page_classifier.LEXICON_LANGUAGE_COVERAGE:
        for level, pattern in _LV1_DEGREE_SLUGS:
            if named(pattern):
                return level
    return None


#: A path segment that ends with a listing word. UBC's catalogue lives at
#: ``/applying-ubc/how-to-apply/degrees-programs/``, which scores higher as an
#: admissions page than as a catalogue — so whether a page is worth walking for
#: programmes is asked separately from which category it best fits.
_CATALOGUE_PATH = re.compile(
    r"/[a-z0-9-]*(programmes?|programs?|degrees?|courses?|studies)/?$", re.IGNORECASE
)


@lru_cache(maxsize=1)
def _registry_hosts_by_domain() -> dict[str, frozenset[str]]:
    """Registrable domain to the hosts this institution's verified seeds name.

    The registry records a homepage and seed URLs per institution, each
    carrying a ``seeds_verified_on`` date: human-checked data about a real
    university. That makes it the sanctioned place for institution-specific
    knowledge — the phase guide allows exactly this and forbids the
    alternative, a rule in code that knows something about one university.

    It answers a question nothing else in the pipeline could: which of an
    institution's many hosts actually publishes its programmes. Toronto's
    seeds name ``future.utoronto.ca``; ``utm.utoronto.ca`` and
    ``utsc.utoronto.ca`` are other campuses and are not named.
    """
    try:
        entries = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a broken registry is a deploy problem
        return {}

    by_domain: dict[str, set[str]] = {}
    for entry in entries:
        urls = [entry.get("homepage") or ""]
        urls += [u for u in (entry.get("seeds") or {}).values() if u]
        hosts = {h for h in (urlparse(u).hostname or "" for u in urls) if h}
        if not hosts:
            continue
        domain = registrable_domain(next(iter(hosts)))
        if domain:
            by_domain.setdefault(domain, set()).update(hosts)
    return {domain: frozenset(hosts) for domain, hosts in by_domain.items()}


def is_seed_host(url: str) -> bool:
    """Whether this URL sits on a host the institution's verified seeds name.

    ``www.`` is ignored on both sides: a registry that records ``www.rug.nl``
    is naming the same host as a search result on ``rug.nl``.
    """
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if not host:
        return False
    named = _registry_hosts_by_domain().get(registrable_domain(host), frozenset())
    return any(host == h.lower().removeprefix("www.") for h in named)


def is_excluded_path(url: str) -> bool:
    """Whether a URL is one of the pages a programme search never wants.

    News, events, vacancies, shops, logins and static media. Public because
    the search package applies the same rule to provider results, and a second
    copy of this list would drift from this one within a release.
    """
    return bool(_url_excluded(urlparse(url).path or ""))


def looks_like_catalogue(url: str) -> bool:
    """Whether a URL looks like a page that lists programmes."""
    path = urlparse(url).path or ""
    if _url_excluded(path):
        return False
    if LOCAL_CATALOGUE_ENTRY and _LOCAL_CATALOGUE_PATH.search(path):
        return True
    return bool(_CATALOGUE_PATH.search(path))


def matches_field_text(label: str, fields: list[str]) -> bool:
    """Whether a link's own text names one of the applicant's subjects.

    A catalogue page links to its programmes under the university's own names
    for them, and those names are often nowhere in the URL: Toronto's bachelor
    lead is ``/data-computer-science`` behind the text "Data & Computer
    Science", which no path pattern for "programmes" would ever match.
    """
    if SUBJECT_TITLE_SHAPES:
        return subject_head_verdict(label, fields) == "field"
    return _matches_field_words(label, fields)


def _matches_field_words(
    label: str, fields: list[str], extra_filler: frozenset[str] = frozenset()
) -> bool:
    """The filler rule on ``label``'s words; ``extra_filler`` is R2's."""
    if LOCALIZED_IDENTITY:
        return _matches_field_text_localized(label, fields, extra_filler)
    words = {w for w in re.split(r"[^a-z]+", label.lower()) if len(w) > 3}
    if not words:
        return False
    own = {f.lower() for f in fields}
    for field_name in with_strong_aliases(fields):
        wanted = {w for w in re.split(r"[^a-z]+", field_name.lower()) if len(w) > 3}
        if not wanted or not wanted <= words:
            continue
        if field_name.lower() in own:
            return True
        # An alias names the field only when nothing else in the title names
        # another subject: "Informatics" is computer science, "Business
        # Informatics" is not, and "Computing and Data Science" is not
        # "Computing" (run 50, Vienna and HKU).
        if words - wanted <= _title_filler() | extra_filler:
            return True
    return False


# --- R2: subject title shapes (SUBJECT_TITLE_SHAPES) ------------------------

#: R2: what introduces a subtitle — a colon (also full-width) or a spaced dash.
_SUBTITLE_MARK = re.compile(r"\s*[:：]\s*|\s+[-–—]\s+")
#: R2: a bracketed part of a title, ASCII or full-width brackets.
_BRACKETED = re.compile(r"[(（]([^()（）]*)[)）]")
#: R2: an award name, which names the degree's faculty, not the subject
#: (19-Q3): "Bachelor of Science", "Bachelor of Engineering", "Bachelor of
#: Science in Engineering". Folded text. "Bachelor of Computing" is not one:
#: "computing" is an alias of the field itself.
_AWARD_NAME = re.compile(
    r"\b(?:bachelor|master|associate)(?:'?s)?(?:\s+degree)?\s+of\s+"
    r"(?:(?:applied\s+)?sciences?(?:\s+in\s+engineering)?|arts|engineering|technology)\b"
)
#: R2: form words that name no subject, in any language (19-Q2; R1 left
#: "studieprogramma", "专业" and "学科" to R2), plus the bachelor's
#: abbreviations long enough to be words. Accents folded. Master's words are
#: never filler.
_SUBJECT_FORM_FILLER = frozenset(
    _fold(word)
    for word in (
        "studieprogramma",
        "studieprogram",
        "studieprogrammet",
        "studiengänge",
        "opleiding",
        "beng",
        "btech",
        "专业",
        "学科",
    )
)
#: R2: a bracketed single word that is filler there and only there
#: ("(International)" is a form; "International Business" is a subject).
_BRACKET_ONLY_FILLER = frozenset({"international"})
#: R2: the related fields the owner listed (19-Q4, glossary "Related field"),
#: as title words; the ontology's ``related_not_equivalent`` heads join them
#: per field (``_related_heads``).
_RELATED_FIELD_WORDS = frozenset(
    {
        "business",
        "engineering",
        "economics",
        "economic",
        "mathematics",
        "mathematical",
        "maths",
        "math",
    }
)
#: R2: the word that joins two subjects in the "… and Economics" shape.
_JOINING_WORD = "and"


@lru_cache(maxsize=1)
def _title_places() -> frozenset[str]:
    """R2: place names a title may carry in brackets, folded.

    The seed rows' cities and countries and the registry's cities — data the
    catalogue already holds, the same for every institution. Whether a place
    is the institution's own is CG-1's question (``foreign_campus_named``),
    which ``profile_rejects`` still asks after the subject.
    """
    names: set[str] = set()
    seed = Path(__file__).resolve().parents[2] / "catalogue" / "unimatch_top500_seed.json"
    try:
        rows = json.loads(seed.read_text(encoding="utf-8")).get("universities") or []
    except (OSError, ValueError, AttributeError):  # pragma: no cover - a deploy problem
        rows = []
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a deploy problem
        registry = []
    for row in [*rows, *registry]:
        if not isinstance(row, dict):
            continue
        for key in ("city", "country"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                names.add(" ".join(_fold(value).split()))
    return frozenset(names)


def _subject_filler() -> frozenset[str]:
    """R2: every word that names no subject under the flags in force."""
    filler = _title_filler() | _LOCAL_TITLE_FILLER | _SUBJECT_FORM_FILLER
    if _page_classifier.LOCALIZED_PAGE_IDENTITY:
        filler = filler | _LOCALIZED_DEGREE_FILLER
    return filler


def _without_award(text: str) -> str:
    """R2: ``text`` folded, with award names taken out."""
    return _AWARD_NAME.sub(" ", _fold(text))


def _names_no_subject(segment: str, filler: frozenset[str]) -> bool:
    """R2: whether a title part holds only degree, form or award words."""
    text = _without_award(segment)
    if _UNSPACED_SCRIPT.search(text):
        for word in (
            *_UNSPACED_DEGREE_FILLER,
            *sorted(_SUBJECT_FORM_FILLER, key=len, reverse=True),
        ):
            text = text.replace(word, " ")
        if _UNSPACED_SCRIPT.search(text) and not all(
            w in filler for w in re.split(r"[\W\d_]+", text) if _UNSPACED_SCRIPT.search(w)
        ):
            return False
    return all(w in filler for w in _folded_words(text))


def subject_head(title: str) -> str:
    """R2: the part of a programme title that names its subject (19 Q1-Q2).

    A bracketed place, a bracketed single filler word and an empty bracket
    are dropped; the title is cut at its first subtitle mark and the part
    before it is the head — unless that part names no subject at all
    ("Bachelor: …", "BTech in CSE – …", "KIT - Study programs - …"), in
    which case the next part is. The tail is ignored.
    """
    filler = _subject_filler()

    def bracket(match: re.Match[str]) -> str:
        inner = match.group(1)
        words = _folded_words(inner)
        if " ".join(_fold(inner).split()) in _title_places():
            return " "
        if not words and not _UNSPACED_SCRIPT.search(inner):
            return " "
        if len(words) == 1 and (words[0] in filler or words[0] in _BRACKET_ONLY_FILLER):
            return " "
        return match.group(0)

    text = _BRACKETED.sub(bracket, title or "")
    parts = [part for part in _SUBTITLE_MARK.split(text) if part.strip()]
    for part in parts:
        if not _names_no_subject(part, filler):
            return part.strip()
    return parts[0].strip() if parts else ""


def _shape_tokens(text: str) -> list[str]:
    """R2: every word of ``text`` in order, short ones too; "&" and "+" read as "and"."""
    text = re.sub(r"[&+]", f" {_JOINING_WORD} ", _without_award(text))
    return [w for w in re.split(r"[\W\d_]+", text) if w]


@lru_cache(maxsize=64)
def _related_heads(field_name: str) -> tuple[tuple[str, ...], ...]:
    """R2: the ontology's ``related_not_equivalent`` heads of a field, as words.

    A head that contains the field itself ("computer science and
    engineering") is left out: its related word is already in the list.
    """
    key = canonical_field(field_name)
    concept = (load_ontology().fields.get(key) or {}) if key else {}
    own = set(_folded_words(field_name))
    heads = []
    for term in concept.get("related_not_equivalent") or ():
        words = tuple(_shape_tokens(term))
        if words and not own <= set(words):
            heads.append(words)
    return tuple(heads)


def _same_word(token: str, word: str) -> bool:
    return token == word or token == f"{word}s"


def _field_span(tokens: list[str], name: str) -> tuple[int, int] | None:
    """R2: where ``name`` stands in ``tokens``: its first whole run, else its words."""
    wanted = _shape_tokens(name)
    if not wanted:
        return None
    for start in range(len(tokens) - len(wanted) + 1):
        if all(_same_word(tokens[start + i], w) for i, w in enumerate(wanted)):
            return start, start + len(wanted) - 1
    significant = set(_folded_words(name))
    at = [i for i, t in enumerate(tokens) if any(_same_word(t, w) for w in significant)]
    return (min(at), max(at)) if at else None


def _related_shape(head: str, name: str, field_name: str) -> bool:
    """R2: whether ``head`` joins ``name`` to a related field in a listed shape.

    Two shapes only (19-Q4, 03-Q4): a related field before the field
    ("Business Science specialising in Computer Science", "Mathematics and
    Computer Science") or after it with "and" ("Computer Science and
    Economics"). "<field> and Engineering" never reaches here as a join
    (``_with_engineering_as_the_field``). Award names are not subjects ("Bachelor of Engineering in
    Computer Science" is the field); any other neighbour ("… (Software
    Engineering)", "… with a second major in Business") is left as today.
    """
    tokens = _shape_tokens(head)
    span = _field_span(tokens, name)
    if span is None:
        return False
    first, last = span
    own = set(_folded_words(name))
    related: list[tuple[int, int]] = [
        (i, i)
        for i, t in enumerate(tokens)
        if t in _RELATED_FIELD_WORDS and not any(_same_word(t, w) for w in own)
    ]
    for words in _related_heads(field_name):
        for start in range(len(tokens) - len(words) + 1):
            if tuple(tokens[start : start + len(words)]) == words:
                related.append((start, start + len(words) - 1))
    if any(end < first for _start, end in related):
        return True
    joined = last + 1 < len(tokens) and tokens[last + 1] == _JOINING_WORD
    return joined and any(start > last + 1 for start, _end in related)


def subject_head_verdict(label: str, fields: list[str]) -> str | None:
    """R2: ``"field"``, ``"related"`` or ``None`` for a programme title.

    The subject head names the field when it holds the applicant's own
    words, or an alias with nothing but filler beside it; it names a
    related programme when it holds the field joined to a related field in
    a listed shape, whichever of the two the name is (symmetry, 19-Q4).
    """
    raw = subject_head(label)
    if not raw:
        return None
    # Presence is read on the head as written (an award's "Science" counts,
    # as it always has); the shapes and the filler test on the head without
    # award names.
    head_words = set(_folded_words(raw))
    head = _without_award(raw)
    for field_name in fields:
        head = _with_engineering_as_the_field(head, with_strong_aliases([field_name]))
    related = False
    for field_name in fields:
        for name in with_strong_aliases([field_name]):
            wanted = set(_folded_words(name))
            if wanted and wanted <= head_words and _related_shape(head, name, field_name):
                related = True
    if related:
        return "related"
    if _matches_field_words(head, fields, _subject_filler()):
        return "field"
    return None


def _with_engineering_as_the_field(head: str, names: list[str]) -> str:
    """R2 (19-Q4 as amended): "<field> and Engineering" is the field itself.

    The owner ruled that "Computer Science and Engineering" *is* the
    computer-science programme (Delft's gold page, IIT Delhi's CSE), so
    " and Engineering" straight after one of the field's names is taken out
    of the folded head before the shapes are read; every other joined field
    stays related ("Computer Science and Economics", "Mathematics and
    Computer Science"). The ontology's ``related_not_equivalent`` entry
    "computer science and engineering" names no related head of its own
    (``_related_heads`` leaves out a head containing the field), and it holds
    no local-language form of this shape, so none is added here.
    """
    for name in names:
        words = _fold(name).split()
        if not words:
            continue
        spelled = r"\s+".join(re.escape(word) for word in words)
        pattern = rf"(?<![^\W\d_])({spelled}s?)\s*(?:\band\b|&|\+)\s*engineering\b"
        head = re.sub(pattern, r"\1", head)
    return head


#: R2: the words of ``profile_rejects``'s verdict for a related programme.
RELATED_PROGRAMME_VERDICT = "names a related programme"


def _slug_subject(url: str) -> str:
    """R2b: a URL's last path segment as words ("computing-beng" -> "computing beng")."""
    segment = unquote((urlparse(url).path or "").rstrip("/").rsplit("/", 1)[-1])
    segment = re.sub(r"\.(?:php|html?|aspx?|jsp)$", "", segment, flags=re.I)
    return " ".join(w for w in re.split(r"[-_.+]+", segment) if w)


def _parent_path(url: str) -> tuple[str, str]:
    """R2b: a URL's host and the path above its last segment."""
    parts = urlparse(url)
    return parts.netloc.lower(), (parts.path or "").rstrip("/").rsplit("/", 1)[0]


def _queue_field_sibling(
    related: tuple[str, str],
    queued: list[str],
    reads: list[str],
    position: int,
    fields: list[str],
    level: str,
) -> list[str]:
    """R2b: after a related verdict, the field's own page beside it is read next.

    A related programme is never the programme (19-Q4, 03-Q3), but it says
    where the institution keeps its programme pages: Imperial's
    ``/2027/mathematics-computer-science-beng`` stands beside
    ``/2027/computing-beng``, which the sitemap kept at rank 37 of 40 and the
    eight confirm reads never reached, so no programme page was confirmed and
    the deadline only that page states was lost. ``related`` is the URL read
    and the URL it ended at (Imperial redirects ``/2027/…`` to the yearless
    path). The best-ranked unread kept candidate in the same directory as
    either whose last path segment names the field
    (the same subject-head rule, on the slug) and no other degree level takes
    the next place, inside the same read cap — one read moves, none is added.
    The page itself still has to pass ``profile_rejects``.
    """
    places = {_parent_path(u) for u in related}
    done = set(reads[:position]) | set(related)
    for url in queued:
        if url in done or _parent_path(url) not in places:
            continue
        if names_other_degree_level(url, level):
            continue
        if not matches_field_text(_slug_subject(url), fields):
            continue
        rest = [u for u in reads[position:] if u != url]
        return [*reads[:position], url, *rest][:MAX_PROGRAM_CANDIDATES_CHECKED]
    return reads


def _queue_subpage_parent(
    subpage: tuple[str, str],
    queued: list[str],
    reads: list[str],
    position: int,
    trace: DiscoveryTrace,
) -> list[str]:
    """SP-1 (confirm stage): the sub-page's parent candidate takes the next read.

    Inside the same read cap, as R2b's sibling: one read moves, none is added.
    """
    done = set(reads[:position]) | set(subpage)
    parent = subpage_parent_lead(subpage, [url for url in queued if url not in done])
    if parent is None:
        return reads
    trace.errors.append(f"SP-1: reading {parent} next, above the sub-page {subpage[0]}")
    rest = [url for url in reads[position:] if url != parent]
    return [*reads[:position], parent, *rest][:MAX_PROGRAM_CANDIDATES_CHECKED]


def _read_subpage_parent_next(
    queue: list[Any], subpage: tuple[str, str], visited: set[str], trace: DiscoveryTrace
) -> None:
    """SP-1 (identity recovery): the sub-page's parent lead moves to the queue's head.

    Only a lead already in the queue moves; no lead and no search is added.
    """
    unread = [lead.url for lead in queue if lead.url not in visited]
    parent = subpage_parent_lead(subpage, unread)
    if parent is None:
        return
    index = next(i for i, lead in enumerate(queue) if lead.url == parent)
    queue.insert(0, queue.pop(index))
    trace.errors.append(f"SP-1: reading {parent} next, above the sub-page {subpage[0]}")


#: Plan rule QT-1 (miss stages 2026-10-19 §3.2), off until a paired run
#: passes. SB-1 stops identity recovery at its first confirmation; on ubc and
#: unsw that confirmation was a qualified sibling of the gold (UBC's B.A. of
#: ``computer-science-vancouver-bsc``; UNSW's ``bachelor-of-commerce-computer-
#: science`` of ``bachelor-of-computer-science``), and the gold sat unread at
#: order #3 behind an unlabelled page that "read the next candidate" would
#: have confirmed instead (§3.1). On: after a confirmation, the one unread lead
#: that is the confirmed URL's *qualifier twin* (:func:`qualifier_twin`) is
#: read before SB-1 stops — one check, metered like any recovery read, judged
#: by the same ``profile_rejects`` — and kept as a second programme page when
#: it passes. No lead other than a twin is read; no lead is added, no query
#: sent. On by default since replays rp-qt1c (ubc and unsw hits, no new wrong
#: page in normal or knockout runs, no stable claim loss); the off arm is
#: ``--no-read-qualifier-twin``.
CONFIRM_READS_QUALIFIER_TWIN = True
#: LL-1 (MISS_STAGES_2026-10-19 §3, candidate 6): recovery's listing follow-up
#: reads a listing's links in the listing's own words. kaznu's bachelor
#: listing (dev2) wraps each programme in one card anchor whose text runs the
#: code, the name and a description together ("6B06104 Компьютерные науки
#: Целью образовательной программы …"), so no label matched the field although
#: the name is an ontology alias; msu's ``cs.msu.ru/education/bachelors``
#: (dev3), headed "Бакалавриат", was refused on subject and, not being typed a
#: catalogue, its links were never looked at. On, for a refused read: (a) a
#: link whose label does not match the field is still followed when the first
#: heading inside its anchor (``WalkerLink.heading``) does, through the same
#: ``matches_field_text`` - the applicant's words, the ontology's strong and
#: localized aliases, nothing new; (b) a page whose head names only the
#: requested level (:func:`page_classifier.head_names_only_a_level`, the degree
#: words in force) has its links followed as a listing's are. Same read cap, same
#: ``score_link`` hard rejects. Off by default; the harness flips it per capture
#: (``--listing-follows-local-aliases``). False changes nothing.
LISTING_FOLLOWS_LOCAL_ALIASES = False
#: QT-1c: the TB-1 read kind the twin is asked as before it uses SB-1b's
#: reserve past the deadline (``_twin_reserve``): an optional discovery read
#: that must leave the verify and the core reserves.
QUALIFIER_TWIN_READ_KIND = "discovery_extra"


def _slug_tokens(url: str) -> tuple[str, str, str, list[str]] | None:
    """QT-1: (host, parent path, suffix, last-segment tokens) of a URL, lowercased."""
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    segments = unquote(parts.path or "").lower().rstrip("/").split("/")
    if not host or len(segments) < 2 or not segments[-1]:
        return None
    slug, dot, suffix = segments[-1].partition(".")
    tokens = [token for token in slug.split("-") if token]
    if not tokens:
        return None
    return host, "/".join(segments[:-1]), dot + suffix, tokens


def _one_token_removed(longer: list[str], shorter: list[str]) -> bool:
    return len(longer) == len(shorter) + 1 and any(
        longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer))
    )


def qualifier_twin(confirmed_url: str, candidates: list[str], level: str) -> str | None:
    """QT-1: the first candidate that is the confirmed URL's qualifier twin.

    A twin has the confirmed URL's host and path up to its last segment, and
    its last segment's ``-`` tokens are the confirmed slug's **minus exactly
    one token** (``bachelor-of-commerce-computer-science`` →
    ``bachelor-of-computer-science``) or the same tokens with **exactly one
    swapped between two degree slugs of the requested level**
    (``_DEGREE_SLUGS``: ``computer-science-vancouver-ba`` → ``…-bsc``). No
    word table of its own: a candidate differing in two tokens
    (``…-okanagan-bsc``) or in one token that is not a degree slug
    (``bachelor-of-science-computer-science``) is not a twin. The query and
    fragment are not read.
    """
    confirmed = _slug_tokens(confirmed_url)
    if confirmed is None:
        return None
    host, parent, suffix, tokens = confirmed
    degree_slugs = set(_DEGREE_SLUGS.get(level, ()))
    for url in candidates:
        other = _slug_tokens(url)
        if other is None or other[:3] != (host, parent, suffix):
            continue
        twin = other[3]
        if _one_token_removed(tokens, twin):
            return url
        if len(twin) == len(tokens):
            differ = [(a, b) for a, b in zip(tokens, twin, strict=True) if a != b]
            if len(differ) == 1 and set(differ[0]) <= degree_slugs:
                return url
    return None


def is_related_refusal(verdict: str | None) -> bool:
    """R2: whether a ``profile_rejects`` verdict refused a related programme."""
    return bool(verdict) and RELATED_PROGRAMME_VERDICT in (verdict or "")


#: Plan v3 change #2(a) (loss stages v3 2026-10-18 §5 #2), off until a paired
#: run passes. R1 reads the twin in the institution's language
#: (``local_alternate``) of **every** refused English page, in the confirm
#: stage (``_queue_english_alternate``) and in identity recovery; a page
#: refused for its *kind* ("reads as unknown, not a programme page") has a twin
#: of the same kind, so the read is wasted — r5 ON: kit 3 of 8 recovery reads,
#: rwth 3-4 of 8, puc 1, ctu 1. On: the local twin is read only when the page
#: was refused on its identity — subject (including R2's related verdict) or
#: degree level (``is_identity_refusal``). The English twin (LI-1) is
#: unchanged. The benchmark harness flips it per capture
#: (``--local-twin-on-identity-refusal``). On by default; False changes nothing.
LOCAL_TWIN_ON_IDENTITY_REFUSAL = True  # on: same runs
#: Change #2(a): the ``profile_rejects`` verdicts that refuse a programme
#: page's identity (subject or level), not its kind or campus.
_IDENTITY_REFUSAL_PREFIXES = (
    "page subject ",
    "page names degree level ",
    "page names an integrated master's",
    # CH-1: the unit verdict (``HEAD_UNIT_VERDICT``) and the head's level and
    # subject verdicts.
    "page head ",
)


def is_identity_refusal(verdict: str | None) -> bool:
    """Change #2(a): whether a ``profile_rejects`` verdict refused subject or level."""
    return bool(verdict) and (verdict or "").startswith(_IDENTITY_REFUSAL_PREFIXES)


def local_twin_wanted(verdict: str | None) -> bool:
    """R1 / change #2(a): whether a refused page's local-language twin is read.

    Off (the default): every refused page's twin, as R1 has it. On: only a
    page refused on its subject or level.
    """
    if verdict is None:
        return False
    return not LOCAL_TWIN_ON_IDENTITY_REFUSAL or is_identity_refusal(verdict)


#: Plan rule FP-1, off until a paired run passes. Identity recovery treats an
#: UNKNOWN page as a listing and accepts it when ``_listed_programme`` finds a
#: full degree title on it, so a faculty site's front page ("Home", path ``/``)
#: reached from the entry-point hop was confirmed as the programme page in the
#: repetitions where search did not return the programme's own page (HKU,
#: baseline 2: 2 of 4). On: a URL whose path is the host root and that has no
#: query is never confirmed as a programme page by identity recovery; it is
#: refused like any listing, so its own matching links are read next. The
#: benchmark harness flips it per capture (``--front-page-not-programme``).
#: On by default; False changes nothing.
# on: runs 39164210866/212652/214438/215839, no stable loss, no wrong claim
FRONT_PAGE_NOT_PROGRAMME = True
#: FP-1: the verdict for a front page, pinned by tests.
FRONT_PAGE_VERDICT = "a site's front page is not a programme page"


def is_front_page(url: str) -> bool:
    """FP-1: whether ``url`` is a host's root (path ``/`` or empty, no query)."""
    parts = urlparse(url)
    return bool(parts.netloc) and (parts.path or "/") == "/" and not parts.query


#: Plan rule EF-1, off until a paired run passes. Identity recovery stops at the
#: first page it accepts, in the provider's ranked order, and that order moves
#: between repetitions with the snippets: TCD's ``/courses/computer-science/``
#: was the top result of all three first-pass families every time, yet a joint
#: honours sibling ``/courses/computer-science-jh`` outscored it on BM25 in 2 of
#: 4 repetitions and was accepted first. On: in a single-field run, the search
#: leads whose last path segment names the requested field and nothing else
#: (``exact_field_slug``, IM-1's rule) are read first, those more query
#: families returned before the others; every other lead keeps its order. Only
#: the reading order changes: the same predicate, the same stop. The benchmark
#: harness flips it per capture (``--exact-field-lead-first``). False (the
#: default) changes nothing.
EXACT_FIELD_LEAD_FIRST = False


def exact_field_leads_first(candidates: Sequence[Any], fields: list[str]) -> list[Any]:
    """EF-1: exact-field leads first (most families first), the rest in order.

    ``sorted`` is stable, so leads that tie keep the provider's ranked order.
    """
    if not fields:
        return list(candidates)

    def key(candidate: Any) -> tuple[int, int]:
        if not exact_field_slug(candidate.url, fields):
            return (1, 0)
        return (0, -len(set(getattr(candidate, "found_by", ()) or ())))

    return sorted(candidates, key=key)


def _title_filler() -> frozenset[str]:
    """Title filler words, with SR-1's degree slug tokens while it is on."""
    if FIELD_SLUG_SCORING:
        return _TITLE_FILLER | _DEGREE_SLUG_FILLER
    return _TITLE_FILLER


def _matches_field_text_localized(
    label: str, fields: list[str], extra_filler: frozenset[str] = frozenset()
) -> bool:
    """``matches_field_text`` under LI-1: any script, accents folded.

    The same rule, with localized aliases among the names and local level and
    form words among the filler. Words are compared whole, so "Informatik"
    names computer science while "Wirtschaftsinformatik", "Bioinformatik" and
    "Medizininformatik" (one word each) do not, and "Ingegneria Informatica"
    is refused because "ingegneria" names another subject.
    """
    words = set(_folded_words(label))
    if not words:
        return False
    page_identity = _page_classifier.LOCALIZED_PAGE_IDENTITY
    if page_identity and _names_related_local_form(label, fields):
        # R1: "Ingeniería Informática", "Bilgisayar Mühendisliği", "计算机工程"
        # are neighbours, refused by name rather than by the filler rule's luck.
        return False
    own = {_fold(f) for f in fields}
    filler = _title_filler() | _LOCAL_TITLE_FILLER | extra_filler
    if page_identity:
        filler = filler | _LOCALIZED_DEGREE_FILLER
    for field_name in with_strong_aliases(fields):
        wanted = set(_folded_words(field_name))
        if not wanted or not wanted <= words:
            continue
        if _fold(field_name) in own:
            return True
        if words - wanted <= filler:
            return True
    if page_identity and _UNSPACED_SCRIPT.search(label):
        return _matches_unspaced_title(label, fields, filler)
    return False


def _names_related_local_form(label: str, fields: list[str]) -> bool:
    """R1: whether a title names a localized ``related_not_equivalent`` form."""
    folded = _fold(label)
    words = _folded_words(label)
    for field_name in fields:
        for term in localized_related_terms(
            field_name, flags=frozenset({"LOCALIZED_PAGE_IDENTITY"})
        ):
            if _UNSPACED_SCRIPT.search(term):
                if _fold(term) in folded:
                    return True
            elif _phrase_in_slug(_folded_words(term), words):
                return True
    return False


def _matches_unspaced_title(label: str, fields: list[str], filler: frozenset[str]) -> bool:
    """R1: an alias in a script written without spaces (ja, zh, ko, th).

    "计算机科学与技术专业" is one word to the whole-word rule, so the alias is
    taken out of the title as a string, then the local degree words; what is
    left must be filler. A leftover character of an unspaced script is never
    filler ("情報科学科" keeps "科"; the form-word rule is R2's).
    """
    folded = _fold(label)
    for name in with_strong_aliases(fields):
        alias = _fold(name)
        if not _UNSPACED_SCRIPT.search(alias) or alias not in folded:
            continue
        rest = folded.replace(alias, " ")
        lv1 = _LV1_UNSPACED_DEGREE_FILLER if _page_classifier.LEXICON_LANGUAGE_COVERAGE else ()
        for word in (*lv1, *_UNSPACED_DEGREE_FILLER):
            rest = rest.replace(word, " ")
        leftover = [
            w
            for w in re.split(r"[\W\d_]+", rest)
            if w and (_UNSPACED_SCRIPT.search(w) or len(w) > 3)
        ]
        if all(w in filler for w in leftover):
            return True
    return False


#: R1: characters of scripts written without spaces between words (Thai,
#: Hangul and its jamo — folding decomposes syllables — kana, CJK ideographs).
_UNSPACED_SCRIPT = re.compile(
    "[\u0e00-\u0e7f\u1100-\u11ff\u3040-\u30ff\u3130-\u318f"
    "\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]"
)
#: R1: bachelor's degree words in unspaced scripts, folded, longest first.
#: Master's words are never filler. Korean "학부" alone is a school, not a level.
_UNSPACED_DEGREE_FILLER: tuple[str, ...] = tuple(
    sorted(
        {
            _fold(w)
            for w in ("本科", "学士", "學士", "学部", "학사학위", "학사과정", "학사", "ปริญญาตรี")
        },
        key=len,
        reverse=True,
    )
)
#: LV-1 (``page_classifier.LEXICON_LANGUAGE_COVERAGE``): ja "学士課程", the
#: bachelor's course as MEXT's Central Council for Education names it
#: ("学士課程教育の構築に向けて", 2008; Kōjien s.v. 学士), left a "課程" over
#: once "学士" was taken out, so "情報科学 学士課程" did not name its subject.
_LV1_UNSPACED_DEGREE_FILLER: tuple[str, ...] = tuple(_fold(w) for w in ("学士課程", "學士課程"))


#: LI-1: title words that carry a bachelor level or a form in another
#: language, never a subject (accents folded). Master's words are absent on
#: purpose: a title saying "magistrale" is not let through on its subject when
#: the classifier missed its level. Every word is a dictionary or degree-law
#: word, or its folded/inflected form (sources per row in
#: HELDOUT_PROVENANCE_AUDIT_2026-10-20): it laurea, triennale, corso,
#: programma (DM 270/2004; Treccani); tr lisans(ı), program(ı) (Law No. 2547
#: art. 3; TDK s.v. program); cs/sk bakalář(ský), studijní / študijný (Act
#: No. 111/1998 Coll. §44-§45; Act No. 131/2002 Coll. §51-§52); ru/kk
#: бакалавр, бакалавриат transliterated (Federal Law 273-FZ art. 10); es
#: grado, licenciatura, programa (Real Decreto 822/2021; RAE DLE); fr licence
#: (Code de l'éducation art. D612-32-2); de Bachelorstudium,
#: Bachelorstudiengang, Studiengang, Studium, Programm (Duden); sv
#: kandidatprogram(met) (Högskoleförordningen bilaga 2, kandidatexamen).
_LOCAL_TITLE_FILLER = frozenset(
    {
        "laurea",
        "triennale",
        "lisans",
        "lisansi",
        "programi",
        "bakalar",
        "bakalarsky",
        "bakalarske",
        "bakalarska",
        "bakalavr",
        "bakalavriat",
        "grado",
        "licence",
        "licenciatura",
        "bachelorstudium",
        "bachelorstudiengang",
        "studiengang",
        "studium",
        "corso",
        "programa",
        "programma",
        "programm",
        "studijni",
        "studijny",
        "kandidatprogram",
        "kandidatprogrammet",
    }
)
#: R1 (``LOCALIZED_PAGE_IDENTITY``): the bachelor's words of
#: ``page_classifier._LOCALIZED_DEGREE_WORDS`` as title words (accents folded),
#: for the languages LI-1's list misses. Master's words stay out, as above.
#: Turkish dotless "ı" does not fold to "i", so LI-1's ASCII "lisansi" and
#: "programi" are listed again as written. Each word is a form of a degree-law
#: word cited at ``page_classifier._LOCALIZED_DEGREE_WORDS`` (re-checked in
#: HELDOUT_PROVENANCE_AUDIT_2026-10-20).
_LOCALIZED_DEGREE_FILLER = frozenset(
    _fold(word)
    for word in (
        "lisansı",
        "programı",
        "bakalaureus",
        "bakalaureuse",
        "bakalaureuseõpe",
        "bakalauras",
        "bakalauro",
        "bakalářský",
        "bakalářské",
        "bakalářského",
        "bakalársky",
        "bacharelado",
        "bacharel",
        "graduação",
        "licencjat",
        "licencjackie",
        "kandidaatti",
        "kandidaatin",
        "bachelorprogram",
        "bachelorprogramme",
        "bachelorprogrammet",
        "bacheloruddannelse",
        "bacheloruddannelsen",
        "bacheloropleiding",
        "bachelorgrad",
        "bachelorgraden",
        "bachelorstudier",
        "bachelorstudium",
        "grau",
        "бакалавриат",
        "бакалавр",
        "бакалавра",
    )
)


def english_alternate(url: str, html: str, domain: str) -> str | None:
    """The English twin a local-language page declares, if LI-1 may follow it.

    ``<link rel="alternate" hreflang="en…" href=…>`` on the same registrable
    domain as the page and the institution, and only when the page's own
    ``<html lang>`` names a language that is not English. A page that states
    no language is not followed: it may already be the English page.
    """
    head = html[:200_000]
    tag = _html_tag(head)
    lang = (_attributes(tag).get("lang") or "").strip().lower() if tag else ""
    if not lang or lang == "en" or lang.startswith("en-"):
        return None
    here = canonical_url(url)
    for link_tag in _link_tags(head):
        attrs = _attributes(link_tag)
        if "alternate" not in (attrs.get("rel") or "").lower().split():
            continue
        hreflang = (attrs.get("hreflang") or "").strip().lower()
        if not (hreflang == "en" or hreflang.startswith("en-")):
            continue
        href = html_unescape((attrs.get("href") or "").strip())
        if not href:
            continue
        link = page_link(url, href)
        if link is None:
            continue
        target = canonical_url(link)
        if target == here or not same_institution(target, domain):
            continue
        if registrable_domain(target) != registrable_domain(url):
            continue
        return target
    return None


def local_alternate(url: str, html: str, domain: str, country: str) -> str | None:
    """R1: the twin an English page declares in a language of the institution's country.

    The other direction of :func:`english_alternate`: ``<link rel="alternate"
    hreflang=…>`` whose primary subtag is one of ``languages.json``'s languages
    for ``country`` (never English), on the page's registrable domain and the
    institution's, and only when the page's own ``<html lang>`` is English.
    The language comes from the institution's country, never the applicant.
    """
    if not _page_classifier.LOCALIZED_PAGE_IDENTITY:
        return None
    languages = [code for code in country_languages(country) if code != "en"]
    if not languages:
        return None
    head = html[:200_000]
    tag = _html_tag(head)
    lang = (_attributes(tag).get("lang") or "").strip().lower() if tag else ""
    if not (lang == "en" or lang.startswith("en-")):
        return None
    here = canonical_url(url)
    for link_tag in _link_tags(head):
        attrs = _attributes(link_tag)
        if "alternate" not in (attrs.get("rel") or "").lower().split():
            continue
        hreflang = (attrs.get("hreflang") or "").strip().lower().split("-")[0]
        if hreflang not in languages:
            continue
        href = html_unescape((attrs.get("href") or "").strip())
        if not href:
            continue
        link = page_link(url, href)
        if link is None:
            continue
        target = canonical_url(link)
        if not target.startswith(("http://", "https://")) or target == here:
            continue
        if not same_institution(target, domain):
            continue
        if registrable_domain(target) != registrable_domain(url):
            continue
        return target
    return None


def declared_alternates(url: str, html: str, domain: str) -> list[str]:
    """Every language twin a page declares, whatever its own language (WF-17).

    ``<link rel="alternate" hreflang=… href=…>`` on the page's registrable
    domain and the institution's; ``x-default`` (a language chooser, not a
    twin) is left out. Recording only: nothing is read because of it.
    """
    head = (html or "")[:200_000]
    here = canonical_url(url)
    found: list[str] = []
    for link_tag in _link_tags(head):
        attrs = _attributes(link_tag)
        if "alternate" not in (attrs.get("rel") or "").lower().split():
            continue
        hreflang = (attrs.get("hreflang") or "").strip().lower()
        if not hreflang or hreflang == "x-default":
            continue
        href = html_unescape((attrs.get("href") or "").strip())
        if not href:
            continue
        link = page_link(url, href)
        if link is None:
            continue
        target = canonical_url(link)
        if not target.startswith(("http://", "https://")) or target == here:
            continue
        if not same_institution(target, domain):
            continue
        if registrable_domain(target) != registrable_domain(url):
            continue
        if target not in found:
            found.append(target)
    return found


# SR2-02: these run on every page read for identity, on up to 200,000
# characters an attacker writes, so each must be linear in its input. The
# plain forms (``<link\b[^>]*>``; an attribute name ``[-\w:.]*`` that may
# start anywhere) restarted a full scan at every ``<link`` with no ``>``
# after it and at every character of a long name with no ``=``: quadratic,
# about 35 s for one 50,000-character name. What they match is unchanged.
#
# A tag is consumed possessively up to its ``>`` or, when there is none, to
# the end of the text, so the scan never restarts inside it; a match that
# reached the end without ``>`` is not a tag and is dropped.
_HTML_TAG = re.compile(r"<html\b[^>]*+>?", re.IGNORECASE)
_LINK_TAG = re.compile(r"<link\b[^>]*+>?", re.IGNORECASE)
# An attribute name is tried once per run of name characters ``[-\w:.]``, from
# the run's start: the leading characters that cannot begin a name (``-``,
# ``.``, digits, non-ASCII letters) are skipped possessively, and the name is
# taken possessively to the run's end. The old pattern found the same name,
# because a later start in the same run meets the same end and fails the same
# way, and a shorter name is followed by a name character, never ``=``.
_ATTRIBUTE = re.compile(
    r"""(?<![-\w:.])(?:[-.]|(?![a-zA-Z_:])\w)*+([a-zA-Z_:][-\w:.]*+)\s*+=\s*+"""
    r"""(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)


def _link_tags(head: str) -> list[str]:
    """Every complete ``<link …>`` tag in ``head``, in order."""
    return [tag for tag in _LINK_TAG.findall(head) if tag.endswith(">")]


def _html_tag(head: str) -> str | None:
    """The page's first complete ``<html …>`` tag, if it has one."""
    match = _HTML_TAG.search(head)
    return match.group(0) if match and match.group(0).endswith(">") else None


def _attributes(tag: str) -> dict[str, str]:
    """A tag's attributes, names lowercased."""
    out: dict[str, str] = {}
    for m in _ATTRIBUTE.finditer(tag):
        value = next((g for g in m.groups()[1:] if g is not None), "")
        out.setdefault(m.group(1).lower(), value)
    return out


def _distinct_fields(fields: list[str]) -> list[str]:
    """Keep applicant order while avoiding duplicate paid subject searches."""
    distinct: list[str] = []
    seen: set[str] = set()
    for raw in fields:
        field_name = raw.strip()
        key = field_name.casefold()
        if field_name and key not in seen:
            seen.add(key)
            distinct.append(field_name)
    return distinct


def _public_requested_fields(profile: ApplicantProfileIn, trace: DiscoveryTrace) -> list[str]:
    """Use only privacy-validated subjects for page matching and attribution.

    The search intent rejects profile-like text before sending it to a provider.
    The same boundary must hold for sitemap, navigation, and fetched-page
    identity; otherwise a rejected field could still become a claim or trace.
    """
    if trace.public_fields is None:
        from app.adapters.search.intent import _reject_applicant_data

        raw = list(profile.context.intended_fields)
        candidates = _distinct_fields(raw) if len(raw) > 1 else raw
        trace.public_fields = []
        for field_name in candidates:
            try:
                if not field_name.strip():
                    continue
                _reject_applicant_data("field", field_name)
            except ValueError:
                # QueryPrivacyError embeds the raw value. Never log it here.
                continue
            trace.public_fields.append(field_name)
    return trace.public_fields


def _field_named_by_subject(subject: str, fields: list[str]) -> str:
    """Name a requested field only when the fetched page's own subject does."""
    return next(
        (
            field_name
            for field_name in _distinct_fields(fields)
            if matches_field_text(subject, [field_name])
        ),
        "",
    )


#: Words a programme title carries besides its subject: level, form, and the
#: procedure notes Vienna appends ("with entrance exam procedure").
_TITLE_FILLER = frozenset(
    {
        "bachelor",
        "bachelors",
        "master",
        "masters",
        "degree",
        "programme",
        "program",
        "programmes",
        "programs",
        "hons",
        "honours",
        "honors",
        "with",
        "entrance",
        "exam",
        "procedure",
        "undergraduate",
        "study",
        "studies",
        "course",
        "english",
        "taught",
        "full",
        "time",
        "year",
        "years",
        "track",
        "major",
    }
)


def matches_degree(url: str, degree: str) -> int:
    """Positive when the URL names the right level, negative when it names another."""
    named = degree_level_named(url)
    if named is None:
        return 0
    return 4 if named == str(degree) else -6


def names_other_degree_level(url: str, degree: str) -> bool:
    """Whether a URL names a level the applicant did not ask for.

    Treated as an outright rejection rather than a score penalty. An MSc page
    is not a weak bachelor lead, it is the wrong page, and a subject-name bonus
    ("computer", "science") must not be able to outweigh the level.

    RK-2 (``retrieval.RETRIEVAL_RANK_V2``): a slug no slug rule reads is also
    read for R1's master's words (:func:`local_master_slug`), so the local
    signals that change adds can never promote a master's page.
    """
    named = degree_level_named(url)
    if named is None:
        from app.adapters.search import retrieval as _retrieval

        if _retrieval.RETRIEVAL_RANK_V2:
            named = local_master_slug(url)
    return named is not None and named != str(degree)


def local_master_slug(url: str) -> str | None:
    """RK-2: ``"master"`` when the URL's slug words hold one of R1's master's words.

    ``page_classifier._LOCALIZED_DEGREE_WORDS`` is the table the confirm step
    reads a page's level with; its master's words that are certain in any
    language (``navazující``, ``maestría``, ``Masterstudium``, ``maisteri…``,
    ``kandidatuddannelse``, ``pós-graduação``…) are tested on the path's words,
    accents folded. The slug table (``_LOCALIZED_DEGREE_SLUGS``) already reads
    ``magistr…``, ``laurea-magistrale`` and ``yuksek-lisans``; a word whose
    level depends on the page's language (Danish ``kandidat``) is not used.
    """
    words = re.sub(r"[\W_]+", " ", _fold(unquote(urlparse(url).path or ""))).strip()
    if not words:
        return None
    for pattern, level, languages in _page_classifier._LOCALIZED_DEGREE_WORDS:
        if level == "master" and languages is None and re.search(pattern, words):
            return "master"
    return None


#: Plan v3 rule R3 (SK-1, stage 2(a); decision: wayfinder ticket 18, URL
#: lexicon audit ticket 09), off until a paired run passes. The sitemap stage's
#: ``keep()`` dropped a URL the moment ``categorise_url`` found no structural
#: programme word, before the subject and level bonuses were added, so 7 of the
#: 39 development gold URLs never reached the confirm stage although their slug
#: names the subject: ``study.um.edu.my/bachelor-of-computer-science-<x>`` ×4,
#: ``ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/``,
#: ``aufnahmeverfahren.univie.ac.at/en/computer-science`` and Paris-Saclay's
#: ``/formation/licence/informatique``. On: a URL with no structural score is
#: kept as a programme lead when its slug names the requested subject (the
#: field or an alias as consecutive whole slug words) *and* the requested level
#: (both bonuses positive, R1's localized aliases and degree words included),
#: or names the subject as an exact field slug
#: (:func:`exact_field_slug`) and no other level; news, events, research, fee,
#: funding, dated and people paths never qualify. These evidence-only picks are
#: held apart from the structural ones and fill at most
#: ``MAX_EVIDENCE_ONLY_CANDIDATES`` of the ``MAX_CANDIDATES_PER_CATEGORY``
#: slots, only the slots the structural picks leave free, so they never
#: displace a URL with a structural score; the confirm order stays
#: score-descending and every pick is read and classified like any other. The
#: benchmark harness flips it per capture (``--sitemap-keep-evidence-sum``).
SITEMAP_KEEP_EVIDENCE_SUM = False
#: R3: evidence-only programme leads kept per institution (of the 40 slots).
MAX_EVIDENCE_ONLY_CANDIDATES = 10
#: R3: slug words that make an evidence-only URL an announcement, an event or
#: a person rather than a programme ("bachelor-computer-science-students-win").
_EVIDENCE_ONLY_REFUSED_WORDS = frozenset(
    {
        "news",
        "event",
        "events",
        "story",
        "stories",
        "press",
        "blog",
        "seminar",
        "seminars",
        "workshop",
        "workshops",
        "conference",
        "conferences",
        "talk",
        "talks",
        "lecture",
        "lectures",
        "award",
        "awards",
        "prize",
        "win",
        "wins",
        "winner",
        "winners",
        "congratulations",
        "celebrates",
        "announcement",
        "announcements",
        "staff",
        "people",
        "person",
        "profile",
        "profiles",
        "directory",
        "team",
        "gallery",
        "video",
        "videos",
        "podcast",
        "photos",
    }
)
#: R3: a dated archive path (``/2025/10/…``) or a dated slug (``…-2025-10-01``).
_DATED_PATH = re.compile(r"/(?:19|20)\d{2}/\d{1,2}(?:/|$)|(?:19|20)\d{2}-\d{1,2}-\d{1,2}")


def evidence_only_score(url: str, fields: list[str], degree: str) -> int:
    """R3: the subject+level score of a URL kept without a structural word, or 0.

    Positive only when the path names a requested field as whole slug words
    (``matches_field``, and the phrase test of ``_field_slug_bonus``) and
    either the requested level (``matches_degree``) or the field as an
    exact last segment (``exact_field_slug``), names no other level, and is
    none of the paths a programme lead never is. The caller asks this only for
    a URL ``categorise_url`` gave no category; the score is field + level.
    """
    if not fields:
        return 0
    path = (urlparse(url).path or "").lower()
    if (
        _url_excluded(path)
        or _NOT_A_PAGE_ABOUT_STUDYING.search(path)
        or _FUNDING_SEGMENT.search(path)
        or _NOT_A_PROGRAMME_PATH.search(path)
        or _is_fee_path(path)
        or _is_fee_or_entry_subpage(path)
        or _DATED_PATH.search(path)
        or _slug_words(url) & _EVIDENCE_ONLY_REFUSED_WORDS
    ):
        return 0
    if names_other_degree_level(url, degree):
        return 0
    field_bonus = matches_field(url, fields)
    # The slug names the subject: the field or one of its strong or localized
    # aliases as consecutive whole slug words (SR-1's test, whatever its flag),
    # so "ciencias" alone in "licenciatura-en-ciencias-biologicas" is not
    # "ciencias de la computación", nor "science" in "materials-science".
    if field_bonus <= 0 or _field_slug_bonus(path, fields) <= 0:
        return 0
    level_bonus = matches_degree(url, degree)
    if level_bonus <= 0 and not exact_field_slug(url, fields):
        return 0
    return field_bonus + level_bonus


def hold_evidence_only(held: list[tuple[int, str]], score: int, url: str) -> bool:
    """R3: keep ``url`` among at most MAX_EVIDENCE_ONLY_CANDIDATES evidence picks.

    The best are kept, not the first, as for the structural slots: a later URL
    replaces the weakest held one only when it scores higher.
    """
    if len(held) >= MAX_EVIDENCE_ONLY_CANDIDATES:
        weakest = min(held)
        if score <= weakest[0]:
            return False
        held.remove(weakest)
    held.append((score, url))
    return True


def merge_evidence_only(
    structural: list[tuple[int, str]], held: list[tuple[int, str]]
) -> list[tuple[int, str]]:
    """R3: the evidence picks that fit beside the structural ones, best first.

    Only the slots the structural picks leave free of the
    MAX_CANDIDATES_PER_CATEGORY are filled, so a site with hundreds of
    ``bachelor-of-<x>`` slugs never pushes a structural pick out.
    """
    room = max(0, MAX_CANDIDATES_PER_CATEGORY - len(structural))
    return sorted(held, key=lambda pair: (-pair[0], len(pair[1]), pair[1]))[:room]


#: Plan rule CQ-1 (gold knockout 2026-10-19 §3, candidate ticket 1), on by
#: default (see below). Every knockout guess had a head naming the requested level
#: and subject plus a qualifier that makes it another programme ("… with
#: Second Major in Business", "Computer Science (JH)"), and R2's shapes cover
#: only "<related field> and <field>" for a closed list of related fields. On:
#: a page whose head (CH-1's: first ``h1`` or the title's first part) names a
#: combination — joint honours, JH, double/dual degree, second major,
#: combined, a major/minor pair, or "with"/"and" joined to a field that is no
#: alias of the requested subject (``combination_head``, tables from a
#: dictionary for every language of ``languages.json``) — is refused with
#: ``HEAD_COMBINATION_VERDICT``: an identity refusal that frees the slot, and
#: R2's related verdict, so the page is recorded as a related programme. A
#: single-subject page "with Honours", "(Hons)" or "with a year in industry"
#: is not refused. On by default since the rp-bundle2 replay (2026-10-19);
#: the benchmark harness switches it off per capture
#: (``--no-reject-combination-head``).
CONFIRM_REJECTS_COMBINATION_HEAD = True


def profile_rejects(
    page: PageClassification,
    requested_level: str,
    fields: list[str],
    *,
    url: str = "",
    country: str = "",
) -> str | None:
    """Why a fetched page is not this applicant's programme page, or ``None``.

    One predicate, shared by the confirm stage and the catalogue walker: the
    page has to read as a single programme, at the level the applicant asked
    for, in a subject they asked for. The strings are trace copy and are
    pinned by tests — change them only together with the tests.
    """
    if page.page_type not in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM):
        return f"reads as {page.page_type.value}, not a programme page"
    if page.degree_level and page.degree_level != requested_level:
        return f"page names degree level {page.degree_level}, not {requested_level}"
    if (
        INTEGRATED_MASTERS_LEVEL
        and requested_level == "bachelor"
        and _integrated_master_page(page, url)
    ):
        return "page names an integrated master's (master level), not bachelor"
    if not fields:
        return "no privacy-safe requested subject to confirm"
    if not matches_field_text(page.subject or "", fields):
        if SUBJECT_TITLE_SHAPES and subject_head_verdict(page.subject or "", fields) == "related":
            # R2 (16-Q6): refused only on the subject head, unless the page
            # is a foreign campus too, which is no related programme.
            return _campus_abroad(page, url, country) or (
                f"page subject {page.subject!r} {RELATED_PROGRAMME_VERDICT}, not {fields!r}"
            )
        return f"page subject {page.subject!r} does not match requested fields {fields!r}"
    if CONFIRM_REJECTS_COMBINATION_HEAD:
        # CQ-1: a combination is a related programme, unless it is a foreign
        # campus too (as R2's related verdict above).
        from app.adapters.discovery.combination_head import head_combination_rejects

        combination = head_combination_rejects(page, fields, country=country)
        if combination is not None:
            return _campus_abroad(page, url, country) or combination
    if CONFIRM_REQUIRES_HEAD_IDENTITY:
        head = head_identity_rejects(page, requested_level, fields, url=url)
        if head is not None:
            return head
    if CONFIRM_REJECTS_SUBPAGE_HEAD:
        subpage = head_subpage_rejects(page, fields)
        if subpage is not None:
            return subpage
    return _campus_abroad(page, url, country)


def _campus_abroad(page: PageClassification, url: str, country: str) -> str | None:
    """CG-1's verdict on a page, or ``None``."""
    if CAMPUS_GUARD:
        # Title and subject each on its own, so a trailing "– Dubai" anchors
        # to the end of either.
        for name in (page.title, page.subject or ""):
            place = foreign_campus_named(name, url, country)
            if place is not None:
                return f"page names a campus abroad ({place}), not the institution's own"
    return None


@dataclass
class DiscoveredUrl:
    url: str
    category: str
    score: int
    #: "manual_seed" | "sitemap" | "navigation"
    provenance: str
    note: str = ""


class WalkerTrace(TypedDict):
    """What the catalogue-walker stage did, as the trace reports it.

    Keys are frozen (T29 contract; T30 reads this): zeros when the walker was
    not triggered, so a report can distinguish "walked and found nothing" from
    "never walked".
    """

    catalogs_walked: int
    candidates: list[dict[str, object]]
    programs_confirmed: int
    outcomes: list[dict[str, str]]


@dataclass
class _RecoveryState:
    """What identity recovery has read so far, shared across QB-1's two passes.

    One institution's search candidates get MAX_PROGRAM_CANDIDATES_CHECKED
    reads in all, however many provider passes produced them, and a URL the
    first pass already read is never read again. ``max_checks`` lowers that
    cap (QB-1b: a page confirmed before search needs only a twin check).
    """

    visited: set[str] = field(default_factory=set)
    pending: list[str] = field(default_factory=list)
    checked: int = 0
    max_checks: int = MAX_PROGRAM_CANDIDATES_CHECKED
    #: PL-1(a): checks of followed ``search-catalogue`` links, under their own
    #: ``max_checks``; 0 while the rule is off (they count in ``checked``).
    followed: int = 0


def _walker_trace() -> WalkerTrace:
    return {"catalogs_walked": 0, "candidates": [], "programs_confirmed": 0, "outcomes": []}


#: Records one fetched page's metadata — the SourcePage.record field set, as
#: keyword arguments. Discovery never touches the database itself: it calls
#: this when a recorder is wired in, and what the recorder does with a page is
#: the runner's business (T32 reads these rows for freshness).
type PageRecorder = Callable[..., object]


@dataclass
class DiscoveryTrace:
    """Why each institution produced what it did.

    Recorded per run so a discovery that found nothing can say which step
    failed, rather than leaving the user with an empty list.
    """

    institution: str
    domain: str
    sitemaps_declared: list[str] = field(default_factory=list)
    sitemaps_read: list[str] = field(default_factory=list)
    sitemap_urls_seen: int = 0
    sitemap_urls_kept: int = 0
    manual_seeds: dict[str, str] = field(default_factory=dict)
    selected: dict[str, list[str]] = field(default_factory=dict)
    rejected: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    #: Safe search failures only; informational trace entries stay out of run.errors.
    search_failures: list[str] = field(default_factory=list)
    #: Query/slot limits are research limitations, not vendor outages.
    search_limitations: list[str] = field(default_factory=list)
    #: Fetched official programme subjects, keyed by canonical URL.
    field_sources: dict[str, dict[str, str]] = field(default_factory=dict)
    #: A search query's field for an unreadable lead; never source evidence.
    field_hints: dict[str, str] = field(default_factory=dict)
    #: Validated public fields only; internal, never serialised with the trace.
    public_fields: list[str] | None = None
    #: Subjects assigned a provider query in this run, for coverage accounting.
    queried_fields: list[str] = field(default_factory=list)
    #: Provider queries discovery sent for this institution; later stages
    #: spend only what remains of the per-institution query budget.
    search_queries_sent: int = 0
    search_coverage: dict[str, int] = field(default_factory=dict)
    used_navigation_fallback: bool = False
    #: (url, link text) for leads found by a catalogue's own wording rather
    #: than by the URL, so the report can show what the wording was.
    kept_by_link_text: list[tuple[str, str]] = field(default_factory=list)
    #: The catalogue-walker stage's report. Zeros until (and unless) the stage
    #: runs, so "inactive" and "ran and found nothing" stay distinguishable.
    walker: WalkerTrace = field(default_factory=_walker_trace)
    #: SO-1 only: the discovery stages in the order they ran, and the host
    #: cost that chose it. Empty while the rule is off, and then not serialised.
    stage_order: list[str] = field(default_factory=list)
    host_cost: dict = field(default_factory=dict)
    #: PG-1 only: search leads identity recovery could not read, kept as
    #: diagnostics instead of programme pages. Not serialised while empty.
    unresolved: list[str] = field(default_factory=list)
    #: QB-1 only: provider queries each discovery pass sent ([3] when the first
    #: pass confirmed a programme page, [3, 3] when it did not). Empty while the
    #: rule is off, and then not serialised.
    discovery_query_passes: list[int] = field(default_factory=list)
    #: DI-1 only: the admissions domain the homepage justified (and the link),
    #: or why none was added. Not serialised while empty.
    admissions_host: dict[str, object] = field(default_factory=dict)
    #: DI-1: registrable domains accepted beside ``domain`` for this run.
    extra_domains: list[str] = field(default_factory=list)
    #: R4 only: the catalogue host whose own sitemap was read, the link that
    #: named it, the documents read and the URLs kept. Not serialised while empty.
    catalogue_host: dict[str, object] = field(default_factory=dict)
    #: NS-1 only: the homepage links queued as hop reads, with their link
    #: score, best first. Not serialised while empty.
    homepage_hop_reads: list[tuple[str, int]] = field(default_factory=list)
    #: CG-1: the institution's country, for the campus guard. Never serialised.
    country: str = ""
    #: SB-1 only: seconds and reads per discovery stage, ``t_first_query`` and
    #: why the budget stopped discovery. Empty while the rule is off, and then
    #: not serialised.
    stage_budget: dict = field(default_factory=dict)
    #: WF-17, measurement only: per provider query, its family and the URLs
    #: the provider returned, in rank order (at most ten). Public URLs only:
    #: no query text, as in ``QueryAuditRecord``. Not serialised while empty.
    search_results: list[dict[str, object]] = field(default_factory=list)
    #: WF-17: the pages discovery read to judge programme identity, each with
    #: its verdict ("" = accepted, else the refusal). Not serialised while empty.
    pages_read: list[tuple[str, str]] = field(default_factory=list)
    #: WF-17: declared ``hreflang`` twins of every page read, both directions,
    #: keyed by URL. The benchmark scores a twin of the gold page as a hit.
    #: Not serialised while empty.
    programme_url_aliases: dict[str, list[str]] = field(default_factory=dict)
    #: RL-1 only: the institution's read ledger, serialised as it stands when
    #: the trace is (after funding in a full run). None, and not serialised,
    #: while the rule is off.
    read_ledger: _fetching.CaseReadLedger | None = None
    #: R2 (16-Q6): pages confirm refused only on the subject-head rule — a
    #: programme page at the requested level whose title joins the field to a
    #: related field — as ``{"url", "title"}`` rows. The benchmark scores them
    #: ``related``; the product payload does not change. Not serialised while
    #: empty.
    related_programmes: list[dict[str, str]] = field(default_factory=list)
    #: TB-1 only: the institution's case clock, serialised like the ledger.
    case_time: _fetching.CaseTimeBudget | None = None
    #: R5 only (``LOCAL_LANGUAGE_QUERIES``): per search lead identity recovery
    #: read, the query families that returned it (``RankedCandidate.found_by``),
    #: so a page the ``local_language`` family alone found can be told apart.
    #: Empty while the rule is off, and then not serialised.
    lead_found_by: dict[str, list[str]] = field(default_factory=dict)
    #: LQ-2 only (``intent.LOCAL_QUERY_FROM_PAGE_EVIDENCE``): the phrase the
    #: ``local_language`` query took from the site, as ``{"phrase", "source",
    #: "link", "page"}`` (``source`` is ``link`` or ``native_name``). Empty, and
    #: not serialised, while the rule is off or no phrase was found.
    local_query_phrase: dict[str, str] = field(default_factory=dict)
    #: UA-1: reads of the institution's own entry points (robots.txt, sitemap
    #: probes, the homepage and the navigation fallback) that succeeded and
    #: that failed, and whether the homepage was among them. Internal: recorded
    #: whatever the flag says and never serialised.
    entry_reads_ok: int = 0
    entry_reads_failed: int = 0
    entry_homepage_read: bool = False
    #: UA-1 only: identity recovery ran with every entry read failed, so it
    #: confirmed no programme page. Serialised only when true.
    entry_unreadable: bool = False
    #: UA-1 only: search leads recovery read and accepted while the entry hosts
    #: were unreadable — leads without a programme scope, never programme
    #: pages. Not serialised while empty.
    unresolved_access: list[str] = field(default_factory=list)
    #: SP-2 only: the process sub-page handed to the evidence stage as a
    #: requirements lead (at most one). Not serialised while empty.
    requirements_leads: list[RequirementsLead] = field(default_factory=list)

    def note_requirements_lead(
        self,
        url: str,
        verdict: str | None,
        page: PageClassification,
        level: str,
        fields: list[str],
    ) -> None:
        """SP-2: keep the first page SP-1 refused for a process word as a lead."""
        if (
            not SUBPAGE_REQUIREMENTS_LEAD
            or self.requirements_leads
            or not is_process_subpage_refusal(verdict)
        ):
            return
        names = head_names_programme(page, level, fields)
        self.requirements_leads.append(RequirementsLead(url, names))
        self.errors.append(
            f"SP-2: {url} kept as a requirements lead for the evidence stage"
            + ("; its h1 names the programme" if names else "")
        )

    def note_entry_read(self, ok: bool, *, homepage: bool = False) -> None:
        """UA-1: one read of an entry point; ``ok`` counts a cache hit as success."""
        if ok:
            self.entry_reads_ok += 1
        else:
            self.entry_reads_failed += 1
        self.entry_homepage_read = self.entry_homepage_read or homepage

    def entry_hosts_unreadable(self) -> bool:
        """UA-1: the homepage and the navigation fallback were tried; no entry read succeeded."""
        return (
            self.used_navigation_fallback
            and self.entry_homepage_read
            and self.entry_reads_failed > 0
            and self.entry_reads_ok == 0
        )

    def note_found_by(self, url: str, families: Sequence[str]) -> None:
        """R5: which query families returned a lead recovery read (bounded)."""
        bounded = len(self.lead_found_by) < PAGES_READ_TRACE_CAP
        if families and bounded and url not in self.lead_found_by:
            self.lead_found_by[url] = list(families)

    def reject(self, url: str, reason: str) -> None:
        # Bounded: a large sitemap would otherwise produce a huge trace.
        if len(self.rejected) < 200:
            self.rejected.append((url, reason))

    def record_search_results(self, by_family: Sequence[tuple[str, Sequence[str]]]) -> None:
        """Keep what the provider returned per query family (WF-17)."""
        for family, urls in by_family:
            if len(self.search_results) >= SEARCH_RESULTS_TRACE_CAP:
                break
            self.search_results.append(
                {"family": family, "urls": list(urls)[:SEARCH_RESULTS_PER_QUERY]}
            )

    def note_read(
        self, url: str, final_url: str, html: str, verdict: str | None, title: str = ""
    ) -> None:
        """A page read to judge identity: its verdict and its declared twins (WF-17).

        Keyed by ``url``, the lead as discovery reports it; the twins resolve
        against ``final_url``, where the page actually was. A related
        programme verdict (R2) records the page and its ``title`` as well.
        """
        if len(self.pages_read) < PAGES_READ_TRACE_CAP:
            self.pages_read.append((url, verdict or ""))
        self.note_alternates(url, declared_alternates(final_url or url, html, self.domain))
        if is_related_refusal(verdict):
            self.note_related(url, title)

    def note_related(self, url: str, title: str) -> None:
        """R2 (16-Q6): a related programme read and refused, once per URL."""
        if len(self.related_programmes) >= PAGES_READ_TRACE_CAP:
            return
        if any(row["url"] == url for row in self.related_programmes):
            return
        self.related_programmes.append({"url": url, "title": title})

    def note_alternates(self, url: str, alternates: Sequence[str]) -> None:
        """Record ``url`` and each declared twin as aliases of one another."""
        for twin in alternates:
            for one, other in ((url, twin), (twin, url)):
                known = self.programme_url_aliases.setdefault(one, [])
                if other not in known and other != one:
                    known.append(other)

    def as_dict(self) -> dict:
        return {
            "institution": self.institution,
            "domain": self.domain,
            "sitemaps_declared": self.sitemaps_declared,
            "sitemaps_read": self.sitemaps_read,
            "sitemap_urls_seen": self.sitemap_urls_seen,
            "sitemap_urls_kept": self.sitemap_urls_kept,
            "manual_seeds": self.manual_seeds,
            "selected": self.selected,
            "rejected_sample": self.rejected[:40],
            "rejected_total": len(self.rejected),
            "errors": self.errors,
            "search_failures": self.search_failures,
            "search_limitations": self.search_limitations,
            "field_sources": self.field_sources,
            "search_coverage": self.search_coverage,
            "used_navigation_fallback": self.used_navigation_fallback,
            "kept_by_link_text": self.kept_by_link_text,
            "walker": dict(self.walker),
            **({"stage_order": self.stage_order} if self.stage_order else {}),
            **({"host_cost": self.host_cost} if self.host_cost else {}),
            **({"unresolved": self.unresolved} if self.unresolved else {}),
            **(
                {"discovery_query_passes": self.discovery_query_passes}
                if self.discovery_query_passes
                else {}
            ),
            **({"admissions_host": self.admissions_host} if self.admissions_host else {}),
            **({"catalogue_host": self.catalogue_host} if self.catalogue_host else {}),
            **({"homepage_hop_reads": self.homepage_hop_reads} if self.homepage_hop_reads else {}),
            **({"stage_budget": self.stage_budget} if self.stage_budget else {}),
            **({"search_results": self.search_results} if self.search_results else {}),
            **({"pages_read": self.pages_read} if self.pages_read else {}),
            **(
                {"programme_url_aliases": self.programme_url_aliases}
                if self.programme_url_aliases
                else {}
            ),
            **({"read_ledger": self.read_ledger.as_dict()} if self.read_ledger is not None else {}),
            **({"related_programmes": self.related_programmes} if self.related_programmes else {}),
            **({"case_time": self.case_time.as_dict()} if self.case_time is not None else {}),
            **({"lead_found_by": self.lead_found_by} if self.lead_found_by else {}),
            **({"local_query_phrase": self.local_query_phrase} if self.local_query_phrase else {}),
            **({"entry_unreadable": True} if self.entry_unreadable else {}),
            **({"unresolved_access": self.unresolved_access} if self.unresolved_access else {}),
            **(
                {
                    "requirements_leads": [
                        {"url": lead.url, "names_programme": lead.names_programme}
                        for lead in self.requirements_leads
                    ]
                }
                if self.requirements_leads
                else {}
            ),
        }


def _remember_field_source(
    trace: DiscoveryTrace,
    *,
    url: str,
    subject: str,
    fields: list[str],
    basis: str,
    source_url: str = "",
) -> None:
    """Retain which official page named the applicant's field."""
    matched = _field_named_by_subject(subject, fields)
    if matched:
        trace.field_sources[canonical_url(url)] = {
            "field": matched,
            "source_url": source_url or url,
            "subject": subject,
            "basis": basis,
        }


# --- sitemaps -------------------------------------------------------------

_SITEMAP_DIRECTIVE = re.compile(r"^\s*sitemap:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
#: Entries whose direct ``loc`` child names a URL. Matched by local name:
#: sites serve the http and the https sitemaps.org namespace, or none (UNSW
#: uses ``https://www.sitemaps.org/...``). Only direct children are taken, so
#: an extension's own ``loc`` (``image:image/image:loc``) is not read as a page.
_SITEMAP_ENTRY_TAGS = ("url", "sitemap")


def _local_name(tag: object) -> str:
    """An element's tag without its ``{namespace}``; '' for comments and PIs."""
    return tag.rpartition("}")[2].lower() if isinstance(tag, str) else ""


def parse_sitemap_directives(robots_text: str) -> list[str]:
    """Sitemap: lines from robots.txt. A site telling us where to look."""
    return [m.group(1).strip() for m in _SITEMAP_DIRECTIVE.finditer(robots_text or "")]


def decode_sitemap(body: bytes, url: str) -> str:
    """Sitemap text, transparently un-gzipping when needed.

    Gzipped sitemaps are common and are not always served with a content
    encoding that the HTTP layer will undo, so the magic number is checked.
    """
    if body[:2] == b"\x1f\x8b" or url.lower().endswith(".gz"):
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError) as exc:
            log.info("could not gunzip %s: %s", url, exc)
            return ""
    return body.decode("utf-8", errors="replace")


async def robots_crawl_delay(fetcher: Fetcher, url: str) -> float | None:
    """The crawl delay the fetcher's own robots policy holds for ``url``'s host.

    No read: the policy answers from the robots.txt it already parsed.
    """
    robots = getattr(fetcher, "robots", None)
    if robots is None:
        return None
    try:
        delay: float | None = await robots.crawl_delay(url)
    except Exception:  # a robots policy that cannot answer says nothing
        return None
    return delay


class HostCost:
    """SO-1: what one host's reads cost so far, to decide the stage order.

    Only the first SLOW_HOST_SAMPLE_READS reads are timed. A crawl delay is
    read from the fetcher's own robots policy, which is also what spaces the
    reads, so the two signals cannot disagree about why a host is slow.
    """

    def __init__(self, *, first_read_rule: bool = False) -> None:
        self.read_seconds: list[float] = []
        self.crawl_delay: float | None = None
        #: SB-1: one slow read among the first two (robots.txt, the first
        #: sitemap document) is enough; SO-1 waits for a median.
        self.first_read_rule = first_read_rule

    async def get(self, fetcher: Fetcher, url: str) -> FetchResult:
        started = _clock()
        result = await fetcher.get(url)
        if len(self.read_seconds) < SLOW_HOST_SAMPLE_READS:
            self.read_seconds.append(_clock() - started)
        return result

    async def learn_crawl_delay(self, fetcher: Fetcher, url: str) -> None:
        if getattr(fetcher, "robots", None) is None:
            return
        self.crawl_delay = await robots_crawl_delay(fetcher, url)

    @property
    def median_read_seconds(self) -> float | None:
        # Two reads are enough to judge: with SM-1 a host whose robots.txt
        # names no sitemap and whose /sitemap.xml answers makes only two.
        if len(self.read_seconds) < 2:
            return None
        return float(statistics.median(self.read_seconds))

    @property
    def slow(self) -> bool:
        if self.crawl_delay is not None and self.crawl_delay >= SLOW_HOST_SECONDS:
            return True
        if self.first_read_rule and any(
            seconds > SLOW_HOST_SECONDS for seconds in self.read_seconds[:2]
        ):
            return True
        median = self.median_read_seconds
        return median is not None and median >= SLOW_HOST_SECONDS

    def document_cap(self) -> int:
        return SLOW_HOST_SITEMAP_DOCUMENTS if self.slow else MAX_SITEMAP_DOCUMENTS

    def as_dict(self) -> dict:
        median = self.median_read_seconds
        return {
            "crawl_delay": self.crawl_delay,
            "median_read_seconds": None if median is None else round(median, 2),
            "slow": self.slow,
        }


class StageBudget:
    """SB-1: one institution's discovery clock and read count, per stage.

    Seconds are wall clock between stage transitions, so parsing and
    classification are charged to the stage that did them; reads are fetches
    the cache did not answer. ``exhausted`` latches: once the deadline or the
    read cap is reached, every later check says so. The read cap counts
    candidate reads only; sitemap reads have their own allowance (SB-1b).
    """

    def __init__(
        self,
        *,
        deadline_seconds: float | None = None,
        read_cap: int | None = None,
    ) -> None:
        # Read at construction, so a test (or the harness) can set the module values.
        self.deadline_seconds = (
            DISCOVERY_DEADLINE_SECONDS if deadline_seconds is None else deadline_seconds
        )
        self.read_cap = DISCOVERY_READ_CAP if read_cap is None else read_cap
        self.started = _clock()
        self.stage = BUDGET_STAGES[0]
        self._since = self.started
        self.seconds = dict.fromkeys(BUDGET_STAGES, 0.0)
        self.reads = dict.fromkeys(BUDGET_STAGES, 0)
        self.t_first_query: float | None = None
        self.stopped_by = ""
        self.stopped_at: float | None = None
        self.stopped_in = ""
        #: Reads refused because the budget was spent (a safety net: stages
        #: check before they read, so this stays 0 unless one did not).
        self.refused_reads = 0
        self.sitemap_allowance = DISCOVERY_SITEMAP_ALLOWANCE
        #: SB-1b: recovery reads made past a spent budget, of RECOVERY_RESERVE_READS.
        self.reserve = RECOVERY_RESERVE_READS
        self.reserve_used = 0
        #: Recovery reads started before the deadline.
        self.recovery_reads_in_time = 0
        #: PL-1(b): recovery reads started, in time or not.
        self.recovery_reads = 0
        self._grants = 0

    def elapsed(self) -> float:
        return _clock() - self.started

    @property
    def total_reads(self) -> int:
        return sum(self.reads.values())

    @property
    def candidate_reads(self) -> int:
        """Reads the read cap counts: every stage's but the sitemap stage's."""
        return self.total_reads - self.reads["sitemap"]

    def past_deadline(self) -> bool:
        return self.elapsed() >= self.deadline_seconds

    def sitemap_spent(self) -> bool:
        return self.reads["sitemap"] >= self.sitemap_allowance

    def enter(self, stage: str) -> str:
        """Charge the time so far to the current stage; return that stage."""
        now = _clock()
        self.seconds[self.stage] += now - self._since
        self._since = now
        previous, self.stage = self.stage, stage
        return previous

    def exhausted(self) -> bool:
        if not self.stopped_by:
            elapsed = self.elapsed()
            if elapsed >= self.deadline_seconds:
                self.stopped_by = "deadline"
            elif self.candidate_reads >= self.read_cap:
                self.stopped_by = "read_cap"
            if self.stopped_by:
                self.stopped_at = round(elapsed, 2)
                self.stopped_in = self.stage
        return bool(self.stopped_by)

    def count_read(self, result: FetchResult) -> None:
        if not getattr(result, "from_cache", False):
            self.reads[self.stage] += 1

    def query_sent(self) -> None:
        if self.t_first_query is None:
            self.t_first_query = round(self.elapsed(), 2)

    def reserve_open(self) -> bool:
        """SB-1b: whether the first pass's recovery may read past a spent budget.

        Past the read cap, up to ``reserve`` reads; past the deadline only when
        the deadline fell before any recovery read.
        """
        if self.reserve_used >= self.reserve:
            return False
        if PROVIDER_LEAD_FLOOR and self.past_deadline():
            # PL-1(b): the first pass gets ``reserve`` recovery reads in all.
            return self.recovery_reads < self.reserve
        return not (self.past_deadline() and self.recovery_reads_in_time)

    def note_recovery_read(self) -> None:
        """A recovery read is about to start; past a spent budget it uses the reserve."""
        self.recovery_reads += 1
        if self.exhausted():
            self.reserve_used += 1
            self._grants += 1
        if not self.past_deadline():
            self.recovery_reads_in_time += 1

    def take_grant(self) -> bool:
        if self._grants:
            self._grants -= 1
            return True
        return False

    def as_dict(self) -> dict:
        self.enter(self.stage)
        return {
            "deadline_seconds": self.deadline_seconds,
            "read_cap": self.read_cap,
            "seconds": round(self.elapsed(), 2),
            "reads": self.total_reads,
            "candidate_reads": self.candidate_reads,
            "sitemap_allowance": self.sitemap_allowance,
            "reserve_reads": self.reserve_used,
            "stage_seconds": {k: round(v, 2) for k, v in self.seconds.items()},
            "stage_reads": dict(self.reads),
            "t_first_query": self.t_first_query,
            "stopped_by": self.stopped_by or None,
            "stopped_at": self.stopped_at,
            "stopped_in": self.stopped_in or None,
            "refused_reads": self.refused_reads,
        }


class _BudgetedFetcher:
    """SB-1: the adapter's Fetcher, counting reads against a StageBudget.

    Every attribute but ``get`` is the wrapped fetcher's own (robots, refused
    hosts, the renderer seam), so robots, rate limits and the PII guard apply
    exactly as before. A read asked for after the budget is spent is not made.
    """

    def __init__(self, inner: Fetcher, budget: StageBudget) -> None:
        self._inner = inner
        self._budget = budget

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        budget = self._budget
        spent = budget.exhausted() and not budget.take_grant()
        if spent or (budget.stage == "sitemap" and budget.sitemap_spent()):
            budget.refused_reads += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.BLOCKED,
                error="discovery stage budget spent",
                final_url=url,
            )
        result = await self._inner.get(url, **kwargs)
        self._budget.count_read(result)
        return result


def _child_priority(url: str) -> int:
    """SM-1: 0 for a programme/page sitemap, 2 for a news/post one, else 1.

    Judged on the child's path and query only (TYPO3 names its children
    ``sitemap.xml?sitemap=news``); a programme word wins over a news word.
    """
    parts = urlparse(url)
    name = f"{parts.path} {parts.query}".lower()
    if _SITEMAP_CHILD_FIRST.search(name):
        return 0
    if _SITEMAP_CHILD_LAST.search(name):
        return 2
    return 1


def parse_sitemap(text: str) -> tuple[list[str], list[str]]:
    """Return (child sitemap URLs, page URLs) from one sitemap document."""
    if not text.strip():
        return [], []
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        # Some sites serve a plain-text list of URLs. Accept that too.
        lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("http")]
        return [], lines[:MAX_SITEMAP_URLS]

    locations = [
        (child.text or "").strip()
        for entry in root.iter()
        if _local_name(entry.tag) in _SITEMAP_ENTRY_TAGS
        for child in entry
        if _local_name(child.tag) == "loc" and (child.text or "").strip()
    ]
    if _local_name(root.tag) == "sitemapindex":
        return locations, []
    return [], locations


def _resolve_loc(base: str, loc: str) -> str:
    """A sitemap ``loc`` made absolute against its document; as-is if malformed."""
    try:
        return urljoin(base, loc)
    except ValueError:
        return loc


class SitemapReader:
    """Reads an institution's sitemaps, within bounds."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def collect(
        self,
        homepage: str,
        domain: str,
        trace: DiscoveryTrace,
        keep: Callable[[str], bool] | None = None,
        cost: HostCost | None = None,
        before_document: Callable[[int], Awaitable[bool]] | None = None,
        *,
        stall_local: bool = False,
    ) -> list[str]:
        """Page URLs the institution's sitemaps declare, deduplicated.

        ``keep`` decides relevance as each URL is read. Without it every URL is
        kept, which is what the unit tests want but not what a real university
        sitemap can afford: filtering afterwards means the bound falls wherever
        the site happens to have listed its news.

        ``before_document`` (SB-1) is awaited before each document after the
        first with the number attempted so far; True ends the sitemap stage.

        ``stall_local`` (PC-1): each document is read as stall-local, so a
        document that stalls is skipped alone, and it ends the stage.
        """
        origin = self._origin(homepage)
        declared = await self._declared_sitemaps(origin, trace, cost)
        if cost is not None:
            await cost.learn_crawl_delay(self.fetcher, homepage)
        queue: list[tuple[str, int]] = [(u, 0) for u in declared]
        #: SM-1: the conventional locations still to probe, dropped once one answers.
        fallbacks: set[str] = set()
        #: SG-1: consecutive guesses answered 404 (counted only while on).
        guess_404s = 0
        if not queue:
            paths = SITEMAP_FALLBACK_PATHS[:SITEMAP_GUESS_CAP]
            if SITEMAP_GUESS_RULE:
                delay = (
                    cost.crawl_delay
                    if cost is not None
                    else await robots_crawl_delay(self.fetcher, homepage)
                )
                if delay is not None and delay >= SLOW_HOST_SECONDS:
                    paths = paths[:SITEMAP_GUESS_SLOW_HOST_CAP]
                    trace.errors.append(
                        f"SG-1: crawl delay {delay:g} s and no declared sitemap; "
                        f"{len(paths)} location guessed"
                    )
            queue = [(urljoin(origin, path), 0) for path in paths]
            fallbacks = {canonical_url(u) for u, _ in queue}

        seen_documents: set[str] = set()
        pages: list[str] = []
        seen_pages: set[str] = set()

        attempted_documents = 0
        while queue and attempted_documents < (
            MAX_SITEMAP_DOCUMENTS if cost is None else cost.document_cap()
        ):
            url, depth = queue.pop(0)
            url = canonical_url(url)
            if url in seen_documents or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_documents.add(url)

            if not same_institution(url, domain):
                trace.reject(url, "sitemap is off the institution's domain")
                continue
            if SITEMAP_TRIM and _trimmed_sitemap(url):
                trace.reject(url, "SM-2: news/events/media sitemap not read")
                continue

            if (
                before_document is not None
                and attempted_documents
                and await before_document(attempted_documents)
            ):
                break
            attempted_documents += 1
            if url in fallbacks:
                # HS-1: a conventional location is a guess, not a published link.
                mark_guessed = getattr(self.fetcher, "mark_guessed", None)
                if mark_guessed is not None:
                    mark_guessed(url)
            if stall_local:
                mark_stall_local = getattr(self.fetcher, "mark_stall_local", None)
                if mark_stall_local is not None:
                    mark_stall_local(url)
            with reading_as("sitemap"):
                result = await (
                    self.fetcher.get(url) if cost is None else cost.get(self.fetcher, url)
                )
            trace.note_entry_read(result.ok)
            if SITEMAP_GUESS_RULE and url in fallbacks:
                guess_404s = guess_404s + 1 if result.status_code == 404 else 0
                if guess_404s >= SITEMAP_GUESS_MAX_404:
                    # SG-1: the host does not keep its sitemap where it is guessed.
                    skipped = [item for item in queue if canonical_url(item[0]) in fallbacks]
                    if skipped:
                        queue = [item for item in queue if item not in skipped]
                        trace.errors.append(
                            f"SG-1: {guess_404s} guessed sitemap locations answered 404; "
                            f"{len(skipped)} more not guessed"
                        )
                    fallbacks = set()
            if not result.ok:
                trace.errors.append(f"{url}: {result.outcome.value} — {result.error}"[:300])
                if stall_local and result.outcome == FetchOutcome.TIMEOUT:
                    # PC-1: the stall is this stage's verdict, not the host's.
                    trace.errors.append(SITEMAP_STALL_LINE)
                    break
                if result.outcome == FetchOutcome.TOO_LARGE:
                    # A site-wide export exceeded the bounded page reader.
                    # More bulk siblings can exhaust the host's time budget
                    # before normal programme pages are tried (live Groningen).
                    trace.errors.append(
                        "Sitemap size budget reached; continuing with targeted discovery."
                    )
                    break
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "sitemap redirected off the institution's site")
                continue
            trace.sitemaps_read.append(url)

            children, locations = parse_sitemap(decode_sitemap(result.content, url))
            # A ``loc`` may be relative (UiO's index lists ``/sitemap-….xml``);
            # it is resolved against the document it came from, and every
            # domain check below still runs on the joined URL.
            base = result.final_url or url
            children = [_resolve_loc(base, child) for child in children]
            locations = [_resolve_loc(base, location) for location in locations]
            if (
                (SITEMAP_CHILD_PRIORITY or SITEMAP_TRIM)
                and url in fallbacks
                and (children or locations)
            ):
                # One conventional location answered with a sitemap; the
                # others are guesses that cost a read each (SM-1, SM-2).
                queue = [item for item in queue if canonical_url(item[0]) not in fallbacks]
                fallbacks = set()
            if SITEMAP_CHILD_PRIORITY:
                children = self._prioritised(
                    children,
                    attempted_documents + len(queue),
                    trace,
                    MAX_SITEMAP_DOCUMENTS if cost is None else cost.document_cap(),
                )
            for child in children:
                queue.append((child, depth + 1))
            for location in locations:
                trace.sitemap_urls_seen += 1
                canonical = canonical_url(location)
                if canonical in seen_pages:
                    continue
                if not same_institution(canonical, domain):
                    trace.reject(canonical, "off the institution's domain")
                    continue
                seen_pages.add(canonical)
                if keep is not None and not keep(canonical):
                    continue
                pages.append(canonical)
                if trace.sitemap_urls_seen >= MAX_SITEMAP_URLS:
                    trace.errors.append(
                        f"stopped after reading {MAX_SITEMAP_URLS:,} sitemap URLs; "
                        "the sitemap is larger than we read"
                    )
                    trace.sitemap_urls_kept = len(pages)
                    return pages

        trace.sitemap_urls_kept = len(pages)
        return pages

    async def collect_catalogue_host(
        self,
        url: str,
        domain: str,
        trace: DiscoveryTrace,
        keep: Callable[[str], bool],
        *,
        degree: str = "",
        stop: Callable[[], bool] | None = None,
    ) -> list[str]:
        """R4: the page URLs a catalogue host's own sitemap declares, kept by ``keep``.

        The host is the one ``url`` sits on. Its robots.txt is read for a
        ``Sitemap:`` line; failing one, the conventional locations are tried
        until one parses. At most CATALOGUE_HOST_SITEMAP_DOCUMENTS documents
        are read: children whose name names a study offer first, then
        ``page`` sitemaps, the rest last; news and media children (SM-2's
        words) are never read, nor, for a bachelor's request, a child naming
        another level. ``stop`` is asked before each document. Every read goes
        through the Fetcher, under that host's own robots.txt.
        """
        origin = self._origin(url)
        record = trace.catalogue_host
        read: list[str] = []
        record["sitemaps_read"] = read
        robots_url = urljoin(origin, "/robots.txt")
        with reading_as("sitemap"):
            robots = await self.fetcher.get(robots_url)
        declared: list[str] = []
        if robots.ok and same_source_site(robots_url, robots.final_url or robots_url):
            declared = parse_sitemap_directives(robots.text)
        queue: list[tuple[str, int]] = [(u, 0) for u in declared]
        fallbacks: set[str] = set()
        if not queue:
            queue = [(urljoin(origin, path), 0) for path in CATALOGUE_HOST_SITEMAP_PATHS]
            fallbacks = {canonical_url(u) for u, _ in queue}

        def priority(item: tuple[str, int]) -> int:
            parts = urlparse(item[0])
            name = f"{parts.path} {parts.query}".lower()
            if _CATALOGUE_HOST_CHILD_FIRST.search(name):
                return 0
            return 1 if re.search(r"(?<![a-z])pages?(?![a-z])", name) else 2

        seen_documents: set[str] = set()
        seen_pages: set[str] = set()
        pages: list[str] = []
        urls_seen = 0
        documents = 0
        while queue and documents < CATALOGUE_HOST_SITEMAP_DOCUMENTS:
            document, depth = queue.pop(0)
            document = canonical_url(document)
            if document in seen_documents or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_documents.add(document)
            if not same_institution(document, domain):
                trace.reject(document, "R4: catalogue-host sitemap is off the institution's domain")
                continue
            if _trimmed_sitemap(document):
                trace.reject(document, "R4: news/events/media sitemap not read")
                continue
            if degree == "bachelor" and _GRADUATE_SITEMAP_NAME.search(
                urlparse(document).path.lower()
            ):
                trace.reject(document, "R4: catalogue-host sitemap of another level not read")
                continue
            if stop is not None and stop():
                break
            documents += 1
            if document in fallbacks:
                mark_guessed = getattr(self.fetcher, "mark_guessed", None)
                if mark_guessed is not None:
                    mark_guessed(document)
            with reading_as("sitemap"):
                result = await self.fetcher.get(document)
            if not result.ok:
                trace.errors.append(
                    f"R4 catalogue host {document}: {result.outcome.value} — {result.error}"[:300]
                )
                continue
            if not same_source_site(document, result.final_url or document):
                trace.reject(document, "sitemap redirected off the institution's site")
                continue
            read.append(document)
            children, locations = parse_sitemap(decode_sitemap(result.content, document))
            base = result.final_url or document
            if document in fallbacks and (children or locations):
                queue = [item for item in queue if canonical_url(item[0]) not in fallbacks]
                fallbacks = set()
            queue.extend((_resolve_loc(base, child), depth + 1) for child in children)
            queue.sort(key=priority)  # stable: file order within a group
            kept_before = len(pages)
            for location in locations:
                urls_seen += 1
                canonical = canonical_url(_resolve_loc(base, location))
                if canonical in seen_pages or not same_institution(canonical, domain):
                    continue
                seen_pages.add(canonical)
                if keep(canonical):
                    pages.append(canonical)
            if depth and len(pages) > kept_before:
                # The host's programme list is read; its other children are
                # further reads for leads of the same kind or of none.
                break
        record["urls_seen"] = urls_seen
        record["kept"] = len(pages)
        return pages

    @staticmethod
    def _prioritised(
        children: list[str], committed: int, trace: DiscoveryTrace, cap: int
    ) -> list[str]:
        """SM-1: an index's children, programme sitemaps first, news last.

        ``committed`` counts documents already read or queued. When the
        first group alone reaches the cap, the last group is not queued at all.
        """
        ordered = sorted(children, key=_child_priority)  # stable: file order within a group
        first = sum(1 for child in children if _child_priority(child) == 0)
        if first and committed + first >= cap:
            skipped = [child for child in ordered if _child_priority(child) == 2]
            for child in skipped:
                trace.reject(child, "news/post sitemap skipped: programme sitemaps fill the cap")
            ordered = [child for child in ordered if _child_priority(child) != 2]
        return ordered

    async def _declared_sitemaps(
        self, origin: str, trace: DiscoveryTrace, cost: HostCost | None = None
    ) -> list[str]:
        robots_url = urljoin(origin, "/robots.txt")
        with reading_as("sitemap"):
            result = await (
                self.fetcher.get(robots_url) if cost is None else cost.get(self.fetcher, robots_url)
            )
        trace.note_entry_read(result.ok)
        if not result.ok:
            trace.errors.append(f"robots.txt unavailable: {result.outcome.value}")
            return []
        if not same_source_site(robots_url, result.final_url or robots_url):
            trace.errors.append("robots.txt redirected off the institution's site")
            return []
        declared = parse_sitemap_directives(result.text)
        trace.sitemaps_declared = declared
        return declared

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlparse(url)
        return f"{parts.scheme}://{parts.netloc}"


# --- the adapter ----------------------------------------------------------


class LiveDiscoveryAdapter:
    """Finds official pages for an institution, sitemap-first."""

    name = "live-sitemap-discovery"

    def __init__(
        self,
        fetcher: Fetcher,
        registry_path: Path | None = None,
        *,
        page_recorder: PageRecorder | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.registry_path = registry_path or REGISTRY_PATH
        self.sitemaps = SitemapReader(fetcher)
        #: Populated per run, so a caller can report why discovery found what it did.
        self.traces: list[DiscoveryTrace] = []
        #: Wired by the runner when fetched pages should feed source_pages
        #: (dormant while None — discovery runs byte-identically without it).
        self.page_recorder = page_recorder
        #: One outcome per walker-touched page, for the run's persisted report.
        self.walker_outcomes: list[PageOutcome] = []
        #: The search provider, resolved once per run. See
        #: :meth:`_search_provider_or_none` for why this is per run and not per
        #: institution.
        self._search_provider: SearchProvider | None = None
        self._search_provider_resolved = False
        #: SB-1: the current institution's budget, and the programme pages a
        #: stage read and accepted. None/empty while the rule is off.
        self._budget: StageBudget | None = None
        self._confirmed: set[str] = set()
        self._has_candidates = False
        #: SB-1b: whether this institution can search, and whether it has.
        self._search_wanted = False
        self._search_attempted = False
        #: Provider queries this institution already spent before discovery
        #: (the catalogue's site-identity fallback). They count in the same
        #: DEFAULT_QUERY_BUDGET, so discovery's own search gets that many fewer.
        self._queries_before_discovery = 0

    def registry(self) -> list[dict]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text())

    def _search_provider_or_none(self) -> SearchProvider | None:
        """The configured provider, or ``None`` when there is none.

        Resolved **once per discovery run**, not once per institution.

        ``get_search_provider`` builds a fresh adapter object on every call, and
        the keyless Exa MCP provider performs its JSON-RPC handshake on first
        use and remembers the session id on the instance. Calling it inside the
        per-institution loop therefore re-handshaked for each of the nineteen
        institutions — nineteen handshakes instead of one — and, because that
        handshake shares the fifteen-second search budget with the first query,
        the first and best-ranked query family was the one that timed out.

        One instance per run keeps the handshake where it belongs: once, before
        the first institution asks anything. A run is also the right scope
        rather than the process, because the provider is built from settings and
        a test that changes settings must still see the change.
        """
        if not self._search_provider_resolved:
            from app.adapters.search import SearchError, get_search_provider

            try:
                self._search_provider = get_search_provider()
            except SearchError:
                self._search_provider = None
            self._search_provider_resolved = True
        return self._search_provider

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        prefs = profile.preferences
        excluded = {c.lower() for c in prefs.excluded_countries}
        preferred = {c.lower() for c in prefs.preferred_countries}

        entries = [e for e in self.registry() if e["country"].lower() not in excluded]
        if preferred:
            entries.sort(key=lambda e: 0 if e["country"].lower() in preferred else 1)
        entries = entries[:limit]

        self.traces = []
        self.walker_outcomes = []
        out: list[Candidate] = []
        for entry in entries:
            candidate, trace = await self._discover_one(entry, profile)
            self.traces.append(trace)
            out.append(candidate)
        return out

    async def _discover_one(
        self, entry: dict, profile: ApplicantProfileIn
    ) -> tuple[Candidate, DiscoveryTrace]:
        # RL-1: this institution's discovery reads are charged to its ledger,
        # which the trace carries (and serialises as it stands at the end).
        institution = urlparse(entry["homepage"]).netloc
        with _fetching.charging(self.fetcher, institution, "discovery") as ledger:
            candidate, trace = await self._discover_one_within_budget(entry, profile)
        if ledger is not None:
            trace.read_ledger = ledger
        timer = _fetching.case_timer(self.fetcher, institution)
        if timer is not None:
            trace.case_time = timer
        return candidate, trace

    async def _discover_one_within_budget(
        self, entry: dict, profile: ApplicantProfileIn
    ) -> tuple[Candidate, DiscoveryTrace]:
        if not STAGE_BUDGETS:
            return await self._discover_institution(entry, profile)
        # SB-1: every discovery read of this institution goes through one
        # budget; the wrapped fetcher is restored for the stages after.
        budget = StageBudget()
        inner = self.fetcher
        budgeted = cast(Fetcher, _BudgetedFetcher(inner, budget))
        self._budget, self._confirmed, self._has_candidates = budget, set(), False
        self._search_attempted = False
        self._search_wanted = (
            bool(profile.context.intended_fields) and self._search_provider_or_none() is not None
        )
        self.fetcher = self.sitemaps.fetcher = budgeted
        try:
            candidate, trace = await self._discover_institution(entry, profile)
        finally:
            self.fetcher = self.sitemaps.fetcher = inner
            self._budget = None
        trace.stage_budget = budget.as_dict()
        if budget.stopped_by:
            trace.errors.append(
                f"SB-1: discovery stopped at {budget.stopped_at} s in {budget.stopped_in} "
                f"({budget.stopped_by}); the verify stage gets what was confirmed"
            )
        return candidate, trace

    def _query_allowance(self, trace: DiscoveryTrace) -> int:
        """Provider queries discovery may still send for this institution.

        One DEFAULT_QUERY_BUDGET covers every query the institution costs,
        including the site-identity fallback that ran before discovery.
        """
        from app.adapters.search.intent import DEFAULT_QUERY_BUDGET

        return max(0, DEFAULT_QUERY_BUDGET - trace.search_queries_sent)

    def _spent(self) -> bool:
        """SB-1: whether this institution's discovery budget is spent."""
        return self._budget is not None and self._budget.exhausted()

    def _search_cut(self) -> bool:
        """SB-1b: search is skipped only for the deadline; a query is not a read."""
        return self._budget is not None and self._budget.past_deadline()

    def _search_due(self) -> bool:
        """SB-1b: nothing confirmed by SEARCH_LATEST_START_SECONDS and no search yet."""
        return (
            self._budget is not None
            and self._search_wanted
            and not self._search_attempted
            and not self._confirmed
            and self._budget.elapsed() >= SEARCH_LATEST_START_SECONDS
        )

    def _walker_stop(self) -> bool:
        """SB-1: the walker stops when spent, and (SB-1b) when the first query is due."""
        return self._spent() or self._search_due()

    def _enter(self, stage: str) -> str:
        """SB-1: charge what follows to ``stage``; '' while the rule is off."""
        return self._budget.enter(stage) if self._budget is not None else ""

    def _skip_hop_roots(self) -> bool:
        """SB-1: hop roots are opened only when no stage offered a programme lead."""
        return self._budget is not None and self._has_candidates

    def _programme_confirmed(self, selected: dict[str, list[str]]) -> bool:
        """SB-1: whether a programme page in the slots was read and accepted."""
        return any(url in self._confirmed for url in selected[PageCategory.PROGRAM_PAGE])

    async def _discover_institution(
        self, entry: dict, profile: ApplicantProfileIn
    ) -> tuple[Candidate, DiscoveryTrace]:
        domain = urlparse(entry["homepage"]).netloc
        trace = DiscoveryTrace(
            institution=entry["name"], domain=domain, country=str(entry.get("country") or "")
        )
        trace.search_queries_sent = self._queries_before_discovery

        candidate = Candidate(
            name=entry["name"],
            country=entry["country"],
            city=entry.get("city", ""),
            domain=domain,
            attributes=entry.get("attributes", {}),
            rankings=[RankingEntry(**r) for r in entry.get("rankings", [])],
            discovery_source=f"{self.name} -> {entry['homepage']}",
        )

        # 1. Manual seeds. A human has verified which page is which. This says
        #    where to look; it is not itself evidence of anything on the page.
        seeds = {k: v for k, v in (entry.get("seeds") or {}).items() if v}
        trace.manual_seeds = dict(seeds)
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        for category, url in seeds.items():
            if category not in selected:
                trace.reject(url, f"unknown seed category {category!r}")
                continue
            if not same_institution(url, domain):
                trace.reject(url, "manual seed is off the institution's domain")
                continue
            selected[category].append(canonical_url(url))

        # 2. Sitemaps. Relevance is decided as each URL is read, not after the
        #    whole sitemap is collected: a university publishes far more news
        #    than programmes, and a bound applied to raw URLs stops in the news.
        ranked: dict[str, list[tuple[int, str]]] = {c: [] for c in PageCategory.ALL}
        fields = _public_requested_fields(profile, trace)
        degree = str(profile.context.level)
        # R3: evidence-only programme leads, held apart from the structural
        # slots and merged into the free ones after the sitemap stage.
        evidence_only: list[tuple[int, str]] = []

        def keep(url: str) -> bool:
            category, score = categorise_url(url)
            if category is None:
                if SITEMAP_KEEP_EVIDENCE_SUM:
                    evidence = evidence_only_score(url, fields, degree)
                    return evidence > 0 and hold_evidence_only(evidence_only, evidence, url)
                return False
            if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
                if names_other_degree_level(url, degree):
                    trace.reject(url, f"names a degree level other than {degree}")
                    return False
                score += matches_field(url, fields) + matches_degree(url, degree)
            elif SERVICE_PAGE_PRIORITY and category in SERVICE_CATEGORIES:
                if names_other_degree_level(url, degree):
                    trace.reject(url, f"{category} page names a degree level other than {degree}")
                    return False
                score += matches_degree(url, degree)
            if score <= 0:
                trace.reject(url, "scored zero for every category")
                return False
            if len(ranked[category]) >= MAX_CANDIDATES_PER_CATEGORY:
                # Keep the best, not the first: a later URL may outrank the
                # weakest one already held.
                weakest = min(ranked[category])
                if score <= weakest[0]:
                    return False
                ranked[category].remove(weakest)
            ranked[category].append((score, url))
            return True

        budget = self._budget
        if budget is not None:
            cost: HostCost | None = HostCost(first_read_rule=True)
        else:
            cost = HostCost() if COST_AWARE_SEARCH_ORDER else None
        stages = trace.stage_order if cost is not None else []
        stages.extend(["seeds", "sitemaps"] if seeds else ["sitemaps"])
        searched_early = False
        tried_early = False

        def search_reached_provider(queries: int, failures: int) -> bool:
            """SB-1c: a search counts as run only when it reached the provider.

            A search refused before any query (every slot held) leaves
            ``searched_early`` unset, so the search after the walker still
            runs; one the provider answered or failed is not repeated, and
            with SB-1 off, or without a provider or a field, nothing changes.
            """
            return (
                trace.search_queries_sent > queries
                or len(trace.search_failures) > failures
                or self._budget is None
                or not self._search_wanted
            )

        def note_candidates() -> None:
            """SB-1: hop roots open only where nothing offered a programme lead."""
            if budget is not None and (
                ranked[PageCategory.PROGRAM_PAGE] or selected[PageCategory.PROGRAM_PAGE]
            ):
                self._has_candidates = True

        # PC-1: with no search provider configured, the sitemap stage has its
        # own end and a stalled document closes the stage, not the host.
        stage_cap = (
            SITEMAP_STAGE_CAP and budget is not None and self._search_provider_or_none() is None
        )

        async def before_document(attempted: int) -> bool:
            """SB-1: cut the sitemap stage when spent, or search a slow host now."""
            nonlocal searched_early, tried_early
            if self._spent() or (budget is not None and budget.sitemap_spent()):
                return True
            if stage_cap and budget is not None and budget.elapsed() >= SITEMAP_STAGE_MAX_SECONDS:
                trace.errors.append(
                    f"PC-1: sitemap stage ended at {budget.elapsed():.1f} s "
                    f"({SITEMAP_STAGE_MAX_SECONDS:g} s with no search provider)"
                )
                return True
            if self._search_due():
                # SB-1b: the first query is due; search runs after this stage.
                return True
            if tried_early or searched_early or cost is None or not cost.slow:
                return False
            # Search costs the host no read; on a slow host it runs right
            # after the first sitemap document rather than after the stages
            # every read of which costs the host's delay.
            trace.host_cost = cost.as_dict()
            stages.append("search")
            tried_early = True
            note_candidates()
            previous = self._enter("search")
            queries, failures = trace.search_queries_sent, len(trace.search_failures)
            await self._add_search_results(entry, domain, selected, trace, profile)
            searched_early = search_reached_provider(queries, failures)
            self._enter(previous)
            # Stop when confirmed: the remaining sitemap documents are leads
            # for a page search already read and accepted.
            return self._programme_confirmed(selected)

        try:
            await self.sitemaps.collect(
                entry["homepage"],
                domain,
                trace,
                keep,
                cost,
                before_document if budget is not None else None,
                stall_local=stage_cap,
            )
        except Exception as exc:  # a malformed sitemap must not end the run
            trace.errors.append(f"sitemap discovery failed: {type(exc).__name__}: {exc}")
        if evidence_only:
            programmes = ranked[PageCategory.PROGRAM_PAGE]
            merged = merge_evidence_only(programmes, evidence_only)
            for pair in evidence_only:
                if pair not in merged:
                    trace.reject(pair[1], "R3: no slot left beside the structural programme leads")
            programmes.extend(merged)
        note_candidates()

        for category, scored in ranked.items():
            scored.sort(key=lambda pair: (-pair[0], len(pair[1])))
            if category == PageCategory.PROGRAM_PAGE:
                scored[:] = _prefer_exact_field(scored, fields)
            for _score, url in scored:
                if len(selected[category]) >= MAX_PAGES_PER_CATEGORY:
                    break
                if url not in selected[category]:
                    selected[category].append(url)

        # 3. Navigation, when sitemaps and seeds did not reach a programme page.
        #    An earlier version fell back only when *nothing at all* was found,
        #    so a registry entry with an admissions seed suppressed the fallback
        #    and the run finished with no programme — which the live canary
        #    showed on six of ten sites.
        if ADMISSIONS_HOST_FROM_HOMEPAGE:
            await self._admissions_host(entry, domain, trace)

        slow_host = cost is not None and cost.slow
        if cost is not None:
            trace.host_cost = cost.as_dict()

        def note_search_due() -> None:
            if budget is not None and self._search_due():
                trace.errors.append(
                    f"SB-1b: nothing confirmed by {SEARCH_LATEST_START_SECONDS:g} s; "
                    f"search starts at {budget.elapsed():.1f} s"
                )

        async def search_now() -> None:
            nonlocal searched_early
            note_search_due()
            self._enter("search")
            queries, failures = trace.search_queries_sent, len(trace.search_failures)
            await self._add_search_results(entry, domain, selected, trace, profile)
            searched_early = search_reached_provider(queries, failures)
            stages.append("search")

        if (
            not searched_early
            and not (self._search_cut() if budget is not None else self._spent())
            and (
                slow_host
                or self._search_due()
                or (
                    (SEARCH_BEFORE_NAVIGATION or COST_AWARE_SEARCH_ORDER)
                    and not selected[PageCategory.PROGRAM_PAGE]
                )
            )
        ):
            await search_now()
        if not selected[PageCategory.PROGRAM_PAGE]:
            if self._spent():
                stages.append("navigation_skipped")
            else:
                trace.used_navigation_fallback = True
                stages.append("navigation")
                self._enter("navigation")
                await self._navigation_fallback(
                    entry, domain, selected, trace, profile, keep=keep, ranked=ranked
                )
                note_candidates()
                if not searched_early and not self._search_cut() and self._search_due():
                    # SB-1b: the navigation fallback was cut for the first query.
                    await search_now()

        # 4. Confirm the programme candidates by reading them.
        #    URL shape alone cannot tell a programme from an open day: live runs
        #    offered "bachelor-open-day", "campus-tour", "webklassen" and a
        #    student newsletter as programme pages, all sitting under the same
        #    path as the real programmes. The classifier already knows the
        #    difference, so discovery asks it rather than guessing harder.
        self._enter("confirm")
        await self._confirm_programs(selected, ranked, trace, profile)
        stages.append("confirm")
        if slow_host:
            # Every catalogue read costs the host's delay; search already ran.
            stages.append("walker_skipped")
        elif budget is not None and (self._spent() or self._programme_confirmed(selected)):
            # SB-1: stop when confirmed — the walker looks for a page the
            # confirm stage already read and accepted.
            stages.append("walker_skipped")
        else:
            stages.append("walker")
            self._enter("walker")
            with reading_as("walker"):
                await self._walk_catalogs(entry, selected, trace, profile)
        # The walker confirms its own candidates under the T29 contract, which
        # deliberately trusts a university's own catalogue listing — so the
        # snapshot is taken after it, and step 7 judges only what search adds.
        confirmed_so_far = set(selected[PageCategory.PROGRAM_PAGE])

        if not searched_early and (self._search_cut() if budget is not None else self._spent()):
            stages.append("search_skipped")
        elif not searched_early:
            note_search_due()
            stages.append("search")
            self._enter("search")
            # Every programme page in the slots by now was read and accepted
            # by the confirm stage or the walker (QB-1 counts them confirmed).
            await self._add_search_results(
                entry, domain, selected, trace, profile, slots_confirmed=True
            )

        # 7. Confirm what search added — built, and off until it is measured.
        #    Step 4 runs before search, so a programme page the provider
        #    contributes reaches the candidate unconfirmed. Applying the
        #    step-4 predicate to those pages *looked* obviously right and the
        #    first live run said otherwise: programme-page recall fell 4/10 →
        #    1/10 and precision fell with it, so it cut correct pages and kept
        #    junk. The predicate is wrong for search-sourced pages in a way I
        #    cannot yet name, and a rule that removes evidence has to earn its
        #    place with a number, not an argument.
        if CONFIRM_SEARCH_PROGRAMMES:
            await self._confirm_added_programs(selected, confirmed_so_far, trace, profile)

        trace.selected = {k: list(v) for k, v in selected.items() if v}
        self._apply(candidate, selected, profile, trace)
        return candidate, trace

    async def _confirm_programs(
        self,
        selected: dict[str, list[str]],
        ranked: dict[str, list[tuple[int, str]]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Keep only programme pages that match the requested level and subject."""
        queued = [*selected[PageCategory.PROGRAM_PAGE]]
        # Next-best candidates, so rejecting one does not mean finding nothing.
        fields_wanted = _public_requested_fields(profile, trace)
        for _score, url in _prefer_exact_field(
            sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True), fields_wanted
        ):
            if url not in queued:
                queued.append(url)

        confirmed: list[str] = []
        requested_level = str(profile.context.level)
        fields = _public_requested_fields(profile, trace)
        reads = queued[:MAX_PROGRAM_CANDIDATES_CHECKED]
        position = 0
        while position < len(reads):
            url = reads[position]
            position += 1
            if len(confirmed) >= MAX_PAGES_PER_CATEGORY:
                break
            if self._budget is not None:
                if url in self._confirmed:
                    # SB-1: search on a slow host already read and accepted it.
                    confirmed.append(url)
                    continue
                if self._spent():
                    for unread in reads[position - 1 :]:
                        trace.reject(unread, "not read: the discovery stage budget is spent")
                    break
            result = await self.fetcher.get(url)
            if not result.ok:
                trace.reject(url, f"could not be read ({result.outcome.value})")
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "programme redirected off the institution's site")
                continue
            page = classify_page(url=result.final_url or url, html=result.text)
            reason = profile_rejects(
                page, requested_level, fields, url=result.final_url or url, country=trace.country
            )
            if LOCALIZED_IDENTITY:
                reads = self._queue_english_alternate(
                    result.final_url or url,
                    result.text,
                    page,
                    requested_level,
                    trace,
                    reads,
                    position,
                    refused=local_twin_wanted(reason),
                )
            trace.note_read(url, result.final_url or url, result.text, reason, page.subject or "")
            if reason is not None:
                trace.reject(url, reason)
                if SUBJECT_TITLE_SHAPES and not confirmed and is_related_refusal(reason):
                    before = reads
                    reads = _queue_field_sibling(
                        (url, result.final_url or url),
                        queued,
                        reads,
                        position,
                        fields,
                        requested_level,
                    )
                    if reads != before:
                        trace.errors.append(
                            f"R2b: reading {reads[position]} next, beside the related "
                            f"programme page {url}"
                        )
                if CONFIRM_REJECTS_SUBPAGE_HEAD and is_subpage_refusal(reason):
                    reads = _queue_subpage_parent(
                        (url, result.final_url or url), queued, reads, position, trace
                    )
                    trace.note_requirements_lead(
                        result.final_url or url, reason, page, requested_level, fields
                    )
                continue
            confirmed.append(url)
            if self._budget is not None:
                self._confirmed.add(url)
            if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                _remember_field_source(
                    trace,
                    url=url,
                    subject=page.subject or "",
                    fields=fields,
                    basis="classified_programme_page",
                    source_url=result.final_url or url,
                )

        if confirmed or selected[PageCategory.PROGRAM_PAGE]:
            # Only replace the list when something was actually checked; an
            # unreachable site keeps its leads rather than losing them silently.
            selected[PageCategory.PROGRAM_PAGE] = confirmed

    @staticmethod
    def _queue_english_alternate(
        url: str,
        html: str,
        page: PageClassification,
        requested_level: str,
        trace: DiscoveryTrace,
        reads: list[str],
        position: int,
        *,
        refused: bool = False,
    ) -> list[str]:
        """LI-1: put a local-language page's English twin next in the reads.

        The twin takes the next place inside the same read cap, so following it
        costs one read like any candidate; a page of another level is not
        followed, since its twin names that level too. R1: a refused English
        page's twin in the institution's language is followed the same way.
        """
        if page.degree_level and page.degree_level != requested_level:
            return reads
        twin, language = english_alternate(url, html, trace.domain), "English"
        if twin is None and refused:
            twin, language = local_alternate(url, html, trace.domain, trace.country), "local"
        if twin is None or twin in reads[:position]:
            return reads
        rest = [u for u in reads[position:] if u != twin]
        trace.errors.append(f"hreflang: reading the {language} alternate of {url}")
        return [*reads[:position], twin, *rest][:MAX_PROGRAM_CANDIDATES_CHECKED]

    async def _confirm_added_programs(
        self,
        selected: dict[str, list[str]],
        already_confirmed: set[str],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Apply the step-4 filter to the programme pages search added.

        The same question step 4 asks: does this page describe a programme at
        the requested level in a requested field? A page that cannot be read
        is kept rather than dropped — an unreachable page is not a refusal.

        The catalogue walker's own candidates are not re-judged here; it
        confirms them under the T29 contract, which deliberately trusts a
        university's own catalogue listing.
        """
        newcomers = [
            url for url in selected[PageCategory.PROGRAM_PAGE] if url not in already_confirmed
        ]
        if not newcomers:
            return

        requested_level = str(profile.context.level)
        fields = _public_requested_fields(profile, trace)
        refused: set[str] = set()
        # Anything past the cap stays unconfirmed rather than being dropped:
        # losing a lead unread is the worse failure, and MAX_PAGES_PER_CATEGORY
        # keeps `selected` far below this in practice. If that ever changes,
        # this is the line that decides which way the doubt falls.
        for url in newcomers[:MAX_PROGRAM_CANDIDATES_CHECKED]:
            result = await self.fetcher.get(url)
            if not result.ok:
                continue
            if not same_source_site(url, result.final_url or url):
                trace.reject(url, "programme redirected off the institution's site")
                refused.add(url)
                trace.field_sources.pop(canonical_url(url), None)
                continue
            page = classify_page(url=result.final_url or url, html=result.text)
            reason = profile_rejects(
                page, requested_level, fields, url=result.final_url or url, country=trace.country
            )
            trace.note_read(url, result.final_url or url, result.text, reason, page.subject or "")
            if reason is not None:
                trace.reject(url, reason)
                refused.add(url)
                trace.field_sources.pop(canonical_url(url), None)
            elif len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                _remember_field_source(
                    trace,
                    url=url,
                    subject=page.subject or "",
                    fields=fields,
                    basis="classified_programme_page",
                    source_url=result.final_url or url,
                )

        if refused:
            selected[PageCategory.PROGRAM_PAGE] = [
                url for url in selected[PageCategory.PROGRAM_PAGE] if url not in refused
            ]

    async def _walk_catalogs(
        self,
        entry: dict,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Read the catalogue itself for the programmes the earlier stages missed.

        The navigation fallback only reaches a few links on a catalogue, and a
        JS-rendered catalogue has no links in its HTTP body at all. The walker
        scores every link the page offers (and the JSON its page fetches, when
        a catalogue renderer is attached) and reads the strongest ones — but
        only when the confirm stage left room, and never beyond the per-category
        cap, so `_apply` sees at most what it always saw.
        """
        # Deferred: catalog_walker imports this module's URL helpers, so the
        # dependency points one way at import time (walker -> discovery).
        from app.adapters.discovery.catalog_walker import (
            TRACE_CANDIDATE_CAP,
            TRACE_OUTCOME_CAP,
            WALKER_MAX_CATALOGS,
            CatalogWalker,
        )

        if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
            return
        catalogues = list(selected[PageCategory.PROGRAM_CATALOG][:WALKER_MAX_CATALOGS])
        if not catalogues and trace.used_navigation_fallback:
            # The navigation fallback owns the homepage: when it ran and found
            # no catalogue anywhere, the homepage is the walk's last root.
            # When the fallback never ran, something was already found and the
            # walk would only repeat its work.
            homepage = entry.get("homepage")
            if homepage:
                catalogues = [homepage]
        if not catalogues:
            return

        walker = CatalogWalker(
            fetcher=self.fetcher,
            domain=trace.domain,
            extra_domains=trace.extra_domains,
            country=trace.country,
            degree=str(profile.context.level),
            fields=_public_requested_fields(profile, trace),
            page_recorder=self.page_recorder,
            # SB-1: no read once the budget is spent, none after a confirmation.
            stop=self._walker_stop if self._budget is not None else None,
            stop_when_confirmed=self._budget is not None,
        )
        try:
            walks = await walker.walk(catalogues[:WALKER_MAX_CATALOGS])
        except Exception as exc:  # a walker failure must not end discovery
            trace.errors.append(f"catalog walker failed: {type(exc).__name__}: {exc}"[:300])
            return

        for walk in walks:
            trace.walker["catalogs_walked"] += 1
            trace.walker["programs_confirmed"] += len(walk.confirmed)
            for link in walk.candidates:
                if len(trace.walker["candidates"]) >= TRACE_CANDIDATE_CAP:
                    break
                trace.walker["candidates"].append(
                    {
                        "url": link.url,
                        "label": link.label,
                        "score": link.score,
                        "source": link.source,
                    }
                )
            for url, outcome in walk.outcomes:
                if len(trace.walker["outcomes"]) >= TRACE_OUTCOME_CAP:
                    break
                trace.walker["outcomes"].append({"url": url, "outcome": outcome})
                self.walker_outcomes.append(
                    PageOutcome(url=url, category="catalog-walker", detail=outcome)
                )
            for url, twins in walk.alternates.items():
                trace.note_alternates(url, twins)
            for url, title in walk.related:
                trace.note_related(url, title)
            for url in walk.confirmed:
                if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
                    break
                if url not in selected[PageCategory.PROGRAM_PAGE]:
                    selected[PageCategory.PROGRAM_PAGE].append(url)
                    if self._budget is not None:
                        self._confirmed.add(url)
                    if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                        _remember_field_source(
                            trace,
                            url=url,
                            subject=walk.confirmed_subjects.get(url, ""),
                            fields=_public_requested_fields(profile, trace),
                            basis="classified_programme_page",
                        )

    async def _add_search_results(
        self,
        entry: dict,
        domain: str,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        *,
        slots_confirmed: bool = False,
    ) -> None:
        """Add programme pages a web search found, if one is configured.

        **Dormant unless a provider is set.** `UNIMATCH_SEARCH_PROVIDER`
        defaults to `none`, the factory raises, and this returns having done
        nothing — so a deployment without a key behaves byte-identically to
        before. Same pattern as ``page_recorder`` above.

        **Appended, never interleaved.** Whatever the sitemap and the walker
        found keeps its place; search only adds pages they missed. The
        alternative was measured and cost whole cases; the write-up lives with
        the benchmark tooling, which production deliberately cannot name — a
        guard test rejects any path to it from this package, docstrings
        included.

        A provider failure degrades this run rather than ending it: discovery
        keeps everything the other generators produced.
        """
        provider = self._search_provider_or_none()
        if provider is None:
            return

        fields = list(profile.context.intended_fields)
        if not fields:
            return
        if self._budget is not None:
            self._search_attempted = True
        # Every programme slot is already taken, so the recovery loop below
        # breaks on its first iteration and whatever the provider ranked is
        # discarded unread. Asking anyway is pure cost: measured, six provider
        # calls, one entry-point read and zero pages added when the registry,
        # the sitemaps and the catalogue walker had already filled the three
        # slots. Checking first is exactly equivalent — with no free slot,
        # search cannot contribute a page — and it removes a handshake, six
        # queries and three reads per institution from every such run.
        #
        # SB-1c: under SB-1 a slot is held only by a page a stage read and
        # accepted. An unread registry or sitemap lead is not a reason to skip
        # search: UiO's sitemap offered three /ba/ career pages, every one of
        # them was rejected when read, and with the slots counted full no
        # query was ever sent. Such leads step aside while search runs, so
        # identity recovery has free slots to read into; the confirm stage
        # still reads them afterwards.
        leads_before = list(selected[PageCategory.PROGRAM_PAGE])
        held = [url for url in leads_before if self._budget is None or url in self._confirmed]
        if len(held) >= MAX_PAGES_PER_CATEGORY:
            trace.search_limitations.append(
                f"Search not run at {entry['name']}: all {MAX_PAGES_PER_CATEGORY} "
                "programme-page slots were already filled by the registry, the "
                "sitemaps and the catalogue walker."
            )
            return
        leads = len(leads_before) - len(held)
        if leads:
            trace.errors.append(
                f"SB-1c: {leads} unconfirmed programme lead(s) hold no slot while search runs"
            )
            selected[PageCategory.PROGRAM_PAGE] = held
        try:
            await self._send_search(
                entry,
                domain,
                selected,
                trace,
                profile,
                provider,
                fields,
                slots_confirmed=slots_confirmed,
            )
        finally:
            if leads:
                # Confirmed pages first, so a budget spent while the confirm
                # stage reads the leads cannot drop a page search accepted.
                found = selected[PageCategory.PROGRAM_PAGE]
                first = [url for url in found if url in self._confirmed]
                selected[PageCategory.PROGRAM_PAGE] = list(
                    dict.fromkeys([*first, *leads_before, *found])
                )

    async def _send_search(
        self,
        entry: dict,
        domain: str,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        provider,
        fields: list[str],
        *,
        slots_confirmed: bool,
    ) -> None:
        """The provider half of :meth:`_add_search_results`, once a slot is free."""
        from app.adapters.search import SearchError
        from app.adapters.search import intent as intent_module
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DiscoveryIntent
        from app.adapters.search.retrieval import DEFAULT_HOP_ENTRY_POINTS, discover_candidates

        if len(_distinct_fields(fields)) > 1:
            await self._add_multi_field_search_results(
                entry, domain, selected, trace, profile, provider
            )
            return

        # LQ-2: the site's own phrase and the seed row's native name ("" while off).
        local_phrase, native_name = _local_phrase_fields(entry, trace)
        try:
            intent = DiscoveryIntent(
                institution=entry["name"],
                # The institution, not the host its homepage sits on: Warsaw's
                # registry homepage is en.uw.edu.pl and its programme catalogue
                # is informatorects.uw.edu.pl, so a host filter kept search on
                # the news pages (run 53).
                domain=registrable_domain(domain) or domain,
                degree=profile.context.level,
                field=fields[0],
                # R5: the institution's own country (its registry row), never
                # the applicant's; read only while LOCAL_LANGUAGE_QUERIES is on.
                institution_country=(
                    trace.country or str(entry.get("country") or "")
                    if intent_module.LOCAL_LANGUAGE_QUERIES
                    else ""
                ),
                local_phrase=local_phrase,
                native_name=native_name,
            )
        except ValueError:
            # A registry entry or a field the intent refuses — for instance one
            # carrying something that looks like applicant data. Skip search for
            # this institution rather than sending it.
            trace.errors.append("search skipped: invalid public discovery intent")
            return
        if intent_module.LOCAL_QUERY_FROM_PAGE_EVIDENCE and intent_module.LOCAL_LANGUAGE_QUERIES:
            _note_local_phrase_plan(intent, trace)

        async def read(url: str) -> str:
            # The adapter's own Fetcher, so robots, rate limits, the PII guard
            # and the SSRF protections apply exactly as they do everywhere else.
            result = await self.fetcher.get(url)
            return (
                result.text if result.ok and same_source_site(url, result.final_url or url) else ""
            )

        allowance = self._query_allowance(trace)
        if allowance <= 0:
            trace.search_limitations.append(
                f"Search not run at {entry['name']}: the institution's "
                f"{intent_module.DEFAULT_QUERY_BUDGET}-query budget is spent."
            )
            return
        if intent_module.DISCOVERY_QUERY_RESERVE and RECOVER_SEARCH_CANDIDATES:
            await self._search_in_two_passes(
                entry,
                intent,
                provider,
                read,
                selected[PageCategory.PROGRAM_PAGE],
                trace,
                profile,
                slots_confirmed=slots_confirmed,
            )
            return

        # The full budget keeps the plan exactly as before; only an institution
        # that already spent queries gets a shorter one.
        budget = None if allowance >= intent_module.DEFAULT_QUERY_BUDGET else allowance
        try:
            if self._budget is None:
                report = await discover_candidates(
                    provider, intent, query_budget=budget, fetch=read, top_k=10
                )
            else:
                self._budget.query_sent()
                report = await discover_candidates(
                    provider,
                    intent,
                    query_budget=budget,
                    fetch=read,
                    top_k=10,
                    hop_entry_points=0 if self._skip_hop_roots() else DEFAULT_HOP_ENTRY_POINTS,
                )
        except SearchError as exc:
            trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
            return
        trace.search_queries_sent += len(report.queries_run)
        trace.record_search_results(report.results_by_family)

        trace.search_failures.extend(report.failure_diagnostics)
        if report.throttled:
            trace.search_limitations.append(
                f"Search at {entry['name']} stopped: {report.provider} answered "
                "HTTP 429, so the remaining query families were not sent. This "
                "is a quota stop, not a search that found nothing."
            )
        pages = selected[PageCategory.PROGRAM_PAGE]
        if RECOVER_SEARCH_CANDIDATES:
            await self._recover_search_pages(report.candidates, pages, trace, profile, reserve=True)
            trace.errors.append(
                f"search identity recovery via {report.provider}; queries {len(report.queries_run)}, "
                f"failed {len(report.failed_queries)}, rejected {dict(report.rejection_counts)}"
            )
            return
        added = 0
        refused = getattr(self.fetcher, "refused_hosts", {})
        skipped: list[str] = []
        navigation = next(
            (c for c in report.candidates if c.provider == "navigation" and c.url not in pages),
            None,
        )
        limit = MAX_PAGES_PER_CATEGORY - (1 if NAVIGATION_SLOT and navigation else 0)
        for found in report.candidates:
            if len(pages) >= limit:
                break
            if found.url in pages:
                continue
            if SKIP_REFUSED_SEARCH_HOSTS and (urlparse(found.url).hostname or "") in refused:
                skipped.append(found.url)
                continue
            pages.append(found.url)
            added += 1
        if NAVIGATION_SLOT and navigation is not None and navigation.url not in pages:
            pages.append(navigation.url)
            added += 1
            trace.errors.append(f"navigation slot: {navigation.url}")
        if skipped:
            trace.errors.append(
                f"search skipped {len(skipped)} candidate(s) on hosts that refused this run: "
                + ", ".join(skipped)[:400]
            )
        # Which pages search offered, so a miss can be told apart from
        # "search never saw the programme" (run 46, Warsaw).
        offered = ", ".join(c.url for c in report.candidates[:5]) or "none"
        trace.errors.append(
            (
                f"search added {added} programme page(s) via {report.provider}"
                if added
                else f"search added nothing via {report.provider}"
            )
            + f"; offered: {offered}"[:600]
            + f"; queries {len(report.queries_run)}, failed {len(report.failed_queries)}"
            + f", rejected {dict(report.rejection_counts)}"[:300]
        )

    async def _search_in_two_passes(
        self,
        entry: dict,
        intent,
        provider,
        read,
        pages: list[str],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        *,
        slots_confirmed: bool,
    ) -> None:
        """QB-1: three query families first; the other three only if nothing was confirmed.

        "Confirmed" is decided here, between the passes, because this is the
        first point that knows it: the first pass's candidates go through
        identity recovery (each read through the Fetcher, classified, and
        accepted by the same predicate as always) before the second pass is
        considered. A programme page counts as confirmed when that recovery
        accepted it, or when it already held a slot as search began *after*
        the confirm stage and the walker (``slots_confirmed``), which accept
        only pages they read. An unread lead never counts. A 429 or a provider
        error in the first pass also ends the search, as it always has.

        The second pass sends only the families the first did not, and opens
        no new navigation entry points: the first pass's hop already read the
        roots, and the per-institution read cap of identity recovery is shared
        by both passes.

        QB-1b: when a programme page is confirmed before the first pass, that
        pass opens no entry points either and recovery reads at most
        PRECONFIRMED_RECOVERY_CHECKS candidates, so the reserved queries are
        not paid for with reads and wall clock the page no longer needs.
        """
        from app.adapters.search import SearchError
        from app.adapters.search import intent as intent_module
        from app.adapters.search import retrieval as _retrieval
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.retrieval import DEFAULT_HOP_ENTRY_POINTS, discover_candidates

        planned = [query.family for query in intent_module.queries_for(intent)]
        planned = planned[: self._query_allowance(trace)]
        first = planned[: intent_module.DISCOVERY_FIRST_PASS_QUERIES]
        rest = planned[len(first) :]
        confirmed = len(pages) if slots_confirmed else 0
        state = _RecoveryState(visited=set(pages))
        first_hop = DEFAULT_HOP_ENTRY_POINTS
        if confirmed:
            first_hop = 0
            state.max_checks = PRECONFIRMED_RECOVERY_CHECKS
            trace.errors.append(
                f"QB-1: first pass capped at {PRECONFIRMED_RECOVERY_CHECKS} checks and no "
                "entry-point hop; a programme page was confirmed before search"
            )
        elif self._skip_hop_roots():
            first_hop = 0
            trace.errors.append("SB-1: no entry-point hop; discovery already has a programme lead")
        for number, families in enumerate((first, rest), start=1):
            if not families:
                break
            # SB-1b: the read cap does not stop the first pass; a query is not a read.
            if self._search_cut() if number == 1 else self._spent():
                trace.errors.append(
                    f"SB-1: discovery pass {number} not sent; the stage budget is spent"
                )
                break
            if number == 2 and confirmed:
                trace.errors.append(
                    f"QB-1: {len(families)} discovery quer{'y' if len(families) == 1 else 'ies'} "
                    "left for topic and award search; a programme page was confirmed after "
                    "the first pass"
                )
                break
            # RK-2(c): before the first confirmation can stop recovery, each
            # first-pass family's top result is read ahead of the ranked order.
            # Only the order changes: the same predicate, the same single stop.
            tops_first = (
                _retrieval.RETRIEVAL_RANK_V2 and number == 1 and not confirmed and not pages
            )
            try:
                if self._budget is not None:
                    self._budget.query_sent()
                report = await discover_candidates(
                    provider,
                    intent,
                    query_budget=len(families),
                    only_families=families,
                    fetch=read,
                    hop_entry_points=first_hop if number == 1 else 0,
                    top_k=10,
                    **({"family_tops_first": True} if tops_first else {}),
                )
            except SearchError as exc:
                trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
                break
            trace.search_queries_sent += len(report.queries_run)
            trace.record_search_results(report.results_by_family)
            trace.discovery_query_passes.append(len(report.queries_run))
            trace.search_failures.extend(report.failure_diagnostics)
            if report.family_tops_first:
                trace.errors.append(
                    "RK-2: family top results moved ahead of the ranked order: "
                    + ", ".join(report.family_tops_first)[:400]
                )
            confirmed += await self._recover_search_pages(
                report.candidates,
                pages,
                trace,
                profile,
                state=state,
                final=False,
                reserve=number == 1,
            )
            trace.errors.append(
                f"search identity recovery via {report.provider} (QB-1 pass {number}); "
                f"queries {len(report.queries_run)}, failed {len(report.failed_queries)}, "
                f"rejected {dict(report.rejection_counts)}"
            )
            if report.throttled:
                trace.search_limitations.append(
                    f"Search at {entry['name']} stopped: {report.provider} answered "
                    "HTTP 429, so the remaining query families were not sent. This "
                    "is a quota stop, not a search that found nothing."
                )
                break
        self._settle_pending(pages, trace, state.pending, multi_requested=False)

    async def _add_multi_field_search_results(
        self, entry, domain, selected, trace, profile, provider
    ) -> None:
        """Search distinct subjects under one institution-wide paid/read budget."""
        from app.adapters.search import SearchError
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DiscoveryIntent
        from app.adapters.search.retrieval import DEFAULT_HOP_ENTRY_POINTS, discover_candidates

        fields = _distinct_fields(list(profile.context.intended_fields))
        public_fields = _public_requested_fields(profile, trace)
        skipped = len(fields) - len(public_fields)
        intents = []
        for field_name in public_fields:
            try:
                intents.append(
                    DiscoveryIntent(
                        institution=entry["name"],
                        domain=registrable_domain(domain) or domain,
                        degree=profile.context.level,
                        field=field_name,
                    )
                )
            except ValueError:
                # A registry value can also fail public-query validation;
                # sitemap and catalogue matching still use the safe field.
                continue
        if skipped:
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: {skipped} requested subject(s) "
                "failed query privacy validation and were not searched."
            )
        allowance = self._query_allowance(trace)
        chosen = intents[:allowance]
        trace.queried_fields = [intent.field for intent in chosen]
        if len(intents) > len(chosen):
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: {len(chosen)} of "
                f"{len(fields)} requested subjects were queried; "
                f"{len(intents) - len(chosen)} were not searched because of the "
                "six-query budget. Search remaining subjects in a separate run."
            )
        if len(fields) > MAX_PAGES_PER_CATEGORY:
            trace.search_limitations.append(
                f"Search coverage limited at {entry['name']}: up to "
                f"{MAX_PAGES_PER_CATEGORY} programmes can be shown per university, "
                "so not every requested subject can appear in this run."
            )
        trace.search_coverage = {
            "requested": len(fields),
            "queried": len(chosen),
            "represented": 0,
        }
        if not chosen:
            return

        query_budgets = [1] * len(chosen)
        for slot in range(allowance - len(chosen)):
            query_budgets[slot % len(chosen)] += 1
        hop_budgets = [0] * len(chosen)
        for slot in range(0 if self._skip_hop_roots() else DEFAULT_HOP_ENTRY_POINTS):
            hop_budgets[slot % len(chosen)] += 1

        async def read(url: str) -> str:
            result = await self.fetcher.get(url)
            return (
                result.text if result.ok and same_source_site(url, result.final_url or url) else ""
            )

        reports = []
        query_count = 0
        failed_count = 0
        rejection_counts: dict[object, int] = {}
        for intent, query_budget, hop_budget in zip(
            chosen, query_budgets, hop_budgets, strict=True
        ):
            if self._search_cut() if intent is chosen[0] else self._spent():
                break
            try:
                if self._budget is not None:
                    self._budget.query_sent()
                report = await discover_candidates(
                    provider,
                    intent,
                    query_budget=query_budget,
                    fetch=read,
                    hop_entry_points=hop_budget,
                    top_k=10,
                )
            except SearchError as exc:
                trace.search_failures.append(search_failure_diagnostic(provider.name, exc))
                continue
            reports.append((intent.field, report))
            trace.search_failures.extend(report.failure_diagnostics)
            # Counted before a throttle stop: the queries sent before the 429
            # were spent, and leaving them out understated the run's cost.
            query_count += len(report.queries_run)
            trace.search_queries_sent += len(report.queries_run)
            trace.record_search_results(report.results_by_family)
            failed_count += len(report.failed_queries)
            if report.throttled:
                # One rate-limit answer ends the run's searching, not just this
                # subject's: the remaining subjects would each re-send a query
                # into a quota that has already refused.
                trace.search_limitations.append(
                    f"Search at {entry['name']} stopped: {provider.name} answered "
                    "HTTP 429, so the remaining subjects were not searched. This "
                    "is a quota stop, not a search that found nothing."
                )
                break
            for reason, count in report.rejection_counts.items():
                rejection_counts[reason] = rejection_counts.get(reason, 0) + count

        # A previously confirmed sitemap/walker page already occupies a slot.
        # Give an as-yet-unrepresented field first access to the remaining
        # slots, while keeping each report's own rank order.
        represented_before = {
            trace.field_sources.get(canonical_url(url), {}).get("field", "")
            for url in selected[PageCategory.PROGRAM_PAGE]
        }
        reports.sort(key=lambda item: item[0] in represented_before)

        # Scores are relative to one field's intent, so preserve per-field
        # ranking and take turns rather than comparing scores across fields.
        merged = []
        seen: set[str] = set()
        longest = max((len(report.candidates) for _, report in reports), default=0)
        for rank in range(longest):
            for field_name, report in reports:
                if rank >= len(report.candidates):
                    continue
                found = report.candidates[rank]
                key = canonical_url(found.url)
                if key in seen:
                    continue
                seen.add(key)
                trace.field_hints[key] = field_name
                merged.append(found)

        pages = selected[PageCategory.PROGRAM_PAGE]
        if RECOVER_SEARCH_CANDIDATES:
            await self._recover_search_pages(merged, pages, trace, profile, reserve=True)
            trace.errors.append(
                f"search identity recovery via {provider.name}; queries {query_count}, "
                f"failed {failed_count}, rejected {rejection_counts}"
            )
            return
        added = 0
        refused = getattr(self.fetcher, "refused_hosts", {})
        skipped_hosts: list[str] = []
        navigation = next(
            (c for c in merged if c.provider == "navigation" and c.url not in pages), None
        )
        limit = MAX_PAGES_PER_CATEGORY - (1 if NAVIGATION_SLOT and navigation else 0)
        for found in merged:
            if len(pages) >= limit:
                break
            if found.url in pages:
                continue
            if SKIP_REFUSED_SEARCH_HOSTS and (urlparse(found.url).hostname or "") in refused:
                skipped_hosts.append(found.url)
                continue
            pages.append(found.url)
            added += 1
        if NAVIGATION_SLOT and navigation is not None and navigation.url not in pages:
            pages.append(navigation.url)
            added += 1
            trace.errors.append(f"navigation slot: {navigation.url}")
        if skipped_hosts:
            trace.errors.append(
                f"search skipped {len(skipped_hosts)} candidate(s) on hosts that refused this run: "
                + ", ".join(skipped_hosts)[:400]
            )
        offered = ", ".join(c.url for c in merged[:5]) or "none"
        trace.errors.append(
            f"search added {added} programme page(s) via {provider.name}; offered: {offered}"[:600]
            + f"; queries {query_count}, failed {failed_count}, rejected {rejection_counts}"[:300]
        )

    async def _recover_search_pages(
        self,
        candidates,
        pages,
        trace,
        profile,
        *,
        state: _RecoveryState | None = None,
        final: bool = True,
        reserve: bool = False,
    ) -> int:
        """Fill programme slots from fetched identities rather than search snippets.

        Existing confirmed catalogue/sitemap pages stay first. A rejected lead
        frees a slot for the next search result. The legacy single-field path
        keeps host failures as unresolved leads; a multi-field result requires
        source-backed field identity before it can become a programme.

        Returns how many pages it confirmed (read and accepted). ``state`` and
        ``final=False`` let QB-1 run it once per provider pass under one read
        cap, settling unread leads only after the last pass. ``reserve`` (SB-1b,
        the first pass) lets it read past a spent discovery budget, up to
        RECOVERY_RESERVE_READS reads.

        UA-1 (``ABSTAIN_ON_UNREADABLE_ENTRY``): when no entry read of the
        institution succeeded, an accepted lead is held as
        ``trace.unresolved_access`` instead of confirmed. A held lead stops
        recovery and counts in the return value exactly where a confirmed one
        would, so the rule reads and queries no more than the off arm.
        """
        from app.adapters.discovery.catalog_walker import extract_links, score_link
        from app.adapters.extraction import html_to_text
        from app.adapters.requirements.web_requirements import (
            _LISTING_PAGE_TYPES,
            _listed_programme,
        )

        fields = _public_requested_fields(profile, trace)
        multi_requested = len(_distinct_fields(list(profile.context.intended_fields))) > 1
        level = str(profile.context.level)
        if state is None:
            state = _RecoveryState()
        state.visited.update(pages)
        pending = state.pending
        queue = list(candidates)
        if EXACT_FIELD_LEAD_FIRST and not multi_requested:
            # EF-1: the field's own page before its joint and related siblings.
            queue = exact_field_leads_first(queue, fields)
        visited = state.visited
        checked = state.checked
        added = 0
        held = 0
        #: QT-1: the confirmed page's qualifier twin, read next past SB-1's stop.
        twin_next: str | None = None
        twin_read = False
        abstain = ABSTAIN_ON_UNREADABLE_ENTRY and trace.entry_hosts_unreadable()
        if abstain and not trace.entry_unreadable:
            trace.entry_unreadable = True
            trace.errors.append(ENTRY_UNREADABLE_LINE)
        previous_stage = self._enter("recovery")
        while queue:
            if len(pages) + held >= MAX_PAGES_PER_CATEGORY:
                break
            # PL-1(a): a followed link spends its own checks, not the provider results'.
            followed = PROVIDER_LEAD_FLOOR and queue[0].provider == SEARCH_CATALOGUE_LEAD
            if (state.followed if followed else checked) >= state.max_checks:
                if not PROVIDER_LEAD_FLOOR:
                    break
                queue.pop(0)
                continue
            twin_due = twin_next is not None and queue[0].url == twin_next
            if self._budget is not None and (
                ((added or held) and not multi_requested and not twin_due)
                or (
                    self._spent()
                    and not (
                        reserve
                        and (
                            self._budget.reserve_open()
                            or (twin_due and await self._twin_reserve(queue[0].url, trace))
                        )
                    )
                )
            ):
                # SB-1: stop when confirmed (QT-1: once its twin is read), or
                # when the budget is spent and (SB-1b) the first pass's
                # reserve is used or not open. QT-1: the twin of a confirmation
                # whose read ran past the deadline may still use the reserve —
                # the confirmation was in time, its twin is one read — when
                # the case clock can spare it (QT-1c).
                break
            found = queue.pop(0)
            if found.url == twin_next:
                twin_next = None
            if found.url in visited:
                continue
            visited.add(found.url)
            if followed:
                state.followed += 1
            else:
                checked += 1
            if _intent_module.LOCAL_LANGUAGE_QUERIES:
                trace.note_found_by(found.url, getattr(found, "found_by", ()))
            if self._budget is not None:
                self._budget.note_recovery_read()
            result = await self.fetcher.get(found.url)
            if not result.ok:
                pending.append(found.url)
                trace.reject(found.url, f"search lead unresolved ({result.outcome.value})")
                continue
            if not same_source_site(found.url, result.final_url or found.url):
                trace.reject(found.url, "search lead redirected off the institution's site")
                continue
            page = classify_page(url=result.final_url or found.url, html=result.text)
            reason = profile_rejects(
                page, level, fields, url=result.final_url or found.url, country=trace.country
            )
            if LOCALIZED_IDENTITY and not (page.degree_level and page.degree_level != level):
                read_url = result.final_url or found.url
                twin, language = english_alternate(read_url, result.text, trace.domain), "English"
                if twin is None and local_twin_wanted(reason):
                    # R1: a refused English page's twin in the institution's language
                    # (change #2(a): only an identity refusal's, when its flag is on).
                    twin = local_alternate(read_url, result.text, trace.domain, trace.country)
                    language = "local"
                if twin is not None and twin not in visited:
                    from app.adapters.search.retrieval import RankedCandidate as _Twin

                    trace.errors.append(
                        f"hreflang: reading the {language} alternate of {found.url}"
                    )
                    queue[:0] = [_Twin(twin, found.title, found.score, "hreflang-alternate")]
            stated_level = page.degree_level
            matched_subject = page.subject or ""
            basis = "classified_programme_page"
            if reason is not None and page.page_type in _LISTING_PAGE_TYPES:
                if multi_requested:
                    # A search title is an unverified hint. It can name an
                    # unrelated degree on an otherwise official listing.
                    listed = None
                    for field_name in _distinct_fields(fields):
                        program = CandidateProgram(
                            name=field_name,
                            field=field_name,
                            degree=profile.context.level,
                            url=found.url,
                        )
                        candidate_title = _listed_programme(html_to_text(result.text), program)
                        if candidate_title and matches_field_text(candidate_title[0], [field_name]):
                            listed = candidate_title
                            break
                else:
                    program = CandidateProgram(
                        name=found.title,
                        field=fields[0] if fields else "",
                        degree=profile.context.level,
                        url=found.url,
                    )
                    listed = _listed_programme(html_to_text(result.text), program)
                if listed is not None and CONFIRM_REQUIRES_HEAD_IDENTITY:
                    # CH-1: a full degree title in the body says the page
                    # lists the programme, not that the page is it; the
                    # head must carry the identity as for any candidate.
                    head = head_identity_rejects(
                        page, level, fields, url=result.final_url or found.url
                    )
                    if head is not None:
                        reason = head
                        listed = None
                if listed is not None:
                    reason = None
                    stated_level = listed[1]
                    matched_subject = listed[0]
                    basis = "full_degree_title_on_listing"
            if reason is None:
                if stated_level != level:
                    reason = "page does not state the requested degree level"
                variants = re.findall(
                    r"\b(?:teacher (?:education|training)|teaching (?:education|subject)"
                    r"|digital literacy|minor|certificate|speciali[sz]ations?|second major"
                    r"|double degree|final examination|final exam|degree plans?"
                    r"|courses? for teachers?|recommended path|why computer science)\b",
                    (page.subject or "") + " " + urlparse(found.url).path.replace("-", " "),
                    flags=re.I,
                )
                if any(not any(v.lower() in f.lower() for f in fields) for v in variants):
                    reason = (
                        "page names an alternate programme variant not requested: "
                        + ", ".join(variants)
                    )
            if (
                reason is None
                and FRONT_PAGE_NOT_PROGRAMME
                and (is_front_page(found.url) or is_front_page(result.final_url or found.url))
            ):
                # FP-1: a front page lists programmes; it is not one of them.
                reason = FRONT_PAGE_VERDICT
            trace.note_read(
                found.url, result.final_url or found.url, result.text, reason, page.subject or ""
            )
            if reason is not None:
                trace.reject(found.url, reason)
                if CONFIRM_REJECTS_SUBPAGE_HEAD and is_subpage_refusal(reason):
                    _read_subpage_parent_next(
                        queue, (found.url, result.final_url or found.url), visited, trace
                    )
                    trace.note_requirements_lead(
                        result.final_url or found.url, reason, page, level, fields
                    )
                if page.page_type in _LISTING_PAGE_TYPES or (
                    LISTING_FOLLOWS_LOCAL_ALIASES
                    and _page_classifier.head_names_only_a_level(
                        page.subject or "", _page_classifier.page_language(result.text)
                    )
                    == level
                ):
                    # A search result can be the catalogue, not its detail
                    # page. Follow its own matching links before trying more
                    # search noise, sharing the same overall read bound.
                    # LL-1: a page headed by the requested level alone is one.
                    from app.adapters.search.retrieval import RankedCandidate

                    leads = []
                    for link in extract_links(result.text, found.url, trace.domain):
                        value = score_link(link.url, link.label, level, fields)
                        if value is None:
                            continue
                        title = link.label
                        if not matches_field_text(link.label, fields):
                            # LL-1: a card's own heading names it when its
                            # whole text (code, name, description) cannot.
                            if not (
                                LISTING_FOLLOWS_LOCAL_ALIASES
                                and link.heading
                                and matches_field_text(link.heading, fields)
                            ):
                                continue
                            title = link.heading
                            named = score_link(link.url, link.heading, level, fields)
                            value = max(value, named or 0)
                        if link.url not in visited:
                            leads.append(
                                RankedCandidate(link.url, title, value, SEARCH_CATALOGUE_LEAD)
                            )
                    leads.sort(key=lambda lead: (-lead.score, lead.url))
                    spent = state.followed if PROVIDER_LEAD_FLOOR else checked
                    followups = leads[: state.max_checks - spent]
                    if multi_requested:
                        # Another requested field's direct search result is
                        # already waiting. Do not let one catalogue's many
                        # links consume the shared read cap ahead of it.
                        queue.extend(followups)
                    else:
                        queue[:0] = followups
                continue
            if abstain:
                # UA-1: a lead, not the programme page; no programme scope.
                held += 1
                if found.url not in trace.unresolved_access:
                    trace.unresolved_access.append(found.url)
                continue
            pages.append(found.url)
            added += 1
            if self._budget is not None:
                self._confirmed.add(found.url)
                if CONFIRM_READS_QUALIFIER_TWIN and not (multi_requested or twin_read):
                    twin_next = self._queue_qualifier_twin(queue, found.url, level, visited, trace)
                    twin_read = twin_next is not None
            if multi_requested:
                _remember_field_source(
                    trace,
                    url=found.url,
                    subject=matched_subject,
                    fields=fields,
                    basis=basis,
                    source_url=result.final_url or found.url,
                )
        state.checked = checked
        self._enter(previous_stage)
        if final:
            self._settle_pending(pages, trace, pending, multi_requested=multi_requested)
        trace.errors.append(
            f"search identity recovery: checked {checked}, confirmed {added}"
            + (f", followed links {state.followed}" if PROVIDER_LEAD_FLOOR else "")
            + (f", held as unresolved access {held}" if abstain else "")
        )
        return added + held

    async def _twin_reserve(self, twin: str, trace: DiscoveryTrace) -> bool:
        """QT-1: whether the first pass's SB-1b reserve has a read left for the twin.

        ``reserve_open`` shuts the reserve past the deadline once a recovery
        read started in time; on ubc that read was the confirmation itself
        (started at 49 s, done at 58 s of 55), so its twin was never read.
        The twin is exempt from that clause only: it still spends a reserve
        read and goes through the Fetcher and the case time budget (TB-1).

        QT-1c: and only when the case clock predicts the twin's read leaves
        both TB-1 reserves (``QUALIFIER_TWIN_READ_KIND``), so the verify
        stage's core reads after it still start. rp-qt1b-cohort ubc: the twin
        read at 57 s took 6.6-7 s of a slow host, and "Dates & deadlines" was
        refused with 16.9 s and 18.1 s left (``ubc:deadline`` lost in both
        repetitions). Otherwise the twin is not read: QT-1's stop at the
        deadline, as before QT-1b.
        """
        budget = self._budget
        if budget is None or budget.reserve_used >= budget.reserve:
            return False
        refusal = await _fetching.time_refusal_now(self.fetcher, twin, QUALIFIER_TWIN_READ_KIND)
        if refusal:
            trace.errors.append(
                f"QT-1: not reading the qualifier twin {twin} past the deadline; "
                f"case time budget (TB-1): {refusal}"
            )
            return False
        return True

    @staticmethod
    def _queue_qualifier_twin(
        queue: list[Any], confirmed: str, level: str, visited: set[str], trace: DiscoveryTrace
    ) -> str | None:
        """QT-1: move the confirmed page's qualifier twin, if unread, to the queue's head."""
        twin = qualifier_twin(
            confirmed, [lead.url for lead in queue if lead.url not in visited], level
        )
        if twin is None:
            return None
        index = next(i for i, lead in enumerate(queue) if lead.url == twin)
        queue.insert(0, queue.pop(index))
        trace.errors.append(
            f"QT-1: reading {twin}, the qualifier twin of the confirmed {confirmed}"
        )
        return twin

    @staticmethod
    def _settle_pending(
        pages: list[str], trace: DiscoveryTrace, pending: list[str], *, multi_requested: bool
    ) -> None:
        """What becomes of the search leads identity recovery could not read."""
        # Preserve the legacy single-field lead fallback. In a multi-field
        # run, a search title cannot establish which subject an unreadable
        # page actually covers, so keep the failure only in diagnostics.
        if _page_classifier.PROGRAMME_PAGE_GUARD:
            # PG-1: an unread page is not a programme page. Aalto reported
            # three it never read when its robots.txt was unreachable.
            trace.unresolved.extend(url for url in pending if url not in trace.unresolved)
        elif not pages and not multi_requested and not trace.entry_unreadable:
            # UA-1: an unread lead is no programme page when no entry read succeeded.
            pages.extend(pending[:MAX_PAGES_PER_CATEGORY])
        if multi_requested and pending:
            trace.search_limitations.append(
                f"Search coverage limited at {trace.institution}: "
                f"{len(pending)} programme lead(s) could not be read, so their "
                "subjects were not confirmed from the source page."
            )

    def _apply(
        self,
        candidate: Candidate,
        selected: dict[str, list[str]],
        profile: ApplicantProfileIn,
        trace: DiscoveryTrace,
    ) -> None:
        """Attach what was found. A category with nothing stays None."""
        candidate.search_queries_used = trace.search_queries_sent
        candidate.extra_domains = list(trace.extra_domains)
        candidate.admissions_url = _first(selected[PageCategory.ADMISSIONS])
        candidate.costs_url = _first(selected[PageCategory.COSTS])
        candidate.scholarships_url = _first(selected[PageCategory.SCHOLARSHIPS])
        # SP-2: empty unless the rule is on and SP-1 refused a process page.
        candidate.requirements_leads = list(trace.requirements_leads)

        fields = _public_requested_fields(profile, trace)
        for url in selected[PageCategory.PROGRAM_PAGE][:MAX_PAGES_PER_CATEGORY]:
            if profile.context.intended_fields and not fields:
                break
            field_name = fields[0] if fields else ""
            program_name = _program_name_from_url(url, fields, profile.context.level)
            if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                source = trace.field_sources.get(canonical_url(url), {})
                field_name = (
                    source.get("field") or trace.field_hints.get(canonical_url(url)) or field_name
                )
                # A curriculum slug can name its matriculation year rather
                # than its degree. Retain the already fetched programme
                # subject so downstream verification checks the same identity.
                program_name = source.get("subject") or program_name
            candidate.programs.append(
                CandidateProgram(
                    name=program_name,
                    field=field_name,
                    degree=profile.context.level,
                    url=url,
                )
            )
        if trace.search_coverage:
            queried_fields = set(trace.queried_fields)
            represented = {
                trace.field_sources[canonical_url(program.url)]["field"]
                for program in candidate.programs
                if program.url
                and canonical_url(program.url) in trace.field_sources
                and trace.field_sources[canonical_url(program.url)]["field"] in queried_fields
            }
            trace.search_coverage["represented"] = len(represented)
            if len(candidate.programs) >= MAX_PAGES_PER_CATEGORY and len(represented) < min(
                trace.search_coverage["queried"], MAX_PAGES_PER_CATEGORY
            ):
                trace.search_limitations.append(
                    f"Search coverage limited at {trace.institution}: all "
                    f"{MAX_PAGES_PER_CATEGORY} programme slots are filled; "
                    f"only {len(represented)} of {trace.search_coverage['queried']} "
                    "queried subjects have source-confirmed programme pages. "
                    "Search remaining subjects in a separate run."
                )
        # A catalogue is a lead, not a programme. It is offered only when no
        # programme page was found, and downstream classification will reject it
        # as a source of requirements — which is the correct outcome.
        if not candidate.programs and selected[PageCategory.PROGRAM_CATALOG]:
            trace.errors.append(
                "no programme page was found; only a catalogue, which cannot confirm a programme"
            )

        found = [c for c in PageCategory.ALL if selected[c]]
        missing = [c for c in PageCategory.ALL if not selected[c]]
        candidate.notes = f"Sitemap-first discovery found: {', '.join(found) or 'nothing'}." + (
            f" Not found: {', '.join(missing)}." if missing else ""
        )

    async def _admissions_host(self, entry: dict, domain: str, trace: DiscoveryTrace) -> None:
        """DI-1: read the homepage once and record its one admissions domain."""
        homepage = entry.get("homepage") or ""
        if not homepage or not same_institution(homepage, domain):
            return
        result = await self.fetcher.get(homepage)
        trace.note_entry_read(result.ok, homepage=True)
        if not result.ok or not same_source_site(homepage, result.final_url or homepage):
            return
        record = admissions_host_from_homepage(result.text, result.final_url or homepage, domain)
        if not record:
            return
        trace.admissions_host = record
        extra = record.get("domain")
        if isinstance(extra, str):
            trace.extra_domains = [extra]

    async def _navigation_fallback(
        self,
        entry: dict,
        domain: str,
        selected: dict[str, list[str]],
        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        *,
        keep: Callable[[str], bool] | None = None,
        ranked: dict[str, list[tuple[int, str]]] | None = None,
    ) -> None:
        """Walk the catalogue's links, then the homepage's.

        A programme catalogue is the page a university builds precisely to list
        its programmes, so when discovery has one it is a far better place to
        look than the global menu. The homepage is the last resort.

        R4 (``LOCAL_CATALOGUE_ENTRY``): the homepage's section links, named in
        the institution's own language, lead on to the catalogue, and a
        catalogue host's own sitemap is read through ``keep`` into ``ranked``.
        """
        degree = str(profile.context.level)
        fields = _public_requested_fields(profile, trace)
        # Catalogues first, deepest lead first; the homepage is the last resort
        # rather than a queue entry. Putting it in the queue let HKU's two
        # Chinese copies of the same catalogue consume the budget before the
        # walk reached the programme list.
        queue = list(selected[PageCategory.PROGRAM_CATALOG][:2])
        walked: set[str] = set()
        scores: dict[str, int] = {}
        homepage_tried = False
        # R4: languages of the institution's country ('' -> none, rule inert);
        # hops from the homepage of each page reached from it; the pages queued
        # on their label alone; whether the one catalogue host was read.
        languages = country_languages(trace.country) if LOCAL_CATALOGUE_ENTRY else ()
        hops: dict[str, int] = {}
        section_pages: set[str] = set()
        catalogue_host_tried = False
        # NS-1: the homepage's links ranked by the link score, read once the
        # queue today's rules build is empty; the pages read that way, which
        # do not count against MAX_FALLBACK_PAGES (they have their own cap).
        hop_ranked: list[tuple[str, int]] = []
        hop_pages: set[str] = set()

        while len(walked - hop_pages) < MAX_FALLBACK_PAGES:
            if selected[PageCategory.PROGRAM_PAGE]:
                break
            if self._spent() or self._search_due():
                break
            if not queue:
                if not homepage_tried:
                    homepage_tried = True
                    queue.append(entry["homepage"])
                    hops[entry["homepage"]] = 0
                elif hop_ranked:
                    for url, score in hop_ranked:
                        if len(hop_pages) >= HOMEPAGE_HOP_READ_CAP:
                            break
                        if url in walked or url in queue:
                            continue
                        hop_pages.add(url)
                        section_pages.add(url)
                        hops[url] = 1
                        queue.append(url)
                        trace.homepage_hop_reads.append((url, score))
                    hop_ranked = []
                    if not queue:
                        break
                else:
                    break
            start = queue.pop(0)
            if start in walked:
                continue
            walked.add(start)
            result = await self.fetcher.get(start)
            trace.note_entry_read(result.ok, homepage=start == entry["homepage"])
            if not result.ok:
                trace.errors.append(
                    f"navigation fallback: {start} unreachable ({result.outcome.value})"
                )
                continue
            if not same_source_site(start, result.final_url or start):
                trace.reject(start, "navigation page redirected off the institution's site")
                continue
            if start in section_pages and not self._section_page_kept(
                start, result, selected, scores, trace
            ):
                continue
            from_catalogue = (
                start in selected[PageCategory.PROGRAM_CATALOG] or start in section_pages
            )
            depth = hops.get(start)
            # R4: section links are taken from the homepage and from pages
            # reached from it, so a lead lands at most LOCAL_SECTION_MAX_HOPS away.
            local = bool(languages) and depth is not None and depth < LOCAL_SECTION_MAX_HOPS
            section_leads: list[tuple[int, int, str, str]] = []
            host_leads: list[tuple[int, int, str, str]] = []
            links = _harvest_links(
                result.text, result.final_url or start, domain, trace.extra_domains
            )
            if (
                _intent_module.LOCAL_QUERY_FROM_PAGE_EVIDENCE
                and _intent_module.LOCAL_LANGUAGE_QUERIES
                and not trace.local_query_phrase
            ):
                # LQ-2: the site's own name for the programme, for the one
                # local-language query search sends after this walk.
                country = trace.country or str(entry.get("country") or "")
                own = local_phrase_from_links(
                    result.text,
                    links,
                    languages=[code for code in country_languages(country) if code != "en"],
                    fields=fields,
                    degree=degree,
                    from_catalogue=from_catalogue,
                )
                if own is not None:
                    trace.local_query_phrase = {
                        "phrase": own[0],
                        "source": "link",
                        "link": own[1],
                        "page": start,
                    }
            if HOMEPAGE_HOP_READS and start == entry["homepage"]:
                hop_ranked = self._homepage_hop_leads(
                    links, entry, domain, trace, degree, fields, {start, result.final_url or start}
                )
            for url, label in links:
                category, score = categorise_url(url)
                section = (
                    self._section_label(label, languages, degree)
                    if local and category in (None, PageCategory.PROGRAM_CATALOG)
                    else None
                )
                if local and keep is not None and not catalogue_host_tried:
                    host_lead = self._catalogue_host_lead(
                        url, label, section, entry["homepage"], domain, degree
                    )
                    if host_lead is not None:
                        host_leads.append((host_lead, len(host_leads), url, label))
                if section is not None and category == PageCategory.PROGRAM_CATALOG:
                    # Its URL already makes it a catalogue lead (below); the
                    # label says it is the section link, and how far it is.
                    if (url, label[:80]) not in trace.kept_by_link_text:
                        trace.kept_by_link_text.append((url, label[:80]))
                    hops.setdefault(canonical_url(url), (depth or 0) + 1)
                if category is None:
                    if (
                        section is not None
                        and not (from_catalogue and matches_field_text(label, fields))
                        and not _url_excluded(urlparse(url).path or "")
                        and not names_other_degree_level(url, degree)
                    ):
                        # R4: a section link, whatever its URL says; it is read
                        # (and classified) after the leads the URL rules queue.
                        section_leads.append((section.tier, len(section_leads), url, label))
                        continue
                    # On a catalogue page, a link whose own text names the
                    # applicant's subject is a programme lead even when the URL
                    # says nothing. Still only a lead: the page is fetched and
                    # classified like any other, and a catalogue or a news item
                    # is rejected there.
                    if not (from_catalogue and matches_field_text(label, fields)):
                        continue
                    if _url_excluded(urlparse(url).path or ""):
                        continue
                    category, score = PageCategory.PROGRAM_PAGE, 4
                    trace.kept_by_link_text.append((url, label[:80]))
                if score <= 0:
                    continue
                if category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
                    if names_other_degree_level(url, degree):
                        continue
                    field_score = matches_field(url, fields)
                    score += field_score + matches_degree(url, degree)
                    if score <= 0:
                        continue
                    if (
                        NAVIGATION_FIELD_LEADS
                        and category == PageCategory.PROGRAM_PAGE
                        and fields
                        and field_score == 0
                        and not matches_field_text(label, fields)
                        and not looks_like_catalogue(url)
                    ):
                        trace.reject(url, "navigation lead names none of the applicant's subjects")
                        continue
                elif SERVICE_PAGE_PRIORITY and category in SERVICE_CATEGORIES:
                    if names_other_degree_level(url, degree) or label_names_other_level(
                        label, degree
                    ):
                        trace.reject(
                            url, f"{category} page names a degree level other than {degree}"
                        )
                        continue
                    score += matches_degree(url, degree)
                canonical = canonical_url(url)
                if (
                    looks_like_catalogue(canonical)
                    and canonical not in walked
                    and canonical not in queue
                    and canonical != canonical_url(start)
                ):
                    # "Degree programmes" often lists "Bachelor programmes"
                    # rather than the programmes themselves. Follow one more
                    # hop rather than stopping at the intermediate page, and go
                    # depth-first: a page below the current one is a more
                    # specific lead than another page beside it.
                    if canonical.startswith(canonical_url(start)):
                        queue.insert(0, canonical)
                    else:
                        queue.append(canonical)
                    if depth is not None and LOCAL_CATALOGUE_ENTRY:
                        hops.setdefault(canonical, depth + 1)
                if canonical in selected[category]:
                    continue
                if len(selected[category]) < MAX_PAGES_PER_CATEGORY:
                    selected[category].append(canonical)
                    scores[canonical] = score
                    continue
                # Keep the strongest leads, not the first ones. Vienna's
                # bachelor list names "Bachelor Programmes by Topic", African
                # Studies and Egyptology before Computer Science, and the
                # three slots were gone by the time the applicant's subject
                # came up. Only leads this walk scored can be displaced: a
                # seed or a sitemap pick stays.
                ours = [u for u in selected[category] if u in scores]
                if not ours:
                    continue
                weakest = min(ours, key=lambda u: scores[u])
                if score > scores[weakest]:
                    selected[category][selected[category].index(weakest)] = canonical
                    del scores[weakest]
                    scores[canonical] = score
            taken = 0
            for _tier, _order, url, label in sorted(section_leads):
                # R4: behind every lead the URL rules queued, so the walk
                # today's rules make comes first and the section links use
                # only the pages it leaves.
                if taken >= LOCAL_SECTION_LINKS_PER_PAGE:
                    break
                if url in walked or url in queue or url == canonical_url(entry["homepage"]):
                    continue
                taken += 1
                section_pages.add(url)
                hops[url] = (depth or 0) + 1
                queue.append(url)
                trace.kept_by_link_text.append((url, label[:80]))
            if host_leads and keep is not None and ranked is not None:
                catalogue_host_tried = True
                _rank, _order, url, label = min(host_leads)
                await self._read_catalogue_host(
                    url, label, domain, selected, ranked, keep, trace, degree, fields
                )

    @staticmethod
    def _section_label(label: str, languages: Sequence[str], degree: str) -> SectionLabel | None:
        """R4: the section or catalogue word a link label is, if any."""
        from app.adapters.search.navigation import study_section_label

        return study_section_label(label, languages, degree)

    @staticmethod
    def _homepage_hop_leads(
        links: Sequence[tuple[str, str]],
        entry: dict,
        domain: str,
        trace: DiscoveryTrace,
        degree: str,
        fields: Sequence[str],
        homepage: set[str],
    ) -> list[tuple[str, int]]:
        """NS-1: the homepage's links by the product's own link score, best first.

        The score is ``navigation._score`` (best over the public requested
        fields), + 3 when the label is a ``study_section_label`` in a language
        of the institution's country, + 2 when it contains a section or
        admissions word. A link counts only on a host of the institution's own
        registrable domain (not a DI-1 admissions domain), outside the excluded
        paths, naming no other degree level in its URL or label, and with a
        score above 0. Ties are broken by URL. No applicant attribute is read:
        the intent holds the institution, the requested level and the public
        fields only.
        """
        from app.adapters.search.intent import DiscoveryIntent
        from app.adapters.search.navigation import (
            _ADMISSION_WORDS,
            _SECTION_WORDS,
            NavigationLink,
            _score,
            study_section_label,
        )

        intents: list[DiscoveryIntent] = []
        for field_name in fields:
            try:
                intents.append(
                    DiscoveryIntent(
                        institution=registrable_domain(domain) or domain,
                        domain=registrable_domain(domain) or domain,
                        degree=DegreeLevel(degree),
                        field=field_name,
                    )
                )
            except ValueError:
                continue
        languages = country_languages(trace.country)
        words = tuple(dict.fromkeys((*_SECTION_WORDS, *_ADMISSION_WORDS)))
        skip = {canonical_url(url) for url in homepage}
        skip.add(canonical_url(entry["homepage"]))
        ranked: list[tuple[int, str]] = []
        for url, label in links:
            if url in skip or not on_institution_site(url, domain):
                continue
            if _url_excluded(urlparse(url).path or ""):
                continue
            if names_other_degree_level(url, degree) or label_names_other_level(label, degree):
                continue
            link = NavigationLink(url=url, text=label, parent_url="")
            score = max((_score(link, intent)[0] for intent in intents), default=0)
            if study_section_label(label, languages, degree) is not None:
                score += 3
            text = label.casefold()
            if any(word in text for word in words):
                score += 2
            if score > 0:
                ranked.append((score, url))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        return [(url, score) for score, url in ranked]

    @staticmethod
    def _catalogue_host_lead(
        url: str,
        label: str,
        section: SectionLabel | None,
        homepage: str,
        domain: str,
        degree: str,
    ) -> int | None:
        """R4: how strongly a link names a catalogue host; None when it does not.

        The host must differ from the homepage's, sit on the institution's own
        registrable domain (another domain is DI-1's case), and neither its name
        nor the link may name continuing education or only another level
        (``phd.``, ``efteruddannelse.``, "Graduate Programs"). A catalogue word
        in the label ranks first, a section word next, a local listing path
        (``/carreras``, ``/opleidingen/n``) last; an English path alone
        (``teach.….edu.tw/course``) is not enough.
        """
        from app.adapters.search.navigation import label_fits_degree

        host = _WWW_PREFIX.sub("", (urlparse(url).hostname or "").lower())
        home = _WWW_PREFIX.sub("", (urlparse(homepage).hostname or "").lower())
        if not host or host == home or not same_institution(url, domain):
            return None
        path = urlparse(url).path or ""
        if _url_excluded(path) or names_other_degree_level(url, degree):
            return None
        if not label_fits_degree(host.split(".")[0].replace("-", " "), degree):
            return None
        if not label_fits_degree(label, degree):
            return None
        if section is not None:
            return section.tier
        return 2 if _LOCAL_CATALOGUE_PATH.search(path) else None

    @staticmethod
    def _section_page_kept(
        start: str,
        result: FetchResult,
        selected: dict[str, list[str]],
        scores: dict[str, int],
        trace: DiscoveryTrace,
    ) -> bool:
        """R4: read a page reached by its label alone as a lead, not as a catalogue.

        A page that reads as news, admissions, fees, scholarships or the like
        lists no programmes: it is dropped and its links are not followed. Any
        other page becomes a catalogue lead (the walker's own catalogue test).
        """
        from app.adapters.discovery.catalog_walker import _NOT_CATALOGUE_TYPES

        page = classify_page(url=result.final_url or start, html=result.text)
        if page.page_type in _NOT_CATALOGUE_TYPES:
            trace.reject(
                start, f"not_program_catalog: the section link reads as {page.page_type.value}"
            )
            return False
        catalogues = selected[PageCategory.PROGRAM_CATALOG]
        if start in catalogues:
            return True
        if len(catalogues) < MAX_PAGES_PER_CATEGORY:
            catalogues.append(start)
            scores[start] = LOCAL_SECTION_LINK_SCORE
            return True
        ours = [u for u in catalogues if u in scores]
        if ours:
            weakest = min(ours, key=lambda u: scores[u])
            if scores[weakest] < LOCAL_SECTION_LINK_SCORE:
                catalogues[catalogues.index(weakest)] = start
                del scores[weakest]
                scores[start] = LOCAL_SECTION_LINK_SCORE
        return True

    async def _read_catalogue_host(
        self,
        url: str,
        label: str,
        domain: str,
        selected: dict[str, list[str]],
        ranked: dict[str, list[tuple[int, str]]],
        keep: Callable[[str], bool],
        trace: DiscoveryTrace,
        degree: str,
        fields: list[str],
    ) -> None:
        """R4: read one catalogue host's own sitemap into the programme leads.

        Its reads are sitemap reads, inside the SB-1 sitemap allowance; the
        URLs go through the sitemap stage's ``keep`` into ``ranked``, and the
        best programme leads fill the empty slots as the sitemap stage fills
        them, so the confirm stage reads them like any sitemap lead.
        """
        budget = self._budget
        trace.catalogue_host.update(
            {"host": (urlparse(url).hostname or "").lower(), "link": url, "label": label[:80]}
        )

        def stop() -> bool:
            return (
                self._spent()
                or self._search_due()
                or (budget is not None and budget.sitemap_spent())
            )

        if stop():
            trace.catalogue_host["skipped"] = "discovery budget"
            return
        previous = self._enter("sitemap")
        try:
            pages = await self.sitemaps.collect_catalogue_host(
                url, domain, trace, keep, degree=degree, stop=stop
            )
        except Exception as exc:  # a malformed sitemap must not end the run
            trace.errors.append(f"R4 catalogue host sitemap failed: {type(exc).__name__}: {exc}")
            pages = []
        finally:
            if previous:
                self._enter(previous)
        if not pages:
            return
        scored = sorted(
            ranked[PageCategory.PROGRAM_PAGE], key=lambda pair: (-pair[0], len(pair[1]))
        )
        for _score, lead in _prefer_exact_field(scored, fields):
            if len(selected[PageCategory.PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY:
                break
            if lead not in selected[PageCategory.PROGRAM_PAGE]:
                selected[PageCategory.PROGRAM_PAGE].append(lead)


def _first(urls: list[str]) -> str | None:
    return urls[0] if urls else None


def _program_name_from_url(url: str, fields: list[str], degree: object) -> str:
    """A readable placeholder name from the URL's last segment.

    Deliberately not treated as the programme's real name: the programme page
    itself supplies that, and the classifier checks it against what was asked
    for. This is only what discovery calls the lead until then.
    """
    slug = (urlparse(url).path or "").rstrip("/").rsplit("/", 1)[-1]
    words = [w for w in re.split(r"[-_]+", slug) if w and not w.isdigit()]
    if not words:
        return f"{fields[0] if fields else 'programme'} ({degree})"
    # Any page extension, not only ".html": KIT's ``bachelor-informatics.php``
    # was named "Bachelor Informatics.Php", and "php" then counted as a
    # requested subject word in verify (loss stages v3 2026-10-18 §2).
    return strip_url_extension(" ".join(words).replace(".html", "")).strip().title()


#: A page file extension at the end of a URL's last segment.
_URL_PAGE_EXTENSION = re.compile(r"\.(?:php|aspx?|jsp|cfm|html?)$", re.IGNORECASE)


def strip_url_extension(slug: str) -> str:
    """``slug`` without a trailing page extension (.php, .aspx, .jsp, .cfm, .htm, .html)."""
    return _URL_PAGE_EXTENSION.sub("", slug)


def _harvest_links(
    html: str, base: str, domain: str, extra_domains: Sequence[str] = ()
) -> list[tuple[str, str]]:
    soup = parse_html(html)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True)[:MAX_LINKS_SCANNED]:
        link = page_link(base, anchor["href"])
        if link is None:
            continue
        url = link.split("#")[0]
        if urlparse(url).scheme not in ("http", "https"):
            continue
        if not on_institution_site(url, domain, extra_domains):
            continue
        canonical = canonical_url(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))[:160]
        out.append((canonical, label))
    return out


# --- LQ-2: the local query from the site's own words -------------------------

# An alias head in R1's unspaced scripts (``_UNSPACED_SCRIPT``) is looked for
# anywhere in a label rather than at a word's start.
#: LQ-2: every flag a localized related form carries. A label naming one is a
#: neighbour's programme whatever flag is in force, so it is never a phrase.
_RELATED_FORM_FLAGS = frozenset(
    {"LOCALIZED_IDENTITY", "LEXICON_V2", "LOCALIZED_PAGE_IDENTITY", "LEXICON_LANGUAGE_COVERAGE"}
)


def alias_head(alias: str) -> str:
    """LQ-2: the stem of an alias's longest word, as a link text is searched for it.

    The longest word carries the subject («computación», not «ciencias»), and
    its stem without the last two letters reaches the word's other forms
    («computacionales»), never fewer than five letters. A word of five letters
    or fewer, or an unspaced script's whole alias up to that length, stays
    whole. An alias in an unspaced script (zh, ja, ko, th) is its own head,
    whole: those scripts do not inflect a word's end.
    """
    folded = unicodedata.normalize("NFC", alias).casefold()
    if _UNSPACED_SCRIPT.search(folded):
        return re.sub(r"\s+", "", folded)
    words = re.findall(r"[^\W\d_]+", folded)
    if not words:
        return ""
    head = max(words, key=len)
    return head if len(head) <= 5 else head[: max(5, len(head) - 2)]


#: LQ-2: words a head's stem reaches that name something else in every
#: language the stem is shared by: *informati-* is also the start of
#: "Information(en)", «información», «informação» — a page's notices, not the
#: field (found by the offline table on a German study page, 2026-10-21).
_HEAD_FALSE_FRIENDS = ("informatio",)


def _names_alias_head(label: str, heads: Sequence[str]) -> bool:
    folded = unicodedata.normalize("NFC", label).casefold()
    for head in heads:
        if not head:
            continue
        if _UNSPACED_SCRIPT.search(head):
            if head in folded:
                return True
            continue
        for found in re.finditer(rf"(?<![^\W\d_]){re.escape(head)}[^\W\d_]*", folded):
            if not found.group(0).startswith(_HEAD_FALSE_FRIENDS):
                return True
    return False


def local_phrase_from_links(
    html: str,
    links: Sequence[tuple[str, str]],
    *,
    languages: Sequence[str],
    fields: Sequence[str],
    degree: str,
    from_catalogue: bool,
) -> tuple[str, str] | None:
    """LQ-2: the phrase one read page offers the local-language query, and its link.

    The page must declare, in ``<html lang>``, a language of the institution's
    country (``languages``, never the applicant's). A link qualifies when its
    target is a programme page or listing — its URL categorises as one, it sits
    on a catalogue page, or its label is R4's study-section word — and its
    text names the head of a localized alias of the field in the page's
    language (never a head false friend, :data:`_HEAD_FALSE_FRIENDS`).
    Refused: a label naming another level (text or URL), a related programme
    (a localized related form, or R2's related head), a unit (CH-1's unit
    nouns with no degree word), and anything :func:`intent.local_query_phrase`
    refuses. A label R2 reads as the field itself comes first, then one whose
    URL names the requested level; otherwise the page's order decides.
    """
    from app.adapters.search.navigation import study_section_label

    language = _page_classifier.page_language(html)
    if not language or language not in languages or not fields:
        return None
    flags = _page_classifier.localized_alias_flags()
    heads: list[str] = []
    related: list[str] = []
    for field_name in fields:
        heads += [alias_head(a) for a in localized_aliases_in(field_name, language, flags=flags)]
        related += [
            term.casefold()
            for term in localized_related_terms(field_name, flags=_RELATED_FORM_FLAGS)
        ]
    heads = [head for head in dict.fromkeys(heads) if head]
    if not heads:
        return None
    units = _unit_word_pattern(tuple(sorted(_UNIT_WORDS.items())))
    best: tuple[int, int, int, str, str] | None = None
    for order, (url, label) in enumerate(links):
        if not label or not _names_alias_head(label, heads):
            continue
        folded = unicodedata.normalize("NFC", label).casefold()
        if any(term in folded for term in related):
            continue
        levels = _page_classifier.degree_levels_named(label)
        if units is not None and units.search(_fold(label)) and not levels:
            # CH-1's unit nouns: «Tietotekniikan laitos» is the department.
            continue
        if label_names_other_level(label, degree) or names_other_degree_level(url, degree):
            continue
        if levels - {degree}:
            # CH-1's table, every language: «Magíster en …» is another level.
            continue
        if _url_excluded(urlparse(url).path or ""):
            continue
        category, _score = categorise_url(url)
        if not (
            category in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG)
            or from_catalogue
            or study_section_label(label, [language], degree) is not None
        ):
            continue
        verdict = subject_head_verdict(label, list(fields))
        if verdict == "related":
            continue
        phrase = _intent_module.local_query_phrase(label)
        if phrase is None:
            continue
        # The field's own title first, then a URL naming the requested level
        # ("bachelor-informatik" before "lehramt-informatik"), then page order.
        rank = (0 if verdict == "field" else 1, -matches_degree(url, degree), order, phrase, url)
        if best is None or rank < best:
            best = rank
    return (best[3], best[4]) if best is not None else None


def _entry_native_name(entry: dict) -> str:
    """LQ-2: the seed row's first native name a query may carry, or ``""``."""
    names = entry.get("native_name") or []
    for name in [names] if isinstance(names, str) else names:
        phrase = _intent_module.local_query_phrase(name) if isinstance(name, str) else None
        if phrase is not None:
            return phrase
    return ""


def _local_phrase_fields(entry: dict, trace: DiscoveryTrace) -> tuple[str, str]:
    """LQ-2: the intent's ``local_phrase`` and ``native_name``; empty while the rule is off."""
    if not (
        _intent_module.LOCAL_QUERY_FROM_PAGE_EVIDENCE and _intent_module.LOCAL_LANGUAGE_QUERIES
    ):
        return "", ""
    found = trace.local_query_phrase
    link = found.get("phrase", "") if found.get("source") == "link" else ""
    return link, _entry_native_name(entry)


def _note_local_phrase_plan(intent: Any, trace: DiscoveryTrace) -> None:
    """LQ-2: record which words the local-language query was planned with."""
    terms = _intent_module.local_language_terms(intent)
    if terms is None or terms.phrase is None:
        if trace.local_query_phrase:
            trace.local_query_phrase["planned"] = "no"
        return
    if terms.phrase_source == "native_name":
        trace.local_query_phrase = {"phrase": terms.phrase, "source": "native_name"}
    trace.local_query_phrase["planned"] = "yes"


def registry_campuses(domain: str) -> dict[str, list[str]]:
    """Campus name to its hosts, for the institution on this registrable domain.

    Verified registry data (``campuses``); empty when the registry records none.
    """
    try:
        entries = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - a broken registry is a deploy problem
        return {}
    target = registrable_domain(domain)
    for entry in entries:
        if not entry.get("campuses"):
            continue
        if registrable_domain(urlparse(entry.get("homepage") or "").hostname or "") == target:
            return {c["name"]: list(c["hosts"]) for c in entry["campuses"]}
    return {}
