"""Finish-algorithm tickets 09 and 10: the owner-signed dev label lines (2026-10-18)."""

import json
from pathlib import Path

import pytest

from evaluation.research import live
from evaluation.research.identities import IdentityMap
from evaluation.research.metrics import canonical_url
from evaluation.research.schema import Case, Dataset

DATA = Path(live.__file__).parent / "data"


def _load(name: str) -> Dataset:
    return Dataset.model_validate_json((DATA / name).read_text(encoding="utf-8"))


def _case(dataset: Dataset, case_id: str) -> Case:
    return next(c for c in dataset.cases if c.id == case_id)


@pytest.mark.parametrize(
    ("draft2", "draft3", "version"),
    [
        ("dev2.draft2.json", "dev2.draft3.json", "2026-10-18.dev2-draft3"),
        ("dev3.draft2.json", "dev3.draft3.json", "2026-10-18.dev3-draft3"),
        ("dev4.draft2.json", "dev4.draft3.json", "2026-10-18.dev4-draft3"),
    ],
)
def test_draft3_keeps_the_cases_and_bumps_the_version(draft2: str, draft3: str, version: str):
    old, new = _load(draft2), _load(draft3)
    assert new.version == version and new.split == "development"
    assert [c.id for c in new.cases] == [c.id for c in old.cases]


@pytest.mark.parametrize(
    ("name", "case_id", "urls", "related"),
    [
        (
            "dev2.draft3.json",
            "tec",
            ["https://tec.mx/es/ingenieria-y-ciencias/ingenieria-en-tecnologias-computacionales"],
            [],
        ),
        (
            "dev2.draft3.json",
            "kaznu",
            [
                "https://welcome.kaznu.kz/ru/education_programs/bachelor/speciality/1730",
                "https://welcome.kaznu.kz/en/education_programs/bachelor/speciality/1730",
            ],
            [],
        ),
        (
            "dev2.draft3.json",
            "uct",
            ["https://sit.uct.ac.za/bsc-degrees"],
            [
                "https://sit.uct.ac.za/ba-informatics",
                "https://sit.uct.ac.za/bachelor-business-science-specialising-computer-science",
            ],
        ),
        (
            "dev2.draft3.json",
            "khalifa",
            [
                "https://www.ku.ac.ae/program/bsc-in-computer-science",
                "https://www.ku.ac.ae/ar/program/bsc-in-computer-science",
            ],
            ["https://www.ku.ac.ae/zmu"],
        ),
        (
            "dev3.draft3.json",
            "ntutw",
            ["https://www.csie.ntu.edu.tw/zh_tw/Admission/Announcement12"],
            [],
        ),
        ("dev3.draft3.json", "msu", ["https://pk.cs.msu.ru/bak_educational_programs"], []),
        (
            "dev3.draft3.json",
            "usp",
            [
                "https://bcc.ime.usp.br/",
                "https://www.icmc.usp.br/en/admission/undergraduate/computer-science",
            ],
            [],
        ),
    ],
)
def test_ticket_10_accepted_programme_pages(
    name: str, case_id: str, urls: list[str], related: list[str]
):
    case = _case(_load(name), case_id)
    assert case.programme_status == "known"
    assert [str(u) for u in case.programme_urls] == urls
    assert [str(u) for u in case.related_programme_urls] == related
    cited = {str(e.url) for e in case.programme_evidence}
    assert cited >= set(urls[:1]) | set(related)
    assert all(e.source_type == "official" for e in case.programme_evidence)


def test_ticket_10_unchanged_and_related_rows():
    dev3 = _load("dev3.draft3.json")
    assert _case(dev3, "utokyo").programme_status == "unknown"
    assert not _case(dev3, "utokyo").programme_urls
    old, new = _load("dev4.draft2.json"), _load("dev4.draft3.json")
    for case_id in ("vut", "boun", "itu"):
        assert _case(new, case_id).programme_urls == _case(old, case_id).programme_urls
        assert (
            _case(new, case_id).related_programme_urls == _case(old, case_id).related_programme_urls
        )
    taltech = [str(u) for u in _case(new, "taltech").related_programme_urls]
    assert taltech == [
        "https://taltech.ee/informaatika",
        "https://taltech.ee/infotehnoloogia-teaduskond/bakalaureuseope/informaatika",
    ]


def test_ticket_09_dev4_is_signed_with_ktu_gpa_unknown():
    old, new = _load("dev4.draft2.json"), _load("dev4.draft3.json")
    for case in new.cases:
        assert case.review.status == "human_verified" and case.review.reviewer == "Диас"
        assert "CERTIFIED 2026-10-18" in case.review.notes
        before = {lb.key: lb for lb in _case(old, case.id).labels}
        assert [lb.key for lb in case.labels] == list(before)
        for label in case.labels:
            if (case.id, label.key) == ("ktu", "gpa"):
                assert before[label.key].status == "known"
                assert label.status == "unknown" and label.value is None and not label.evidence
                assert "60% minimum average grade" in label.notes
            else:
                assert (label.status, label.value) == (
                    before[label.key].status,
                    before[label.key].value,
                )


def test_ticket_09_rwth_award_page_is_a_second_source_url():
    bindings = IdentityMap.model_validate(
        json.loads((DATA / "identity_bindings.dev4-draft3.json").read_text(encoding="utf-8"))
    )
    assert bindings.version == "2026-10-18.dev4-draft3"
    rwth = [b for b in bindings.bindings if b.key == "scholarships.deutschlandstipendium"]
    assert len(rwth) == 2 and len({b.subject for b in rwth}) == 1
    award = (
        "https://www.rwth-aachen.de/cms/root/studium/Im-Studium/Stipendien-Foerderung/"
        "Bildungsfonds-Deutschlandstipendium/~goap/Bildungsfonds-Deutschlandstipendium-/"
    )
    assert canonical_url(award) in {canonical_url(str(b.source_url)) for b in rwth}
    resolved = bindings.resolve("award", award, rwth[0].subject)
    assert resolved == "scholarships.deutschlandstipendium"
