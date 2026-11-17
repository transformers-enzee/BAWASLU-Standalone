import {useEffect,useState} from 'react';
import {addAnswerAuditFindings,exportAnswerAuditIssueRegister} from '@/lib/assistantAuditIssueRegister';

export default function AssistantSavedAnswerAudit({item,disabled=false}){
 const [answer,setAnswer]=useState('');
 const [busy,setBusy]=useState(false);
 const [result,setResult]=useState(null);
 const [error,setError]=useState('');
 const [mixed,setMixed]=useState(false);
 const [additionalIds,setAdditionalIds]=useState('');
 const [register,setRegister]=useState([]);
 const [registerError,setRegisterError]=useState('');
 useEffect(()=>{setAnswer('');setResult(null);setError('');setAdditionalIds('');setMixed(false)},[item?.source_record_id]);
 async function run(){
  if(busy||disabled||!item?.source_record_id||!answer.trim())return;
  setBusy(true);setError('');setResult(null);
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw Error('An authorized session is required.');
   const refs=[item.source_record_id,...(mixed?additionalIds.split(/[\s,]+/).map(x=>x.trim()).filter(Boolean):[])];
   const response=await fetch(mixed?
    '/api/assistant-evaluation/mixed-answer-audit':
    '/api/assistant-evaluation/saved-answer-audit',{
    method:'POST',cache:'no-store',
    headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
    body:JSON.stringify({source_ids:refs,question:item.question,answer})
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Source audit failed.');
   if(data.schema!==(mixed?'BAWASLU_MIXED_ANSWER_AUDIT_V1609':'BAWASLU_SAVED_ANSWER_AUDIT_V1608'))
    throw Error('Unknown audit response schema.');
   setResult(data);
  }catch(e){setError(e.message||'Could not audit the submitted answer.')}
  finally{setBusy(false)}
 }
 function addToRegister(){
  try{setRegister(old=>addAnswerAuditFindings(old,result));setRegisterError('')}
  catch(ex){setRegisterError(ex.message||'Cannot register audit')}
 }
 function exportRegister(){
  try{
   const blob=new Blob([exportAnswerAuditIssueRegister(register)],{type:'application/json;charset=utf-8'});
   const url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download='BAWASLU-AI-QA-issue-candidates-v1611.json';a.click();
   setTimeout(()=>URL.revokeObjectURL(url),10000);setRegisterError('');
  }catch(ex){setRegisterError(ex.message||'Cannot export issue register')}
 }
 if(!item)return null;
 return <div data-testid="assistant-saved-answer-audit"
  className="rounded-lg border border-[#d5e1ea] bg-[#f8fbfd] p-3 space-y-2">
  <p className="text-xs font-semibold text-[#263749]">Read-only source audit · {item.source_record_id}</p>
  <p className="text-[11px] text-[#60748a]">
   Run the prepared question in the Assistant separately, then paste its response here.
   This compares citation IDs and lexical readiness with the saved source you can access.
   It neither generates an answer nor verifies factual truth; the pasted text is not stored.
  </p>
  <label className="flex gap-2 items-center text-xs">
   <input type="checkbox" checked={mixed} onChange={e=>{setMixed(e.target.checked);setResult(null)}}/>
   Cross-module audit (include authorized Inbox INT IDs and/or exact PDF page IDs)
  </label>
  {mixed&&<div className="space-y-1">
   <label htmlFor="mixed-audit-additional-ids" className="block text-xs font-semibold">
    Additional exact source IDs (comma or space separated; maximum 8 total)
   </label>
   <input id="mixed-audit-additional-ids" data-testid="mixed-audit-additional-ids"
    className="w-full rounded-md border border-[#ccd7df] bg-white px-3 py-2 text-xs"
    value={additionalIds} onChange={e=>{setAdditionalIds(e.target.value);setResult(null)}}
    maxLength={500} placeholder="INT-2026-000001, DOC-1-P2"/>
   <p className="text-[11px] text-[#876532]">An inaccessible source fails the entire audit. The selected PDF page and formal Inbox record must already be available to your account. No legal conclusion is verified.</p>
  </div>}
  <label htmlFor="saved-answer-audit-text" className="block text-xs font-semibold">
   Actual Assistant answer to inspect
  </label>
  <textarea id="saved-answer-audit-text" data-testid="assistant-saved-answer-input"
   value={answer} onChange={e=>{setAnswer(e.target.value);setResult(null)}}
   disabled={disabled||busy} maxLength={10000} rows={5}
   className="w-full rounded-md border border-[#ccd7df] bg-white px-3 py-2 text-xs"
   placeholder="Paste the actual AI Assistant response, including displayed [SOCIAL-ID] citations."/>
  <button type="button" className="intel-button text-xs"
   disabled={disabled||busy||answer.trim().length<3} onClick={run}
   data-testid="assistant-run-saved-answer-audit">
   {busy?'Checking…':mixed?'Check mixed sources (no AI call)':'Check against saved source (no AI call)'}
  </button>
  {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
  {result&&<div data-testid="assistant-saved-answer-audit-result" className="space-y-2">
   <p className="text-xs font-semibold">Audit: {result.review_required_checks} checks need review · {(result.cited_count??result.cited_authorized_ids?.length??0)} authorized citation(s)</p>
   {mixed&&result.missing_cited_source_kinds?.length>0&&<p className="text-xs text-amber-800">Selected source types not cited in the answer: {result.missing_cited_source_kinds.join(', ')}</p>}
   {mixed&&result.legal_review_issue_codes?.length>0&&<p className="text-xs text-amber-800">Review signals: {result.legal_review_issue_codes.join(', ')}</p>}
   {result.rejected_unavailable_citation_count>0&&<p className="text-xs text-amber-800">
    {result.rejected_unavailable_citation_count} citation(s) were unavailable in the selected evidence.
   </p>}
   {result.issue_triage&&<div data-testid="assistant-audit-issue-triage" className="rounded-md border border-[#e5d8bb] bg-white p-2 space-y-1">
    <p className="font-semibold text-xs">Automated issue candidates: {result.issue_triage.issue_candidate_count}</p>
    <p className="text-[11px] text-[#64748b]">These candidates are not independently confirmed errors.</p>
    {result.issue_triage.issue_candidates.map((issue,i)=><p key={issue.category+issue.code+i} className="text-xs">{issue.category.replaceAll('_',' ')}: {issue.code.replaceAll('_',' ')}</p>)}
    {result.issue_triage.issue_candidate_count>0&&<button type="button" className="intel-ghost text-xs"
     data-testid="assistant-add-audit-register" onClick={addToRegister}>Add candidates to session register</button>}
   </div>}
   {(result.checks||[]).map(c=><p key={c.id} className="text-xs">
    <strong>{c.id.replaceAll('_',' ')} — {c.status}</strong>: {c.reason}
   </p>)}
   <p className="text-[11px] text-[#876532]">
    This is a deterministic source check, not an accuracy score or legal approval.
    The source's original claims remain unverified; independent officer assessment is required.
   </p>
  </div>}
  <div data-testid="assistant-qa-issue-register" className="border-t border-[#d9e2e9] pt-2 space-y-2">
   <p className="text-xs font-semibold">Session-only QA register · {register.length}/30</p>
   <p className="text-[11px] text-[#64748b]">Entries are deduplicated by source IDs and issue codes. They are lost on page refresh; no answer or source text is stored.</p>
   {registerError&&<p role="alert" className="text-xs text-red-700">{registerError}</p>}
   {register.length>0&&<div className="flex flex-wrap gap-2">
    <button type="button" className="intel-ghost text-xs" data-testid="assistant-export-qa-issue-register" onClick={exportRegister}>Export sanitized issue list (.json)</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>setRegister([])}>Clear register</button>
   </div>}
   {register.slice(-5).map(x=><p className="text-xs text-[#52647a]" key={x.key}>
    {x.source_ids.join(', ')} · {x.issue_count} candidate(s)</p>)}
  </div>
 </div>
}
