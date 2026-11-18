import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const overview=read('../backend/app/assessment_operations_overview.py');
const module=read('../backend/app/assessment_exception_review.py');
const panel=read('src/components/intel/AssessmentOperationsPanel.jsx');
assert.ok(overview.includes("'exception_review':exception_review"));
for(const key of ['assessment-exception-review','exception-group-','exception-review-next-step',
 'exception-history-boundary','Historical provider usage independently verified: No']) {
 assert.ok(panel.includes(key),key);
}
for(const key of ['REFRESH_SNAPSHOT','INVESTIGATE_PROVIDER_HISTORY','RECONCILE_QUEUE',
 'VERIFY_HISTORICAL_USAGE_INDEPENDENTLY','historical_provider_usage_independently_verified']) {
 assert.ok(module.includes(key),key);
}
assert.ok(!panel.includes("action:'campaignAssessmentInterruptedQuarantine'"));
console.log('PASS v171.4 administrator exception review static contract');
