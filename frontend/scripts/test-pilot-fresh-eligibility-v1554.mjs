import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const casework=read('../backend/app/casework.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const fragment of ['scoped_post(db,p,item["campaign_id"],item["source_id"])',
  'LATEST_ASSESSMENT_NOT_RELEVANT','SOURCE_NOT_IN_AUTHORIZED_SCOPE',
  'preview_latest_saved_recheck_count','preview_latest_recheck_is_not_full_cohort',
  'item["casework_link"]=None','item["source_link"]=None']) {
  assert.ok(casework.includes(fragment),fragment);
}
for(const fragment of ['Latest saved source eligible (preview)',
  'Latest assessment no longer relevant (preview)',
  'Source now unavailable in scope (preview)',
  'Source no longer available in your permission scope']) {
  assert.ok(ui.includes(fragment),fragment);
}
assert.ok(main.includes("'build_version':'155.4'"));
assert.ok(shell.includes('data-build-version="155.4"'));
console.log('PASS v155.4 latest saved-source eligibility and pilot navigation guards');
