"""The single door to the outside world.

Every network read in the product goes through ``Fetcher``. That is what makes
the politeness guarantees checkable in one place: robots.txt is consulted
before the first request to a host, per-host concurrency is capped, requests
are spaced, responses are cached on disk, and failures back off rather than
retry tightly.

The fetcher also enforces a privacy rule that is easy to violate by accident:
no applicant data may appear in an outbound URL. ``assert_no_pii`` is called on
every request and raises rather than leaking — and the same guard runs on
every redirect hop the fetcher discovers along the way, not just the URL the
caller asked for.

A 200 also records its HTTP validators (ETag, Last-Modified) and a content
hash of the extracted text. The hash is only ever compared against hashes
computed by the same formula, so it is self-consistent by construction: if
text extraction drifts, the worst case is one redundant re-extraction — never
a false "unchanged".
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import ssl
import time
import unicodedata
import urllib.parse
import urllib.robotparser
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.adapters.network_policy import (
    MAX_REDIRECTS,
    BlockedRequest,
    ResolvedTarget,
    check_url,
)
from app.adapters.url_canonical import invalid_url_reason
from app.domain.enums import FetchOutcome
from app.domain.site_identity import hosts_share_site, registrable_domain

log = logging.getLogger("unimatch.fetch")

USER_AGENT = (
    "ASHYQApplyBot/0.2 (+https://github.com/wpalish/ashyq-apply; "
    "university admissions research for a single applicant; contact: set FETCH_CONTACT)"
)
DEFAULT_TIMEOUT = 20.0
#: The longest robots.txt Crawl-delay this crawler will honour by waiting. A
#: longer one is honoured by not reading the host at all: waiting it out made
#: a single university's run hang until its wall clock ended.
MAX_CRAWL_DELAY_SECONDS = 10.0
DEFAULT_DELAY_SECONDS = 1.5
MAX_PER_HOST_CONCURRENCY = 2
MAX_ATTEMPTS = 3
#: httpx's timeout bounds each connect and each read, not the whole response:
#: a server that trickles bytes never trips it. Aalto's robots.txt held a run
#: for its entire 90 s this way. These bound the whole exchange.
ROBOTS_DEADLINE_SECONDS = 15.0
ATTEMPT_DEADLINE_FACTOR = 1.0
#: Name resolution is a blocking libc call. Run on the event loop it froze
#: every coroutine, deadlines included, for as long as the resolver took.
DNS_DEADLINE_SECONDS = 10.0
#: How many of a host's validated addresses one attempt may try, and how long
#: each may take to accept a connection when there is another to fall back on.
MAX_ADDRESSES_TRIED = 3
PER_ADDRESS_CONNECT_SECONDS = 5.0
#: Plan rule HS-1. A URL the pipeline guessed rather than found (a
#: conventional sitemap location probed because robots.txt named none) says
#: nothing about its host when it hangs: dev3, www.ub.edu let a guessed
#: /sitemap/sitemap.xml run 21 s, the host was blacked out for the run, yet it
#: answers its other pages in 0.5 s. With this on, a guessed URL's stall skips
#: only that URL, and a guess may spend at most GUESSED_URL_TIMEOUT_SECONDS.
#: A stall on a discovered URL still stalls the host. Off by default.
GUESSED_URL_STALL_EXEMPT = False
GUESSED_URL_TIMEOUT_SECONDS = 6.0
#: Plan rule RS-1 (read budget analysis 2026-10-18, §4 step 1.1), off until a
#: paired run passes. Imperial's course and fee URLs under ``/2027/`` answer 301
#: and take two or three hops, and a page linked again under any URL of the
#: chain paid the hops again: 30-49 of its 66-74 wire requests were redirect
#: overhead. On: every URL of a redirect chain that ended in a readable page is
#: remembered, for this fetcher's life (one run), as leading to that page; a
#: later read of one of them starts at the final URL, and the page is also
#: cached under its final URL, so a link straight to it is a cache hit. Every
#: hop still goes through robots, pacing, the network policy and the PII guard.
#: The benchmark harness flips it per capture (``--redirect-memory``).
REDIRECT_MEMORY = True
#: Plan rule RS-2 (same analysis, §4 step 1.2), off until a paired run passes.
#: Chula's tuition page was read as ``http://`` and as ``https://``, Imperial's
#: entry requirements with and without the trailing slash: two cold reads of
#: one page. On: the cache key of a URL ignores its trailing slash and treats
#: ``http`` as ``https`` on the same host, before the cache is asked. The URL
#: requested on a miss is the caller's own. The benchmark harness flips it per
#: capture (``--url-variant-dedupe``).
URL_VARIANT_DEDUPE = True


def variant_key(url: str) -> str:
    """RS-2: one cache key for a URL's trailing-slash and http/https variants.

    The host, port, path case and query are kept; only ``http`` becomes
    ``https`` and a non-root path loses its trailing slashes. A URL that does
    not parse as http(s) is its own key.
    """
    try:
        parts = urlparse(url)
    except ValueError:
        return url
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return url
    path = parts.path.rstrip("/") or "/"
    rebuilt = parts._replace(scheme="https", path=path, fragment="")
    return rebuilt.geturl()


# --- RL-1: the per-institution read ledger ----------------------------------

#: Plan rule RL-1, the case read ledger (read budget analysis 2026-10-18 §4
#: step 2; not the route-leads rule ``ROUTE_LEADS``, which also went by RL-1).
#: Off until a paired run passes. DoD target 5 counts every HTTP request to a
#: university site (owner decision 2026-10-18): the scorecard's
#: ``http_fetches`` is one per ``_pinned_request`` — every redirect hop, retry,
#: address tried and robots.txt load — while every cap in code counted
#: ``Fetcher.get`` calls, so nothing could stop a case at 60. On: each
#: institution has a ledger, opened by ``charging`` around its discovery,
#: verify and funding work; every wire request is charged to it immediately
#: before ``_pinned_request`` builds it, and none is built past
#: ``CASE_READ_CAP``. A read is refused before it starts when fewer reads than
#: its kind's floor (``read_floor``) would remain: sitemap documents first,
#: then walker leads, the rest of discovery (which leaves
#: ``VERIFY_RESERVE_READS`` for the six core questions), scholarship award
#: pages, extra question pages; the confirmed programme page, the admissions
#: page and one page per still-unanswered core question (kind ``"core"``) are
#: refused only at the cap. Every refusal is recorded with its reason
#: (``CaseReadLedger.refusals``, in the discovery trace). Per institution,
#: because production shares one Fetcher across universities; a page two
#: institutions share is charged to the first, and cache hits are free. The
#: benchmark harness flips it per capture (``--case-read-ledger``).
CASE_READ_LEDGER = True
#: RL-1: wire requests one institution may make (DoD target 5).
CASE_READ_CAP = 60
#: RL-1: reads discovery leaves for the verify stage's six core questions.
VERIFY_RESERVE_READS = 16
#: RL-1: refusals kept per ledger, so a long run cannot bloat the trace.
MAX_LEDGER_REFUSALS = 50
#: RL-1: the kind a read is charged as when its caller named none, by phase.
PHASE_DEFAULT_KIND = {"discovery": "discovery", "verify": "question_extra", "funding": "award"}

_ACTIVE_LEDGER: ContextVar[CaseReadLedger | None] = ContextVar("case_read_ledger", default=None)
_READ_KIND: ContextVar[str | None] = ContextVar("case_read_kind", default=None)


def read_floor(kind: str, reserve: int) -> int:
    """RL-1: reads that must remain after a read of ``kind`` for it to start.

    The higher the floor, the sooner the kind is refused when reads run short.
    """
    floors = {
        "sitemap": reserve + 8,
        "walker": reserve + 4,
        "discovery": reserve,
        "award": 4,
        "question_extra": 2,
        "question_open": 2,
        "core": 0,
    }
    return floors.get(kind, reserve)


class CaseReadSpent(Exception):
    """RL-1: the institution's ledger holds no read for this wire request."""


@dataclass
class CaseReadLedger:
    """RL-1: one institution's wire requests, by phase and kind, and its refusals."""

    institution: str
    cap: int = field(default_factory=lambda: CASE_READ_CAP)
    reserve: int = field(default_factory=lambda: VERIFY_RESERVE_READS)
    phase: str = "discovery"
    spent: int = 0
    by_phase: dict[str, int] = field(default_factory=dict)
    by_kind: dict[str, int] = field(default_factory=dict)
    refusals: list[dict[str, str]] = field(default_factory=list)
    refused: int = 0

    @property
    def remaining(self) -> int:
        return max(self.cap - self.spent, 0)

    def kind(self) -> str:
        return _READ_KIND.get() or PHASE_DEFAULT_KIND.get(self.phase, "discovery")

    def admit(self, needed: int, kind: str) -> str:
        """Why a read needing ``needed`` requests is refused now, or ""."""
        floor = read_floor(kind, self.reserve)
        if self.remaining - needed >= floor:
            return ""
        if floor:
            return (
                f"{self.remaining} of {self.cap} reads left; a {kind} read needs "
                f"{needed} and must leave {floor}"
            )
        return f"{self.remaining} of {self.cap} reads left; this read needs {needed}"

    def charge(self, url: str) -> None:
        """Spend one wire request, or raise ``CaseReadSpent`` at the cap."""
        if self.spent >= self.cap:
            raise CaseReadSpent(f"case read budget spent: {self.cap} requests to {url[:120]}")
        kind = self.kind()
        self.spent += 1
        self.by_phase[self.phase] = self.by_phase.get(self.phase, 0) + 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1

    def refuse(self, url: str, kind: str, reason: str) -> None:
        self.refused += 1
        if len(self.refusals) < MAX_LEDGER_REFUSALS:
            self.refusals.append(
                {"url": url[:300], "phase": self.phase, "kind": kind, "reason": reason}
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "institution": self.institution,
            "cap": self.cap,
            "verify_reserve": self.reserve,
            "spent": self.spent,
            "remaining": self.remaining,
            "by_phase": dict(self.by_phase),
            "by_kind": dict(self.by_kind),
            "refused": self.refused,
            "refusals": list(self.refusals),
        }


