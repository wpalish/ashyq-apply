"""The single door to the outside world.

Every network read in the product goes through ``Fetcher``. That is what makes
the politeness guarantees checkable in one place: robots.txt is consulted
before the first request to a host, per-host concurrency is capped, requests
are spaced, responses are cached on disk, and failures back off rather than
retry tightly.

The fetcher also enforces a privacy rule that is easy to violate by accident:
no applicant data may appear in an outbound URL. ``assert_no_pii`` is called on
every request and raises rather than leaking.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.domain.enums import FetchOutcome

log = logging.getLogger("unimatch.fetch")

USER_AGENT = (
    "UniMatchResearchBot/0.1 (+https://github.com/unimatch/unimatch; "
    "university admissions research for a single applicant; contact: set FETCH_CONTACT)"
)
DEFAULT_TIMEOUT = 20.0
DEFAULT_DELAY_SECONDS = 1.5
MAX_PER_HOST_CONCURRENCY = 2
MAX_ATTEMPTS = 3
MAX_BYTES = 5_000_000


class PIILeakError(RuntimeError):
    """Raised when applicant data would be placed in an outbound request."""


#: Below this many characters of extractable text, a "successful" HTML fetch is
#: an empty shell worth escalating to a browser.
MIN_USEFUL_TEXT = 400


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
                }
            )
        )


class RobotsPolicy:
    """robots.txt, fetched once per host and cached for the process lifetime."""

    def __init__(self, user_agent: str = USER_AGENT, enabled: bool = True) -> None:
        self.user_agent = user_agent
        self.enabled = enabled
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._lock = asyncio.Lock()

    async def allowed(self, url: str, client: httpx.AsyncClient) -> tuple[bool, str]:
        if not self.enabled:
            return True, "robots checking disabled by configuration"
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        async with self._lock:
            if host not in self._parsers:
                self._parsers[host] = await self._load(host, client)
        parser = self._parsers[host]
        if parser is None:
            # No reachable robots.txt is treated as "allowed" - the same
            # interpretation the RFC and every major crawler uses.
            return True, "no robots.txt available"
        allowed = parser.can_fetch(self.user_agent, url)
        return allowed, "robots.txt allows" if allowed else "robots.txt disallows this path"

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

    async def _load(self, host: str, client: httpx.AsyncClient) -> urllib.robotparser.RobotFileParser | None:
        try:
            resp = await client.get(f"{host}/robots.txt", timeout=10.0)
        except (httpx.HTTPError, OSError) as exc:
            log.info("robots.txt unavailable for %s (%s)", host, exc.__class__.__name__)
            return None
        if resp.status_code >= 400:
            return None
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser


# --- PII guard ------------------------------------------------------------

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("credential-like parameter", re.compile(r"(?i)\b(password|passwd|otp|token|secret|api[_-]?key)=")),
)

#: A long digit run is only suspicious in a query string. Content management
#: systems put numeric node ids in paths all the time
#: (https://www.aalto.fi/en/node/1008496), and treating those as passport
#: numbers made the guard fire on ordinary university URLs.
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
    ) -> None:
        self.cache = ResponseCache(cache_dir, cache_ttl_seconds)
        self.robots = RobotsPolicy(enabled=respect_robots)
        self.delay = delay_seconds
        self.offline = offline
        self.timeout = timeout
        self.user_agent = USER_AGENT.replace("set FETCH_CONTACT", contact) if contact else USER_AGENT
        self._host_locks: dict[str, asyncio.Semaphore] = {}
        self._last_request: dict[str, float] = {}
        self._client: httpx.AsyncClient | None = None
        self.corpus_dir = corpus_dir
        #: Set by attach_renderer(). Escalation happens inside get(), so every
        #: adapter benefits without knowing the tier exists.
        self._renderer: object | None = None
        self.stats: dict[str, int] = {o.value: 0 for o in FetchOutcome}
        self.tier_counts: dict[str, int] = {"fixture": 0, "http": 0, "browser": 0, "pdf": 0}

    def attach_renderer(self, renderer: object) -> None:
        """Give the fetcher a browser to escalate to.

        Escalation lives here rather than in each adapter because the previous
        arrangement - a helper the adapters were supposed to call - meant the
        browser tier was constructed on every run and never invoked once.
        """
        self._renderer = renderer

    async def _maybe_render(self, result: FetchResult) -> FetchResult:
        """Escalate to the browser when a 200 came back with no usable text."""
        if self._renderer is None or not result.ok or result.is_pdf:
            return result
        from app.adapters.extraction import html_to_text

        if len(html_to_text(result.text)) >= MIN_USEFUL_TEXT:
            return result

        rendered = await self._renderer.render(result.url)  # type: ignore[attr-defined]
        if rendered.ok and len(html_to_text(rendered.text)) > len(html_to_text(result.text)):
            rendered.fetch_tier = "browser"
            self.tier_counts["browser"] += 1
            log.info("escalated %s to the browser tier", result.url[:120])
            self.cache.put(rendered)
            return rendered
        return result

    async def __aenter__(self) -> Fetcher:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent, "Accept-Language": "en"},
            follow_redirects=True,
            timeout=self.timeout,
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
            wait = delay - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
        self._last_request[host] = time.monotonic()

    def _fetch_fixture(self, url: str) -> FetchResult:
        """Serve a bundled page for a ``fixture://`` URL.

        Demo mode routes through here so it exercises the same parsing,
        claim-building and assessment code as a live run - the only difference
        is where the bytes came from.
        """
        if self.corpus_dir is None:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.NOT_FOUND if hasattr(FetchOutcome, "NOT_FOUND") else FetchOutcome.HTTP_ERROR,
                error="No corpus directory is configured for fixture:// URLs.",
            )
        rel = url[len("fixture://") :].lstrip("/")
        path = (self.corpus_dir / rel).resolve()
        # Refuse to escape the corpus directory.
        if not str(path).startswith(str(self.corpus_dir.resolve())):
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error="path traversal refused")
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

    async def get(self, url: str, *, use_cache: bool = True) -> FetchResult:
        # A URL harvested from a page can contain anything. Refuse it and move
        # on: one bad link must not end a research run.
        leak = find_pii(url)
        if leak is not None:
            log.warning("refusing %s: looks like %s", url[:120], leak)
            self.stats[FetchOutcome.REFUSED_PRIVACY.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.REFUSED_PRIVACY,
                error=(
                    f"Refused: the URL contains what looks like a {leak}. "
                    "It was not fetched."
                ),
            )

        if url.startswith("fixture://"):
            result = self._fetch_fixture(url)
            self.tier_counts["fixture" if result.ok else "http"] += 1
            return result

        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                self.stats[FetchOutcome.CACHED.value] += 1
                self.tier_counts[cached.fetch_tier] = (
                    self.tier_counts.get(cached.fetch_tier, 0) + 1
                )
                return cached

        if self.offline:
            self.stats[FetchOutcome.NETWORK_UNAVAILABLE.value] += 1
            return FetchResult(
                url=url,
                outcome=FetchOutcome.NETWORK_UNAVAILABLE,
                error="Offline mode: no cached copy of this page is available.",
            )

        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")

        host = urlparse(url).netloc
        async with self._semaphore(host):
            allowed, reason = await self.robots.allowed(url, self._client)
            if not allowed:
                log.warning("robots.txt disallows %s", url)
                self.stats[FetchOutcome.ROBOTS_DISALLOWED.value] += 1
                return FetchResult(url=url, outcome=FetchOutcome.ROBOTS_DISALLOWED, error=reason)

            for attempt in range(1, MAX_ATTEMPTS + 1):
                await self._space_requests(host, url)
                try:
                    resp = await self._client.get(url)
                except httpx.TimeoutException as exc:
                    if attempt == MAX_ATTEMPTS:
                        self.stats[FetchOutcome.TIMEOUT.value] += 1
                        return FetchResult(url=url, outcome=FetchOutcome.TIMEOUT, error=str(exc))
                except (httpx.HTTPError, OSError) as exc:
                    if attempt == MAX_ATTEMPTS:
                        self.stats[FetchOutcome.NETWORK_UNAVAILABLE.value] += 1
                        return FetchResult(
                            url=url, outcome=FetchOutcome.NETWORK_UNAVAILABLE, error=str(exc)
                        )
                else:
                    if resp.status_code == 429 or 500 <= resp.status_code < 600:
                        if attempt == MAX_ATTEMPTS:
                            self.stats[FetchOutcome.HTTP_ERROR.value] += 1
                            return FetchResult(
                                url=url,
                                outcome=FetchOutcome.HTTP_ERROR,
                                status_code=resp.status_code,
                                error=f"HTTP {resp.status_code} after {MAX_ATTEMPTS} attempts",
                            )
                    elif resp.status_code >= 400:
                        self.stats[FetchOutcome.HTTP_ERROR.value] += 1
                        return FetchResult(
                            url=url,
                            outcome=FetchOutcome.HTTP_ERROR,
                            status_code=resp.status_code,
                            error=f"HTTP {resp.status_code}",
                        )
                    else:
                        content = resp.content[:MAX_BYTES]
                        result = FetchResult(
                            url=url,
                            outcome=FetchOutcome.OK,
                            status_code=resp.status_code,
                            content=content,
                            text=content.decode(resp.encoding or "utf-8", errors="replace"),
                            content_type=resp.headers.get("content-type", ""),
                            final_url=str(resp.url),
                        )
                        self.cache.put(result)
                        self.stats[FetchOutcome.OK.value] += 1
                        self.tier_counts["pdf" if result.is_pdf else "http"] += 1
                        return await self._maybe_render(result)
                # Exponential backoff: 2s, 4s.
                await asyncio.sleep(2 ** attempt)

        self.stats[FetchOutcome.HTTP_ERROR.value] += 1
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error="exhausted attempts")
