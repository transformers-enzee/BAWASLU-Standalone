import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/casework.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for (const key of ['pilot_next_action_counts_preview_only','pilot_next_action_not_legal_determination',
  'SOURCE_UNAVAILABLE','RECHECK_LATEST_ASSESSMENT','RECOVER_SAVED_EVIDENCE',
  'RECONFIRM_INCIDENT_JURISDICTION','REVIEW_UPDATED_FLAG_ASSESSMENT',
  'CONTINUE_EXISTING_CASE','REVIEW_SOURCE_IN_INBOX']) assert.ok(backend.includes(key),key);
for(const key of ['PILOT_NEXT_ACTIONS','briefing-pilot-next-actions',
  'pilot-source-next-action','Preview only. Officer verification']) assert.ok(ui.includes(key),key);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(back&&front&&back===front);
console.log('PASS v155.8 deterministic pilot officer next actions and release parity');
