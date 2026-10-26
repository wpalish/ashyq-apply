"""Free-search ticket 07: the scheduled KB re-verification, offline.

``scripts/verify_evidence.py --from-kb`` rows from a fixture KB, the diff's
classes and queue file, and ``kb_build --refresh``. Every client is an
``httpx.MockTransport``; DNS is a fixed public address. No network.
"""

from __future__ import annotations

import json
import socket
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters import fetching
from app.adapters.fetching import Fetcher
from evaluation.research.expert import kb_build, kb_refresh_diff
from evaluation.research.expert.kb_refresh_diff import classify, compare
from scripts import verify_evidence

MIT = "qs2027-001"
HOST = "www.mit.edu"
QUOTE = "IELTS Minimum: 7 Recommended: 7.5"
PAGE = f"<html><body><main><p>{QUOTE}</p>" + "<p>Admissions text.</p>" * 30 + "</main></body>"
OTHER = "<html><body><main>" + "<p>Nothing about tests here.</p>" * 30 + "</main></body>"


def _fact(key: str, url: str, quote: str = QUOTE, **extra: Any) -> dict[str, Any]:
    return {
        "key": key,
        "value": 7.0,
        "source_url": url,
        "quote": quote,
        "verified_on": "2026-01-02",
        "verified_by": "ci",
        "stale": False,
        **extra,
    }


def _kb() -> dict[str, Any]:
    """Two universities; one fact per page behaviour of the mock site."""
    return {
        "format": "kb-cs-bachelor/1",
        "intake": "fall 2027",
        "stale_policy": {"as_of": "2026-10-19"},
        "evidence_reports": ["evidence_check.ci-2026-10-19.json"],
        "entries": {
            MIT: {
                "seed_id": MIT,
                "source_case": MIT,
                "university": "MIT",
                "verified_on": "2026-01-02",
                "programme": {
                    "status": "known",
                    "evidence": [
                        {
                            "url": f"https://{HOST}/programme",
                            "quote": QUOTE,
                            "verified_on": "2026-01-02",
                            "verified_by": "ci",
                        }
                    ],
                },
                "facts": {
                    "english": [
                        _fact("ielts.overall", f"https://{HOST}/english"),
                        _fact("ielts.subscores", f"https://{HOST}/english"),
                    ],
                    "deadline": [
                        _fact("deadline", f"https://{HOST}/gone", value="2027-01-01"),
                    ],
                    "tuition": [
                        _fact(
                            "tuition",
                            f"https://{HOST}/forbidden",
                            academic_year="2025/2026",
                            value={"amount": 1.0, "currency": "USD"},
                        ),
                        _fact("tuition", f"https://{HOST}/missing"),
                    ],
                    "gpa": [_fact("gpa", f"https://{HOST}/private/gpa")],
                    "scholarship_exists": [_fact("scholarships.x.exists", f"https://{HOST}/old")],
                    # Not an official host: checked, never verified.
                    "scholarship_international": [
                        _fact(
                            "scholarships.x.applicability.international", "https://mit.example.com/"
                        )
                    ],
                },
                "not_applicable": [
                    {
                        "question": "gpa",
                        "key": "gpa",
                        "source_url": f"https://{HOST}/english",
                        "quote": QUOTE,
                        "verified_on": "2026-01-02",
                    },
                    # No quote: nothing to check, left alone.
                    {"question": "deadline", "key": "deadline", "source_url": f"https://{HOST}/x"},
                ],
            },
            # A heldout case is never read, whatever a KB file says.
            "qs2027-999": {
                "seed_id": "qs2027-999",
                "source_case": "tum",
                "facts": {"english": [_fact("ielts.overall", "https://www.tum.de/x")]},
            },
        },
    }


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


def _handler(seen: list[str]) -> Any:
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        html = {"content-type": "text/html"}
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        if path in ("/programme", "/english"):
            return httpx.Response(200, text=PAGE, headers=html)
        if path == "/gone":
            return httpx.Response(200, text=OTHER, headers=html)
        if path == "/forbidden":
            return httpx.Response(403, text="no", headers=html)
        if path == "/old":
            return httpx.Response(301, headers={"location": f"https://{HOST}/new"})
        if path == "/new":
            return httpx.Response(200, text=OTHER, headers=html)
        return httpx.Response(404, text="not found", headers=html)

    return handle


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    real = httpx.AsyncClient

    class Mocked(real):  # type: ignore[misc, valid-type]
        def __init__(self, **kwargs: Any) -> None:
            for key in ("proxy", "verify", "trust_env"):
                kwargs.pop(key, None)
            super().__init__(transport=httpx.MockTransport(_handler(seen)), **kwargs)

    monkeypatch.setattr(fetching.httpx, "AsyncClient", Mocked)
    return seen


