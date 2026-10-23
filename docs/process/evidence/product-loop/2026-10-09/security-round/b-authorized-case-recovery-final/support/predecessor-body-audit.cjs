const fs=require('fs'),path=require('path'),ts=require('../runtime/on/frontend/node_modules/typescript');
const root=path.resolve(__dirname,'..');const prior=path.join(root,'../b-authorized-case-recovery/proposed/frontend/src/lib/store.test.tsx');const final=path.join(root,'proposed/frontend/src/lib/store.test.tsx');
const parse=p=>ts.createSourceFile(p,fs.readFileSync(p,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const a=parse(prior),b=parse(final),rows=x=>x.statements.filter(n=>!ts.isImportDeclaration(n)).map(n=>n.getText(x));
const old=rows(a),now=rows(b);if(old.some((s,i)=>s!==now[i]))throw Error('PRIOR_TEST_STATEMENT_CHANGED');
fs.writeFileSync(path.join(root,'predecessor-body-audit.json'),JSON.stringify({prior_non_import_statements:old.length,all_prior_statements_exact:true,appended_statements:now.length-old.length},null,2)+'\n');
