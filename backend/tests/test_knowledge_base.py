"""The verified knowledge base: build, merge, staleness, and the kb research mode.

Owner decision 2026-10-19: live search frozen; a CS bachelor is answered from
the KB. Every URL and quote below is synthetic test data.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.catalogue.importer import import_catalogue
from app.catalogue.retrieval import retrieve
from app.config import Settings
from app.db import create_all_for_tests
from app.domain.enums import ClaimStatus, ClaimType
from app.knowledge import (
    academic_year_end,
    carried_stale_reasons,
    load_knowledge_base,
    review_label,
    stale_reasons,
)
from app.knowledge.claims import answer, covers
from app.models import ClaimRow, ProgramResultRow, ResearchRun, University
from app.models.base import ensure_utc
from app.pipeline.runner import ResearchRunner, _kb_claim_is_stale
from app.pipeline.state import RunState
from evaluation.research.expert import kb_build
from tests.conftest import profile_row

MIT = "qs2027-001"
URL = "https://www.mit.edu/admissions/synthetic"
#: The day the fixtures below were written for. The runner judges KB staleness
#: on ``kb_today()``; unpinned, every "VERIFIED_CURRENT" here would turn stale
#: on 2027-10-20 (365 days after ``verified_on``) and every "2027/28" fee in 2028.
FIXTURE_DAY = date(2026, 10, 19)


@pytest.fixture(autouse=True)
def _pinned_kb_day(monkeypatch):
    monkeypatch.setattr("app.knowledge.claims.kb_today", lambda: FIXTURE_DAY)


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


@pytest.mark.parametrize(
    ("published", "reason"),
    [
        ("2026", "published for academic year 2026"),
        ("not stated (latest occasion shown: Höst 2026)", "the academic year is not stated"),
        (
            "from the 2025 fall semester (no academic year stated)",
            "the academic year is not stated",
        ),
    ],
)
def test_converter_words_a_value_based_reason_without_the_build_intake(tmp_path, published, reason):
    root = tmp_path / "drafts"
    _write(
        root / "batch2/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "tuition": {
                    "status": "known",
                    "value": {"amount": 52000, "currency": "AUD", "academic_year": published},
                    "url": URL,
                    "quote": "Annual tuition fee AUD 52,000",
                },
            },
        },
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    (fee,) = entry["facts"]["tuition"]
    assert fee["stale"] and fee["stale_reasons"] == [reason]
    # Stored for every intake: no intake is named, and none drops it.
    assert "intake" not in reason
    assert carried_stale_reasons(fee, "spring 2028") == [reason]


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


@pytest.mark.parametrize(
    ("text", "end"),
    [
        ("2026/27", 2027),
        ("2026-2027", 2027),
        ("2026/2027", 2027),
        ("2027/2028 (2027 entry)", 2028),
        ("2026-27 (2026-27 cohort)", 2027),
        ("2027/28 (September 2027 start selected on the page)", 2028),
        (None, None),
        ("2027", None),
        # Science Tokyo: an ISO date is not academic year 2019/04 (= 2004).
        ("not stated (bachelor students entering on or after 2019-04-01)", None),
        ("entering on or after 2019-04-01", None),
        # Heidelberg: the year a policy began is not the fee's academic year.
        ("since winter semester 2017/18 (no academic year stated)", None),
        ("since winter semester 2017/18", None),
        # FU Berlin: a year the "not stated" note mentions is context only.
        ("not stated (standing policy; semester fees shown for WS 2026/27)", None),
        ("2026/2028", None),
    ],
)
def test_academic_year_end_reads_only_an_academic_year(text, end):
    assert academic_year_end(text) == end


def test_a_date_or_a_policy_start_is_not_a_past_academic_year():
    today = date(2026, 10, 19)
    for published in (
        "not stated (bachelor students entering on or after 2019-04-01)",
        "since winter semester 2017/18 (no academic year stated)",
        "not stated (standing policy; semester fees shown for WS 2026/27)",
    ):
        fee = _fact("tuition", 1, "q", academic_year=published)
        assert not stale_reasons(fee, today, "fall 2027")


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


def test_a_summer_intake_joins_the_academic_year_that_began_the_autumn_before():
    """Review 2026-10-19: "summer 2027" read as 2027/28, so its own 2026/27 fee was stale."""
    from app.knowledge import intake_academic_year_start

    assert intake_academic_year_start("summer 2027") == 2026
    assert intake_academic_year_start("spring 2027") == 2026
    assert intake_academic_year_start("fall 2027") == 2027
    fee = _fact("tuition", 1, "q", academic_year="2026/27")
    assert not stale_reasons(fee, FIXTURE_DAY, "summer 2027")
    assert stale_reasons(
        _fact("tuition", 1, "q", academic_year="2025/26"), FIXTURE_DAY, "summer 2027"
    )


def test_a_running_academic_year_is_not_past_from_1_january():
    """Review P4: 2026/27 was "past" from 2027-01-01, refusing a spring 2027 fee."""
    fee = _fact("tuition", 1, "q", academic_year="2026/27", verified_on="2026-12-01")
    for day in (date(2027, 1, 2), date(2027, 6, 30), date(2027, 8, 31)):
        assert not stale_reasons(fee, day, "spring 2027"), day
        assert not stale_reasons(fee, day), day
    reasons = stale_reasons(fee, date(2027, 9, 1), "spring 2027")
    assert reasons == ["academic year 2026/27 is past"]
    # A year that ended before this calendar year is past at any month.
    old = _fact("tuition", 1, "q", academic_year="2025/26", verified_on="2026-12-01")
    assert "academic year 2025/26 is past" in stale_reasons(old, date(2027, 1, 2))


def _built_fee(**extra: Any):
    """A 2026/27 fee as the fall 2027 build stored it: stale for *that* intake."""
    from app.knowledge import _entry

    fee = _fact(
        "tuition",
        {"amount": 66720.0, "currency": "USD"},
        "Tuition 2026-2027: $66,720",
        academic_year="2026/2027",
        period="year",
        stale=True,
        stale_reasons=["academic year 2026/2027 is before the fall 2027 intake's 2027/28"],
        **extra,
    )
    return _entry(MIT, _mit_entry(tuition=[fee]), "t")


def test_a_stored_reason_for_the_build_intake_does_not_stale_another_intake():
    """Review 2026-10-19: the build's fall 2027 verdict was carried to every applicant."""
    for intake in ("spring 2027", "summer 2027"):
        found = answer(_built_fee(), programme="CS", intake=intake, academic_year="2026/27")
        (fee,) = found.claims[1:]
        assert fee.status is ClaimStatus.VERIFIED_CURRENT, intake
        assert "fall 2027" not in fee.notes
        assert found.costs.items  # the applicant's own year's fee is the cost table
    found = answer(_built_fee(), programme="CS", intake="fall 2027", academic_year="2027/28")
    (fee,) = found.claims[1:]
    assert fee.status is ClaimStatus.POSSIBLY_STALE
    assert "before the fall 2027 intake's 2027/28" in fee.notes
    assert not found.costs.items
    # A later intake is still refused, in its own words.
    found = answer(_built_fee(), programme="CS", intake="fall 2028", academic_year="2028/29")
    (fee,) = found.claims[1:]
    assert fee.status is ClaimStatus.POSSIBLY_STALE
    assert "before the fall 2028 intake's 2028/29" in fee.notes
    assert "fall 2027" not in fee.notes


