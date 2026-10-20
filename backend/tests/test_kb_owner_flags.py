"""The two pending owner decisions on the KB, both off by default.

* ``--yearless-deadlines-with-caveat`` (``KB_YEARLESS_DEADLINES_WITH_CAVEAT``):
  a verified deadline whose quote prints day and month but no year is kept,
  its year inferred from the intake's application cycle, with a caveat;
* ``--standing-fee-policy-current`` (``KB_STANDING_FEE_POLICY_CURRENT``, Q7):
  a listed standing fee policy that prints no academic year is current, with a
  caveat; it enters the yearly cost table only when its period is a year.

Offline: synthetic drafts and reports only.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from app.domain.enums import ClaimStatus, ClaimType, CostCategory
from app.domain.message_keys import CAVEATS, annotate_claim, caveat_of
from app.knowledge import (
    STANDING_FEE_POLICY_CAVEAT,
    YEAR_INFERRED_CAVEAT,
    fact_caveat,
    load_knowledge_base,
)
from app.knowledge.claims import answer
from app.schemas.claim import ClaimOut
from evaluation.research.expert import kb_build

MIT = "qs2027-001"
ETH = "qs2027-008"  # a listed standing fee policy
URL = "https://www.mit.edu/admissions/synthetic"
ETH_URL = "https://ethz.ch/fees/synthetic"


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _draft(root: Path, case: str, **answers: dict[str, Any]) -> None:
    _write(
        root / "batch1/core" / f"{case}.json",
        {"case": case, "researched_on": "2026-10-19", "answers": answers},
    )


def _ci(tmp_path: Path, case: str, item: str, url: str) -> Path:
    path = tmp_path / "evidence_check.ci-2026-10-19.json"
    rows = json.loads(path.read_text()) if path.exists() else []
    rows.append(
        {"case": case, "item": item, "url": url, "outcome": "ok", "official": True,
         "quote_found": True}
    )  # fmt: skip
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _deadline(value: str, quote: str, notes: str = "") -> dict[str, Any]:
    return {"status": "known", "value": value, "url": URL, "quote": quote, "notes": notes}


def _build(tmp_path: Path, report: Path, **flags: Any) -> dict[str, Any]:
    return kb_build.build(tmp_path / "drafts", [report], built_at="2026-10-19", **flags)


# ------------------------------------------------------------ the cycle rule


@pytest.mark.parametrize(
    ("month", "intake", "year"),
    [
        (1, "fall 2027", 2027),  # January: the spring before the fall start
        (7, "fall 2027", 2027),  # July: the last month read as the intake year
        (8, "fall 2027", 2026),  # August: the first month read as the year before
        (10, "fall 2027", 2026),  # UCAS 15 October
        (12, "Fall 2027", 2026),
        (3, "autumn 2028", 2028),
        (9, "autumn 2028", 2027),
    ],
)
def test_the_application_cycle_rule(month, intake, year):
    assert kb_build.application_cycle_year(month, intake) == year


@pytest.mark.parametrize("intake", ["spring 2027", "winter 2027", "2027", "", "fall"])
def test_no_cycle_rule_outside_a_fall_intake(intake):
    assert kb_build.application_cycle_year(1, intake) is None


def test_the_day_and_month_the_quote_prints():
    days = kb_build.quoted_day_months
    assert days("Regular Decision (Deadline: January 2)") == {(2, 1)}
    assert days("Jan. 1 Application with Princeton-specific Questions Due") == {(1, 1)}
    assert days("15 January: Last day to apply") == {(15, 1)}
    assert days("Bewerbungsfristen 15. Juli für das Wintersemester") == {(15, 7)}
    assert days("Für das 1. Fachsemester mit Start im WS: 01.06.-15.07.") == {(1, 6), (15, 7)}
    assert days("Meld je voor 1 mei aan in Studielink") == {(1, 5)}
    assert days("Sista anmälningsdag är normalt den 15 april") == {(15, 4)}
    assert days("申报时间 3月1日至5月15日") == {(1, 3), (15, 5)}
    assert days("December 1st") == {(1, 12)}
    assert days("Updated July 2026") == set()


# ------------------------------------------------------- yearless deadlines


def test_off_a_yearless_deadline_stays_unknown(tmp_path):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline("2027-01-15", "Apply by January 15"))
    data = _build(
        tmp_path,
        _ci(tmp_path, MIT, "deadline", URL),
        yearless_deadlines_with_caveat=False,
        standing_fee_policy_current=False,
    )
    entry = data["entries"][MIT]
    assert entry["facts"]["deadline"] == []
    assert any("carries no year" in u["reason"] for u in entry["unknown"])
    assert "owner_flags" not in data and "caveat_facts" not in data


def test_both_owner_flags_are_on_by_default():
    # Owner decision 2026-10-20: yes to both.
    assert kb_build.KB_YEARLESS_DEADLINES_WITH_CAVEAT is True
    assert kb_build.KB_STANDING_FEE_POLICY_CURRENT is True
    assert "qs2027-049" not in kb_build.STANDING_FEE_POLICIES  # UCLA: a dated current-year page


def test_a_yearless_deadline_is_kept_with_the_inferred_year_and_a_caveat(tmp_path):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline("2027-01-15", "Apply by January 15"))
    data = _build(
        tmp_path,
        _ci(tmp_path, MIT, "deadline", URL),
        yearless_deadlines_with_caveat=True,
        standing_fee_policy_current=False,
    )
    entry = data["entries"][MIT]
    (fact,) = entry["facts"]["deadline"]
    assert fact["value"] == "2027-01-15" and fact["year_inferred"] == 2027
    assert fact["caveat"] == YEAR_INFERRED_CAVEAT
    assert fact["period"] == "fall 2027" and not fact["stale"]
    assert not any(u["key"] == "deadline" for u in entry["unknown"])
    assert data["owner_flags"] == {
        "yearless_deadlines_with_caveat": True,
        "standing_fee_policy_current": False,
    }
    assert [c["seed_id"] for c in data["caveat_facts"]] == [MIT]


def test_an_autumn_month_is_read_as_the_year_before_and_is_stale_once_passed(tmp_path):
    _draft(
        tmp_path / "drafts",
        MIT,
        deadline=_deadline("2026-10-15", "The UCAS deadline is 6pm (UK time) on 15 October"),
    )
    data = _build(
        tmp_path, _ci(tmp_path, MIT, "deadline", URL), yearless_deadlines_with_caveat=True
    )
    (fact,) = data["entries"][MIT]["facts"]["deadline"]
    assert fact["value"] == "2026-10-15" and fact["year_inferred"] == 2026
    assert fact["stale"] and fact["stale_reasons"] == ["deadline 2026-10-15 has passed"]


@pytest.mark.parametrize(
    ("value", "quote", "notes", "why"),
    [
        ("2026-11-01", "Early Decision deadline: November 1", "", "another intake or round"),
        ("2027-05-31", "Semester 2 - May 31 of the year of commencement", "", "round"),
        ("2027-01-15", "15. Januar für das Sommersemester", "", "another intake or round"),
        ("2027-01-15", "Apply by January 15 (2025 entry)", "", "another cycle's year"),
        ("2026-01-15", "Apply by January 15", "", "the expert dated it 2026"),
        ("2027-01-15", "Apply by mid-January", "", "does not print this day and month"),
        (
            "2027-01-15",
            "Apply by January 15",
            "Only the 2026 entry cycle is published",
            "another cycle",
        ),
    ],
)
def test_a_yearless_deadline_is_refused_when_the_quote_does_not_back_the_year(
    tmp_path, value, quote, notes, why
):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline(value, quote, notes))
    data = _build(
        tmp_path, _ci(tmp_path, MIT, "deadline", URL), yearless_deadlines_with_caveat=True
    )
    entry = data["entries"][MIT]
    assert entry["facts"]["deadline"] == []
    (unknown,) = [u for u in entry["unknown"] if u["key"] == "deadline"]
    assert "Year not inferred" in unknown["reason"] and why in unknown["reason"]
    assert data["caveat_facts"] == []


def test_a_yearless_deadline_needs_the_ci_check(tmp_path):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline("2027-01-15", "Apply by January 15"))
    report = _ci(tmp_path, MIT, "english", URL)  # no deadline row
    data = _build(tmp_path, report, yearless_deadlines_with_caveat=True)
    assert data["entries"][MIT]["facts"]["deadline"] == []


def test_no_inference_for_an_intake_without_a_cycle_rule(tmp_path):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline("2027-01-15", "Apply by January 15"))
    data = kb_build.build(
        tmp_path / "drafts",
        [_ci(tmp_path, MIT, "deadline", URL)],
        built_at="2026-10-19",
        intake="spring 2027",
        yearless_deadlines_with_caveat=True,
    )
    assert data["entries"][MIT]["facts"]["deadline"] == []


def test_a_dated_deadline_is_untouched_by_the_flag(tmp_path):
    _draft(tmp_path / "drafts", MIT, deadline=_deadline("2027-01-05", "Apply by 5 January 2027"))
    report = _ci(tmp_path, MIT, "deadline", URL)
    off = _build(tmp_path, report)["entries"][MIT]["facts"]["deadline"]
    on = _build(tmp_path, report, yearless_deadlines_with_caveat=True)
    assert on["entries"][MIT]["facts"]["deadline"] == off and "caveat" not in off[0]


# -------------------------------------------------------- standing fee policy


def _fee(amount: float, currency: str, period: str, year: Any, quote: str) -> dict[str, Any]:
    value = {"amount": amount, "currency": currency, "period": period, "academic_year": year}
    return {"status": "known", "value": value, "url": ETH_URL, "quote": quote}


def test_off_a_standing_policy_fee_stays_stale(tmp_path):
    _draft(tmp_path / "drafts", ETH, tuition=_fee(2190, "CHF", "semester", None, "CHF 2190 / sem"))
    data = _build(
        tmp_path, _ci(tmp_path, ETH, "tuition", ETH_URL), standing_fee_policy_current=False
    )
    (fee,) = data["entries"][ETH]["facts"]["tuition"]
    assert fee["stale"] and "the academic year is not stated" in fee["stale_reasons"]
    assert "caveat" not in fee


@pytest.mark.parametrize(
    "stated",
    [None, "not stated", "since winter semester 2017/18 (no academic year stated)"],
)
def test_a_listed_standing_policy_fee_is_current_with_a_caveat(tmp_path, stated):
    _draft(tmp_path / "drafts", ETH, tuition=_fee(2190, "CHF", "semester", stated, "CHF 2190"))
    data = _build(
        tmp_path, _ci(tmp_path, ETH, "tuition", ETH_URL), standing_fee_policy_current=True
    )
    (fee,) = data["entries"][ETH]["facts"]["tuition"]
    assert not fee["stale"] and "stale_reasons" not in fee
    assert fee["caveat"] == STANDING_FEE_POLICY_CAVEAT and fee["standing_policy"] is True
    assert fee["academic_year"] is None and fee.get("academic_year_stated") == stated
    assert fee["period"] == "semester"
    assert [c["seed_id"] for c in data["caveat_facts"]] == [ETH]


def test_a_fee_for_a_stated_year_or_off_the_list_is_not_a_standing_policy(tmp_path):
    _draft(tmp_path / "drafts", ETH, tuition=_fee(2190, "CHF", "year", "2026/27", "CHF 2190"))
    _draft(tmp_path / "drafts", MIT, tuition={**_fee(60000, "USD", "year", None, "$60,000"),
                                              "url": URL})  # fmt: skip
    _ci(tmp_path, ETH, "tuition", ETH_URL)
    data = _build(tmp_path, _ci(tmp_path, MIT, "tuition", URL), standing_fee_policy_current=True)
    for seed in (ETH, MIT):
        (fee,) = data["entries"][seed]["facts"]["tuition"]
        assert fee["stale"] and "caveat" not in fee, seed


# ------------------------------------------------------- loader and claims


def _entry(tmp_path: Path, *facts: dict[str, Any]) -> Any:
    tuition = [f for f in facts if f["key"] == "tuition"]
    deadline = [f for f in facts if f["key"] == "deadline"]
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {
                "version": "t",
                "entries": {
                    ETH: {
                        "seed_id": ETH,
                        "university": "ETH Zurich",
                        "official_domain": "ethz.ch",
                        "review_status": "expert_checked",
                        "verified_on": "2026-10-19",
                        "programme": {"status": "unknown"},
                        "facts": {"tuition": tuition, "deadline": deadline},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return load_knowledge_base(path, tmp_path / "none.json").get(ETH)


def _fact(key: str, value: Any, **extra: Any) -> dict[str, Any]:
    return {
        "key": key, "value": value, "source_url": ETH_URL, "quote": "q",
        "verified_on": "2026-10-19", "accessed_on": "2026-10-19", **extra,
    }  # fmt: skip


def _answer(entry: Any, today: date = date(2026, 10, 19)) -> Any:
    return answer(entry, programme="CS", intake="fall 2027", academic_year="2027/28", today=today)


def test_a_yearly_standing_policy_fee_fills_the_cost_table_with_its_caveat(tmp_path):
    fee = _fact(
        "tuition",
        {"amount": 535800, "currency": "JPY"},
        period="year",
        caveat=STANDING_FEE_POLICY_CAVEAT,
    )
    result = _answer(_entry(tmp_path, fee))
    (claim,) = result.claims
    assert claim.status is ClaimStatus.VERIFIED_CURRENT
    assert f"Caveat: {STANDING_FEE_POLICY_CAVEAT}." in claim.notes
    assert result.costs.items[CostCategory.TUITION].amount == 535800


def test_a_per_semester_standing_policy_fee_stays_out_of_the_cost_table(tmp_path):
    fee = _fact(
        "tuition",
        {"amount": 2190, "currency": "CHF"},
        period="semester",
        caveat=STANDING_FEE_POLICY_CAVEAT,
    )
    result = _answer(_entry(tmp_path, fee))
    (claim,) = result.claims
    assert claim.status is ClaimStatus.VERIFIED_CURRENT and "Amount per semester" in claim.notes
    assert CostCategory.TUITION not in result.costs.items


def test_an_inferred_deadline_is_current_with_its_caveat_then_stale_once_passed(tmp_path):
    deadline = _fact("deadline", "2027-01-15", year_inferred=2027)  # caveat lost: restored
    entry = _entry(tmp_path, deadline)
    assert fact_caveat(entry.facts["deadline"][0]) == YEAR_INFERRED_CAVEAT
    (now,) = _answer(entry).claims
    assert now.claim_type is ClaimType.ADMISSION_DEADLINE
    assert now.status is ClaimStatus.VERIFIED_CURRENT
    assert caveat_of(now.notes) == YEAR_INFERRED_CAVEAT
    (later,) = _answer(entry, today=date(2027, 2, 1)).claims
    assert later.status is ClaimStatus.POSSIBLY_STALE
    assert "deadline 2027-01-15 has passed" in later.notes
    assert caveat_of(later.notes) == YEAR_INFERRED_CAVEAT


def test_the_caveat_is_keyed_when_served_and_absent_otherwise(tmp_path):
    (claim,) = _answer(_entry(tmp_path, _fact("deadline", "2027-01-15", year_inferred=2027))).claims
    served = ClaimOut(**claim.model_dump(), id="c1")
    annotate_claim(served)
    assert served.caveat_message is not None and served.caveat_message.key == "caveat.yearInferred"
    plain = ClaimOut(
        id="c2", claim_type=ClaimType.TUITION, normalized_value=1, source_url="https://a.b/c",
        accessed_at=datetime.now(UTC), status=ClaimStatus.VERIFIED_CURRENT, notes="Verified.",
    )  # fmt: skip
    annotate_claim(plain)
    assert "caveat_message" not in plain.model_dump(mode="json")


def test_the_caveat_templates_are_the_build_caveats():
    assert {t.text for t in CAVEATS} == {YEAR_INFERRED_CAVEAT, STANDING_FEE_POLICY_CAVEAT}
