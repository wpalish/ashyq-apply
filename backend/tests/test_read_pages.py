"""scripts/read_pages.py: official pages read on the CI runner for KB drafting.

No network: the fetcher is either a recording fake or the production
``Fetcher`` over an ``httpx.MockTransport`` with DNS fixed to a public address.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

from app.adapters import fetching
from app.adapters.fetching import USER_AGENT, FetchResult
from app.domain.enums import FetchOutcome
from scripts import read_pages, verify_evidence
from scripts.read_pages import Row
from tests.test_verify_evidence import CASE, DISALLOW_ALL, HOST, _resolve_public, _Site

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/benchmark-capture.yml"
BLOCKED_LIST = "evaluation/research/expert/data/read_pages/blocked-2026-10-20.json"
#: Every list committed under read_pages/ (RP-1's self-hosted list among them).
COMMITTED_LISTS = sorted(
    p.relative_to(read_pages.BACKEND).as_posix()
    for p in (read_pages.DATA_DIR / "read_pages").glob("*.json")
)


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _resolve_public)


@pytest.fixture(autouse=True)
def _no_pacing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fetcher's pacing clock: sleeping only advances it."""
    now = [1000.0]

    async def sleep(seconds: float) -> None:
        now[0] += seconds

    monkeypatch.setattr(fetching, "_clock", lambda: now[0])
    monkeypatch.setattr(fetching, "_sleep", sleep)


class FakeFetcher:
    """Answers every URL with one HTML page and records what it was asked."""

    def __init__(self, html: str = "<html><body><main><p>Fees</p></main></body></html>") -> None:
        self.html = html
        self.asked: list[str] = []

    async def get(self, url: str, use_cache: bool = True) -> FetchResult:
        assert use_cache is False
        self.asked.append(url)
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            text=self.html,
            content_type="text/html",
            final_url=url,
        )


# ------------------------------------------------------------------ the list


@pytest.mark.parametrize(
    "path",
    [
        "evaluation/research/expert/data/../../../app/config.json",
        "evaluation/research/expert/data/read_pages/../x.json",
        "evaluation/research/expert/data/.hidden.json",
        "evaluation/research/data/kb_top100_list.json",
        "evaluation/research/expert/data/read_pages/list.py",
        "/etc/passwd.json",
        "evaluation/research/expert/data/a b.json",
        "evaluation/research/expert/data/x.json\n--out /tmp",
    ],
)
def test_a_list_outside_the_data_dir_is_refused(path: str) -> None:
    with pytest.raises(ValueError):
        read_pages.resolve_list(path)


def test_the_committed_lists_include_the_self_hosted_one() -> None:
    assert BLOCKED_LIST in COMMITTED_LISTS
    assert (
        "evaluation/research/expert/data/read_pages/self-hosted-2026-10-21.json" in COMMITTED_LISTS
    )


@pytest.mark.parametrize("listed", COMMITTED_LISTS)
def test_the_committed_list_resolves_and_parses(listed: str) -> None:
    path = read_pages.resolve_list(listed)
    assert path.is_relative_to(read_pages.DATA_DIR)
    rows = read_pages.parse_rows(path)
    assert 0 < len(rows) <= read_pages.MAX_ROWS
    assert len({r.url for r in rows}) == len(rows)
    # Every committed URL is official for its seed and no heldout case is listed.
    assert [r for r in rows if not read_pages.is_official(r)] == []
    assert [r for r in rows if read_pages.heldout(r.seed_id)] == []


def test_json_and_text_lists_parse_and_deduplicate(tmp_path: Path) -> None:
    url = f"https://{HOST}/admissions"
    (tmp_path / "a.json").write_text(
        json.dumps({"rows": [{"seed_id": CASE, "url": url}, {"seed_id": CASE, "url": url}]})
    )
    (tmp_path / "a.txt").write_text(f"# reading list\n{CASE} {url}  # fees\n\n{CASE} {url}\n")
    assert read_pages.parse_rows(tmp_path / "a.json") == [Row(CASE, url)]
    assert read_pages.parse_rows(tmp_path / "a.txt") == [Row(CASE, url)]


@pytest.mark.parametrize(
    "rows",
    [
        [{"seed_id": CASE, "url": "ftp://www.mit.edu/x"}],
        [{"seed_id": "../x", "url": "https://www.mit.edu/"}],
        [{"url": "https://www.mit.edu/"}],
        ["https://www.mit.edu/"],
    ],
)
def test_a_malformed_row_is_an_error(tmp_path: Path, rows: list[Any]) -> None:
    (tmp_path / "bad.json").write_text(json.dumps(rows))
    with pytest.raises(ValueError):
        read_pages.parse_rows(tmp_path / "bad.json")


