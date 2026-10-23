from pathlib import Path
import hashlib,json
stage=Path(__file__).resolve().parent
repo=stage.parents[1]/'work/unimatch-calendar-materials'
paths=['backend/app/domain/admissions_actions.py','backend/app/api/routes_admissions_actions.py','backend/tests/test_admissions_action_edits.py','backend/app/api/routes_results.py','backend/tests/test_result_read_freshness.py']
pins={}
for p in paths:
    raw=(repo/p).read_bytes();pins[p]=hashlib.sha256(raw).hexdigest()
    for name in ['repairs6c-preimages','repairs6c-proposal']:
        out=stage/name/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
def edit(p,old,new):
    out=stage/'repairs6c-proposal'/p;t=out.read_text();assert t.count(old)==1,(p,old[:80],t.count(old));out.write_text(t.replace(old,new))
p=paths[0]
edit(p,'def validate_state(value: object) -> s.CaseActionsState:', '''def retains_application_target(
    request: s.SetApplicationContextV2, state: s.CaseActionsState | None
) -> bool:
    """Exact owned saved target; no new source assertion or target substitution."""
    return state is not None and any(
        item.id == request.target.id and item.target == request.application_target
        for item in state.applications
    )


def validate_state(value: object) -> s.CaseActionsState:''')
edit(p,'''        current_app = application(request.target.id)
        if isinstance(request.application_target, s.ApplicationTargetV1):''','''        current_app = application(request.target.id)
        changed_context = current_app.target != request.application_target
        if changed_context and isinstance(request.application_target, s.ApplicationTargetV1):''')
edit(p,'''        changed_context = current_app.target != request.application_target
        if changed_context and current_app.status''','''        if changed_context and current_app.status''')
p=paths[1]
edit(p,'''    if isinstance(request, s.SetApplicationContextV2):
        target = request.application_target
        return (''','''    if isinstance(request, s.SetApplicationContextV2):
        if d.retains_application_target(request, state):
            return [], False
        target = request.application_target
        return (''')
edit(p,'''        and isinstance(request.application_target, s.ApplicationTargetV1)
    ):
        target = _application_target''','''        and isinstance(request.application_target, s.ApplicationTargetV1)
        and not d.retains_application_target(request, current.state)
    ):
        target = _application_target''')
p=paths[2]
edit(p,'from app.schemas import admissions_actions as s','from app.schemas import admissions_actions as s\nfrom app.models import ProgramResultRow, Entitlement')
with (stage/'repairs6c-proposal'/p).open('a') as f:f.write('''

@pytest.mark.parametrize("lost", ["result_deleted", "not_selected", "award_access_expired"])
def test_native_exact_saved_application_remains_editable_without_new_source(shared_route_lab, lost):
    lab = shared_route_lab
    result_id = seed_source(lab, scholarship=lost == "award_access_expired")
    selected = target(result_id)
    if lost == "award_access_expired":
        selected.update(purpose="scholarship", award_id="synthetic-award")
    first = post(lab, command("create_application", target=selected, label="Synthetic retained target", details=details()))
    app_id = first["applied_delta"]["applications"][0]["id"]
    with lab["factory"]() as session:
        if lost == "result_deleted":
            session.delete(session.get(ProgramResultRow, result_id))
        elif lost == "not_selected":
            session.get(ProgramResultRow, result_id).user_decision = "undecided"
        else:
            session.query(Entitlement).filter_by(profile_id=lab["case"]).delete()
        session.commit()
    body = change_context(app_id, 1, selected)
    edited = post(lab, body)
    app = edited["applied_delta"]["applications"][0]
    assert app["target"] == first["applied_delta"]["applications"][0]["target"]
    assert app["label"] == "Synthetic updated application" and app["context_ref"] is None
    assert app["created_ref"] == first["applied_delta"]["applications"][0]["created_ref"]
    assert post(lab, body) == edited
    changed = deepcopy(selected)
    changed["route"] = {"state": "applicant_entered", "value": "Synthetic changed route"}
    before = stored(lab)
    response = lab["client"].post(endpoint(lab) + "/commands", json=change_context(app_id, 2, changed))
    safe_error(response, "record_not_found" if lost == "result_deleted" else "target_not_selected" if lost == "not_selected" else "source_locked")
    assert stored(lab) == before
    assert read(lab)["state"]["applications"][0]["target"] == app["target"]
''')
p=paths[3]
edit(p,'from datetime import UTC, date, datetime','from datetime import UTC, date, datetime, timedelta')
edit(p,'from sqlalchemy.orm import Session','from sqlalchemy import and_, or_\nfrom sqlalchemy.orm import Session')
edit(p,'from app.domain.enums import Bucket, ClaimStatus, UserDecision','from app.domain.enums import Bucket, ClaimStatus, UserDecision\nfrom app.domain.freshness import DEFAULT_MAX_AGE_DAYS, MAX_AGE_DAYS')
edit(p,'''    if status:
        q = q.filter(ClaimRow.status == status)
    response.headers["X-Total-Count"] = str(q.count())
    now = datetime.now(UTC)''','''    now = datetime.now(UTC)
    if status in {ClaimStatus.VERIFIED_CURRENT.value, ClaimStatus.POSSIBLY_STALE.value}:
        # Use the same inclusive windows as the detached read BEFORE count/paging.
        # Authoritative row columns determine lifecycle/type/read moment; no DML.
        aged = or_(
            *[
                and_(ClaimRow.claim_type == kind.value, ClaimRow.accessed_at <= now - timedelta(days=days))
                for kind, days in MAX_AGE_DAYS.items()
            ],
            and_(ClaimRow.claim_type.notin_([kind.value for kind in MAX_AGE_DAYS]), ClaimRow.accessed_at <= now - timedelta(days=DEFAULT_MAX_AGE_DAYS)),
        )
        if status == ClaimStatus.VERIFIED_CURRENT.value:
            q = q.filter(ClaimRow.status == status, ~aged)
        else:
            q = q.filter(or_(ClaimRow.status == status, and_(ClaimRow.status == ClaimStatus.VERIFIED_CURRENT.value, aged)))
    elif status:
        q = q.filter(ClaimRow.status == status)
    response.headers["X-Total-Count"] = str(q.count())''')
