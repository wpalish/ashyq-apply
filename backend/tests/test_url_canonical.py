"""PD-2 (PDF map ticket 06): a numeric cache-buster is dropped before the PII guard sees a link."""

from __future__ import annotations

import inspect
import re

import pytest

from app.adapters import fetching, url_canonical
from app.adapters.fetching import find_pii
from app.adapters.url_canonical import canonical_link

UM = "https://study.um.edu.my/doc/tution-fee/Fee%20Structure.pdf"
UCPH = "https://www.ku.dk/studieordninger/erhvervska.pdf"
DOMAINS = ("um.edu.my", "ku.dk")


@pytest.fixture
def on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(url_canonical, "CACHE_BUSTER_CANONICAL", True)


def test_a_named_numeric_cache_buster_is_dropped(on: None) -> None:
    assert find_pii(f"{UM}?_t=1761184801")  # refused before PD-2
    assert canonical_link(f"{UM}?_t=1761184801", DOMAINS) == UM
    assert find_pii(UM) is None


def test_a_bare_number_query_is_dropped(on: None) -> None:
    assert canonical_link(f"{UCPH}?177667006", DOMAINS) == UCPH


def test_other_parameters_are_kept_and_the_buster_alone_dropped(on: None) -> None:
    url = "https://study.um.edu.my/fees.pdf?lang=en&v=1761184801"
    assert canonical_link(url, DOMAINS) == "https://study.um.edu.my/fees.pdf?lang=en"


def test_an_id_parameter_is_unchanged_and_still_refused(on: None) -> None:
    url = "https://study.um.edu.my/apply?id=123456789"
    assert canonical_link(url, DOMAINS) == url
    assert find_pii(canonical_link(url, DOMAINS))


def test_a_buster_beside_letters_is_unchanged(on: None) -> None:
    url = "https://study.um.edu.my/doc.pdf?_t=abc123456789"
    assert canonical_link(url, DOMAINS) == url


def test_a_digit_run_in_the_path_is_untouched(on: None) -> None:
    url = "https://study.um.edu.my/node/1761184801/fees.pdf?x=1"
    assert canonical_link(url, DOMAINS) == url


def test_another_registrable_domain_is_unchanged(on: None) -> None:
    url = "https://cdn.example.com/fee.pdf?_t=1761184801"
    assert canonical_link(url, DOMAINS) == url


def test_flag_off_is_the_identity() -> None:
    assert url_canonical.CACHE_BUSTER_CANONICAL is False
    url = f"{UM}?_t=1761184801"
    assert canonical_link(url, DOMAINS) == url


def test_the_pii_guard_itself_is_unchanged() -> None:
    assert fetching._QUERY_DIGITS.pattern == r"\b\d{9,}\b"
    source = inspect.getsource(fetching.find_pii)
    assert "canonical" not in source and "_QUERY_DIGITS.search(query)" in source
    assert not re.search(r"url_canonical", inspect.getsource(fetching).split("_QUERY_DIGITS =")[1])


@pytest.mark.asyncio
async def test_the_cost_stage_requests_the_canonical_link(on: None) -> None:
    from app.adapters.base import Candidate
    from app.adapters.cost.web_costs import WebCostAdapter
    from tests.test_pdf_evidence import FakeFetcher

    fetcher = FakeFetcher({})
    candidate = Candidate(
        name="Universiti Malaya",
        country="Malaysia",
        city="Kuala Lumpur",
        domain="um.edu.my",
        costs_url=f"{UM}?_t=1761184801",
    )
    await WebCostAdapter(fetcher, "2026/27").fetch(candidate)  # type: ignore[arg-type]
    assert fetcher.requested == [UM]
