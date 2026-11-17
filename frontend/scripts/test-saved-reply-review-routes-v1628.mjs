import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const py=read('../backend/app/assistant_saved_history_eval.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const shell=read('src/components/intel/Shell.jsx');
for(const token of ['_historical_review_route','review_route_counts','review_routes_are_unverified_suggestions','RECHECK_CURRENT_EVIDENCE_ACCESS','HUMAN_EVIDENCE_SPOT_CHECK'])
 assert.ok(py.includes(token),token);
for(const token of ['batch.review_route_counts','x.review_route','audit.review_route'])
 assert.ok(ui.includes(token),token);
assert.ok(shell.includes('data-build-version="162.8"'));
assert.ok(shell.includes('aria-label="Build version">v162.8'));
console.log('PASS v162.8 historical audit reviewer next-step routing guards');
