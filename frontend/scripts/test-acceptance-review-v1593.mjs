import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const app=read('src/App.jsx');
const admin=read('src/pages/Administration.jsx');
const ui=read('src/pages/AcceptanceReview.jsx');
const shell=read('src/components/intel/Shell.jsx');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const backend=read('../backend/app/main.py');
assert.ok(app.includes('path="/administration/acceptance-review" element={<AcceptanceReview />}'));
assert.ok(app.includes('permission="administration"'));
assert.ok(admin.includes('to="/administration/acceptance-review"'));
assert.ok(admin.includes('access.geographic_scope===\'Nationwide\''));
assert.ok(!ui.includes('VITE_API_BASE_URL'),'Acceptance actions must use same-origin authenticated API');
for(const s of ['window.__BAWASLU_DEMO_REPLICA__','National Administrator','geographic_scope',
 'SUBMITTED_UNVERIFIED','REVISION_REQUESTED','EVIDENCE_REVIEWED',
 'Independent administrator required','aria-modal="true"','View audit history',
 'legal or client sign-off','cache:\'no-store\''])assert.ok(ui.includes(s),s);
for(const s of ['_admin(db,user)','Independent reviewer required','REVIEWED',
 'REVISION_REQUESTED','legal_signoff','client_acceptance'])assert.ok(api.includes(s),s);
const v=backend.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1593);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v159.3 administrator Acceptance Review UI, safe review actions and version parity');
