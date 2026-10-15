const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createRequire} = require('node:module');
const frontend = path.resolve(__dirname,'../../../business_management_frontend');
const frontendRequire = createRequire(path.join(frontend,'package.json'));
const ts = frontendRequire('typescript');
const cache = new Map();
function load(relative) {
  if(cache.has(relative))return cache.get(relative);
  const output = ts.transpileModule(fs.readFileSync(path.join(frontend,'src',relative),'utf8'),
    {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
  const module={exports:{}};
  vm.runInNewContext(output,{module,exports:module.exports,require:name=>name==='@/utils/apiError'?load('utils/apiError.ts'):frontendRequire(name)});
  cache.set(relative,module.exports);return module.exports;
}
const normalize=load('utils/apiError.ts').normalizeApiError;
const parse=load('api/errors.ts').parseApiError;
const error=(status,data,headers={})=>({isAxiosError:true,response:{status,data,headers}});
const suspended='Your company workspace is suspended. Contact your company administrator or platform support.';
assert.equal(normalize(error(403,{error:{code:'ACCOUNT_ACCESS_UNAVAILABLE',message:suspended}})).message,suspended);
assert.equal(normalize(error(400,{error:{message:'One or more fields are invalid.',fields:{non_field_errors:['This published form cannot be changed. Create a revision instead.']}}})).message,'This published form cannot be changed. Create a revision instead.');
const field=normalize(error(400,{error:{message:'One or more fields are invalid.',fields:{reason:['A reason is required.']}}}));
assert.equal(field.message,'Reason: A reason is required.');assert.equal(field.fields.reason,'A reason is required.');
assert.equal(normalize(error(400,{error:['Choose a longer password.','Avoid a common password.']})).message,'Choose a longer password. Avoid a common password.');
assert.equal(normalize(error(400,{error:{message:'One or more fields are invalid.',fields:['This request has already been approved.']}})).message,'This request has already been approved.');
assert.equal(normalize(error(400,{error:'This password-reset link has expired or is invalid. Request a new reset link.'})).message,'This password-reset link has expired or is invalid. Request a new reset link.');
assert.equal(normalize(error(500,'<html>private traceback</html>')).message,'The service is temporarily unavailable. Please try again shortly.');
assert.equal(normalize(error(500,{detail:'private server diagnostic'})).message,'The service is temporarily unavailable. Please try again shortly.');
assert.equal(normalize(error(503,{error:{code:'VERIFICATION_EMAIL_UNAVAILABLE',message:"We couldn't send your verification email. Please try signing in again shortly."}})).message,"We couldn't send your verification email. Please try signing in again shortly.");
assert.match(normalize({isAxiosError:true}).message,/Check your connection/);
assert.equal(normalize(error(429,{detail:'Request was throttled.'},{'retry-after':'90'})).message,'Too many attempts. Please try again in 2 minutes.');
assert.match(normalize(error(404,{detail:'Not found.'})).message,/may not have access/);
assert.match(normalize(error(403,{detail:'You do not have permission to perform this action.'})).message,/Contact an administrator/);
assert.equal(parse(error(400,{error:{code:'VALIDATION_ERROR',message:'One or more fields are invalid.',fields:{reason:['Enter a reason.']},request_id:'synthetic'}})).message,'Reason: Enter a reason.');
assert.equal(parse(error(400,{error:{message:'One or more fields are invalid.',fields:{reason:['Enter a reason.']}}})).fields.reason[0],'Enter a reason.');
console.log('15 action-message contracts passed.');
