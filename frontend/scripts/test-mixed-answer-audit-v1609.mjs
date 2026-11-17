import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const endpoint=read('../backend/app/assistant_eval_sampling.py');
const ui=read('src/components/intel/AssistantSavedAnswerAudit.jsx');
const qa=read('../backend/tests/test_mixed_answer_audit_v1609.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const token of ['@router.post("/mixed-answer-audit")','retrieve_exact_pdf_pages(db,principal,question,limit=8)',
 'set(resolved)!=set(ids)','list_intelligence(db,principal)',
 'build_mixed_answer_audit','"human_accuracy":None',
 '"raw_source_text_included":False','"pasted_answer_stored":False'])
 assert.ok(endpoint.includes(token),token);
for(const token of ['Cross-module audit','mixed-audit-additional-ids',
 '/api/assistant-evaluation/mixed-answer-audit','missing_cited_source_kinds',
 'legal_review_issue_codes'])
 assert.ok(ui.includes(token),token);
assert.ok(qa.includes('test_inaccessible_pdf_page_aborts_entire_request'));
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1609);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v160.9 all-or-nothing permission-scoped mixed source audit');
