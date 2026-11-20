import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const tests=read('../backend/tests/test_assistant_acceptance_http_v1595.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(api.includes('.with_for_update()'),'Review parent-row lock must be present');
for(const x of ['TestClient(app)','sqlite:///:memory:',
 'test_two_admin_authenticated_http_review_and_no_formal_signoff',
 'test_revision_and_duplicate_review_is_preserved_across_http',
 'test_invalid_review_action_and_unknown_id_leave_audit_unchanged',
 'app.dependency_overrides[get_db]']){
 assert.ok(tests.includes(x),x);
}
const v=readBackendVersion(main);
assert.ok(Number(v.replace('.',''))>=1595);
assert.ok(hasDynamicBuildVersion(shell,v));
console.log('PASS v159.5 isolated two-administrator HTTP acceptance QA and review lock');
