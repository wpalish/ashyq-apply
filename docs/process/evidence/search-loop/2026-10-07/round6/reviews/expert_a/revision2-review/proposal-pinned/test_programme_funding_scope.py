"""Independent offline regression controls for the flag, outside the repository."""

import hashlib
import importlib.util
import os
import socket
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from app.adapters import page_classifier as legacy
from app.adapters.extraction import readable_text

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import replay_classifier as replay  # noqa: E402

TARGET = os.environ.get("CLASSIFIER_REVIEW_TARGET", "proposal")
if TARGET == "legacy":
    candidate = legacy
else:
    spec = importlib.util.spec_from_file_location(
        "expert_b_classifier_test_target", BASE / "proposed_page_classifier.py"
    )
    candidate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = candidate
    spec.loader.exec_module(candidate)

CASES = replay.controls()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Real network forbidden in classifier review")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(candidate, "PROGRAMME_IDENTITY_BEFORE_FUNDING", False, raising=False)


def test_flag_starts_off():
    assert candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING is False


@pytest.mark.parametrize("name,url,html,expected", CASES, ids=[case[0] for case in CASES])
def test_flag_off_is_complete_legacy_output(name, url, html, expected):
    candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
    assert asdict(candidate.classify_page(url=url, html=html)) == asdict(
        legacy.classify_page(url=url, html=html)
    )


@pytest.mark.parametrize("name,url,html,expected", CASES, ids=[case[0] for case in CASES])
def test_enabled_semantic_controls(name, url, html, expected):
    candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
    found = candidate.classify_page(url=url, html=html)
    assert found.page_type.value == expected
    assert found.accepts("program_exists") is (expected == "program_detail")
    if expected.startswith("scholarship"):
        assert not found.accepts("requirements")


@pytest.mark.parametrize("include_text", [False, True], ids=["html_only", "original_text"])
def test_actual_retained_wits_off_on_on_off(include_text):
    raw = replay.BODY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == replay.EXPECTED_BODY_SHA
    html = raw.decode()
    text = readable_text(html) if include_text else ""
    results = []
    for enabled in (False, True, True, False):
        candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING = enabled
        results.append(asdict(candidate.classify_page(url=replay.URL, html=html, text=text)))
    assert (
        results[0]
        == results[3]
        == asdict(legacy.classify_page(url=replay.URL, html=html, text=text))
    )
    assert [r["page_type"].value for r in results] == [
        "scholarship_index",
        "program_detail",
        "program_detail",
        "scholarship_index",
    ]


@pytest.mark.asyncio
async def test_actual_requirements_reader_keeps_identity_quote_and_unknown_intake():
    html = replay.BODY.read_text()
    candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
    off = await replay.reader_replay(candidate.classify_page, html)
    candidate.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
    on = await replay.reader_replay(candidate.classify_page, html)
    assert off["claims"] == []
    assert len(on["claims"]) == 1
    evidence = on["claims"][0]
    assert evidence["claim"]["claim_type"] == "program_exists"
    assert evidence["verbatim_in_original_title"] is True
    assert evidence["excerpt_present_in_original_html"] is True
    claim = evidence["claim"]
    assert claim["normalized_value"]["language"] is None
    assert claim["scope"]["intake"] is None
    assert claim["scope"]["academic_year"] is None
    assert any("intake status is unknown" in error.lower() for error in on["result"]["errors"])
