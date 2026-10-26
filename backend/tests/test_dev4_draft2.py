import json
from pathlib import Path

from evaluation.research import live
from evaluation.research.identities import IdentityMap
from evaluation.research.schema import Dataset

DATA = Path(live.__file__).parent / "data"


def test_the_dev4_draft2_keeps_the_programme_rows_and_adds_unsigned_core_labels():
    draft1 = Dataset.model_validate_json((DATA / "dev4.draft1.json").read_text(encoding="utf-8"))
    draft2 = Dataset.model_validate_json((DATA / "dev4.draft2.json").read_text(encoding="utf-8"))
    assert draft2.version == "2026-10-18.dev4-draft2" and draft2.split == "development"
    before = {c.id: c for c in draft1.cases}
    assert {c.id for c in draft2.cases} == set(live.DEV4_DOMAINS)
    for case in draft2.cases:
        old = before[case.id]
        assert case.review.status == "draft"
        assert case.programme_urls == old.programme_urls
        assert case.related_programme_urls == old.related_programme_urls
        assert case.labels[0].key == "programme.exists"
        for label in case.labels[1:]:
            # Nothing is known without evidence from a passing evidence check.
            assert label.status == "unknown" or label.evidence
    bindings = IdentityMap.model_validate(
        json.loads((DATA / "identity_bindings.dev4-draft2.json").read_text(encoding="utf-8"))
    )
    assert bindings.version == draft2.version