async def _rows(tmp_path: Path, only: set[str] | None = None) -> list[dict[str, Any]]:
    targets = verify_evidence.kb_targets(_kb(), kb="kb.json", only=only)
    async with Fetcher(tmp_path / "cache", delay_seconds=0) as fetcher:
        return await verify_evidence.check_kb_with(fetcher, targets)


# ------------------------------------------------------------ --from-kb rows


def test_from_kb_rows_cover_programme_facts_and_not_applicable():
    targets = verify_evidence.kb_targets(_kb(), kb="kb.json")
    assert [(t.source, t.item, t.key) for t in targets] == [
        ("programme", "programme", f"https://{HOST}/programme"),
        ("fact", "english", "ielts.overall"),
        ("fact", "english", "ielts.subscores"),
        ("fact", "deadline", "deadline"),
        ("fact", "tuition", "tuition"),
        ("fact", "tuition", "tuition"),
        ("fact", "gpa", "gpa"),
        ("fact", "scholarship_exists", "scholarships.x.exists"),
        ("fact", "scholarship_international", "scholarships.x.applicability.international"),
        ("not_applicable", "gpa", "gpa"),
    ]
    assert {t.case for t in targets} == {MIT}  # the heldout entry is never a row
    only = verify_evidence.kb_targets(_kb(), only={"deadline", "tuition"})
    assert [t.item for t in only] == ["deadline", "tuition", "tuition"]


def test_only_rejects_an_unknown_item():
    assert verify_evidence.parse_only("deadline, tuition") == {"deadline", "tuition"}
    assert verify_evidence.parse_only("") is None
    with pytest.raises(ValueError, match="fees"):
        verify_evidence.parse_only("fees")
    with pytest.raises(SystemExit):
        verify_evidence.main(["--only", "deadline"])


async def test_from_kb_check_reads_each_url_once_with_robots_honoured(tmp_path, site):
    rows = await _rows(tmp_path)
    by = {(r["item"], r["key"], r["url"].rsplit("/", 1)[-1]): r for r in rows}
    assert {k: classify(r) for k, r in by.items()} == {
        ("programme", f"https://{HOST}/programme", "programme"): "verified",
        ("english", "ielts.overall", "english"): "verified",
        ("english", "ielts.subscores", "english"): "verified",
        ("deadline", "deadline", "gone"): "quote_gone",
        ("tuition", "tuition", "forbidden"): "http_403",
        ("tuition", "tuition", "missing"): "http_404",
        ("gpa", "gpa", "gpa"): "robots_refused",
        ("scholarship_exists", "scholarships.x.exists", "old"): "moved",
        ("scholarship_international", "scholarships.x.applicability.international", ""): (
            "not_official"
        ),
        ("gpa", "gpa", "english"): "verified",
    }
    pages = [p for p in site if p != "/robots.txt"]
    assert pages.count("/english") == 1 and "/private/gpa" not in pages
    first = rows[0]
    assert {
        "case",
        "item",
        "url",
        "outcome",
        "status_code",
        "official",
        "quote_found",
        "checked_on",
        "seed_id",
        "key",
        "source",
        "quote",
        "final_url",
    } <= set(first)
    moved = by[("scholarship_exists", "scholarships.x.exists", "old")]
    assert moved["final_url"].endswith("/new")


def test_from_kb_cli_writes_the_report(tmp_path, monkeypatch):
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps(_kb()), encoding="utf-8")
    seen: list[str] = []

    async def fake(targets, timeout, *, trust_env_proxy=False):
        seen.extend(t.item for t in targets)
        return [{"url": t.url, "outcome": "ok"} for t in targets]

    monkeypatch.setattr(verify_evidence, "check_kb", fake)
    out = tmp_path / "report.json"
    verify_evidence.main(["--from-kb", str(kb), "--only", "deadline", "--out", str(out)])
    assert seen == ["deadline"] and len(json.loads(out.read_text())) == 1
    with pytest.raises(SystemExit):
        verify_evidence.main(["--from-kb", str(kb), "--recheck", str(out)])


# ------------------------------------------------------------------- diff


def test_classes_of_a_row():
    def row(**extra: Any) -> dict[str, Any]:
        base = {"url": "https://a.edu/x", "official": True, "quote_found": False, "outcome": "ok"}
        return {**base, **extra}

    assert classify(row(quote_found=True)) == "verified"
    assert classify(row()) == "quote_gone"
    assert classify(row(final_url="https://a.edu/y")) == "moved"
    assert classify(row(final_url="https://a.edu/x/")) == "quote_gone"  # same page
    assert classify(row(outcome="http_error", status_code=403)) == "http_403"
    assert classify(row(outcome="http_error", status_code=410)) == "http_404"
    assert classify(row(outcome="robots_disallowed")) == "robots_refused"
    assert classify(row(outcome="robots_crawl_delay")) == "robots_refused"
    unreachable = (
        "robots.txt unreachable (ConnectError); RFC 9309 treats the whole site as disallowed"
    )
    assert classify(row(outcome="robots_disallowed", note=unreachable)) == "robots_unreachable"
    assert classify(row(outcome="timeout")) == "timeout"
    assert classify(row(outcome="network_unavailable")) == "fetch_error"
    assert classify(row(official=False, quote_found=True)) == "not_official"


