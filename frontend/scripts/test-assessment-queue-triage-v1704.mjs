import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const panel=read('src/components/intel/AssessmentOperationsPanel.jsx');
const backend=read('../backend/app/assessment_operations_overview.py');
const diagnostic=read('../backend/app/assessment_queue_triage.py');
assert.ok(backend.includes("'queue_triage':queue_triage"),'API supplies triage payload');
assert.ok(panel.includes('data?.queue_triage'),'UI binds to new API payload');
for(const key of ['Assessment queue lifecycle triage','queue-bucket-','assessment-pending-breakdown',
 'RECHECK_INDEPENDENT_SNAPSHOTS','breakdown.breakdown_reconciled','triage.buckets_partition_all_jobs',
 'triage.outdated_superseded_classifications','triage.stale_threshold_minutes']) {
  assert.ok(panel.includes(key),'UI lifecycle contract missing '+key);
}
for(const category of ['STALE_PROCESSING','QUARANTINED_INTERRUPTED','FAILED_OTHER',
 'SUPERSEDED_ASSESSED','PROCESSING_ACTIVE','PENDING','COMPLETED']) {
  assert.ok(diagnostic.includes("'"+category+"'"),'diagnostic category missing '+category);
}
assert.ok(panel.includes('read-only'));
assert.ok(panel.includes('No new assessments, retries or paid requests.'));
assert.ok(!panel.includes('action:\'campaignAssessmentSupersededApply\''),'triage must not auto-reconcile');
assert.ok(!panel.includes('action:\'campaignAssessmentInterruptedQuarantine\''),'triage must not auto-quarantine');
console.log('PASS v170.4 read-only administrator queue-triage contract');