def _charge_wire(url: str) -> None:
    """RL-1: charge the active ledger one wire request, before it is built."""
    ledger = _ACTIVE_LEDGER.get()
    if ledger is not None:
        ledger.charge(url)


@contextmanager
def reading_as(kind: str) -> Iterator[None]:
    """RL-1: the reads inside are charged, and refused, as ``kind``."""
    token = _READ_KIND.set(kind)
    try:
        yield
    finally:
        _READ_KIND.reset(token)


def charging(fetcher: object, institution: str, phase: str) -> AbstractContextManager[Any]:
    """RL-1: charge the reads inside to ``institution``'s ledger, as ``phase``.

    A no-op while the rule is off, without an institution, or for a fetcher
    that is not a ``Fetcher`` (a test's stub, a stage's wrapper). TB-1: the
    same scope runs ``institution``'s case clock; with the ledger off and
    TB-1 on it yields no ledger but still times the reads inside.
    """
    if not institution or not isinstance(fetcher, Fetcher):
        return nullcontext()
    if CASE_READ_LEDGER:
        return fetcher.charging(institution, phase)
    if CASE_TIME_BUDGET:
        return fetcher.timing(institution, phase)
    return nullcontext()


# --- TB-1: the per-case time budget -------------------------------------------

#: Plan rule TB-1, off until a paired run passes. DoD target 5 allows 120 s
#: per university, and a case the harness's wall clock ends (115 s) counts as
#: over budget (owner decision 2026-10-18). After RL-1 the only cases still
#: over were clock kills with few requests: UBC (25-31 requests; you.ubc.ca
#: answers in 5-17 s, no Crawl-delay), UNSW (22-26; ``Crawl-delay: 10``, so
#: every www.unsw.edu.au read costs ~10 s of waiting), KU Leuven (hosts that
#: fail after 21 s). Only discovery watched a clock (SB-1, 55 s), checked at
#: read start, so its last read ran past it, and verify, costs and funding
#: read until the kill, in the middle of the scholarship stage, which files
#: nothing until it returns. On: each institution has a case clock, opened by
#: ``charging`` with its read ledger and running while the institution is
#: the fetcher's latest (so production's interleaved universities each get
#: their own seconds). Before a read starts, the fetcher predicts its cost —
#: the host's Crawl-delay or pacing wait, which is never shortened, plus the
#: host's mean observed read time — and refuses it when it would leave less
#: than its kind's floor (``time_floor``): sitemap documents first, then
#: walker leads, the rest of discovery (which leaves VERIFY_RESERVE_SECONDS),
#: extra question pages (which leave CORE_RESERVE_SECONDS for the cost and
#: scholarship pages), scholarship award pages. Core reads (the confirmed
#: programme page, the admissions page, the first page per unanswered core
#: question) start whenever time remains after their crawl-delay wait. No
#: read, hop, retry or wait runs past CASE_TIME_SECONDS: an exchange still
#: running then is cut there, and the stage files what it has. A slow host
#: therefore gets fewer reads, not shorter waits. Topic and award queries
#: are not sent with less than QUERY_MIN_SECONDS left. Refusals and seconds
#: per phase are in the discovery trace (``case_time``). The benchmark
#: harness flips it per capture (``--case-time-budget``).
CASE_TIME_BUDGET = (
    True  # on: runs 39127473231 / 39127474664 / 39128704750 / 39128706390 (0 over budget, 0 losses)
)
#: TB-1: seconds of one institution's work by which every read has ended;
#: the harness ends a case at 115 s, which leaves the last page's parsing,
#: the assessment and the report five seconds.
CASE_TIME_SECONDS = 110.0
#: TB-1: seconds discovery leaves for verify, costs and funding (SB-1's own
#: 55 s deadline stops it first; this bounds a read started just before it).
VERIFY_RESERVE_SECONDS = 40.0
#: TB-1: seconds an extra question page leaves for the core cost and
#: scholarship reads after it.
CORE_RESERVE_SECONDS = 20.0
#: TB-1 / FE-2b (``extraction.FEE_READERS_V2``): a further page for a core
#: question still unanswered (kind ``question_open``) leaves only what this
#: many reads of its host take - the cost page and the award index, the core
#: reads after it - not the whole CORE_RESERVE_SECONDS. Paired run
#: 39146090779: UBC's "Dates & deadlines" page was refused in both flag-on
#: repetitions with 25.2 s and 26.7 s left (a 7 s read that had to leave 20 s),
#: so the reserve kept for the fee read cost the unanswered deadline.
OPEN_QUESTION_CORE_READS = 2
#: TB-1: what a read of a host with no observed read is expected to take
#: (robots.txt still to load costs as much again).
DEFAULT_READ_SECONDS = 2.0
#: TB-1: the least time a core read needs left after its crawl-delay wait.
MIN_CORE_READ_SECONDS = 1.0
#: TB-1: the least time left for which a topic or award query is sent.
QUERY_MIN_SECONDS = 5.0
#: TB-1: an exchange that timed out with this little time left was cut by
#: the case clock, not stalled by its host.
TIME_CUT_SLACK_SECONDS = 0.25
#: TB-1: refusals kept per clock, so a long run cannot bloat the trace.
MAX_TIME_REFUSALS = 50


def _clock() -> float:
    """TB-1's clock; a module attribute a test can replace. The fetcher's pacing
    uses it too, so a Crawl-delay is waited on the clock the budget reads."""
    return time.monotonic()


async def _sleep(seconds: float) -> None:
    """The fetcher's pacing and backoff sleep; replaced with ``_clock`` in tests."""
    await asyncio.sleep(seconds)


_ACTIVE_TIMER: ContextVar[CaseTimeBudget | None] = ContextVar("case_time_budget", default=None)


def time_floor(kind: str, verify_reserve: float, core_reserve: float) -> float:
    """TB-1: seconds that must remain after a read of ``kind`` is expected to end.

    The higher the floor, the sooner the kind is refused when time runs
    short. ``core`` has none: it is refused only when no time remains.
    """
    floors = {
        "sitemap": verify_reserve + 20.0,
        "walker": verify_reserve + 10.0,
        "discovery": verify_reserve,
        "question_extra": core_reserve,
        "question_open": core_reserve,
        "award": 0.0,
        "core": 0.0,
    }
    return floors.get(kind, verify_reserve)


@dataclass
class _ReadTiming:
    """TB-1: what one ``Fetcher.get`` spent waiting on pacing, and whether it read."""

    waited: float = 0.0
    network: bool = False


_READ_TIMING: ContextVar[_ReadTiming | None] = ContextVar("case_read_timing", default=None)
#: TB-1: how every refusal and cut the case clock makes begins.
_TB_PREFIX = "case time budget (TB-1): "


