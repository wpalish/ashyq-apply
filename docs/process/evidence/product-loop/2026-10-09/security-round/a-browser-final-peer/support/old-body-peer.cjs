const fs = require('node:fs');
const path = require('node:path');
const ts = require('../runtime/frontend/node_modules/typescript');
const crypto = require('node:crypto');
const original = '/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/browser-proposal-final/original';
const runtime = path.resolve(__dirname, '../runtime');
const parse = (file) => ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const rows = {};
for (const rel of ['frontend/src/AuthGate.test.tsx', 'frontend/src/lib/store.test.tsx']) {
 const a = parse(path.join(original, rel));
 const b = parse(path.join(runtime, rel));
 const statements = (tree) => tree.statements.filter(n => !ts.isImportDeclaration(n)).map(n => n.getText(tree));
 const x = statements(a), y = statements(b);
 if (x.some((s,i) => s !== y[i])) throw new Error('ORIGINAL_STATEMENT_CHANGED:' + rel);
 rows[rel] = { exact_original_non_import_statements: x.length, all_exact: true,
   original_text_sha256: crypto.createHash('sha256').update(x.join('\n')).digest('hex') };
}
const title = 'does not let post-login status A erase or supersede the newer acknowledged owner B';
const findTest = (tree) => {
 let result = null;
 const visit = (n) => {
  if (ts.isCallExpression(n) && n.expression.getText(tree) === 'it'
    && n.arguments[0]?.text === title) result = n.arguments[1].getText(tree);
  ts.forEachChild(n, visit);
 };
 visit(tree); return result;
};
const red = parse('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/a-browser-peer/independent-auth-race.test.tsx');
const final = parse(path.join(runtime, 'frontend/src/AuthGate.test.tsx'));
if (!findTest(red) || findTest(red) !== findTest(final)) throw new Error('INDEPENDENT_EXPECTATION_CHANGED');
rows.independent_post_login = { exact_original_red_test_callback: true,
  callback_sha256: crypto.createHash('sha256').update(findTest(red)).digest('hex') };
console.log(JSON.stringify(rows, null, 2));