def test_a_list_longer_than_the_cap_is_refused(tmp_path: Path) -> None:
    rows = [{"seed_id": CASE, "url": f"https://{HOST}/{i}"} for i in range(301)]
    (tmp_path / "long.json").write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="more than 300"):
        read_pages.parse_rows(tmp_path / "long.json")


# ------------------------------------------------------------ what is read


async def test_a_non_official_host_is_never_handed_to_the_fetcher() -> None:
    fetcher = FakeFetcher()
    rows = [
        Row(CASE, f"https://{HOST}/admissions"),
        Row(CASE, "https://www.topuniversities.com/mit"),
        Row(CASE, "https://mit.edu.evil.example/fees"),
        Row("no-such-seed", f"https://{HOST}/fees"),
    ]
    out = await read_pages.read_with(fetcher, rows)  # type: ignore[arg-type]
    assert fetcher.asked == [f"https://{HOST}/admissions"]
    assert [r["status"] for r in out] == ["ok", "not_read", "not_read", "not_read"]
    assert [r["official"] for r in out] == [True, False, False, False]
    assert all("not an official domain" in r["note"] for r in out[1:])
    assert all(r["text"] == "" and r["robots"] == "not_read" for r in out[1:])


async def test_a_heldout_case_is_never_read() -> None:
    fetcher = FakeFetcher()
    held = sorted(verify_evidence.HELDOUT_CASES)[0]
    domain = verify_evidence.OFFICIAL_DOMAINS[held][0]
    out = await read_pages.read_with(fetcher, [Row(held, f"https://www.{domain}/")])  # type: ignore[arg-type]
    assert fetcher.asked == []
    assert out[0]["status"] == "not_read" and "heldout" in out[0]["note"]


async def test_text_is_capped_but_counted_and_hashed_in_full() -> None:
    body = "Tuition fee for international students. " * 50
    fetcher = FakeFetcher(f"<html><body><main><p>{body}</p></main></body></html>")
    (out,) = await read_pages.read_with(
        fetcher,  # type: ignore[arg-type]
        [Row(CASE, f"https://{HOST}/fees")],
        max_chars=100,
    )
    full = verify_evidence.page_text(await fetcher.get(f"https://{HOST}/fees", use_cache=False))
    assert out["chars"] == len(full) > 100
    assert out["text"] == full[:100] and out["truncated"] is True
    assert out["sha256"] == hashlib.sha256(full.encode()).hexdigest()
    assert out["robots"] == "allowed" and out["final_url"] == f"https://{HOST}/fees"


async def test_a_pdf_goes_through_the_pdf_extractor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify_evidence, "pdf_to_text", lambda data: f"PDF:{data.decode()}")

    class PdfFetcher(FakeFetcher):
        async def get(self, url: str, use_cache: bool = True) -> FetchResult:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                content=b"guide",
                content_type="application/pdf",
                final_url=url,
            )

    (out,) = await read_pages.read_with(PdfFetcher(), [Row(CASE, f"https://{HOST}/g.pdf")])  # type: ignore[arg-type]
    assert out["text"] == "PDF:guide" and out["content_type"] == "application/pdf"


# ------------------------------------------------- robots.txt and its override


async def test_robots_disallow_is_honoured_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    site = _Site(DISALLOW_ALL)
    site.install(monkeypatch)
    (out,) = await read_pages.read([Row(CASE, f"https://{HOST}/admissions")], 5.0)
    assert out["status"] == "robots_disallowed" and out["robots"] == "disallowed"
    assert out["text"] == "" and "robots_override" not in out
    assert site.page_requests() == []


async def test_override_rereads_only_official_refused_urls_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site = _Site(DISALLOW_ALL)
    site.install(monkeypatch)
    rows = [
        Row(CASE, f"https://{HOST}/admissions"),
        Row(CASE, "https://www.example.org/admissions"),
    ]
    official, other = await read_pages.read(rows, 5.0, robots_override_kb=True)
    assert official["status"] == "ok" and official["robots"] == "overridden"
    assert official["robots_override"] is True and official["robots_override_used"] is True
    assert "IELTS 7.0" in official["text"]
    assert other["status"] == "not_read" and "robots_override" not in other
    # One page request, to the official URL, under our own user agent.
    pages = site.page_requests()
    assert [(r.headers["host"], r.url.path) for r in pages] == [(HOST, "/admissions")]
    assert {r.headers["user-agent"] for r in site.requests} == {USER_AGENT}


