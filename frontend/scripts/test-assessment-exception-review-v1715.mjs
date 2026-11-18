import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const view=read('src/components/intel/AssessmentOperationsPanel.jsx');
const overview=read('../backend/app/assessment_operations_overview.py');
const review=read('../backend/app/assessment_exception_review.py');
for(const token of ['exception-missing-audits','exception-snapshot-warning',
 'exception-audit-coverage','history_verification_blocked_by_missing_audits']) {
 assert.ok((view+review).includes(token),'Missing explicit review safeguard: '+token);
}
assert.ok(overview.includes('assessment_exception_review(issues,queue_triage,acceptance,consistency)'));
assert.ok(review.includes('RESTORE_MISSING_AUDITS'));
assert.ok(review.includes("snapshot_consistency.get('all_consistent') is True"));
assert.ok(view.includes('Historical provider usage independently verified: No'));
console.log('PASS v171.5 audit availability and consistency review UI contract');
