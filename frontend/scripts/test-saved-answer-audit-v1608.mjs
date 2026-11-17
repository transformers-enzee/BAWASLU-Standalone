import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_eval_sampling.py');
const pane=read('src/components/intel/AssistantSavedAnswerAudit.jsx');
const sampler=read('src/components/intel/AssistantEvaluationSampler.jsx');
const qa=read('../backend/tests/test_saved_answer_audit_v1608.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const token of ['@router.post("/saved-answer-audit")',
 'def build_saved_answer_audit','live_inbox_findings(db,principal)',
 'set(found)!=wanted','"raw_source_text_included":False',
 '"pasted_answer_stored":False','"human_accuracy":None',
 '"Cache-Control"]="private, no-store"'])
 assert.ok(api.includes(token),token);
for(const token of ['saved-answer-audit','maxLength={10000}',
 'Check against saved source (no AI call)','data-testid="assistant-saved-answer-audit-result"'])
 assert.ok(pane.includes(token),token);
assert.ok(sampler.includes('AssistantSavedAnswerAudit'));
assert.ok(sampler.includes('item.not_a_real_source?null:item'));
assert.ok(qa.includes('test_all_or_nothing_source_scope_does_not_enumerate_hidden_rows'));
const v=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(v.replace('.',''))>=1608);
assert.ok(shell.includes('data-build-version="'+v+'"'));
console.log('PASS v160.8 real saved-source, no-generation answer audit and privacy guards');