def test_a_stored_reason_that_names_no_intake_is_kept_for_every_intake():
    from app.knowledge import _entry

    fee = _fact(
        "tuition",
        {"amount": 1.0, "currency": "USD"},
        "q",
        stale_reasons=["the academic year is not stated"],
    )
    entry = _entry(MIT, _mit_entry(tuition=[fee]), "t")
    found = answer(entry, programme="CS", intake="spring 2027", academic_year="2026/27")
    assert found.claims[1].status is ClaimStatus.POSSIBLY_STALE
    assert "the academic year is not stated" in found.claims[1].notes


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
async def test_kb_mode_judges_staleness_on_the_kb_day(
    catalogue_session, profile, settings, tmp_path, no_network, monkeypatch
):
    """The runner reads ``kb_today()``: a year on, the same KB fact is not current."""
    monkeypatch.setattr("app.knowledge.claims.kb_today", lambda: date(2027, 10, 21))
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    row = s.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    ielts = {c["claim_type"]: c for c in row.payload["claims"]}["ielts_min_overall"]
    assert ielts["status"] == "POSSIBLY_STALE"
    assert "more than 365 days ago" in ielts["notes"]
    # Every claim is already stale and a re-read of the same KB cannot move
    # its verification date: no recheck is armed (it was one a minute, forever).
    assert {c["status"] for c in row.payload["claims"]} == {"POSSIBLY_STALE"}
    assert run.next_recheck_at is None


