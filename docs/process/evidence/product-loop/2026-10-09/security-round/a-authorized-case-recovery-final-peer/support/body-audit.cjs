const fs=require('fs'),crypto=require('crypto');const ts=require("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/a-authorized-case-recovery-final-peer/runtime/frontend/node_modules/typescript");
const parse=p=>ts.createSourceFile('review.tsx',fs.readFileSync(p,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const statements=s=>s.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(s));
const sourceA=parse("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/b-authorized-case-recovery/original/frontend/src/lib/store.test.tsx");
const sourceCB=parse("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/b-authorized-case-recovery/proposed/frontend/src/lib/store.test.tsx");
const sourceFinal=parse("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/b-authorized-case-recovery-final/proposed/frontend/src/lib/store.test.tsx");
const aa=statements(sourceA),cc=statements(sourceCB),ff=statements(sourceFinal);
if(aa.some((s,i)=>s!==ff[i]))throw Error('OLD_BODY_CHANGED');if(cc.some((s,i)=>s!==ff[i]))throw Error('CB_BODY_CHANGED');
function firstTest(p){const s=parse(p);let text=null;function visit(n){if(text===null&&ts.isCallExpression(n)&&n.expression.getText(s)==='it'&&ts.isStringLiteral(n.arguments[0]))text=n.getText(s);ts.forEachChild(n,visit);}visit(s);return text;}
const firstA=firstTest("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/a-authorized-case-recovery-peer/recovery.peer.original.test.tsx"),firstFinal=firstTest("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1/a-authorized-case-recovery-final-peer/recovery.peer.test.tsx");if(firstA!==firstFinal)throw Error('LOADING_CASE_CHANGED');
console.log(JSON.stringify({old_statements:aa.length,cb_statements:cc.length,final_statements:ff.length,old_exact:true,cb_exact:true,original_loading_case_exact:true,loading_case_sha256:crypto.createHash('sha256').update(firstFinal).digest('hex')}));
