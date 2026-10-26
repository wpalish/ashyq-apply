"""Measurement ID-1 / D2 (core-gap analysis 2026-10-18, change 3).

ID-1: NTU serves the Nanyang Global Scholarship at ``/admissions/ug/…/detail/
nanyang-scholarship``; the bindings spell it ``/admissions/undergraduate/…``.
The pipeline read the right award with the right values in every repetition
and the scorer filed it as ``unmapped.*``. A binding now also matches the same
award page under another path of the same host — the final path segment, which
names the award, must be the binding's — and only with the binding's exact
subject.

D2: NTU's signed SAT label is ``english_evidence.sat.minimum`` (SAT is one of
its English-proficiency alternatives) while every other case, and the claim
mapping, use ``sat.minimum``. A ``sat.minimum`` prediction is scored under the
English-evidence key only for a case that knows that key and not its own.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import pytest

from evaluation.research.identities import Binding, IdentityMap, same_award_page
from evaluation.research.live import REVIEWED_BINDINGS, load_identities
from evaluation.research.mapping import normalize_subject_claims
from evaluation.research.metrics import score, scored_key
from evaluation.research.schema import Capture, Dataset, Evidence, Label, Observation, Prediction
from evaluation.research.scorecard import label_outcomes

DATA = Path(__file__).resolve().parents[1] / "evaluation/research/data"
NANYANG = "Nanyang Global Scholarship"
BOUND = (
    "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
    "scholarship-opportunities/detail/nanyang-scholarship"
)
LIVE = "https://www.ntu.edu.sg/admissions/ug/scholarships/scholarship-opportunities/detail/nanyang-scholarship"


@pytest.fixture(autouse=True)
def _id1_on(monkeypatch):
    """ID-1 is on by default since the owner signed it (02-Q1/Q2, 2026-10-18);
    these tests pin it on so a later default cannot silently change them."""
    from evaluation.research import identities, metrics

    monkeypatch.setattr(identities, "ID1_URL_ALIAS", True)
    monkeypatch.setattr(
        metrics, "GOLD_KEY_ALIASES", {"sat.minimum": "english_evidence.sat.minimum"}
    )


def test_id1_is_on_by_default():
    from evaluation.research import identities, metrics

    # The autouse fixture pins the URL alias on, so read its default from source.
    assert "ID1_URL_ALIAS = True" in Path(identities.__file__).read_text()
    assert metrics.ID1_SCORER_ALIASES is True


def _reviewed() -> IdentityMap:
    return IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text(encoding="utf-8"))


def _award(url: str, subject: str = NANYANG, key: str = "scholarships.nanyang_global") -> Binding:
    return Binding(kind="award", source_url=url, subject=subject, key=key, notes="test")  # type: ignore[arg-type]


class TestAwardUrlAlias:
    def test_the_live_ntu_path_resolves_to_the_bound_award(self) -> None:
        assert _reviewed().resolve("award", LIVE, NANYANG) == "scholarships.nanyang_global"

    def test_the_three_read_claims_land_on_their_corpus_keys(self) -> None:
        identities = load_identities(
            [DATA / "identity_bindings.draft2.json", DATA / "identity_bindings.dev2-draft1.json"]
        )
        raw = {"subject_key": NANYANG, "source_url": LIVE}
        mapped = {
            claim_type: normalize_subject_claims(
                claim_type, {**raw, "normalized_value": value}, identities
            )[0][:2]
            for claim_type, value in (
                ("scholarship_exists", NANYANG),
                ("scholarship_citizenship_restriction", "all"),
                ("scholarship_international_eligible", True),
            )
        }
        assert mapped == {
            "scholarship_exists": ("scholarships.nanyang_global.exists", True),
            "scholarship_citizenship_restriction": (
                "scholarships.nanyang_global.applicability.nationality",
                "all",
            ),
            "scholarship_international_eligible": (
                "scholarships.nanyang_global.applicability.international",
                True,
            ),
        }

    def test_the_exact_url_still_resolves(self) -> None:
        assert _reviewed().resolve("award", BOUND, NANYANG) == "scholarships.nanyang_global"

    @pytest.mark.parametrize(
        ("url", "subject"),
        [
            # another award's page on the same host
            (
                "https://www.ntu.edu.sg/admissions/ug/scholarships/scholarship-opportunities/"
                "detail/asean-undergraduate-scholarship",
                NANYANG,
            ),
            # the same slug on another host
            (
                "https://www.example.edu.sg/admissions/ug/scholarships/detail/nanyang-scholarship",
                NANYANG,
            ),
            # the right page, another award's name
            (LIVE, "ASEAN Undergraduate Scholarship"),
            # a FAQ under the same tree
            ("https://www.ntu.edu.sg/admissions/ug/scholarships/faqs-on-scholarships", NANYANG),
        ],
        ids=["other-award", "other-host", "other-subject", "faq"],
    )
    def test_not_an_alias(self, url: str, subject: str) -> None:
        assert _reviewed().resolve("award", url, subject) is None

    def test_a_query_is_part_of_the_page(self) -> None:
        assert not same_award_page(BOUND, LIVE + "?id=2", NANYANG)

    def test_a_generic_final_segment_names_no_award(self) -> None:
        bound = "https://www.uni.example/study/scholarships/"
        assert not same_award_page(bound, "https://www.uni.example/ug/scholarships", "Uni Award")
        assert same_award_page(
            "https://www.uni.example/a/uni-award.php",
            "https://www.uni.example/b/uni-award.php",
            "Uni Award",
        )

    def test_a_slug_that_is_not_the_award_name_is_no_alias(self) -> None:
        assert not same_award_page(
            "https://www.uni.example/a/detail/12345",
            "https://www.uni.example/b/detail/12345",
            "Uni Award",
        )

    def test_two_bindings_that_disagree_bind_neither(self) -> None:
        identities = IdentityMap(
            version="t",
            bindings=[
                _award("https://www.ntu.edu.sg/a/nanyang-scholarship", key="scholarships.one"),
                _award("https://www.ntu.edu.sg/b/nanyang-scholarship", key="scholarships.two"),
            ],
        )
        assert (
            identities.resolve("award", "https://www.ntu.edu.sg/c/nanyang-scholarship", NANYANG)
            is None
        )
        assert (
            identities.resolve("award", "https://www.ntu.edu.sg/a/nanyang-scholarship", NANYANG)
            == "scholarships.one"
        )

    def test_two_spellings_of_one_award_agree(self) -> None:
        identities = IdentityMap(
            version="t",
            bindings=[
                _award(BOUND),
                _award(BOUND.replace("/scholarships/", "/scholarships-and-awards/")),
            ],
        )
        assert identities.resolve("award", LIVE, NANYANG) == "scholarships.nanyang_global"

    def test_documents_are_not_aliased(self) -> None:
        identities = IdentityMap(
            version="t",
            bindings=[
                Binding(
                    kind="document",
                    source_url=BOUND,  # type: ignore[arg-type]
                    subject="Nanyang essay",
                    key="documents.scholarship.nanyang_global.essay",
                    notes="test",
                )
            ],
        )
        assert identities.resolve("document", BOUND, "Nanyang essay") is not None
        assert identities.resolve("document", LIVE, "Nanyang essay") is None


def _label(key: str, status: Literal["known", "unknown"] = "known") -> Label:
    # Only the key and status matter here; a known label's evidence is not read.
    return Label.model_construct(key=key, status=status, value=1250 if status == "known" else None)


class TestSatKeyAlias:
    def test_a_case_that_files_the_sat_under_english_evidence(self) -> None:
        labels = {
            "sat.minimum": _label("sat.minimum", "unknown"),
            "english_evidence.sat.minimum": _label("english_evidence.sat.minimum"),
        }
        assert scored_key("sat.minimum", labels) == "english_evidence.sat.minimum"

    def test_a_case_that_knows_its_own_sat_key_keeps_it(self) -> None:
        labels = {
            "sat.minimum": _label("sat.minimum"),
            "english_evidence.sat.minimum": _label("english_evidence.sat.minimum"),
        }
        assert scored_key("sat.minimum", labels) == "sat.minimum"
        assert scored_key("sat.minimum", {"sat.minimum": _label("sat.minimum", "unknown")}) == (
            "sat.minimum"
        )
        assert scored_key("ielts.overall", labels) == "ielts.overall"

    def test_ntu_scores_a_read_sat_1250_as_its_english_evidence_label(self) -> None:
        dataset = Dataset.model_validate_json(
            (DATA / "ground_truth.reviewed11.json").read_text(encoding="utf-8")
        )
        ntu = next(c for c in dataset.cases if c.id == "ntu")
        url = "https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements"
        prediction = Prediction(
            key="sat.minimum",
            value=1250,
            evidence=Evidence(
                url=url,  # type: ignore[arg-type]
                excerpt="SAT Total score – 1250",
                # As the pipeline records the section (reviewed11, 02-Q2: the
                # label's population is "international").
                scope=ntu.request.model_copy(
                    update={"degree": "bachelor", "population": "international"}
                ),
                accessed_on=date(2026, 10, 18),
                source_type="official",
            ),
        )
        capture = Capture(
            pipeline_sha="test",
            captured_at="2026-10-18T00:00:00Z",
            mode="synthetic",
            config={},
            observations=[Observation(case_id="ntu", predictions=[prediction])],
        )
        one = dataset.model_copy(update={"cases": [ntu]})
        outcomes = label_outcomes(one, capture)
        assert {x["key"]: x["outcome"] for x in outcomes["labels"]}[
            "english_evidence.sat.minimum"
        ] == "hit"
        report = score(one, capture)
        assert report["fields"]["english_evidence.sat.minimum"]["recall"]["numerator"] == 1
        assert report["metrics"]["claim_precision"]["value"] == 1.0