@pytest.mark.asyncio
async def test_kb_mode_recheck_waits_for_the_day_a_fact_turns_stale(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """Review 2026-10-19: the KB recheck clock and ``stale_reasons`` disagreed by a day,
    and a claim already stale stayed due at every recheck."""
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    verified = datetime(2026, 10, 19, tzinfo=UTC)
    assert ensure_utc(run.next_recheck_at) == verified + timedelta(days=366)
    rows = s.scalars(select(ClaimRow).where(ClaimRow.run_id == run.id)).all()
    current = [r for r in rows if r.status == "VERIFIED_CURRENT"]
    stale = [r for r in rows if r.status == "POSSIBLY_STALE"]  # the 2025 TOEFL fact
    assert current and stale
    # Day 365 is still current by stale_reasons, so a recheck then changes nothing.
    assert stale_reasons(_fact("x", 1, "q"), date(2027, 10, 19)) == []
    assert not any(_kb_claim_is_stale(r, verified + timedelta(days=365)) for r in current)
    assert all(_kb_claim_is_stale(r, verified + timedelta(days=366)) for r in current)
    assert not any(_kb_claim_is_stale(r, verified + timedelta(days=3650)) for r in stale)


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


def test_capabilities_name_the_knowledge_base_in_kb_mode(monkeypatch, settings, catalogue_session):
    import app.api.routes_meta as routes_meta
    from app.api.routes_universities import _knowledge_base

    kb = settings.model_copy(update={"demo_mode": False, "knowledge_mode": "kb"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: kb)
    body = routes_meta.capabilities(catalogue_session)
    # RM-1: the coverage note names the KB's reach, read from the loaded KB and
    # the catalogue (never a literal), and says that no page is read.
    loaded = _knowledge_base(kb.knowledge_base_path, kb.knowledge_imported_path)
    verified = [e for e in loaded.entries.values() if e.has_verified_data]
    total = catalogue_session.scalar(select(func.count()).select_from(University))
    coverage = body["live_coverage"]
    assert coverage["mode"] == "kb"
    assert coverage["institutions"] == len(verified) > 0
    assert coverage["catalogue_total"] == total > len(verified)
    assert coverage["countries"] == sorted({e.country for e in verified if e.country})
    assert coverage["recall_note"] == (
        f"The verified knowledge base answers for {len(verified)} of {total} catalogue "
        "universities (bachelor's in Computer Science). A university outside it, or another "
        "programme, gets 'No verified data yet'; no page is read during a run."
    )
    assert "Live mode" not in coverage["recall_note"]
    assert coverage["recall_message"] == {
        "key": "coverage.kb",
        "params": {"universities": str(len(verified)), "total": str(total)},
        "parts": {},
    }
    assert body["knowledge_mode"] == "kb"
    assert "verified knowledge base" in body["data_origin"]
    # CAT-1: the KB adapter is listed first and active; the registry and the
    # five web readers are listed as inactive, ``live`` unchanged.
    by_name = {a["name"]: a for a in body["adapters"]}
    assert body["adapters"][0] == {
        "name": "verified-knowledge-base",
        "role": "discovery and verification",
        "live": False,
        "active": True,
    }
    inactive = {n for n, a in by_name.items() if a.get("active") is False}
    assert inactive == {
        "live-institution-registry",
        "web-requirements",
        "web-costs",
        "web-scholarships",
        "web-documents",
        "web-government",
    }
    assert all(by_name[n]["live"] is True for n in inactive)
    live = settings.model_copy(update={"demo_mode": False, "knowledge_mode": "live"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: live)
    assert routes_meta.capabilities(catalogue_session)["data_origin"] == "live official sources"
    live_adapters = routes_meta.capabilities(catalogue_session)["adapters"]
    assert routes_meta.capabilities(catalogue_session)["live_coverage"]["mode"] == "live"
    assert "verified-knowledge-base" not in {a["name"] for a in live_adapters}
    assert all("active" not in a for a in live_adapters)
    demo = settings.model_copy(update={"demo_mode": True, "knowledge_mode": "kb"})
    monkeypatch.setattr(routes_meta, "get_settings", lambda: demo)
    demo_body = routes_meta.capabilities(catalogue_session)
    assert demo_body["knowledge_mode"] == "demo"
    assert demo_body["live_coverage"] == routes_meta.registry_coverage()


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


def test_a_run_keeps_the_knowledge_mode_it_started_in(settings, tmp_path) -> None:
    """Review P1: the mode is the run's, recorded at its first start, not the deployment's."""
    from app.pipeline.runner import run_knowledge_mode

    kb, live = _kb_settings(settings, tmp_path, "kb"), _kb_settings(settings, tmp_path, "live")
    fresh = ResearchRun(stage="queued", settings_snapshot={})
    assert run_knowledge_mode(fresh, kb) == "kb"
    assert run_knowledge_mode(fresh, live) == "live"
    recorded_kb = ResearchRun(settings_snapshot={"knowledge_mode": "kb"})
    assert run_knowledge_mode(recorded_kb, live) == "kb"
    recorded_live = ResearchRun(settings_snapshot={"knowledge_mode": "live"})
    assert run_knowledge_mode(recorded_live, kb) == "live"
    # A run from before live runs recorded their mode ran live: its claims are live.
    old_live = ResearchRun(settings_snapshot={"demo_mode": False, "candidate_limit": 1})
    assert run_knowledge_mode(old_live, kb) == "live"
    started = ResearchRun(settings_snapshot={}, started_at=datetime(2026, 10, 1, tzinfo=UTC))
    assert run_knowledge_mode(started, kb) == "live"


def test_a_pre_switch_live_run_resumes_live_in_a_kb_deployment(
    catalogue_session, settings, tmp_path, profile
):
    """Review P1: a resumed or rechecked live run must not finish from the KB."""
    from app.catalogue.discovery import CatalogueDiscoveryAdapter

    s = catalogue_session
    applicant = profile_row(s, profile)
    run = ResearchRun(
        profile_id=applicant.id,
        stage="program_verification",
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
        started_at=datetime(2026, 10, 18, tzinfo=UTC),
        settings_snapshot={"demo_mode": False, "candidate_limit": 1, "university_ids": []},
    )
    resumed = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "kb"))
    assert not resumed.kb_mode and resumed.knowledge_mode == "live"
    assert not resumed._make_fetcher().offline
    assert isinstance(
        resumed._make_discovery_adapter(resumed._make_fetcher()), CatalogueDiscoveryAdapter
    )


@pytest.mark.asyncio
async def test_a_kb_run_stays_kb_after_the_deployment_switches_to_live(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    run = await _run(s, profile, _kb_settings(settings, tmp_path), "Massachusetts Institute")
    assert run.settings_snapshot["knowledge_mode"] == "kb"
    later = ResearchRunner(s, run, profile, _kb_settings(settings, tmp_path, "live"))
    assert later.kb_mode
    # A recheck under the live deployment still re-reads the KB (no_network
    # fails any page read or search) and keeps the run's recorded mode.
    assert await later.recheck_stale() == 0
    await later.run_to_decision()
    assert run.settings_snapshot["knowledge_mode"] == "kb"
    assert run.settings_snapshot["knowledge_base"] == "test.kb"


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


# ------------------------------------------------- kb wording (smoke B2-B5)


def test_programme_name_is_a_short_title_not_the_evidence_quote():
    from app.knowledge.claims import FALLBACK_PROGRAMME, programme_name

    def named(*quotes: str, **extra: Any) -> str:
        return programme_name({"evidence": [{"quote": q} for q in quotes], **extra})

    mit = (
        "Computer Science and Engineering (Course 6-3) Department of Electrical Engineering "
        "and Computer Science Bachelor of Science in Computer Science and Engineering"
    )
    assert named(mit) == "Computer Science and Engineering"
    assert (
        named("Bachelor Computer Science (official German title: Bachelor Informatik; BSc ETH)")
        == "Bachelor Computer Science"
    )
    # The name that says the degree wins over a longer heading.
    assert (
        named("Informatik Mono-Bachelor & Modulangebote im Kombi-Bachelor", "BSc Informatik")
        == "BSc Informatik"
    )
    # A sentence is evidence, not a name; a degree title inside it is.
    assert (
        named("The BS in Computer Science emphasizes advanced mathematics, science and more.")
        == "BS in Computer Science"
    )
    assert named("This major covers a wide range of algorithms.") == FALLBACK_PROGRAMME
    assert named() == FALLBACK_PROGRAMME
    assert named(mit, title="Course 6-3") == "Course 6-3"


@pytest.mark.asyncio
async def test_kb_mode_names_the_programme_without_the_quote(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry()
    entry["programme"]["evidence"][0]["quote"] = (
        "Computer Science and Engineering (Course 6-3) Department of Electrical Engineering "
        "and Computer Science Bachelor of Science in Computer Science and Engineering"
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["program"] == "Computer Science and Engineering"
    (programme,) = [c for c in payload["claims"] if c["claim_type"] == "program_exists"]
    assert programme["original_text_excerpt"].startswith("Computer Science and Engineering (")


@pytest.mark.asyncio
async def test_kb_mode_cost_gap_names_a_stale_fee_instead_of_saying_none_was_found(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(
        tuition=[
            _fact(
                "tuition",
                {"amount": 66720.0, "currency": "USD"},
                "Tuition 2026-2027: $66,720",
                academic_year="2026/2027",
            )
        ]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["costs"]["items"] == {}
    gap = payload["funding_gap"]
    assert gap["computable"] is False
    reason = gap["reason"]
    assert "No official cost of attendance was found" not in reason
    assert "An official tuition fee was found, but for another academic year" in reason
    assert "66,720 USD a year, academic year 2026/2027" in reason
    assert "is before the fall 2027 intake's 2027/28" in reason
    assert not any("could not be verified" in w for w in gap["warnings"])
    assert any("Confirm the fall 2027 fee" in w for w in gap["warnings"])


@pytest.mark.asyncio
async def test_kb_mode_cost_gap_names_a_per_semester_fee(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(
        tuition=[
            _fact(
                "tuition",
                {"amount": 2190.0, "currency": "CHF"},
                "CHF 2,190 per semester",
                period="semester",
                academic_year="2027/28",
            )
        ]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    reason = payload["funding_gap"]["reason"]
    assert "not as a current yearly figure for the fall 2027 intake" in reason
    assert "2,190 CHF per semester, academic year 2027/28" in reason


@pytest.mark.asyncio
async def test_kb_mode_row_without_awards_asks_about_funding_in_kb_words(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(english=[_fact("ielts.overall", 7.0, "IELTS 7.0 overall")])
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["scholarships"] == []
    (question,) = [q for q in payload["unresolved"] if q["topic"] == "funding"]
    assert question["blocking"] is False
    assert "names no award" in question["why_it_matters"]
    assert "not confirmed absent" in question["why_it_matters"]


@pytest.mark.asyncio
async def test_kb_mode_no_scholarship_statement_needs_no_funding_question(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = {**_mit_entry(), "not_applicable": [_NO_AWARD]}
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert not [q for q in payload["unresolved"] if q["topic"] == "funding"]


_NO_ENGLISH = {
    "question": "english",
    "key": "ielts.overall",
    "reason": (
        "Not an English requirement: the language requirement is German (german_level=DSH 2 "
        "for enrolment (or telc C1 Hochschule; german_required=True). Expert (2026-10-19): "
        "German-taught programme."
    ),
    "source_url": URL,
    "quote": "Immatrikulation: DSH 2",
    "verified_on": "2026-10-19",
}


@pytest.mark.asyncio
async def test_kb_mode_quotes_a_verified_does_not_apply_requirement(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """FU Berlin / ETH: no English test, a German one instead (smoke B4)."""
    subscores = {**_NO_ENGLISH, "key": "ielts.subscores"}
    entry = {**_mit_entry(), "not_applicable": [_NO_ENGLISH, subscores]}
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    (question,) = [q for q in payload["unresolved"] if q["topic"] == "language requirement"]
    assert question["question"].startswith(
        "Not an English requirement: the language requirement is German (DSH 2 for enrolment)."
    )
    assert "german_level" not in question["question"] and "Expert" not in question["question"]
    assert '"Immatrikulation: DSH 2"' in question["why_it_matters"]
    assert question["blocking"] is False


_NO_TEST = {
    "question": "english",
    "key": "ielts.overall",
    "reason": (
        "No English language test result is required for this route. Expert (2026-10-19): "
        "'No Japanese Language Proficiency Required' at application."
    ),
    "source_url": URL,
    "quote": "Are English proficiency exams required? No, we do not require any English "
    "proficiency exams.",
    "verified_on": "2026-10-19",
}


@pytest.mark.asyncio
async def test_kb_mode_asks_no_instead_when_no_other_language_is_named(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """Smoke U6 (Stanford, Harvard, Kyoto): no English test and nothing else named."""
    entry = {**_mit_entry(), "not_applicable": [_NO_TEST]}
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    (question,) = [q for q in payload["unresolved"] if q["topic"] == "language requirement"]
    assert "instead" not in question["question"]
    assert question["question"] == (
        "No English language test result is required for this route. Does Massachusetts "
        "Institute of Technology ask for any other language evidence? The verified knowledge "
        "base names none."
    )
    assert question["blocking"] is False


@pytest.mark.parametrize(
    ("statement", "quote", "named"),
    [
        # ETH: the generic statement, the quote names German C1.
        (
            "No English language test result is required for this route.",
            "The German C1 language certificate must be submitted by the application deadline",
            True,
        ),
        # The build's "is <language>" statement.
        (
            "Not an English requirement: the language requirement is Chinese.",
            "with Chinese as the medium of instruction.",
            True,
        ),
        # The page's own language: LMU, KU Leuven, UBA, Nanjing, Paris-Saclay.
        (
            "No English test.",
            "Das Studium an der LMU setzt ausreichende Deutschkenntnisse voraus",
            True,
        ),
        ("No English test.", "Nederlandse taalvaardigheid is B2 van het ERK", True),
        (
            "No English test.",
            "Si tu título fue emitido en un país no hispanohablante , de acuerdo",
            True,
        ),
        ("No English test.", "所有专业须达到HSK5级180分以上", True),
        ("No English test.", "Langue d'enseignement Français", True),
        # Stanford, Harvard, Kyoto: English only.
        ("No English test.", "No, we do not require any English proficiency exams.", False),
        (
            "No English test.",
            "there is no specific minimum score for the English requirement",
            False,
        ),
        # A language named only to say it is not asked for.
        ("No English test.", "No Japanese language proficiency required at application.", False),
    ],
)
def test_names_other_language(statement: str, quote: str, named: bool) -> None:
    from app.knowledge.claims import names_other_language

    assert names_other_language(statement, quote) is named


def test_committed_kb_asks_instead_only_where_another_language_is_named() -> None:
    """Smoke U6 on the committed KB: the "instead" question follows the verified text."""
    from app.knowledge.claims import requirement_statement_questions

    kb = load_knowledge_base()
    instead: dict[str, bool] = {}
    for entry in kb.entries.values():
        for q in requirement_statement_questions(
            entry, university=entry.university, programme="CS"
        ):
            if q.topic == "language requirement":
                instead[entry.university] = "instead" in q.question
    for university in ("Stanford University", "Harvard University", "Kyoto University"):
        assert instead[university] is False, university
    for university in ("ETH Zurich", "KU Leuven", "University of Copenhagen", "Nanjing University"):
        assert instead[university] is True, university


@pytest.mark.asyncio
async def test_kb_mode_cost_gap_without_any_kb_fee_says_so_in_kb_words(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """Smoke U8 (Edinburgh, Oxford): no page was read, so none "could not be verified"."""
    _run_, payload = await _funding_run(
        catalogue_session, profile, settings, tmp_path, _mit_entry()
    )
    gap = payload["funding_gap"]
    assert gap["computable"] is False
    assert gap["reason"] == (
        "The verified knowledge base holds no tuition fee for this programme yet, so the "
        "remaining cost is not computed."
    )
    assert not any("could not be verified" in w for w in gap["warnings"])
    assert any("Confirm the fall 2027 fee" in w for w in gap["warnings"])


@pytest.mark.asyncio
async def test_kb_mode_needs_clarification_always_says_why(
    catalogue_session, profile, settings, tmp_path, no_network
):
    named = {"award": {"subject": "MIT Synthetic Award", "source_url": AWARD_URL}}
    entry = _mit_entry(
        scholarship_exists=[_award("synthetic", "exists", True, "MIT Synthetic Award", **named)]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["eligibility"] == "NEEDS_OFFICIAL_CLARIFICATION"
    (question,) = [q for q in payload["unresolved"] if q["topic"] == "entry requirements"]
    assert question["blocking"] is False
    assert "needing clarification" in question["why_it_matters"]


# --- review P5: the KB answers a CS applicant only --------------------------


def _with_fields(profile, fields: list[str]):
    return profile.model_copy(
        update={"context": profile.context.model_copy(update={"intended_fields": fields})}
    )


@pytest.mark.parametrize(
    "fields",
    [
        ["computer science"],
        ["Computer Science"],
        ["Computing"],
        ["Informatics"],
        ["Informatik"],  # a localized alias in the ontology
        ["law", "computer science"],
        [],  # no field stated: the profile's default is computer science
    ],
)
def test_covers_answers_computer_science_and_its_ontology_aliases(profile, fields) -> None:
    assert covers(_with_fields(profile, fields))


@pytest.mark.parametrize(
    "field",
    ["Software Engineering", "Computer Engineering", "Business Informatics", "Data Science"],
)
def test_covers_does_not_answer_a_neighbouring_field_with_cs_facts(profile, field) -> None:
    """Review P5: a field that merely contains a CS word is another programme."""
    assert not covers(_with_fields(profile, [field]))


# ------------------------------------------- two honest fee shapes (round 11)


def _fee_draft(root: Path, value: dict[str, Any], quote: str) -> None:
    _write(
        root / "batch2/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "tuition": {"status": "known", "value": value, "url": URL, "quote": quote},
            },
        },
    )


@pytest.mark.parametrize(
    "bounds",
    [
        {"min": 27650, "max": 34670},
        {"amount_min": 27650, "amount_max": 34670},
        {"amount": 27650, "amount_max": 34670},  # the Auckland draft's spelling
    ],
)
def test_converter_keeps_a_printed_range_as_a_range(tmp_path, bounds):
    root = tmp_path / "drafts"
    _fee_draft(
        root,
        {**bounds, "currency": "GBP", "academic_year": "2027/28", "period": "year"},
        "For the 2027/28 academic year, tuition fees between £27,650 and £34,670",
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    (fee,) = entry["facts"]["tuition"]
    # Never the low bound alone (the Auckland fact before round 11), never a midpoint.
    assert fee["value"] == {"min": 27650.0, "max": 34670.0, "currency": "GBP"}
    assert fee["period"] == "year" and fee["unit"] == "GBP per year"
    assert not fee["stale"] and not any(u["key"] == "tuition" for u in entry["unknown"])


def test_converter_keeps_a_past_year_range_as_stale(tmp_path):
    root = tmp_path / "drafts"
    _fee_draft(
        root,
        {"min": 42554, "max": 51106, "currency": "USD", "academic_year": "2026-27"},
        "Non-Resident Tuition $42,554-$51,106",
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    (fee,) = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]["facts"]["tuition"]
    assert fee["value"] == {"min": 42554.0, "max": 51106.0, "currency": "USD"}
    assert fee["stale"] and fee["academic_year"] == "2026-27"


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        ({"min": 27650, "max": 34999}, "range bound 34999 is not printed in the quote"),
        ({"min": 34670, "max": 27650}, "are not a low and a higher bound"),
        ({"max": 34670}, "a range needs both bounds and a currency"),
    ],
)
def test_converter_refuses_a_range_the_quote_does_not_bear_out(tmp_path, value, problem):
    root = tmp_path / "drafts"
    _fee_draft(
        root,
        {**value, "currency": "GBP", "academic_year": "2027/28"},
        "tuition fees between £27,650 and £34,670",
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    entry = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]
    assert entry["facts"]["tuition"] == []
    (unknown,) = [u for u in entry["unknown"] if u["key"] == "tuition"]
    assert problem in unknown["reason"]


def test_converter_keeps_a_per_credit_rate_unmultiplied(tmp_path):
    root = tmp_path / "drafts"
    _fee_draft(
        root,
        {"amount": 1789.18, "currency": "CAD", "academic_year": "2027/28", "period": "credit"},
        "Science $1,789.18",
    )
    ci = _report(tmp_path / "evidence_check.ci-2026-10-19.json", [_row("tuition", URL)])
    (fee,) = kb_build.build(root, [ci], built_at="2026-10-19")["entries"][MIT]["facts"]["tuition"]
    assert fee["value"] == {"amount": 1789.18, "currency": "CAD"}
    assert fee["period"] == "credit" and fee["unit"] == "CAD per credit"
    assert not fee["stale"]


def test_converter_keeps_a_published_range_out_of_a_container_check(tmp_path):
    root = tmp_path / "drafts"
    _fee_draft(
        root,
        {"min": 27650, "max": 34670, "currency": "GBP", "academic_year": "2027/28"},
        "tuition fees between £27,650 and £34,670",
    )
    container = _report(
        tmp_path / "evidence_check.container-2026-10-20.json", [_row("tuition", URL)]
    )
    entry = kb_build.build(root, [container], built_at="2026-10-19")["entries"][MIT]
    assert entry["facts"]["tuition"] == []


@pytest.mark.asyncio
async def test_kb_mode_takes_a_printed_range_at_its_upper_bound_and_says_so(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(
        tuition=[
            _fact(
                "tuition",
                {"min": 27650.0, "max": 34670.0, "currency": "GBP"},
                "tuition fees between £27,650 and £34,670",
                period="year",
                academic_year="2027/28",
            )
        ]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    tuition = payload["costs"]["items"]["tuition"]
    assert (tuition["amount"], tuition["range_low"], tuition["range_high"]) == (
        34670.0,
        27650.0,
        34670.0,
    )
    assert tuition["currency"] == "GBP" and payload["costs"]["is_range"] is True
    (claim,) = [c for c in payload["claims"] if c["claim_type"] == "tuition"]
    assert claim["normalized_value"] == {
        "amount": 34670.0,
        "currency": "GBP",
        "range_low": 27650.0,
        "range_high": 34670.0,
    }
    assert "Published as a range, not a single figure." in claim["notes"]
    assert claim["status"] == "VERIFIED_CURRENT"
    assert (
        "Tuition is published only as a range, 27,650–34,670 GBP; the cost uses its upper "
        "bound, so it is not understated."
    ) in payload["funding_gap"]["warnings"]


@pytest.mark.asyncio
async def test_kb_mode_names_a_stale_range_as_published_range(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(
        tuition=[
            _fact(
                "tuition",
                {"min": 42554.0, "max": 51106.0, "currency": "USD"},
                "Non-Resident Tuition $42,554-$51,106",
                period="year",
                academic_year="2026-27",
            )
        ]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["costs"]["items"] == {}
    reason = payload["funding_gap"]["reason"]
    assert "published range 42,554–51,106 USD a year, academic year 2026-27 (not current:" in reason


@pytest.mark.asyncio
async def test_kb_mode_never_multiplies_a_per_credit_rate(
    catalogue_session, profile, settings, tmp_path, no_network
):
    entry = _mit_entry(
        tuition=[
            _fact(
                "tuition",
                {"amount": 1789.18, "currency": "CAD"},
                "Science $1,789.18",
                period="credit",
                academic_year="2027/28",
            )
        ]
    )
    _run_, payload = await _funding_run(catalogue_session, profile, settings, tmp_path, entry)
    assert payload["costs"]["items"] == {} and payload["costs"]["total"] is None
    reason = payload["funding_gap"]["reason"]
    assert payload["funding_gap"]["computable"] is False
    assert (
        "1,789 CAD per credit, academic year 2027/28 (published per credit (no yearly figure "
        "printed))" in reason
    )


# ------------------------------------------- REL-1: no standalone CS bachelor

LSE = "qs2027-062"
RELATED_URL = "https://www.mit.edu/admissions/synthetic-related"
LSE_URL = "https://www.lse.ac.uk/study/synthetic-data-science"


def _related_batch(root: Path) -> None:
    """MIT: a related route only (Sydney-like); LSE: not offered, with its closest programme."""
    _write(
        root / "batch1/programme" / f"{MIT}.0-related.json",
        {
            "case": MIT,
            "note": "word for word. Related, not the programme: MIT has no bachelor titled "
            "Computer Science; it is a major inside Course 6. More notes.",
            "programme": {"url": RELATED_URL, "title": "Course 6-3"},
            "related_programme_urls": [RELATED_URL],
            "related_programmes": ["Course 6-3 (major: Computer Science)"],
            "accessed_on": "2026-10-18",
            "answers": {},
        },
    )
    _write(
        root / "batch1/programme" / f"{LSE}.0-related.json",
        {
            "case": LSE,
            "note": "NONE: LSE offers no bachelor in Computer Science; the closest is BSc Data "
            "Science.",
            "programme": {"url": LSE_URL, "title": "BSc Data Science"},
            "programme_offered": False,
            "related_programme_urls": [LSE_URL],
            "related_programmes": ["BSc Data Science (N3UD)"],
            "accessed_on": "2026-10-19",
            "answers": {},
        },
    )


def test_the_build_keeps_why_there_is_no_programme_page(tmp_path):
    _related_batch(tmp_path / "drafts")
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [_row("programme", RELATED_URL), {**_row("programme", LSE_URL), "case": LSE}],
    )
    entries = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")["entries"]
    mit, lse = entries[MIT]["programme"], entries[LSE]["programme"]
    assert mit["status"] == "unknown" and "offered" not in mit
    assert mit["related_reason"] == {
        "statement": "MIT has no bachelor titled Computer Science; it is a major inside Course 6.",
        "name": "Course 6-3 (major: Computer Science)",
        "url": RELATED_URL,
        "verified": True,
        "checked_on": "2026-10-18",
    }
    assert lse["offered"] is False
    assert lse["related_reason"]["name"] == "BSc Data Science (N3UD)"
    assert lse["related_reason"]["statement"] == (
        "LSE offers no bachelor in Computer Science; the closest is BSc Data Science."
    )


def test_an_entry_with_a_programme_page_gains_no_new_field(tmp_path):
    _batch(tmp_path / "drafts")
    report = _report(tmp_path / "evidence_check.ci-2026-10-20.json", [_row("programme", URL)])
    entry = kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-21")["entries"][MIT]
    assert set(entry["programme"]) == {"status", "urls", "evidence", "related_programme_urls"}


def _route_entry(**programme: Any) -> dict[str, Any]:
    entry = _mit_entry(english=[_fact("ielts.overall", 6.5, "IELTS 6.5 overall")])
    entry["programme"] = {"status": "unknown", "urls": [], "evidence": [], **programme}
    return entry


_REASON = {
    "statement": "No CS bachelor.",
    "name": "Course 6-3 (major: Computer Science)",
    "url": RELATED_URL,
    "verified": True,
    "checked_on": "2026-10-18",
}


@pytest.mark.parametrize(
    "programme,route",
    [
        ({"related_reason": _REASON}, "related_only"),
        ({"related_reason": _REASON, "offered": False}, "not_offered"),
        ({"offered": False}, "not_offered"),
        ({}, "unknown"),
    ],
)
def test_programme_route(tmp_path, programme, route):
    kb = load_knowledge_base(
        _kb(tmp_path / "kb.json", {MIT: _route_entry(**programme)}), tmp_path / "none.json"
    )
    assert kb.entries[MIT].programme_route == route
    known = load_knowledge_base(
        _kb(tmp_path / "known.json", {MIT: _mit_entry()}), tmp_path / "none.json"
    )
    assert known.entries[MIT].programme_route == "known"


def test_the_import_does_not_hide_a_route_the_built_file_settled(tmp_path):
    kb = load_knowledge_base(
        _kb(tmp_path / "kb.json", {MIT: _route_entry(related_reason=_REASON)}),
        _kb(tmp_path / "imported.json", {MIT: _route_entry()}),
    )
    assert kb.entries[MIT].programme_route == "related_only"
    # A verified page in the import still wins over a related route.
    kb = load_knowledge_base(
        _kb(tmp_path / "kb2.json", {MIT: _route_entry(related_reason=_REASON)}),
        _kb(tmp_path / "imported2.json", {MIT: _mit_entry()}),
    )
    assert kb.entries[MIT].programme_route == "known"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "programme,blocking,text",
    [
        (
            {"related_reason": _REASON},
            False,
            "No standalone bachelor's in Computer Science is published; the closest official "
            f"route is Course 6-3 (major: Computer Science) (official page: {RELATED_URL}). "
            "Does that route suit you?",
        ),
        (
            {"related_reason": _REASON, "offered": False},
            False,
            "Massachusetts Institute of Technology publishes no bachelor's in Computer "
            "Science (checked 2026-10-18).",
        ),
        ({}, True, "Which official page publishes the"),
    ],
)
async def test_the_three_routes_are_said_and_only_an_unsettled_one_blocks(
    catalogue_session, profile, settings, tmp_path, no_network, programme, blocking, text
):
    _run_, payload = await _funding_run(
        catalogue_session, profile, settings, tmp_path, _route_entry(**programme)
    )
    (question,) = [q for q in payload["unresolved"] if q["topic"] == "official source"]
    assert question["blocking"] is blocking
    assert question["question"].startswith(text)
    if not blocking:
        assert question["suggested_contact"] == RELATED_URL
        assert "Which official page" not in question["question"]


# ----------------------------------------------- WHY-1: why a value is unknown

KINDS_TABLE = (
    Path(kb_build.__file__).parent / "data/kb_drafts.2026-10-19" / kb_build.UNKNOWN_KINDS_FILE
)


def _kinds(root: Path, rows: list[dict[str, Any]]) -> None:
    _write(root / kb_build.UNKNOWN_KINDS_FILE, {"rows": rows})


def test_the_build_takes_the_kind_from_the_reviewed_table(tmp_path):
    root = tmp_path / "drafts"
    _batch(root)
    _kinds(
        root,
        [
            {"seed_id": MIT, "question": "deadline", "kind": "access"},
            {"seed_id": MIT, "question": "gpa", "key": "gpa", "kind": "not_published"},
        ],
    )
    report = _report(tmp_path / "evidence_check.ci-2026-10-20.json", [_row("english", URL)])
    entry = kb_build.build(root, [report], built_at="2026-10-21")["entries"][MIT]
    kinds = {u["question"]: u["kind"] for u in entry["unknown"]}
    assert kinds["deadline"] == "access"
    assert kinds["gpa"] == "not_published"
    # A record the table does not list is never guessed.
    assert kinds["tuition"] == "unspecified"
    # Each record says when its draft was researched.
    assert {u["checked_on"] for u in entry["unknown"]} == {"2026-10-19"}
    # The facts are untouched.
    assert [f["key"] for f in entry["facts"]["english"]] == ["ielts.overall"]


def test_the_build_without_a_table_marks_every_unknown_unspecified(tmp_path):
    _batch(tmp_path / "drafts")
    data = kb_build.build(tmp_path / "drafts", [], built_at="2026-10-21")
    assert {u["kind"] for u in data["entries"][MIT]["unknown"]} == {"unspecified"}


def test_the_build_refuses_a_kind_outside_the_vocabulary(tmp_path):
    root = tmp_path / "drafts"
    _batch(root)
    _kinds(root, [{"seed_id": MIT, "question": "gpa", "kind": "probably_none"}])
    with pytest.raises(ValueError, match="UNKNOWN_KINDS"):
        kb_build.build(root, [], built_at="2026-10-21")


def test_the_committed_table_covers_every_unknown_of_the_committed_kb():
    """The main session's rebuild leaves no v21 unknown ``unspecified``."""
    from evaluation.research.expert.unknown_kinds import validate

    rows = json.loads(KINDS_TABLE.read_text(encoding="utf-8"))["rows"]
    assert validate(rows) == []
    listed = {(r["seed_id"], r["question"]) for r in rows}
    kb = json.loads((Path(kb_build.KB_FILE)).read_text(encoding="utf-8"))
    missing = {
        (seed, u["question"])
        for seed, entry in kb["entries"].items()
        for u in entry["unknown"]
        if (seed, u["question"]) not in listed
    }
    assert missing == set()


@pytest.mark.parametrize(
    "reason,kind",
    [
        ("expert value 90 is not in the quoted excerpt.", "unverified_quote"),
        ("The quoted date carries no year; a deadline written without a year", "undated"),
        ("Access failure: www.example.edu returns HTTP 403 (CloudFront)", "access"),
        ("only the 2026/2027 fee is published, not 2027/28", "other_year"),
        ("No minimum GPA published; holistic review.", "not_published"),
        ("Expert draft 2026-10-19.", "not_researched"),
    ],
)
def test_the_seed_keyword_table(reason, kind):
    from evaluation.research.expert.unknown_kinds import classify

    assert classify(reason) == kind


def test_a_re_seed_never_rewrites_a_reviewed_row():
    from evaluation.research.expert.unknown_kinds import merge

    reviewed = [{"seed_id": MIT, "question": "gpa", "key": "gpa", "kind": "not_researched"}]
    seeded = [
        {"seed_id": MIT, "question": "gpa", "key": "gpa", "kind": "not_published"},
        {"seed_id": MIT, "question": "deadline", "key": "deadline", "kind": "access"},
    ]
    assert merge(reviewed, seeded) == [reviewed[0], seeded[1]]


def _why_entry() -> dict[str, Any]:
    entry = _mit_entry(english=[_fact("ielts.overall", 7.0, "IELTS 7.0 overall")])
    entry["unknown"] = [
        # A missing TOEFL beside a verified IELTS leaves no empty cell.
        {"question": "english", "key": "english_evidence.toefl_ibt.minimum", "kind": "access"},
        {"question": "gpa", "key": "gpa", "kind": "not_published", "checked_on": "2026-10-19"},
        {"question": "tuition", "key": "tuition", "kind": "access", "checked_on": "2026-10-19"},
        {"question": "deadline", "key": "deadline", "checked_on": "2026-10-20"},
        {"question": "scholarship_exists", "key": "scholarships", "kind": "invented"},
    ]
    return entry


def test_unknown_reasons_list_only_unanswered_questions(tmp_path):
    kb = load_knowledge_base(_kb(tmp_path / "kb.json", {MIT: _why_entry()}), tmp_path / "x.json")
    assert kb.entries[MIT].unknown_reasons() == [
        {"question": "gpa", "kind": "not_published", "checked_on": "2026-10-19"},
        {"question": "tuition", "kind": "access", "checked_on": "2026-10-19"},
        {"question": "deadline", "kind": "unspecified", "checked_on": "2026-10-20"},
        {"question": "scholarship_exists", "kind": "unspecified", "checked_on": None},
    ]


@pytest.mark.asyncio
async def test_a_kb_row_carries_why_each_question_is_unknown(
    catalogue_session, profile, settings, tmp_path, no_network
):
    _run_, payload = await _funding_run(
        catalogue_session, profile, settings, tmp_path, _why_entry()
    )
    assert payload["kb_unknown"][:2] == [
        {"question": "gpa", "kind": "not_published", "checked_on": "2026-10-19"},
        {"question": "tuition", "kind": "access", "checked_on": "2026-10-19"},
    ]
    # Nothing is asked and nothing blocks because of it.
    assert not any("not published" in q["question"] for q in payload["unresolved"])


@pytest.mark.asyncio
async def test_a_row_with_every_question_answered_has_no_kb_unknown_key(
    catalogue_session, profile, settings, tmp_path, no_network
):
    _run_, payload = await _funding_run(
        catalogue_session, profile, settings, tmp_path, _mit_entry()
    )
    assert "kb_unknown" not in payload
