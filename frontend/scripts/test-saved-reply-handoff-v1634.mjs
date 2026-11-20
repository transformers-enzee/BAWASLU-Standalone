import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/saved_reply_reviews.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
for(const token of ['def pilot_handoff','BAWASLU_OWNED_PILOT_HANDOFF_V1634',
 'source_authorization_at_export','answer_text_included','handoff_bucket_counts',
 'bounded_inventory_not_all_historical_replies'])assert.ok(backend.includes(token),token);
for(const token of ['assistant-export-pilot-handoff','assistant-pilot-handoff-summary',
 'exportPilotHandoff','BAWASLU-owned-pilot-handoff-v1634.json'])assert.ok(ui.includes(token),token);
const version=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(version.replace('.',''))>=1634);
assert.ok(hasDynamicBuildVersion(read('src/components/intel/Shell.jsx'),version));
console.log('PASS v163.4 sanitized pilot handoff, review buckets and privacy contract');
