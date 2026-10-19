"""Heldout label audit (owner decision H-2, 2026-10-19): the proposed reviewed2 corpus loads.

Only the schema is checked here. The draft is unsigned, so no test asserts a label value: the
owner signs the lines in docs/process/HELDOUT_LABEL_AUDIT_2026-10-19.md, not this test.
"""

import json
from pathlib import Path

from evaluation.research import live
from evaluation.research.schema import Case, Dataset

DRAFT = Path(live.__file__).parent / "data" / "heldout.reviewed2.draft.json"
NINE = ["nu", "metu", "sabanci", "charles", "masaryk", "tum", "tartu", "polimi", "vilnius"]


def test_reviewed2_draft_parses_as_a_validation_dataset():
    dataset = Dataset.model_validate_json(DRAFT.read_text(encoding="utf-8"))
    assert dataset.version == "2026-10-19.heldout-reviewed2-draft"
    assert dataset.split == "validation"
    assert [case.id for case in dataset.cases] == NINE


def test_every_case_parses_in_the_case_schema_and_is_unsigned():
    raw = json.loads(DRAFT.read_text(encoding="utf-8"))
    for item in raw["cases"]:
        case = Case.model_validate(item)
        assert case.review.status == "draft"
        assert case.review.reviewer is None and case.review.verified_on is None
        assert all(label.evidence for label in case.labels if label.status != "unknown")
