"""scripts/verify_evidence.py from an agent sandbox: proxy opt-in, Crawl-delay wait, --recheck.

No network: every client is an ``httpx.MockTransport`` and DNS is a fixed
public address.
"""

from __future__ import annotations

import json
import socket
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import certifi
import httpx
import pytest

from app.adapters import fetching
from app.adapters.fetching import USER_AGENT, Fetcher, ProxySettings
from app.domain.enums import FetchOutcome
from scripts import verify_evidence

HOST = "www.mit.edu"
CASE = "qs2027-001"
PROXY = "http://127.0.0.1:9"
PAGE = (
    "<html><body><main><p>IELTS 7.0 overall is required.</p>"
    + ("<p>Admissions text.</p>" * 30)
    + "</main></body></html>"
)


def _resolve_public(url: str, **_kwargs: Any) -> Any:
    from app.adapters.network_policy import check_url as real

    def resolve(host: str, port: int, **_kw: Any) -> list[Any]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    return real(url, resolver=resolve)


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _resolve_public)


class _Site:
    """A mock web site: robots.txt text plus HTML pages; records every request."""

    def __init__(self, robots: str, pages: dict[str, str] | None = None) -> None:
        self.robots = robots
        self.pages = pages or {}
        self.requests: list[httpx.Request] = []
        self.client_options: dict[str, Any] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=self.robots, headers={"content-type": "text/plain"})
        body = self.pages.get(request.url.path, PAGE)
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        site = self
        real = httpx.AsyncClient

        class Recording(real):  # type: ignore[misc, valid-type]
            def __init__(self, **kwargs: Any) -> None:
                site.client_options = dict(kwargs)
                # The proxy and TLS context are recorded, then replaced by the mock.
                for key in ("proxy", "verify", "trust_env"):
                    kwargs.pop(key, None)
                super().__init__(transport=httpx.MockTransport(site.handler), **kwargs)

        monkeypatch.setattr(fetching.httpx, "AsyncClient", Recording)

    def page_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path != "/robots.txt"]


