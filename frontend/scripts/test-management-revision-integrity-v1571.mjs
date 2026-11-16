import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/management_reporting.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
for(const key of ['def _report_version_integrity','superseded_returned_versions',
 'latest_approved_after_return','latest_draft_after_return',
 'latest_returned_awaiting_revision','historical_versions_are_not_approvals',
 '"report_version_integrity":report_version_integrity'])assert.ok(api.includes(key),key);
for(const key of ['briefing-report-version-integrity','Report revision history',
 'Historical returned reports','Latest approved after a return',
 'Returned awaiting revision'])assert.ok(ui.includes(key),key);
const b=main.split("'build_version':'")[1]?.split("'")[0];
const f=shell.split('data-build-version="')[1]?.split('"')[0];
assert.equal(b,f);assert.ok(Number(b.replace('.',''))>=1571);
console.log('PASS v157.1 report-revision history and latest-version KPI transparency');
