"""The verified knowledge base: build, merge, staleness, and the kb research mode.

Owner decision 2026-10-19: live search frozen; a CS bachelor is answered from
the KB. Every URL and quote below is synthetic test data.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.catalogue.importer import import_catalogue
from app.catalogue.retrieval import retrieve
from app.config import Settings
from app.db import create_all_for_tests
from app.domain.enums import ClaimStatus, ClaimType
from app.knowledge import load_knowledge_base, review_label, stale_reasons
from app.knowledge.claims import answer
from app.models import ClaimRow, ProgramResultRow, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from evaluation.research.expert import kb_build
from tests.conftest import profile_row

MIT = "qs2027-001"
URL = "https://www.mit.edu/admissions/synthetic"


def _fact(key: str, value: Any, quote: str, **extra: Any) -> dict[str, Any]:
    return {
        "key": key,
        "value": value,
        "period": None,
        "academic_year": None,
        "population": None,
        "source_url": URL,
        "quote": quote,
        "source_type": "official",
        "accessed_on": "2026-10-19",
        "verified_on": "2026-10-19",
        **extra,
    }


def _kb(path: Path, entries: dict[str, Any], version: str = "test.kb") -> Path:
    path.write_text(
        json.dumps(
            {
                "format": "kb-cs-bachelor/1",
                "version": version,
                "built_at": "2026-10-19",
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    return path


def _mit_entry(**facts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "seed_id": MIT,
        "review_status": "expert_checked",
        "verified_on": "2026-10-19",
        "university": "Massachusetts Institute of Technology (MIT)",
        "country": "United States of America",
        "official_domain": "mit.edu",
        "programme": {
            "status": "known",
            "urls": [URL],
            "evidence": [
                {
                    "url": URL,
                    "quote": "Bachelor of Science in Computer Science",
                    "accessed_on": "2026-10-19",
                    "verified_on": "2026-10-19",
                }
            ],
        },
        "facts": facts,
    }


# ------------------------------------------------------------------ converter


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _batch(root: Path) -> None:
    _write(
        root / "batch1/programme" / f"{MIT}.0-local.json",
        {"case": MIT, "programme": {"url": URL, "title": "Computer Science BSc"}, "answers": {}},
    )
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "english": {
                    "status": "known",
                    "value": {"ielts_overall": 7.0},
                    "url": URL,
                    "quote": "IELTS 7.0 overall",
                },
                "deadline": {
                    "status": "known",
                    "value": "2027-01-05",
                    "url": "https://elsewhere.example/deadline",
                    "quote": "Apply by 5 January 2027",
                },
            },
        },
    )


def _report(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _row(item: str, url: str, official: bool = True, found: bool = True) -> dict[str, Any]:
    return {
        "case": MIT,
        "item": item,
        "url": url,
        "outcome": "ok",
        "official": official,
        "quote_found": found,
    }


def test_converter_marks_known_only_what_the_ci_check_found(tmp_path):
    _batch(tmp_path / "drafts")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [
            _row("programme", URL),
            _row("english", URL),
            _row("deadline", "https://elsewhere.example/deadline", official=False),
        ],
    )
    data = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")
    assert data["version"] and data["built_at"] == "2026-10-21"
    entry = data["entries"][MIT]
    assert entry["programme"]["status"] == "known"
    english = entry["facts"]["english"]
    assert [f["key"] for f in english] == ["ielts.overall"]
    fact = english[0]
    assert fact["value"] == 7.0 and fact["quote"] == "IELTS 7.0 overall"
    assert fact["source_url"] == URL and fact["unit"] == "IELTS band"
    assert fact["accessed_on"] == "2026-10-19"
    assert fact["verified_on"] == "2026-10-20"  # the date of the CI check (report name)
    assert {"period", "academic_year", "population"} <= set(fact)
    assert entry["facts"]["deadline"] == []
    deadline = next(u for u in entry["unknown"] if u["key"] == "deadline")
    assert "not an official domain" in deadline["reason"]


NONE_URL = "https://www.mit.edu/finaid/synthetic-none"
NONE_QUOTE = "We do not offer any scholarships for bachelor's studies."


def _none_batch(root: Path, **exists: Any) -> None:
    """A core draft whose expert found no institutional scholarship (KTH, FU Berlin, ...)."""
    none = {"status": "not_applicable", "url": NONE_URL, "quote": NONE_QUOTE, **exists}
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "scholarship_exists": {**none, "notes": "Scholarships are for master's only."},
                "scholarship_international": {**none, "notes": "None, so none for internationals."},
            },
        },
    )


def test_converter_writes_a_verified_no_scholarship_statement(tmp_path):
    from app.knowledge.claims import none_offered_rows

    _none_batch(tmp_path / "drafts")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [_row("scholarship_exists", NONE_URL), _row("scholarship_international", NONE_URL)],
    )
    data = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")
    entry = data["entries"][MIT]
    [none] = entry["not_applicable"]
    assert none == {
        "question": "scholarship_exists",
        "key": "scholarships",
        "reason": "No institutional scholarship for incoming bachelor applicants. "
        "Expert (2026-10-19): Scholarships are for master's only.",
        "source_url": NONE_URL,
        "quote": NONE_QUOTE,
        "verified_on": "2026-10-20",
        "verified_by": "ci",
    }
    assert entry["facts"]["scholarship_exists"] == []
    assert entry["facts"]["scholarship_international"] == []
    assert not [u for u in entry["unknown"] if u["question"].startswith("scholarship")]
    # The loader and the runtime read it as the explicit "none offered" statement.
    kb = load_knowledge_base(_kb(tmp_path / "kb.json", data["entries"]), tmp_path / "none.json")
    assert [r["quote"] for r in none_offered_rows(kb.entries[MIT])] == [NONE_QUOTE]
    claims = answer(
        kb.entries[MIT],
        programme="Computer Science",
        intake="fall 2027",
        academic_year="2027/28",
        today=date(2026, 10, 21),
    ).claims
    [claim] = [c for c in claims if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS]
    assert claim.normalized_value is False and claim.status is ClaimStatus.VERIFIED_CURRENT


def test_converter_keeps_an_unverified_no_scholarship_statement_unknown(tmp_path):
    _none_batch(tmp_path / "drafts")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [_row("scholarship_exists", NONE_URL, found=False)],
    )
    for reports in ([report], []):
        entry = kb_build.build(tmp_path / "drafts", reports, built_at="2026-10-21")["entries"][MIT]
        assert entry["not_applicable"] == []
        [unknown] = [u for u in entry["unknown"] if u["question"].startswith("scholarship")]
        assert unknown["key"] == "scholarships"
        assert unknown["reason"].startswith("expert value not_applicable unverified")


def test_converter_without_a_quote_writes_no_no_scholarship_statement(tmp_path):
    _none_batch(tmp_path / "drafts", quote="")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json", [_row("scholarship_exists", NONE_URL)]
    )
    entry = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")["entries"][MIT]
    assert entry["not_applicable"] == []
    [unknown] = [u for u in entry["unknown"] if u["question"].startswith("scholarship")]
    assert "no scholarship keys written" in unknown["reason"]


def test_dataset_converters_still_write_no_scholarship_keys_for_none():
    """``none_statement`` is the KB builder's; dev4/dev5 datasets are unchanged."""
    from evaluation.research.expert import core_drafts
    from evaluation.research.identities import IdentityMap

    none = {"status": "not_applicable", "url": NONE_URL, "quote": NONE_QUOTE}
    ev = core_drafts.evidence(NONE_URL, NONE_QUOTE, {}, "2026-10-19")
    ids = IdentityMap(version="t", bindings=[])
    ex_p, in_p, binding, note = core_drafts.propose_scholarship(none, none, ev, ev, "mit.edu", ids)
    assert (ex_p, in_p, binding) == ([], [], None)
    assert note.endswith("no scholarship keys written.")
    draft = {"case": MIT, "answers": {"scholarship_exists": none}}
    report = {(MIT, "scholarship_exists"): _row("scholarship_exists", NONE_URL)}
    items, _b, _n = core_drafts.items_for(draft, {}, "mit.edu", ids, report)
    assert not [i for i in items if i.question == "scholarship"]
    kb_items, _b, kb_note = core_drafts.items_for(
        draft, {}, "mit.edu", ids, report, none_statement=True
    )
    [item] = [i for i in kb_items if i.question == "scholarship"]
    assert [(p.key, p.status) for p in item.proposals] == [("scholarships", "not_applicable")]
    assert kb_note == ""


