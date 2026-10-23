"""Static source equivalence using the product's Python 3.12 grammar."""
import ast
import hashlib
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1]


class RemoveImports(ast.NodeTransformer):
    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None


class Aliases(ast.NodeVisitor):
    def __init__(self):
        self.scope = []
        self.items = []

    def visit_ClassDef(self, node):
        self.scope.append("class:" + node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.scope.append("def:" + node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        self.items += [(tuple(self.scope), "", 0, a.name, a.asname) for a in node.names]

    def visit_ImportFrom(self, node):
        self.items += [
            (tuple(self.scope), node.module or "", node.level, a.name, a.asname)
            for a in node.names
        ]


checks = {}
for f in sorted((p / "pre-backend-format").rglob("*.py")):
    rel = f.relative_to(p / "pre-backend-format")
    after = p / "runtime/on" / rel
    left, right = f.read_text(), after.read_text()
    a, b = ast.parse(left), ast.parse(right)
    aa, bb = Aliases(), Aliases()
    aa.visit(a)
    bb.visit(b)
    alias_equal = sorted(aa.items, key=repr) == sorted(bb.items, key=repr)
    ast_equal = ast.dump(RemoveImports().visit(a), include_attributes=False) == ast.dump(
        RemoveImports().visit(b), include_attributes=False
    )
    assert alias_equal and ast_equal, str(rel)
    checks[str(rel)] = {
        "before_sha256": hashlib.sha256(left.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(right.encode()).hexdigest(),
        "scoped_import_aliases_equal": True,
        "non_import_AST_equal": True,
        "source_bytes_changed": left != right,
    }
    (p / "proposed" / rel).write_bytes(after.read_bytes())

(p / "harness/test_rejected_diagnostics.py").write_bytes(
    (p / "proposed/backend/tests/test_rejected_diagnostics.py").read_bytes()
)
(p / "backend-format-equivalence.json").write_text(
    json.dumps({
        "configuration": "Exact normal backend/ruff.toml inside isolated ON/backend, actual app/tests paths; no rules changed",
        "files": checks,
    }, indent=2) + "\n"
)
print("AST/aliases equivalent", len(checks), "formatted bytes changed",
      sum(r["source_bytes_changed"] for r in checks.values()))