@pytest.fixture
def proxy_env(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("HTTPS_PROXY", PROXY)
    monkeypatch.setenv("SSL_CERT_FILE", certifi.where())
    return certifi.where()


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The fetcher's pacing clock and sleep: sleeping only advances the clock."""
    now = [1000.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(fetching, "_clock", lambda: now[0])
    monkeypatch.setattr(fetching, "_sleep", sleep)
    return slept


# ---------------------------------------------------------------- proxy opt-in


def test_proxy_settings_come_only_from_the_environment_named():
    settings = ProxySettings.from_env({"HTTPS_PROXY": PROXY, "SSL_CERT_FILE": certifi.where()})
    assert settings == ProxySettings(url=PROXY, ca_bundle=certifi.where())
    context = settings.ssl_context()
    assert context.verify_mode is ssl.CERT_REQUIRED and context.check_hostname
    with pytest.raises(ValueError, match="HTTPS_PROXY"):
        ProxySettings.from_env({"SSL_CERT_FILE": certifi.where()})
    # No CA bundle in the environment: the system store, still verifying.
    assert ProxySettings.from_env({"https_proxy": PROXY}).ca_bundle is None


def test_without_the_opt_in_the_fetcher_reads_no_proxy(tmp_path, proxy_env):
    fetcher = Fetcher(tmp_path)
    assert fetcher.proxy is None and fetcher._client_options() == {}
    assert fetcher.robots.pin_addresses


async def test_opt_in_sends_by_host_name_through_the_proxy_with_tls_verified(
    tmp_path, monkeypatch, proxy_env
):
    site = _Site("User-agent: *\nDisallow: /private/\n")
    site.install(monkeypatch)
    async with Fetcher(tmp_path, trust_env_proxy=True, delay_seconds=0) as fetcher:
        result = await fetcher.get(f"https://{HOST}/admissions", use_cache=False)
    assert result.outcome is FetchOutcome.OK
    assert site.client_options["proxy"] == PROXY
    verify = site.client_options["verify"]
    assert isinstance(verify, ssl.SSLContext)
    assert verify.verify_mode is ssl.CERT_REQUIRED and verify.check_hostname
    assert site.client_options["trust_env"] is False
    assert [r.url.path for r in site.requests] == ["/robots.txt", "/admissions"]
    for request in site.requests:
        # The proxy's CONNECT names the host; nothing is pinned to an address.
        assert request.url.host == HOST
        assert "sni_hostname" not in request.extensions
        assert request.headers["user-agent"] == USER_AGENT


async def test_default_fetcher_still_pins_the_validated_address(tmp_path, monkeypatch):
    site = _Site("User-agent: *\nDisallow:\n")
    site.install(monkeypatch)
    async with Fetcher(tmp_path, delay_seconds=0) as fetcher:
        result = await fetcher.get(f"https://{HOST}/admissions", use_cache=False)
    assert result.outcome is FetchOutcome.OK
    assert "proxy" not in site.client_options
    assert {r.url.host for r in site.requests} == {"93.184.216.34"}
    assert all(r.extensions.get("sni_hostname") == HOST for r in site.requests)


@pytest.mark.parametrize(
    "path",
    ["/search?q=x&tag=cs", "/private/fees", "/files/report.pdf"],
)
async def test_robots_disallow_is_final_with_wildcards_through_the_proxy(
    tmp_path, monkeypatch, proxy_env, path
):
    site = _Site(
        "User-agent: *\nAllow: /\nDisallow: /*?*tag=*\nDisallow: /private/\nDisallow: /*.pdf$\n"
    )
    site.install(monkeypatch)
    async with Fetcher(tmp_path, trust_env_proxy=True, delay_seconds=0) as fetcher:
        result = await fetcher.get(f"https://{HOST}{path}", use_cache=False)
    assert result.outcome is FetchOutcome.ROBOTS_DISALLOWED
    assert site.page_requests() == []


def test_a_more_specific_allow_still_opens_its_path():
    parser = fetching._FractionalCrawlDelayParser()
    parser.parse(["User-agent: *", "Disallow: /", "Allow: /admissions/"])
    assert not parser.disallows(USER_AGENT, f"https://{HOST}/admissions/international")
    assert parser.disallows(USER_AGENT, f"https://{HOST}/research")


# ---------------------------------------------------------------- crawl delay


def _draft(*answers: tuple[str, str, str]) -> dict[str, Any]:
    return {
        "case": CASE,
        "answers": {
            item: {"status": "known", "value": "x", "url": url, "quote": quote}
            for item, url, quote in answers
        },
    }


TWO_PAGES = _draft(
    ("english", f"https://{HOST}/a", "IELTS 7.0 overall"),
    ("gpa", f"https://{HOST}/b", "IELTS 7.0 overall is required"),
)


async def test_crawl_delay_up_to_30_seconds_is_waited_out(monkeypatch, fake_clock):
    site = _Site("User-agent: *\nCrawl-delay: 20\n")
    site.install(monkeypatch)
    rows = await verify_evidence.check([TWO_PAGES], 5.0)
    assert [(r["item"], r["outcome"], r["quote_found"]) for r in rows if r["url"]] == [
        ("english", "ok", True),
        ("gpa", "ok", True),
    ]
    assert [r.url.path for r in site.page_requests()] == ["/a", "/b"]
    assert fake_clock == [20.0]  # the second read waited the host's full delay


async def test_crawl_delay_above_30_seconds_is_still_skipped(monkeypatch, fake_clock):
    site = _Site("User-agent: *\nCrawl-delay: 45\n")
    site.install(monkeypatch)
    rows = await verify_evidence.check([TWO_PAGES], 5.0)
    assert {r["outcome"] for r in rows if r["url"]} == {"robots_crawl_delay"}
    assert site.page_requests() == [] and fake_clock == []


# ---------------------------------------------------------------- recheck


def _row(item: str, url: str | None, outcome: str = "ok", **extra: Any) -> dict[str, Any]:
    return {
        "case": CASE,
        "item": item,
        "url": url,
        "outcome": outcome,
        "official": True,
        "quote_found": True,
        **extra,
    }


def test_recheck_targets_only_failed_rows_robots_refusals_excluded():
    report = [
        _row("programme", "https://a/ok"),
        _row("english", "https://a/403", "http_error", status_code=403, quote_found=False),
        _row("gpa", "https://a/robots", "robots_disallowed", quote_found=False),
        _row("deadline", "https://a/slow", "robots_crawl_delay", quote_found=False),
        _row("tuition", "https://other/x", official=False),
        _row("scholarship_exists", "https://a/missing", quote_found=False),
        _row("scholarship_international", None, "-", official=None, quote_found=None),
        # One URL read twice (two programme drafts): it passed once, so it stands.
        _row("programme", "https://a/twice", quote_found=False),
        _row("programme", "https://a/twice"),
    ]
    assert verify_evidence.recheck_targets(report) == {
        (CASE, "english", "https://a/403"),
        (CASE, "deadline", "https://a/slow"),
        (CASE, "tuition", "https://other/x"),
        (CASE, "scholarship_exists", "https://a/missing"),
    }


def test_recheck_writes_only_the_failed_rows_beside_the_report(tmp_path, monkeypatch):
    site = _Site("User-agent: *\nDisallow:\n")
    site.install(monkeypatch)
    batch = tmp_path / "batch1"
    (batch / "core").mkdir(parents=True)
    (batch / "core" / f"{CASE}.json").write_text(
        json.dumps(
            _draft(
                ("english", f"https://{HOST}/a", "IELTS 7.0 overall"),
                ("gpa", f"https://{HOST}/b", "IELTS 7.0 overall"),
                ("deadline", f"https://{HOST}/c", "IELTS 7.0 overall"),
            )
        ),
        encoding="utf-8",
    )
    report = batch / "evidence_check.ci-2026-10-19.json"
    report.write_text(
        json.dumps(
            [
                _row("english", f"https://{HOST}/a"),
                _row("gpa", f"https://{HOST}/b", "http_error", status_code=403, quote_found=False),
                _row("deadline", f"https://{HOST}/c", "robots_disallowed", quote_found=False),
            ]
        ),
        encoding="utf-8",
    )
    verify_evidence.main(["--recheck", str(report)])
    day = datetime.now(UTC).date().isoformat()
    out = batch / f"evidence_check.recheck-{day}.json"
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert [(r["item"], r["outcome"], r["official"], r["quote_found"]) for r in rows] == [
        ("gpa", "ok", True, True)
    ]
    assert rows[0]["origin"] == "sandbox-proxy" and rows[0]["checked_on"] == day
    assert {"case", "draft_status", "url", "status_code", "chars", "note"} <= set(rows[0])
    assert [r.url.path for r in site.page_requests()] == ["/b"]


def test_recheck_refuses_a_drafts_directory_too(tmp_path):
    with pytest.raises(SystemExit):
        verify_evidence.main([str(tmp_path), "--recheck", str(tmp_path / "r.json")])


def test_load_skips_reports_beside_the_drafts(tmp_path: Path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.json").write_text(json.dumps({"case": "x"}), encoding="utf-8")
    (tmp_path / "evidence_check.recheck-2026-10-19.json").write_text("[]", encoding="utf-8")
    assert verify_evidence.load(tmp_path) == [{"case": "x"}]
