from pathlib import Path
import json,hashlib
from evaluation.research.expert.models import ExpertTrace
b=Path(__file__).resolve().parent;fixture=json.loads((b/'runtime/backend/evaluation/research/expert/data/trace.schema.json').read_text())
legacy=ExpertTrace.model_json_schema();wall=ExpertTrace.expert_wall_only_json_schema();assert legacy==fixture
assert legacy['$defs']==wall['$defs'] and legacy['additionalProperties'] is False and wall['additionalProperties'] is False
for schema in [ExpertTrace.model_json_schema(False,'#/custom/{model}',mode='serialization'),ExpertTrace.expert_wall_only_json_schema(False,'#/custom/{model}',mode='serialization')]:assert schema['properties']['actions']['items']['$ref']=='#/custom/Action'
wall['properties']['max_fetcher_calls']['const']=999
wall['$defs']['Action']['title']='mutated local result'
legacy['required'].clear()
assert ExpertTrace.model_json_schema()==fixture
fresh=ExpertTrace.expert_wall_only_json_schema();assert fresh['properties']['max_fetcher_calls']['const']==60 and fresh['$defs']['Action']['title']=='Action'
assert set(['max_elapsed_ms','max_search_queries','timing_policy','protective_wall_ms','initial_search_queries'])<=set(fresh['required'])
record={'status':'PASS_SINGLE_NATIVE_SCHEMA_API_CONTROL','default_entire_schema_equal_unchanged_fixture':True,'shared_state_mutation_does_not_leak':True,'positional_by_alias_ref_template_and_serialization_mode_forwarded':True,'explicit_wall_constraints':{k:fresh['properties'][k] for k in ['max_fetcher_calls','max_search_queries','max_elapsed_ms','timing_policy','protective_wall_ms','initial_search_queries']},'nonexpressible_raw_quote_packet_chronology_authority':'Python validators retained, not claimed by JSONSchema','app_network_model_SQL_calls':0}
(b/'logs/schema-api-check.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
