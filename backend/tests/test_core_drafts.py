"""Expert core drafts -> draft corpora: verification, mapping rules, merge, worksheet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.research.expert import core_drafts
from evaluation.research.identities import IdentityMap
from evaluation.research.schema import Dataset

REQUEST = {
    "university": "University of Groningen",
    "programme": None,
    "degree": "bachelor",
    "field": "computer science",
    "intake": "fall 2027",
    "population": None,
    "qualification": None,
    "academic_year": None,
}
RUG = "https://www.rug.nl/language"


def answer(status: str, value: Any = None, url: str = "", quote: str = "", notes: str = ""):
    return {"status": status, "value": value, "url": url, "quote": quote, "notes": notes}


def groningen_draft() -> dict[str, Any]:
    """Cohort: a conflicting IELTS, a verified deadline, an unverified fee."""
    return {
        "case": "groningen",
        "university": "University of Groningen",
        "researched_on": "2026-10-17",
        "programme": {"url": "https://www.rug.nl/bachelors/cs", "title": "Computing Science"},
        "answers": {
            "english": answer("known", {"ielts_overall": 6.0}, RUG, "IELTS Academic 6.0"),
            "gpa": answer("not_applicable", {"description": "No grade threshold."}, RUG, "VWO"),
            "deadline": answer(
                "known", "2027-05-01", "https://www.rug.nl/cs", "non-EU 01 May 2027"
            ),
            "tuition": answer(
                "known",
                {"amount": 19800, "currency": "EUR", "period": "year", "academic_year": "2027/28"},
                "https://www.rug.nl/cs",
                "2027-2028 € 19800",
            ),
            "scholarship_exists": answer(
                "known", {"name": "NL Scholarship"}, "https://www.rug.nl/nl", "NL Scholarship"
            ),
            "scholarship_international": answer(
                "known", True, "https://www.rug.nl/nl", "non-EEA nationals"
            ),
        },
    }


def tum_draft() -> dict[str, Any]:
    """Heldout: German requirement, SAT-only threshold, 2026 deadline, no award."""
    url = "https://www.tum.de/informatics"
    return {
        "case": "tum",
        "university": "Technical University of Munich (TUM)",
        "researched_on": "2026-10-17",
        "programme": {"url": url, "title": "Informatics B.Sc.", "teaching_language": "German"},
        "answers": {
            "english": answer("known", {"german_level": "DSH-2"}, url, "DSH-2 is required"),
            "gpa": answer(
                "known",
                {"description": "SAT total at least 1350", "value": 1350},
                url,
                "SAT total score at least 1350",
            ),
            "deadline": answer(
                "known",
                "2026-05-04",
                url,
                "2. März bis 4. Mai 2026",
                "THIS IS THE 2026/27 CYCLE.",
            ),
            "tuition": answer("unknown"),
            "scholarship_exists": answer(
                "not_applicable", None, url, "Only master awards.", "No bachelor award."
            ),
            "scholarship_international": answer("not_applicable", None, url, "n/a"),
        },
    }


def reviewed() -> dict[str, Any]:
    ev = {
        "url": "https://www.rug.nl/fse/language",
        "excerpt": "IELTS 6.5",
        "scope": REQUEST,
        "accessed_on": "2026-10-05",
        "source_type": "official",
        "excerpt_truncated": False,
    }
    return {
        "schema_version": "1",
        "version": "test.reviewed9",
        "split": "development",
        "cases": [
            {
                "id": "groningen",
                "dataset_version": "test.reviewed9",
                "university": "University of Groningen",
                "domain": "rug.nl",
                "country": "Netherlands",
                "site_types": ["large_sitemap"],
                "request": REQUEST,
                "programme_urls": ["https://www.rug.nl/bachelors/cs"],
                "programme_status": "known",
                "programme_evidence": [{**ev, "excerpt": "BSc"}],
                "labels": [
                    {
                        "key": "ielts.overall",
                        "status": "known",
                        "value": 6.5,
                        "evidence": [ev],
                        "critical": True,
                        "notes": "signed",
                    },
                    {
                        "key": "deadline",
                        "status": "unknown",
                        "value": None,
                        "evidence": [],
                        "critical": True,
                        "notes": "Not yet established.",
                    },
                ],
                "review": {
                    "status": "human_verified",
                    "prepared_by": "claude-opus-5",
                    "reviewer": "Owner",
                    "verified_on": "2026-10-05",
                    "notes": "signed",
                },
            }
        ],
    }


IDENTITIES = IdentityMap.model_validate({"version": "test", "bindings": []})


def passing(case: str, *items: str) -> list[dict[str, Any]]:
    return [
        {"case": case, "item": i, "official": True, "quote_found": True, "outcome": "fetched-ok"}
        for i in items
    ]


def report_for(rows: list[dict[str, Any]]) -> core_drafts.Report:
    return {(r["case"], r["item"]): r for r in rows}


ALL_TUM = ("programme", "english", "gpa", "deadline", "scholarship_exists")
#: Groningen without tuition: that row is absent from the report.
SOME_RUG = (*ALL_TUM, "scholarship_international")


def build(report: core_drafts.Report | None) -> core_drafts.Outputs:
    return core_drafts.build([groningen_draft(), tum_draft()], reviewed(), IDENTITIES, report)


def labels(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {label["key"]: label for label in case["labels"]}


def verified_outputs() -> core_drafts.Outputs:
    return build(report_for(passing("groningen", *SOME_RUG) + passing("tum", *ALL_TUM)))


def test_verified_known_becomes_known_label_with_evidence() -> None:
    out = verified_outputs()
    deadline = labels(out.cohort["cases"][0])["deadline"]
    assert deadline["status"] == "known"
    assert deadline["value"] == "2027-05-01"
    [ev] = deadline["evidence"]
    assert ev["url"] == "https://www.rug.nl/cs"
    assert ev["excerpt"] == "non-EU 01 May 2027"
    assert ev["accessed_on"] == "2026-10-17"
    assert ev["source_type"] == "official"
    assert ev["scope"]["intake"] == "fall 2027"
    Dataset.model_validate(out.cohort)


def test_unverified_known_becomes_unknown_with_note() -> None:
    out = verified_outputs()
    tuition = labels(out.cohort["cases"][0])["tuition"]
    assert tuition["status"] == "unknown"
    assert tuition["value"] is None and tuition["evidence"] == []
    assert tuition["notes"].startswith("expert value 19,800 EUR unverified: no evidence-check row")


def test_without_report_nothing_is_verified() -> None:
    out = build(None)
    for case in [*out.cohort["cases"], *out.heldout["cases"]]:  # type: ignore[index]
        for label in case["labels"]:
            if label["notes"].startswith("expert value"):
                assert label["status"] == "unknown"
                assert "unchecked" in label["notes"]
    assert "отчёта нет" in out.worksheet
    assert "| да |" not in out.worksheet


def test_2026_cycle_deadline_is_unknown() -> None:
    tum = labels(verified_outputs().heldout["cases"][0])  # type: ignore[index]
    assert tum["deadline"]["status"] == "unknown"
    assert "only the 2026 cycle is published" in tum["deadline"]["notes"]


def test_sat_threshold_is_not_a_gpa() -> None:
    gpa = labels(verified_outputs().heldout["cases"][0])["gpa"]  # type: ignore[index]
    assert gpa["status"] == "not_applicable"
    assert gpa["value"] is None
    assert "SAT total at least 1350" in gpa["notes"]


def test_german_requirement_makes_english_not_applicable() -> None:
    tum = labels(verified_outputs().heldout["cases"][0])  # type: ignore[index]
    assert tum["ielts.overall"]["status"] == "not_applicable"
    assert "German" in tum["ielts.overall"]["notes"]
    assert tum["ielts.subscores"]["status"] == "not_applicable"


def test_conflict_with_signed_known_is_reported_and_kept() -> None:
    out = verified_outputs()
    case = out.cohort["cases"][0]
    ielts = labels(case)["ielts.overall"]
    assert ielts["value"] == 6.5 and ielts["notes"] == "signed"
    assert "CONFLICT ielts.overall" in case["review"]["notes"]
    assert case["review"]["status"] == "draft" and case["review"]["reviewer"] is None
    section = out.worksheet.split("## Основные: добавления")[0]
    assert "было 6.5 → эксперт 6" in section
    assert "rug.nl/fse/language" in section and RUG in section


def test_unverified_conflict_is_still_reported() -> None:
    out = build(None)
    assert "было 6.5 → эксперт 6" in out.worksheet
    assert labels(out.cohort["cases"][0])["ielts.overall"]["value"] == 6.5


def test_scholarship_not_applicable_writes_no_keys() -> None:
    case = verified_outputs().heldout["cases"][0]  # type: ignore[index]
    assert not [k for k in labels(case) if k.startswith("scholarships")]
    assert "no scholarship keys written" in case["review"]["notes"]


def test_new_award_gets_a_draft_binding_and_keys() -> None:
    out = verified_outputs()
    rug = labels(out.cohort["cases"][0])
    assert rug["scholarships.nl.exists"]["value"] is True
    assert rug["scholarships.nl.applicability.international"]["status"] == "known"
    [binding] = out.bindings["bindings"]
    assert binding["key"] == "scholarships.nl"
    assert binding["notes"] == "expert draft 2026-10-17, unsigned"
    IdentityMap.model_validate(out.bindings)


def test_heldout_case_shape() -> None:
    out = verified_outputs()
    heldout = Dataset.model_validate(out.heldout)
    assert heldout.version == "2026-10-17.heldout-draft1"
    [tum] = heldout.cases
    assert (tum.domain, tum.country, tum.university) == (
        "tum.de",
        "Germany",
        "Technical University of Munich",
    )
    assert tum.programme_status == "known" and tum.review.status == "draft"
    assert tum.request.intake == "fall 2027"


def test_fee_for_an_earlier_year_is_unknown() -> None:
    [p] = core_drafts.propose_tuition(
        answer("known", {"amount": 7100, "currency": "EUR", "academic_year": "2026/27"}),
        {"excerpt": "7100 EUR", "scope": REQUEST},
        2027,
    )
    assert p.status == "unknown" and "only the 2026/27 fee is published" in p.notes


def test_cli_writes_valid_files_and_short_worksheet(tmp_path: Path) -> None:
    drafts = tmp_path / "experts"
    drafts.mkdir()
    for d in (groningen_draft(), tum_draft()):
        (drafts / f"{d['case']}.json").write_text(json.dumps(d), encoding="utf-8")
    (tmp_path / "r9.json").write_text(json.dumps(reviewed()), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"version": "t", "bindings": []}), "utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps(passing("tum", *ALL_TUM)), encoding="utf-8")
    out = tmp_path / "out"
    code = core_drafts.main(
        [
            str(drafts),
            "--evidence",
            str(report),
            "--reviewed",
            str(tmp_path / "r9.json"),
            "--bindings",
            str(tmp_path / "b.json"),
            "--out-cohort",
            str(out / "c.json"),
            "--out-heldout",
            str(out / "h.json"),
            "--out-bindings",
            str(out / "b.json"),
            "--worksheet",
            str(out / "w.md"),
        ]
    )
    assert code == 0
    cohort = Dataset.model_validate_json((out / "c.json").read_text(encoding="utf-8"))
    assert cohort.version == "2026-10-17.draft10" and cohort.split == "development"
    Dataset.model_validate_json((out / "h.json").read_text(encoding="utf-8"))
    worksheet = (out / "w.md").read_text(encoding="utf-8").splitlines()
    assert len(worksheet) <= 140
    assert worksheet[-1] == "Подписываю draft10 и heldout1"


def test_label_scope_keeps_only_what_a_page_states():
    """The request's field and intake are not stamped on a label (NTU wrong-scope, 2026-10-17)."""
    from evaluation.research.expert.core_drafts import label_scope

    scope = {
        "university": "U",
        "programme": None,
        "degree": "bachelor",
        "field": "computer science",
        "intake": "fall 2027",
        "population": None,
        "qualification": None,
        "academic_year": None,
    }
    assert label_scope(scope) == {**scope, "field": None, "intake": None}
