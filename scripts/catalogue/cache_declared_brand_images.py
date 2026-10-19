"""Cache six brand images explicitly declared in already-read institutional pages."""
import json,urllib.request,io,hashlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
assets={
'qs2027-084':('https://www.uba.ar/','https://www.uba.ar/imgs/logofooter.png'),
'qs2027-146':('https://www.tongji.edu.cn/','https://www.tongji.edu.cn/images/smalllogo.png'),
'qs2027-304':('https://en.xmu.edu.cn/','https://en.xmu.edu.cn/img/logo.png'),
'qs2027-335':('https://iitr.ac.in/','https://cmsredesign.channeli.in/library/assets/images/iitrLogo.png'),
'qs2027-349':('https://ev.buaa.edu.cn/','https://ev.buaa.edu.cn/image/logo364.png'),
'qs2027-445':('https://en.shu.edu.cn/','https://en.shu.edu.cn/logo.png')}
rows={r['id']:r for r in json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())};receipt=[]
for id,(page,url) in assets.items():
 item={'id':id,'domain':rows[id]['domain'],'page':page,'content_location':url,'canonical_website':page,'kind':'institution_logo','status':'failed'}
 try:
  with urllib.request.urlopen(url,timeout=20) as f:blob=f.read(1500000)
  image=Image.open(io.BytesIO(blob));assert image.width>8 and image.height>8;dest=ROOT/'frontend/public/universities'/('brand-'+id+'.png');image.convert('RGBA').save(dest,'PNG');item.update(status='cached',path='/universities/'+dest.name,width=image.width,height=image.height,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
 except Exception as e:item['error']=str(e)
 receipt.append(item);print(id,item['status'],item.get('error',''),flush=True)
(ROOT/'frontend/src/data/universityDeclaredBrands.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
