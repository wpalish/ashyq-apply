"""The decision seam: TypeSafe over a mock transport, the fake, and the link ranker."""

from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.decisions import Choice, DecisionUnavailable, Noul
from app.adapters.decisions.fake import FakeDecisionModel
from app.adapters.decisions.link_ranker import LinkCandidate, rank_links
from app.adapters.decisions.typesafe import DEFAULT_MODEL, TYPESAFE_URL, TypeSafeDecisionModel
from app.config import Settings


def _model(handler) -> TypeSafeDecisionModel:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TypeSafeDecisionModel("test-key-not-real", client=client)


def _ok(body):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=body)

    handler.calls = calls  # type: ignore[attr-defined]
    return handler


async def test_the_request_and_the_answers_follow_the_contract():
    handler = _ok(
        {
            "model": "jev-1.13.0",
            "answers": {
                "urgent": {"type": "noul", "noul": 0.9},
                "team": {
                    "type": "choice",
                    "choice": "a",
                    "probabilities": {"a": 0.7, "b": 0.3},
                    "confidence": 0.6,
                },
            },
            "usage": {"input_tokens": 12},
        }
    )
    response = await _model(handler).ask(
        {"x": 1},
        {"urgent": Noul("urgent?"), "team": Choice("which?", {"a": "A", "b": "B"})},
    )
    request = handler.calls[0]
    body = json.loads(request.content)
    assert str(request.url) == TYPESAFE_URL
    assert request.headers["authorization"] == "Bearer test-key-not-real"
    assert body["model"] == DEFAULT_MODEL
    assert body["questions"]["team"] == {
        "type": "choice",
        "instructions": "which?",
        "criteria": {"a": "A", "b": "B"},
    }
    assert response.answers["urgent"].probability == 0.9
    assert response.answers["team"].choice == "a"
    assert response.answers["team"].probability == 0.7
    assert (response.model, response.input_tokens) == ("jev-1.13.0", 12)


@pytest.mark.parametrize(
    "status, body",
    [
        (429, {"error": "slow down"}),
        (200, {"answers": {}}),
        (200, {"answers": {"q": {"type": "noul", "noul": 1.7}}}),
        (200, {"answers": {"q": {"type": "choice", "choice": "zzz"}}}),
    ],
)
async def test_anything_unexpected_is_unavailable(status, body):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    question = Choice("?", {"a": "A"}) if "choice" in json.dumps(body) else Noul("?")
    with pytest.raises(DecisionUnavailable):
        await _model(handler).ask({}, {"q": question})


async def test_a_transport_error_is_unavailable():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(DecisionUnavailable):
        await _model(boom).ask({}, {"q": Noul("?")})


def test_settings_validate_the_provider_and_key():
    with pytest.raises(RuntimeError, match="UNIMATCH_TYPESAFE_API_KEY"):
        Settings(decision_provider="typesafe").validate_runtime()
    with pytest.raises(RuntimeError, match="not one of"):
        Settings(decision_provider="gpt").validate_runtime()
    assert "k-secret" not in repr(Settings(typesafe_api_key="k-secret"))


async def test_the_ranker_only_reorders_the_links_it_was_given():
    links = [
        LinkCandidate("https://u.edu/contact", "Contact us"),
        LinkCandidate("https://u.edu/bachelors/computer-science", "Computer Science"),
        LinkCandidate("https://u.edu/museum", "Museum"),
    ]

    def answer(state, qid, question):
        return 0.95 if "computer" in state["links"][qid]["url"] else 0.1

    ranked, model = await rank_links(
        FakeDecisionModel(answer),
        links,
        field="computer science",
        degree="bachelor",
        target="programme page",
    )
    assert ranked[0].url == "https://u.edu/bachelors/computer-science"
    assert {r.url for r in ranked} == {lk.url for lk in links}
    assert model == "fake-0"


async def test_the_ranker_falls_back_to_the_input_order_when_unavailable():
    links = [LinkCandidate("https://u.edu/a"), LinkCandidate("https://u.edu/b")]
    ranked, model = await rank_links(
        FakeDecisionModel(fail=True), links, field="cs", degree="bachelor", target="x"
    )
    assert [r.url for r in ranked] == ["https://u.edu/a", "https://u.edu/b"]
    assert model is None and all(r.probability is None for r in ranked)


async def test_no_applicant_data_is_in_the_state():
    model = FakeDecisionModel()
    await rank_links(
        model, [LinkCandidate("https://u.edu/a", "A")], field="cs", degree="bachelor", target="x"
    )
    state, _ = model.calls[0]
    assert set(state) == {"field", "degree", "links"}