def test_converter_keeps_a_past_year_fee_as_stale_with_its_period(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch2/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "tuition": {
                    "status": "known",
                    "value": {
                        "amount": 555000,
                        "currency": "SEK",
                        "academic_year": "2026/27",
                        "period": "programme (total, 3 years)",
                    },
                    "url": URL,
                    "quote": "Total programme price 555 000 kr (2026/27)",
                },
            },
        },
    )
    rows = [_row("tuition", URL)]
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", rows)
    container = _report(tmp_path / "evidence_check.container-2026-10-19.json", rows)
    assert (
        kb_build.build(root, [container], built_at="2026-10-19")["entries"][MIT]["facts"]["tuition"]
        == []
    )  # a container pre-check is not the CI evidence check
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    (fee,) = entry["facts"]["tuition"]
    assert fee["value"] == {"amount": 555000.0, "currency": "SEK"}
    assert fee["period"] == "programme (total, 3 years)" and fee["academic_year"] == "2026/27"
    assert fee["stale"] and any("2026/27" in r for r in fee["stale_reasons"])
    assert not any(u["key"] == "tuition" for u in entry["unknown"])


def test_converter_takes_a_calendar_year_fee_for_the_same_year_intake_as_current(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch2/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "tuition": {
                    "status": "known",
                    "value": {"amount": 52000, "currency": "AUD", "academic_year": "2027"},
                    "url": URL,
                    "quote": "2027 annual tuition fee AUD 52,000",
                },
            },
        },
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    (fee,) = entry["facts"]["tuition"]
    assert fee["academic_year"] == "2027" and not fee["stale"]


def test_converter_without_evidence_knows_nothing(tmp_path):
    _batch(tmp_path / "drafts")
    data = kb_build.build(tmp_path / "drafts", [], built_at="2026-10-21")
    entry = data["entries"][MIT]
    assert entry["known_fact_count"] == 0
    assert entry["programme"]["status"] == "unknown"
    assert all("unverified" in u["reason"] or "did not" in u["reason"] for u in entry["unknown"])


