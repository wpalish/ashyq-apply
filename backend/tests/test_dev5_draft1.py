import json
from pathlib import Path

from app.adapters.discovery.live_discovery import registrable_domain
from evaluation.research import live
from evaluation.research.expert import core_drafts_dev5
from evaluation.research.identities import IdentityMap
from evaluation.research.schema import Dataset

DATA = Path(live.__file__).parent / "data"
EXPERT = Path(live.__file__).parent / "expert" / "data"
DEV5_IDS = "kbtu satbayev aitu hacettepe bilkent ytu upol zcu tud lmu unipd sapienza vilniustech"


def _dataset() -> Dataset:
    return Dataset.model_validate_json((DATA / "dev5.draft1.json").read_text(encoding="utf-8"))


def test_the_dev5_draft1_loads_as_an_unsigned_development_set_of_thirteen():
    dev5 = _dataset()
    assert dev5.version == "2026-10-19.dev5-draft1" and dev5.split == "development"
    assert [case.id for case in dev5.cases] == DEV5_IDS.split()
    assert {case.id for case in dev5.cases} == set(live.DEV5_DOMAINS)
    heldout_domains = set(live.HELDOUT.values())
    for case in dev5.cases:
        assert case.domain == live.DEV5_DOMAINS[case.id]
        assert case.dataset_version == dev5.version
        assert case.review.status == "draft" and case.review.reviewer is None
        assert case.university == live.dev2_entry(case.id)["name"]
        assert case.labels[0].key == "programme.exists"
        for label in case.labels:
            # Nothing is known without evidence from a passing CI evidence check.
            assert label.status == "unknown" or label.evidence, (case.id, label.key)
        for url in [*case.programme_urls, *case.related_programme_urls]:
            assert registrable_domain(str(url)) == case.domain
            assert registrable_domain(str(url)) not in heldout_domains
    bindings = IdentityMap.model_validate(
        json.loads((DATA / "identity_bindings.dev5-draft1.json").read_text(encoding="utf-8"))
    )
    assert bindings.version == dev5.version


def test_access_and_related_cases_keep_programme_status_unknown():
    cases = {case.id: case for case in _dataset().cases}
    for case_id in core_drafts_dev5.ACCESS:
        case = cases[case_id]
        assert case.programme_status == "unknown" and not case.programme_urls
        assert case.related_programme_urls and not case.programme_evidence
        assert all(label.status == "unknown" for label in case.labels)
        assert "ACCESS CASE" in case.review.notes
    for case_id in core_drafts_dev5.RELATED:
        case = cases[case_id]
        assert case.programme_status == "unknown" and not case.programme_urls
        assert case.related_programme_urls and case.labels[0].status == "known"
    for case_id in set(cases) - core_drafts_dev5.ACCESS - core_drafts_dev5.RELATED:
        assert cases[case_id].programme_status == "known", case_id


def test_the_converter_rebuilds_the_committed_dev5_files():
    data, bindings, _ = core_drafts_dev5.build(
        EXPERT / "programme_drafts_dev5.2026-10-19", EXPERT / "core_drafts_dev5.2026-10-19"
    )
    written = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    assert written == (DATA / "dev5.draft1.json").read_text(encoding="utf-8")
    assert bindings == json.loads(
        (DATA / "identity_bindings.dev5-draft1.json").read_text(encoding="utf-8")
    )


def test_an_unverified_quote_never_becomes_evidence():
    cases = {case.id: case for case in _dataset().cases}
    tud = cases["tud"]
    twin = "https://tu-dresden.de/studium/vor-dem-studium/studienangebot/sins/sins_studiengang?autoid=281"
    # The twin's quote was not found by the CI check: a URL of the programme, never evidence.
    assert twin in {str(u) for u in tud.programme_urls}
    assert twin not in {str(e.url) for e in tud.programme_evidence}
    assert twin not in {str(e.url) for e in tud.labels[0].evidence}
