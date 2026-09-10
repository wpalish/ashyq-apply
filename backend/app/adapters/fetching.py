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
import re
import time
import unicodedata
import urllib.robotparser
from dataclasses import dataclass, field
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
from app.adapters.offload import off_loop
from app.domain.enums import FetchOutcome

log = logging.getLogger("unimatch.fetch")

USER_AGENT = (
    "ASHYQApplyBot/0.2 (+https://github.com/wpalish/ashyq-apply; "
    "university admissions research for a single applicant; contact: set FETCH_CONTACT)"
)
DEFAULT_TIMEOUT = 20.0
DEFAULT_DELAY_SECONDS = 1.5
MAX_PER_HOST_CONCURRENCY = 2
MAX_ATTEMPTS = 3
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
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Request:
    """Connect to the validated IP while preserving virtual-host TLS and HTTP."""
    pinned_url = httpx.URL(target.url).copy_with(host=target.pinned_address)
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

    async def _load(
        self, host: str, client: httpx.AsyncClient
    ) -> urllib.robotparser.RobotFileParser | None:
        robots_url = f"{host}/robots.txt"
        try:
            # robots.txt is fetched from a host the crawler was pointed at, so
            # it is exactly as attacker-influenced as any other URL.
            target = await off_loop(check_url, robots_url)
        except BlockedRequest as exc:
            log.warning("refusing robots.txt for %s: %s", host, exc)
            return None
        try:
            request = _pinned_request(client, target, timeout=10.0)
            resp = await client.send(request, stream=True)
        except (httpx.HTTPError, OSError) as exc:
            log.info("robots.txt unavailable for %s (%s)", host, exc.__class__.__name__)
            return None
        try:
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
        self.user_agent = (
            USER_AGENT.replace("set FETCH_CONTACT", contact) if contact else USER_AGENT
        )
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

    async def _request_with_redirects(
        self, url: str, *, validators: dict[str, str] | None = None
    ) -> FetchResult:
        """Follow redirects by hand, re-validating every hop.

        Each Location is put through the same policy as the original URL, so a
        public page cannot bounce the crawler onto a private address — and it
        goes through the privacy guard too, so a redirect cannot smuggle
        applicant data into another host's access log.
        """
        if self._client is None:
            raise RuntimeError("Fetcher must be used as an async context manager")
        current = url
        validators = dict(validators) if validators else None
        for _hop in range(MAX_REDIRECTS + 1):
            target = await off_loop(check_url, current)
            # ``get()`` buffers the entire body before returning, which would
            # make the byte cap below cosmetic (and lets an endless response
            # exhaust memory). Keep the response streaming from the socket.
            request = (
                _pinned_request(self._client, target, headers=validators)
                if isinstance(self._client, httpx.AsyncClient)
                else self._client.build_request("GET", current, headers=validators)
            )
            # Validators ride the caller's request only: a hop can land on
            # another host, and an entity tag minted by one origin must not be
            # replayed to another.
            validators = None
            response = await self._client.send(request, stream=True)

            # A 304 is a 3xx but not a redirect: it is the answer to a
            # conditional request, and httpx counts every 3xx as is_redirect.
            # Hand it to _read_response, which tests it before any of the
            # content-type, size or body branches.
            if response.status_code == 304 or not response.is_redirect:
                return await self._read_response(url, current, response)

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    await response.aclose()
                    return FetchResult(
                        url=url,
                        outcome=FetchOutcome.HTTP_ERROR,
                        status_code=response.status_code,
                        error="redirect without a Location header",
                        final_url=current,
                    )
                # The hop was streamed, so its body is an open socket: close
                # it before chasing the next Location, or every redirect
                # leaks one connection.
                await response.aclose()
                current = str(httpx.URL(current).join(location))
                # The same privacy guard that ran on the caller's URL runs on
                # every hop discovered here, before the next check_url: the
                # URL is refused before it can even reach DNS. It returns
                # rather than raises — a crawl-discovered link is skipped, not
                # fatal — and the hop's response is already closed above.
                leak = find_pii(current)
                if leak is not None:
                    log.warning("refusing %s: looks like %s", current[:120], leak)
                    return FetchResult(
                        url=url,
                        outcome=FetchOutcome.REFUSED_PRIVACY,
                        error=(
                            f"Refused: the URL contains what looks like a {leak}. "
                            "It was not fetched."
                        ),
                        final_url=current,
                    )
                continue

        return FetchResult(
            url=url,
            outcome=FetchOutcome.HTTP_ERROR,
            final_url=current,
            error=f"more than {MAX_REDIRECTS} redirects",
        )

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

    async def __aenter__(self) -> Fetcher:
        self._client = httpx.AsyncClient(
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

    async def get(
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
            cached = self.cache.get(url)
            if cached is not None:
                self.stats[FetchOutcome.CACHED.value] += 1
                self.tier_counts[cached.fetch_tier] = self.tier_counts.get(cached.fetch_tier, 0) + 1
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

        try:
            target = await off_loop(check_url, url)
        except BlockedRequest as exc:
            log.warning("blocked by network policy: %s", exc)
            self.stats[FetchOutcome.BLOCKED.value] += 1
            return FetchResult(url=url, outcome=FetchOutcome.BLOCKED, error=str(exc))

        host = target.host
        async with self._semaphore(host):
            allowed, reason = await self.robots.allowed(url, self._client)
            if not allowed:
                log.warning("robots.txt disallows %s", url)
                self.stats[FetchOutcome.ROBOTS_DISALLOWED.value] += 1
                return FetchResult(url=url, outcome=FetchOutcome.ROBOTS_DISALLOWED, error=reason)

            for attempt in range(1, MAX_ATTEMPTS + 1):
                await self._space_requests(host, url)
                try:
                    result = await self._request_with_redirects(url, validators=validators)
                except BlockedRequest as exc:
                    log.warning("blocked mid-redirect: %s", exc)
                    self.stats[FetchOutcome.BLOCKED.value] += 1
                    return FetchResult(url=url, outcome=FetchOutcome.BLOCKED, error=str(exc))
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
                    if result.outcome is FetchOutcome.OK:
                        self.cache.put(result)
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
                # Exponential backoff: 2s, 4s.
                await asyncio.sleep(2**attempt)

        self.stats[FetchOutcome.HTTP_ERROR.value] += 1
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error="exhausted attempts")
