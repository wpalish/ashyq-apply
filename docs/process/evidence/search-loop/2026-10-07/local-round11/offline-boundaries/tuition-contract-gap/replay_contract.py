"""Bounded native contract proof, not a tuition-rule prototype. Saved bytes only."""
import asyncio,json,re
from dataclasses import asdict,fields
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
from app.adapters.base import Candidate
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import ClaimBuilder,_MONEY,parse_money,readable_text
from app.adapters.fetching import FetchResult
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import main_content
from app.adapters.structured_costs import _complete_quote
from app.domain.claim_scope import ClaimScope,RequestedScope
from app.domain.enums import ClaimType,FetchOutcome,SourceSpecificity
from app.schemas.claim import Claim
from app.schemas.money import Money

B=Path(__file__).resolve().parent
BODY=B/'evidence/bebf43d56e3b363476eed0f7cddede69.body';META=BODY.with_name(BODY.name.replace('.body','.meta.json'))
class RetainedOnly:
 def __init__(self):self.calls=[]
 async def get(self,url):
  m=json.loads(META.read_text());assert url==m['url'],'unretained URL';self.calls.append(url);b=BODY.read_bytes()
  return FetchResult(url=url,outcome=FetchOutcome.OK,status_code=m['status_code'],content=b,text=b.decode(m['encoding']),content_type=m['content_type'],final_url=m['final_url'],fetched_at=datetime.fromisoformat(m['fetched_at']),content_hash=m['content_hash'])
