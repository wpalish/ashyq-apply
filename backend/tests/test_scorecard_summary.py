"""``scorecard --summary-only``: aggregates only, for the heldout look (finish-algorithm ticket 19).

Synthetic data only. The summary must carry no case id, URL, university, claim
value or gold value, in stdout or in the ``--out`` JSON, and its numbers must
equal the full scorecard's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.research import scorecard
from evaluation.research.schema import Dataset
from tests.test_scorecard import DEADLINE, TOEFL, TUITION_RIGHT, TUITION_WRONG, capture, dataset

CASES = {"zqalpha": "zqalpha-uni.example", "zqbeta": "zqbeta-uni.example"}
UNIVERSITIES = {"zqalpha": "Zqalpha Institute", "zqbeta": "Zqbeta Institute"}
# Values that are per-case data: gold values and claimed values of the synthetic corpus.
VALUES = ["2027-05-01", "Deadline 1 May 2027", "EUR 100 per year", "EUR 200 per year", "TOEFL iBT"]


def _rename(blob: Any, case_id: str) -> Any:
    text = json.dumps(blob)
    text = text.replace("uni.edu", CASES[case_id]).replace('"uni"', f'"{case_id}"')
    return json.loads(text.replace("Example University", UNIVERSITIES[case_id]))


def _dataset() -> Dataset:
    one = dataset().model_dump(mode="json")
    one["cases"] = [_rename(one["cases"][0], case_id) for case_id in CASES]
    return Dataset.model_validate(one)


def _raw(access: str, checked: int, failed: int) -> dict[str, Any]:
    inst = {"access": access, "pages_checked": checked, "pages_failed": failed}
    return {"canary": {"institutions": [inst]}}


def _run(root: Path) -> Path:
    """Two arms × two repetitions; zqbeta is refused in the on arm's first repetition."""
    plan: dict[tuple[str, str], list[list[dict[str, Any]]]] = {
        ("off", "zqalpha"): [[DEADLINE, TUITION_RIGHT], [DEADLINE]],
        ("off", "zqbeta"): [[TUITION_WRONG], []],
        ("on", "zqalpha"): [[DEADLINE, TUITION_RIGHT, TOEFL], [DEADLINE, TUITION_RIGHT]],
        ("on", "zqbeta"): [[DEADLINE], [DEADLINE, TUITION_WRONG]],
    }
    for (arm, case_id), reps in plan.items():
        for i, predictions in enumerate(reps, 1):
            target = root / f"{case_id}-{arm}" / f"20261005T00000{i}Z"
            target.mkdir(parents=True)
            cap = _rename(capture(predictions, queries=3 + i), case_id)
            if (arm, case_id, i) == ("off", "zqbeta", 2):
                cap["observations"][0]["programme_urls"] = [f"https://{CASES[case_id]}/law"]
            (target / "capture.json").write_text(json.dumps(cap))
            blocked = (arm, case_id, i) == ("on", "zqbeta", 1)
            raw = _raw("BLOCKED", 6, 6) if blocked else _raw("REACHED", 20, 1)
            (target / f"{case_id}.raw.json").write_text(json.dumps(raw))
            if i == 2:
                # Every request to the site failed in this repetition.
                log = [
                    f"get #1 start t=0s https://{CASES[case_id]}/fees",
                    "get #1 took 0.2s timeout",
                ]
                (target / f"{case_id}.log").write_text("\n".join(log))
    return root


@pytest.fixture()
def paths(tmp_path: Path) -> dict[str, Path]:
    run = _run(tmp_path / "run")
    corpus = tmp_path / "corpus.json"
    corpus.write_text(_dataset().model_dump_json())
    return {"run": run, "corpus": corpus, "tmp": tmp_path}


