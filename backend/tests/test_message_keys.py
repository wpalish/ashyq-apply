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
from app.domain.enums import ClaimStatus, ClaimType, CostCategory, SourceSpecificity
from app.domain.funding import funding_fit_for
from app.domain.message_keys import (
    CATALOGUE,
    DOCUMENT_ITEMS,
    FUNDING,
    QUESTIONS,
    STALE_REASONS,
    WHYS,
    annotate_result,
    match,
    stale_reason_message,
    stale_reasons,
)
from app.knowledge import stale_reasons as kb_stale_reasons
from app.schemas.claim import Claim, ClaimOut, UnresolvedQuestion
from app.schemas.money import Money
from app.schemas.result import CostBreakdown, FundingGap, ProgramResult
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
        cand = SimpleNamespace(name="Example University")
        prog = SimpleNamespace(name="Data Science")
        q = _runner_method("_no_verified_programme_page")(None, cand, prog)
        ref = match(QUESTIONS, q.question)
        assert ref is not None and ref.key == "question.programmePage"
        assert ref.params == {"programme": "Data Science"}
        assert match(WHYS, q.why_it_matters).key == "why.programmePageUnverified"  # type: ignore[union-attr]

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
        for group in (QUESTIONS, WHYS, STALE_REASONS, DOCUMENT_ITEMS, FUNDING):
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
