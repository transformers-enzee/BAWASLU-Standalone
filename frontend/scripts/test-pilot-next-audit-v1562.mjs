import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const audit=read('../backend/app/officer_pilot_audit.py');
const endpoint=read('../backend/app/casework.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for (const marker of ['next_unobserved_stage','HISTORY_INCOMPLETE_REVIEW_FULL_AUDIT',
'ALL_FIVE_STAGES_OBSERVED_AWAIT_HUMAN_ACCEPTANCE']) assert.ok(audit.includes(marker),marker);
for (const marker of ['acceptance_next_audit_stage','acceptance_preview_incomplete_audit_count',
'acceptance_preview_next_missing_stage_count']) assert.ok(endpoint.includes(marker),marker);
for (const marker of ['pilot-next-audit-stage','pilot-audit-history-incomplete',
'pilot-audit-all-observed','older evidence may exist']) assert.ok(ui.includes(marker),marker);
const back=readBackendVersion(main);
const front=readShellVersion(shell);
assert.ok(back&&front&&back===front);
console.log('PASS v156.2 next audit stage, incomplete history, and signoff safeguards');
