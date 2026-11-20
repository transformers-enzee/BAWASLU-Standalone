import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
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
const ver=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(ver.replace('.',''))>=1628);
assert.ok(hasDynamicBuildVersion(shell,ver));
assert.ok(hasDynamicBuildVersion(shell,ver),'Footer must show the runtime backend release');
console.log('PASS v162.8 historical audit reviewer next-step routing guards');
