import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const report=read('../backend/app/management_reporting.py');
const template=read('../backend/app/management_report_templates.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
for(const value of ['def _casework_activity_window','older_cases_with_observed_activity',
 'approved_events_on_older_cases','case_creation_kpis_remain_separate',
 'def briefing_activity_csv','AUTHORIZED_CASEWORK_PERIOD_AUDIT'])assert.ok(report.includes(value),value);
for(const value of ['Cases with audit activity in period','Approval audit events on older cases'])assert.ok(template.includes(value),value);
for(const value of ['briefing-period-audit-activity','exportActivityCsv','Activity CSV'])assert.ok(ui.includes(value),value);
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const back=readBackendVersion(main),front=readShellVersion(shell);
assert.equal(back,front);assert.ok(Number(back.replace('.',''))>=1574);
console.log('PASS v157.4 cross-period casework audit activity transparency');
