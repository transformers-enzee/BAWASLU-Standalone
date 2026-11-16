import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const template=read('../backend/app/management_report_templates.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
for(const key of ['approval_activity_cases_latest_approved',
 'approval_activity_cases_latest_not_approved',
 'approval_activity_cases_without_saved_report',
 'approval_activity_latest_status_reconciled',
 'func.row_number().over','CaseReport.case_id.in_(ids)'])
 assert.ok(api.includes(key),key);
for(const key of ['Approval-activity cases still approved',
 'Approval-activity cases no longer approved'])
 assert.ok(template.includes(key),key);
for(const key of ['Approval activity without a saved report',
 'Reconciled with the latest saved report per case'])
 assert.ok(ui.includes(key),key);
const bv=main.split("'build_version':'")[1]?.split("'")[0];
const fv=shell.split('data-build-version="')[1]?.split('"')[0];
assert.equal(bv,fv);assert.ok(Number(bv.replace('.',''))>=1576);
console.log('PASS v157.6 approval-event to latest-report reconciliation');
