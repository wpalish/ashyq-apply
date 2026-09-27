"""The fetcher records a host that refused outright, and nothing else changes."""

from __future__ import annotations

from app.adapters.fetching import FetchResult, _refusal
from app.domain.enums import FetchOutcome


def _result(outcome: FetchOutcome, *, status: int | None = None, error: str = "") -> FetchResult:
    return FetchResult(url="https://x.edu/a", outcome=outcome, status_code=status, error=error)


def test_a_403_or_401_is_a_refusal_of_the_host() -> None:
    assert _refusal(_result(FetchOutcome.HTTP_ERROR, status=403)) == "HTTP 403"
    assert _refusal(_result(FetchOutcome.HTTP_ERROR, status=401)) == "HTTP 401"


def test_a_missing_or_broken_page_says_nothing_about_the_host() -> None:
    assert _refusal(_result(FetchOutcome.HTTP_ERROR, status=404)) == ""
    assert _refusal(_result(FetchOutcome.HTTP_ERROR, status=503)) == ""
    assert _refusal(_result(FetchOutcome.OK, status=200)) == ""


def test_an_unreadable_robots_txt_refuses_the_host_but_a_path_rule_does_not() -> None:
    unreachable = (
        "robots.txt unreachable (ReadTimeout); RFC 9309 treats the whole site as disallowed"
    )
    assert _refusal(_result(FetchOutcome.ROBOTS_DISALLOWED, error=unreachable))
    assert _refusal(_result(FetchOutcome.ROBOTS_DISALLOWED, error="Disallow: /private")) == ""


async def test_get_records_the_refusing_host(tmp_path, monkeypatch) -> None:
    from app.adapters.fetching import Fetcher

    fetcher = Fetcher(tmp_path)

    async def refused(url: str, **kwargs: object) -> FetchResult:
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=403)

    monkeypatch.setattr(fetcher, "_get", refused)
    result = await fetcher.get("https://future.utoronto.ca/apply")

    assert result.status_code == 403
    assert fetcher.refused_hosts == {"future.utoronto.ca": "HTTP 403"}
