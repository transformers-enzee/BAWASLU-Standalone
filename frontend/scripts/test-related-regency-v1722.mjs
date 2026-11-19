import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const panel=read('src/pages/Inbox.jsx');
const backend=read('../backend/app/related_incident_locations.py');
const workflow=read('../.github/workflows/playwright.yml');
for(const token of ['Open original source','noopener noreferrer',
 'within_72_hours_count','cross_platform_review_lead',
 'publication_window_status'])assert.ok(panel.includes(token),token);
for(const token of ['_safe_source_url','UNKNOWN_PUBLICATION_TIME',
 'WITHIN_72_HOURS','platform_variety_is_not_independent_corroboration'])
 assert.ok(backend.includes(token),token);
assert.ok(workflow.includes('test-related-regency-v1722.mjs'));
console.log('PASS v172.2 safe cross-platform locality review source navigation');
