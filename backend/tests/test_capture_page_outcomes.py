"""EXTRA-5: a capture says why a case produced nothing, not only that it did.

Run 35697105238 filed zero claims for nine of ten universities, and the
capture could not say which of the runner's five per-page outcomes happened to
any of them — the records existed on the run and were thrown away.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.research.schema import Capture, Observation, PageOutcome

FROZEN = Path(__file__).resolve().parent.parent / "evaluation/research/baseline/capture.json"


class TestTheFrozenCaptureStillLoads:
    def test_the_certified_capture_validates_unchanged(self):
        """A schema change that breaks the certified corpus is worse than no
        diagnostic, so this is the first test, not the last."""
        capture = Capture.model_validate_json(FROZEN.read_text(encoding="utf-8"))
        assert len(capture.observations) == 10
        assert all(o.page_outcomes == [] for o in capture.observations)

    def test_an_observation_written_before_the_field_existed_is_still_valid(self):
        raw = {"case_id": "toronto", "predictions": [], "programme_urls": []}
        assert Observation.model_validate(raw).page_outcomes == []


class TestWhatAPageOutcomeRecords:
    def test_it_keeps_the_runner_s_own_vocabulary(self):
        outcome = PageOutcome(
            category="classifier-rejected",
            url="https://example.edu/open-day",
            page_type="news",
            detail="not a programme page",
            characters=1200,
        )
        back = PageOutcome.model_validate_json(outcome.model_dump_json())
        assert back.category == "classifier-rejected"
        assert back.characters == 1200

    def test_a_page_with_no_character_count_is_not_recorded_as_zero(self):
        """A page that was never read has no length; zero would be a claim."""
        assert PageOutcome(category="fetch-failed", url="https://example.edu/x").characters is None

    def test_a_negative_length_is_refused(self):
        with pytest.raises(ValidationError):
            PageOutcome(category="unreadable", url="https://example.edu/x", characters=-1)


def test_a_capture_carrying_outcomes_round_trips():
    observation = Observation(
        case_id="toronto",
        page_outcomes=[
            PageOutcome(category="no-pattern-match", url="https://example.edu/a"),
            PageOutcome(category="fetched-ok", url="https://example.edu/b"),
        ],
    )
    payload = json.loads(observation.model_dump_json())
    assert [o["category"] for o in payload["page_outcomes"]] == [
        "no-pattern-match",
        "fetched-ok",
    ]
    assert Observation.model_validate(payload).page_outcomes[0].url == "https://example.edu/a"
