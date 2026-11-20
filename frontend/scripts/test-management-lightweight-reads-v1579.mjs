import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const backend=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
const block=api.split('def _scoped_casework_window(')[1].split('def _casework_activity_window(')[0];
assert.ok(block.includes('for offset in range(0,len(ids),400)'));
for(const key of ['CaseReport.id,CaseReport.case_id','CaseReport.status,CaseReport.created_at',
 'CaseTransition.id,CaseTransition.case_id','CaseTransition.action,CaseTransition.details_json'])
 assert.ok(block.includes(key),key);
assert.ok(!block.includes('db.query(CaseReport)'));
assert.ok(!block.includes('db.query(CaseTransition)'));
const b=readBackendVersion(backend),f=readShellVersion(shell);
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1579);
console.log('PASS v157.9 lightweight management report metadata projections');
