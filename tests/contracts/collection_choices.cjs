const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const frontend = path.resolve(__dirname, '../../../business_management_frontend');
const ts = require(path.join(frontend, 'node_modules/typescript'));

function moduleFrom(relative, imports) {
  const source = fs.readFileSync(path.join(frontend, 'src', relative), 'utf8');
  const code = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText;
  const exports = {};
  vm.runInNewContext(code, {exports, require: name => {
    assert.ok(name in imports, `Unexpected dependency: ${name}`);
    return imports[name];
  }}, {filename: relative});
  return exports;
}

(async () => {
  const calls = [];
  const get = async (endpoint, config) => {
    const page = config?.params?.page ?? 1;
    calls.push({endpoint, page});
    return {data: {count: 26, previous: page === 1 ? null : 'previous', next: page === 1 ? 'https://untrusted.example/next' : null,
      results: Array.from({length: page === 1 ? 25 : 1}, (_, index) => ({id: (page - 1) * 25 + index + 1}))}};
  };
  const utilities = moduleFrom('utils/api.ts', {});
  const structure = moduleFrom('api/companyStructureApi.ts', {'./client': {apiClient: {get}}, './companySetupApi': {companySetupApi: {}}});
  const dependencies = {'./client': {apiClient: {get}}, './companyStructureApi': structure, '@/utils/api': utilities};
  const organizations = moduleFrom('api/organizationApi.ts', dependencies);
  const branches = moduleFrom('api/branchApi.ts', dependencies);
  for (const [read, endpoint] of [[branches.getBranches, 'branches/'], [organizations.getDepartments, 'departments/'], [organizations.getTeams, 'teams/'], [organizations.getPositions, 'organizations/positions/'], [organizations.getEmployees, 'employees/']]) {
    calls.length = 0;
    const result = await read();
    assert.equal(result.length, 26);
    assert.equal(result[25].id, 26);
    assert.deepEqual(calls, [{endpoint, page: 1}, {endpoint, page: 2}]);
  }
  await assert.rejects(() => structure.readStructurePages(async () => ({results: [{id: 1}], next: 'next'})), /complete company structure/);
  const originalPage = {count: 26, next: 'next', previous: null, results: [{id: 'uuid-record'}]};
  assert.equal(utilities.asPaginatedResponse(originalPage), originalPage);
  assert.equal(utilities.asPaginatedResponse([{id: 'legacy-record'}]).count, 1);
  console.log('Collection contracts passed: complete choices, fixed endpoints, loop protection and preserved pagination.');
})().catch(error => {console.error(error); process.exitCode = 1;});