def test_changes_against_the_previous_checks_a_passing_row_wins():
    url = "https://a.edu/x"
    new = [
        {"case": "c", "item": "english", "url": url, "official": True, "quote_found": True},
        {"case": "c", "item": "gpa", "url": url, "official": True, "outcome": "ok"},
        {"case": "c", "item": "deadline", "url": url, "outcome": "timeout"},
        {"case": "c", "item": "tuition", "url": url, "official": True, "quote_found": True},
    ]
    previous = [
        # english: CI failed (403), the sandbox recheck passed -> verified before.
        {
            "case": "c",
            "item": "english",
            "url": url,
            "status_code": 403,
            "checked_on": "2026-10-19",
        },
        {"case": "c", "item": "english", "url": url, "official": True, "quote_found": True},
        # gpa: verified before under another case id (the (item, URL) fallback).
        {"case": "old", "item": "gpa", "url": url, "official": True, "quote_found": True},
        {"case": "c", "item": "tuition", "url": url, "status_code": 403},
    ]
    out = compare(new, previous)
    assert [(r["class"], r["change"]) for r in out] == [
        ("verified", "unchanged"),
        ("quote_gone", "lost"),
        ("timeout", "new"),
        ("verified", "newly_verified"),
    ]
    assert out[1]["previous_class"] == "verified"


async def test_queue_file_lists_redrafts_blocked_and_stale_by_university(tmp_path, site):
    rows = await _rows(tmp_path)
    report = tmp_path / "report.json"
    report.write_text(json.dumps(rows), encoding="utf-8")
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps(_kb()), encoding="utf-8")
    queue = tmp_path / "KB_REFRESH_2026-10-20.md"
    counts_path = tmp_path / "counts.json"
    args = [str(report), "--kb", str(kb), "--queue", str(queue), "--summary", str(counts_path)]
    kb_refresh_diff.main([*args, "--today", "2026-10-20"])
    counts = json.loads(counts_path.read_text())
    assert counts["classes"] == {
        "verified": 4,
        "quote_gone": 1,
        "moved": 1,
        "http_404": 1,
        "not_official": 1,
        "http_403": 1,
        "robots_refused": 1,
    }
    assert counts["changes"] == {"new": 10} and counts["redraft"] == 4 and counts["blocked"] == 2
    text = queue.read_text()
    assert text.startswith("# KB refresh queue — 2026-10-20")
    redraft = text.split("## Re-draft")[1].split("## Blocked")[0]
    blocked = text.split("## Blocked")[1].split("## Stale")[0]
    stale = text.split("## Stale in the KB")[1]
    assert redraft.count("| MIT | qs2027-001 |") == 4 and "quote_gone (ok 200)" in redraft
    assert "/new" in redraft  # where the moved page went
    assert blocked.count("| MIT |") == 2 and "http_403" in blocked and "robots_refused" in blocked
    assert "academic year 2025/2026 is past" in stale
    assert "tum" not in text


# ---------------------------------------------------------------- refresh


async def test_refresh_restamps_verified_records_and_marks_the_rest_never_altering_values(
    tmp_path, site
):
    rows = await _rows(tmp_path)
    for row in rows:
        row["checked_on"] = "2026-10-20"
    before = _kb()
    after = kb_build.refresh(before, rows, today=date(2026, 10, 20), report="r.json")
    assert before == _kb()  # the input is not mutated

    mit_before, mit = before["entries"][MIT], after["entries"][MIT]
    for question, facts in mit_before["facts"].items():
        assert [f["value"] for f in mit["facts"][question]] == [f["value"] for f in facts]
        assert [f["quote"] for f in mit["facts"][question]] == [f["quote"] for f in facts]
    english = mit["facts"]["english"]
    assert {(f["verified_on"], f["verified_by"]) for f in english} == {("2026-10-20", "ci")}
    assert all("review" not in f for f in english)
    assert mit["programme"]["evidence"][0]["verified_on"] == "2026-10-20"
    assert mit["not_applicable"][0]["verified_on"] == "2026-10-20"
    assert mit["not_applicable"][1] == mit_before["not_applicable"][1]  # nothing to check

    deadline = mit["facts"]["deadline"][0]
    assert deadline["verified_on"] == "2026-01-02"  # old date kept, value kept
    assert deadline["review"] == {
        "needed": True,
        "class": "quote_gone",
        "outcome": "ok",
        "status_code": 200,
        "checked_on": "2026-10-20",
    }
    forbidden = mit["facts"]["tuition"][0]
    assert forbidden["review"]["class"] == "http_403"
    assert forbidden["stale"] and "academic year 2025/2026 is past" in forbidden["stale_reasons"]
    assert mit["verified_on"] == "2026-10-20"
    assert {(r["question"], r["class"]) for r in after["review_queue"]} == {
        ("deadline", "quote_gone"),
        ("tuition", "http_403"),
        ("tuition", "http_404"),
        ("gpa", "robots_refused"),
        ("scholarship_exists", "moved"),
        ("scholarship_international", "not_official"),
    }
    assert after["refreshed_at"] == "2026-10-20" and after["stale_policy"]["as_of"] == "2026-10-20"
    assert after["evidence_reports"][-1] == "r.json"
    assert {s["key"] for s in after["stale_facts"]} == {"tuition"}
    # The heldout entry is untouched.
    assert after["entries"]["qs2027-999"] == before["entries"]["qs2027-999"]