def test_converter_takes_recheck_reports_and_a_passing_row_wins(tmp_path):
    _batch(tmp_path / "drafts")
    deadline_url = "https://elsewhere.example/deadline"
    ci = _report(
        tmp_path / "evidence_check.ci-2026-10-19.json",
        [
            _row("programme", URL),
            {**_row("english", URL, found=False), "outcome": "http_error", "status_code": 403},
            _row("deadline", deadline_url, official=False),
        ],
    )
    recheck = _report(
        tmp_path / "evidence_check.recheck-2026-10-20.json",
        [
            # CI passed the programme page; a failed recheck does not undo it.
            {**_row("programme", URL, found=False), "origin": "sandbox-proxy"},
            {**_row("english", URL), "origin": "sandbox-proxy", "checked_on": "2026-10-20"},
            {**_row("deadline", deadline_url, official=False), "origin": "sandbox-proxy"},
        ],
    )
    entry = kb_build.build(tmp_path / "drafts", [ci, recheck], built_at="2026-10-21")["entries"][
        MIT
    ]
    (english,) = entry["facts"]["english"]
    assert english["verified_by"] == "recheck" and english["verified_on"] == "2026-10-20"
    (page,) = entry["programme"]["evidence"]
    assert page["verified_by"] == "ci" and page["verified_on"] == "2026-10-19"
    assert entry["facts"]["deadline"] == []
    assert entry["verified_on_basis"] == "ci_evidence_check+sandbox_recheck"

    # The order of the reports does not matter, and CI alone knows only the programme.
    reversed_entry = kb_build.build(tmp_path / "drafts", [recheck, ci], built_at="2026-10-21")
    assert reversed_entry["entries"][MIT]["facts"] == entry["facts"]
    ci_only = kb_build.build(tmp_path / "drafts", [ci], built_at="2026-10-21")["entries"][MIT]
    assert ci_only["facts"]["english"] == [] and ci_only["programme"]["status"] == "known"
    assert ci_only["verified_on_basis"] == "ci_evidence_check"
    assert ci_only["programme"]["evidence"][0]["verified_by"] == "ci"


def test_converter_prefers_the_ci_row_when_both_checks_pass(tmp_path):
    _batch(tmp_path / "drafts")
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("english", URL)])
    recheck = _report(
        tmp_path / "evidence_check.recheck-2026-10-20.json",
        [{**_row("english", URL), "origin": "sandbox-proxy"}],
    )
    entry = kb_build.build(tmp_path / "drafts", [recheck, ci], built_at="2026-10-21")["entries"][
        MIT
    ]
    (english,) = entry["facts"]["english"]
    assert english["verified_by"] == "ci" and english["verified_on"] == "2026-10-19"


def _override_row(item: str, url: str, *, used: bool = True, **extra: Any) -> dict[str, Any]:
    return {
        **_row(item, url),
        "robots_override": True,
        "robots_override_used": used,
        "origin": "sandbox-proxy",
        "checked_on": "2026-10-20",
        **extra,
    }


def test_converter_marks_and_lists_facts_only_the_robots_override_verified(tmp_path):
    _batch(tmp_path / "drafts")
    ci = _report(
        tmp_path / "evidence_check.ci-2026-10-19.json",
        [
            {**_row("programme", URL, found=False), "outcome": "robots_disallowed"},
            {**_row("english", URL, found=False), "outcome": "robots_disallowed"},
        ],
    )
    override = _report(
        tmp_path / "evidence_check.robots-override-2026-10-20.json",
        [_override_row("programme", URL), _override_row("english", URL)],
    )
    data = kb_build.build(tmp_path / "drafts", [ci, override], built_at="2026-10-21")
    entry = data["entries"][MIT]
    (english,) = entry["facts"]["english"]
    assert english["verified_by"] == "robots_override" and english["robots_override"] is True
    assert english["verified_on"] == "2026-10-20"
    (page,) = entry["programme"]["evidence"]
    assert page["verified_by"] == "robots_override" and page["robots_override"] is True
    assert entry["verified_on_basis"] == "ci_evidence_check+robots_override"
    assert data["robots_override_excluded"] is False
    assert {(r["source"], r["question"], r["url"]) for r in data["robots_override_facts"]} == {
        ("programme", "programme", URL),
        ("fact", "english", URL),
    }

    # Launch day: one flag removes them, and nothing else changes.
    excluded = kb_build.build(
        tmp_path / "drafts", [ci, override], built_at="2026-10-21", exclude_robots_override=True
    )
    gone = excluded["entries"][MIT]
    assert gone["facts"]["english"] == [] and gone["programme"]["status"] == "unknown"
    assert excluded["robots_override_facts"] == [] and excluded["robots_override_excluded"]
    assert not any(
        f.get("robots_override")
        for e in excluded["entries"].values()
        for fs in e["facts"].values()
        for f in fs
    )
    assert (
        excluded["entries"][MIT]["facts"]
        == kb_build.build(tmp_path / "drafts", [ci], built_at="2026-10-21")["entries"][MIT]["facts"]
    )


def test_converter_prefers_ordinary_checks_and_counts_an_unneeded_override_as_recheck(tmp_path):
    _batch(tmp_path / "drafts")
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("english", URL)])
    override = _report(
        tmp_path / "evidence_check.robots-override-2026-10-20.json",
        [_override_row("english", URL), _override_row("programme", URL, used=False)],
    )
    data = kb_build.build(tmp_path / "drafts", [override, ci], built_at="2026-10-21")
    entry = data["entries"][MIT]
    (english,) = entry["facts"]["english"]
    # A passing CI row wins over the override's: the fact is not an override fact.
    assert english["verified_by"] == "ci" and "robots_override" not in english
    # robots.txt allowed the read after all: an ordinary recheck, kept on launch day.
    (page,) = entry["programme"]["evidence"]
    assert page["verified_by"] == "recheck" and "robots_override" not in page
    assert data["robots_override_facts"] == []
    launch = kb_build.build(
        tmp_path / "drafts", [override, ci], built_at="2026-10-21", exclude_robots_override=True
    )
    assert launch["entries"][MIT]["programme"]["status"] == "known"


