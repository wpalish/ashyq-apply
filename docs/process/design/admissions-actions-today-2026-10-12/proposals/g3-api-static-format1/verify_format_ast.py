import ast,json
from pathlib import Path
p=Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-static-format1");m=json.loads((p/"MANIFEST.json").read_text());out={}
for name in m["allowlist"]:
 a=ast.parse((p/"format-input"/name).read_text());b=ast.parse((p/"files"/name).read_text())
 def parts(tree):
  imports=sorted(ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)))
  tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
  return imports,ast.dump(tree,include_attributes=False)
 x,y=parts(a),parts(b);assert x==y,name;out[name]={"same_import_nodes":True,"same_other_ast":True}
print(json.dumps({"status":"MECHANICAL_FORMAT_AST_EQUAL_NOT_RUNTIME_PROOF","files":out},indent=2))