async def test_override_leaves_an_allowed_page_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    site = _Site("User-agent: *\nAllow: /\n")
    site.install(monkeypatch)
    (out,) = await read_pages.read(
        [Row(CASE, f"https://{HOST}/admissions")], 5.0, robots_override_kb=True
    )
    assert out["robots"] == "allowed" and "robots_override" not in out
    assert len(site.page_requests()) == 1


def test_main_writes_records_and_an_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    site = _Site("User-agent: *\nAllow: /\n")
    site.install(monkeypatch)
    monkeypatch.setattr(
        read_pages, "parse_rows", lambda _path: [Row(CASE, f"https://{HOST}/admissions")]
    )
    read_pages.main([BLOCKED_LIST, "--out", str(tmp_path / "out")])
    (rec,) = [json.loads(line) for line in (tmp_path / "out/pages.jsonl").read_text().splitlines()]
    assert set(rec) >= {"url", "final_url", "status", "robots", "chars", "sha256", "text"}
    index = (tmp_path / "out/index.tsv").read_text().splitlines()
    assert index[0].split("\t")[:2] == ["seed_id", "status"] and len(index) == 2


def test_main_refuses_a_path_outside_the_data_dir(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        read_pages.main(["../app/config.json", "--out", str(tmp_path)])


# -------------------------------------------------------------- the workflow


def _read_step() -> str:
    text = WORKFLOW.read_text()
    name = "Read the listed pages with the production fetcher"
    section = text.split(f"      - name: {name}\n", 1)[1].split("      - ", 1)[0]
    script = section.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] for line in script.splitlines()) + "\n"


def _run_step(tmp_path: Path, read_args: str) -> subprocess.CompletedProcess[str]:
    """The step's shell in ``tmp_path/backend`` with a recording python."""
    backend = tmp_path / "backend"
    python = backend / ".venv/bin/python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text(
        f"#!{sys.executable}\nimport json, sys\n"
        "open('calls.jsonl','a').write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    python.chmod(0o700)
    return subprocess.run(
        ["bash", "-c", _read_step()],
        cwd=backend,
        env={**os.environ, "READ_ARGS": read_args},
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_read_pages_job_takes_its_input_through_env() -> None:
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["read_pages"]
    assert job["if"] == "inputs.mode == 'read_pages'"
    (step,) = [s for s in job["steps"] if s.get("name", "").startswith("Read the listed")]
    assert step["env"]["READ_ARGS"] == "${{ inputs.extra_args }}"
    assert "inputs." not in step["run"]
    # No secret reaches this job.
    assert "secrets." not in yaml.safe_dump(job)


@pytest.mark.parametrize(
    ("read_args", "expected"),
    [
        (BLOCKED_LIST, [BLOCKED_LIST]),
        (f"{BLOCKED_LIST} --robots-override-kb", [BLOCKED_LIST, "--robots-override-kb"]),
    ],
)
def test_the_step_passes_a_valid_list(tmp_path: Path, read_args: str, expected: list[str]) -> None:
    result = _run_step(tmp_path, read_args)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (tmp_path / "backend/calls.jsonl").read_text().splitlines()
    (call,) = [json.loads(line) for line in calls]
    assert call[0] == "scripts/read_pages.py" and call[1] == expected[0]
    assert call[2:4] == ["--out", "../artifacts/read-pages"]
    assert call[4:] == expected[1:]


@pytest.mark.parametrize(
    "read_args",
    [
        "",
        "evaluation/research/expert/data/../../../app/x.json",
        "app/knowledge/kb_cs_bachelor.json",
        'x.json"; touch pwned; "',
        "evaluation/research/expert/data/a.json $(touch pwned)",
        f"{BLOCKED_LIST} --trust-env-proxy",
        f"{BLOCKED_LIST} --robots-override-kb extra",
    ],
)
def test_the_step_refuses_anything_else(tmp_path: Path, read_args: str) -> None:
    result = _run_step(tmp_path, read_args)
    assert result.returncode != 0
    assert not (tmp_path / "backend/calls.jsonl").exists()
    assert not list(tmp_path.rglob("pwned"))


def test_the_workflow_pattern_is_the_scripts_pattern() -> None:
    assert read_pages.LIST_PATH.pattern in WORKFLOW.read_text()