def _main(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str], *flags: str
) -> tuple[str, str]:
    out = paths["tmp"] / ("summary.json" if flags else "card.json")
    args = [str(paths["run"]), "--dataset", str(paths["corpus"]), "--out", str(out), *flags]
    assert scorecard.main(args) == 0
    return capsys.readouterr().out, out.read_text(encoding="utf-8")


def _forbidden() -> list[str]:
    urls = [str(u) for case in _dataset().cases for u in case.programme_urls]
    evidence = [
        str(e.url) for case in _dataset().cases for label in case.labels for e in label.evidence
    ]
    return [*CASES, *CASES.values(), *UNIVERSITIES.values(), *urls, *evidence, *VALUES]


def test_the_full_scorecard_carries_the_per_case_data(paths, capsys) -> None:
    """The guard below is meaningful: normal mode does show what summary mode hides."""
    stdout, written = _main(paths, capsys)
    for needle in ["zqalpha", "zqbeta", "zqalpha-uni.example", "EUR"]:
        assert needle in stdout + written


def test_summary_only_leaks_no_case_id_url_or_value(paths, capsys) -> None:
    stdout, written = _main(paths, capsys, "--summary-only")
    for needle in _forbidden():
        assert needle not in stdout, needle
        assert needle not in written, needle
    for marker in ("http", "://", "## Per case", "## Wrong claims", ":deadline", ":tuition"):
        assert marker not in stdout + written, marker
    assert json.loads(written)["summary_only"] is True


def test_summary_numbers_equal_the_full_scorecard(paths, capsys) -> None:
    _, full_text = _main(paths, capsys)
    _, summary_text = _main(paths, capsys, "--summary-only")
    full, summary = json.loads(full_text), json.loads(summary_text)
    assert summary["targets"] == full["targets"]
    assert summary["changes"] == {k: len(v) for k, v in full["changes"].items()}
    assert sum(summary["changes"].values()) > 0
    assert list(summary["arms"]) == list(full["arms"]) == ["off", "on"]
    for name, arm in full["arms"].items():
        for rep, short in zip(
            arm["repetitions"], summary["arms"][name]["repetitions"], strict=True
        ):
            assert short["metrics"] == rep["metrics"]
            readable = {k: v for k, v in rep["readable"].items() if k != "excluded"}
            assert short["readable"] == readable
            assert short["excluded_cases"] == len(rep["readable"]["excluded"])
            assert short["wrong_claims"] == len(rep["outcomes"]["wrong_claims"])
            assert short["cases_scored"] == len(rep["cost"]) == 2
    on = summary["arms"]["on"]["repetitions"]
    assert [r["unavailable_cases"] for r in on] == [1, 0]
    # Repetition 2's host failed every request: both known core questions of both cases left.
    assert on[1]["excluded_core_questions"] == {"host_failed": 4}
    assert on[0]["excluded_core_questions"] == {}
    assert summary["arms"]["off"]["repetitions"][1]["readable"]["wrong_programme_pages"] == 1


def test_summary_rows_match_the_full_render(paths, capsys) -> None:
    """Every aggregate row the full card prints reads the same in the summary."""
    full_out, _ = _main(paths, capsys)
    summary_out, _ = _main(paths, capsys, "--summary-only")
    full_lines, summary_lines = full_out.splitlines(), summary_out.splitlines()
    shared = [
        line
        for line in full_lines
        if line.startswith("| ") and not line.startswith(("| zq", "| case "))
    ]
    assert shared
    for line in shared:
        assert line in summary_lines, line
    assert "**Stable gains**: " in summary_out


def test_normal_mode_prints_exactly_the_full_render(paths, capsys) -> None:
    """Without the flag, stdout and ``--out`` are the unchanged full scorecard."""
    stdout, written = _main(paths, capsys)
    card = scorecard.build(_dataset(), scorecard.load_run(paths["run"]))
    assert stdout == scorecard.render(card)
    assert written == json.dumps(card, ensure_ascii=False, indent=1, default=str)
    assert "summary_only" not in written
