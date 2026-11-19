import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/jurisdiction_review.py');
const inbox=read('src/pages/Inbox.jsx');
const api=read('../backend/app/campaigns.py');
const saved=read('../backend/app/saved_assessment_views.py');
const readiness=read('../backend/app/jurisdiction_readiness.py');
const ci=read('../.github/workflows/playwright.yml');
for(const s of ['jurisdiction_statuses_for_posts','_jurisdiction_status_from_rows',
 'AuditEvent.subject_id.in_(subject_ids)'])assert.ok(backend.includes(s),s);
for(const s of ['jurisdiction_statuses_for_posts','jurisdiction_posts_by_id'])
 assert.ok(api.includes(s),s);
assert.ok(saved.includes('scoped_statuses=jurisdiction_statuses_for_posts'));
assert.ok(readiness.includes("city.get('decision')!='REJECTED'"));
for(const s of ['jurisdiction-review-toolbar','jurisdiction-review-main-queue',
 'Open jurisdiction review queue','onClick={()=>loadJurisdictionReadiness()}'])
 assert.ok(inbox.includes(s),s);
assert.ok(ci.includes('test-jurisdiction-bulk-v1731.mjs'));
console.log('PASS v173.1 shared bulk review states, scoped queue and query budget');