edit(p,'ClaimOut.model_validate({**c.payload, "id": c.id, "status": c.status})','ClaimOut.model_validate({**c.payload, "id": c.id, "status": c.status, "claim_type": c.claim_type, "accessed_at": c.accessed_at})')
p=paths[4]
with (stage/'repairs6c-proposal'/p).open('a') as f:f.write('''

@pytest.mark.parametrize("status", ["VERIFIED_CURRENT", "POSSIBLY_STALE", "SUPERSEDED", "not-a-status"])
def test_native_projected_claim_filter_count_and_paging_use_exact_current_windows(prep_lab, monkeypatch, status):
    from app.api import routes_results
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)
    monkeypatch.setattr(routes_results, "datetime", FixedClock)
    lab = prep_lab
    full_case(lab)
    run_id, _ = seed_run(lab)
    rows = [
        ("admission_deadline", "VERIFIED_CURRENT", 30, -1),
        ("admission_deadline", "VERIFIED_CURRENT", 30, 0),
        ("tuition", "VERIFIED_CURRENT", 120, 0),
        ("program_exists", "VERIFIED_CURRENT", 180, 0),
        ("admission_deadline", "POSSIBLY_STALE", 1, 0),
        ("admission_deadline", "SUPERSEDED", 300, 0),
    ]
    originals = {}
    with lab["factory"]() as session:
        for kind, lifecycle, days, microseconds in rows:
            at = NOW - timedelta(days=days, microseconds=microseconds)
            value = claim(status=lifecycle, at=at)
            value.claim_type = kind
            row = ClaimRow(run_id=run_id, claim_type=kind, status=lifecycle, source_url=value.source_url, accessed_at=at, source_specificity=value.source_specificity.value, payload={})
            session.add(row);session.flush();value.id = row.id
            # Read metadata is authoritative in columns even if the old payload disagrees.
            value.accessed_at = NOW
            row.payload = value.model_dump(mode="json")
            originals[row.id] = deepcopy(row.payload)
        session.commit()
    expected = {"VERIFIED_CURRENT": 1, "POSSIBLY_STALE": 4, "SUPERSEDED": 1, "not-a-status": 0}[status]
    found = []
    for offset in range(expected + 1):
        response, sql = _capture(lab, lambda offset=offset: lab["client"].get(f"/api/runs/{run_id}/claims", params={"status": status, "limit": 1, "offset": offset}))
        assert response.status_code == 200, response.text
        assert_no_dml(sql)
        assert response.headers["X-Total-Count"] == str(expected)
        page = response.json()
        assert len(page) == (1 if offset < expected else 0)
        assert all(item["status"] == status for item in page)
        found.extend(item["id"] for item in page)
    assert len(set(found)) == expected
    with lab["factory"]() as session:
        assert {row.id: row.payload for row in session.query(ClaimRow).filter_by(run_id=run_id)} == originals
''')
(stage/'REPAIRS_6C_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','paths':pins},indent=2)+'\n')
print('External-only exact5 repair proposal prepared; no app imports/tests or source/Git changes.')
