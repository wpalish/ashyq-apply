"""Application documents in the verified knowledge base: converter, loader, kb-mode checklist.

Offline: the kb-mode runs use the ``no_network`` fixture, which fails the test on
any search provider, live discovery or page read.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import select

from app.adapters.documents.web_documents import document_rule
from app.domain.enums import ClaimStatus, ClaimType, DocumentOwner, UserDecision
from app.knowledge import QUESTIONS, carried_stale_reasons, load_knowledge_base
from app.knowledge import _entry as kb_entry
from app.knowledge.claims import answer
from app.knowledge.documents import (
    DOCUMENT_KINDS,
    EXTRA_KINDS,
    LIVE_KINDS,
    document_kind,
    kb_checklist,
)
from app.models import ClaimRow, ProgramResultRow
from app.pipeline.runner import ResearchRunner
from evaluation.research.expert import kb_build
from evaluation.research.expert.kb_refresh_diff import current_stale_reasons
from scripts import verify_evidence
from tests import test_knowledge_base as kb_tests
from tests.test_knowledge_base import (
    MIT,
    URL,
    _fact,
    _full_batch,
    _funding_settings,
    _kb,
    _mit_entry,
    _report,
    _row,
    _run,
    _write,
)

#: The KB tests' fixtures: an imported catalogue, and no network or search at all.
catalogue_session = kb_tests.catalogue_session
no_network = kb_tests.no_network

DOCS_URL = "https://www.mit.edu/admissions/synthetic-documents"


def _doc(kind: str, quote: str, requirement: str = "required", **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "requirement": requirement, "url": DOCS_URL, "quote": quote, **extra}


def _documents_answer(*items: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "status": "known",
        "population": "international",
        "academic_year": None,
        "items": list(items),
        **extra,
    }


def _doc_row(kind: str, url: str = DOCS_URL, **extra: Any) -> dict[str, Any]:
    return {**_row(f"documents.{kind}", url), **extra}


# ------------------------------------------------------------------ vocabulary


def test_every_kind_uses_the_live_reader_names_owners_and_flags():
    assert set(LIVE_KINDS).isdisjoint(EXTRA_KINDS)
    assert set(LIVE_KINDS) | set(EXTRA_KINDS) == DOCUMENT_KINDS
    for kind, name in LIVE_KINDS.items():
        rule = document_rule(name)
        assert rule is not None, kind
        assert document_kind(kind) == (name, *rule)
    english = document_kind("english_test_report")
    assert english == ("English language test report", DocumentOwner.THIRD_PARTY, {})
    assert document_kind("horoscope") is None
    assert QUESTIONS[-1] == "documents"


# ------------------------------------------------------------------- converter


def test_converter_keeps_only_verified_quoted_documents(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "researched_on": "2026-10-19",
            "answers": {
                "documents": _documents_answer(
                    _doc("transcript", "Official transcripts from every school attended"),
                    _doc(
                        "translation",
                        "Documents not in English need a certified translation.",
                        "conditional",
                        condition="documents are not in English",
                    ),
                    _doc("cv", "A CV is optional.", "optional"),
                    {
                        **_doc("passport", "Copy of your passport"),
                        "url": "https://elsewhere.example/p",
                    },
                    _doc("portfolio", "Portfolio"),  # no evidence row
                    _doc("horoscope", "Your horoscope"),
                    _doc("essay", "An essay if asked", "conditional"),  # no condition
                    _doc("transcript", "Transcripts again"),
                )
            },
        },
    )
    report = _report(
        tmp_path / "evidence_check.ci-2026-10-20.json",
        [
            _doc_row("transcript"),
            _doc_row("translation"),
            _doc_row("cv"),
            _doc_row("passport", "https://elsewhere.example/p", official=False),
            _doc_row("horoscope"),
            _doc_row("essay"),
        ],
    )
    entry = kb_build.build(root, [report], built_at="2026-10-21")["entries"][MIT]
    facts = {f["key"]: f for f in entry["facts"]["documents"]}
    assert list(facts) == ["documents.transcript", "documents.translation", "documents.cv"]
    transcript = facts["documents.transcript"]
    assert transcript["value"] == {
        "kind": "transcript",
        "requirement": "required",
        "condition": None,
    }
    assert transcript["quote"] == "Official transcripts from every school attended"
    assert transcript["source_url"] == DOCS_URL and transcript["source_type"] == "official"
    assert transcript["population"] == "international"
    assert transcript["verified_on"] == "2026-10-20" and transcript["verified_by"] == "ci"
    assert transcript["stale"] is False
    assert facts["documents.translation"]["value"]["condition"] == "documents are not in English"
    assert facts["documents.cv"]["value"]["requirement"] == "optional"
    reasons = {u["key"]: u["reason"] for u in entry["unknown"] if u["question"] == "documents"}
    assert "not an official domain" in reasons["documents.passport"]
    assert reasons["documents.portfolio"] == "no evidence-check row"
    assert "not in the document vocabulary" in reasons["documents.horoscope"]
    assert "without its condition" in reasons["documents.essay"]
    assert entry["known_fact_count"] == 3


def test_converter_marks_a_past_year_document_list_stale_and_keeps_unknown_reasons(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "answers": {
                "documents": _documents_answer(
                    _doc("transcript", "Transcripts", academic_year="2025/26")
                )
            },
        },
    )
    report = _report(tmp_path / "evidence_check.ci-2026-10-20.json", [_doc_row("transcript")])
    data = kb_build.build(root, [report], built_at="2026-10-21")
    (fact,) = data["entries"][MIT]["facts"]["documents"]
    assert fact["stale"] is True and "academic year 2025/26 is past" in fact["stale_reasons"]
    assert {"seed_id": MIT, "question": "documents"}.items() <= data["stale_facts"][0].items()

    _write(
        root / "batch1/core" / f"{MIT}.json",
        {"case": MIT, "answers": {"documents": {"status": "unknown", "notes": "HTTP 403"}}},
    )
    entry = kb_build.build(root, [report], built_at="2026-10-21")["entries"][MIT]
    assert entry["facts"]["documents"] == []
    assert {"question": "documents", "key": "documents", "reason": "HTTP 403"} in entry["unknown"]


OTHER_CYCLE = 'document list published for "2027 Spring Admissions Guide", not the fall 2027 intake'


def test_converter_marks_a_list_for_another_cycle_stale_with_the_printed_cycle(tmp_path):
    root = tmp_path / "drafts"
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "answers": {
                "documents": _documents_answer(
                    _doc("transcript", "Transcripts"),
                    # An item's own judgement wins over the answer's.
                    _doc("passport", "Passport", cycle_is_intake=True),
                    _doc("cv", "CV", cycle_stated="Last  Update:\n02/12/2021"),
                    cycle_stated="2027 Spring Admissions Guide",
                    cycle_is_intake=False,
                ),
            },
        },
    )
    rows = [_doc_row("transcript"), _doc_row("passport"), _doc_row("cv")]
    report = _report(tmp_path / "evidence_check.ci-2026-10-20.json", rows)
    data = kb_build.build(root, [report], built_at="2026-10-21")
    facts = {f["key"]: f for f in data["entries"][MIT]["facts"]["documents"]}
    transcript = facts["documents.transcript"]
    assert transcript["stale"] is True and transcript["stale_reasons"] == [OTHER_CYCLE]
    assert transcript["cycle_stated"] == "2027 Spring Admissions Guide"
    assert transcript["academic_year"] is None  # never inferred from the cycle text
    passport = facts["documents.passport"]
    assert passport["stale"] is False and passport["cycle_stated"] == (
        "2027 Spring Admissions Guide"
    )
    cv = facts["documents.cv"]
    assert cv["stale_reasons"] == [
        'document list published for "Last Update: 02/12/2021", not the fall 2027 intake'
    ]
    stale = {f["key"] for f in data["stale_facts"]}
    assert stale == {"documents.transcript", "documents.cv"}

    # A printed cycle the expert judged to be the intake's is recorded, not stale.
    _write(
        root / "batch1/core" / f"{MIT}.json",
        {
            "case": MIT,
            "answers": {
                "documents": _documents_answer(
                    _doc("transcript", "Transcripts"), cycle_stated="Fall 2027"
                )
            },
        },
    )
    (fact,) = kb_build.build(root, [report], built_at="2026-10-21")["entries"][MIT]["facts"][
        "documents"
    ]
    assert fact["stale"] is False and fact["cycle_stated"] == "Fall 2027"
    assert "stale_reasons" not in fact


@pytest.mark.parametrize("intake", ["fall 2027", "spring 2027", "fall 2028"])
def test_another_cycles_list_stays_stale_for_every_intake(intake):
    fact = _doc_fact(
        "transcript", "Transcripts", stale=True, stale_reasons=[OTHER_CYCLE], cycle_stated="x"
    )
    assert carried_stale_reasons(fact, intake) == [OTHER_CYCLE]
    entry = kb_entry(MIT, _mit_entry(documents=[fact]), "kb.json")
    found = kb_checklist(entry, university="MIT", programme="CS", intake=intake)
    assert found is not None
    checklist, (claim,) = found
    assert claim.status is ClaimStatus.POSSIBLY_STALE
    assert checklist.completeness == "partial"
    item = checklist.admission_documents[0]
    assert item.format_notes == f"Possibly outdated: {OTHER_CYCLE}."
    assert OTHER_CYCLE in checklist.unresolved[0].why_it_matters
    assert "not as confirmed" in checklist.unresolved[0].why_it_matters
    # The refresh recomputes only the date-based reasons; this one is kept.
    kept = current_stale_reasons(fact, date(2026, 11, 1), intake)
    assert kept == [OTHER_CYCLE]


def test_a_documents_only_top_up_merges_without_becoming_the_base(tmp_path):
    root = tmp_path / "drafts"
    _full_batch(root)
    reports = sorted(root.glob("*/evidence_check.*.json"))
    before = kb_build.build(root, reports, built_at="2026-10-21")["entries"][MIT]
    # "topup_documents1" sorts before "topup_imported"-like dirs; it is still merged in.
    _write(
        root / "topup_a_documents/core" / f"{MIT}.json",
        {
            "case": MIT,
            "seed_id": MIT,
            "answers": {"documents": _documents_answer(_doc("transcript", "Transcripts"))},
        },
    )
    _report(root / "topup_a_documents/evidence_check.ci-2026-10-20.json", [_doc_row("transcript")])
    _write(
        root / "topup_b_core/core" / f"{MIT}.json",
        {"case": MIT, "seed_id": MIT, "answers": {}},
    )
    _report(root / "topup_b_core/evidence_check.ci-2026-10-20.json", [])
    reports = sorted(root.glob("*/evidence_check.*.json"))
    entry = kb_build.build(root, reports, built_at="2026-10-21")["entries"][MIT]
    assert entry["source_batch"] == "batch1"
    assert entry["source_batches"] == ["batch1", "topup_b_core", "topup_a_documents"]
    for question in ("english", "tuition", "deadline"):
        assert entry["facts"][question] == before["facts"][question] != []
    (doc,) = entry["facts"]["documents"]
    assert doc["source_batch"] == "topup_a_documents"
    # A batch row for the same URL never verifies a top-up's quote: scoped per dir.
    _report(root / "topup_a_documents/evidence_check.ci-2026-10-20.json", [])
    _report(root / "batch1/evidence_check.ci-2026-10-19.json", [_doc_row("transcript")])
    reports = sorted(root.glob("*/evidence_check.*.json"))
    entry = kb_build.build(root, reports, built_at="2026-10-21")["entries"][MIT]
    assert entry["facts"]["documents"] == []


def test_verify_evidence_checks_each_listed_document_on_its_own():
    draft = {
        "case": MIT,
        "answers": {
            "documents": _documents_answer(_doc("transcript", "T"), _doc("cv", "C", "optional"))
        },
    }
    rows = verify_evidence.items(draft)
    assert ("documents.transcript", "known", DOCS_URL, "T") in rows
    assert ("documents.cv", "known", DOCS_URL, "C") in rows
    unknown = {"case": MIT, "answers": {"documents": {"status": "unknown"}}}
    assert ("documents", "unknown", None, None) in verify_evidence.items(unknown)
    assert not [r for r in verify_evidence.items({"case": MIT}) if r[0].startswith("documents")]

    kb = {
        "entries": {
            MIT: {
                "facts": {
                    "documents": [{"key": "documents.cv", "source_url": DOCS_URL, "quote": "C"}],
                    "english": [{"key": "ielts.overall", "source_url": URL, "quote": "I"}],
                }
            }
        }
    }
    targets = verify_evidence.kb_targets(kb)
    assert {t.item for t in targets} == {"documents.cv", "english"}
    assert [t.item for t in verify_evidence.kb_targets(kb, only={"documents"})] == ["documents.cv"]
    assert verify_evidence.parse_only("documents") == {"documents"}


# ---------------------------------------------------------------------- loader


def _doc_fact(kind: str, quote: str, requirement: str = "required", **extra: Any):
    condition = extra.pop("condition", None)
    return _fact(
        f"documents.{kind}",
        {"kind": kind, "requirement": requirement, "condition": condition},
        quote,
        source_url=DOCS_URL,
        population="international",
        **extra,
    )


def test_loader_reads_and_merges_document_facts(tmp_path):
    built = _kb(
        tmp_path / "kb.json",
        {MIT: _mit_entry(documents=[_doc_fact("transcript", "Old transcript rule")])},
    )
    newer = _doc_fact("transcript", "New transcript rule", verified_on="2026-10-20")
    imported = _kb(
        tmp_path / "imp.json",
        {MIT: _mit_entry(documents=[newer, _doc_fact("cv", "CV")])},
    )
    entry = load_knowledge_base(built, imported).entries[MIT]
    quotes = sorted(f["quote"] for f in entry.facts["documents"])
    assert quotes == ["CV", "New transcript rule"]
    # Document facts are not row claims: the document stage builds them.
    found = answer(entry, programme="CS", intake="fall 2027", academic_year="2027/28")
    assert ClaimType.REQUIRED_DOCUMENT not in {c.claim_type for c in found.claims}
    only_docs = _kb(
        tmp_path / "docs-only.json",
        {MIT: {**_mit_entry(documents=[_doc_fact("cv", "CV")]), "programme": {}}},
    )
    assert load_knowledge_base(only_docs, tmp_path / "none.json").entries[MIT].has_verified_data


# ------------------------------------------------------------- checklist (pure)


def test_kb_checklist_builds_the_live_checklist_objects():
    entry = kb_entry(
        MIT,
        _mit_entry(
            documents=[
                _doc_fact("transcript", "Official transcripts"),
                _doc_fact("recommendation_letter", "Two letters of recommendation"),
                _doc_fact(
                    "translation",
                    "Translate documents not in English.",
                    "conditional",
                    condition="documents are not in English",
                ),
                _doc_fact("cv", "A CV is optional.", "optional"),
                _doc_fact("entrance_test", "Sit the TMUA.", academic_year="2027/28"),
            ]
        ),
        "kb.json",
    )
    found = kb_checklist(entry, university="MIT", programme="CS", intake="fall 2027")
    assert found is not None
    checklist, claims = found
    assert checklist.completeness == "official" and checklist.unresolved == []
    items = {d.name: d for d in checklist.admission_documents}
    transcript = items["Full academic transcript"]
    owner, flags = document_rule("Full academic transcript") or (None, {})
    assert transcript.owner is owner is DocumentOwner.SCHOOL
    assert transcript.lead_time_days == flags["lead_time_days"]
    assert transcript.needs_translation is True and transcript.required is True
    assert transcript.source_url == DOCS_URL and transcript.claim_ids == [DOCS_URL]
    assert transcript.scope is not None and transcript.scope.population == "international"
    translation = items["Certified English translation of non-English documents"]
    assert translation.required is False
    assert translation.format_notes == "Required only when: documents are not in English."
    assert items["Curriculum vitae"].format_notes == "Optional, as published."
    test = items["Admission test result"]
    assert test.owner is DocumentOwner.THIRD_PARTY and test.lead_time_days is None
    assert [d.name for d in checklist.recommender_actions] == ["Letter of recommendation"]
    assert [d.name for d in checklist.school_actions] == ["Full academic transcript"]
    assert checklist.ordered_steps[0].startswith("1. Your referee: Letter of recommendation")

    assert {c.claim_type for c in claims} == {ClaimType.REQUIRED_DOCUMENT}
    by_quote = {c.original_text_excerpt: c for c in claims}
    official = by_quote["Official transcripts"]
    assert official.normalized_value == "Full academic transcript"
    assert official.official_domain is True and official.confidence == 0.8
    assert official.status is ClaimStatus.VERIFIED_CURRENT
    assert by_quote["Translate documents not in English."].normalized_value == {
        "document": "Certified English translation of non-English documents",
        "requirement": "conditional",
        "condition": "documents are not in English",
    }


def test_kb_checklist_shows_stale_documents_as_partial_and_says_why():
    raw = _mit_entry(
        documents=[
            _doc_fact("transcript", "Transcripts", verified_on="2025-01-01"),
            _doc_fact("passport", "Passport", academic_year="2026/27"),
        ]
    )
    raw["unknown"] = [{"question": "documents", "key": "documents.cv", "reason": "HTTP 403"}]
    entry = kb_entry(MIT, raw, "kb.json")
    found = kb_checklist(entry, university="MIT", programme="CS", intake="fall 2027")
    assert found is not None
    checklist, claims = found
    assert checklist.completeness == "partial"
    assert {c.status for c in claims} == {ClaimStatus.POSSIBLY_STALE}
    transcript = checklist.admission_documents[0]
    assert transcript.format_notes.startswith("Possibly outdated: verified on 2025-01-01")
    topics = [(q.topic, q.blocking) for q in checklist.unresolved]
    assert topics == [("required documents", False), ("required documents", False)]
    assert "still the one for the fall 2027 intake" in checklist.unresolved[0].question
    assert "academic year 2026/27 is before" in checklist.unresolved[0].why_it_matters
    assert "1 document item(s)" in checklist.unresolved[1].why_it_matters
    assert (
        kb_checklist(
            kb_entry(MIT, _mit_entry(), "kb.json"),
            university="MIT",
            programme="CS",
            intake="fall 2027",
        )
        is None
    )


def test_the_stale_documents_question_is_keyed_for_ru_and_kk_readers():
    """Every stale reason in the question, the build's other-cycle one too, has a key."""
    from app.domain.message_keys import annotate_question, stale_reasons

    item, answer = {"cycle_stated": "Admission Guide, 2026", "cycle_is_intake": False}, {}
    _cycle, other = kb_build.other_cycle_reason(item, answer, "fall 2027")
    passport = _doc_fact("passport", "Passport", academic_year="2026/27", verified_on="2025-01-01")
    passport["stale_reasons"] = [other]
    entry = kb_entry(MIT, _mit_entry(documents=[passport]), "kb.json")
    found = kb_checklist(
        entry, university="MIT", programme="CS", intake="fall 2027", today=date(2026, 10, 19)
    )
    assert found is not None
    checklist, claims = found
    question = checklist.unresolved[0]
    annotate_question(question)
    assert question.question_message is not None
    assert question.question_message.key == "question.documentListCurrent"
    assert question.question_message.params == {
        "programme": "CS",
        "university": "MIT",
        "intake": "fall 2027",
    }
    why = question.why_message
    assert why is not None and why.key == "why.documentsNotCurrent"
    [doc] = why.parts["documents"]
    assert doc is not None and doc.key == "stale.documentItem"
    # The name holds its own parentheses; the reasons are still found after it.
    assert doc.params["document"] == "Passport identity page (copy)"
    assert [r.key for r in doc.parts["reasons"] if r] == [
        "stale.tooOld",
        "stale.yearBeforeIntake",
        "stale.documentsForCycle",
    ]
    assert doc.parts["reasons"][-1].params["cycle"] == "Admission Guide, 2026"  # type: ignore[union-attr]
    keyed = stale_reasons(claims[0].notes)
    assert keyed is not None and all(keyed) and len(keyed) == 3


