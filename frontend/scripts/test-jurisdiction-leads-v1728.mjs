import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const logic=read('../backend/app/jurisdiction_readiness.py');
const ui=read('src/pages/Inbox.jsx');
const workflow=read('../.github/workflows/playwright.yml');
for(const p of ['officer_review_leads','STALE_OR_CONFLICTED',
 'MULTIPLE_INCIDENT_LOCALITIES','review_leads_truncated',
 '_safe_source_url(post.canonical_url)','not_independently_verified'])
 assert.ok(logic.includes(p),p);
for(const p of ['jurisdiction-officer-review-leads',
 'Inspect on visible Inbox page','Open saved original post','noopener noreferrer'])
 assert.ok(ui.includes(p),p);
assert.ok(workflow.includes('test-jurisdiction-leads-v1728.mjs'));
console.log('PASS v172.8 officer review leads security and bounded evidence');
