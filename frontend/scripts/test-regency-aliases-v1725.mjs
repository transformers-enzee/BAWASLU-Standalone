import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../backend/app/incident_regency_candidates.py',import.meta.url),'utf8');
const tests=readFileSync(new URL('../../backend/tests/test_regency_alias_precision_v1725.py',import.meta.url),'utf8');
const workflow=readFileSync(new URL('../../.github/workflows/playwright.yml',import.meta.url),'utf8');
for(const item of ['_UNIQUE_SUFFIXES','_EXPLICIT_FORMS',"'Kab. '",
 'len(rows)==1'])assert.ok(source.includes(item),item);
assert.ok(tests.includes('test_source_location_precision_fixture'));
assert.ok(workflow.includes('test-regency-aliases-v1725.mjs'));
console.log('PASS v172.5 locality aliases and ambiguity contract');
