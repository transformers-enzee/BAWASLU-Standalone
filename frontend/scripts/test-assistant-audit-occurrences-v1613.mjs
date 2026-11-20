import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {addAnswerAuditFindings,summarizeAnswerAuditIssueRegister,
 exportAnswerAuditIssueRegister,exportAnswerAuditIssueCsv} from '../src/lib/assistantAuditIssueRegister.js';
const input={source_record_ids:['SOCIAL-7','INT-2026-000001'],
 issue_triage:{schema:'BAWASLU_ANSWER_AUDIT_CANDIDATES_V1611',issue_candidates:[
  {category:'CROSS_MODULE_COVERAGE',code:'SELECTED_UNCITED_FORMAL_INTELLIGENCE',human_confirmed:false},
  {category:'CITATION_INTEGRITY',code:'UNAVAILABLE_DISPLAYED_REFERENCE',human_confirmed:false}]}};
const once=addAnswerAuditFindings([],input);
const twice=addAnswerAuditFindings(once,input);
assert.equal(twice.length,1);
assert.equal(twice[0].occurrences,2);
assert.equal(summarizeAnswerAuditIssueRegister(twice).total_audit_occurrences,2);
assert.equal(summarizeAnswerAuditIssueRegister(twice).category_counts.CITATION_INTEGRITY,1);
assert.equal(summarizeAnswerAuditIssueRegister(twice).category_occurrences.CITATION_INTEGRITY,2);
assert.equal(summarizeAnswerAuditIssueRegister(twice).human_verified_findings,0);
const json=JSON.parse(exportAnswerAuditIssueRegister(twice));
assert.equal(json.schema,'BAWASLU_LOCAL_AUDIT_ISSUE_REGISTER_V1613');
assert.equal(json.entries[0].occurrences,2);
assert.equal(json.contains_raw_answer,false);
assert.equal(json.contains_source_excerpt,false);
assert.deepEqual(Object.keys(json.entries[0]).sort(),
 ['client_accepted','human_verified','issue_candidates','issue_count','occurrences','source_ids']);
const csv=exportAnswerAuditIssueCsv(twice);
assert.ok(csv.includes('"INT-2026-000001 | SOCIAL-7"'));
assert.ok(csv.includes('"2"'));
assert.ok(csv.includes('review_instruction'));
assert.ok(csv.includes('Check the omitted module'));
assert.ok(!csv.includes('source_excerpt'));
assert.throws(()=>exportAnswerAuditIssueCsv([{...twice[0],occurrences:-1}]));
assert.throws(()=>exportAnswerAuditIssueRegister([{...twice[0],source_ids:['SOCIAL-0']}]));
assert.throws(()=>exportAnswerAuditIssueRegister([{...twice[0],issue_candidates:[
 {category:'LEGAL_SCOPE_REVIEW',code:'=HYPERLINK()',status:'PENDING_HUMAN_REVIEW'}]}]));
assert.equal(addAnswerAuditFindings([], {...input,issue_triage:{...input.issue_triage,issue_candidates:[]}}).length,0);
const ui=readFileSync(new URL('../src/components/intel/AssistantSavedAnswerAudit.jsx',import.meta.url),'utf8');
for(const key of ['assistant-export-qa-issue-csv','assistant-audit-category-summary','audit occurrence(s)',
 'summarizeAnswerAuditIssueRegister'])assert.ok(ui.includes(key),key);
const main=readFileSync(new URL('../../backend/app/main.py',import.meta.url),'utf8');
const shell=readFileSync(new URL('../src/components/intel/Shell.jsx',import.meta.url),'utf8');
const current=readBackendVersion(main);
assert.ok(Number(current.replace('.',''))>=1613);
assert.ok(hasDynamicBuildVersion(shell,current));
// Version parity checked using the current release, not a stale exact label.
console.log('PASS v161.3 recurring warning aggregation, safe CSV/JSON, human verification boundaries');
