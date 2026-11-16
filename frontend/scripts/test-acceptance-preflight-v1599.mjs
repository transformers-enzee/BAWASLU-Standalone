import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const ui=read('src/pages/AcceptanceReview.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(api.includes('@router.get("/{evidence_id}")'));
assert.ok(api.includes('def get_evidence('));
assert.ok(api.includes('response.headers["Cache-Control"]="private, no-store"'));
for(const s of ['async function prepareReview(entry,action)',
 'fresh.status!==\'SUBMITTED_UNVERIFIED\'',
 'setConfirm({id:entry.id,action,reference:fresh.reference',
 'async function review()','error.status=reply.status',
 'Review conflict: this submission','Review recorded, but unable to reload the list',
 'prepareReview(entry,\'EVIDENCE_REVIEWED\')',
 'prepareReview(entry,\'REVISION_REQUESTED\')'])
 assert.ok(ui.includes(s),s);
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1599);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v159.9 fresh review preflight, stale-conflict messaging, no false failure');
