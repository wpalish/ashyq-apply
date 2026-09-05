"""What a school sees: quota spent silently, then the phase 1 price."""

from __future__ import annotations

from app.models.subscription import Subscription, SubscriptionStatus


def _grant(quota: int) -> str:
    """Give the paid client's organization a subscription. Returns its id."""
    from app.db import session_scope
    from app.security import DEV_ORGANIZATION_ID

    with session_scope() as session:
        sub = Subscription(
            organization_id=DEV_ORGANIZATION_ID,
            case_quota=quota,
            duration_days=365,
            status=SubscriptionStatus.PENDING.value,
        )
        session.add(sub)
        session.flush()
        return sub.id


def test_without_a_subscription_the_paywall_offers_only_a_price(paid_client, case_id) -> None:
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is False
    assert body["subscription_cases_left"] is None
    assert body["subscription_queued"] == 0


def test_a_subscription_is_reported_before_it_is_spent(paid_client, case_id) -> None:
    _grant(5)
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    # Not started yet, so it is queued rather than current.
    assert body["subscription_queued"] == 1
    assert body["subscription_cases_left"] is None


def test_starting_a_run_spends_one_unit_and_runs_full(paid_client, case_id) -> None:
    _grant(5)
    run = paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True}).json()
    assert run["candidate_limit"] > 5

    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is True
    assert body["subscription_cases_left"] == 4


def test_a_second_run_on_the_same_case_spends_nothing(paid_client, case_id) -> None:
    _grant(5)
    for _ in range(2):
        paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True})
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["subscription_cases_left"] == 4


def test_unlocking_from_the_subscription_opens_a_case(paid_client, case_id) -> None:
    _grant(2)
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": case_id}
    )
    assert response.status_code == 200
    assert response.json()["full_access"] is True
    assert response.json()["subscription_cases_left"] == 1


def test_unlocking_without_quota_is_a_conflict(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": case_id}
    )
    assert response.status_code == 409


def test_a_402_tells_the_frontend_there_is_no_quota(paid_client, case_id) -> None:
    run = paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True}).json()
    body = paid_client.get(f"/api/runs/{run['id']}/claims").json()
    assert body["code"] == "payment_required"
    assert body["subscription_cases_left"] is None


def test_a_second_case_still_sees_the_remaining_quota(paid_client, case_id) -> None:
    """One unit spent on the first case leaves one to offer on the next."""
    from app.corpus.demo_profile import DEMO_PROFILE

    _grant(2)
    paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True})

    second = paid_client.post(
        "/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")
    ).json()["id"]
    body = paid_client.get(f"/api/billing/entitlements?profile_id={second}").json()
    assert body["full_access"] is False
    assert body["subscription_cases_left"] == 1


def test_an_unknown_case_cannot_be_unlocked(paid_client) -> None:
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": "0" * 32}
    )
    assert response.status_code == 404
