// Actual frontend helpers, simulated transport: no live requests, entries or uploads.
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const assert=require('node:assert/strict');
const frontend=path.resolve(__dirname,'../../../business_management_frontend');
const scopedRequire=createRequire(path.join(frontend,'package.json'));
const ts=scopedRequire('typescript');
function load(relative) {
  const source=fs.readFileSync(path.join(frontend,relative),'utf8');
  const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const exported={};new Function('exports','require',compiled)(exported,scopedRequire);return exported;
}

(async()=>{
  const {saveFormWithFiles:save}=load('src/utils/saveFormWithFiles.ts');
  const {requiredFormErrors,formErrors}=load('src/utils/formErrors.ts');
  const {normalizeApiError}=load('src/utils/apiError.ts');
  const {isFieldVisible}=load('src/components/forms/DynamicForm.tsx');
  const fields=[{key:'yes',label:'Yes or no',field_type:'BOOLEAN',required:true},{key:'inactive',label:'Inactive',is_active:false,required:true},{key:'hidden',label:'Hidden',required:true,validation_rules:{show_when:{field:'yes',equals:true}}}];
  assert.deepEqual(requiredFormErrors(fields,{yes:false},isFieldVisible),{});
  const normalized=normalizeApiError({isAxiosError:true,response:{status:400,data:{error:{message:'Check answers',fields:{data:{items:[{quantity:['Enter a positive quantity.']}]}}}}}});
  assert.deepEqual(formErrors(normalized.fields),{'items.0.quantity':'Enter a positive quantity.'});

  let savedId=null,creates=0,updates=0,submits=0,failUpload=true;
  let pending=[{name:'first.txt'},{name:'second.txt'}];const uploaded=[];
  const transport={async createDraft(template,values,key,branch){assert.equal(key,'request-1');assert.equal(branch,42);creates++;return {id:'entry-1',status:'DRAFT'};},async update(id){updates++;return {id,status:'DRAFT'};},async submission(id){return {id,status:'DRAFT'};},async uploadAttachment(id,file){if(file.name==='second.txt'&&failUpload){failUpload=false;throw new Error('Interrupted upload');}uploaded.push(file.name);},async submit(id){submits++;return {id,status:'SUBMITTED'};}};
  const run=()=>save({transport,templateId:'template-1',clientRequestId:'request-1',branch:42,savedId,values:{note:'Test'},files:pending,submit:true,onDraftSaved:id=>savedId=id,onFileUploaded:file=>pending=pending.filter(item=>item!==file)});
  await assert.rejects(run());assert.equal(savedId,'entry-1');assert.equal(submits,0);await run();
  assert.equal(creates,1);assert.equal(submits,1);assert.deepEqual(uploaded,['first.txt','second.txt']);

  let lostId=null,serverCreates=0,createCalls=0,committed=null;
  const lost={async createDraft(template,values,key){assert.equal(key,'stable-key');createCalls++;if(!committed){serverCreates++;committed={id:'retained-entry',status:'DRAFT'};throw new Error('Create response lost');}return committed;},async update(id){return {id,status:'DRAFT'};},async uploadAttachment(){},async submit(id){return {id,status:'SUBMITTED'};}};
  const lostRun=()=>save({transport:lost,templateId:'template-1',clientRequestId:'stable-key',savedId:lostId,values:{note:'Test'},files:[],submit:false,onDraftSaved:id=>lostId=id,onFileUploaded(){}});
  await assert.rejects(lostRun());await lostRun();assert.equal(createCalls,2);assert.equal(serverCreates,1);assert.equal(lostId,'retained-entry');

  let lostSubmit=true,status='DRAFT',actualSubmits=0,lockedUpdates=0;
  const uncertain={async submission(id){return {id,status};},async createDraft(){throw new Error('Unexpected create');},async update(id){lockedUpdates++;return {id,status};},async uploadAttachment(){},async submit(id){actualSubmits++;status='SUBMITTED';if(lostSubmit){lostSubmit=false;throw new Error('Submit response lost');}return {id,status};}};
  const submitRun=()=>save({transport:uncertain,templateId:'template-1',savedId:'existing-entry',values:{note:'Test'},files:[],submit:true,onDraftSaved(){},onFileUploaded(){}});
  await assert.rejects(submitRun());const recovered=await submitRun();assert.equal(recovered.status,'SUBMITTED');assert.equal(actualSubmits,1);assert.equal(lockedUpdates,1);
  console.log('Frontend regressions passed: required/hidden/inactive questions, nested errors, upload retry, lost create response and lost submit response.');
})().catch(error=>{console.error(error);process.exitCode=1;});
