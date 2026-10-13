from pathlib import Path
s=Path(__file__).resolve().parent;out=s/'inputs6a-proposal';pre=s/'inputs6a-preimages'
def get(p):return(pre/p).read_text()
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='backend/app/pipeline/runner.py';t=get(p);marker='from app.schemas.profile import ApplicantProfileIn';assert marker in t;t=t.replace(marker,'from app.domain.profile_input_provenance import INPUT_OBSERVATION_KEY, observe_actual_inputs\n'+marker,1)
marker='        self.run.stage_state = self.state.dump()';assert marker in t;t=t.replace(marker,'''        # Actual runner inputs join the existing own heartbeat transaction.
        # Legacy/corrupt snapshots are never backfilled from today's profile.
        snapshot = self.run.settings_snapshot or {}
        observed_inputs = observe_actual_inputs(snapshot.get(INPUT_OBSERVATION_KEY), self.profile)
        if observed_inputs is not None:
            self.run.settings_snapshot = {**snapshot, INPUT_OBSERVATION_KEY: observed_inputs}
'''+marker,1)
marker='        if read_budget.LEDGER_KEY in previous_snapshot:';assert marker in t;t=t.replace(marker,'''        if INPUT_OBSERVATION_KEY in previous_snapshot:
            self._pending_settings_snapshot[INPUT_OBSERVATION_KEY] = previous_snapshot[INPUT_OBSERVATION_KEY]
'''+marker,1);put(p,t)
p='backend/app/api/routes_research.py';t=get(p);marker='from app.schemas.programme_observations import';index=t.index(marker);t=t[:index]+'from app.domain.profile_input_provenance import INPUT_OBSERVATION_KEY, input_status, pending_input_observation\nfrom app.schemas.profile import ApplicantProfileIn\nfrom app.schemas.research_read import ResearchInputStatusReadV1\n'+t[index:]
t=t.replace('class RunView(BaseModel):\n','class RunView(BaseModel):\n    profile_input_status: ResearchInputStatusReadV1\n',1)
marker='    observed = observation_projection(run.programme_observations)';assert marker in t;t=t.replace(marker,'''    profile_row = session.get(ApplicantProfileRow, run.profile_id)
    observed_profile = None
    if profile_row is not None:
        try:
            observed_profile = ApplicantProfileIn.model_validate(profile_row.payload)
        except ValueError:
            pass  # Corrupt historical profile cannot certify current applicability.
    profile_read = input_status((run.settings_snapshot or {}).get(INPUT_OBSERVATION_KEY), observed_profile, now)
'''+marker,1)
t=t.replace('    return RunView(\n','    return RunView(\n        profile_input_status=profile_read,\n',1)
t=t.replace('        settings=dict(run.settings_snapshot or {}),','        settings={key: value for key, value in (run.settings_snapshot or {}).items() if key != INPUT_OBSERVATION_KEY},',1)
marker='        stage_state=RunState.load(None).dump(),';assert marker in t;t=t.replace(marker,marker+'\n        settings_snapshot={INPUT_OBSERVATION_KEY: pending_input_observation()},',1);put(p,t)
p='backend/app/api/routes_results.py';t=get(p);marker='from app.schemas.result import DecisionIn, ProgramResult';assert marker in t;t=t.replace(marker,'from app.domain.result_read import claim_read, result_read\nfrom app.schemas.claim import ClaimOut\nfrom app.schemas.research_read import ProgramResultReadV1\n'+marker,1)
t=t.replace('@router.get("/results", response_model=list[ProgramResult])','@router.get("/results", response_model=list[ProgramResultReadV1])',1)
a=t.index('def list_results(');b=t.index('\n\n@router.get("/summary"',a);block=t[a:b].replace(') -> list[ProgramResult]:',') -> list[ProgramResultReadV1]:',1)
block=block.replace('    if allowed:\n        return results','    now = datetime.now(UTC)\n    if allowed:\n        return [result_read(result, now) for result in results]',1).replace('return [free_view(r) for r in truncate_shortlist(results, settings.free_shortlist_rows)]','return [result_read(free_view(r), now, evidence_available=False) for r in truncate_shortlist(results, settings.free_shortlist_rows)]',1);t=t[:a]+block+t[b:]
# Change only the current detail GET; mutations retain original saved schema.
marker='@router.get("/results/{result_id}", response_model=ProgramResult)';assert marker in t;t=t.replace(marker,'@router.get("/results/{result_id}", response_model=ProgramResultReadV1)',1);a=t.index('def get_result(') if 'def get_result(' in t else t.index('def result_detail(');b=t.index('\n\nclass RefreshOut',a);block=t[a:b].replace(') -> ProgramResult:',') -> ProgramResultReadV1:',1).replace('return ProgramResult.model_validate(row.payload)','return result_read(ProgramResult.model_validate(row.payload), datetime.now(UTC))',1);t=t[:a]+block+t[b:]
# The public evidence page remains paginated and uses row status as the authoritative stored lifecycle.
a=t.index('def list_claims(');b=t.index('\n\n@router.get("/conflicts"',a);block=t[a:b];old='''    return [
        {"id": c.id, "result_id": c.result_id, **c.payload}
        for c in q.order_by(ClaimRow.claim_type).limit(limit).offset(offset).all()
    ]''';new='''    now = datetime.now(UTC)
    return [
        {"result_id": c.result_id, **claim_read(ClaimOut.model_validate({**c.payload, "id": c.id, "status": c.status}), now).model_dump(mode="json")}
        for c in q.order_by(ClaimRow.claim_type).limit(limit).offset(offset).all()
    ]''';assert old in block;block=block.replace(old,new,1);t=t[:a]+block+t[b:];put(p,t)
print('External route/runner proposals prepared; original saved mutations/exports untouched. Native test proposals/review still pending; nothing applied.')
