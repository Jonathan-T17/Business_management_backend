const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const root = path.resolve(process.argv[2]);
const ts = createRequire(path.join(path.resolve(process.argv[3] || root),'package.json'))('typescript');
const result = {calls:[], skipped:[], capabilities:[]};
function variants(node) {
 if (ts.isStringLiteralLike(node)) return [node.text];
 if (ts.isConditionalExpression(node)) {
  const a=variants(node.whenTrue), b=variants(node.whenFalse);
  return a && b ? [...a,...b] : null;
 }
 if (ts.isTemplateExpression(node)) {
  let strings=[node.head.text];
  for(const span of node.templateSpans) {
   const values=variants(span.expression) ?? ['1','00000000-0000-0000-0000-000000000001'];
   strings=strings.flatMap(s=>values.map(v=>s+v+span.literal.text));
   if(strings.length>128) return null;
  }
  return strings;
 }
 return null;
}
for (const file of fs.readdirSync(path.join(root,'src/api')).filter(f=>f.endsWith('.ts'))) {
 const name=path.join(root,'src/api',file);
 const source=ts.createSourceFile(name,fs.readFileSync(name,'utf8'),ts.ScriptTarget.Latest,true);
 const aliases=new Map();
 for(const node of source.statements) {
  if(!ts.isImportDeclaration(node) || !/\/?client$/.test(node.moduleSpecifier.text)) continue;
  const bindings=node.importClause?.namedBindings;
  if(bindings && ts.isNamedImports(bindings)) for(const item of bindings.elements) {
   const imported=(item.propertyName??item.name).text;
   if(['apiClient','platformClient'].includes(imported)) aliases.set(item.name.text,imported==='platformClient'?'/api/platform/v1/':'/api/v1/');
  }
 }
 function visit(node) {
  if(ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
   const member=node.expression;
   const prefix=aliases.get(member.expression.getText(source));
   if(prefix && ['get','post','put','patch','delete','head','options'].includes(member.name.text)) {
    const arg=node.arguments[0];
    const entry={file,line:source.getLineAndCharacterOfPosition(node.getStart()).line+1,method:member.name.text,path:arg?.getText(source)??''};
    const paths=arg ? variants(arg) : null;
    if(paths) result.calls.push({...entry,paths:[...new Set(paths.map(p=>prefix+p.replace(/^\//,'')))]});
    else result.skipped.push(entry);
   }
  }
  ts.forEachChild(node,visit);
 }
 visit(source);
}
const capFile=path.join(root,'src/utils/capabilities.ts');
const source=ts.createSourceFile(capFile,fs.readFileSync(capFile,'utf8'),ts.ScriptTarget.Latest,true);
function visitCaps(node) {
 if(ts.isVariableDeclaration(node) && node.name.getText(source)==='CAPABILITIES') {
  let value=node.initializer;
  while(value && (ts.isAsExpression(value)||ts.isSatisfiesExpression(value)))value=value.expression;
  if(value && ts.isObjectLiteralExpression(value)) for(const field of value.properties) {
   if(ts.isPropertyAssignment(field) && ts.isStringLiteralLike(field.initializer)) result.capabilities.push(field.initializer.text);
  }
 }
 ts.forEachChild(node,visitCaps);
}
visitCaps(source);
console.log(JSON.stringify(result));
