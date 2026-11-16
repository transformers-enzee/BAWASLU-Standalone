import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const router=read('../backend/app/assistant_eval_sampling.py');
const register=read('../backend/app/assistant_acceptance_evidence.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const item of ['@router.get("/acceptance-evidence.csv")',
 'readiness=acceptance_readiness(','private, no-store',
 'PENDING_HUMAN_REVIEW'])assert.ok(router.includes(item),item);
for(const item of ['synthetic_checks_are_human_approval',
 'recorded_approvals','FORMAL_CLIENT_ACCEPTANCE',
 'csv.DictWriter','lstrip().startswith'])assert.ok(register.includes(item),item);
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1588);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v158.8 acceptance evidence CSV and no-approval contract');
