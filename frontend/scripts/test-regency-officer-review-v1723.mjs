import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ui=read('src/pages/Inbox.jsx');
const api=read('../backend/app/jurisdiction_review.py');
const dispatch=read('../backend/app/campaigns.py');
const workflow=read('../.github/workflows/playwright.yml');
for(const text of ['campaignRegencyReview','reviewed-regency-city',
 'Verify selected Kabupaten/Kota','Reject Kabupaten/Kota cue',
 'expected_source_fingerprint','expected_review_event_id'])
 assert.ok(ui.includes(text),text);
for(const text of ['CampaignIncidentRegencyReview',
 'INCIDENT_REGENCY_REVIEWED','STALE_ASSESSMENT_CHANGED',
 'Source changed since preview','Review changed since preview',
 'Human Validation permission required'])
 assert.ok(api.includes(text),text);
assert.ok(dispatch.includes('campaignRegencyReview'));
assert.ok(workflow.includes('test-regency-officer-review-v1723.mjs'));
console.log('PASS v172.3 audited officer Kabupaten/Kota review contract');
