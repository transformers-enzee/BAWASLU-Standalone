const ID=/^(?:SOCIAL-[1-9][0-9]{0,11}|INT-[A-Za-z0-9:_-]{1,80}|DOC-[1-9][0-9]{0,11}-P[1-9][0-9]{0,7})$/;
const CODE=/^[A-Z0-9_]{1,100}$/;
const TYPES=new Set(['CITATION_INTEGRITY','SOURCE_RELEVANCE','CROSS_MODULE_COVERAGE',
 'LEGAL_SCOPE_REVIEW','HUMAN_EVIDENCE_VERIFICATION','FORMAL_DECISION_PROVENANCE',
 'PLATFORM_POLICY_AUTHORITY']);
export function captureAnswerAuditFindings(result){
 const triage=result?.issue_triage,refs=result?.source_record_ids;
 if(triage?.schema!=='BAWASLU_ANSWER_AUDIT_CANDIDATES_V1611')throw Error('Unknown audit issue format');
 if(!Array.isArray(refs)||!refs.length||refs.length>8||refs.some(x=>!ID.test(x)))throw Error('Invalid source IDs');
 const entries=triage.issue_candidates;
 if(!Array.isArray(entries)||entries.length>24)throw Error('Invalid candidate count');
 const unique=new Map();
 for(const x of entries){
  if(!TYPES.has(x.category)||!CODE.test(x.code)||x.human_confirmed!==false)throw Error('Invalid candidate code');
  unique.set(x.category+':'+x.code,{category:x.category,code:x.code,status:'PENDING_HUMAN_REVIEW'});
 }
 const source_ids=[...new Set(refs)].sort();
 const issue_candidates=[...unique.values()];
 return {key:JSON.stringify([source_ids,issue_candidates.map(x=>x.category+':'+x.code).sort()]),
  source_ids,issue_candidates,issue_count:issue_candidates.length,
  human_verified:false,client_accepted:false,raw_answer_present:false};
}
export function addAnswerAuditFindings(register,result){
 const row=captureAnswerAuditFindings(result);
 if(!row.issue_count)return register;
 return [...register.filter(x=>x.key!==row.key),row].slice(-30);
}
export function exportAnswerAuditIssueRegister(register){
 if(!Array.isArray(register)||register.length>30)throw Error('Invalid register');
 return JSON.stringify({schema:'BAWASLU_LOCAL_AUDIT_ISSUE_REGISTER_V1611',
  scope:'CURRENT_BROWSER_SESSION_ONLY',entries:register.map(x=>({
   source_ids:x.source_ids,issue_candidates:x.issue_candidates,issue_count:x.issue_count,
   human_verified:false,client_accepted:false})),
  entries_total:register.length,observed_model_accuracy:null,
  human_verified_findings:0,contains_raw_answer:false,contains_source_excerpt:false,
  formal_client_acceptance:false},null,2);
}
