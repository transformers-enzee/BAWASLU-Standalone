import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const core=read('../backend/app/incident_regency_candidates.py');
const evalModule=read('../backend/app/incident_regency_eval.py');
const tests=read('../backend/tests/test_incident_regency_eval_v1726.py');
const flow=read('../.github/workflows/playwright.yml');
assert.ok(core.includes('_NEGATED_INCIDENT'));
assert.ok(!core.includes('temuan|pemilu|pilkada'));
for(const item of ['micro_precision','micro_recall','false_positives',
 'labeled_cases','not_real_world_accuracy_without_representative_labels'])
 assert.ok(evalModule.includes(item),item);
assert.ok(tests.includes("labeled_cases']==10"));
assert.ok(flow.includes('test-regency-eval-v1726.mjs'));
console.log('PASS v172.6 reproducible source-level jurisdiction evaluation');
