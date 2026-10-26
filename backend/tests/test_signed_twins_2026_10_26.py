"""The owner's twin signatures of 2026-10-26 («Подтверждаю», TRACK_B_2026-10-26 §1).

reviewed12 (cohort), dev2-draft4 and dev3-draft4 are their predecessors plus the
signed twins in ``programme_urls``; nothing else moves. The bare-host rule of the
same signature lives in the scorer (``tests/test_scorer_bare_host_variant.py``).
"""

import json
from pathlib import Path

import pytest

from evaluation.research import live
from evaluation.research.metrics import adjudicate_programme_pages
from evaluation.research.schema import Case, Dataset, Observation

DATA = Path(live.__file__).parent / "data"

SIGNED = {
    ("ground_truth.reviewed11.json", "ground_truth.reviewed12.json", "2026-10-26.reviewed12"): {
        "hku": ["https://www.cs.hku.hk/programmes/undergraduate/beng-in-computer-science"],
        "ubc": [
            "https://vancouver.calendar.ubc.ca/faculties-colleges-and-schools/faculty-science/"
            "bachelor-science/computer-science"
        ],
    },
    ("dev2.draft3.json", "dev2.draft4.json", "2026-10-26.dev2-draft4"): {
        "uppsala": ["https://www.uu.se/en/study/programme-syllabus?query=2332"],
    },
    ("dev3.draft3.json", "dev3.draft4.json", "2026-10-26.dev3-draft4"): {
        "kuleuven": [
            "https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742/diploma_omschrijving",
            "https://www.kuleuven.be/opleidingen/bachelor-informatica",
            "https://www.kuleuven.be/programmes/opleidingen/bachelor-informatica",
        ],
    },
}


def _raw(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _case(dataset: Dataset, case_id: str) -> Case:
    return next(c for c in dataset.cases if c.id == case_id)


@pytest.mark.parametrize(("files", "twins"), list(SIGNED.items()))
def test_only_the_signed_twins_are_added(files: tuple[str, str, str], twins: dict) -> None:
    old_name, new_name, version = files
    old, new = _raw(old_name), _raw(new_name)
    Dataset.model_validate(new)
    assert new["version"] == version and new["split"] == old["split"] == "development"
    assert [c["id"] for c in new["cases"]] == [c["id"] for c in old["cases"]]
    for before, after in zip(old["cases"], new["cases"], strict=True):
        assert after["dataset_version"] == version
        added = twins.get(after["id"], [])
        assert after["programme_urls"] == before["programme_urls"] + added
        if not added:
            before["dataset_version"] = version
            assert after == before, after["id"]
            continue
        assert after["labels"] == before["labels"]
        assert after.get("related_programme_urls") == before.get("related_programme_urls")
        assert after["programme_status"] == before["programme_status"] == "known"
        assert (
            after["programme_evidence"][: len(before["programme_evidence"])]
            == (before["programme_evidence"])
        )
        assert {e["url"] for e in after["programme_evidence"]} <= set(after["programme_urls"])
        assert after["review"]["status"] == before["review"]["status"]
        assert after["review"]["notes"].startswith(before["review"]["notes"].rstrip())
        assert (
            "2026-10-26" in after["review"]["notes"] and "Подтверждаю" in after["review"]["notes"]
        )


@pytest.mark.parametrize(
    ("name", "case_id", "returned", "outcome"),
    [
        (new, case_id, url, "hit")
        for (_, new, _), twins in SIGNED.items()
        for case_id, urls in twins.items()
        for url in urls
    ]
    + [
        # Not signed: ubc's other campus stays wrong (DC-1's job), and the
        # kuleuven campus sub-pages were not part of the signature.
        (
            "ground_truth.reviewed12.json",
            "ubc",
            "https://cs.ok.ubc.ca/undergraduate/computer-science",
            "wrong",
        ),
        (
            "dev3.draft4.json",
            "kuleuven",
            "https://www.kuleuven.be/opleidingen/bachelor-informatica/kortrijk",
            "wrong",
        ),
    ],
)
def test_a_signed_twin_scores_a_hit(name: str, case_id: str, returned: str, outcome: str) -> None:
    case = _case(Dataset.model_validate(_raw(name)), case_id)
    observation = Observation(case_id=case_id, programme_urls=[returned])
    assert adjudicate_programme_pages(case, observation).outcome == outcome


def test_held_out_labels_are_not_touched() -> None:
    names = {new for (_, new, _) in SIGNED}
    assert not any("heldout" in name for name in names)