# ----------------------------------------------------------- kb-mode document stage


async def _approve_and_collect(session, profile, settings, run) -> dict[str, Any]:
    row = session.scalars(select(ProgramResultRow).where(ProgramResultRow.run_id == run.id)).one()
    row.user_decision = UserDecision.APPROVED.value
    session.commit()
    built = await ResearchRunner(session, run, profile, settings).collect_documents()
    session.refresh(row)
    return {"built": built, "payload": dict(row.payload), "checklist": row.checklist}


@pytest.mark.asyncio
async def test_kb_mode_document_stage_builds_the_checklist_from_the_kb(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    entry = _mit_entry(
        english=[_fact("ielts.overall", 7.0, "IELTS 7.0 overall")],
        documents=[
            _doc_fact("transcript", "Official transcripts"),
            _doc_fact("english_test_report", "IELTS or TOEFL score report"),
        ],
    )
    kb_settings = _funding_settings(settings, tmp_path, entry)
    run = await _run(s, profile, kb_settings, "Massachusetts Institute")
    out = await _approve_and_collect(s, profile, kb_settings, run)
    assert out["built"] == 1 and run.stage == "completed" and run.pages_checked == 0
    checklist = out["checklist"]
    assert checklist["completeness"] == "official"
    assert [d["name"] for d in checklist["admission_documents"]] == [
        "Full academic transcript",
        "English language test report",
    ]
    assert checklist["result_id"] == out["payload"]["id"]
    questions = " ".join(q["why_it_matters"] for q in out["payload"]["unresolved"])
    assert "does not hold document lists yet" not in questions
    docs = [c for c in out["payload"]["claims"] if c["claim_type"] == "required_document"]
    assert {c["original_text_excerpt"] for c in docs} == {
        "Official transcripts",
        "IELTS or TOEFL score report",
    }
    assert all(c["is_stale"] is False and c["official_domain"] for c in docs)
    assert DOCS_URL in out["payload"]["source_urls"]
    stored = s.scalars(
        select(ClaimRow).where(
            ClaimRow.run_id == run.id, ClaimRow.claim_type == "required_document"
        )
    ).all()
    assert len(stored) == 2

    # Collecting again refreshes the same claims instead of adding copies.
    again = await _approve_and_collect(s, profile, kb_settings, run)
    assert again["built"] == 1
    stored = s.scalars(
        select(ClaimRow).where(
            ClaimRow.run_id == run.id, ClaimRow.claim_type == "required_document"
        )
    ).all()
    assert len(stored) == 2 and {r.status for r in stored} == {"VERIFIED_CURRENT"}


@pytest.mark.asyncio
async def test_kb_mode_document_stage_marks_stale_document_claims(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    entry = _mit_entry(documents=[_doc_fact("transcript", "Transcripts", verified_on="2025-01-01")])
    kb_settings = _funding_settings(settings, tmp_path, entry)
    run = await _run(s, profile, kb_settings, "Massachusetts Institute")
    out = await _approve_and_collect(s, profile, kb_settings, run)
    assert out["checklist"]["completeness"] == "partial"
    (claim,) = [c for c in out["payload"]["claims"] if c["claim_type"] == "required_document"]
    assert claim["status"] == "POSSIBLY_STALE" and claim["is_stale"] is True


@pytest.mark.asyncio
async def test_kb_mode_without_document_facts_still_asks(
    catalogue_session, profile, settings, tmp_path, no_network
):
    s = catalogue_session
    entry = _mit_entry(english=[_fact("ielts.overall", 7.0, "IELTS 7.0 overall")])
    kb_settings = _funding_settings(settings, tmp_path, entry)
    run = await _run(s, profile, kb_settings, "Massachusetts Institute")
    out = await _approve_and_collect(s, profile, kb_settings, run)
    assert out["built"] == 0 and out["checklist"] is None
    (question,) = [q for q in out["payload"]["unresolved"] if q["topic"] == "documents"]
    assert "does not hold document lists yet" in question["why_it_matters"]

    # The KB gains the list: the next collection builds it and drops that question.
    entry["facts"]["documents"] = [_doc_fact("transcript", "Transcripts")]
    (tmp_path / "later").mkdir()
    later = _funding_settings(settings, tmp_path / "later", entry)
    again = await _approve_and_collect(s, profile, later, run)
    assert again["built"] == 1 and again["checklist"]["completeness"] == "official"
    assert not [q for q in again["payload"]["unresolved"] if q["topic"] == "documents"]

    law = profile.model_copy(
        update={"context": profile.context.model_copy(update={"intended_fields": ["law"]})}
    )
    docs = _mit_entry(documents=[_doc_fact("transcript", "Transcripts")])
    (tmp_path / "law").mkdir()
    docs_settings = _funding_settings(settings, tmp_path / "law", docs)
    run = await _run(s, law, docs_settings, "Massachusetts Institute")
    out = await _approve_and_collect(s, law, docs_settings, run)
    assert out["built"] == 0 and out["checklist"] is None
    # MIT holds a list - for Computer Science. "No lists yet" would be false (D5).
    (question,) = [q for q in out["payload"]["unresolved"] if q["topic"] == "documents"]
    assert "does not hold document lists yet" not in question["why_it_matters"]
    assert "answers only for the bachelor's in Computer Science" in question["why_it_matters"]


@pytest.mark.asyncio
async def test_kb_mode_document_question_for_a_university_outside_the_kb_says_so(
    catalogue_session, profile, settings, tmp_path, no_network
):
    """KB v10 smoke D5: AUT, not in the KB, was told the KB holds no document lists yet.

    It has no entry at all. Its document question now says so, in the words
    (and message key) of its own "No verified data yet" question.
    """
    from app.domain.message_keys import WHYS, match

    s = catalogue_session
    entry = _mit_entry(documents=[_doc_fact("transcript", "Transcripts")])
    kb_settings = _funding_settings(settings, tmp_path, entry)
    run = await _run(s, profile, kb_settings, "Stanford")
    out = await _approve_and_collect(s, profile, kb_settings, run)
    assert out["built"] == 0 and out["checklist"] is None
    (question,) = [q for q in out["payload"]["unresolved"] if q["topic"] == "documents"]
    assert "does not hold document lists yet" not in question["why_it_matters"]
    assert "has no entry in the verified knowledge base" in question["why_it_matters"]
    ref = match(WHYS, question["why_it_matters"])
    assert ref is not None and ref.key == "why.noKbEntry"
    (no_data,) = [q for q in out["payload"]["unresolved"] if q["topic"] == "verified data"]
    assert no_data["why_it_matters"] == question["why_it_matters"]
