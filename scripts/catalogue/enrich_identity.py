"""Fetch public encyclopedia identity data. No applicant data or model/provider calls."""
import json,re,unicodedata,urllib.request,urllib.parse,time,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
seed=json.loads((ROOT/'backend/app/catalogue/unimatch_top500_seed.json').read_text())['universities']
source=json.load(open('/tmp/unimatch-public-universities.json'))
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',re.sub(r'\([^)]*\)','',s)).encode('ascii','ignore').decode().lower()).removeprefix('the')
index={norm(x['name']):x for x in source}; history={x['description']:x for x in source if len(x.get('description',''))>120}
manual={'UCL':'University College London','KFUPM':'King Fahd University of Petroleum and Minerals','KAIST':'KAIST','Universiti Malaya (UM)':'University of Malaya','The University of New South Wales (UNSW Sydney)':'University of New South Wales','EPFL – École polytechnique fédérale de Lausanne':'EPFL','Ludwig-Maximilians-Universität München':'Ludwig Maximilian University of Munich','Université PSL':'Paris Sciences et Lettres University','Trinity College Dublin, The University of Dublin':'Trinity College Dublin','Université Paris-Saclay':'Paris-Saclay University','Adelaide University':'Adelaide University','The University of Osaka':'Osaka University','Institute of Science Tokyo':'Institute of Science Tokyo','Freie Universitaet Berlin':'Free University of Berlin','Pohang University of Science And Technology (POSTECH)':'Pohang University of Science and Technology'}
rows=[]
for s in seed:
 m=index.get(norm(s['name'])) or history.get(s['short_history'])
 title=manual.get(s['name']) or (m['name'] if m else re.sub(r'\s*\([^)]*\)','',s['name']))
 rows.append((s,title,m))
api='https://en.wikipedia.org/w/api.php'
def query(params):
 params={'action':'query','format':'json',**params};url=api+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':'UnimatchCatalogue/1.0 (identity snapshots; local development)'})
 with urllib.request.urlopen(req,timeout=40) as f:return json.load(f)
allpages={};redirects={};errors=[]
for start in range(0,len(rows),20):
 titles=[x[1] for x in rows[start:start+20]]
 try:
  q=query({'titles':'|'.join(titles),'redirects':'1','prop':'extracts|images|pageprops','exintro':'1','explaintext':'1','exlimit':'20','imlimit':'500'})['query']
  redirects.update({x['from']:x['to'] for x in q.get('normalized',[])+q.get('redirects',[])})
  for p in q.get('pages',{}).values():allpages[p['title']]=p
 except Exception as e:errors.append({'titles':titles,'error':str(e)});break
 print('batch',start,'pages',len(allpages),flush=True)
 time.sleep(.12)
Path('/tmp/unimatch-wiki-identities.json').write_text(json.dumps({'pages':allpages,'redirects':redirects,'errors':errors}))
result=[];miss=[]
for s,title,m in rows:
 seen=set()
 while title in redirects and title not in seen:seen.add(title);title=redirects[title]
 p=allpages.get(title,{})
 if 'disambiguation' in p.get('pageprops',{}):p={}
 excerpt=p.get('extract','')
 images=[x['title'] for x in p.get('images',[]) if re.search(r'logo|seal|coat.of.arms|crest|emblem|wordmark',x['title'],re.I) and not re.search(r'commons-logo|wiki|ambox|flag|question|info',x['title'],re.I)]
 row={**s,'encyclopedia_title':p.get('title'),'encyclopedia_url':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(p['title'].replace(' ','_')) if p else None,'history':excerpt[:1800] if excerpt else s['short_history'],'history_source':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(p['title'].replace(' ','_')) if excerpt else s['sources'].get('stats_history'),'image_candidates':images,'dataset_image':m.get('image_url') if m else None}
 if not excerpt:miss.append((s['name'],title))
 result.append(row)
Path('/tmp/unimatch-enriched-identities.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('histories',sum(bool(x.get('encyclopedia_title')) for x in result),'images',sum(bool(x['image_candidates']) for x in result),'missing',json.dumps(miss,ensure_ascii=False),flush=True)
