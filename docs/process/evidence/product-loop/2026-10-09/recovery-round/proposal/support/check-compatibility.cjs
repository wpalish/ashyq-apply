const fs = require('node:fs');
const path = require('node:path');
const ts = require('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/node_modules/typescript');
const root = path.dirname(__dirname);
function parse(kind, rel) { const p = path.join(root, kind, 'frontend/src', rel); return ts.createSourceFile(p, fs.readFileSync(p, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX); }
function testBodies(sf) { const out = new Map(); function visit(n) { if (ts.isCallExpression(n) && n.arguments.length >= 2 && ts.isStringLiteral(n.arguments[0]) && n.expression.getText(sf).startsWith('it') && (ts.isArrowFunction(n.arguments[1]) || ts.isFunctionExpression(n.arguments[1]))) out.set(n.arguments[0].text, n.arguments[1].getText(sf)); ts.forEachChild(n, visit); } visit(sf); return out; }
function named(sf, name, variable=true) { let out; function visit(n) { if ((variable ? ts.isVariableDeclaration(n) : ts.isFunctionDeclaration(n)) && n.name?.getText(sf) === name) out = variable ? n.initializer.getText(sf) : n.getText(sf); ts.forEachChild(n, visit); } visit(sf); return out; }
const report = { old_test_bodies: {}, unchanged_native_expressions: {}, retained_detail_functions: {} };
for (const rel of ['screens/ShortlistScreen.test.tsx','components/ResultDetail.scope.test.tsx']) { const old = testBodies(parse('original', rel)); const next = testBodies(parse('proposed', rel)); const mismatches = [...old].filter(([key, body]) => next.get(key) !== body).map(([key]) => key); report.old_test_bodies[rel] = { original_templates:old.size, proposed_templates:next.size, unchanged:old.size-mismatches.length, mismatches }; if(mismatches.length) throw new Error(JSON.stringify(report)); }
const old = parse('original','screens/ShortlistScreen.tsx'); const next = parse('proposed','screens/ShortlistScreen.tsx');
for(const name of ['rows','clearFilters','activeFilters','decideRow','renderTable']) { const equal = named(old,name)===named(next,name); report.unchanged_native_expressions[name]=equal; if(!equal)throw new Error(name); }
const detailOld = parse('original','components/ResultDetail.tsx'); const detailNext = parse('proposed','components/ResultDetail.tsx');
for(const name of ['ResultDetail','Requirements','Funding','Costs','Sources','Score']) { const equal = named(detailOld,name,false)===named(detailNext,name,false); report.retained_detail_functions[name]=equal; if(!equal || !named(detailOld,name,false))throw new Error(name); }
const documentsOld=named(detailOld,'Documents',false);const documentsNext=named(detailNext,'Documents',false);
report.retained_checklist_return = documentsOld.slice(documentsOld.indexOf('  return (', documentsOld.indexOf('    );')) )===documentsNext.slice(documentsNext.indexOf('  return (', documentsNext.indexOf('    );')) );
if(!report.retained_checklist_return)throw new Error('checklist changed');
fs.writeFileSync(path.join(root,'compatibility.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
