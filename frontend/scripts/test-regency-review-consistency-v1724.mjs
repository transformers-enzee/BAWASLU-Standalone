import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ui=read('src/pages/Inbox.jsx');
const api=read('../backend/app/jurisdiction_review.py');
const dispatch=read('../backend/app/campaigns.py');
const flow=read('../.github/workflows/playwright.yml');
for(const key of ['expected_assessment_version','regency-review-history',
 'campaignRegencyReviewHistory','Review is separate from regional access'])
 assert.ok(ui.includes(key),key);
for(const key of ['with_for_update','PROVINCE_REVIEW_CONFLICT',
 'Saved assessment changed since preview','Resolve confirmed Kabupaten',
 'regency_review_history'])assert.ok(api.includes(key),key);
assert.ok(dispatch.includes('campaignRegencyReviewHistory'));
assert.ok(flow.includes('test-regency-review-consistency-v1724.mjs'));
console.log('PASS v172.4 jurisdiction review revision/history/consistency contract');
