"""Read saved public pages offline for editorial qualification; no new fetch."""
import json,re,sys
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(sys.argv[1]);ids=set(sys.argv[2:]);rows=[json.loads(l) for l in (ROOT/'institutions.jsonl').read_text().splitlines()]
for row in rows:
 if row['institution_id'] not in ids:continue
 for p in row['programmes']:
  print('\nPAGE',p['institution_id'],p['level'],p['url'],p['content_sha256'])
  soup=BeautifulSoup((ROOT/'pages'/(p['content_sha256']+'.bin')).read_bytes(),'html.parser')
  main=soup.find('main') or soup.find('article') or soup
  for x in main.select('script,style,nav,footer,header,aside'):x.decompose()
  text='\n'.join(x.strip() for x in main.get_text('\n',strip=True).splitlines() if x.strip())
  lines=text.splitlines();print('INTRO',' '.join(lines[:35])[:1300]);indices=set()
  for i,line in enumerate(lines):
   if re.search(r'fee|scholarship|deadline|entry requirements|admission requirements|IELTS|TOEFL|2027|tuition|english|duration|adgangskrav|stipend|application|£|€|EUR|USD',line,re.I):indices.update(range(max(0,i-1),min(len(lines),i+4)))
  print('DETAILS','\n'.join(f'{i}:{lines[i]}' for i in sorted(indices))[:10000])
