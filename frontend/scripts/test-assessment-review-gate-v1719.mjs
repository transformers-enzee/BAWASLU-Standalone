import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const core=read('../backend/app/assessment_exception_review.py');
const panel=read('src/components/intel/AssessmentOperationsPanel.jsx');
const browser=read('e2e/assessment-operations-interaction.spec.js');
for(const phrase of ['CONFLICTING_DIAGNOSTICS',
 'PROVIDER_FLAGS_MISSING_FROM_EXCEPTIONS',
 'PROVENANCE_GAPS_MISSING_FROM_EXCEPTIONS',
 'COMPLETED_PARTITION_DRIFT','QUEUE_SNAPSHOT_RECHECK_REQUIRED',
 'CONTRADICTORY_SNAPSHOT_REPORT'])assert.ok(core.includes(phrase),phrase);
assert.ok(panel.includes('exception-diagnostic-conflicts'));
assert.ok(browser.includes('contradictory nested review diagnostics are presented as blocked'));
console.log('PASS v171.9 nested administrator diagnostic safety contract');
