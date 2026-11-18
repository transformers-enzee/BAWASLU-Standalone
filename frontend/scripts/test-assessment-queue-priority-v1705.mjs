import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const code=read('src/components/intel/AssessmentOperationsPanel.jsx');
for(const key of [
 'NEEDS_HISTORY','URGENT_HISTORY_REVIEW','HISTORY_REVIEW',
 'NEEDS_QUEUE','QUEUE_REVIEW','priorityLabel','priorityStyle',
 'filter(row=>Number(row.count)>0)','categories.action.map','categories.information.map',
 'data-testid="assessment-triage-categories"','snapshotUnreliable',
 'data?.snapshot_consistency?.all_consistent===false',
 "data-testid=\"assessment-triage-read-time\"",
 'Refreshing; displayed figures may be outdated.',
 'previous results may be out of date',
 'Only nonzero categories are displayed.',
 'No active history or queue-review categories.'
]) assert.ok(code.includes(key),'Missing read-only queue priority UI guard: '+key);
assert.ok(code.includes("action:'campaignAssessmentOperationsOverview'"));
assert.ok(!code.includes("action:'campaignAssessmentSupersededApply'"));
assert.ok(!code.includes("action:'campaignAssessmentInterruptedQuarantine'"));
assert.ok(!code.includes("confirm_ai_cost:true"));
console.log('PASS v170.5 separated review/informational queue states with safe snapshot freshness');
