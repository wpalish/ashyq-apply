"""The crawler must not be usable to reach the network it runs on.

Every URL the crawler follows comes from a third-party page, so all of them are
attacker-influenced. Before this policy existed the crawler reached
``127.0.0.1``, ``localhost`` and ``192.168.1.1``; the cloud metadata endpoint
was "blocked" only because it happened to time out.
"""

from __future__ import annotations

import socket

import pytest

from app.adapters.fetching import ALLOWED_CONTENT_TYPES, MAX_BYTES, Fetcher
from app.adapters.network_policy import (
    ALLOWED_PORTS,
    MAX_REDIRECTS,
    BlockedRequest,
    check_url,
    is_allowed,
    is_blocked_address,
)
from app.domain.enums import FetchOutcome


def resolver_returning(*addresses: str):
    """A stand-in for getaddrinfo, so DNS behaviour is testable offline."""

    def resolve(host, port, **_kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
            for a in addresses
        ]

    return resolve


class TestBlockedAddresses:
    @pytest.mark.parametrize(
        "address",
        [
            "127.0.0.1",
            "127.1.2.3",
            "0.0.0.0",
            "10.0.0.1",
            "10.255.255.254",
            "172.16.0.1",
            "172.31.255.254",
            "192.168.0.1",
            "192.168.1.1",
            "169.254.169.254",  # AWS/GCP/Azure metadata
            "100.64.0.1",  # carrier-grade NAT
            "198.18.0.1",  # benchmarking
            "224.0.0.1",  # multicast
            "::1",  # IPv6 loopback
            "fe80::1",  # IPv6 link-local
            "fd00::1",  # IPv6 unique-local
            "::",  # unspecified
            "::ffff:127.0.0.1",  # IPv4 loopback wrapped in IPv6
            "::ffff:10.0.0.1",  # IPv4 private wrapped in IPv6
        ],
    )
    def test_private_and_reserved_addresses_are_blocked(self, address):
        blocked, reason = is_blocked_address(address)
        assert blocked, f"{address} was allowed"
        assert reason

    @pytest.mark.parametrize("address", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1::1"])
    def test_public_addresses_are_allowed(self, address):
        blocked, _ = is_blocked_address(address)
        assert not blocked

    def test_a_malformed_address_is_blocked_not_ignored(self):
        blocked, reason = is_blocked_address("not-an-ip")
        assert blocked
        assert "not a valid IP" in reason


class TestUrlPolicy:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/x",
            "gopher://example.com/",
            "data:text/html,<script>alert(1)</script>",
            "jar:http://example.com/!/",
        ],
    )
    def test_only_http_and_https_are_allowed(self, url):
        allowed, reason = is_allowed(url)
        assert not allowed
        assert "http and https" in reason or "no host" in reason

    @pytest.mark.parametrize(
        "host",
        [
            "localhost",
            "LOCALHOST",
            "localhost.",
            "metadata.google.internal",
            "instance-data",
        ],
    )
    def test_hostnames_that_name_the_local_host_are_blocked_by_name(self, host):
        """Blocked before resolution, so a resolver quirk cannot let one past."""
        allowed, reason = is_allowed(f"http://{host}/")
        assert not allowed
        assert "local host" in reason

    @pytest.mark.parametrize("port", [22, 25, 3306, 5432, 6379, 9200, 11211, 8099])
    def test_non_web_ports_are_blocked(self, port):
        allowed, reason = is_allowed(f"http://example.com:{port}/")
        assert not allowed
        assert str(port) in reason

    @pytest.mark.parametrize("port", sorted(ALLOWED_PORTS))
    def test_web_ports_are_allowed(self, port):
        allowed, _ = is_allowed(
            f"http://example.com:{port}/", resolver=resolver_returning("93.184.216.34")
        )
        assert allowed

    def test_a_url_with_no_host_is_blocked(self):
        allowed, reason = is_allowed("http:///path")
        assert not allowed
        assert "no host" in reason

    @pytest.mark.parametrize(
        "url",
        ["https://user@example.com/", "https://user:password@example.com/"],
    )
    def test_credentials_in_urls_are_blocked(self, url):
        allowed, reason = is_allowed(url, resolver=resolver_returning("93.184.216.34"))
        assert not allowed
        assert "credentials" in reason


