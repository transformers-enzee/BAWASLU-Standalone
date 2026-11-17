import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_saved_history_eval.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const qa=read('../backend/tests/test_saved_reply_batch_v1618.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const s of ['@router.post("/saved-reply-batch-audit")',
 'len(selections)>5','AssistantThread.user_id==user_id',
 'status="SOURCE_UNAVAILABLE"','"human_accuracy":None',
 '"database_writes":0','"schema":"BAWASLU_SAVED_REPLY_BATCH_AUDIT_V1618"'])
 assert.ok(api.includes(s),s);
for(const s of ['assistant-run-saved-reply-batch',
 'assistant-saved-reply-batch-result','assistant-save-batch-audit-candidates',
 'batch.unavailable','addAnswerAuditFindings'])assert.ok(ui.includes(s),s);
assert.ok(qa.includes('test_stale_source_is_explicit_failure_not_success'));
assert.ok(qa.includes('test_other_user_thread_not_audited_or_disclosed'));
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1618);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v161.8 bounded saved reply batch audit and fail-closed source authorization');
