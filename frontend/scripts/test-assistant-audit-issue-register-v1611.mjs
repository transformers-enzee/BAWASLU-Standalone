import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {addAnswerAuditFindings,exportAnswerAuditIssueRegister} from '../src/lib/assistantAuditIssueRegister.js';
const fixture={source_record_ids:['SOCIAL-7','INT-2026-000001'],
 issue_triage:{schema:'BAWASLU_ANSWER_AUDIT_CANDIDATES_V1611',
 issue_candidates:[{category:'CROSS_MODULE_COVERAGE',
 code:'SELECTED_UNCITED_FORMAL_INTELLIGENCE',human_confirmed:false}]}};
const rows=addAnswerAuditFindings([],fixture);
assert.equal(rows.length,1);
assert.equal(addAnswerAuditFindings(rows,fixture).length,1);
const exportText=exportAnswerAuditIssueRegister(rows);
assert.equal(JSON.parse(exportText).observed_model_accuracy,null);
assert.equal(JSON.parse(exportText).human_verified_findings,0);
assert.deepEqual(Object.keys(JSON.parse(exportText).entries[0]).sort(),
 ['client_accepted','human_verified','issue_candidates','issue_count','occurrences','source_ids']);
assert.equal(JSON.parse(exportText).contains_source_excerpt,false);
assert.equal(JSON.parse(exportText).contains_raw_answer,false);
assert.throws(()=>addAnswerAuditFindings([],{...fixture,source_record_ids:['SOCIAL-0']}));
assert.throws(()=>addAnswerAuditFindings([],{...fixture,issue_triage:{
 ...fixture.issue_triage,issue_candidates:[{category:'LEGAL_SCOPE_REVIEW',code:'=BAD()',human_confirmed:false}]
}}));
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_eval_sampling.py');
const ui=read('src/components/intel/AssistantSavedAnswerAudit.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(api.includes('classify_answer_audit(qa,ground,cited'));
assert.ok(api.includes('classify_answer_audit(quality,ground,cited,kinds)'));
for(const token of ['assistant-add-audit-register','assistant-qa-issue-register',
 'assistant-export-qa-issue-register','issue_triage.issue_candidates'])
 assert.ok(ui.includes(token),token);
const v=readBackendVersion(main);
assert.ok(Number(v.replace('.',''))>=1611);
assert.ok(hasDynamicBuildVersion(shell,v));
console.log('PASS v161.1 warning-only QA register and sanitized local export');
