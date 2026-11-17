// Privacy-bounded, session-only QA issue occurrences; no source or answer excerpts.
const ID=/^(?:SOCIAL-[1-9][0-9]{0,11}|INT-[A-Za-z0-9:_-]{1,80}|DOC-[1-9][0-9]{0,11}-P[1-9][0-9]{0,7})$/;
const CODE=/^[A-Z0-9_]{1,100}$/;
const TYPES=new Set(['CITATION_INTEGRITY','SOURCE_RELEVANCE','CROSS_MODULE_COVERAGE',
 'LEGAL_SCOPE_REVIEW','HUMAN_EVIDENCE_VERIFICATION','FORMAL_DECISION_PROVENANCE',
 'PLATFORM_POLICY_AUTHORITY']);
const GUIDANCE={
 CITATION_INTEGRITY:'Reopen the actual answer and verify each displayed citation against the original authorized record.',
 SOURCE_RELEVANCE:'Check whether the selected evidence actually addresses the user question.',
 CROSS_MODULE_COVERAGE:'Check the omitted module and whether a claim needs its source cited.',
 LEGAL_SCOPE_REVIEW:'Ask an authorized legal reviewer to check applicable current provisions.',
 HUMAN_EVIDENCE_VERIFICATION:'Compare the claim with the original source before confirming an error.',
 FORMAL_DECISION_PROVENANCE:'Locate the formal decision record; social posts alone cannot certify a ruling.',
 PLATFORM_POLICY_AUTHORITY:'Verify the specific provider policy and version separately from electoral law.'
};
function vetted(entries){
 if(!Array.isArray(entries)||entries.length>30)throw Error('Invalid issue register');
 return entries.map(entry=>{
  if(!Array.isArray(entry?.source_ids)||!entry.source_ids.length||
     entry.source_ids.length>8||entry.source_ids.some(x=>typeof x!=='string'||!ID.test(x)))
   throw Error('Invalid source references');
  if(!Array.isArray(entry.issue_candidates)||entry.issue_candidates.length>24)
   throw Error('Invalid issue list');
  const candidates=entry.issue_candidates.map(x=>{
   if(!TYPES.has(x?.category)||!CODE.test(x?.code||'')||
      x?.status!=='PENDING_HUMAN_REVIEW')throw Error('Invalid issue category/code');
   return {category:x.category,code:x.code,status:'PENDING_HUMAN_REVIEW'};
  });
  if(!Number.isSafeInteger(entry.occurrences)||entry.occurrences<1||entry.occurrences>100000)
   throw Error('Invalid occurrence count');
  return {source_ids:[...new Set(entry.source_ids)].sort(),
   issue_candidates:candidates,issue_count:candidates.length,occurrences:entry.occurrences,
   human_verified:false,client_accepted:false};
 });
}
export function captureAnswerAuditFindings(result){
 const triage=result?.issue_triage,refs=result?.source_record_ids;
 if(triage?.schema!=='BAWASLU_ANSWER_AUDIT_CANDIDATES_V1611')
  throw Error('Unknown audit issue format');
 if(!Array.isArray(refs)||!refs.length||refs.length>8||
    refs.some(x=>typeof x!=='string'||!ID.test(x)))
  throw Error('Invalid source IDs');
 const issues=triage.issue_candidates;
 if(!Array.isArray(issues)||issues.length>24)throw Error('Invalid candidate list');
 const unique=new Map();
 for(const x of issues){
  if(!TYPES.has(x?.category)||!CODE.test(x?.code||'')||x?.human_confirmed!==false)
   throw Error('Invalid candidate code');
  unique.set(x.category+':'+x.code,
    {category:x.category,code:x.code,status:'PENDING_HUMAN_REVIEW'});
 }
 const source_ids=[...new Set(refs)].sort();
 const issue_candidates=[...unique.values()].sort((a,b)=>
  (a.category+':'+a.code).localeCompare(b.category+':'+b.code));
 return {key:JSON.stringify([source_ids,issue_candidates.map(x=>x.category+':'+x.code)]),
  source_ids,issue_candidates,issue_count:issue_candidates.length,occurrences:1,
  human_verified:false,client_accepted:false,raw_answer_present:false};
}
export function addAnswerAuditFindings(register,result){
 const row=captureAnswerAuditFindings(result);
 if(!row.issue_count)return register;
 const previous=register.find(x=>x.key===row.key);
 if(previous)row.occurrences=Math.min(100000,(previous.occurrences||1)+1);
 return [...register.filter(x=>x.key!==row.key),row].slice(-30);
}
export function summarizeAnswerAuditIssueRegister(register){
 const records=vetted(register);
 const counts={},observations={};
 for(const entry of records){
  for(const issue of entry.issue_candidates){
   counts[issue.category]=(counts[issue.category]||0)+1;
   observations[issue.category]=(observations[issue.category]||0)+entry.occurrences;
  }
 }
 return {distinct_issue_categories:Object.keys(counts).length,
  audit_entry_count:records.length,
  total_audit_occurrences:records.reduce((n,x)=>n+x.occurrences,0),
  category_counts:Object.fromEntries(Object.entries(counts).sort()),
  category_occurrences:Object.fromEntries(Object.entries(observations).sort()),
  next_checks:Object.keys(counts).sort().map(category=>({
   category,review_instruction:GUIDANCE[category],
   human_confirmed:false})),
  observed_model_accuracy:null,human_verified_findings:0};
}
export function exportAnswerAuditIssueRegister(register){
 const entries=vetted(register),summary=summarizeAnswerAuditIssueRegister(register);
 return JSON.stringify({schema:'BAWASLU_LOCAL_AUDIT_ISSUE_REGISTER_V1613',
  scope:'CURRENT_BROWSER_SESSION_ONLY',entries,summary,
  entries_total:entries.length,observed_model_accuracy:null,
  human_verified_findings:0,contains_raw_answer:false,contains_source_excerpt:false,
  formal_client_acceptance:false},null,2);
}
const csvCell=value=>{
 const valueText=String(value??'');
 const safe=/^[=+@\-\t\r]/.test(valueText)?'\''+valueText:valueText;
 return '"'+safe.replaceAll('"','""')+'"';
};
export function exportAnswerAuditIssueCsv(register){
 const entries=vetted(register);
 const rows=[['source_ids','issue_category','issue_code','occurrences','review_instruction',
              'human_confirmed','formal_client_acceptance']];
 for(const entry of entries){
  for(const issue of entry.issue_candidates)
   rows.push([entry.source_ids.join(' | '),issue.category,issue.code,
    entry.occurrences,GUIDANCE[issue.category],'false','false']);
 }
 return rows.map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
