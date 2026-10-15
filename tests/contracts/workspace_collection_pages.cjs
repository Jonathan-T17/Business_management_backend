const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const frontend=path.resolve(__dirname,'../../../business_management_frontend');
const local=createRequire(path.join(frontend,'package.json'));
const ts=local('typescript');
const calls=[];
let response={count:26,next:'https://untrusted.example/next',previous:null,results:[{id:'visible'}]};
const apiClient={async get(endpoint,options){calls.push({endpoint,params:options.params});return {data:response};}};
function load(file){
 const compiled=ts.transpileModule(fs.readFileSync(path.join(frontend,'src',file),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 const output={};
 new Function('exports','require',compiled)(output,name=>name==='./client'?{apiClient}:name==='@/utils/api'?load('utils/api.ts'):local(name));
 return output;
}
(async()=>{
 for(const [file,name,endpoint] of [['requestsApi','requestsApi','business-requests/'],['fieldOperationsApi','fieldOperationsApi','field-activities/']]){
  const api=load(`api/${file}.ts`)[name];
  response={count:26,next:'https://untrusted.example/next',previous:null,results:[{id:'visible'}]};
  assert.equal((await api.page(2,{search:'supplies',page:99})).count,26);
  assert.deepEqual(calls.at(-1),{endpoint,params:{search:'supplies',page:2}});
  assert.equal(calls.filter(call=>call.endpoint.startsWith('https:')).length,0);
  response=[{id:'legacy'}];
  assert.deepEqual(await api.page(),{count:1,next:null,previous:null,results:response});
 }
 console.log('Workspace page contracts passed: fixed endpoints, filters, explicit page, totals and array compatibility.');
})().catch(error=>{console.error(error);process.exitCode=1;});