def test_kb_build_cli_takes_the_exclude_flag(tmp_path):
    _batch(tmp_path / "drafts")
    override = _report(
        tmp_path / "evidence_check.robots-override-2026-10-20.json",
        [_override_row("english", URL)],
    )
    out = tmp_path / "kb.json"
    drafts = str(tmp_path / "drafts")
    flags = ["--built-at", "2026-10-21", "--exclude-robots-override"]
    kb_build.main([drafts, "--evidence", str(override), "--out", str(out), *flags])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["robots_override_excluded"] is True and data["robots_override_facts"] == []
    assert data["entries"][MIT]["facts"]["english"] == []


def test_verify_evidence_accepts_kb_list_domains():
    from scripts import verify_evidence

    assert verify_evidence.is_official("https://web.mit.edu/x", MIT)
    assert verify_evidence.is_official("https://www.ox.ac.uk/admissions", "qs2027-004")
    assert verify_evidence.is_official("https://www.mit.edu/", "mit", seed_id=MIT)
    assert not verify_evidence.is_official("https://mit.example.com/", MIT)
    assert verify_evidence.is_official("https://cs.illinois.edu/x", "qs2027-074")  # extra_domains
    assert verify_evidence.is_official("https://www.rug.nl/x", "groningen")


# --------------------------------------------------------------------- loader


