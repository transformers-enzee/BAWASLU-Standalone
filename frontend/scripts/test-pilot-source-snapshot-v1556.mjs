import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/casework.py');
const intake=read('../backend/app/officer_pilot_intake.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['source_availability_changed_since_inbox','assessment_version_changed_since_inbox',
    'preview_source_availability_changed_count','preview_assessment_version_changed_count',
    'source_recovery_reason','_original_url_available(post.canonical_url)']) assert.ok(backend.includes(key),key);
assert.ok(intake.includes('inbox_snapshot_assessment_version'));
for(const key of ['Saved evidence availability changed (preview)','New assessment version (preview)',
    'Saved assessment updated since Inbox snapshot','Source availability updated since Inbox snapshot'])
    assert.ok(ui.includes(key),key);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(back && front && back===front);
assert.ok(Number(back.split('.')[0])>=155);
console.log('PASS v155.6 current saved text/URL/assessment snapshot reconciliation');
