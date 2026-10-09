"""Model suggestions are bounded proposals, never self-authenticating facts."""

from types import SimpleNamespace

import pytest

from app.research.semantic import (
    CritiqueResponse,
    PublicFragment,
    SemanticBudget,
    SemanticRequest,
    SemanticResponse,
    semantic_fallback,
)
from tests.test_research_evidence import NOW, URL, policy  # noqa: F401


@pytest.fixture
def setup_semantic(policy):  # noqa: F811 - imported pytest fixture
    doc, rule, _ = policy
    request = SemanticRequest(
        questions=(rule.question,),
        fragments=(
            PublicFragment(
                url=URL,
                block_id=rule.evidence[0].block_id,
                text=rule.evidence[0].quote,
                section_path=rule.evidence[0].section_path,
            ),
        ),
    )
    calls = []

    async def propose(request, *, max_output_tokens):
        calls.append("propose")
        assert max_output_tokens <= 2000
        return SemanticResponse(rules=(rule,), input_tokens=20, output_tokens=40, model="fake")

    async def critique(request, rules, *, max_output_tokens):
        calls.append("critic")
        return CritiqueResponse(
            rejected_ids=frozenset(), input_tokens=30, output_tokens=10, model="other-fake"
        )

    return (
        request,
        SimpleNamespace(propose=propose),
        SimpleNamespace(critique=critique),
        doc,
        rule,
        calls,
    )


async def execute(setup_semantic, budget=None, proof=lambda *_: True):
    request, provider, critic, doc, _, _ = setup_semantic
    return await semantic_fallback(
        request, provider, critic, budget or SemanticBudget(), {URL: doc}, {URL}, NOW, proof
    )


@pytest.mark.asyncio
async def test_candidate_requires_both_independent_critic_and_deterministic_proof(setup_semantic):
    *_, calls = setup_semantic
    assert await execute(setup_semantic, proof=lambda *_: False) == []
    assert calls == ["propose", "critic"]
    assert len(await execute(setup_semantic)) == 1


@pytest.mark.asyncio
async def test_critic_rejection_cannot_be_overridden(setup_semantic):
    _, _, critic, _, rule, _ = setup_semantic

    async def reject(*args, **kwargs):
        return CritiqueResponse(
            rejected_ids=frozenset({rule.id}), input_tokens=10, output_tokens=10, model="critic"
        )

    critic.critique = reject
    assert await execute(setup_semantic) == []


@pytest.mark.asyncio
async def test_retry_keeps_reservations_and_unknown_cost_after_provider_failure(setup_semantic):
    _, provider, _, _, _, calls = setup_semantic

    async def fail(*args, **kwargs):
        calls.append("failed")
        raise RuntimeError("refused")

    provider.propose = fail
    budget = SemanticBudget(max_calls=1)
    with pytest.raises(RuntimeError, match="refused"):
        await execute(setup_semantic, budget)
    assert budget.calls == 1 and budget.input_tokens > 0 and budget.output_tokens == 2000
    assert budget.cost_usd is None
    with pytest.raises(ValueError, match="exhausted"):
        await execute(setup_semantic, budget)
    assert calls == ["failed"]


@pytest.mark.asyncio
async def test_critic_is_charged_and_missing_cost_is_not_zero(setup_semantic):
    budget = SemanticBudget()
    await execute(setup_semantic, budget)
    assert budget.calls == 2 and budget.output_tokens == 4000
    assert budget.cost_usd is None


@pytest.mark.asyncio
async def test_insufficient_input_budget_prevents_dispatch(setup_semantic):
    with pytest.raises(ValueError, match="exhausted"):
        await execute(setup_semantic, SemanticBudget(max_input_tokens=1))
    assert setup_semantic[-1] == []