def test_loader_merges_the_development_import_by_seed_id(tmp_path):
    built = _kb(
        tmp_path / "kb.json",
        {
            MIT: _mit_entry(
                english=[_fact("ielts.overall", 7.0, "IELTS 7.0", verified_on="2026-10-19")]
            )
        },
    )
    imported = tmp_path / "imported.json"
    imported.write_text(
        json.dumps(
            {
                "format": "kb-imported-dev/1",
                "entries": {
                    MIT: {
                        **_mit_entry(
                            english=[
                                _fact("ielts.overall", 6.5, "IELTS 6.5", verified_on="2026-10-01")
                            ],
                            deadline=[_fact("deadline", "2027-01-05", "5 Jan 2027")],
                        ),
                        "review_status": "human_verified",
                    },
                    "qs2027-002": {
                        **_mit_entry(),
                        "seed_id": "qs2027-002",
                        "review_status": "draft",
                        "official_domain": "imperial.ac.uk",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    kb = load_knowledge_base(built, imported)
    assert set(kb.entries) == {MIT, "qs2027-002"}
    mit = kb.entries[MIT]
    assert [f["value"] for f in mit.facts["english"]] == [7.0]  # the newer fact wins
    assert [f["value"] for f in mit.facts["deadline"]] == ["2027-01-05"]  # import fills a gap
    assert kb.by_domain("www.imperial.ac.uk") is kb.entries["qs2027-002"]
    assert review_label(kb.entries["qs2027-002"].review_status) == (
        "expert-checked, quote verified"
    )
    assert review_label("human_verified") == "human verified"
    assert load_knowledge_base(tmp_path / "none.json", tmp_path / "none2.json").entries == {}


def test_repository_import_loads():
    kb = load_knowledge_base()
    assert "qs2027-002" in kb.entries  # the committed development import
    for entry in kb.entries.values():
        for _q, fact in entry.all_facts():
            assert fact["source_url"].startswith("http") and fact["quote"]


def test_stale_facts_are_not_current():
    today = date(2026, 10, 19)
    assert stale_reasons(_fact("x", 1, "q", verified_on="2025-10-01"), today)
    assert stale_reasons(_fact("tuition", 1, "q", academic_year="2025/26"), today)
    assert stale_reasons(_fact("deadline", "2026-01-15", "q"), today)
    assert not stale_reasons(_fact("tuition", 1, "q", academic_year="2026/27"), today)
    # ... but a 2026/27 fee is not current for a fall 2027 applicant.
    assert stale_reasons(_fact("tuition", 1, "q", academic_year="2026/27"), today, "fall 2027")
    assert not stale_reasons(_fact("tuition", 1, "q", academic_year="2027/28"), today, "fall 2027")
    from app.knowledge import _entry

    entry = _entry(
        MIT,
        _mit_entry(
            english=[_fact("ielts.overall", 7.0, "IELTS 7.0", verified_on="2025-01-01")],
            tuition=[
                _fact(
                    "tuition",
                    {"amount": 60000, "currency": "USD"},
                    "USD 60,000",
                    academic_year="2027/28",
                )
            ],
        ),
        "t",
    )
    found = answer(entry, programme="CS", intake="fall 2027", academic_year="2026/27", today=today)
    by_type = {c.claim_type: c for c in found.claims}
    assert by_type[ClaimType.IELTS_MIN_OVERALL].status is ClaimStatus.POSSIBLY_STALE
    assert "Stale" in by_type[ClaimType.IELTS_MIN_OVERALL].notes
    assert by_type[ClaimType.TUITION].status is ClaimStatus.VERIFIED_CURRENT
    assert found.costs.items  # a current tuition fact is the cost table


# --------------------------------------------------------------- product mode


@pytest.fixture
def catalogue_session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as session:
        import_catalogue(session)
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test on any search provider, live discovery or page read."""
    import app.adapters.search as search
    from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
    from app.adapters.fetching import Fetcher
    from app.adapters.search import brave, exa, exa_mcp, fake, serper, tavily

    def refuse(*args, **kwargs):
        raise AssertionError("network or search was called in kb mode")

    async def refuse_async(*args, **kwargs):
        raise AssertionError("network or search was called in kb mode")

    monkeypatch.setattr(search, "get_search_provider", refuse)
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", refuse)
    for module in (brave, exa, exa_mcp, fake, serper, tavily):
        for name in dir(module):
            cls = getattr(module, name)
            if isinstance(cls, type) and name.endswith("SearchProvider") and hasattr(cls, "search"):
                monkeypatch.setattr(cls, "search", refuse_async)
    monkeypatch.setattr(LiveDiscoveryAdapter, "discover", refuse_async)
    monkeypatch.setattr(Fetcher, "get", refuse_async)


def _kb_settings(settings: Settings, tmp_path: Path, mode: str = "kb") -> Settings:
    kb = _kb(
        tmp_path / "kb.json",
        {
            MIT: _mit_entry(
                english=[
                    _fact("ielts.overall", 7.0, "IELTS 7.0 overall"),
                    _fact(
                        "english_evidence.toefl_ibt.minimum",
                        100,
                        "TOEFL 100",
                        verified_on="2025-01-01",
                    ),
                ],
                deadline=[_fact("deadline", "2027-01-05", "Apply by 5 January 2027")],
                tuition=[
                    _fact(
                        "tuition",
                        {"amount": 60000.0, "currency": "USD"},
                        "Tuition 2027/28: USD 60,000",
                        academic_year="2027/28",
                    )
                ],
            )
        },
    )
    return settings.model_copy(
        update={
            "knowledge_mode": mode,
            "knowledge_base_path": kb,
            "knowledge_imported_path": tmp_path / "no-import.json",
        }
    )


async def _run(session: Session, profile, settings: Settings, query: str) -> ResearchRun:
    uni = retrieve(session, query=query)[0]
    applicant = profile_row(session, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="queued",
        demo_mode=False,
        candidate_limit=1,
        verify_limit=1,
        university_ids=[uni.id],
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    await ResearchRunner(session, run, profile, settings).run_to_decision()
    return run


@pytest.mark.asyncio
async def test_kb_mode_answers_from_the_kb_without_network(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    assert run.stage == "awaiting_user_decision"
    assert run.settings_snapshot["knowledge_mode"] == "kb"
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    claims = {c["claim_type"]: c for c in row.payload["claims"]}
    assert set(claims) >= {"program_exists", "ielts_min_overall", "admission_deadline", "tuition"}
    ielts = claims["ielts_min_overall"]
    assert ielts["original_text_excerpt"] == "IELTS 7.0 overall"
    assert ielts["official_domain"] is True and ielts["confidence"] == 0.8
    assert ielts["status"] == "VERIFIED_CURRENT" and ielts["is_stale"] is False
    toefl = claims["toefl_min_total"]
    assert toefl["status"] == "POSSIBLY_STALE" and toefl["is_stale"] is True
    assert row.payload["costs"]["items"]["tuition"]["amount"] == 60000.0
    assert s.scalars(select(ClaimRow).where(ClaimRow.run_id == run.id)).all()
    assert run.pages_checked == 0


@pytest.mark.asyncio
async def test_kb_mode_says_no_verified_data_for_a_university_outside_it(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Stanford")
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    assert row.payload["claims"] == []
    questions = [q["question"] for q in row.payload["unresolved"]]
    assert any(q.startswith("No verified data yet for Stanford") for q in questions)
    assert s.scalars(select(ClaimRow).where(ClaimRow.run_id == run.id)).all() == []


@pytest.mark.asyncio
async def test_kb_mode_out_of_scope_programme_does_not_claim_the_university_is_missing(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """MIT is in the KB; a Law applicant must not be told it has no entry (smoke 2026-10-19)."""
    s = catalogue_session
    law = profile.model_copy(
        update={"context": profile.context.model_copy(update={"intended_fields": ["law"]})}
    )
    run = await _run(s, law, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    assert row.payload["claims"] == []
    (question,) = [q for q in row.payload["unresolved"] if q["topic"] == "verified data"]
    assert question["blocking"] is True
    assert "covers only the bachelor's in Computer Science" in question["question"]
    assert "has no entry" not in question["why_it_matters"]
    assert "answers only for the bachelor's in Computer Science" in question["why_it_matters"]


@pytest.mark.asyncio
async def test_kb_mode_entry_without_programme_page_does_not_say_catalogue_only(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """KTH-like entry: verified facts, no verified programme page (smoke 2026-10-19)."""
    entry = _mit_entry(english=[_fact("ielts.overall", 6.5, "IELTS 6.5 overall")])
    entry["programme"] = {"status": "unknown", "urls": [], "evidence": []}
    s = catalogue_session
    run = await _run(
        s, profile, _funding_settings(settings, tmp_path, entry), "Massachusetts Institute"
    )
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    assert {c["claim_type"] for c in row.payload["claims"]} == {"ielts_min_overall"}
    texts = " ".join(q["question"] + q["why_it_matters"] for q in row.payload["unresolved"])
    assert "catalogue only" not in texts
    assert "Nothing about it has been verified" not in texts
    (question,) = [q for q in row.payload["unresolved"] if q["topic"] == "official source"]
    assert question["blocking"] is True
    assert "verified on its official site" in question["why_it_matters"]


def test_capabilities_name_the_knowledge_base_in_kb_mode(monkeypatch, settings):
    import app.api.routes_meta as routes_meta

    kb = settings.model_copy(update={"demo_mode": False, "knowledge_mode": "kb"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: kb)
    body = routes_meta.capabilities()
    assert body["knowledge_mode"] == "kb"
    assert "verified knowledge base" in body["data_origin"]
    live = settings.model_copy(update={"demo_mode": False, "knowledge_mode": "live"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: live)
    assert routes_meta.capabilities()["data_origin"] == "live official sources"
    demo = settings.model_copy(update={"demo_mode": True, "knowledge_mode": "kb"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: demo)
    assert routes_meta.capabilities()["knowledge_mode"] == "demo"


def test_live_mode_keeps_the_live_pipeline(catalogue_session, settings, tmp_path, profile):
    from app.catalogue.discovery import CatalogueDiscoveryAdapter

    s = catalogue_session
    applicant = profile_row(s, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="queued",
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
    )
    live = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "live"))
    assert not live.kb_mode
    assert isinstance(live._make_discovery_adapter(live._make_fetcher()), CatalogueDiscoveryAdapter)
    kb = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "kb"))
    assert kb.kb_mode and kb._make_fetcher().offline
    # Demo mode keeps its own fixtures whatever the knowledge mode says.
    run.demo_mode = True
    assert not ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "kb")).kb_mode


def test_knowledge_mode_defaults_to_kb_and_rejects_others(monkeypatch):
    monkeypatch.delenv("UNIMATCH_KNOWLEDGE_MODE", raising=False)
    assert Settings().knowledge_mode == "kb"
    with pytest.raises(RuntimeError, match="KNOWLEDGE_MODE"):
        Settings(knowledge_mode="web", demo_mode=True)._validate_search()


# ------------------------------------------------------------ kb funding stage

AWARD_URL = "https://www.mit.edu/finaid/synthetic-award"


def _award(slug: str, field: str, value: Any, quote: str, **extra: Any) -> dict[str, Any]:
    key = (
        f"scholarships.{slug}.exists"
        if field == "exists"
        else f"scholarships.{slug}.applicability.international"
    )
    return _fact(key, value, quote, source_url=AWARD_URL, **extra)


def _funding_settings(settings: Settings, tmp_path: Path, entry: dict[str, Any]) -> Settings:
    return settings.model_copy(
        update={
            "knowledge_mode": "kb",
            "knowledge_base_path": _kb(tmp_path / "kb.json", {MIT: entry}),
            "knowledge_imported_path": tmp_path / "no-import.json",
        }
    )


async def _funding_run(
    session: Session, profile, settings: Settings, tmp_path: Path, entry: dict[str, Any]
) -> tuple[ResearchRun, dict[str, Any]]:
    run = await _run(
        session, profile, _funding_settings(settings, tmp_path, entry), "Massachusetts Institute"
    )
    row = session.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    return run, dict(row.payload)


_NO_AWARD = {
    "question": "scholarship_exists",
    "key": "scholarships",
    "reason": "No scholarships are offered for bachelor's applicants.",
    "source_url": AWARD_URL,
    "quote": "MIT does not offer merit scholarships to undergraduates.",
    "verified_on": "2026-10-19",
}


@pytest.mark.asyncio
async def test_kb_mode_builds_scholarships_from_kb_facts(
    catalogue_session, profile, settings, tmp_path, no_network
):
    named = {"award": {"subject": "MIT Synthetic Award", "source_url": AWARD_URL}}
    entry = _mit_entry(
        scholarship_exists=[
            _award(
                "synthetic",
                "exists",
                True,
                "MIT Synthetic Award for undergraduate students",
                **named,
            ),
            _award("local_only", "exists", True, "Local Bursary for undergraduate students"),
            _award("old", "exists", True, "Old Award", verified_on="2025-01-01"),
        ],
        scholarship_international=[
            # Unstamped: still the same award as its stamped exists fact.
            _award("synthetic", "international", True, "Open to international students."),
            _award("local_only", "international", False, "Only for US citizens."),
        ],
    )
    run, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    awards = {a["name"]: a for a in payload["scholarships"]}
    assert set(awards) == {"MIT Synthetic Award", "local_only", "old"}

    claim_ids = {c["id"] for c in payload["claims"]}
    synthetic = awards["MIT Synthetic Award"]
    assert synthetic["opportunity_exists"] is True
    assert synthetic["international_eligible"] == "yes"
    assert synthetic["degree_applicability"] == "yes"  # from the quoted "undergraduate"
    assert len(synthetic["claim_ids"]) == 2 and set(synthetic["claim_ids"]) <= claim_ids
    assert synthetic["source_urls"] == [AWARD_URL]
    # The KB holds no amount or coverage table: never invented, so unknown.
    assert synthetic["amount"] is None and synthetic["coverage"] == []
    assert synthetic["classification"] == "UNKNOWN"

    assert awards["local_only"]["international_eligible"] == "no"
    assert awards["local_only"]["classification"] == "NOT_ELIGIBLE"

    # A stale fact names its award but settles nothing about this cycle.
    old = awards["old"]
    assert old["international_eligible"] == "unknown"
    assert old["available_this_intake"] == "unknown"
    stale_claims = [c for c in payload["claims"] if c["subject_key"] == "old"]
    assert [c["status"] for c in stale_claims] == ["POSSIBLY_STALE"]
    assert any(
        q["topic"] == "funding" and q["question"].startswith("Is old still offered")
        for q in payload["unresolved"]
    )

    assert payload["funding_fit"] == "UNKNOWN"
    assert run.pages_checked == 0


@pytest.mark.asyncio
async def test_kb_mode_no_scholarship_for_bachelors_is_an_explicit_outcome(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = {**_mit_entry(), "not_applicable": [_NO_AWARD]}
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["scholarships"] == []
    none = [c for c in payload["claims"] if c["claim_type"] == "scholarship_exists"]
    assert len(none) == 1 and none[0]["normalized_value"] is False
    assert none[0]["subject_key"] is None and none[0]["status"] == "VERIFIED_CURRENT"
    assert "No institutional scholarship" in none[0]["notes"]
    assert payload["funding_fit"] == "NOT_ELIGIBLE"
    assert payload["best_funding_classification"] == "NOT_ELIGIBLE"
    assert any("No institutional scholarship" in w for w in payload["funding_gap"]["warnings"])


@pytest.mark.asyncio
async def test_kb_mode_stale_no_scholarship_statement_leaves_funding_unknown(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = {**_mit_entry(), "not_applicable": [{**_NO_AWARD, "verified_on": "2025-01-01"}]}
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    none = [c for c in payload["claims"] if c["claim_type"] == "scholarship_exists"]
    assert none[0]["status"] == "POSSIBLY_STALE" and none[0]["is_stale"] is True
    assert payload["funding_fit"] == "UNKNOWN"
    warnings = " ".join(payload["funding_gap"]["warnings"])
    assert "stale" in warnings and "not confirmed absent" in warnings


def test_not_applicable_scholarship_fact_value_is_a_no_award_claim():
    from app.knowledge import _entry

    na = _fact("scholarships.exists", "not_applicable", "No scholarships for bachelor's.")
    entry = _entry(MIT, _mit_entry(scholarship_exists=[na]), "t")
    found = answer(
        entry, programme="CS", intake="fall 2027", academic_year="2027/28", today=date(2026, 10, 19)
    )
    schol = [c for c in found.claims if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS]
    assert len(schol) == 1
    assert schol[0].normalized_value is False and schol[0].subject_key is None
    # A named award contradicts "none": then no no-award claim is made.
    award = _award("x", "exists", True, "X Award")
    raw = {**_mit_entry(scholarship_exists=[award]), "not_applicable": [_NO_AWARD]}
    found = answer(_entry(MIT, raw, "t"), programme="CS", intake="fall 2027", academic_year="")
    exists = [c for c in found.claims if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS]
    assert [(c.normalized_value, c.subject_key) for c in exists] == [(True, "x")]


def test_loader_keeps_and_merges_not_applicable(tmp_path):
    built = _kb(tmp_path / "kb.json", {MIT: {**_mit_entry(), "not_applicable": [_NO_AWARD]}})
    newer = {**_NO_AWARD, "reason": "newer", "verified_on": "2026-10-20"}
    imported = _kb(tmp_path / "imp.json", {MIT: {**_mit_entry(), "not_applicable": [newer]}})
    kb = load_knowledge_base(built, imported)
    assert [n["reason"] for n in kb.entries[MIT].not_applicable] == ["newer"]
    alone = load_knowledge_base(built, tmp_path / "none.json")
    assert alone.entries[MIT].not_applicable == [_NO_AWARD]


def test_batch_dirs_include_top_up_dirs(tmp_path):
    for name in ("batch2", "batch10", "topup_imported", "notes"):
        (tmp_path / name).mkdir()
    assert [p.name for p in kb_build.batch_dirs(tmp_path)] == [
        "batch10",
        "batch2",
        "topup_imported",
    ]


# --------------------------------------------------- top-up drafts: answer-level merge

TOPUP_URL = "https://www.mit.edu/admissions/english-topup"
FEE_URL = "https://www.mit.edu/admissions/tuition"
DEADLINE_URL = "https://www.mit.edu/admissions/deadlines"


def _full_batch(root: Path, english: dict[str, Any] | None = None) -> None:
    """A batch draft with English, tuition and a deadline, and its CI report in its dir."""
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "english": english
                or {
                    "status": "known",
                    "value": {"ielts_overall": 7.0},
                    "url": URL,
                    "quote": "IELTS 7.0 overall",
                },
                "tuition": {
                    "status": "known",
                    "value": {"amount": 60000, "currency": "USD", "academic_year": "2027-2028"},
                    "url": FEE_URL,
                    "quote": "Tuition 2027-2028: $60,000",
                },
                "deadline": {
                    "status": "known",
                    "value": "2027-01-05",
                    "url": DEADLINE_URL,
                    "quote": "Apply by 5 January 2027",
                },
            },
        },
    )
    _report(
        root / "batch1/evidence_check.ci-2026-10-19.json",
        [_row("english", URL), _row("tuition", FEE_URL), _row("deadline", DEADLINE_URL)],
    )


def _topup(root: Path, answers: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """A partial top-up draft (only the filled answers) and its CI report in its dir."""
    _write(
        root / "topup_round2/core" / f"{MIT}.json",
        {"case": MIT, "seed_id": MIT, "researched_on": "2026-10-20", "answers": answers},
    )
    _report(root / "topup_round2/evidence_check.ci-2026-10-20.json", rows)


def _build_dir_reports(root: Path) -> dict[str, Any]:
    reports = sorted(root.glob("*/evidence_check.*.json"))
    data: dict[str, Any] = kb_build.build(root, reports, built_at="2026-10-21")
    return data["entries"][MIT]


_TOPUP_ENGLISH = {
    "status": "known",
    "value": {"ielts_overall": 7.0, "duolingo": 120},
    "url": TOPUP_URL,
    "quote": "IELTS Minimum: 7 Duolingo English Test (DET) Minimum: 120",
}


def test_a_partial_top_up_keeps_the_batch_answers_it_does_not_hold(tmp_path):
    root = tmp_path / "drafts"
    _full_batch(root)
    before = _build_dir_reports(root)
    _topup(root, {"english": _TOPUP_ENGLISH}, [_row("english", TOPUP_URL)])
    entry = _build_dir_reports(root)

    # Tuition and the deadline stay as the batch draft built them, unmarked.
    assert entry["facts"]["tuition"] == before["facts"]["tuition"] != []
    assert entry["facts"]["deadline"] == before["facts"]["deadline"] != []
    # English comes from the top-up, with its provenance.
    english = {f["key"]: f for f in entry["facts"]["english"]}
    assert set(english) == {"ielts.overall", "english_evidence.duolingo.minimum"}
    assert english["english_evidence.duolingo.minimum"]["value"] == 120
    assert {f["source_url"] for f in english.values()} == {TOPUP_URL}
    assert {f["source_batch"] for f in english.values()} == {"topup_round2"}
    assert entry["source_batch"] == "batch1"
    assert entry["source_batches"] == ["batch1", "topup_round2"]
    assert entry["known_fact_count"] == 4
    # A single-draft build adds no provenance fields.
    assert "source_batches" not in before
    assert not any("source_batch" in f for fs in before["facts"].values() for f in fs)


def test_an_english_test_merges_on_its_own(tmp_path):
    root = tmp_path / "drafts"
    _full_batch(
        root,
        english={
            "status": "known",
            "value": {"ielts_overall": 7.0, "toefl_ibt": 100},
            "url": URL,
            "quote": "IELTS 7.0 overall, TOEFL iBT 100",
        },
    )
    duolingo_only = {
        "status": "known",
        "value": {"duolingo": 120},
        "url": TOPUP_URL,
        "quote": "Duolingo English Test (DET) Minimum: 120",
    }
    _topup(root, {"english": duolingo_only}, [_row("english", TOPUP_URL)])
    english = {f["key"]: f for f in _build_dir_reports(root)["facts"]["english"]}
    assert english["ielts.overall"]["source_url"] == URL
    assert english["english_evidence.toefl_ibt.minimum"]["value"] == 100
    assert "source_batch" not in english["english_evidence.toefl_ibt.minimum"]
    assert english["english_evidence.duolingo.minimum"]["source_batch"] == "topup_round2"


def test_an_unknown_top_up_answer_never_overwrites_a_known_one(tmp_path):
    root = tmp_path / "drafts"
    _full_batch(root)
    before = _build_dir_reports(root)
    new_fee = {
        "status": "known",
        "value": {"amount": 1, "currency": "USD", "academic_year": "2027-2028"},
        "url": FEE_URL,
        "quote": "Tuition 2027-2028: $1",
    }
    _topup(
        root,
        {
            # Researched again, still not established.
            "deadline": {"status": "unknown", "notes": "No date published yet."},
            # Known in the draft, but its quote failed the check.
            "english": _TOPUP_ENGLISH,
            # Same URL as the batch's passing row, but the top-up's CI has no row
            # for it: a batch row never vouches for a top-up's different quote.
            "tuition": new_fee,
        },
        [_row("english", TOPUP_URL, found=False)],
    )
    entry = _build_dir_reports(root)
    assert entry["facts"]["deadline"] == before["facts"]["deadline"] != []
    assert entry["facts"]["english"] == before["facts"]["english"] != []
    assert entry["facts"]["tuition"] == before["facts"]["tuition"] != []
    # Only the test the batch never had is unknown, with the top-up's reason.
    assert [
        (u["key"], u.get("source_batch"))
        for u in entry["unknown"]
        if u["question"] in {"deadline", "english", "tuition"}
    ] == [("english_evidence.duolingo.minimum", "topup_round2")]


def test_a_top_up_reason_replaces_an_unknown_and_programme_pages_are_a_union(tmp_path):
    root = tmp_path / "drafts"
    page = {"case": MIT, "programme": {"url": URL, "title": "Computer Science BSc"}}
    _write(root / "batch1/programme" / f"{MIT}.0-local.json", page)
    _write(root / "batch1/core" / f"{MIT}.json", {"case": MIT, "answers": {}})
    _report(root / "batch1/evidence_check.ci-2026-10-19.json", [_row("programme", URL)])
    other = "https://www.mit.edu/admissions/cs-department"
    _write(root / "topup_round2/programme" / f"{MIT}.0-local.json", page)  # restated
    _write(
        root / "topup_round2/programme" / f"{MIT}.1-department.json",
        {"case": MIT, "programme": {"url": other, "title": "EECS 6-3"}},
    )
    _topup(
        root,
        {"deadline": {"status": "unknown", "notes": "The dates page renders client-side."}},
        [_row("programme", other)],
    )
    entry = _build_dir_reports(root)
    assert entry["programme"]["urls"] == [URL, other]
    assert len(entry["programme"]["evidence"]) == 2
    (deadline,) = [u for u in entry["unknown"] if u["question"] == "deadline"]
    assert "client-side" in deadline["reason"] and deadline["source_batch"] == "topup_round2"
    # A question the top-up did not research keeps the batch's reason.
    (tuition,) = [u for u in entry["unknown"] if u["question"] == "tuition"]
    assert "source_batch" not in tuition
