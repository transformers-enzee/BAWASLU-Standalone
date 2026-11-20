import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const backend=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['approval_activity_reconciliation_totals_match',
'Latest report status at export (approval activity only)',
'Current approval reconciliation','STILL_APPROVED',
'NO_SAVED_REPORT','SUPERSEDED_OR_NOT_APPROVED',
'NOT_APPLICABLE_NO_APPROVAL_EVENT',
'NOT_CHECKED_NO_APPROVAL_EVENT']) assert.ok(api.includes(key),key);
const b=readBackendVersion(backend);
const f=readShellVersion(shell);
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1577);
console.log('PASS v157.7 activity CSV status reconciliation parity');
