import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const api=read('../backend/app/assistant_saved_history_eval.py');
const test=read('../backend/tests/test_saved_reply_selection_v1620.py');
for(const item of ['batchSelected','toggleBatch(item)','assistant-batch-selection',
 'batchSelected.length>=5','batchSelected.map(key','reason_code_counts',
 'explicitly selected replies'])assert.ok(ui.includes(item),item);
for(const item of ['EXPLICIT_USER_SELECTED_REPLIES','batch_is_representative',
 '"reason_code_counts":dict(sorted(Counter('])assert.ok(api.includes(item),item);
for(const item of ['test_explicit_selection_status_totals_and_denied_reasons',
 'test_source_denial_distinguished_without_disclosing_hidden_source',
 'test_ineligible_selected_turn_is_counted_without_evidence_lookup'])
 assert.ok(test.includes(item),item);
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1620);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v162.0 explicit user selection and privacy-bounded reason aggregation');
