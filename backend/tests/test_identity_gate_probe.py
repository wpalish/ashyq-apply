"""IG-2: the identity-gate probe, offline (a fake fetcher; no network, no provider).

The probe reads every development homepage through the production gate's
``_identity_branch`` with no fallback query, writes the cohort and dev2-dev4
per case and dev5 as counts only, and refuses to emit anything that names a
dev5 case. The workflow job takes its input through env, word by word (SR-05).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml  # type: ignore[import-untyped]

from app.adapters.fetching import FetchOutcome, FetchResult
from app.catalogue import discovery
from app.catalogue.importer import identity_key
from evaluation.research import identity_gate_probe as probe
from evaluation.research import live

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/benchmark-capture.yml"


class FakeFetcher:
    """Each case's homepage names the case's own university in English, unless overridden."""

    def __init__(self, overrides: dict[str, FetchResult] | None = None) -> None:
        self.overrides = overrides or {}
        self.read: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.read.append(url)
        if url in self.overrides:
            return self.overrides[url]
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR)

    async def __aenter__(self) -> FakeFetcher:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


def html_page(url: str, title: str, lang: str = "en", final: str = "") -> FetchResult:
    html = f"<html lang='{lang}'><head><title>{title}</title></head><body>x</body></html>"
    return FetchResult(url=url, outcome=FetchOutcome.OK, content=html.encode(), final_url=final)


def root(case: probe.Case) -> str:
    return f"https://{urlsplit(case.entry['homepage']).hostname}/"


def every_case_named() -> tuple[list[probe.Case], dict[str, FetchResult]]:
    cases = probe.cases_for(probe.SETS)
    pages = {
        root(c): html_page(root(c), f"{c.entry['name']} - home of the university") for c in cases
    }
    return cases, pages


@pytest.fixture(autouse=True)
def gate_defaults(monkeypatch):
    monkeypatch.setattr(discovery, "SITE_IDENTITY_V2", True)
    monkeypatch.setattr(discovery, "IDENTITY_FOLD_MARKS", False)


# --- the cases ----------------------------------------------------------------------


def test_the_sets_are_the_loop_protocols_and_no_heldout_case_is_among_them() -> None:
    assert [len(probe.SETS[s]) for s in ("cohort", "dev2", "dev3", "dev4", "dev5")] == [
        10,
        10,
        15,
        9,
        13,
    ]
    every = {case for cases in probe.SETS.values() for case in cases}
    assert not every & set(live.HELDOUT)
    assert {"dev5"} == probe.BLIND_SETS


def test_a_heldout_case_is_refused(monkeypatch) -> None:
    monkeypatch.setitem(probe.SETS, "dev2", ("ethz", "nu"))
    with pytest.raises(ValueError, match="held-out"):
        probe.cases_for(["dev2"])


def test_the_entries_are_the_benchmarks() -> None:
    by_id = {c.case_id: c for c in probe.cases_for(probe.SETS)}
    assert by_id["groningen"].entry == live.seed_entry("groningen")
    assert by_id["uppsala"].entry == live.seed_entry("uppsala")
    assert by_id["taltech"].entry == live.dev2_entry("taltech")


def test_a_cohort_row_loses_its_registry_entry_and_an_off_seed_row_is_bare() -> None:
    session = probe.catalogue_session()
    try:
        cohort = probe.bind_university(session, live.seed_entry("groningen"))
        assert cohort.registry_entry is None
        assert cohort.domain_status in {"seed", "unknown"}
        taltech = probe.bind_university(session, live.dev2_entry("taltech"))
        assert taltech.name == "Tallinn University of Technology" and not taltech.seed_snapshot
    finally:
        session.close()


# --- the verdicts --------------------------------------------------------------------


async def test_every_named_homepage_passes_and_no_query_is_sent(monkeypatch) -> None:
    def no_provider() -> None:
        raise AssertionError("the probe never asks a search provider")

    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", no_provider)
    cases, pages = every_case_named()
    fetcher = FakeFetcher(pages)
    records = await probe.measure(fetcher, cases)
    assert all(r["passed"] for r in records), [r["result"] for r in records]
    assert {r["result"] for r in records} <= set(probe.PASS_RESULTS)
    assert len(records) == 57


async def test_each_refusal_is_named() -> None:
    cases = probe.cases_for(["dev4"])
    by_id = {c.case_id: c for c in cases}
    pages = {root(c): html_page(root(c), c.entry["name"]) for c in cases}
    pages.pop(root(by_id["ctu"]))  # HTTP error
    pages[root(by_id["vut"])] = html_page(root(by_id["vut"]), "Synthetic Other University")
    pages[root(by_id["rwth"])] = html_page(
        root(by_id["rwth"]), "x", final="https://elsewhere.example/"
    )
    pages[root(by_id["kit"])] = html_page(root(by_id["kit"]), "This domain is for sale")
    # An off-seed row has no hosts of its own, so a page that names nobody proves nothing.
    pages[root(by_id["taltech"])] = html_page(root(by_id["taltech"]), "Avaleht", lang="et")
    records = {r["case"]: r for r in await probe.measure(FakeFetcher(pages), cases)}
    assert records["ctu"]["result"] == "fetch:http_error"
    assert records["vut"]["result"] == "names_other_institution"
    assert records["rwth"]["result"] == "redirect_off_site"
    assert records["kit"]["result"] == "parked"
    assert records["taltech"]["result"] == "no_branch"
    assert records["unibo"]["passed"] is True


async def test_a_third_party_homepage_is_never_read() -> None:
    session = probe.catalogue_session()
    try:
        uni = probe.bind_university(session, live.dev2_entry("taltech"))
    finally:
        session.close()
    fetcher = FakeFetcher()
    verdict = await probe.probe_case(fetcher, uni, "https://en.wikipedia.org/wiki/x")
    assert verdict["result"] == "third_party_host" and fetcher.read == []


# --- NN-1a / NN-1b ---------------------------------------------------------------------


def proposals(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "catalogue_native_names.proposed/1", "proposals": list(rows)}


def native_row(entry: dict[str, str], confidence: str, decision: str | None) -> dict[str, Any]:
    return {
        "seed_id": None,
        "identity_key": identity_key(entry["name"], entry["country"]),
        "match_confidence": confidence,
        "proposed_native_names": ["Tallinna Tehnikaülikool"],
        "review": {"decision": decision, "reviewer": None, "note": None},
    }


@pytest.mark.parametrize(
    "confidence,decision,used",
    [
        ("high", None, True),
        ("medium", None, True),
        ("low", None, False),
        ("low", "accept", True),
        ("high", "reject", False),
    ],
)
async def test_native_names_are_used_as_the_module_says(confidence, decision, used) -> None:
    (case,) = [c for c in probe.cases_for(["dev4"]) if c.case_id == "taltech"]
    native = probe.usable_native_names(proposals(native_row(case.entry, confidence, decision)))
    page = html_page(root(case), "Tallinna Tehnikaülikool", lang="et")
    (record,) = await probe.measure(FakeFetcher({root(case): page}), [case], native)
    assert record["native_name_given"] is used
    assert record["result"] == ("native_name" if used else "no_branch")


async def test_the_fold_reaches_the_gate(monkeypatch) -> None:
    (case,) = [c for c in probe.cases_for(["dev4"]) if c.case_id == "taltech"]
    row = native_row(case.entry, "high", None)
    row["proposed_native_names"] = ["Tallinna Tehnikaulikool Oslo"]
    native = probe.usable_native_names(proposals(row))
    page = html_page(root(case), "Tallinna Tehnikaulikool Øslo", lang="et")
    off = await probe.measure(FakeFetcher({root(case): page}), [case], native)
    monkeypatch.setattr(discovery, "IDENTITY_FOLD_MARKS", True)
    on = await probe.measure(FakeFetcher({root(case): page}), [case], native)
    assert (off[0]["result"], on[0]["result"]) == ("no_branch", "native_name")


# --- dev5: counts only -------------------------------------------------------------------


async def test_dev5_is_counted_and_never_named() -> None:
    cases, pages = every_case_named()
    records = await probe.measure(FakeFetcher(pages), cases)
    summary = probe.summarize(records, {"fold_letters": False, "native_names": ""})
    assert "rows" not in summary["sets"]["dev5"]
    assert summary["sets"]["dev5"]["cases"] == 13
    assert [r["case"] for r in summary["sets"]["dev4"]["rows"]] == list(probe.SETS["dev4"])
    text = json.dumps(summary, ensure_ascii=False) + probe.render(summary)
    assert probe.leak_check(text, cases) == []
    for case_id in probe.SETS["dev5"]:
        assert f"| {case_id} |" not in text and f'"{case_id}"' not in text


def test_the_leak_check_sees_a_blind_case() -> None:
    cases = probe.cases_for(["dev5"])
    one = cases[0]
    assert probe.leak_check(f"row {one.case_id} passed", cases) == ["blind_case"]
    assert probe.leak_check(f"{one.entry['name']}", cases) == ["blind_case"]
    assert probe.leak_check("dev5 passed 3/13", cases) == []


def run_main(monkeypatch, tmp_path: Path, pages: dict[str, FetchResult], *argv: str) -> int:
    fetcher = FakeFetcher(pages)
    monkeypatch.setattr(probe, "Fetcher", lambda *args, **kwargs: fetcher)
    return probe.main(
        [
            "--out",
            str(tmp_path / "report.json"),
            "--markdown",
            str(tmp_path / "tables.md"),
            *argv,
        ]
    )


def test_main_writes_the_report_and_the_tables(monkeypatch, tmp_path, capsys) -> None:
    _, pages = every_case_named()
    assert run_main(monkeypatch, tmp_path, pages, "--fold-letters") == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["config"]["fold_letters"] is True and report["config"]["fallback_query"] is False
    assert report["sets"]["dev5"]["passed"] == 13
    assert "| dev5 | 13/13 |" in capsys.readouterr().out
    assert discovery.IDENTITY_FOLD_MARKS is True  # restored by the fixture


def test_main_reads_a_native_names_file(monkeypatch, tmp_path) -> None:
    entry = live.dev2_entry("taltech")
    path = tmp_path / "catalogue_native_names.proposed.json"
    path.write_text(json.dumps(proposals(native_row(entry, "high", None))), encoding="utf-8")
    _, pages = every_case_named()
    assert run_main(monkeypatch, tmp_path, pages, "--native-names", str(path)) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["config"]["native_names"] == path.name
    assert report["sets"]["dev4"]["native_name_given"] == 1


def test_main_refuses_to_emit_a_blind_case(monkeypatch, tmp_path) -> None:
    _, pages = every_case_named()
    blind = probe.SETS["dev5"][0]
    monkeypatch.setattr(probe, "render", lambda summary: f"| {blind} | passed |\n")
    with pytest.raises(probe.LeakError):
        run_main(monkeypatch, tmp_path, pages)
    assert not (tmp_path / "report.json").exists() and not (tmp_path / "tables.md").exists()


# --- the workflow job (SR-05) -------------------------------------------------------------


def gate_step() -> str:
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["identity_gate"]
    (step,) = [s for s in job["steps"] if s.get("name") == "Probe the identity gate"]
    return step["run"]


def test_the_job_takes_its_input_through_env_and_no_secret() -> None:
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["identity_gate"]
    assert job["if"] == "inputs.mode == 'identity_gate'"
    (step,) = [s for s in job["steps"] if s.get("name") == "Probe the identity gate"]
    assert step["env"]["GATE_ARGS"] == "${{ inputs.extra_args }}"
    assert "inputs." not in step["run"]
    assert "secrets." not in yaml.safe_dump(job)
    assert job["env"]["UNIMATCH_SEARCH_PROVIDER"] == "none"


def _run_step(tmp_path: Path, gate_args: str) -> subprocess.CompletedProcess[str]:
    backend = tmp_path / "backend"
    python = backend / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        f"#!{sys.executable}\nimport json, sys\n"
        "open('calls.jsonl','a').write(json.dumps(sys.argv[1:])+'\\n')\n"
        "from pathlib import Path\n"
        "Path('../artifacts/identity-gate/tables.md').write_text('t')\n"
    )
    python.chmod(0o700)
    return subprocess.run(
        ["bash", "-c", gate_step()],
        cwd=backend,
        env={
            **os.environ,
            "GATE_ARGS": gate_args,
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        },
        capture_output=True,
        text=True,
        check=False,
    )


PROPOSED = "evaluation/research/data/catalogue_native_names.proposed.json"


@pytest.mark.parametrize(
    "gate_args,expected",
    [
        ("", []),
        ("--fold-letters", ["--fold-letters"]),
        (
            f"--fold-letters --native-names {PROPOSED}",
            ["--fold-letters", "--native-names", PROPOSED],
        ),
        (
            "--native-names app/catalogue/catalogue_native_names.signed.json",
            ["--native-names", "app/catalogue/catalogue_native_names.signed.json"],
        ),
    ],
)
def test_the_step_passes_valid_flags(tmp_path: Path, gate_args: str, expected: list[str]) -> None:
    result = _run_step(tmp_path, gate_args)
    assert result.returncode == 0, result.stdout + result.stderr
    (call,) = [
        json.loads(line) for line in (tmp_path / "backend/calls.jsonl").read_text().splitlines()
    ]
    assert call[:2] == ["-m", "evaluation.research.identity_gate_probe"]
    assert call[call.index("--markdown") + 2 :] == expected


@pytest.mark.parametrize(
    "gate_args",
    [
        "--native-names",
        "--native-names evaluation/research/data/../../../etc/passwd.json",
        "--native-names evaluation/research/data/other.json",
        "--trust-env-proxy",
        "--sets dev5",
        f"--native-names {PROPOSED} $(touch pwned)",
        'x"; touch pwned; "',
    ],
)
def test_the_step_refuses_anything_else(tmp_path: Path, gate_args: str) -> None:
    result = _run_step(tmp_path, gate_args)
    assert result.returncode != 0
    assert not (tmp_path / "backend/calls.jsonl").exists()
    assert not list(tmp_path.rglob("pwned"))
