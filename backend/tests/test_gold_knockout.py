"""G-07: the gold-knockout arm, measurement only (harness wrapper, never ``Fetcher``).

Synthetic data only: a development-split corpus written to ``tmp_path`` whose
one case borrows a cohort id so ``capture_one`` accepts it; its URLs are
invented. The arm answers the gold and its forms with a counted synthetic 404
and no read; off the arm nothing changes and nothing new is serialised.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research import live, stage_summary
from evaluation.research.schema import Capture, Dataset, Observation
from scripts import canary_discovery as canary

CASE = "groningen"
GOLD = "https://www.rug.nl/bachelors/computing-science"
TWIN = "https://www.rug.nl/nl/bachelors/informatica"
SIBLING = "https://www.rug.nl/bachelors/artificial-intelligence"


def _case(case_id: str, programme_urls: list[str]) -> dict[str, Any]:
    known = bool(programme_urls)
    return {
        "id": case_id,
        "dataset_version": "synthetic-1",
        "university": "Synthetic University",
        "domain": "rug.nl",
        "country": "Nowhere",
        "site_types": [],
        "request": {"university": "Synthetic University", "degree": "bachelor"},
        "programme_urls": programme_urls,
        "programme_status": "known" if known else "unknown",
        "programme_evidence": [
            {
                "url": programme_urls[0],
                "excerpt": "Computing Science",
                "scope": {"university": "Synthetic University", "degree": "bachelor"},
                "accessed_on": "2026-10-01",
                "source_type": "official",
            }
        ]
        if known
        else [],
        "labels": [],
        "review": {
            "status": "human_verified",
            "prepared_by": "t",
            "reviewer": "r",
            "verified_on": "2026-10-01",
            "notes": "synthetic",
        },
    }


def _dataset(programme_urls: list[str], split: str = "development") -> dict[str, Any]:
    return {
        "version": "synthetic-1",
        "split": split,
        "cases": [_case(CASE, programme_urls)],
    }


def _corpus(tmp_path: Path, programme_urls: list[str], split: str = "development") -> Path:
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(_dataset(programme_urls, split)), encoding="utf-8")
    return path


class _Fetcher:
    """Answers every read itself; records which URLs reached it."""

    def __init__(self, pages: dict[str, FetchResult] | None = None) -> None:
        self.calls: list[str] = []
        self.tier_counts = {"browser": 0}
        self.pages = pages or {}

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append(url)
        if url in self.pages:
            return self.pages[url]
        return FetchResult(
            url=url, outcome=FetchOutcome.OK, status_code=200, text="<html></html>", final_url=url
        )


def _page(url: str, html: str, final_url: str | None = None) -> FetchResult:
    return FetchResult(
        url=url,
        outcome=FetchOutcome.OK,
        status_code=200,
        text=html,
        content_type="text/html",
        final_url=final_url or url,
    )


async def _capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fetcher: _Fetcher,
    urls: list[str],
    knockout: Path | None,
    max_pages: int = 40,
    strict: bool = False,
) -> tuple[Observation, list[FetchResult]]:
    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: fetcher)
    results: list[FetchResult] = []

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        wrapped = object.__new__(canary.CanaryRunner)._make_fetcher()
        for url in urls:
            results.append(await wrapped.get(url))
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / f"{CASE}.json"
    await live.capture_one(
        CASE, output, max_pages, 120, strict_expert_budget=strict, knockout_gold=knockout
    )
    return Observation.model_validate_json(output.read_text()), results


@pytest.mark.parametrize(
    "url",
    [
        GOLD,
        GOLD + "/",
        GOLD + ".html",
        GOLD + "/index.html",
        GOLD + "?lang=en",
        "http://rug.nl/bachelors/computing-science",
        "https://www.rug.nl/bachelors/2027/computing-science",
        TWIN,
    ],
)
def test_the_gold_its_variants_and_labelled_twins_are_knocked_out(url: str) -> None:
    knockout = live.GoldKnockout([GOLD, TWIN], "rug.nl")
    assert knockout.matches(url)


@pytest.mark.parametrize(
    "url", [SIBLING, GOLD + "-minor", GOLD + "?p=2", "https://www.rug.nl/bachelors"]
)
def test_a_sibling_or_another_query_is_not_knocked_out(url: str) -> None:
    assert not live.GoldKnockout([GOLD, TWIN], "rug.nl").matches(url)


@pytest.mark.asyncio
async def test_on_the_gold_is_a_counted_synthetic_404_with_no_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    get_settings.cache_clear()
    declares_twin = f'<html><head><link rel="alternate" hreflang="nl" href="{GOLD}"></head></html>'
    redirect = "https://www.rug.nl/cs"
    fetcher = _Fetcher(
        {
            "https://www.rug.nl/en/bsc-cs": _page("https://www.rug.nl/en/bsc-cs", declares_twin),
            redirect: _page(redirect, "<html></html>", final_url=GOLD + "/"),
        }
    )
    urls = [GOLD, GOLD + "/?lang=en", SIBLING, "https://www.rug.nl/en/bsc-cs", redirect]
    observation, results = await _capture(
        tmp_path, monkeypatch, fetcher, urls, _corpus(tmp_path, [GOLD]), 60, True
    )
    get_settings.cache_clear()
    # The gold forms never reach the fetcher; the twin and the redirect were
    # read (nothing announced them) and their answer is replaced.
    assert fetcher.calls == [SIBLING, "https://www.rug.nl/en/bsc-cs", redirect]
    refused = [r for r in results if r.error == live.KNOCKOUT_ERROR]
    assert len(refused) == 4
    assert all(r.status_code == 404 and not r.ok for r in refused)
    assert results[2].ok and results[2].url == SIBLING
    # Counted as reads: the page budget is spent exactly as on the off arm,
    # and nothing went on the wire.
    assert observation.telemetry.http_fetches == 5
    budget = json.loads((tmp_path / f"{CASE}.budget.json").read_text())
    assert budget["fetcher_calls"] == 5
    assert budget["network_http_requests"] == 0
    assert observation.telemetry.knockout_gold_urls == 1
    assert observation.telemetry.knockout_refused == 4


@pytest.mark.asyncio
async def test_off_nothing_is_refused_and_nothing_new_is_serialised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetcher = _Fetcher()
    observation, results = await _capture(tmp_path, monkeypatch, fetcher, [GOLD, SIBLING], None)
    assert fetcher.calls == [GOLD, SIBLING]
    assert all(r.ok for r in results)
    assert observation.telemetry.knockout_gold_urls is None
    text = (tmp_path / f"{CASE}.json").read_text()
    assert "knockout" not in text


@pytest.mark.asyncio
async def test_a_refused_read_spends_the_legacy_page_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetcher = _Fetcher()
    _, results = await _capture(
        tmp_path, monkeypatch, fetcher, [GOLD, GOLD + "/", SIBLING], _corpus(tmp_path, [GOLD]), 2
    )
    assert fetcher.calls == []
    assert results[2].outcome == FetchOutcome.BLOCKED


@pytest.mark.asyncio
async def test_a_case_without_a_programme_label_is_a_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fetcher = _Fetcher()
    observation, _ = await _capture(
        tmp_path, monkeypatch, fetcher, [GOLD, SIBLING], _corpus(tmp_path, [])
    )
    assert fetcher.calls == [GOLD, SIBLING]
    assert observation.telemetry.knockout_gold_urls == 0
    assert observation.telemetry.knockout_refused == 0
    assert "knockout: no-op" in capsys.readouterr().out


def test_the_arm_refuses_a_heldout_case_and_a_validation_corpus(tmp_path: Path) -> None:
    heldout = next(iter(live.HELDOUT))
    with pytest.raises(ValueError, match="heldout"):
        live.GoldKnockout.from_dataset(_corpus(tmp_path, [GOLD]), heldout)
    with pytest.raises(ValueError, match="development"):
        live.GoldKnockout.from_dataset(_corpus(tmp_path, [GOLD], "validation"), CASE)
    with pytest.raises(ValueError, match="not in"):
        live.GoldKnockout.from_dataset(_corpus(tmp_path, [GOLD]), "delft")


def test_the_flag_is_forwarded_to_the_child_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = _corpus(tmp_path, [GOLD])
    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["live", "--live", "--case", CASE, "--out", str(out), "--knockout-gold", str(corpus)],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands: list[list[str]] = []

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id=CASE).model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    (command,) = commands
    assert command[command.index("--knockout-gold") + 1] == str(corpus)
    capture = Capture.model_validate_json(next(out.rglob("capture.json")).read_text())
    assert capture.config["knockout_gold"] is True
    assert capture.config["knockout_dataset"] == "corpus.json"


def test_the_child_hands_the_dataset_to_capture_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = _corpus(tmp_path, [GOLD])
    seen: list[Any] = []

    async def fake_capture(*args: Any, **kwargs: Any) -> None:
        seen.append(kwargs.get("knockout_gold"))

    monkeypatch.setattr(live, "capture_one", fake_capture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            CASE,
            "--out",
            str(tmp_path / "o.json"),
            "--knockout-gold",
            str(corpus),
        ],
    )
    live.main()
    assert seen == [corpus]


def test_the_flag_refuses_a_heldout_case_at_the_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heldout = next(iter(live.HELDOUT))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            heldout,
            "--out",
            str(tmp_path),
            "--knockout-gold",
            str(_corpus(tmp_path, [GOLD])),
        ],
    )
    with pytest.raises(SystemExit):
        live.main()


def _observation(case_id: str, urls: list[str], knockout: int | None) -> dict[str, Any]:
    telemetry: dict[str, Any] = {}
    if knockout is not None:
        telemetry = {"knockout_gold_urls": knockout, "knockout_refused": 2 if knockout else 0}
    return {"case_id": case_id, "programme_urls": urls, "telemetry": telemetry}


def test_stage_summary_counts_guesses_while_the_gold_is_knocked_out() -> None:
    dataset = Dataset.model_validate(
        {
            "version": "synthetic-1",
            "split": "development",
            "cases": [
                _case("zqone", [GOLD]),
                _case("zqtwo", [GOLD]),
                _case("zqthree", []),
            ],
        }
    )

    def column(knockout: bool) -> dict[str, Any]:
        capture = Capture.model_validate(
            {
                "pipeline_sha": "abc",
                "captured_at": "20261019T000000Z",
                "mode": "synthetic",
                "config": {},
                "observations": [
                    # A sibling confirmed while the gold was unreachable: a guess.
                    _observation("zqone", [SIBLING], 1 if knockout else None),
                    # Nothing confirmed: the honest abstention.
                    _observation("zqtwo", [], 1 if knockout else None),
                    # No programme label: the arm was a no-op.
                    _observation("zqthree", [SIBLING], 0 if knockout else None),
                ],
            }
        )
        funnel: dict[str, Any] = stage_summary.repetition_summary(dataset, capture, {})[
            "discovery funnel"
        ]
        return funnel

    on = column(True)
    assert on["knockout_cases"] == 3
    assert on["knockout_cases_gold_refused"] == 2
    assert on["knockout_cases_no_gold_noop"] == 1
    assert on["knockout_reads_refused"] == 4
    assert on["knockout_guess_cases"] == 1
    assert on["knockout_guess_cases_wrong"] == 1
    assert on["knockout_guess_pages"] == 1
    assert on["knockout_guess_pages_wrong"] == 1
    assert on["knockout_abstained"] == 1
    assert on["knockout_leaked_hits"] == 0
    assert not any(row.startswith("knockout") for row in column(False))
