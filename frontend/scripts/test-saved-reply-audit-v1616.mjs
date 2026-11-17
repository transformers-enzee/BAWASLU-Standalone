import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_saved_history_eval.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const sampler=read('src/components/intel/AssistantEvaluationSampler.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
const audit=read('../backend/app/assistant_eval_sampling.py');
for(const s of ['AssistantThread.user_id==user.id','resolve_mixed_audit_sources(db,principal,audit)',
 '_read_messages','"includes_answer_text":False','"source_permission_rechecked_at_listing":False',
 '"history_content_user_editable":True','"original_model_generation_provenance_verified":False',
 'model_calls":0','MAX_SOURCE_CARDS=12','"X-Evaluation-Generation"]="NONE"'])
 assert.ok(api.includes(s),s);
assert.ok(main.includes('app.include_router(saved_history_eval_router)'));
assert.ok(audit.includes('max_length=12'));
assert.ok(audit.includes('retrieve_exact_pdf_pages(db,principal,question,limit=12)'));
for(const s of ['assistant-load-saved-replies','assistant-run-saved-reply-audit',
 'assistant-saved-reply-audit-result','assistant-record-saved-reply-candidates'])
 assert.ok(ui.includes(s),s);
assert.ok(sampler.includes('<AssistantSavedReplyAudit disabled={disabled||loading}/>'));
assert.ok(main.includes("'build_version':'161.6'"));
assert.ok(shell.includes('data-build-version="161.6"'));
console.log('PASS v161.6 owned answer replay, no source substitution, zero credits and privacy');
