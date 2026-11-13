import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const casework=read('../backend/app/casework.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['jurisdiction_status(db,campaign.id,post.id,post)',
'flag_review_recheck_required','jurisdiction_verification_changed_since_inbox',
'preview_flag_signal_recheck_count','preview_jurisdiction_verification_changed_count'])
 assert.ok(casework.includes(key),key);
for(const key of ['Flag signals needing renewed review (preview)',
'Jurisdiction verification changed (preview)',
'Incident jurisdiction verification changed; reconfirm before routing'])
 assert.ok(ui.includes(key),key);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(back && front && back===front);
console.log('PASS v155.7 jurisdiction and flag-review freshness contract');
