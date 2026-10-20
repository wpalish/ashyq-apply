"""Gap B6: backend sentences carry a stable key the interface can localise.

The English is stored and served unchanged; a key and parameters ride beside it
on the way out, so a Russian or Kazakh reader sees the same sentence in their
language. These tests hold three promises:

- the sentences the pipeline really writes are recognised, with the right
  parameters (so a reworded generator that nobody re-keyed shows up here);
- nothing about it is stored, so saved runs and the golden demo do not move;
- every key has an English, Russian and Kazakh entry in the frontend
  catalogue, and the English there is the backend's template, word for word.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.conflicts import enforce_source_hierarchy
from app.domain.costs import compute_funding_gap
from app.domain.enums import (
    ClaimStatus,
    ClaimType,
    CostCategory,
    EligibilityStatus,
    FundingFit,
    SourceSpecificity,
)
from app.domain.funding import funding_fit_for
from app.domain.message_keys import (
    AXIS_REASONS,
    BUCKET_REASONS,
    CATALOGUE,
    CLASSIFICATION_SENTENCES,
    CONFLICT_LABELS,
    CONFLICT_RULES,
    CONFLICT_SUBJECTS,
    COVERAGE,
    DEGREE_REASONS,
    DOCUMENT_ITEMS,
    FUNDING,
    KNOCKOUTS,
    QUESTIONS,
    REQUIREMENT_EXPLANATIONS,
    REQUIREMENT_LABELS,
    STALE_REASONS,
    WHYS,
    _complete,
    annotate_conflict,
    annotate_result,
    conflict_why,
    match,
    match_sentences,
    stale_rates_message,
    stale_reason_message,
    stale_reasons,
)
from app.knowledge import stale_reasons as kb_stale_reasons
from app.schemas.claim import Claim, ClaimOut, MessageRef, UnresolvedQuestion
from app.schemas.money import Money
from app.schemas.result import CostBreakdown, FundingGap, ProgramResult, Scholarship
from tests.test_api import client, finished_run  # noqa: F401  (fixtures)

FRONTEND_CATALOGUE = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "i18n.results.ts"
)


def _runner_method(name: str):
    from app.pipeline.runner import ResearchRunner

    return getattr(ResearchRunner, name)


class TestTheSentencesThePipelineWritesAreRecognised:
    def test_no_verified_data_in_and_out_of_the_kb_scope(self, monkeypatch, profile):
        import app.pipeline.runner as runner

        cand = SimpleNamespace(name="Example University")
        prog = SimpleNamespace(name="Computer Science")
        for in_scope, key, why in (
            (True, "question.noVerifiedDataInScope", "why.noKbEntry"),
            (False, "question.noVerifiedDataOutOfScope", "why.kbOutOfScope"),
        ):
            monkeypatch.setattr(runner, "covers", lambda _p, value=in_scope: value)
            q = _runner_method("_no_verified_data")(SimpleNamespace(profile=profile), cand, prog)
            question, reason = match(QUESTIONS, q.question), match(WHYS, q.why_it_matters)
            assert question is not None and question.key == key
            assert question.params == {"university": "Example University"}
            assert reason is not None and reason.key == why

    def test_no_verified_programme_page(self):
        cand = SimpleNamespace(name="Example University", discovery_source="kb:x")
        prog = SimpleNamespace(name="Data Science")
        runner = SimpleNamespace(knowledge=SimpleNamespace(get=lambda _seed: None))
        q = _runner_method("_no_verified_programme_page")(runner, cand, prog)
        ref = match(QUESTIONS, q.question)
        assert ref is not None and ref.key == "question.programmePage"
        assert ref.params == {"programme": "Data Science"}
        assert match(WHYS, q.why_it_matters).key == "why.programmePageUnverified"  # type: ignore[union-attr]

    @pytest.mark.parametrize(
        "programme,question_key,why_key",
        [
            (
                {
                    "related_reason": {
                        "name": "BSc Data Science (N3UD)",
                        "url": "https://x.example/ds",
                        "checked_on": "2026-10-19",
                    }
                },
                "question.programmeRelatedOnly",
                "why.programmeRelatedOnly",
            ),
            (
                {
                    "offered": False,
                    "related_reason": {
                        "name": "BSc Data Science (N3UD)",
                        "url": "https://x.example/ds",
                        "checked_on": "2026-10-19",
                    },
                },
                "question.programmeNotOffered",
                "why.programmeNotOffered",
            ),
            ({"offered": False}, "question.programmeNotOffered", "why.programmeNotOfferedNoRoute"),
        ],
    )
    def test_a_programme_the_kb_settled_is_said_and_keyed(self, programme, question_key, why_key):
        from app.knowledge import KnowledgeEntry

        entry = KnowledgeEntry(
            seed_id="x",
            university="Example University",
            country="",
            # The route's page is on an official domain, or no route is named (SR2-05).
            official_domains=("x.example",),
            review_status="expert_checked",
            verified_on="2026-10-20",
            programme={"status": "unknown", "urls": [], "evidence": [], **programme},
            facts={},
        )
        cand = SimpleNamespace(name="Example University", discovery_source="kb:x")
        prog = SimpleNamespace(name="Computer Science")
        runner = SimpleNamespace(knowledge=SimpleNamespace(get=lambda _seed: entry))
        q = _runner_method("_no_verified_programme_page")(runner, cand, prog)
        assert q.blocking is False
        ref, why = match(QUESTIONS, q.question), match(WHYS, q.why_it_matters)
        assert ref is not None and ref.key == question_key
        assert why is not None and why.key == why_key
        if "route" in ref.params:
            # A name with its own parentheses is not split at them.
            assert ref.params == {"route": "BSc Data Science (N3UD)", "url": "https://x.example/ds"}
        else:
            assert ref.params == {
                "university": "Example University",
                "date": "2026-10-19" if "related_reason" in programme else "2026-10-20",
            }

    def test_an_aggregator_demotion(self):
        claim = Claim(
            claim_type=ClaimType.IELTS_MIN_OVERALL,
            normalized_value=6.5,
            source_url="https://rankings.example.com/x",
            accessed_at=datetime.now(UTC),
            source_specificity=SourceSpecificity.AGGREGATOR,
        )
        _claims, questions = enforce_source_hierarchy([claim])
        assert questions, "an aggregator-only IELTS claim must raise a question"
        ref = match(QUESTIONS, questions[0].question)
        assert ref is not None and ref.key == "question.confirmOnOfficialPage"
        assert ref.params["field"] == "ielts min overall"
        assert match(WHYS, questions[0].why_it_matters).key == "why.aggregator"  # type: ignore[union-attr]

    def test_the_kb_stale_reasons(self):
        today = date(2026, 10, 19)
        fact = {
            "key": "deadline",
            "value": "2026-01-15",
            "academic_year": "2025/2026",
            "verified_on": "2024-01-01",
        }
        reasons = kb_stale_reasons(fact, today, "fall 2027")
        assert reasons, "the fact is stale three ways"
        keys = [match(STALE_REASONS, r) for r in reasons]
        assert all(keys), [r for r, k in zip(reasons, keys, strict=True) if k is None]
        assert {k.key for k in keys if k} >= {"stale.tooOld", "stale.deadlinePassed"}
        notes = "Verified knowledge base. Stale, not current: " + "; ".join(reasons) + "."
        parsed = stale_reasons(notes)
        assert parsed is not None and [p.key for p in parsed if p] == [k.key for k in keys if k]

    def test_a_claim_with_no_stale_sentence_has_no_stale_messages(self):
        assert stale_reasons("timezone: Europe/Amsterdam") is None

    def test_the_funding_gap_refusals(self):
        no_cost = compute_funding_gap(CostBreakdown(), [], "USD")
        assert match(FUNDING, no_cost.reason).key == "gap.noCost"  # type: ignore[union-attr]
        assert [match(FUNDING, w).key for w in no_cost.warnings] == ["gap.costUnverified"]  # type: ignore[union-attr]

        mixed = CostBreakdown(
            items={
                CostCategory.TUITION: Money(amount=1000, currency="USD", academic_year="2026/27"),
                CostCategory.HOUSING: Money(amount=500, currency="USD", academic_year="2027/28"),
            }
        )
        gap = compute_funding_gap(mixed, [], "USD")
        ref = match(FUNDING, gap.reason)
        assert ref is not None and ref.key == "gap.mixedYears"
        assert ref.params == {"years": "2026/27, 2027/28"}

    def test_the_funding_outcome_with_no_scholarships(self):
        _fit, _class, reason = funding_fit_for([])
        assert match(FUNDING, reason).key == "funding.noInformation"  # type: ignore[union-attr]

    def test_a_stale_award_keys_each_reason_inside_the_sentence(self):
        why = (
            "What the verified knowledge base holds about this award is stale (deadline "
            "2026-01-15 has passed; no verification date), so it is not shown as current and "
            "does not count as funding until the scholarships office confirms it."
        )
        ref = match(WHYS, why)
        assert ref is not None and ref.key == "why.awardStale"
        assert [p.key for p in ref.parts["reasons"] if p] == [
            "stale.deadlinePassed",
            "stale.noDate",
        ]

    @pytest.mark.parametrize(
        ("reason", "key", "params"),
        [
            ("no verification date", "stale.noDate", {}),
            (
                "verified on 2024-01-01, more than 365 days ago",
                "stale.tooOld",
                {"date": "2024-01-01", "days": "365"},
            ),
            (
                "academic year 2026/2027 is before the fall 2027 intake's 2027/28",
                "stale.yearBeforeIntake",
                {"year": "2026/2027", "intake": "fall 2027", "wanted": "2027/28"},
            ),
            (
                "academic year 2025-26 (2025-26 cohort) is before the fall 2027 intake's 2027/28",
                "stale.yearBeforeIntake",
                {"year": "2025-26 (2025-26 cohort)", "intake": "fall 2027", "wanted": "2027/28"},
            ),
            ("academic year 2024/2025 is past", "stale.yearPast", {"year": "2024/2025"}),
            ("deadline 2026-01-15 has passed", "stale.deadlinePassed", {"date": "2026-01-15"}),
            ("published for academic year 2026", "stale.publishedForYear", {"year": "2026"}),
            ("the academic year is not stated", "stale.yearNotStated", {}),
            ("published for the 2026 cycle", "stale.publishedForCycle", {"year": "2026"}),
            (
                'document list published for "Last Update: 02/12/2021", not the fall 2027 intake',
                "stale.documentsForCycle",
                {"cycle": "Last Update: 02/12/2021", "intake": "fall 2027"},
            ),
            (
                "document list published for another cycle, not the fall 2027 intake",
                "stale.documentsAnotherCycle",
                {"intake": "fall 2027"},
            ),
        ],
    )
    def test_each_stale_reason_shape_parses_to_its_key(self, reason, key, params):
        ref = stale_reason_message(reason)
        assert ref is not None and ref.key == key and ref.params == params

    def test_an_unknown_stale_reason_keeps_its_english(self):
        assert stale_reason_message("withdrawn by the university") is None
        parsed = stale_reasons("Stale, not current: the academic year is not stated; odd one.")
        assert parsed is not None and parsed[1] is None
        assert parsed[0] is not None and parsed[0].key == "stale.yearNotStated"

    def test_the_build_written_reasons_are_recognised(self):
        from evaluation.research.expert.kb_build import other_cycle_reason

        for item, intake, key in (
            ({"cycle_stated": "2027 Spring", "cycle_is_intake": False}, "fall 2027",
             "stale.documentsForCycle"),
            ({"cycle_is_intake": False}, "fall 2027", "stale.documentsAnotherCycle"),
        ):  # fmt: skip
            _cycle, reason = other_cycle_reason(item, {}, intake)
            ref = stale_reason_message(reason or "")
            assert ref is not None and ref.key == key and ref.params["intake"] == intake

    def test_every_stale_reason_in_the_committed_kb_has_a_key(self):
        import json

        from app.knowledge import KB_FILE

        found: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                found.extend(str(r) for r in node.get("stale_reasons") or [])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(json.loads(KB_FILE.read_text(encoding="utf-8")))
        assert found, "the committed KB holds stale reasons"
        assert [r for r in found if stale_reason_message(r) is None] == []

    def test_a_stale_documents_list_keys_each_document_and_its_reasons(self):
        why = (
            "The verified knowledge base holds these documents, but not as current: Passport "
            "(verified on 2024-01-01, more than 365 days ago, document list published for "
            '"Guide, 2026", not the fall 2027 intake); Transcript (certified) (the academic '
            "year is not stated). They are listed so you can prepare, not as confirmed."
        )
        ref = match(WHYS, why)
        assert ref is not None and ref.key == "why.documentsNotCurrent"
        passport, transcript = ref.parts["documents"]
        assert passport is not None and passport.params["document"] == "Passport"
        assert [r.key for r in passport.parts["reasons"] if r] == [
            "stale.tooOld",
            "stale.documentsForCycle",
        ]
        assert passport.parts["reasons"][1].params["cycle"] == "Guide, 2026"  # type: ignore[union-attr]
        assert transcript is not None and transcript.params["document"] == "Transcript (certified)"
        assert [r.key for r in transcript.parts["reasons"] if r] == ["stale.yearNotStated"]

    def test_a_document_with_an_unknown_reason_keeps_its_english(self):
        why = (
            "The verified knowledge base holds these documents, but not as current: Passport "
            "(withdrawn). They are listed so you can prepare, not as confirmed."
        )
        ref = match(WHYS, why)
        assert ref is not None and ref.parts["documents"] == [None]

    def test_an_unrecognised_sentence_gets_no_key_and_keeps_its_english(self):
        assert match(QUESTIONS, "Is this a sentence nobody templated?") is None

    def test_every_template_is_recognised_by_itself_alone(self):
        # A sample filled from each template must match that template and no
        # earlier one, or the first match would hand back the wrong key.
        from app.domain import message_keys

        groups = (
            QUESTIONS,
            WHYS,
            STALE_REASONS,
            DOCUMENT_ITEMS,
            FUNDING,
            COVERAGE,
            REQUIREMENT_LABELS,
            REQUIREMENT_EXPLANATIONS,
            DEGREE_REASONS,
            message_keys.MISSING_COVERAGE,
            CLASSIFICATION_SENTENCES,
            AXIS_REASONS,
            KNOCKOUTS,
            BUCKET_REASONS,
            CONFLICT_LABELS,
            CONFLICT_SUBJECTS,
            CONFLICT_RULES,
        )
        for group in groups:
            for template in group:
                sample = re.sub(r"\{(\w+)\}", lambda m: f"<{m.group(1)}>", template.text)
                ref = match(group, sample)
                assert ref is not None and ref.key == template.key, (template.key, ref)


def _kb_row(**overrides) -> ProgramResult:
    base = {
        "id": "r", "run_id": "run", "university": "Example University", "university_id": "u",
        "country": "NL", "city": "X", "program": "Computer Science", "degree": "bachelor",
        "intake": "fall 2027",
    }  # fmt: skip
    return ProgramResult.model_validate({**base, **overrides})


def _tuition(status: ClaimStatus, notes: str) -> ClaimOut:
    return ClaimOut(
        id="c0", claim_type=ClaimType.TUITION, normalized_value={"amount": 2530, "currency": "EUR"},
        source_url="https://example.edu/fees", accessed_at=datetime.now(UTC), status=status,
        academic_year="2026/2027", notes=notes,
    )  # fmt: skip


class TestTheKbModeWordingIsRecognised:
    """B2-B4: the kb-mode sentences that landed beside B6 are keyed too."""

    def test_every_verified_does_not_apply_statement_in_the_kb(self):
        from app.knowledge import load_knowledge_base
        from app.knowledge.claims import requirement_statement_questions

        kb = load_knowledge_base()
        questions = [
            q
            for entry in kb.entries.values()
            for q in requirement_statement_questions(
                entry, university=entry.university, programme="Computer Science"
            )
        ]
        assert questions, "the KB holds verified 'does not apply' requirements"
        unkeyed = [
            q.question
            for q in questions
            if match(QUESTIONS, q.question) is None or match(WHYS, q.why_it_matters) is None
        ]
        assert unkeyed == [], unkeyed

    def test_no_award_question(self):
        from app.knowledge.funding import no_award_question

        row = _kb_row(claims=[_tuition(ClaimStatus.VERIFIED_CURRENT, "").model_dump(mode="json")])
        q = no_award_question(row, [])
        assert q is not None
        assert match(QUESTIONS, q.question).key == "question.kbScholarships"  # type: ignore[union-attr]
        assert match(WHYS, q.why_it_matters).key == "why.kbNoAward"  # type: ignore[union-attr]

    def test_both_language_questions_are_keyed(self):
        from app.knowledge import KnowledgeEntry
        from app.knowledge.claims import requirement_statement_questions

        rows = [
            {"question": "english", "key": "ielts.overall", "source_url": "https://e.edu/a",
             "reason": "No English language test result is required for this route.",
             "quote": "The German C1 language certificate must be submitted."},
            {"question": "english", "key": "ielts.overall", "source_url": "https://e.edu/b",
             "reason": "No English language test result is required for this route.",
             "quote": "No, we do not require any English proficiency exams."},
        ]  # fmt: skip
        entry = KnowledgeEntry(
            seed_id="x", university="Example University", country="X", official_domains=(),
            review_status="expert_checked", verified_on=None, programme={}, facts={},
            not_applicable=rows,
        )  # fmt: skip
        keys = [
            match(QUESTIONS, q.question).key  # type: ignore[union-attr]
            for q in requirement_statement_questions(
                entry, university="Example University", programme="CS"
            )
        ]
        assert keys == ["question.languageInstead", "question.languageNoneRecorded"]

    def test_no_fee_in_the_kb(self):
        from app.knowledge.funding import explain_unused_tuition

        row = _kb_row()
        row.funding_gap = compute_funding_gap(row.costs, [], "USD")
        explain_unused_tuition(row)
        gap = row.funding_gap
        assert match(FUNDING, gap.reason).key == "gap.kbNoFee"  # type: ignore[union-attr]
        assert [match(FUNDING, w).key for w in gap.warnings] == [  # type: ignore[union-attr]
            "gap.confirmIntakeFee"
        ]

    def test_an_unused_fee_for_another_year(self):
        from app.knowledge.funding import explain_unused_tuition

        stale = _tuition(
            ClaimStatus.POSSIBLY_STALE,
            "Stale, not current: academic year 2026/2027 is before the fall 2027 intake's 2027/28.",
        )
        row = _kb_row(claims=[stale.model_dump(mode="json")])
        row.funding_gap = compute_funding_gap(row.costs, [], "USD")
        explain_unused_tuition(row)
        gap = row.funding_gap
        reason = match(FUNDING, gap.reason)
        assert reason is not None and reason.key == "gap.feeOtherYear", gap.reason
        assert reason.params["intake"] == "fall 2027"
        assert [match(FUNDING, w).key for w in gap.warnings] == ["gap.confirmIntakeFee"]  # type: ignore[union-attr]

    def test_a_fee_not_published_per_year(self):
        from app.knowledge.funding import explain_unused_tuition

        per_term = _tuition(
            ClaimStatus.VERIFIED_CURRENT, "Amount per semester, as published; not a yearly figure."
        )
        row = _kb_row(claims=[per_term.model_dump(mode="json")])
        row.funding_gap = compute_funding_gap(row.costs, [], "USD")
        explain_unused_tuition(row)
        assert match(FUNDING, row.funding_gap.reason).key == "gap.feeNotYearly"  # type: ignore[union-attr]

    def test_a_per_credit_rate_says_no_yearly_figure_was_printed(self):
        from app.knowledge.funding import explain_unused_tuition

        per_credit = _tuition(
            ClaimStatus.VERIFIED_CURRENT, "Amount per credit, as published; not a yearly figure."
        )
        row = _kb_row(claims=[per_credit.model_dump(mode="json")])
        row.funding_gap = compute_funding_gap(row.costs, [], "USD")
        explain_unused_tuition(row)
        reason = match(FUNDING, row.funding_gap.reason)
        assert reason is not None and reason.key == "gap.feeNotYearly"
        assert "2,530 EUR per credit" in reason.params["fees"]
        assert "(published per credit (no yearly figure printed))" in reason.params["fees"]

    def test_a_published_range_in_the_cost_table_is_said_and_keyed(self):
        from app.knowledge.funding import explain_unused_tuition

        row = _kb_row(
            costs={
                "items": {
                    "tuition": {
                        "amount": 34670, "currency": "GBP", "academic_year": "2027/28",
                        "range_low": 27650, "range_high": 34670,
                    }
                },
                "is_range": True,
            }
        )  # fmt: skip
        row.funding_gap = compute_funding_gap(row.costs, [], "GBP")
        explain_unused_tuition(row)
        refs = [match(FUNDING, w) for w in row.funding_gap.warnings]
        (ref,) = [r for r in refs if r is not None and r.key == "gap.kbTuitionRange"]
        assert ref.params["range"] == "27,650–34,670 GBP"

    def test_why_a_kb_row_needs_clarification(self):
        from app.domain.enums import EligibilityStatus
        from app.pipeline.runner import _kb_clarification_question
        from app.schemas.result import RequirementCheck

        unclear = RequirementCheck(
            requirement="IELTS overall", status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        )
        for checks, why in (
            ([unclear], "why.kbRequirementsUnsettled"),
            ([], "why.kbNoComparableRequirement"),
        ):
            q = _kb_clarification_question(_kb_row(requirement_checks=checks))
            assert match(QUESTIONS, q.question).key == "question.kbEntryRequirements"  # type: ignore[union-attr]
            assert match(WHYS, q.why_it_matters).key == why  # type: ignore[union-attr]


class TestNothingIsStored:
    def test_an_unannotated_payload_has_no_new_keys(self):
        q = UnresolvedQuestion(topic="t", question="q", why_it_matters="w")
        assert set(q.model_dump(mode="json")) == {
            "topic",
            "question",
            "why_it_matters",
            "university",
            "program",
            "suggested_contact",
            "blocking",
        }
        assert "reason_message" not in FundingGap(computable=False).model_dump(mode="json")
        claim = ClaimOut(
            id="c",
            claim_type=ClaimType.TUITION,
            normalized_value=1,
            source_url="https://a.b/c",
            accessed_at=datetime.now(UTC),
            status=ClaimStatus.VERIFIED_CURRENT,
        )
        assert "stale_messages" not in claim.model_dump(mode="json")

    def test_an_annotated_result_round_trips(self):
        q = UnresolvedQuestion(
            topic="research",
            question="Which groups at Example University work on robotics?",
            why_it_matters=(
                "The profile lists robotics as a research interest. The pages read do not "
                "mention it, which is not the same as it being absent."
            ),
        )
        result = ProgramResult.model_validate(
            {
                "id": "r",
                "run_id": "run",
                "university": "Example University",
                "university_id": "u",
                "country": "NL",
                "city": "X",
                "program": "CS",
                "degree": "bachelor",
                "intake": "fall 2027",
                "unresolved": [q.model_dump(mode="json")],
            }
        )
        dumped = annotate_result(result).model_dump(mode="json")
        served = dumped["unresolved"][0]
        assert served["question_message"] == {
            "key": "question.researchGroups",
            "params": {"university": "Example University", "interest": "robotics"},
            "parts": {},
        }
        assert served["why_message"]["key"] == "why.researchInterest"
        assert served["question"] == q.question, "the English is served unchanged"
        assert ProgramResult.model_validate(dumped).unresolved[0].question_message is not None


class TestTheApiServesTheKeys:
    def test_demo_results_carry_keys_and_the_stored_rows_do_not(self, client, finished_run):  # noqa: F811
        _profile, run = finished_run
        results = client.get(f"/api/runs/{run['id']}/results").json()
        questions = [q for r in results for q in r["unresolved"]]
        assert questions, "the demo raises open questions"
        unkeyed = [q["question"] for q in questions if not q.get("question_message")]
        assert unkeyed == [], unkeyed
        unkeyed_why = [q["why_it_matters"] for q in questions if not q.get("why_message")]
        assert unkeyed_why == [], unkeyed_why
        gaps = [r["funding_gap"] for r in results if r.get("funding_gap")]
        assert gaps and all(g["reason_message"] for g in gaps)
        assert all(len(g["warning_messages"]) == len(g["warnings"]) for g in gaps)
        unkeyed_warnings = [
            w
            for g in gaps
            for w, m in zip(g["warnings"], g["warning_messages"], strict=True)
            if not m
        ]
        assert unkeyed_warnings == [], unkeyed_warnings
        stale = [c for r in results for c in r["claims"] if "Stale, not current: " in c["notes"]]
        assert all(c.get("stale_messages") for c in stale)

        import app.db as db_module
        from app.models import ProgramResultRow

        with db_module.SessionLocal() as session:
            rows = (
                session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run["id"]).all()
            )
            stored = "".join(str(row.payload) for row in rows)
        assert "question_message" not in stored and "reason_message" not in stored

        listed = client.get(f"/api/runs/{run['id']}/questions").json()
        assert any(item.get("question_message") for item in listed)

        one = client.get(f"/api/runs/{run['id']}/results/{results[0]['id']}").json()
        assert one["funding_gap"]["reason_message"]


class TestTheFrontendCatalogueKeepsUp:
    @pytest.fixture(scope="class")
    def catalogue(self) -> str:
        return FRONTEND_CATALOGUE.read_text(encoding="utf-8")

    def test_every_key_is_in_english_russian_and_kazakh(self, catalogue):
        for template in CATALOGUE:
            found = re.findall(rf"'msg\.{re.escape(template.key)}':", catalogue)
            assert len(found) == 3, f"msg.{template.key} appears {len(found)} times, want en/ru/kk"

    def test_the_english_is_the_backend_template_word_for_word(self, catalogue):
        for template in CATALOGUE:
            entry = re.search(
                rf"'msg\.{re.escape(template.key)}':\s*\n?\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+),",
                catalogue,
            )
            assert entry is not None, template.key
            pieces = re.findall(r"'((?:[^'\\]|\\.)*)'", entry.group(1))
            english = "".join(pieces).replace("\\'", "'")
            assert english == template.text, template.key

    def test_every_translation_names_the_same_parameters(self, catalogue):
        entries = re.findall(
            r"'msg\.([\w.]+)':\s*\n?\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+),", catalogue
        )
        by_key: dict[str, list[set[str]]] = {}
        for key, body in entries:
            by_key.setdefault(key, []).append(set(re.findall(r"\{(\w+)\}", body)))
        for template in CATALOGUE:
            wanted = set(re.findall(r"\{(\w+)\}", template.text))
            assert by_key[template.key] == [wanted] * 3, template.key


# --- I18N-2: requirement checks, award classifications, the ranking, conflicts


def _req_claim(claim_type: ClaimType, value: object) -> Claim:
    return Claim(
        claim_type=claim_type,
        normalized_value=value,
        source_url="https://u.example/admissions",
        accessed_at=datetime.now(UTC),
        status=ClaimStatus.VERIFIED_CURRENT,
        source_specificity=SourceSpecificity.PROGRAM,
    )


def _keyed(templates, text: str, key: str) -> MessageRef:
    ref = match(templates, text)
    assert ref is not None and ref.key == key, (text, ref)
    assert _complete(ref), (text, ref)
    return ref


class TestTheRequirementChecksAreRecognised:
    def test_every_numeric_minimum_shape(self):
        from app.domain.eligibility import _check_numeric_minimum

        gpa = _req_claim(ClaimType.MIN_GPA, 3.5)
        cases = [
            (_check_numeric_minimum("Minimum GPA", None, 3.0), "explain.noMinimum"),
            (
                _check_numeric_minimum("SAT total", _req_claim(ClaimType.MIN_GPA, "high"), 1400),
                "explain.notNumber",
            ),
            (_check_numeric_minimum("IELTS overall", gpa, None), "explain.noApplicantValue"),
            (_check_numeric_minimum("Minimum GPA", gpa, 3.0), "explain.minimumNotMet"),
            (_check_numeric_minimum("Minimum GPA", gpa, 3.8), "explain.minimumMet"),
            (_check_numeric_minimum("IELTS writing", gpa, 7.0), "explain.minimumMet"),
        ]
        for check, key in cases:
            _keyed(REQUIREMENT_EXPLANATIONS, check.explanation, key)
            assert _complete(match(REQUIREMENT_LABELS, check.requirement)), check.requirement
        ref = _keyed(REQUIREMENT_EXPLANATIONS, cases[0][0].explanation, "explain.noMinimum")
        assert ref.parts["label"][0].key == "req.minGpa"  # type: ignore[union-attr]
        band = match(REQUIREMENT_LABELS, "IELTS writing")
        assert band is not None and band.key == "req.ieltsBand"
        assert band.params == {"band": "writing"}

    def test_a_whole_programme_evaluation_is_keyed(self, profile):
        from app.domain.eligibility import evaluate_program

        claims = [
            _req_claim(ClaimType.INTAKE_OPEN, False),
            _req_claim(ClaimType.ADMISSION_DEADLINE, "2020-01-15"),
            _req_claim(ClaimType.MIN_GPA, 3.0),
            _req_claim(ClaimType.IELTS_MIN_OVERALL, 6.5),
            _req_claim(ClaimType.IELTS_MIN_SUBSCORE, 6.0),
            _req_claim(ClaimType.IELTS_ACCEPTED_TYPES, ["academic"]),
            _req_claim(ClaimType.ENGLISH_TEST_WAIVER, "schooling in English"),
            _req_claim(ClaimType.SAT_POLICY, "test-optional"),
            _req_claim(ClaimType.PORTFOLIO_REQUIRED, True),
            _req_claim(ClaimType.INTERVIEW_REQUIRED, True),
            _req_claim(ClaimType.ENTRANCE_EXAM_REQUIRED, True),
            _req_claim(ClaimType.CREDENTIAL_EVALUATION_REQUIRED, True),
            _req_claim(ClaimType.REQUIRED_SUBJECTS, ["mathematics", "latin"]),
        ]
        outcome = evaluate_program(profile, claims, today=date(2026, 10, 20))
        assert len(outcome.checks) >= 10
        for check in outcome.checks:
            assert _complete(match(REQUIREMENT_LABELS, check.requirement)), check.requirement
            assert _complete(match(REQUIREMENT_EXPLANATIONS, check.explanation)), check.explanation

    def test_the_other_deadline_and_policy_shapes(self, profile):
        from app.domain.eligibility import _population_deadline_check, evaluate_program

        rows = [
            ("home", date(2026, 1, 1), _req_claim(ClaimType.ADMISSION_DEADLINE, "2026-01-01")),
            ("overseas", date(2027, 1, 1), _req_claim(ClaimType.ADMISSION_DEADLINE, "2027-01-01")),
        ]
        for today, key in (
            (date(2025, 6, 1), "explain.deadlineByPopulation"),
            (date(2026, 6, 1), "explain.deadlineByPopulationPassed"),
            (date(2027, 6, 1), "explain.allDeadlinesPassed"),
        ):
            check = _population_deadline_check(rows, today, None)
            _keyed(REQUIREMENT_EXPLANATIONS, check.explanation, key)
        for claims, key in (
            ([_req_claim(ClaimType.ADMISSION_DEADLINE, "2030-01-15")], "explain.deadlineOpen"),
            ([_req_claim(ClaimType.ADMISSION_DEADLINE, "03/04/2027")], "explain.deadlineUnparsed"),
            ([_req_claim(ClaimType.SAT_POLICY, "required")], "explain.satPolicyNoMinimum"),
            ([_req_claim(ClaimType.ADMISSION_DEADLINE, "2030-01-15")], "explain.noAssessable"),
        ):
            outcome = evaluate_program(profile, claims, today=date(2026, 10, 20))
            keys = {
                ref.key
                for c in outcome.checks
                if (ref := match(REQUIREMENT_EXPLANATIONS, c.explanation)) is not None
            }
            assert key in keys, (key, [c.explanation for c in outcome.checks])

    def test_a_gpa_on_another_scale_and_all_subjects_present(self):
        _keyed(
            REQUIREMENT_EXPLANATIONS,
            "All published subject prerequisites are present in the profile.",
            "explain.subjectsPresent",
        )
        _keyed(
            REQUIREMENT_EXPLANATIONS,
            "The applicant's GPA is on the 5-point scale and the programme publishes a "
            "different scale. No conversion is applied without a documented method, so this "
            "cannot be decided here.",
            "explain.gpaScale",
        )

    def test_the_award_eligibility_checks(self, profile):
        from app.domain.citizenship import match_citizenship
        from app.pipeline.runner import _scholarship_eligibility

        seen = set()
        for restrictions in (
            [""],
            ["Kazakh nationals"],
            ["European Union"],
            ["Central Asian nationals"],
            ["Nigerian citizens"],
        ):
            _verdict, text = match_citizenship(restrictions, ["kazakhstan"])
            ref = match(REQUIREMENT_EXPLANATIONS, text)
            assert _complete(ref), text
            seen.add(ref.key)  # type: ignore[union-attr]
        assert {"explain.citizenshipUnreadable", "explain.citizenshipExcluded"} <= seen
        award = SimpleNamespace(
            citizenship_restrictions=[],
            international_eligible="yes",
            faculty_restrictions=["the Faculty of Science"],
            program_restrictions=["BSc Data Science"],
            min_test_scores={"ielts": 6.5, "sat": 1400.0},
        )
        checks = _scholarship_eligibility(award, profile)
        closed = SimpleNamespace(**{**vars(award), "international_eligible": "no"})
        checks += _scholarship_eligibility(closed, profile)
        for check in checks:
            assert _complete(match(REQUIREMENT_LABELS, check.requirement)), check.requirement
            assert _complete(match(REQUIREMENT_EXPLANATIONS, check.explanation)), check.explanation
        _keyed(
            REQUIREMENT_EXPLANATIONS,
            "The published scholarship deadline 2026-01-01 has passed.",
            "explain.scholarshipDeadlinePassed",
        )
        _keyed(
            REQUIREMENT_EXPLANATIONS,
            "Kazakhstan is a member of the EAEU, which the award names as its restriction.",
            "explain.citizenshipMember",
        )
        _keyed(
            REQUIREMENT_EXPLANATIONS,
            "The award requires SAT 1400.0; no score is in the profile.",
            "explain.scholarshipTestMissing",
        )


def _award(**fields) -> Scholarship:
    return Scholarship.model_validate({"id": "s", "name": "Example Award", **fields})


class TestTheAwardClassificationIsRecognised:
    @pytest.mark.parametrize(
        "fields,keys",
        [
            ({"applicant_eligible": "no"}, ["class.excluded"]),
            (
                {"applicant_eligible": "no", "citizenship_restrictions": ["Nigeria"]},
                ["class.citizenship"],
            ),
            (
                {
                    "applicant_eligible": "no",
                    "degree_applicability": "no",
                    "degree_applicability_reason": "the page explicitly excludes bachelor "
                    "applicants",
                },
                ["class.degreeLevel"],
            ),
            ({"degree_applicability": "no"}, ["class.degreeLevel"]),
            ({"international_eligible": "no"}, ["class.notInternational"]),
            ({}, ["class.noCoverage"]),
        ],
    )
    def test_each_exclusion(self, fields, keys):
        from app.domain.funding import classify

        verdict = classify(_award(**fields))
        refs = match_sentences(CLASSIFICATION_SENTENCES, verdict.reason)
        assert refs is not None, verdict.reason
        assert [r.key for r in refs] == keys

    def test_every_degree_reason_the_adapter_writes(self):
        from app.adapters.applicability import assess_degree_applicability

        for text in (
            "",
            "Master's students are not eligible for this award.",
            "This award is open to bachelor applicants.",
            "This award is for master students in engineering.",
            "Scholarships for doctoral and master programmes.",
            "A generous award.",
        ):
            reason = assess_degree_applicability(text, "bachelor").reason
            assert _complete(match(DEGREE_REASONS, reason)), reason

    def test_the_coverage_verdicts(self):
        from app.domain.funding import classify

        def cov(**states):
            return [{"category": c, "covered": v} for c, v in states.items()]

        full = cov(tuition="yes", mandatory_fees="yes", housing="yes", meals="yes")
        tuition = cov(tuition="yes", housing="no", meals="unknown")
        partial = cov(tuition="partial")
        for award, key in (
            (_award(coverage=full), "class.fullRide"),
            (_award(coverage=tuition), "class.fullTuition"),
            (_award(coverage=partial), "class.shareUnknown"),
            (
                _award(coverage=partial, amount={"amount": 30000, "currency": "EUR"}),
                "class.largeGrant",
            ),
            (
                _award(coverage=partial, amount={"amount": 3000, "currency": "EUR"}),
                "class.partial",
            ),
            (_award(coverage=partial, scholarship_type="need_based"), "class.needBased"),
        ):
            reason = classify(award, total_cost_amount=40000.0).reason
            refs = match_sentences(CLASSIFICATION_SENTENCES, reason)
            assert refs is not None and refs[0].key == key, (key, reason)
        refs = match_sentences(CLASSIFICATION_SENTENCES, classify(_award(coverage=tuition)).reason)
        assert refs is not None
        missing = refs[0].parts["missing"]
        assert all(missing)
        assert {m.key for m in missing if m} == {"missing.notCovered", "missing.unknown"}

    def test_the_runner_additions_are_said_sentence_by_sentence(self):
        from app.domain.funding import award_meets_shape

        reason = (
            "No official per-category coverage information was found. Page uses promotional "
            "wording (full ride) but publishes no breakdown. The page uses promotional wording "
            "such as 'full ride'; the classification here follows the published coverage table "
            "instead."
        )
        refs = match_sentences(CLASSIFICATION_SENTENCES, reason)
        assert [r.key for r in refs or []] == [
            "class.noCoverage",
            "class.promotionalNoBreakdown",
            "class.promotional",
        ]
        needs = SimpleNamespace(
            requires_full_ride=True,
            accepts_full_tuition=False,
            accepts_partial=False,
            willing_to_submit_need_documents=False,
        )
        for classification in ("FULL_TUITION", "PARTIAL", "NEED_BASED_POSSIBLE"):
            _ok, shape = award_meets_shape(_award(classification=classification), needs)  # type: ignore[arg-type]
            text = (
                f"Covers roughly 40% of published cost of attendance. {shape} The profile "
                "requires housing, meals to be covered; this award states it is not."
            )
            refs = match_sentences(CLASSIFICATION_SENTENCES, text)
            assert refs is not None and len(refs) == 3, text
            assert refs[1].key == "class.onlyFullRide"
        relaxed = SimpleNamespace(**{**vars(needs), "requires_full_ride": False})
        for classification, key in (
            ("FULL_TUITION", "class.noTuitionOnly"),
            ("PARTIAL", "class.noPartial"),
            ("NEED_BASED_POSSIBLE", "class.needDocuments"),
        ):
            _ok, shape = award_meets_shape(_award(classification=classification), relaxed)  # type: ignore[arg-type]
            _keyed(CLASSIFICATION_SENTENCES, shape, key)

    def test_an_unknown_sentence_leaves_the_whole_reason_english(self):
        reason = "Covers roughly 40% of published cost of attendance. A sentence nobody wrote."
        assert match_sentences(CLASSIFICATION_SENTENCES, reason) is None
        unknown = "Not applicable to this applicant's degree level: some new reason"
        assert match_sentences(CLASSIFICATION_SENTENCES, unknown) is None


class TestTheRankingIsRecognised:
    def test_every_axis_reason(self):
        from app.domain import ranking_v2 as r

        careers = [
            r.u_career(
                has_coop=coop,
                has_internships=intern,
                has_page=page,
                values_internships=False,
                values_coop=values,
            )[1]
            for coop, intern, page, values in (
                (True, None, False, True),
                (None, True, False, True),
                (None, None, True, True),
                (None, None, False, True),
                (None, None, False, False),
            )
        ]
        reasons = [
            r.u_academic(EligibilityStatus.MET, None)[1],
            r.u_academic(EligibilityStatus.MET, 0.12)[1],
            r.u_academic(EligibilityStatus.PENDING, None)[1],
            r.u_academic(EligibilityStatus.GAP, None)[1],
            r.u_academic(EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION, None)[1],
            *(r.u_funding(fit)[1] for fit in FundingFit),
            r.u_affordability(None, 1000)[1],
            r.u_affordability(1000, None)[1],
            r.u_affordability(0, 0)[1],
            r.u_affordability(5000, 0)[1],
            r.u_affordability(5000, 10000)[1],
            r.u_affordability(12000, 10000)[1],
            r.u_affordability(30000, 10000)[1],
            r.u_country("Netherlands", [], [])[1],
            r.u_country("Netherlands", ["Netherlands"], [])[1],
            r.u_country("Netherlands", ["Canada"], [])[1],
            r.u_standing(None, "top_100")[1],
            r.u_standing(40, "top_100")[1],
            r.u_standing(3000, "top_100")[1],
            r.u_standing(250, "top_100")[1],
            r.u_ladder("climate", "warm", "any")[1],
            r.u_ladder("university_size", None, "large")[1],
            r.u_ladder("city", "large", "large")[1],
            r.u_ladder("city", "large", "medium")[1],
            r.u_ladder("city", "small", "metropolis")[1],
            r.u_ladder("campus", "urban", "campus")[1],
            *careers,
            r.u_post_study_work(None, False)[1],
            r.u_post_study_work(None, True)[1],
            r.u_post_study_work(18, True)[1],
        ]
        keys = set()
        for reason in reasons:
            ref = match(AXIS_REASONS, reason)
            assert _complete(ref), reason
            keys.add(ref.key)  # type: ignore[union-attr]
        # Every template but "Ranked {rank}." (unreachable past the anchors) is written.
        assert {t.key for t in AXIS_REASONS} - keys == {"rank.ranked"}

    def test_every_bucket_and_knockout(self):
        from app.domain import ranking_v2 as r
        from app.domain.enums import AdmissionsFit

        reasons = [
            r.bucket_of(AdmissionsFit.INSUFFICIENT_DATA, FundingFit.UNKNOWN, None, "important")[1],
            r.bucket_of(AdmissionsFit.STRONGER_FIT, FundingFit.UNKNOWN, 3.0, "important")[1],
            r.bucket_of(
                AdmissionsFit.STRONGER_FIT, FundingFit.CONFIRMED_OPPORTUNITY, 0.5, "important"
            )[1],
            r.bucket_of(
                AdmissionsFit.PLAUSIBLE_FIT, FundingFit.COMPETITIVE_OPPORTUNITY, 1.2, "important"
            )[1],
            r.bucket_of(AdmissionsFit.AMBITIOUS, FundingFit.UNKNOWN, None, "important")[1],
        ]
        assert [match(BUCKET_REASONS, x).key for x in reasons] == [  # type: ignore[union-attr]
            t.key for t in BUCKET_REASONS
        ]
        with pytest.raises(r.KnockOut) as excluded:
            r.u_country("Canada", [], ["Canada"])
        _keyed(KNOCKOUTS, str(excluded.value), "rank.excludedCountry")
        knockout = _keyed(
            KNOCKOUTS,
            "Minimum GPA: Published minimum 3.5; applicant 3. The published minimum is not met.",
            "rank.knockout",
        )
        assert knockout.parts["requirement"][0].key == "req.minGpa"  # type: ignore[union-attr]
        assert knockout.parts["explanation"][0].key == "explain.minimumNotMet"  # type: ignore[union-attr]
        _keyed(KNOCKOUTS, "Portfolio: a published requirement is not met", "rank.knockoutUnmet")

    def test_a_ranked_row_is_annotated_on_the_way_out_only(self, profile):
        from app.domain.ranking_v2 import rank_result

        row = _kb_row(
            requirement_checks=[
                {
                    "requirement": "Minimum GPA",
                    "status": "GAP",
                    "is_hard_filter": True,
                    "explanation": "Published minimum 3.5; applicant 3. The published minimum "
                    "is not met.",
                }
            ]
        )
        row.ranking = rank_result(row, profile)
        stored = row.model_dump(mode="json")
        assert "knocked_out_messages" not in stored["ranking"]
        assert "requirement_message" not in stored["requirement_checks"][0]
        served = annotate_result(row).model_dump(mode="json")
        ranking = served["ranking"]
        assert [m["key"] for m in ranking["knocked_out_messages"]] == ["rank.knockout"]
        assert ranking["bucket_reason_message"]["key"] == "rank.knockout"
        assert ranking["disclaimer_message"]["key"] == "rank.disclaimer"
        check = served["requirement_checks"][0]
        assert check["requirement_message"]["key"] == "req.minGpa"
        assert check["explanation_message"]["params"] == {"published": "3.5", "applicant": "3"}


class TestTheConflictsAreRecognised:
    def test_every_resolution_rule_and_subject(self):
        from app.domain.conflicts import _LABELS, _why_not_a_contradiction
        from app.domain.enums import ConflictKind

        claim = _req_claim(ClaimType.MIN_GPA, 3.0)
        for kind in ConflictKind:
            if kind is not ConflictKind.TRUE_CONFLICT:
                rule = _why_not_a_contradiction(kind, claim)
                assert _complete(match(CONFLICT_RULES, rule)), kind
        _keyed(
            CONFLICT_RULES,
            "Preferring the more specific source (program); the disagreement is shown rather "
            "than resolved.",
            "conflict.preferSpecific",
        )
        labels = [match(CONFLICT_LABELS, label) for label in _LABELS.values()]
        assert {ref.key for ref in labels if ref} == {t.key for t in CONFLICT_LABELS}
        assert all(labels)
        for label in _LABELS.values():
            for subject, key in (
                (label, "conflict.subject"),
                (f"{label} — international", "conflict.subjectKeyed"),
                (f"{label} (Computer Science (Hons))", "conflict.subjectProgramme"),
                (f"{label} — international (Computer Science)", "conflict.subjectFull"),
            ):
                ref = _keyed(CONFLICT_SUBJECTS, subject, key)
                assert ref.params["what"] == label

    def test_a_real_conflict_and_the_questions_why(self):
        from app.domain.conflicts import find_conflicts

        a = _req_claim(ClaimType.IELTS_MIN_OVERALL, 6.5)
        b = a.model_copy(
            update={
                "normalized_value": 7.0,
                "source_url": "https://u.example/other",
                "source_specificity": SourceSpecificity.UNIVERSITY_ADMISSIONS,
            }
        )
        conflicts, _claims = find_conflicts([a, b], context="Computer Science")
        assert conflicts
        conflict = conflicts[0]
        assert "subject_message" not in conflict.model_dump(mode="json")
        annotate_conflict(conflict)
        assert _complete(conflict.subject_message)
        assert conflict.resolution_message is not None
        why, ref = conflict_why(conflict)
        assert why == f"Official sources disagree on {conflict.subject}: {conflict.values}"
        assert ref is not None and ref.key == "conflict.why" and _complete(ref)


class TestTheExchangeRateWarning:
    def test_the_stale_rates_sentence(self):
        import app.api.routes_meta as meta

        warning = (
            f"These conversions use exchange rates from {meta.RATE_DATE.isoformat()}, "
            f"{meta.rate_age_days()} days old. Treat converted amounts as indicative and "
            "check the current rate before relying on one."
        )
        ref = stale_rates_message(warning)
        assert ref is not None and ref.key == "currency.staleRates"
        assert stale_rates_message("") is None

    def test_capabilities_serve_the_key_only_when_stale(self, client, monkeypatch):  # noqa: F811
        import app.api.routes_meta as meta

        monkeypatch.setattr(meta, "rates_are_stale", lambda: False)
        fresh = client.get("/api/capabilities").json()["currency"]
        assert fresh["stale_warning"] == "" and "stale_warning_message" not in fresh
        monkeypatch.setattr(meta, "rates_are_stale", lambda: True)
        stale = client.get("/api/capabilities").json()["currency"]
        assert stale["stale_warning"]
        assert stale["stale_warning_message"]["key"] == "currency.staleRates"


class TestTheDemoServesEveryResultsSentenceKeyed:
    def test_checks_awards_ranking_and_conflicts(self, client, finished_run):  # noqa: F811
        _profile, run = finished_run
        results = client.get(f"/api/runs/{run['id']}/results").json()
        checks = [c for r in results for c in r["requirement_checks"]]
        checks += [c for r in results for s in r["scholarships"] for c in s["eligibility_checks"]]
        assert checks
        assert [c["requirement"] for c in checks if not c.get("requirement_message")] == []
        unkeyed = [c["explanation"] for c in checks if not c.get("explanation_message")]
        assert unkeyed == []
        awards = [s for r in results for s in r["scholarships"]]
        assert awards
        unkeyed = [
            s["classification_reason"] for s in awards if not s.get("classification_messages")
        ]
        assert unkeyed == []
        rankings = [r["ranking"] for r in results if r.get("ranking")]
        assert rankings
        unkeyed = [a["reason"] for k in rankings for a in k["axes"] if not a.get("reason_message")]
        assert unkeyed == []
        assert all(k.get("bucket_reason_message") for k in rankings if k["bucket_reason"])
        assert all(k.get("disclaimer_message") for k in rankings)
        for k in rankings:
            if k["knocked_out_by"]:
                assert all(k["knocked_out_messages"]), k["knocked_out_by"]
        conflicts = [c for r in results for c in r["conflicts"]]
        assert all(c.get("subject_message") and c.get("resolution_message") for c in conflicts)

        import app.db as db_module
        from app.models import ProgramResultRow

        with db_module.SessionLocal() as session:
            rows = (
                session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run["id"]).all()
            )
            stored = "".join(str(row.payload) for row in rows)
        for field in (
            "requirement_message",
            "explanation_message",
            "classification_messages",
            "bucket_reason_message",
            "disclaimer_message",
            "subject_message",
        ):
            assert field not in stored, field

        listed = client.get(f"/api/runs/{run['id']}/questions").json()
        for item in listed:
            if item["topic"] == "source conflict":
                assert item["why_message"]["key"] == "conflict.why"
        for c in client.get(f"/api/runs/{run['id']}/conflicts").json():
            assert c["subject_message"]
