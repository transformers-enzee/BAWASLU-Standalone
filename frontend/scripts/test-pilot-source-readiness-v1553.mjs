import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const pilot=read('../backend/app/officer_pilot_intake.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const backend=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const flag of ['MISSING_TEXT_AND_URL','MISSING_ORIGINAL_TEXT','MISSING_ORIGINAL_URL',
 'missing_saved_text_count','missing_saved_url_count','preview_existing_case_count',
 'existing_case_count_preview_only','original_source_verified']) assert.ok(pilot.includes(flag), flag);
for(const flag of ['Missing saved text','Missing original URL','Existing cases in preview',
 'Recover saved source text','Recover original source URL','Existing case: recheck original source']) assert.ok(ui.includes(flag), flag);
assert.ok(backend.includes("'build_version':'155.3'"));
assert.ok(shell.includes('data-build-version="155.3"'));
console.log('PASS v155.3 saved-source recovery distinctions, existing-case preview counts and release parity');
