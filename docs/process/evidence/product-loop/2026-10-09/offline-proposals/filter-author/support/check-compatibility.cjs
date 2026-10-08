const fs = require('node:fs');
const path = require('node:path');
const ts = require('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/node_modules/typescript');
const root = path.dirname(__dirname);
function parse(kind, name) { const p = path.join(root, kind, 'frontend/src/screens', name); const text = fs.readFileSync(p, 'utf8'); return ts.createSourceFile(p, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX); }
function testBodies(sf) { const out = new Map(); function visit(n) { if (ts.isCallExpression(n) && n.arguments.length >= 2 && ts.isStringLiteral(n.arguments[0]) && n.expression.getText(sf).startsWith('it') && (ts.isArrowFunction(n.arguments[1]) || ts.isFunctionExpression(n.arguments[1]))) out.set(n.arguments[0].text, n.arguments[1].getText(sf)); ts.forEachChild(n, visit); } visit(sf); return out; }
function namedVar(sf, name) { let out; function visit(n) { if (ts.isVariableDeclaration(n) && n.name.getText(sf) === name) out = n.initializer.getText(sf); ts.forEachChild(n, visit); } visit(sf); return out; }
const report = { old_test_bodies: {}, unchanged_native_expressions: {}, new_app_paths: ['ShortlistScreen.tsx', 'ApprovedScreen.tsx'] };
for (const name of ['ShortlistScreen.test.tsx', 'JourneyScreens.test.tsx']) { const old = testBodies(parse('original', name)); const next = testBodies(parse('proposed', name)); const mismatches = [...old].filter(([key, body]) => next.get(key) !== body).map(([key]) => key); report.old_test_bodies[name] = { original_templates: old.size, proposed_templates: next.size, unchanged: old.size - mismatches.length, mismatches }; if (mismatches.length) throw new Error(JSON.stringify(report)); }
const old = parse('original', 'ShortlistScreen.tsx'); const next = parse('proposed', 'ShortlistScreen.tsx');
for (const name of ['rows', 'decideRow', 'renderTable']) { const equal = namedVar(old, name) === namedVar(next, name); report.unchanged_native_expressions[name] = equal; if (!equal) throw new Error(name); }
fs.writeFileSync(path.join(root, 'compatibility.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
