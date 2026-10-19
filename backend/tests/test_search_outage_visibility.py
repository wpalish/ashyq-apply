"""A search-provider outage must never read as a pipeline result (2026-10-19).

Every Serper call answered HTTP 400 for hours, the case logs said only
"no reason, http 400", and eight paired runs were scored as measurements.
Synthetic data and a mock transport only: no network, no real key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters.search.base import (
    BODY_EXCERPT_CHARS,
    SearchUnavailable,
    error_body_excerpt,
    search_failure_diagnostic,
)
from app.adapters.search.serper import SerperSearchProvider
from evaluation.research import scorecard, search_preflight, stage_summary
from tests import test_stage_summary as staged
from tests.test_scorecard import DEADLINE, capture, dataset

KEY = "test-key-not-a-real-one"


def _serper(status: int, body: object) -> SerperSearchProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SerperSearchProvider(KEY, client=client)


# --- 1. the adapter keeps the status and the body, never the key -------------


async def test_a_serper_error_carries_its_status_and_a_capped_body_without_the_key():
    body = {"message": f"Not enough credits for {KEY}", "statusCode": 400, "pad": "x" * 500}
    with pytest.raises(SearchUnavailable) as caught:
        await _serper(400, body).search(query="public programme query")
    exc = caught.value
    assert exc.http_status == 400
    assert exc.body_excerpt is not None
    assert "Not enough credits" in exc.body_excerpt
    assert KEY not in exc.body_excerpt
    assert "[redacted]" in exc.body_excerpt
    assert len(exc.body_excerpt) <= BODY_EXCERPT_CHARS + 1
    # The product-facing text stays status-only, exactly as before.
    assert str(exc) == "Serper answered 400"
    assert search_failure_diagnostic("serper", exc) == (
        "Search service unavailable (serper; HTTP 400)."
    )


def test_the_key_is_masked_before_the_cap_so_no_half_key_survives():
    text = "a" * (BODY_EXCERPT_CHARS - 5) + KEY
    excerpt = error_body_excerpt(text, secrets=[KEY])
    assert KEY[:5] not in excerpt
    assert "\n" not in error_body_excerpt(b"line one\nline two")


async def test_a_healthy_answer_is_unchanged():
    response = await _serper(200, {"organic": [{"link": "https://uni.edu/cs"}]}).search(query="q")
    assert [r.url for r in response.results] == ["https://uni.edu/cs"]


# --- 2. stage_summary counts the failures ------------------------------------


def _outage_run(root: Path) -> Path:
    staged._run(root)
    for case_id in staged.IDS:
        raw_path = next((root / f"{case_id}-off").glob("*/*.raw.json"))
        raw = json.loads(raw_path.read_text())
        trace = raw["canary"]["institutions"][0]["discovery_trace"]
        trace["search_failures"] = (
            ["Search service unavailable (serper; HTTP 400)."] * 3
            if case_id == "zqalpha"
            else ["Search service unavailable (serper)."]
        )
        raw_path.write_text(json.dumps(raw))
    return root


def test_stage_summary_rows_count_failures_by_status_and_their_share(tmp_path: Path):
    run = _outage_run(tmp_path / "run")
    column = stage_summary.summarize_run(staged._dataset(), stage_summary.load_run(run))
    funnel = column["columns"]["off#1"]["discovery funnel"]
    assert funnel["search_failures"] == 4
    assert funnel["search_failures_by_status:400"] == 3
    assert funnel["search_failures_by_status:none"] == 1
    # Three answered discovery queries (one row + two rows) and four failures.
    assert funnel["discovery_queries"] == 3
    assert funnel["discovery_search_failed_share"] == round(4 / 7, 3)
    text = stage_summary.guarded_render(staged._dataset(), stage_summary.load_run(run))
    assert "| discovery_search_failed_share | 0.571 |" in text
    assert "| search_failures_by_status:400 | 3 |" in text


def test_a_run_without_failures_reports_zero(tmp_path: Path):
    run = staged._run(tmp_path / "run")
    column = stage_summary.summarize_run(staged._dataset(), stage_summary.load_run(run))
    funnel = column["columns"]["off#1"]["discovery funnel"]
    assert funnel["search_failures"] == 0
    assert funnel["discovery_search_failed_share"] == 0.0


# --- 3. the scorecard refuses to call an outage a measurement -----------------


def _scorecard_run(root: Path, *, failed_in_rep2: int) -> Path:
    for i, failed in enumerate((0, failed_in_rep2), 1):
        target = root / "uni-on" / f"20261005T00000{i}Z"
        target.mkdir(parents=True)
        (target / "capture.json").write_text(json.dumps(capture([DEADLINE], queries=5)))
        lines: list[str] = []
        for n in range(1, 6):
            if n <= failed:
                lines.append(
                    "search failed after 0.2s: SearchUnavailable "
                    "(no reason, http 400, body 'Not enough credits')"
                )
            lines.append(f"search #{n} took 0.2s (t=1s)")
        (target / "uni.log").write_text("\n".join(lines))
    return root


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    return corpus


@pytest.mark.parametrize("summary_only", [False, True])
def test_an_outage_in_any_repetition_prints_a_warning_and_fails_a_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], summary_only: bool
) -> None:
    run = _scorecard_run(tmp_path / "run", failed_in_rep2=2)
    args = [str(run), "--dataset", str(_corpus(tmp_path)), "--out", str(tmp_path / "c.json")]
    assert scorecard.main(args + (["--summary-only"] if summary_only else [])) == 0
    printed = capsys.readouterr().out
    assert "WARNING: SEARCH PROVIDER UNHEALTHY" in printed
    assert "NOT A VALID MEASUREMENT" in printed
    assert "on#2 2/5" in printed
    assert "| on | search_provider_healthy | 0.400 | <= 0.2 | NO |" in printed
    saved = json.loads((tmp_path / "c.json").read_text())
    row = next(r for r in saved["targets"] if r["metric"] == "search_provider_healthy")
    assert row["met"] is False


def test_a_healthy_run_has_no_warning_and_no_extra_target(tmp_path: Path) -> None:
    run = _scorecard_run(tmp_path / "run", failed_in_rep2=1)  # 1 of 5 = 0.2, the limit
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert [rep["search_health"]["failed"] for rep in card["arms"]["on"]["repetitions"]] == [0, 1]
    assert all(rep["search_health"]["healthy"] for rep in card["arms"]["on"]["repetitions"])
    assert "WARNING" not in scorecard.render(card)
    assert "WARNING" not in scorecard.render_summary(scorecard.summarize(card))
    assert not any(r["metric"] == "search_provider_healthy" for r in card["targets"])


def test_without_a_log_only_failures_with_a_status_count(tmp_path: Path) -> None:
    from evaluation.research.schema import Capture

    cap = Capture.model_validate(capture([DEADLINE], queries=2))
    traces: dict[str, dict[str, Any]] = {
        "uni": {
            "search_failures": [
                "Search service unavailable (serper; HTTP 400).",
                "Search service unavailable (serper).",  # a strict budget's own refusal
            ]
        }
    }
    health = scorecard.search_health(cap, traces, {})
    assert (health["calls"], health["failed"], health["healthy"]) == (2, 1, False)


# --- 4. the workflow pre-flight -----------------------------------------------


class _Provider:
    name = "serper"

    def __init__(self, error: Exception | None) -> None:
        self.error = error
        self.calls = 0

    async def search(self, *, query: str, domains: Any = (), max_results: int = 10) -> Any:
        self.calls += 1
        if self.error:
            raise self.error
        return type("R", (), {"results": ()})()


def test_the_preflight_fails_fast_with_status_and_body(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _Provider(
        SearchUnavailable("Serper answered 400", http_status=400, body_excerpt="Not enough credits")
    )
    monkeypatch.setattr(search_preflight, "get_search_provider", lambda: provider)
    assert search_preflight.main([]) == 1
    err = capsys.readouterr().err
    assert "http 400" in err
    assert "Not enough credits" in err
    assert provider.calls == 1


def test_the_preflight_passes_on_a_live_provider(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _Provider(None)
    monkeypatch.setattr(search_preflight, "get_search_provider", lambda: provider)
    assert search_preflight.main([]) == 0
    assert "pre-flight ok" in capsys.readouterr().out
    assert provider.calls == 1
