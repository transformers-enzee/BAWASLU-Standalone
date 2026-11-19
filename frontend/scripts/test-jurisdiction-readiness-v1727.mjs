import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const endpoint=read('../backend/app/jurisdiction_review.py');
const dispatch=read('../backend/app/campaigns.py');
const readiness=read('../backend/app/jurisdiction_readiness.py');
const inbox=read('src/pages/Inbox.jsx');
const detector=read('../backend/app/incident_regency_candidates.py');
const flow=read('../.github/workflows/playwright.yml');
for(const phrase of ['campaignJurisdictionReadiness','View campaign jurisdiction readiness (free)',
 'campaign-jurisdiction-readiness','not full-corpus totals'])
 assert.ok((endpoint+dispatch+inbox).includes(phrase),phrase);
for(const phrase of ['SCAN_LIMIT=30','more_evidence_may_exist',
 'not_geolocation_accuracy','not_client_acceptance',
 '_result_in_scope','allowed(principal,campaign)'])
 assert.ok(readiness.includes(phrase),phrase);
assert.ok(detector.includes('for _ in range(8)'));
assert.ok(flow.includes('test-jurisdiction-readiness-v1727.mjs'));
console.log('PASS v172.7 scoped jurisdiction readiness and chained locality contract');
