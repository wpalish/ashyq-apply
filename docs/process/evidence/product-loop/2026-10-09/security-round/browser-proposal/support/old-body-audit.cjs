const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ts=require('../runtime/on/frontend/node_modules/typescript');
const root=path.resolve(__dirname,'..');
const sha=(s)=>crypto.createHash('sha256').update(s).digest('hex');
const rows={};
for(const rel of ['frontend/src/AuthGate.test.tsx','frontend/src/lib/store.test.tsx']) {
 const parse=(where)=>ts.createSourceFile(rel,fs.readFileSync(path.join(root,where,rel),'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const original=parse('original'),proposed=parse('proposed');
 const a=original.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(original));
 const b=proposed.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(proposed));
 if(a.some((s,i)=>s!==b[i]))throw Error('OLD_MODULE_STATEMENT_CHANGED:'+rel);
 rows[rel]={original_non_import_statements:a.length,all_original_statements_exact:true,old_body_sha256:sha(a.join('\n')),new_statement_count:b.length-a.length};
}
fs.writeFileSync(path.join(root,'old-body-audit.json'),JSON.stringify(rows,null,2)+'\n');