class TestDnsHandling:
    def test_a_name_resolving_to_a_private_address_is_blocked(self):
        """The classic bypass: a public name pointing inward."""
        with pytest.raises(BlockedRequest, match="private"):
            check_url("http://evil.example.com/", resolver=resolver_returning("10.0.0.5"))

    def test_every_resolved_address_is_checked_not_just_the_first(self):
        """A name answering with one public and one private address must fail."""
        with pytest.raises(BlockedRequest, match="private"):
            check_url(
                "http://mixed.example.com/",
                resolver=resolver_returning("93.184.216.34", "192.168.1.1"),
            )

    def test_a_name_that_does_not_resolve_is_blocked(self):
        def failing(host, port, **_kwargs):
            raise OSError("NXDOMAIN")

        with pytest.raises(BlockedRequest, match="does not resolve"):
            check_url("http://nowhere.example.com/", resolver=failing)

    def test_a_name_resolving_to_nothing_is_blocked(self):
        with pytest.raises(BlockedRequest, match="resolves to nothing"):
            check_url("http://empty.example.com/", resolver=lambda *a, **k: [])

    def test_the_resolved_addresses_are_recorded_for_pinning(self):
        target = check_url("https://ok.example.com/x", resolver=resolver_returning("93.184.216.34"))
        assert target.addresses == ("93.184.216.34",)
        assert target.port == 443


