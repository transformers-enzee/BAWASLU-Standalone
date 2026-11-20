import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/saved_reply_reviews.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
for(const code of ['def pilot_queue','BAWASLU_OWNED_SAVED_REPLY_PILOT_QUEUE_V1633','recommended_next_batch_count',
 'source_permission_rechecked_at_listing','_gate(db,user)','limit(40)','len(records)>=120'])
 assert.ok(backend.includes(code),code);
for(const code of ['assistant-load-pilot-review-queue','assistant-pilot-review-summary',
 'assistant-select-pilot-batch','selectPilotBatch','slice(0,5)'])assert.ok(ui.includes(code),code);
const version=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(version.replace('.',''))>=1633);
assert.ok(hasDynamicBuildVersion(read('src/components/intel/Shell.jsx'),version));
console.log('PASS v163.3 owned pilot review inventory and bounded selection');
