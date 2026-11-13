import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/casework.py');
const audit=read('../backend/app/officer_pilot_audit.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['observed_casework_stages','acceptance_audit_observed_stage_count',
  'acceptance_case_audit_evidence_available','acceptance_audit_evidence_is_not_human_signoff'])
 assert.ok(backend.includes(key),key);
for(const key of ['_acceptance_trace','row_num<=200','observed_stages','CaseReport.id.desc()'])
 assert.ok(audit.includes(key),key);
for(const key of ['Observed in bounded casework audit (not formal acceptance)',
'Not observed in available casework audit','Audit history truncated'])
 assert.ok(ui.includes(key),key);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(back&&front&&back===front);
console.log('PASS v156.0 bounded authorized casework audit trace on pilot worksheet');
