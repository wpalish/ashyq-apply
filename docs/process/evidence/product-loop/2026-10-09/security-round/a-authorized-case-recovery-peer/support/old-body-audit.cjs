const fs=require('fs'),crypto=require('crypto');
const ts=require("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/a-authorized-case-recovery-peer/runtime/frontend/node_modules/typescript");
const a=ts.createSourceFile('store.test.tsx',fs.readFileSync("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/b-authorized-case-recovery/original/frontend/src/lib/store.test.tsx",'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const c=ts.createSourceFile('store.test.tsx',fs.readFileSync("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/b-authorized-case-recovery/proposed/frontend/src/lib/store.test.tsx",'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const aa=a.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(a));const cc=c.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(c));
if(aa.some((s,i)=>s!==cc[i]))throw Error('OLD_BODY_CHANGED');
console.log(JSON.stringify({original_non_import_statements:aa.length,appended_statements:cc.length-aa.length,old_exact:true,old_body_sha256:crypto.createHash('sha256').update(aa.join('\n')).digest('hex')}));