@dataclass
class CaseTimeBudget:
    """TB-1: one institution's case clock, its seconds by phase, and its refusals."""

    institution: str
    limit: float = field(default_factory=lambda: CASE_TIME_SECONDS)
    verify_reserve: float = field(default_factory=lambda: VERIFY_RESERVE_SECONDS)
    core_reserve: float = field(default_factory=lambda: CORE_RESERVE_SECONDS)
    phase: str = "discovery"
    #: Seconds run before the clock last paused.
    accrued: float = 0.0
    #: When the clock last started running; None while paused.
    since: float | None = None
    by_phase: dict[str, float] = field(default_factory=dict)
    refusals: list[dict[str, str]] = field(default_factory=list)
    refused: int = 0
    cut: int = 0
    #: Elapsed seconds at the first refusal: where the case started stopping.
    first_refusal_at: float | None = None
    _mark: float = 0.0

    def elapsed(self, now: float | None = None) -> float:
        if self.since is None:
            return self.accrued
        return self.accrued + ((_clock() if now is None else now) - self.since)

    def left(self) -> float:
        return max(self.limit - self.elapsed(), 0.0)

    def resume(self, now: float) -> None:
        if self.since is None:
            self.since = self._mark = now

    def pause(self, now: float) -> None:
        if self.since is not None:
            self._attribute(now)
            self.accrued += now - self.since
            self.since = None

    def enter(self, phase: str, now: float) -> None:
        """Charge the seconds so far to the current phase; ``phase`` runs next."""
        self._attribute(now)
        self.phase = phase

    def _attribute(self, now: float) -> None:
        if self.since is not None:
            self.by_phase[self.phase] = self.by_phase.get(self.phase, 0.0) + now - self._mark
            self._mark = now

    def admit(self, kind: str, wait: float, expected: float) -> str:
        """Why a read of ``kind`` is refused now, or "".

        ``wait`` is the host's pacing wait (Crawl-delay), ``expected`` the
        read's predicted seconds after it.
        """
        left = self.left()
        if kind == "core":
            if wait + MIN_CORE_READ_SECONDS <= left:
                return ""
            return (
                f"{left:.1f} of {self.limit:.0f} s left; a core read would wait "
                f"{wait:.1f} s for the host's crawl delay first"
            )
        floor = time_floor(kind, self.verify_reserve, self.core_reserve)
        if kind == "question_open":
            floor = min(floor, OPEN_QUESTION_CORE_READS * expected)
        if wait + expected + floor <= left:
            return ""
        return (
            f"{left:.1f} of {self.limit:.0f} s left; a {kind} read is expected to take "
            f"{wait + expected:.1f} s ({wait:.1f} s crawl-delay wait) and must leave {floor:.0f} s"
        )

    def refuse(self, url: str, kind: str, reason: str) -> None:
        self.refused += 1
        if self.first_refusal_at is None:
            self.first_refusal_at = round(self.elapsed(), 2)
        if len(self.refusals) < MAX_TIME_REFUSALS:
            self.refusals.append(
                {"url": url[:300], "phase": self.phase, "kind": kind, "reason": reason}
            )

    def as_dict(self) -> dict[str, Any]:
        now = _clock()
        by_phase = dict(self.by_phase)
        if self.since is not None:
            by_phase[self.phase] = by_phase.get(self.phase, 0.0) + now - self._mark
        return {
            "institution": self.institution,
            "limit_seconds": self.limit,
            "verify_reserve_seconds": self.verify_reserve,
            "core_reserve_seconds": self.core_reserve,
            "elapsed_seconds": round(self.elapsed(now), 2),
            "seconds_by_phase": {k: round(v, 2) for k, v in by_phase.items()},
            "first_refusal_at": self.first_refusal_at,
            "refused": self.refused,
            "cut": self.cut,
            "refusals": list(self.refusals),
        }


def case_seconds_left() -> float | None:
    """TB-1: seconds left on the active institution's case clock; None when untimed."""
    timer = _ACTIVE_TIMER.get() if CASE_TIME_BUDGET else None
    return None if timer is None else timer.left()


def case_timer(fetcher: object, institution: str) -> CaseTimeBudget | None:
    """TB-1: ``institution``'s case clock, if TB-1 is on and one was opened."""
    if not CASE_TIME_BUDGET or not institution or not isinstance(fetcher, Fetcher):
        return None
    return fetcher.timers.get(registrable_domain(institution) or institution)


async def _resolve_checked(url: str) -> ResolvedTarget:
    """``check_url`` off the event loop, bounded. Raises TimeoutError."""
    return await asyncio.wait_for(asyncio.to_thread(check_url, url), DNS_DEADLINE_SECONDS)


MAX_BYTES = 5_000_000
MAX_ROBOTS_BYTES = 512_000
#: Content types worth parsing. Anything else is refused before it is read, so
#: a link to a large binary cannot be pulled through the size limit byte by byte.
ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/pdf",
    "text/xml",
    "application/xml",
    "application/json",
)


def _pinned_request(
    client: httpx.AsyncClient,
    target: ResolvedTarget,
    *,
    timeout: float | httpx.Timeout | None = None,
    headers: dict[str, str] | None = None,
    address: str | None = None,
    pin: bool = True,
) -> httpx.Request:
    """Connect to the validated IP while preserving virtual-host TLS and HTTP.

    ``pin=False`` (a fetcher opted into an explicit HTTPS proxy, see
    ``Fetcher(trust_env_proxy=True)``) addresses the host by name: the proxy's
    CONNECT names the host and TLS is verified against that name. The target
    was still validated by the network policy before this request was built.
    """
    if not pin:
        return client.build_request("GET", target.url, headers=headers, timeout=timeout)
    pinned_url = httpx.URL(target.url).copy_with(host=address or target.pinned_address)
    host = f"[{target.host}]" if ":" in target.host else target.host
    default_port = 443 if target.scheme == "https" else 80
    if target.port != default_port:
        host = f"{host}:{target.port}"
    return client.build_request(
        "GET",
        pinned_url,
        headers={"Host": host, **(headers or {})},
        timeout=timeout,
        extensions={"sni_hostname": target.host},
    )


class PIILeakError(RuntimeError):
    """Raised when applicant data would be placed in an outbound request."""


#: Below this many characters of extractable text, a "successful" HTML fetch is
#: an empty shell worth escalating to a browser.
MIN_USEFUL_TEXT = 400


def same_source_site(requested_url: str, final_url: str) -> bool:
    """Whether a fetched body stayed on the requested registrable domain.

    A redirect to a different organisation cannot be cited under the URL that
    initiated it, even when both hosts pass the network/SSRF policy.
    """
    try:
        requested = urlparse(requested_url)
        final = urlparse(final_url)
    except ValueError:
        return False
    if requested.scheme not in ("http", "https") or final.scheme not in ("http", "https"):
        return requested_url == final_url and requested.scheme == "fixture"
    return hosts_share_site(requested_url, final_url)


@dataclass
class FetchResult:
    url: str
    outcome: FetchOutcome
    status_code: int | None = None
    content: bytes = b""
    text: str = ""
    content_type: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    from_cache: bool = False
    error: str = ""
    final_url: str = ""
    #: Which tier produced this content. Recorded on every SourcePage so a run
    #: can prove the browser tier is doing work rather than merely existing.
    fetch_tier: str = "http"
    #: HTTP validators, exactly as the origin sent them, plus a self-consistent
    #: hash of the extracted text. Recorded per page so the next visit can ask
    #: a conditional GET instead of re-downloading. A validator only means
    #: something to the origin that minted it; the browser tier carries none.
    etag: str = ""
    last_modified: str = ""
    content_hash: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome in (FetchOutcome.OK, FetchOutcome.CACHED)

    @property
    def is_pdf(self) -> bool:
        return "pdf" in self.content_type.lower() or self.final_url.lower().endswith(".pdf")


class ResponseCache:
    """Content-addressed disk cache. Keeps repeat runs off the network."""

    def __init__(self, root: Path, ttl_seconds: int = 86_400) -> None:
        self.root = root
        self.ttl = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, url: str) -> tuple[Path, Path]:
        digest = hashlib.sha256(url.encode()).hexdigest()[:32]
        bucket = self.root / digest[:2]
        return bucket / f"{digest}.meta.json", bucket / f"{digest}.body"

    def get(self, url: str) -> FetchResult | None:
        meta_path, body_path = self._paths(url)
        if not meta_path.exists() or not body_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - meta.get("stored_at", 0) > self.ttl:
            return None
        body = body_path.read_bytes()
        return FetchResult(
            url=url,
            outcome=FetchOutcome.CACHED,
            status_code=meta.get("status_code"),
            content=body,
            text=body.decode(meta.get("encoding", "utf-8"), errors="replace"),
            content_type=meta.get("content_type", ""),
            fetched_at=datetime.fromisoformat(meta["fetched_at"]),
            from_cache=True,
            final_url=meta.get("final_url", url),
            # Entries written before validators were recorded restore defaults.
            etag=meta.get("etag", ""),
            last_modified=meta.get("last_modified", ""),
            content_hash=meta.get("content_hash", ""),
        )

    def put(self, result: FetchResult) -> None:
        meta_path, body_path = self._paths(result.url)
        bucket = meta_path.parent
        bucket.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(result.content)
        meta_path.write_text(
            json.dumps(
                {
                    "url": result.url,
                    "final_url": result.final_url or result.url,
                    "status_code": result.status_code,
                    "content_type": result.content_type,
                    "fetched_at": result.fetched_at.isoformat(),
                    "stored_at": time.time(),
                    "encoding": "utf-8",
                    "etag": result.etag,
                    "last_modified": result.last_modified,
                    "content_hash": result.content_hash,
                }
            )
        )


