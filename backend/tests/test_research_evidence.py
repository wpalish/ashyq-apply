"""Failure cases for public evidence reuse and applicant-local projection."""

from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.document_ir import build_document_ir
from app.research.contracts import PolicyRule, PublicScope, QuestionGroup, ResearchQuestion
from app.research.evidence import PublicEvidenceStore, project, span_from_block, validate_rule

NOW = datetime(2026, 10, 9, tzinfo=UTC)
URL = "https://example.edu/english"


@pytest.fixture
def policy():
    doc = build_document_ir("<h1>English</h1><p>IELTS overall 6.5; each band 6.0.</p>", URL)
    block = next(b for b in doc.blocks if "IELTS" in b.text)
    span = span_from_block(doc, block.id, 0, len(block.text), NOW)
    scope = PublicScope(
        university="Example",
        cycle="2027",
        programme="CS",
        degree="bachelor",
        population="international",
        qualification="NIS",
        campus="main",
    )
    rule = PolicyRule(
        id="overall",
        question="english.overall",
        group=QuestionGroup.ENGLISH,
        value=6.5,
        scope=scope,
        evidence=(span,),
        valid_until=NOW + timedelta(days=30),
    )
    question = ResearchQuestion(
        id="english",
        group=QuestionGroup.ENGLISH,
        scope=scope,
        required=("english.overall", "english.bands", "english.waiver"),
    )
    return doc, rule, question


def answer(policy, rules=None, **kwargs):
    doc, rule, question = policy
    return project(
        question,
        rules if rules is not None else [rule],
        {URL: doc},
        {URL},
        NOW,
        proof=lambda r: r.value == 6.5,
        **kwargs,
    )


def test_overall_score_does_not_close_subscores_and_waiver(policy):
    result = answer(policy)
    assert result.state == "partial"
    assert result.missing == ("english.bands", "english.waiver")


@pytest.mark.parametrize(
    "dimension,value",
    [
        ("programme", "Business"),
        ("campus", "other"),
        ("cycle", "2026"),
        ("degree", "master"),
        ("qualification", "attestat"),
        ("population", "exchange"),
    ],
)
def test_other_scope_cannot_answer(policy, dimension, value):
    doc, rule, question = policy
    changed = rule.model_copy(update={"scope": rule.scope.model_copy(update={dimension: value})})
    assert answer((doc, changed, question)).state == "pending"


def test_missing_scope_is_not_universal(policy):
    doc, rule, question = policy
    unscoped = rule.model_copy(update={"scope": rule.scope.model_copy(update={"campus": None})})
    assert answer((doc, unscoped, question)).state == "pending"


def test_changed_source_invalidates_cached_policy(policy, tmp_path):
    doc, rule, _ = policy
    store = PublicEvidenceStore(tmp_path)
    store.save("Example", "2027", [rule])
    assert store.load("Example", "2027", {URL: doc}, {URL}, NOW) == [rule]
    changed = build_document_ir("<p>IELTS overall 7.0</p>", URL)
    assert store.load("Example", "2027", {URL: changed}, {URL}, NOW) == []
    assert store.load("Example", "2028", {URL: doc}, {URL}, NOW) == []


def test_forged_quote_and_same_domain_authority_fail(policy):
    doc, rule, _ = policy
    forged = rule.model_copy(
        update={"evidence": (rule.evidence[0].model_copy(update={"quote": "7.0"}),)}
    )
    with pytest.raises(ValueError, match="authenticated"):
        validate_rule(forged, {URL: doc}, {URL}, NOW)
    with pytest.raises(ValueError, match="authenticated"):
        validate_rule(rule, {URL: doc}, {"https://example.edu/cafeteria"}, NOW)


def test_conflicting_policies_remain_visible(policy):
    _, rule, _ = policy
    other = rule.model_copy(update={"id": "other", "value": 7.0})
    doc, _, question = policy
    result = project(question, [rule, other], {URL: doc}, {URL}, NOW, proof=lambda _: True)
    assert result.state == "conflict"
    assert len(result.rules) == 2


def test_failed_search_never_means_not_published(policy):
    result = answer(policy, [], unavailable_reason="provider refused")
    assert result.state == "unavailable"
    assert answer(policy, []).state == "pending"


def test_expiry_and_missing_dependency_withhold_policy(policy):
    _, rule, _ = policy
    assert answer(policy, [rule.model_copy(update={"valid_until": NOW})]).state == "pending"
    assert (
        answer(policy, [rule.model_copy(update={"dependencies": ("missing",)})]).state == "pending"
    )


def test_complete_explicit_contract_can_close(policy):
    _, rule, _ = policy
    rules = [
        rule.model_copy(update={"id": key, "question": key})
        for key in (
            "english.overall",
            "english.bands",
            "english.waiver",
        )
    ]
    assert answer(policy, rules).state == "answered"


def test_cache_rejects_cross_institution_write(policy, tmp_path):
    _, rule, _ = policy
    with pytest.raises(ValueError, match="identity"):
        PublicEvidenceStore(tmp_path).save("Other", "2027", [rule])


def test_authentic_quote_cannot_certify_invented_value(policy):
    _, rule, _ = policy
    assert answer(policy, [rule.model_copy(update={"value": 99})]).state == "pending"


def test_unspecified_campus_does_not_select_specific_campus(policy):
    doc, rule, question = policy
    unspecified = question.model_copy(
        update={"scope": question.scope.model_copy(update={"campus": None})}
    )
    assert answer((doc, rule, unspecified)).state == "pending"


def test_conditions_and_exceptions_require_local_resolution(policy):
    _, rule, _ = policy
    conditional = rule.model_copy(update={"conditions": ("qualification recognised",)})
    assert answer(policy, [conditional]).state == "pending"
    assert answer(policy, [conditional], condition_applies=lambda _: True).state == "partial"
    exception = rule.model_copy(update={"exceptions": ("exchange applicant",)})
    assert answer(policy, [exception]).state == "pending"
    assert answer(policy, [exception], condition_applies=lambda _: False).state == "partial"


def test_cyclic_dependencies_do_not_prove_each_other(policy):
    _, rule, _ = policy
    a = rule.model_copy(update={"dependencies": ("b",)})
    b = rule.model_copy(update={"id": "b", "dependencies": (a.id,)})
    assert answer(policy, [a, b]).state == "pending"


def test_valid_cross_group_dependency_is_available_to_projection(policy):
    _, rule, _ = policy
    parent = rule.model_copy(update={"id": "parent", "group": QuestionGroup.ACADEMIC})
    dependent = rule.model_copy(update={"dependencies": (parent.id,)})
    assert answer(policy, [dependent, parent]).state == "partial"