async def run():
 html=BODY.read_text();meta=json.loads(META.read_text());text=readable_text(html);content=main_content(parse_html(html));ir=build_document_ir(str(content),meta['url']);tables=content.find_all('table');checks={};outputs=[]
 cand=Candidate(name='Aalto University',country='Finland',city='Espoo',domain='aalto.fi',costs_url=meta['url'])
 for attempt in range(2):
  f=RetainedOnly();breakdown,ar=await WebCostAdapter(f,'2027/28').fetch(cand)
  outputs.append({'breakdown':breakdown.model_dump(mode='json'),'adapter':{'claims':[c.model_dump(mode='json') for c in ar.claims],'errors':ar.errors,'pages_checked':ar.pages_checked,'pages_failed':ar.pages_failed,'retry_urls':ar.retry_urls,'page_types':ar.page_types,'page_outcomes':[asdict(x) for x in ar.page_outcomes]},'calls':f.calls})
 checks['OFF_native_full_output_repeat_equality']=outputs[0]==outputs[1]
 checks['OFF_original_no_claim_or_arithmetic_item']=outputs[0]['adapter']['claims']==[] and outputs[0]['breakdown']['items']=={} and outputs[0]['breakdown']['total'] is None
 diag=[]
 for tableid,table in enumerate(tables):
  proof=' '.join(table.get_text(' ',strip=True).split());quote=_complete_quote(proof,text)
  cells=ir.table_cells(tableid);degree=next(c.text for c in cells if re.fullmatch(r"(?:Bachelor|Master)'s programmes",c.text))
  cohort=next(c.text for c in cells if c.text.startswith('Tuition fees for rights to study beginning'))
  money_cells=[c for c in cells if c.row_headers and _MONEY.search(c.text)]
  diag.append({'table_id':tableid,'degree_header_original':degree,'cohort_header_original':cohort,'entire_table_contiguous_original_quote':quote,'quote_chars':len(quote),'quote_contiguous':bool(quote and quote in text),'source_rows_diagnostic_only':[{'field_header_original':c.row_headers[0],'money_original':c.text,'parsed_money_atom':parse_money(c.text),'annual_period_original':'per academic year' if re.search(r'per academic year$',c.text) else None} for c in money_cells],'population':None,'population_unknown_reason':'not stated inside either own complete table quote; global fee population/exemption prose is not silently transferred','academic_year':None,'programme':None,'intake':None,'claims_emitted':0})
 checks['original_degree_tables_Bachelor3_Master4_source_rows_only']=[len(t['source_rows_diagnostic_only']) for t in diag]==[3,4]
 checks['original_table_quotes_whole_contiguous_under600']=all(t['quote_contiguous'] and t['quote_chars']<=600 for t in diag)
 cohort_value='rights to study beginning on or after 1 August 2025';requested={'university':'Aalto University','degree':'bachelor','effective_cohort':cohort_value,'study_field':'Field of Technology','period':'per academic year'}
 mapped=ClaimScope.from_mapping(requested);cohort_keys={'effective_cohort','study_field','period'}
 checks['scope_from_mapping_drops_source_owned_cohort_field_period']=not any(k in mapped.stated() for k in cohort_keys)
 errors={}
 for target,fn in [('ClaimScope',lambda:ClaimScope(degree='bachelor',effective_cohort=cohort_value)),('RequestedScope',lambda:RequestedScope(effective_cohort=cohort_value)),('Money',lambda:Money(amount=12000,currency='EUR',effective_cohort=cohort_value,period='per academic year'))]:
  try:fn()
  except (TypeError,ValidationError) as e:errors[target]={'type':type(e).__name__,'message':str(e)}
 checks['native_typed_models_reject_unknown_cohort_dimensions']=set(errors)=={'ClaimScope','RequestedScope','Money'}
 # A minimal native ClaimBuilder contrast: unknown year is allowed, but scope cannot
 # preserve the source's cohort/field/period as dimensions. Not a proposal emission.
 excerpt=diag[0]['entire_table_contiguous_original_quote'];builder=ClaimBuilder(source_url=meta['url'],page_title='Scholarships and Tuition Fees | Aalto University',specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,academic_year=None,official_domain=True,accessed_at=datetime.fromisoformat(meta['fetched_at']),scope=ClaimScope(degree='bachelor'),page_text=text,allowed_domains=('aalto.fi',))
 value={'amount':12000,'currency':'EUR','effective_cohort':cohort_value,'study_field':'Field of Technology','period':'per academic year'}
 claim=builder.add(ClaimType.TUITION,value,excerpt,subject_key='Field of Technology',notes='DIAGNOSTIC CONTRACT CONTROL ONLY; not proposal output')
 assert claim is not None,builder.rejected
 checks['ClaimBuilder_unknown_year_allowed_without_requested2027']=claim.academic_year is None and claim.intake is None and claim.program is None and claim.scope.academic_year is None
 checks['extra_normalized_value_not_typed_scope']=cohort_keys<=set(claim.normalized_value) and not any(k in claim.scope.stated() for k in cohort_keys)
 checks['unknown_year_scope_covers_requested2027_isUNKNOWN']=str(claim.scope.covers(RequestedScope(degree='bachelor',academic_year='2027/28')))=='unknown'
 checks['no_scope_fields_for_effective_cohort_period_studyfield']=cohort_keys.isdisjoint({f.name for f in fields(ClaimScope)})
 gap={'source_owned_dimensions_unrepresentable':['effective start-of-study cohort','study field distinct from faculty or programme','annual tariff period distinct from academic year'],'free_text_or_arbitrary_dict_not_typed_scope':True,'missing_schema_dimensions_do_not_authorize_mapping_to_academic_year':'1 August2025 onward is an open cohort boundary, not2025/26 or2027/28','current_native_builder_control_payload':claim.model_dump(mode='json'),'scope_constructor_model_errors':errors,'scope_mapping_drops':sorted(cohort_keys),'scope_mapping_retained':asdict(mapped)}
 out={'status':'CONTRACT_GAP_NO_RULE_PATCH','proposed_feature_default':False,'feature_implemented':False,'OFF_contract':'Unchanged native WebCostAdapter called twice, exact whole-result value equality; no patched-module OFF claim','normal_app_imports':True,'network_provider_model_calls':0,'semantic_labels_or_scoring':0,'checks':checks,'OFF_native_outputs':outputs,'original_table_observations_not_claims':diag,'contract_gap':gap,'controls_not_executed_due_gap':['persemester/month/oneoff/waiver/exemption/year/field/header/currency/quote negatives for a future ON rule; no ON algorithm exists']}
 (B/'contract-controls.offline.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
 print('PASS',sum(checks.values()),'RED',sum(not x for x in checks.values()),'degree rows',[len(x['source_rows_diagnostic_only']) for x in diag]);print('wholequotes',[x['quote_chars'] for x in diag]);assert all(checks.values()),checks
if __name__=='__main__':asyncio.run(run())
