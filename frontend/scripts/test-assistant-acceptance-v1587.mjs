import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_eval_sampling.py');
const ready=read('../backend/app/assistant_acceptance_readiness.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(api.includes('@router.get("/acceptance-readiness")'));
assert.ok(api.includes('not has(principal,"administration")'));
for(const term of ['PREPARATION_ONLY_NOT_FORMAL_ACCEPTANCE',
 'LEGAL_REFERENCE_SIGNOFF','NEGATIVE_CONTROL_REVIEW','FORMAL_CLIENT_ACCEPTANCE',
 'human_accuracy_measured','legal_reference_signoff_complete']){
  assert.ok(ready.includes(term),term);
}
const bv=main.split("'build_version':'")[1]?.split("'")[0];
assert.equal(bv,shell.split('data-build-version="')[1]?.split('"')[0]);
assert.equal(bv,'158.7');
console.log('PASS v158.7 legal and Assistant acceptance readiness safeguards');
