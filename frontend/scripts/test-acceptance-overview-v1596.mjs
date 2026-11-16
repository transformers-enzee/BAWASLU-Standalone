import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const ui=read('src/pages/AcceptanceReview.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for (const s of ['limit(101)','AssistantAcceptanceEvidenceEvent.evidence_id.in_',
 'MOST_RECENT_100_SUBMISSIONS_ONLY','historical_records_may_be_excluded',
 'external_acceptance_tracks_pending','has_formal_approval']){
 assert.ok(api.includes(s),s);
}
for(const s of ['Acceptance requirements — evidence coverage only',
 'Formal sign-off: not verified','Older submissions are outside the 100-record window',
 'result.track_progress?.[code]'])assert.ok(ui.includes(s),s);
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1596);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v159.6 bounded acceptance coverage and batched event retrieval');
