import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const readiness=read('../backend/app/officer_pilot_readiness.py');
const exportCode=read('../backend/app/management_reporting.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const s of ['INSPECT_TRUNCATED_WINDOW_AND_FULL_CASE_HISTORY',
'VERIFY_UNOBSERVED_STAGES_AGAINST_FULL_CASE_HISTORY',
'HUMAN_CONFIRM_FIVE_OBSERVED_STAGES','missing_stage_confirmed_absent'])
 assert.ok(readiness.includes(s),s);
for(const s of ['Recommended reviewer action','SELECTED_UTC_PERIOD_ONLY_NOT_LIFETIME',
'PENDING_AUTHORIZED_HUMAN_REVIEW']) assert.ok(exportCode.includes(s),s);
for(const s of ['pilot-packet-review-actions','pilot-packet-period-caveat',
'Inspect truncated audit and full history']) assert.ok(ui.includes(s),s);
const bv=readBackendVersion(main);
const fv=readShellVersion(shell);
assert.ok(bv&&bv===fv);
console.log('PASS v156.3 management officer pilot packet reviewer triage and period scope');
