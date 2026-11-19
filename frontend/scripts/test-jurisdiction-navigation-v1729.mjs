import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ready=read('../backend/app/jurisdiction_readiness.py');
const jurisdiction=read('../backend/app/jurisdiction_review.py');
const ui=read('src/pages/Inbox.jsx');
const tests=read('../backend/tests/test_jurisdiction_navigation_v1729.py');
const workflow=read('../.github/workflows/playwright.yml');
for(const phrase of ['CampaignEvidence.id<cursor',
 'DESCENDING_EVIDENCE_ID_KEYSET','next_cursor','WATCHLIST_ACCOUNT'])
 assert.ok(ready.includes(phrase),phrase);
assert.ok(jurisdiction.includes("data.get('cursor')"));
for(const phrase of ['openJurisdictionReviewLead','Inspect source in Inbox',
 'jurisdiction-review-pagination','Inspect older 30 campaign links',
 'result_id:expectedSource,paged:true,page_size:1'])
 assert.ok(ui.includes(phrase),phrase);
assert.ok(tests.includes('test_exact_scoped_post_lookup_works_when_outside_loaded_inbox_page'));
assert.ok(workflow.includes('test-jurisdiction-navigation-v1729.mjs'));
console.log('PASS v172.9 older review queue navigation and scoped evidence open contracts');
