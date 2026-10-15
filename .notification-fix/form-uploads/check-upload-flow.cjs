const fs = require('node:fs');
const assert = require('node:assert/strict');
const ts = require('C:/Users/1213/Desktop/Jonathan/business_management_frontend/node_modules/typescript');
const source = fs.readFileSync('C:/Users/1213/Desktop/Jonathan/business_management_frontend/src/utils/saveFormWithFiles.ts', 'utf8');
const compiled = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020}}).outputText;
const moduleResult = {exports: {}};
new Function('exports', 'module', compiled)(moduleResult.exports, moduleResult);
const {saveFormWithFiles} = moduleResult.exports;

async function check() {
  const first = {name: 'receipt.pdf'}; const second = {name: 'photo.jpg'};
  let remaining = [first, second]; let id = null; let fail = true; const calls = [];
  const transport = {
    async createDraft() {calls.push('create'); return {id: 'saved-draft'};},
    async update(saved) {assert.equal(saved, 'saved-draft'); calls.push('update'); return {id: saved};},
    async uploadAttachment(saved, file) {assert.equal(saved, 'saved-draft'); calls.push(file.name); if (file === second && fail) throw new Error('upload unavailable');},
    async submit(saved) {calls.push('submit'); return {id: saved};},
  };
  const options = () => ({transport, templateId: 'template', savedId: id, values: {}, files: remaining, submit: true,
    onDraftSaved: saved => {id = saved;}, onFileUploaded: file => {remaining = remaining.filter(item => item !== file);}});
  await assert.rejects(saveFormWithFiles(options()), /upload unavailable/);
  assert.equal(id, 'saved-draft'); assert.deepEqual(remaining, [second]);
  assert.deepEqual(calls, ['create', 'receipt.pdf', 'photo.jpg']);
  fail = false; await saveFormWithFiles(options());
  assert.deepEqual(calls, ['create', 'receipt.pdf', 'photo.jpg', 'update', 'photo.jpg', 'submit']);
  assert.deepEqual(remaining, []);
  calls.length = 0; await saveFormWithFiles({...options(), submit: false});
  assert.deepEqual(calls, ['update']);
  calls.length = 0;
  await assert.rejects(saveFormWithFiles({...options(), transport: {...transport, async update() {throw new Error('save unavailable');}}}), /save unavailable/);
  assert.deepEqual(calls, []);
  console.log('Passed: upload failure blocks submission, successful files are not repeated, retry reuses the draft, save-only never submits, save failure never uploads.');
}
check().catch(error => {console.error(error); process.exitCode = 1;});