class _FractionalCrawlDelayParser(urllib.robotparser.RobotFileParser):
    """A robots parser that keeps fractional Crawl-delay values.

    The stdlib parser stores a group's crawl-delay only when the value is all
    digits (``"2.5".isdigit()`` is False), so a site asking for
    ``Crawl-delay: 2.5`` — exactly what the REP examples use — had its request
    silently dropped and the fetcher fell back to its own, usually shorter,
    default. Everything else about parsing is the stdlib's; this only re-reads
    the crawl-delay lines with float semantics and patches them onto the
    entries the stdlib parser built, for the same user-agent groups.
    """

    #: Defined by the stdlib base class in __init__, whose stubs do not
    #: surface them; this subclass reads both after super().parse().
    entries: list[Any]
    default_entry: Any | None

    def parse(self, lines) -> None:
        super().parse(lines)
        groups: list[tuple[list[str], float]] = []
        useragents: list[str] = []
        delay: float | None = None
        saw_rule = False

        def close_group() -> None:
            nonlocal useragents, delay, saw_rule
            if useragents and delay is not None:
                groups.append((useragents, delay))
            useragents, delay, saw_rule = [], None, False

        for raw in lines:
            line = raw.split("#", 1)[0].strip()
            if not line:
                close_group()
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                # A user-agent line after a rule starts a new group, exactly
                # as the stdlib state machine treats it; consecutive
                # user-agent lines share one group.
                if saw_rule:
                    close_group()
                useragents.append(value)
            elif key in ("allow", "disallow", "crawl-delay", "request-rate"):
                saw_rule = True
                if key == "crawl-delay":
                    try:
                        delay = float(value)
                    except ValueError:
                        delay = None
        close_group()

        candidates = list(self.entries)
        if self.default_entry is not None:
            candidates.append(self.default_entry)
        for entry in candidates:
            if entry.delay is None:
                for group_useragents, group_delay in groups:
                    if entry.useragents == group_useragents:
                        entry.delay = group_delay
                        break

    def disallows(self, useragent: str, url: str) -> bool:
        """True when a Disallow rule of the group for ``useragent`` decides against ``url``.

        Two gaps of the stdlib parser, closed in the strict direction only (it
        can refuse what the stdlib allowed, never the reverse):

        * it compares a rule's path as a plain prefix, so ``Disallow: /*?*tag=*``
          or ``Disallow: /*.pdf$`` never matched anything and the page was read;
        * it takes the first matching line, so ``Allow: /`` above
          ``Disallow: /private/`` let the private path through.

        A matching Disallow is final unless a matching Allow is strictly more
        specific (longer), as in RFC 9309 §2.2.2, with a tie going to Disallow.
        The group is the one the stdlib picks (the first naming this agent,
        else ``*``).
        """
        entry = next((e for e in self.entries if e.applies_to(useragent)), self.default_entry)
        if entry is None:
            return False
        parsed = urllib.parse.urlsplit(urllib.parse.unquote(url))
        target = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
        longest = {True: -1, False: -1}
        for rule in entry.rulelines:
            path = urllib.parse.unquote(rule.path)
            if not path:
                continue
            anchored = path.endswith("$")
            pattern = ".*".join(re.escape(part) for part in path.rstrip("$").split("*"))
            if re.match(pattern + ("$" if anchored else ""), target):
                longest[rule.allowance] = max(longest[rule.allowance], len(path))
        return longest[False] >= 0 and longest[False] >= longest[True]


class _RobotsUnreachable(Exception):
    """robots.txt could not be fetched for a network or server reason."""


@dataclass(frozen=True)
class ProxySettings:
    """An explicit HTTPS proxy and the CA bundle that verifies TLS through it.

    Used only by ``Fetcher(trust_env_proxy=True)``. TLS verification is never
    turned off: without a CA bundle in the environment the system store is used.
    """

    url: str
    ca_bundle: str | None

    #: Read in this order; the first that is set wins.
    PROXY_VARS = ("HTTPS_PROXY", "https_proxy")
    CA_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> ProxySettings:
        env = os.environ if environ is None else environ
        url = next((env[k] for k in cls.PROXY_VARS if env.get(k)), "")
        if not url:
            raise ValueError("trust_env_proxy was asked for, but HTTPS_PROXY is not set")
        ca = next((env[k] for k in cls.CA_VARS if env.get(k)), None)
        return cls(url=url, ca_bundle=ca)

    def ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(cafile=self.ca_bundle)
        # create_default_context already verifies; stated so no edit loosens it.
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context


class RobotsPolicy:
    """robots.txt, fetched once per host and cached for the process lifetime."""

    def __init__(self, user_agent: str = USER_AGENT, enabled: bool = True) -> None:
        self.user_agent = user_agent
        self.enabled = enabled
        #: False when the fetcher sends through an explicit HTTPS proxy.
        self.pin_addresses = True
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        #: Hosts whose robots.txt never finished arriving.
        self.stalled: set[str] = set()
        #: Origins whose robots.txt was *unreachable* — a network error, a 5xx
        #: or a stall. RFC 9309 §2.3.1.4: the crawler MUST then assume a
        #: complete disallow. Unavailable (4xx) is different: no restrictions.
        self._unreachable: dict[str, str] = {}
        #: One lock per origin: a stalled host must not hold every other
        #: host's robots.txt behind it.
        self._locks: dict[str, asyncio.Lock] = {}

    async def allowed(self, url: str, client: httpx.AsyncClient) -> tuple[bool, str]:
        if not self.enabled:
            return True, "robots checking disabled by configuration"
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        async with self._locks.setdefault(host, asyncio.Lock()):
            if host not in self._parsers and host not in self._unreachable:
                try:
                    self._parsers[host] = await asyncio.wait_for(
                        self._load(host, client), ROBOTS_DEADLINE_SECONDS
                    )
                except TimeoutError:
                    # Remembered, so the host is not stalled on again.
                    log.info("robots.txt for %s did not arrive in time", host)
                    self._unreachable[host] = "did not arrive in time"
                    self.stalled.add(parsed.hostname or parsed.netloc)
                except _RobotsUnreachable as exc:
                    log.info("robots.txt for %s unreachable: %s", host, exc)
                    self._unreachable[host] = str(exc)
        if host in self._unreachable:
            return False, (
                f"robots.txt unreachable ({self._unreachable[host]}); RFC 9309 treats the "
                "whole site as disallowed"
            )
        parser = self._parsers[host]
        if parser is None:
            # Unavailable (4xx, or a robots.txt we will not read): the RFC's
            # "no restrictions" reading.
            return True, "no robots.txt available"
        allowed = parser.can_fetch(self.user_agent, url)
        if (
            allowed
            and isinstance(parser, _FractionalCrawlDelayParser)
            and parser.disallows(self.user_agent, url)
        ):
            allowed = False
        return allowed, "robots.txt allows" if allowed else "robots.txt disallows this path"

    def known(self, url: str) -> bool:
        """RL-1: whether a read of ``url`` needs no robots.txt request first."""
        if not self.enabled:
            return True
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        return host in self._parsers or host in self._unreachable

    async def crawl_delay(self, url: str) -> float | None:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._parsers.get(host)
        if parser is None:
            return None
        try:
            delay = parser.crawl_delay(self.user_agent)
            return float(delay) if delay else None
        except (AttributeError, TypeError, ValueError):
            return None

    async def _load(
        self, host: str, client: httpx.AsyncClient
    ) -> urllib.robotparser.RobotFileParser | None:
        robots_url = f"{host}/robots.txt"
        try:
            # robots.txt is fetched from a host the crawler was pointed at, so
            # it is exactly as attacker-influenced as any other URL.
            target = await _resolve_checked(robots_url)
        except BlockedRequest as exc:
            log.warning("refusing robots.txt for %s: %s", host, exc)
            return None
        # RL-1: charged before the request exists; past the cap, never built.
        _charge_wire(robots_url)
        try:
            request = _pinned_request(client, target, timeout=10.0, pin=self.pin_addresses)
            resp = await client.send(request, stream=True)
        except (httpx.HTTPError, OSError) as exc:
            raise _RobotsUnreachable(exc.__class__.__name__) from exc
        try:
            if resp.status_code >= 500:
                raise _RobotsUnreachable(f"HTTP {resp.status_code}")
            if resp.status_code < 200 or resp.status_code >= 300:
                return None
            declared = resp.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > MAX_ROBOTS_BYTES:
                log.info("robots.txt for %s exceeds the size limit", host)
                return None
            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes():
                total += len(chunk)
                if total > MAX_ROBOTS_BYTES:
                    log.info("robots.txt for %s exceeded the streaming size limit", host)
                    return None
                chunks.append(chunk)
        finally:
            await resp.aclose()
        parser = _FractionalCrawlDelayParser()
        parser.parse(b"".join(chunks).decode("utf-8", errors="replace").splitlines())
        return parser


# --- PII guard ------------------------------------------------------------

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    (
        "credential-like parameter",
        re.compile(r"(?i)\b(password|passwd|otp|token|secret|api[_-]?key)="),
    ),
)

#: A long digit run is only suspicious in a query string. Content management
#: systems put numeric node ids in paths all the time
#: (https://www.aalto.fi/en/node/1008496), and treating those as passport
#: numbers made the guard fire on ordinary university URLs.
#: PD-2: a numeric cache-buster (``?_t=1761184801``) is dropped before a stage
#: requests the link (``app/adapters/url_canonical.py``); this guard is unchanged.
_QUERY_DIGITS = re.compile(r"\b\d{9,}\b")


def find_pii(url: str, extra: str = "") -> str | None:
    """Name the kind of applicant data in a request, or None if there is none."""
    haystack = f"{url} {extra}"
    for label, pattern in _PII_PATTERNS:
        if pattern.search(haystack):
            return label
    query = urlparse(url).query
    if query and _QUERY_DIGITS.search(query):
        return "long digit sequence in a query parameter (passport/ID/card)"
    if extra and _QUERY_DIGITS.search(extra):
        return "long digit sequence (passport/ID/card)"
    return None


def assert_no_pii(url: str, extra: str = "") -> None:
    """Refuse to send applicant-identifying data to a third-party host.

    Raises, because a caller that *builds* a URL out of profile fields has a
    bug that must not be swallowed. ``Fetcher.get`` catches this for URLs it
    merely discovered while crawling, where the right response is to skip the
    link and carry on.
    """
    label = find_pii(url, extra)
    if label is not None:
        raise PIILeakError(
            f"Refusing to fetch: the request contains what looks like a {label}. "
            "Applicant data must never appear in an outbound URL."
        )


