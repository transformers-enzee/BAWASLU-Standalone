import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const panel=read('src/components/intel/AssessmentOperationsPanel.jsx');
const core=read('../backend/app/assessment_exception_review.py');
for(const token of ['manual-approval-review-gate','manual-approval-blockers',
 'displayable_capacity_if_all_checks_clear','Raw legacy capacity (not an authorization)']) {
 assert.ok(panel.includes(token),token);
}
for(const token of ['UNRECONCILED_SNAPSHOT','MISSING_DIAGNOSTIC_AUDITS',
 'UNRECOGNIZED_EXCEPTION','HISTORICAL_EXCEPTION','QUEUE_RECONCILIATION_REQUIRED',
 'LEGACY_PREFLIGHT_NOT_ELIGIBLE','never_authorizes_paid_processing']) {
 assert.ok(core.includes(token),token);
}
assert.ok(!panel.includes("action:'campaignAssessmentInterruptedQuarantine'"));
console.log('PASS v171.6 consolidated preflight safety contract');
