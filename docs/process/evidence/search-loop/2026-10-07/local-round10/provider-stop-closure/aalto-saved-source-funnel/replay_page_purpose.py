"""Read saved public bytes only. Normal frozen app imports; no Fetcher."""
import json
from dataclasses import asdict
from pathlib import Path
from app.adapters.page_classifier import classify_page,main_content
from app.adapters.html_parse import parse_html
from app.adapters.extraction import readable_text
from app.adapters.discovery.live_discovery import profile_rejects

base=Path(__file__).resolve().parent
rows=[]
for meta in sorted((base/'public-cache').glob('*.meta.json')):
 m=json.loads(meta.read_text())
 if 'text/html' not in m['content_type']:continue
 html=meta.with_name(meta.name.replace('.meta.json','.body')).read_text()
 page=classify_page(url=m['final_url'],html=html)
 main=main_content(parse_html(html))
 text=readable_text(html)
 row={'url':m['url'],'final_url':m['final_url'],'meta':meta.name,'body':meta.name.replace('.meta.json','.body'),'classification':asdict(page),'requested_level':'bachelor','requested_fields':['Computer Science'],'profile_rejects':profile_rejects(page,'bachelor',['Computer Science']),'main_h1':[h.get_text(' ',strip=True) for h in main.find_all('h1')],'main_headings':[h.get_text(' ',strip=True) for h in main.find_all(['h1','h2','h3'])],'readable_chars':len(text)}
 rows.append(row)
 (base/'readable').mkdir(exist_ok=True)
 (base/'readable'/row['body'].replace('.body','.txt')).write_text(text)
(base/'page-purpose.offline.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:
 p=r['classification']; print(r['url'], '|',p['title'],'|',p['page_type'],'|',p['subject'],'|',p['degree_level'],'|',r['profile_rejects'])