# --- content hash -----------------------------------------------------------


def _content_hash(text: str) -> str:
    """A self-consistency hash of page text: detects change without a body.

    sha256 over the NFKC-normalized, whitespace-collapsed extracted text. The
    hash is only ever compared against hashes computed by this same formula,
    so it is self-consistent by construction: if text extraction drifts, the
    worst case is one redundant re-extraction — never a false "unchanged".
    Falls back to the raw text when extraction fails or yields nothing, so a
    page the extractor cannot read is hashed as itself, not as empty.
    """
    try:
        from app.adapters.extraction import html_to_text

        extracted = html_to_text(text)
    except Exception:
        extracted = ""
    if not extracted:
        extracted = text
    normalized = unicodedata.normalize("NFKC", " ".join(extracted.split()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _refusal(result: FetchResult) -> str:
    """Why a host refused this read outright, or "" when it did not.

    A page that is missing (404) or broken (5xx) says nothing about the rest
    of the host; a 401/403, an unreadable robots.txt or a stalled host does.
    """
    if result.outcome == FetchOutcome.HTTP_ERROR and result.status_code in (401, 403):
        return f"HTTP {result.status_code}"
    if result.outcome == FetchOutcome.ROBOTS_DISALLOWED and "unreachable" in result.error:
        return "robots.txt unreachable"
    if result.outcome == FetchOutcome.TIMEOUT and "not waited on again" in result.error:
        return "host stalled"
    return ""


class Fetcher:
    """Polite, cached, rate-limited HTTP access."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        delay_seconds: float = DEFAULT_DELAY_SECONDS,
        respect_robots: bool = True,
        offline: bool = False,
        cache_ttl_seconds: int = 86_400,
        timeout: float = DEFAULT_TIMEOUT,
        contact: str = "",
        corpus_dir: Path | None = None,
        max_crawl_delay: float | None = MAX_CRAWL_DELAY_SECONDS,
        trust_env_proxy: bool = False,
    ) -> None:
        self.cache = ResponseCache(cache_dir, cache_ttl_seconds)
        self.robots = RobotsPolicy(enabled=respect_robots)
        #: Explicit opt-in (evidence checks run from an agent sandbox): send
        #: through the HTTPS_PROXY of the environment and verify TLS against its
        #: CA bundle. Off, nothing reads the proxy environment.
        self.proxy: ProxySettings | None = ProxySettings.from_env() if trust_env_proxy else None
        self.robots.pin_addresses = self.proxy is None
        self.delay = delay_seconds
        #: None waits out any Crawl-delay: for background work with no clock.
        self.max_crawl_delay = max_crawl_delay
        self.offline = offline
        self.timeout = timeout
        self.user_agent = (
            USER_AGENT.replace("set FETCH_CONTACT", contact) if contact else USER_AGENT
        )
        self._host_locks: dict[str, asyncio.Semaphore] = {}
        #: Hosts that already let one whole exchange run past its deadline in
        #: this fetcher's life. Run 20: Aalto stalled robots.txt, then
        #: sitemap.xml, and each stall cost the case most of its clock.
        self._stalled_hosts: set[str] = set()
        #: HS-1: URLs a caller declared as guesses (see mark_guessed).
        self._guessed_urls: set[str] = set()
        self._last_request: dict[str, float] = {}
        self._client: httpx.AsyncClient | None = None
        self.corpus_dir = corpus_dir
        #: Set by attach_renderer(). Escalation happens inside get(), so every
        #: adapter benefits without knowing the tier exists.
        self._renderer: object | None = None
        self.stats: dict[str, int] = {o.value: 0 for o in FetchOutcome}
        self.tier_counts: dict[str, int] = {"fixture": 0, "http": 0, "browser": 0, "pdf": 0}
        #: Hosts that refused this fetcher outright earlier in its life, and
        #: why: a 401/403, a robots.txt that could not be read, a host that
        #: stalled. Recorded only; nothing here changes what ``get`` does.
        #: Discovery may use it to stop offering pages on a host that is
        #: known not to answer (expert trace, Toronto 2026-09-27).
        self.refused_hosts: dict[str, str] = {}
        #: RS-1: URL -> the final URL its redirect chain reached, this run.
        self._redirect_memory: dict[str, str] = {}
        #: RL-1: one read ledger per institution, for this fetcher's life.
        self.ledgers: dict[str, CaseReadLedger] = {}
        #: TB-1: one case clock per institution, and the one running now.
        self.timers: dict[str, CaseTimeBudget] = {}
        self._running_timer: CaseTimeBudget | None = None
        #: TB-1: seconds each host's reads took, pacing waits excluded.
        self._host_seconds: dict[str, list[float]] = {}

    def ledger_for(self, institution: str) -> CaseReadLedger:
        """RL-1: ``institution``'s read ledger, opened on first use.

        Keyed by registrable domain, so the host discovery starts from
        (``www.imperial.ac.uk``) and the catalogue's domain (``imperial.ac.uk``)
        share one ledger.
        """
        key = registrable_domain(institution) or institution
        ledger = self.ledgers.get(key)
        if ledger is None:
            ledger = self.ledgers[key] = CaseReadLedger(key)
        return ledger

    @contextmanager
    def charging(self, institution: str, phase: str) -> Iterator[CaseReadLedger]:
        """RL-1: charge every wire request inside to ``institution``, as ``phase``."""
        ledger = self.ledger_for(institution)
        previous_phase = ledger.phase
        ledger.phase = phase
        token = _ACTIVE_LEDGER.set(ledger)
        timed = self.timing(institution, phase) if CASE_TIME_BUDGET else nullcontext()
        try:
            with timed:
                yield ledger
        finally:
            _ACTIVE_LEDGER.reset(token)
            ledger.phase = previous_phase

    def timer_for(self, institution: str) -> CaseTimeBudget:
        """TB-1: ``institution``'s case clock, opened (not started) on first use.

        Keyed like the read ledger, by registrable domain.
        """
        key = registrable_domain(institution) or institution
        timer = self.timers.get(key)
        if timer is None:
            timer = self.timers[key] = CaseTimeBudget(key)
        return timer

    @contextmanager
    def timing(self, institution: str, phase: str) -> Iterator[None]:
        """TB-1: the reads inside run on ``institution``'s case clock, as ``phase``.

        The clock keeps running after the scope ends, until another
        institution's scope starts: the work between two stages (parsing,
        filing claims) is still this institution's, and production's
        interleaved universities each get their own seconds.
        """
        timer = self.timer_for(institution)
        now = _clock()
        if self._running_timer is not timer:
            if self._running_timer is not None:
                self._running_timer.pause(now)
            timer.resume(now)
            self._running_timer = timer
        timer.enter(phase, now)
        token = _ACTIVE_TIMER.set(timer)
        try:
            yield None
        finally:
            _ACTIVE_TIMER.reset(token)

    def _pacing_wait(self, host: str, delay: float) -> float:
        """TB-1: how long the next request to ``host`` would wait for its pacing."""
        last = self._last_request.get(host)
        if last is None:
            return 0.0
        return max(delay - (_clock() - last), 0.0)

    def _expected_seconds(self, url: str) -> float:
        """TB-1: a read's predicted seconds after its wait: the host's mean so far."""
        samples = self._host_seconds.get(urlparse(url).hostname or "")
        expected = sum(samples) / len(samples) if samples else DEFAULT_READ_SECONDS
        if not self.robots.known(url):
            expected += DEFAULT_READ_SECONDS
        return expected

    async def _time_refusal(self, timer: CaseTimeBudget, url: str, start: str) -> str:
        """TB-1: why a read of ``url`` (starting at ``start``) is not started, or ""."""
        host = urlparse(start).hostname or ""
        delay = await self.robots.crawl_delay(start) or self.delay
        kind = _READ_KIND.get() or PHASE_DEFAULT_KIND.get(timer.phase, "discovery")
        reason = timer.admit(kind, self._pacing_wait(host, delay), self._expected_seconds(start))
        if reason:
            timer.refuse(url, kind, reason)
        return reason

    def _memory_key(self, url: str) -> str:
        return variant_key(url) if URL_VARIANT_DEDUPE else url

    def _cache_key(self, url: str) -> str:
        """RS-2: the key the disk cache is asked under; the URL itself while off."""
        return variant_key(url) if URL_VARIANT_DEDUPE else url

    def _remembered_final(self, url: str) -> str:
        """RS-1: where a URL is known to redirect to in this run, else itself."""
        if not REDIRECT_MEMORY:
            return url
        return self._redirect_memory.get(self._memory_key(url), url)

    def _cached(self, url: str) -> FetchResult | None:
        """The disk cache's copy of ``url`` (RS-2 key; RS-1 final URL), labelled ``url``."""
        keys = [self._cache_key(url)]
        final = self._remembered_final(url)
        if final != url:
            keys.append(self._cache_key(final))
        for key in dict.fromkeys(keys):
            cached = self.cache.get(key)
            if cached is not None:
                cached.url = url
                return cached
        return None

    def _store(self, result: FetchResult) -> None:
        """Cache a read under its URL (RS-2 key) and, with RS-1, its final URL."""
        key = self._cache_key(result.url)
        if key == result.url:
            self.cache.put(result)
        else:
            self.cache.put(replace(result, url=key))
        final = result.final_url
        if REDIRECT_MEMORY and final and self._cache_key(final) != key:
            self.cache.put(replace(result, url=self._cache_key(final), final_url=final))

    def _remember_chain(self, chain: list[str], final: str) -> None:
        """RS-1: every URL of a chain that ended at a readable ``final`` leads there."""
        if not REDIRECT_MEMORY:
            return
        for hop in chain:
            if hop != final:
                self._redirect_memory[self._memory_key(hop)] = final

    def mark_guessed(self, url: str) -> None:
        """Declare ``url`` a guess: probed by convention, not found on a page.

        Only recorded; it changes nothing unless GUESSED_URL_STALL_EXEMPT is
        on. Robots, pacing and the privacy guard apply to it as to any URL.
        """
        self._guessed_urls.add(url)

    def _is_guessed(self, url: str) -> bool:
        return GUESSED_URL_STALL_EXEMPT and url in self._guessed_urls

    def attach_renderer(self, renderer: object) -> None:
        """Give the fetcher a browser to escalate to.

        Escalation lives here rather than in each adapter because the previous
        arrangement - a helper the adapters were supposed to call - meant the
        browser tier was constructed on every run and never invoked once.
        """
        self._renderer = renderer

    async def _send_to_any_address(
        self, target: ResolvedTarget, current: str, headers: dict[str, str] | None
    ) -> httpx.Response:
        """Send to the first validated address that accepts a connection.

        A name often resolves to several addresses; one bad edge used to make
        the whole host look down. Every address was validated by the network
        policy, so trying the next one widens nothing. Only a failure to
        *connect* moves on — a server that answered is the answer.
        """
        assert self._client is not None
        if not isinstance(self._client, httpx.AsyncClient):
            request = self._client.build_request("GET", current, headers=headers)
            return await self._client.send(request, stream=True)
        if self.proxy is not None:
            # The proxy resolves the name and connects; there is no address
            # of ours to pin or to fall back from.
            _charge_wire(current)
            request = _pinned_request(self._client, target, headers=headers, pin=False)
            return await self._client.send(request, stream=True)
        addresses = list(dict.fromkeys(target.addresses))[:MAX_ADDRESSES_TRIED]
        timeout = (
            httpx.Timeout(self.timeout, connect=min(PER_ADDRESS_CONNECT_SECONDS, self.timeout))
            if len(addresses) > 1
            else None
        )
        for index, address in enumerate(addresses):
            _charge_wire(current)
            request = _pinned_request(
                self._client, target, headers=headers, address=address, timeout=timeout
            )
            try:
                return await self._client.send(request, stream=True)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if index == len(addresses) - 1:
                    raise
                log.info("%s via %s: %s; trying the next address", target.host, address, exc)
        raise AssertionError("unreachable")

    async def _request_with_redirects(
        self,
        url: str,
        *,
        validators: dict[str, str] | None = None,
        deadline: float | None = None,
        start: str | None = None,
    ) -> FetchResult:
        """Follow redirects by hand, re-validating every hop.

        Each Location is put through the same policy as the original URL, so a
        public page cannot bounce the crawler onto a private address — and it
        goes through the privacy guard too, so a redirect cannot smuggle
        applicant data into another host's access log.

        ``start`` (RS-1) is where the chain begins when it is not ``url``: the
        final URL ``url`` is remembered to redirect to. The result is still
        labelled ``url``.
        """
        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")
        current = start or url
        chain = [url, current]
        validators = dict(validators) if validators else None
        network_budget = self.timeout * ATTEMPT_DEADLINE_FACTOR
        if deadline is not None:
            network_budget = min(network_budget, deadline)
        for _hop in range(MAX_REDIRECTS + 1):
            resolve_started = time.monotonic()
            target = await _resolve_checked(current)
            network_budget -= time.monotonic() - resolve_started
            if network_budget <= 0:
                raise TimeoutError("redirect chain exhausted its network deadline")
            hop_result, network_used = await self._request_one_hop(
                url, current, target, validators, network_budget
            )
            network_budget -= network_used
            # Validators ride the caller's request only: a hop can land on
            # another host, and an entity tag minted by one origin must not be
            # replayed to another.
            validators = None
            if isinstance(hop_result, FetchResult):
                if hop_result.outcome is FetchOutcome.OK and same_source_site(url, current):
                    self._remember_chain(chain, current)
                return hop_result
            status_code, location = hop_result
            if not location:
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.HTTP_ERROR,
                    status_code=status_code,
                    error="redirect without a Location header",
                    final_url=current,
                )
            invalid: str | None
            try:
                joined = str(httpx.URL(current).join(location))
            except (httpx.InvalidURL, ValueError, UnicodeError) as exc:
                joined, invalid = location, str(exc)
            else:
                invalid = invalid_url_reason(joined)
            if invalid is not None:
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.HTTP_ERROR,
                    status_code=status_code,
                    error=f"redirect to an invalid URL: {invalid}"[:300],
                    final_url=current,
                )
            current = joined
            chain.append(current)
            # Refuse unsafe URLs before DNS or the destination's robots lookup.
            leak = find_pii(current)
            if leak is not None:
                log.warning("refusing %s: looks like %s", current[:120], leak)
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.REFUSED_PRIVACY,
                    error=f"Refused: the URL contains what looks like a {leak}. It was not fetched.",
                    final_url=current,
                )
            if not same_source_site(url, current):
                log.warning(
                    "refusing cross-site redirect from %s to %s",
                    urlparse(url).hostname,
                    urlparse(current).hostname,
                )
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.BLOCKED,
                    error=(
                        "redirect left the requested site's domain for "
                        f"{urlparse(current).hostname}; no source was read"
                    ),
                    final_url=current,
                )

        return FetchResult(
            url=url,
            outcome=FetchOutcome.HTTP_ERROR,
            final_url=current,
            error=f"more than {MAX_REDIRECTS} redirects",
        )

    async def _request_one_hop(
        self,
        requested_url: str,
        current: str,
        target: ResolvedTarget,
        validators: dict[str, str] | None,
        network_budget: float,
    ) -> tuple[FetchResult | tuple[int, str | None], float]:
        """Apply per-host policy and stream one response inside its host limit."""
        async with self._semaphore(target.host):
            refused = await self._redirect_policy(requested_url, current, target.host)
            if refused is not None:
                return refused, 0.0
            timer = _ACTIVE_TIMER.get() if CASE_TIME_BUDGET else None
            if timer is not None:
                # TB-1: no exchange runs past the case deadline.
                network_budget = min(network_budget, timer.left())
                if network_budget <= 0:
                    raise TimeoutError("case time budget (TB-1) spent before the exchange")

            async def exchange() -> FetchResult | tuple[int, str | None]:
                # The whole network/body exchange is bounded, including a
                # trickling response. Robots and permitted Crawl-delay above
                # do not spend this network budget.
                response = await self._send_to_any_address(target, current, validators)
                try:
                    # A 304 is terminal despite being in the 3xx family.
                    if response.status_code == 304 or not response.is_redirect:
                        return await self._read_response(requested_url, current, response)
                    return response.status_code, response.headers.get("location")
                finally:
                    await response.aclose()

            network_started = time.monotonic()
            result = await asyncio.wait_for(exchange(), network_budget)
            return result, time.monotonic() - network_started

    async def _redirect_policy(
        self, requested_url: str, redirect_url: str, host: str
    ) -> FetchResult | None:
        """Apply the destination's robots and pacing before following a hop."""
        assert self._client is not None
        if host in self._stalled_hosts or host in self.robots.stalled:
            return FetchResult(
                url=requested_url,
                outcome=FetchOutcome.TIMEOUT,
                error="redirect host stopped responding earlier in this run",
                final_url=redirect_url,
            )
        allowed, reason = await self.robots.allowed(redirect_url, self._client)
        if host in self.robots.stalled:
            return FetchResult(
                url=requested_url,
                outcome=FetchOutcome.TIMEOUT,
                error="redirect host robots.txt never finished arriving",
                final_url=redirect_url,
            )
        if not allowed:
            return FetchResult(
                url=requested_url,
                outcome=FetchOutcome.ROBOTS_DISALLOWED,
                error=reason,
                final_url=redirect_url,
            )
        asked = await self.robots.crawl_delay(redirect_url)
        if asked is not None and self.max_crawl_delay is not None and asked > self.max_crawl_delay:
            return FetchResult(
                url=requested_url,
                outcome=FetchOutcome.ROBOTS_CRAWL_DELAY,
                error=f"robots.txt asks for a {asked:.0f}s crawl delay on redirect host",
                final_url=redirect_url,
            )
        timer = _ACTIVE_TIMER.get() if CASE_TIME_BUDGET else None
        if timer is not None:
            # TB-1: the crawl delay is waited out in full or not at all.
            wait = self._pacing_wait(host, asked or self.delay)
            if wait >= timer.left():
                reason = (
                    f"{timer.left():.1f} s left; the host's crawl delay would end past the case "
                    "deadline"
                )
                timer.refuse(requested_url, _READ_KIND.get() or "hop", reason)
                return FetchResult(
                    url=requested_url,
                    outcome=FetchOutcome.BLOCKED,
                    error=f"case time budget (TB-1): {reason}; not read",
                    final_url=redirect_url,
                )
        await self._space_requests(host, redirect_url)
        return None

    async def _read_response(self, url: str, final_url: str, response) -> FetchResult:
        """Read a response, refusing what is too large or not worth parsing."""
        # A validated conditional request ends here (RFC 7232): a 304 has no
        # body and no content type to police, and the caller keeps the copy it
        # already has. Test this before the content-type, size and body
        # branches — none of them mean anything for a 304.
        if response.status_code == 304:
            await response.aclose()
            return FetchResult(
                url=url,
                outcome=FetchOutcome.CACHED,
                status_code=304,
                from_cache=True,
                error="not modified (304)",
                final_url=final_url,
            )

        if response.status_code >= 400:
            await response.aclose()
            return FetchResult(
                url=url,
                outcome=FetchOutcome.HTTP_ERROR,
                status_code=response.status_code,
                error=f"HTTP {response.status_code}",
                final_url=final_url,
            )

        content_type = response.headers.get("content-type", "")
        base_type = content_type.split(";")[0].strip().lower()
        if base_type and not any(base_type == allowed for allowed in ALLOWED_CONTENT_TYPES):
            await response.aclose()
            return FetchResult(
                url=url,
                outcome=FetchOutcome.UNPARSEABLE,
                status_code=response.status_code,
                content_type=content_type,
                final_url=final_url,
                error=f"content type {base_type!r} is not something we parse",
            )

        # A declared length over the cap is refused without reading anything.
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_BYTES:
            await response.aclose()
            return FetchResult(
                url=url,
                outcome=FetchOutcome.TOO_LARGE,
                status_code=response.status_code,
                content_type=content_type,
                final_url=final_url,
                error=f"declared {int(declared):,} bytes, over the {MAX_BYTES:,} limit",
            )

        # And an undeclared one is cut off as it arrives, not after.
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > MAX_BYTES:
                await response.aclose()
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.TOO_LARGE,
                    status_code=response.status_code,
                    content_type=content_type,
                    final_url=final_url,
                    error=f"body exceeded the {MAX_BYTES:,} byte limit while streaming",
                )
            chunks.append(chunk)
        await response.aclose()

        content = b"".join(chunks)
        text = content.decode(response.encoding or "utf-8", errors="replace")
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=response.status_code,
            content=content,
            text=text,
            content_type=content_type,
            final_url=final_url,
            # Record what the next visit needs to ask "has this changed?".
            etag=response.headers.get("etag", ""),
            last_modified=response.headers.get("last-modified", ""),
            content_hash=_content_hash(text),
        )

    async def _maybe_render(self, result: FetchResult) -> FetchResult:
        """Escalate to the browser when a 200 came back with no usable text."""
        if self._renderer is None or not result.ok or result.is_pdf:
            return result
        from app.adapters.extraction import html_to_text

        if len(html_to_text(result.text)) >= MIN_USEFUL_TEXT:
            return result

        rendered = await self._renderer.render(result.url)  # type: ignore[attr-defined]
        # A renderer that reports OK while carrying an error status (an older
        # browser tier did) must not launder its error page into the fetch of
        # record or the disk cache: the rendered body stays unread and the
        # original HTTP result stands.
        if rendered.status_code is not None and rendered.status_code >= 400:
            log.warning(
                "browser tier returned HTTP %s for %s; keeping the plain HTTP result",
                rendered.status_code,
                result.url[:120],
            )
            return result
        if rendered.ok and not same_source_site(result.url, rendered.final_url or rendered.url):
            log.warning("browser tier left the requested host %s", urlparse(result.url).hostname)
            return result
        if rendered.ok and len(html_to_text(rendered.text)) > len(html_to_text(result.text)):
            rendered.fetch_tier = "browser"
            # Browser output has no HTTP validators: whatever a renderer claims
            # to carry over from the HTTP tier is dropped here, and the content
            # hash is recomputed from the rendered text.
            rendered.etag = ""
            rendered.last_modified = ""
            rendered.content_hash = _content_hash(rendered.text)
            self.tier_counts["browser"] += 1
            log.info("escalated %s to the browser tier", result.url[:120])
            self.cache.put(rendered)
            return rendered
        return result

    def _client_options(self) -> dict[str, Any]:
        """Keyword arguments of the ``httpx.AsyncClient``; the proxy only when opted in."""
        if self.proxy is None:
            return {}
        return {
            "proxy": self.proxy.url,
            "verify": self.proxy.ssl_context(),
            # Only what was resolved explicitly above; no other env lookups.
            "trust_env": False,
        }

    async def __aenter__(self) -> Fetcher:
        self._client = httpx.AsyncClient(
            **self._client_options(),
            headers={"User-Agent": self.user_agent, "Accept-Language": "en"},
            # Redirects are followed by hand so every hop is re-validated. With
            # httpx following them, a public URL could redirect straight to a
            # private address and the policy would never see it.
            follow_redirects=False,
            timeout=self.timeout,
            max_redirects=0,
            # Requests are keyed by pinned IP. Avoid reusing one TLS
            # connection for two virtual hosts that share that address.
            limits=httpx.Limits(max_keepalive_connections=0),
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _semaphore(self, host: str) -> asyncio.Semaphore:
        if host not in self._host_locks:
            self._host_locks[host] = asyncio.Semaphore(MAX_PER_HOST_CONCURRENCY)
        return self._host_locks[host]

    async def _space_requests(self, host: str, url: str) -> None:
        delay = await self.robots.crawl_delay(url) or self.delay
        last = self._last_request.get(host)
        if last is not None:
            wait = delay - (_clock() - last)
            if wait > 0:
                await _sleep(wait)
                timing = _READ_TIMING.get()
                if timing is not None:
                    timing.waited += wait
        self._last_request[host] = _clock()

    def _fetch_fixture(self, url: str) -> FetchResult:
        """Serve a bundled page for a ``fixture://`` URL.

        Demo mode routes through here so it exercises the same parsing,
        claim-building and assessment code as a live run - the only difference
        is where the bytes came from.
        """
        if self.corpus_dir is None:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.NOT_FOUND
                if hasattr(FetchOutcome, "NOT_FOUND")
                else FetchOutcome.HTTP_ERROR,
                error="No corpus directory is configured for fixture:// URLs.",
            )
        rel = url[len("fixture://") :].lstrip("/")
        path = (self.corpus_dir / rel).resolve()
        # Refuse to escape the corpus directory.
        if not str(path).startswith(str(self.corpus_dir.resolve())):
            return FetchResult(
                url=url, outcome=FetchOutcome.HTTP_ERROR, error="path traversal refused"
            )
        if not path.is_file():
            self.stats[FetchOutcome.HTTP_ERROR.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.HTTP_ERROR,
                status_code=404,
                error=f"No bundled page at {rel}",
                final_url=url,
            )
        data = path.read_bytes()
        ctype = "application/pdf" if path.suffix == ".pdf" else "text/html; charset=utf-8"
        self.stats[FetchOutcome.OK.value] += 1
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            content=data,
            text=data.decode("utf-8", errors="replace") if path.suffix != ".pdf" else "",
            content_type=ctype,
            final_url=url,
        )

    def _time_cut(self, timer: CaseTimeBudget, url: str, reason: str) -> FetchResult:
        """TB-1: a read the case clock ended after it started; the host is not blamed."""
        timer.cut += 1
        timer.refuse(url, _READ_KIND.get() or "read", reason)
        self.stats[FetchOutcome.BLOCKED.value] += 1
        return FetchResult(
            url=url,
            outcome=FetchOutcome.BLOCKED,
            error=f"{_TB_PREFIX}{reason}",
            final_url=url,
        )

    async def get(
        self,
        url: str,
        *,
        use_cache: bool = True,
        etag: str | None = None,
        if_modified_since: str | None = None,
    ) -> FetchResult:
        """Fetch a URL from the disk cache when possible, else politely.

        See ``_get``; this wrapper only records a host that refused outright
        and, under TB-1, how long a read that went to the network took.
        """
        invalid = invalid_url_reason(url)
        if invalid is not None:
            # Before anything parses it: the PII guard, the host bookkeeping
            # below and httpx would each raise on it.
            return self._invalid_url(url, invalid)
        timing = _ReadTiming() if CASE_TIME_BUDGET else None
        token = _READ_TIMING.set(timing) if timing is not None else None
        began = _clock()
        try:
            result = await self._get(
                url, use_cache=use_cache, etag=etag, if_modified_since=if_modified_since
            )
        except httpx.InvalidURL as exc:
            # A URL that slipped past ``invalid_url_reason`` (or a redirect
            # chain that built one) is a failed read, never an exception
            # that ends the case.
            result = self._invalid_url(url, str(exc))
        finally:
            if token is not None:
                _READ_TIMING.reset(token)
        if timing is not None and timing.network and not result.error.startswith(_TB_PREFIX):
            # TB-1: the host's read time, pacing waits excluded, predicts its next read.
            seconds = max(_clock() - began - timing.waited, 0.0)
            self._host_seconds.setdefault(urlparse(url).hostname or "", []).append(seconds)
        reason = _refusal(result)
        host = urlparse(url).hostname or ""
        if reason and host:
            self.refused_hosts.setdefault(host, reason)
        return result

    def _invalid_url(self, url: str, reason: str) -> FetchResult:
        """A URL that cannot be requested as written: a failed read, not an exception.

        Real pages link hosts ending in a zero-width space (usp) and phone
        numbers where the port goes (rwth); see ``page_link``, the extraction rule.
        """
        log.warning("not fetching a malformed URL: %s", reason[:200])
        self.stats[FetchOutcome.UNPARSEABLE.value] += 1
        return FetchResult(
            url=url,
            outcome=FetchOutcome.UNPARSEABLE,
            error=f"invalid URL, not fetched: {reason}"[:300],
            final_url=url,
        )

    async def _get(
        self,
        url: str,
        *,
        use_cache: bool = True,
        etag: str | None = None,
        if_modified_since: str | None = None,
    ) -> FetchResult:
        """Fetch a URL from the disk cache when possible, else politely.

        ``etag`` / ``if_modified_since`` are supplied by the caller (from its
        own source_pages records); the fetcher never touches the database. With
        a validator present the disk cache is skipped and the first request
        carries If-None-Match and/or If-Modified-Since (RFC 7232: when both are
        sent, the entity tag takes precedence). A 304 is a terminal success:
        it comes back as CACHED with an empty body and ``status_code == 304``,
        so callers must check the status and keep the copy they already have.
        """
        # A URL harvested from a page can contain anything. Refuse it and move
        # on: one bad link must not end a research run.
        leak = find_pii(url)
        if leak is not None:
            log.warning("refusing %s: looks like %s", url[:120], leak)
            self.stats[FetchOutcome.REFUSED_PRIVACY.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.REFUSED_PRIVACY,
                error=(f"Refused: the URL contains what looks like a {leak}. It was not fetched."),
            )

        if url.startswith("fixture://"):
            result = self._fetch_fixture(url)
            self.tier_counts["fixture" if result.ok else "http"] += 1
            return result

        # Conditional GET: the point of a validator is to ask the origin, not
        # to answer from the local cache, so a validator skips the cache read.
        validators: dict[str, str] = {}
        if etag:
            validators["If-None-Match"] = etag
        if if_modified_since:
            validators["If-Modified-Since"] = if_modified_since

        if use_cache and not validators:
            cached = self._cached(url)
            if cached is not None:
                if same_source_site(url, cached.final_url or url):
                    self.stats[FetchOutcome.CACHED.value] += 1
                    self.tier_counts[cached.fetch_tier] = (
                        self.tier_counts.get(cached.fetch_tier, 0) + 1
                    )
                    return cached
                log.warning("ignoring cached cross-site response for %s", urlparse(url).hostname)

        if self.offline:
            self.stats[FetchOutcome.NETWORK_UNAVAILABLE.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.NETWORK_UNAVAILABLE,
                error="Offline mode: no cached copy of this page is available.",
            )

        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")

        #: RS-1: a URL known to redirect starts its read at the final URL.
        start = self._remembered_final(url)
        early = urlparse(url).hostname or ""
        if early in self._stalled_hosts or early in self.robots.stalled:
            self.stats[FetchOutcome.TIMEOUT.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.TIMEOUT,
                error="host stopped responding earlier in this run; not waited on again",
            )
        ledger = _ACTIVE_LEDGER.get()
        if ledger is not None:
            # RL-1: a read that would leave fewer reads than its kind's floor
            # is not started; robots.txt still to load costs one more.
            kind = ledger.kind()
            reason = ledger.admit(1 if self.robots.known(start) else 2, kind)
            if reason:
                ledger.refuse(url, kind, reason)
                self.stats[FetchOutcome.BLOCKED.value] += 1
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.BLOCKED,
                    error=f"case read budget (RL-1): {reason}; not read",
                    final_url=url,
                )
        timer = _ACTIVE_TIMER.get() if CASE_TIME_BUDGET else None
        if timer is not None:
            # TB-1: a read predicted to leave less than its kind's floor is
            # not started; neither is one whose crawl delay outlasts the clock.
            reason = await self._time_refusal(timer, url, start)
            if reason:
                self.stats[FetchOutcome.BLOCKED.value] += 1
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.BLOCKED,
                    error=f"{_TB_PREFIX}{reason}; not read",
                    final_url=url,
                )
        timing = _READ_TIMING.get()
        if timing is not None:
            timing.network = True
        try:
            target = await _resolve_checked(url)
        except TimeoutError:
            self._stalled_hosts.add(urlparse(url).hostname or url)
            self.stats[FetchOutcome.TIMEOUT.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.TIMEOUT,
                error=f"name resolution took longer than {DNS_DEADLINE_SECONDS:.0f}s",
            )
        except BlockedRequest as exc:
            log.warning("blocked by network policy: %s", exc)
            self.stats[FetchOutcome.BLOCKED.value] += 1
            return FetchResult(url=url, outcome=FetchOutcome.BLOCKED, error=str(exc))

        host = target.host
        guessed = self._is_guessed(url)
        deadline = min(self.timeout, GUESSED_URL_TIMEOUT_SECONDS) if guessed else None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            attempt_deadline = deadline
            if timer is not None:
                # TB-1: every attempt ends by the case deadline.
                left = timer.left()
                if left <= 0:
                    return self._time_cut(timer, url, "no time left for this attempt")
                attempt_deadline = left if deadline is None else min(deadline, left)
            try:
                result = await self._request_with_redirects(
                    url,
                    validators=validators,
                    deadline=attempt_deadline,
                    start=start if start != url else None,
                )
            except BlockedRequest as exc:
                log.warning("blocked mid-redirect: %s", exc)
                self.stats[FetchOutcome.BLOCKED.value] += 1
                return FetchResult(url=url, outcome=FetchOutcome.BLOCKED, error=str(exc))
            except CaseReadSpent as exc:
                # RL-1: the cap fell inside this read (a hop, a retry, robots).
                if ledger is not None:
                    ledger.refuse(url, ledger.kind(), "the cap was reached during the read")
                self.stats[FetchOutcome.BLOCKED.value] += 1
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.BLOCKED,
                    error=f"{exc} (RL-1); the read stopped at the cap",
                    final_url=url,
                )
            except TimeoutError:
                if timer is not None and timer.left() <= TIME_CUT_SLACK_SECONDS:
                    # TB-1: the case clock ended the exchange, not the host.
                    return self._time_cut(timer, url, "the read was cut at the case deadline")
                # The whole exchange overran: a server that trickles will
                # trickle again, so this is not retried, nor is the host.
                # HS-1: a guessed URL's stall skips only that URL.
                if not guessed:
                    self._stalled_hosts.add(host)
                self.stats[FetchOutcome.TIMEOUT.value] += 1
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.TIMEOUT,
                    error="no complete response within the deadline",
                )
            except httpx.TimeoutException as exc:
                # HS-1: a guess is not worth a second wait.
                if attempt == MAX_ATTEMPTS or guessed:
                    self.stats[FetchOutcome.TIMEOUT.value] += 1
                    return FetchResult(url=url, outcome=FetchOutcome.TIMEOUT, error=str(exc))
            except (httpx.HTTPError, OSError) as exc:
                if attempt == MAX_ATTEMPTS:
                    self.stats[FetchOutcome.NETWORK_UNAVAILABLE.value] += 1
                    return FetchResult(
                        url=url, outcome=FetchOutcome.NETWORK_UNAVAILABLE, error=str(exc)
                    )
            else:
                if result.outcome is FetchOutcome.OK:
                    if not same_source_site(url, result.final_url or url):
                        self.stats[FetchOutcome.BLOCKED.value] += 1
                        return FetchResult(
                            url=url,
                            outcome=FetchOutcome.BLOCKED,
                            error="response left the requested site's domain",
                            final_url=result.final_url,
                        )
                    self._store(result)
                    self.stats[FetchOutcome.OK.value] += 1
                    self.tier_counts["pdf" if result.is_pdf else "http"] += 1
                    try:
                        return await self._maybe_render(result)
                    except Exception as exc:
                        # The escalation sits outside the retry excepts
                        # above, so an infra failure in the browser tier
                        # must be contained here: it becomes a diagnostic
                        # result, never an exception out of get().
                        log.warning("browser tier failed for %s: %s", url, exc)
                        self.stats[FetchOutcome.UNPARSEABLE.value] += 1
                        return FetchResult(
                            url=url,
                            outcome=FetchOutcome.UNPARSEABLE,
                            error=f"browser tier failed: {exc}"[:300],
                        )
                # Retry only what is worth retrying.
                retryable = result.status_code == 429 or (
                    result.status_code is not None and 500 <= result.status_code < 600
                )
                if not retryable or attempt == MAX_ATTEMPTS:
                    self.stats[result.outcome.value] += 1
                    return result
            if timer is not None and timer.left() <= 2**attempt + MIN_CORE_READ_SECONDS:
                # TB-1: no retry whose backoff would leave no time to read.
                return self._time_cut(timer, url, "no time left to retry")
            # Exponential backoff: 2s, 4s.
            await _sleep(2**attempt)

        self.stats[FetchOutcome.HTTP_ERROR.value] += 1
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error="exhausted attempts")