class TestFetcherEnforcement:
    """The policy has to be enforced by the thing that actually connects."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/",
            "http://localhost/",
            "http://[::1]/",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/",
            "http://172.16.5.4/",
            "http://192.168.1.1/",
            "http://[::ffff:127.0.0.1]/",
            "file:///etc/passwd",
            "http://example.com:22/",
        ],
    )
    async def test_the_fetcher_refuses_before_connecting(self, tmp_path, url):
        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            result = await fetcher.get(url)
        assert result.outcome is FetchOutcome.BLOCKED, f"{url} was not blocked"
        assert result.content == b""

    @pytest.mark.asyncio
    async def test_a_blocked_url_is_reported_not_raised(self, tmp_path):
        """One bad link must not end a research run."""
        async with Fetcher(tmp_path / "c", delay_seconds=0.0) as fetcher:
            result = await fetcher.get("http://127.0.0.1/")
        assert result.outcome is FetchOutcome.BLOCKED
        assert "Refusing" in result.error

    @pytest.mark.asyncio
    async def test_redirects_are_not_followed_automatically(self, tmp_path):
        """httpx following them itself would bypass the per-hop check."""
        async with Fetcher(tmp_path / "c", delay_seconds=0.0) as fetcher:
            assert fetcher._client.follow_redirects is False

    @pytest.mark.asyncio
    async def test_a_redirect_to_a_private_address_is_blocked(self, tmp_path, monkeypatch):
        """A public page must not be able to bounce the crawler inward."""
        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            if request.headers.get("host") == "public.example.com":
                return httpx.Response(302, headers={"location": "http://169.254.169.254/"})
            return httpx.Response(200, text="secret metadata")

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr(
                "app.adapters.fetching.check_url",
                lambda u, **k: __import__(
                    "app.adapters.network_policy", fromlist=["check_url"]
                ).check_url(u, resolver=resolver_returning("93.184.216.34"))
                if "public.example.com" in u
                else _real_check(u),
            )
            result = await fetcher.get("http://public.example.com/")

        assert result.outcome is FetchOutcome.BLOCKED
        assert "169.254.169.254" in result.error
        assert "secret metadata" not in result.text

    @pytest.mark.asyncio
    async def test_connection_is_pinned_to_the_validated_address(self, tmp_path, monkeypatch):
        """A second DNS answer cannot change where the socket connects."""
        import httpx

        observed: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            observed["url_host"] = request.url.host
            observed["host_header"] = request.headers.get("host")
            observed["sni"] = request.extensions.get("sni_hostname")
            return httpx.Response(200, headers={"content-type": "text/html"}, text="safe")

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/page")

        assert result.outcome is FetchOutcome.OK
        assert observed == {
            "url_host": "93.184.216.34",
            "host_header": "ok.example.com",
            "sni": "ok.example.com",
        }

    @pytest.mark.asyncio
    async def test_a_redirect_loop_is_bounded(self, tmp_path, monkeypatch):
        import httpx

        hops = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            hops["n"] += 1
            return httpx.Response(302, headers={"location": "https://ok.example.com/next"})

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/")

        assert result.outcome is FetchOutcome.HTTP_ERROR
        assert "redirects" in result.error
        assert hops["n"] <= MAX_REDIRECTS + 1


class TestResponseLimits:
    @pytest.mark.asyncio
    async def test_a_declared_oversize_body_is_refused_before_reading(self, tmp_path, monkeypatch):
        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/html", "content-length": str(MAX_BYTES * 3)},
                content=b"x",
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/big")

        assert result.outcome is FetchOutcome.TOO_LARGE
        assert "declared" in result.error

    @pytest.mark.asyncio
    async def test_an_undeclared_oversize_body_is_cut_off_while_streaming(
        self, tmp_path, monkeypatch
    ):
        """A server that omits its length must not win by drip-feeding."""
        import httpx

        class EndlessStream(httpx.AsyncByteStream):
            """No content-length, so only the streaming cap can stop it."""

            def __init__(self) -> None:
                self.sent = 0

            async def __aiter__(self):
                while True:
                    chunk = b"a" * 64_000
                    self.sent += len(chunk)
                    yield chunk

        stream = EndlessStream()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                stream=stream,
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/huge")

        assert result.outcome is FetchOutcome.TOO_LARGE
        assert "streaming" in result.error
        assert len(result.content) == 0
        # It stopped soon after the cap rather than reading forever.
        assert stream.sent < MAX_BYTES * 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content_type",
        [
            "application/zip",
            "video/mp4",
            "application/octet-stream",
            "image/png",
        ],
    )
    async def test_content_we_do_not_parse_is_refused(self, tmp_path, monkeypatch, content_type):
        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"content-type": content_type}, content=b"x" * 100)

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/file")

        assert result.outcome is FetchOutcome.UNPARSEABLE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("content_type", list(ALLOWED_CONTENT_TYPES))
    async def test_content_we_do_parse_is_accepted(self, tmp_path, monkeypatch, content_type):
        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": f"{content_type}; charset=utf-8"},
                content=b"<html>ok</html>",
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)
            result = await fetcher.get("https://ok.example.com/page")

        assert result.outcome is FetchOutcome.OK


def _real_check(url: str):
    from app.adapters.network_policy import check_url as real

    return real(url)


def _allow_example(url: str, **_kwargs):
    from app.adapters.network_policy import check_url as real

    return real(url, resolver=resolver_returning("93.184.216.34"))


class TestMalformedHostsFromUntrustedPages:
    """A link on a crawled page must never take the run down.

    `http://0177.0.0.1/` is a classic obfuscated-loopback probe. On a resolver
    that reads the octal it becomes 127.0.0.1 and the policy blocks it; on one
    that does not, it resolves to a public address, is allowed, and then the
    HTTP client rejects the literal as an invalid IPv4 address. That exception
    escaped `Fetcher.get` and crashed the caller.
    """

    @pytest.mark.parametrize("url", [
        "http://0177.0.0.1/",
        "http://0x7f.0x0.0x0.0x1/",
        "http://00000177.0.0.1/",
        "http://999.999.999.999/",
        "http://[not-an-ipv6]/",
        "http://exam ple.edu/",
    ])
    @pytest.mark.asyncio
    async def test_a_malformed_host_is_reported_not_raised(self, tmp_path, url):
        async with Fetcher(tmp_path / "c", respect_robots=False) as fetcher:
            result = await fetcher.get(url)
        assert not result.ok
        assert result.error

    @pytest.mark.parametrize("url", [
        "http://0177.0.0.1/",
        "http://00000177.0.0.1/",
        "http://0x7f.0x0.0x0.0x1/",
    ])
    def test_an_octal_or_hex_encoded_host_is_refused_outright(self, url):
        """Defence that does not depend on how this machine's resolver reads
        a leading zero. No legitimate hostname is written that way."""
        with pytest.raises(BlockedRequest):
            check_url(url)