def test_refresh_marks_a_sandbox_row_as_recheck_and_skips_records_not_checked():
    url = f"https://{HOST}/english"
    rows = [
        {
            "seed_id": MIT,
            "source": "fact",
            "item": "english",
            "key": "ielts.overall",
            "url": url,
            "quote": QUOTE,
            "official": True,
            "quote_found": True,
            "checked_on": "2026-10-21",
            "origin": "sandbox-proxy",
        }
    ]
    after = kb_build.refresh(_kb(), rows, today=date(2026, 10, 21))
    english = after["entries"][MIT]["facts"]["english"]
    assert (english[0]["verified_on"], english[0]["verified_by"]) == ("2026-10-21", "recheck")
    assert english[1]["verified_on"] == "2026-01-02" and "review" not in english[1]
    assert after["review_queue"] == []


def test_refresh_cli_never_overwrites_the_built_kb(tmp_path):
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps(_kb()), encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        kb_build.main(["--refresh", str(kb), "--evidence", str(report)])
    with pytest.raises(SystemExit):
        kb_build.main(["--refresh", str(kb), "--evidence", str(report), "--out", str(kb)])
    out = tmp_path / "refreshed.json"
    args = ["--refresh", str(kb), "--evidence", str(report), "--out", str(out)]
    assert kb_build.main([*args, "--built-at", "2026-10-20"]) == 0
    assert json.loads(kb.read_text()) == _kb()
    refreshed = json.loads(out.read_text())
    assert refreshed["review_queue"] == [] and refreshed["refreshed_at"] == "2026-10-20"


def test_refresh_keeps_the_builds_year_reasons_and_recomputes_the_dated_ones():
    kb = _kb()
    fact = kb["entries"][MIT]["facts"]["english"][0]
    fact.update(
        verified_on="2025-01-02",
        stale=True,
        stale_reasons=[
            "the academic year is not stated",
            "verified on 2025-01-02, more than 365 days ago",
        ],
    )
    row = {
        "seed_id": MIT,
        "source": "fact",
        "item": "english",
        "key": "ielts.overall",
        "url": fact["source_url"],
        "quote": QUOTE,
        "official": True,
        "quote_found": True,
        "checked_on": "2026-10-20",
    }
    after = kb_build.refresh(kb, [row], today=date(2026, 10, 20))
    refreshed = after["entries"][MIT]["facts"]["english"][0]
    assert refreshed["stale"] and refreshed["stale_reasons"] == ["the academic year is not stated"]
    stale = kb_refresh_diff.current_stale_reasons(fact, date(2026, 10, 20), "fall 2027")
    assert stale[0] == "the academic year is not stated" and "more than 365 days" in stale[1]


@pytest.mark.parametrize("seed_id", ["qs2027-097", "qs2027-086", "qs2027-099"])
def test_refresh_keeps_a_standing_policy_fee_with_a_date_in_its_note_current(seed_id):
    # Science Tokyo ("... on or after 2019-04-01"), Heidelberg ("since winter
    # semester 2017/18") and FU Berlin ("... WS 2026/27"): the note's year is not
    # the fee's academic year. Since the owner's 2026-10-20 "yes" (KB v17) the
    # three are standing fee policies: current with a caveat, the printed text
    # kept aside, and a refresh does not turn the note's date into a stale year.
    from app.knowledge import KB_FILE

    kb = json.loads(KB_FILE.read_text(encoding="utf-8"))
    (fee,) = kb["entries"][seed_id]["facts"]["tuition"]
    assert fee["standing_policy"] and not fee["stale"] and fee["caveat"]
    assert fee["academic_year"] is None
    for intake in ("fall 2027", "spring 2027", "fall 2028"):
        assert kb_refresh_diff.current_stale_reasons(fee, date(2026, 10, 20), intake) == []
