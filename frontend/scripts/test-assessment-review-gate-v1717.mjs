import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const panel=read('src/components/intel/AssessmentOperationsPanel.jsx');
const core=read('../backend/app/assessment_exception_review.py');
const playwright=read('e2e/assessment-operations-interaction.spec.js');
const workflow=read('../.github/workflows/playwright.yml');
assert.ok(core.includes('SNAPSHOT_AUDIT_UNAVAILABLE'));
assert.ok(panel.includes('manual-approval-gate-unavailable'));
assert.ok(playwright.includes('older API without consolidated gate prominently fails closed'));
assert.ok(playwright.includes('consolidated gate blocks capacity when snapshot audit is unavailable'));
for(const version of ['1714','1715','1716','1717']){
 assert.ok(workflow.includes('test-assessment-'+(version==='1714'||version==='1715'?'exception-review-':'review-gate-v')+version+'.mjs') || workflow.includes('v'+version+'.mjs'),
  'Missing v'+version+' frontend regression execution');
}
console.log('PASS v171.7 administrator regression wiring and browser coverage');
