"""Verify the finite offline institution directory and its chosen image receipts."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def verify():
 rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())
 assert len(rows)==500 and len({row['id'] for row in rows})==500
 receipts={}
 for path in (ROOT/'frontend/src/data').glob('university*receipt.json'):
  for row in json.loads(path.read_text()):
   if row.get('status')=='cached':receipts[row['path']]=row
 assets=[];hashes=set()
 for row in rows:
  assert row['history'] and row['historySource'].startswith('https://')
  assert row['website'].startswith(('https://','http://'))
  assert row['image'].startswith('/universities/') and '..' not in row['image']
  path=ROOT/'frontend/public'/row['image'].lstrip('/');data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
  assert sha==receipts[row['image']]['sha256'],row['id']
  assert sha not in hashes,('duplicate identity image',row['id']);hashes.add(sha)
  if data.startswith(b'\x89PNG\r\n\x1a\n'):
   width,height=struct.unpack('>II',data[16:24]);assert width>0 and height>0
  else:
   assert path.suffix=='.svg' and b'<svg' in data; width=height=None
  assets.append(dict(id=row['id'],image=row['image'],kind=row['imageKind'],bytes=len(data),sha256=sha,width=width,height=height,source=row['imageSource']))
 return dict(institutions=len(rows),histories=500,websites=500,local_images=len(assets),duplicate_hashes=0,receipt_hashes_match=True,assets=assets)
if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
