import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/casework.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['from .officer_pilot_readiness import _STAGES',
 'acceptance_workflow_checklist','acceptance_checklist_is_unsigned',
 'acceptance_workflow_stages_not_observed_here','acceptance_legal_approval_not_granted'])
 assert.ok(backend.includes(key),key);
for(const key of ['PILOT_ACCEPTANCE_STAGES','pilot-acceptance-checklist',
 'Unsigned preparation only. Completion and approval',
 'Requires verified casework evidence']) assert.ok(ui.includes(key),key);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(back&&front&&back===front);
console.log('PASS v155.9 unsigned five-stage officer acceptance worksheet');
