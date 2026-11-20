import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const report=read('../backend/app/management_reporting.py');
const template=read('../backend/app/management_report_templates.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const backend=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['distinct_cases_with_approval','distinct_cases_with_return',
'distinct_cases_with_revision','distinct_older_cases_with_approval',
'Distinct approved case indicator','distinct_counts_do_not_prove_latest_report_status'])
 assert.ok(report.includes(key),key);
for(const key of ['Distinct cases with approval activity','Distinct cases with return activity'])
 assert.ok(template.includes(key),key);
for(const key of ['Distinct cases with returned reports',
'Distinct cases with revisions','Distinct cases with approval activity'])
 assert.ok(ui.includes(key),key);
const bv=readBackendVersion(backend);
const fv=readShellVersion(shell);
assert.equal(bv,fv);assert.ok(Number(bv.replace('.',''))>=1575);
console.log('PASS v157.5 distinct case activity versus audit events');
