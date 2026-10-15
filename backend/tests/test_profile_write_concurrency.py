"""Two real saved-profile clients must not silently lose independent edits.

Native migrated SQLite/private PostgreSQL and two independent Session reads;
no model, Session, HTTP handler or persistence response is replaced.
"""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ApplicantProfileRow

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")


@pytest.mark.parametrize("first_field", ["funding", "gpa"])
def test_two_native_clients_preserve_the_first_change_and_reject_a_stale_profile(
    shared_route_lab, first_field, record_property
):
    lab = shared_route_lab
    with lab["factory"]() as first_session, lab["factory"]() as second_session:
        assert first_session is not second_session
        first = first_session.get(ApplicantProfileRow, lab["case"])
        second = second_session.get(ApplicantProfileRow, lab["case"])
        assert first is not None and second is not None
        first_draft, second_draft = deepcopy(first.payload), deepcopy(second.payload)
        assert first_draft == second_draft

    # Both clients prepared their edits from exactly P0 before either save.
    budget = first_draft if first_field == "funding" else second_draft
    grades = second_draft if first_field == "funding" else first_draft
    budget["funding"]["max_annual_budget"] = 12345.0
    grades["academics"]["gpa"] = {
        "raw_value": 3.125,
        "raw_scale_max": 5,
        "raw_scale_label": "Synthetic scale",
    }
    path = f"/api/profiles/{lab['case']}"
    clients = [TestClient(app), TestClient(app)]  # no application lifespan/worker
    try:
        for client in clients:
            client.cookies.update(lab["client"].cookies)
        headers = {"X-Expected-Profile-Revision": "1", "Idempotency-Key": str(uuid4())}
        accepted = clients[0].put(path, json=first_draft, headers=headers)
        assert accepted.status_code == 200, accepted.text
        stale = clients[1].put(
            path,
            json=second_draft,
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        current = clients[0].get(path)
        assert current.status_code == 200, current.text
        body = current.json()
        record_property("native_driver", lab["engine"].dialect.name)
        record_property("two_actual_sessions_read_p0", True)
        record_property("first_field", first_field)
        record_property("stale_http_status", stale.status_code)
        record_property("final_budget", body["funding"]["max_annual_budget"])
        record_property("final_gpa", body["academics"]["gpa"]["raw_value"])
        assert stale.status_code == 409, stale.text
        if first_field == "funding":
            assert body["funding"]["max_annual_budget"] == 12345.0
        else:
            assert body["academics"]["gpa"]["raw_value"] == 3.125
    finally:
        for client in clients:
            client.close()
