from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'proposed/backend';p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('    receipt = {"case_id": case_id,','''    pending = [{"path": str(path.relative_to(root)), "sha256": sha(path)} for path in (root / "raw").glob("*.json") if read(path).get("outcome") == "pending"]
    receipt = {"pending_raw_logs": pending, "source_counters_complete": not pending, "case_id": case_id,''',1)
s=s.replace('and clock is time.monotonic, "runtime_mode"', 'and clock is time.monotonic and not pending, "runtime_mode"',1)
p.write_text(s)
p=B/'tests/test_local_pilot.py';s=p.read_text();anchor="    with pytest.raises(ValueError,match='wall cannot reset'):run_tool(plan(wall_elapsed_before_ms=1,resume_summary=second),tmp_path)"
s=s.replace(anchor,anchor+"\n    contradictory=copy.deepcopy(second);contradictory['protective_wall_ms']=1\n    with pytest.raises(ValueError,match='summary'):run_tool(plan(wall_elapsed_before_ms=350000,resume_summary=contradictory),tmp_path)")
s += '''
'''
# Include exact whole trace monotonic wall check in existing closure scenario.
anchor="    # All OTHER citations remain gated; a fabricated quote cannot enter a journal."
insert='''    from evaluation.research.expert.models import Action, _controller_budget, validate_trace
    summary=p.read(root/'tool-0001.summary.json')
    second_summary=run_tool(plan(case_id='groningen',log_prefix='groningen',official_domains=['rug.nl'],wall_elapsed_before_ms=max(100,summary['final']['wall_elapsed_ms']),resume_summary=summary,actions=[dict(tool='fetcher',url='https://rug.nl/admissions')]),root/'raw')
    row=second_summary['actions'][0]
    second=copy.deepcopy(receipt['trace']['actions'][0])
    second.update(step=2,at=row['at'],observed_before='Read the source again.',observed_from_step=1,action='Read the source again.',raw_log_path=row['raw_log_path'],raw_log_sha256=row['raw_log_sha256'],request=row['request'],final_url=row['final_url'],elapsed_ms=row['elapsed_ms'],elapsed_ms_cumulative=row['elapsed_ms_cumulative'],fetcher_calls_cumulative=row['fetcher_calls_cumulative'],search_queries_cumulative=row['search_queries_cumulative'])
    full_trace=copy.deepcopy(receipt['trace']);full_trace['actions'].append(second);full_trace['ended_at']=datetime.now(UTC).isoformat()
    packet=p.read(root/'packet.original.json')
    validate_trace(full_trace,packet,logs_dir=root/'raw')
    raw_second=root/'raw'/row['raw_log_path'];value=p.read(raw_second);value['wall_elapsed_ms_before']=0;raw_second.write_text(json.dumps(value));full_trace['actions'][1]['raw_log_sha256']=p.sha(raw_second)
    with pytest.raises(ValueError,match='between actions'):validate_trace(full_trace,packet,logs_dir=root/'raw')
    with pytest.raises(ValueError,match='structured'):_controller_budget(ExpertTrace.model_validate(legacy),Action.model_validate(legacy['actions'][0]),{'tool_policy':['malformed']},'independent_full_budget')
'''
assert anchor in s;s=s.replace(anchor,insert+anchor);p.write_text(s)
for p in B.rglob('*.py'):
 q=O/'runtime/backend'/p.relative_to(B);q.write_bytes(p.read_bytes())
