import {useState} from 'react';
import {addAnswerAuditFindings,exportAnswerAuditIssueRegister} from '@/lib/assistantAuditIssueRegister';

export default function AssistantSavedReplyAudit({disabled=false}){
 const [items,setItems]=useState([]);
 const [selected,setSelected]=useState('');
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [audit,setAudit]=useState(null);
 const [register,setRegister]=useState([]);
 const [batch,setBatch]=useState(null);
 const [notice,setNotice]=useState('');
 async function request(path,body){
  const token=window.localStorage.getItem('bawaslu_access_token')||'';
  if(!token)throw Error('An authorized session is required');
  const response=await fetch('/api/assistant-evaluation/'+path,{
   method:body?'POST':'GET',cache:'no-store',
   headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
   ...(body?{body:JSON.stringify(body)}:{})
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Could not inspect saved answers.');
  return data;
 }
 async function load(){
  setError('');setAudit(null);setBatch(null);setLoading(true);setSelected('');
  try{
   const data=await request('saved-reply-candidates');
   if(data.schema!=='BAWASLU_SAVED_REPLY_CANDIDATES_V1616')throw Error('Unknown reply inventory format');
   setItems(data.candidates||[]);
  }catch(e){setError(e.message||'Could not load owned replies')}
  finally{setLoading(false)}
 }
 async function runBatch(){
  const selections=items.filter(x=>x.eligible).slice(0,5)
   .map(x=>({thread_id:x.thread_id,answer_message_index:x.answer_message_index}));
  if(!selections.length||loading)return;
  setLoading(true);setError('');setBatch(null);setNotice('');
  try{
   const data=await request('saved-reply-batch-audit',{selections});
   if(data.schema!=='BAWASLU_SAVED_REPLY_BATCH_AUDIT_V1618')
    throw Error('Unknown batch audit response format');
   setBatch(data);
  }catch(e){setError(e.message||'Batch audit unavailable')}
  finally{setLoading(false)}
 }
 function keepBatch(){
  try{
   setRegister(previous=>{
    let rows=previous;
    for(const result of batch.results||[]){
     if(result.status!=='AUDITED'||!(result.issue_candidate_count>0))continue;
     rows=addAnswerAuditFindings(rows,{
      source_record_ids:result.source_record_ids,
      issue_triage:result.issue_triage});
    }
    return rows;
   });
   setNotice('Unverified warning candidates added to the session register.');
  }catch(e){setError(e.message||'Cannot capture batch candidates')}
 }
 async function run(){
  const row=items.find(x=>x.thread_id+':'+x.answer_message_index===selected);
  if(!row?.eligible||loading)return;
  setLoading(true);setError('');setAudit(null);
  try{
   const data=await request('saved-reply-audit',{
    thread_id:row.thread_id,answer_message_index:row.answer_message_index});
   if(data.schema!=='BAWASLU_SAVED_REPLY_AUDIT_V1616'||
      data.audit?.schema!=='BAWASLU_MIXED_ANSWER_AUDIT_V1609')
    throw Error('Unknown replay audit result');
   setAudit(data);
  }catch(e){setError(e.message||'Saved reply audit unavailable')}
  finally{setLoading(false)}
 }
 function keep(){
  try{setRegister(previous=>addAnswerAuditFindings(previous,audit.audit));
   setNotice('Warning candidates added to this local session register.')}
  catch(e){setError(e.message||'Could not add candidates')}
 }
 function exportIssues(){
  try{
   const blob=new Blob([exportAnswerAuditIssueRegister(register)],
    {type:'application/json;charset=utf-8'});
   const url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download='BAWASLU-saved-reply-audit-candidates-v1616.json';a.click();
   setTimeout(()=>URL.revokeObjectURL(url),10000);setNotice('Sanitized JSON export generated.');
  }catch(e){setError(e.message||'Could not export register')}
 }
 const chosen=items.find(x=>x.thread_id+':'+x.answer_message_index===selected);
 return <section data-testid="assistant-saved-reply-evaluation"
  className="rounded-lg border border-[#d5e1ea] bg-[#f8fbfd] p-3 space-y-2">
  <p className="text-xs font-semibold">Audit an existing saved Assistant reply (no new AI call)</p>
  <p className="text-[11px] text-[#60748a]">
   Shows only replies from your own saved conversations. No answer text is transferred to
   this panel. Each selected source is checked again against current access rights.
   Saved threads are user-editable, so this does not establish authentic model provenance,
   semantic accuracy, legal correctness or client acceptance.
  </p>
  <button type="button" className="intel-ghost text-xs"
   data-testid="assistant-load-saved-replies" disabled={disabled||loading}
   onClick={load}>{loading?'Checking…':'Find my saved replies'}</button>
  {items.length>0&&<div className="space-y-2">
   <p className="text-[11px] text-[#60748a]">
    Bulk audit uses up to five eligible saved replies from the list. Each is
    rechecked under current access rights; unavailable sources remain failures
    rather than being skipped as passing answers.
   </p>
   <button type="button" className="intel-ghost text-xs"
    data-testid="assistant-run-saved-reply-batch"
    disabled={disabled||loading||!items.some(x=>x.eligible)}
    onClick={runBatch}>{loading?'Checking…':'Audit up to five saved replies'}</button>
   <label htmlFor="assistant-saved-reply-choice" className="block text-xs font-semibold">
    Saved reply to audit
   </label>
   <select id="assistant-saved-reply-choice" data-testid="assistant-saved-reply-choice"
    className="w-full rounded-md border border-[#ccd7df] bg-white px-3 py-2 text-xs"
    value={selected} disabled={disabled||loading}
    onChange={e=>{setSelected(e.target.value);setAudit(null);setError('');setNotice('')}}>
    <option value="">Choose an answer by saved thread and message position</option>
    {items.map(x=><option key={x.thread_id+':'+x.answer_message_index}
     value={x.thread_id+':'+x.answer_message_index}>
     {x.thread_id.slice(0,8)} · message {x.answer_message_index+1} · {x.saved_source_count} selected sources · {x.eligible?'Ready for access check':x.reason_code}
    </option>)}
   </select>
   {chosen&&!chosen.eligible&&<p className="text-xs text-amber-800">
    This saved reply cannot be audited automatically: {chosen.reason_code}. No partial evidence was silently substituted.
   </p>}
   {chosen?.eligible&&<button type="button" className="intel-ghost text-xs"
    data-testid="assistant-run-saved-reply-audit" onClick={run} disabled={disabled||loading}>
    Reauthorize evidence and audit this saved reply
   </button>}
  </div>}
  {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
  {notice&&<p role="status" className="text-xs text-[#146347]">{notice}</p>}
  {batch&&<div data-testid="assistant-saved-reply-batch-result"
    className="rounded-md border border-[#d9e2e9] bg-white p-2 space-y-2">
   <p className="text-xs font-semibold">Batch review: {batch.audited} audited,
    {' '}{batch.ineligible} ineligible, {batch.unavailable} unavailable</p>
   <p className="text-[11px] text-[#876532]">
    Counts refer only to this bounded, self-selected session; warnings are not
    verified AI errors, legal conclusions or a representative accuracy score.
   </p>
   {Object.entries(batch.issue_category_occurrences||{}).map(([category,count])=>
    <p className="text-xs" key={category}>{category.replaceAll('_',' ')}:
     {' '}{count} automated warning occurrence(s)</p>)}
   {(batch.results||[]).map(x=><p className="text-xs" key={x.thread_id+':'+x.answer_message_index}>
    Saved thread {x.thread_id.slice(0,8)}, reply {x.answer_message_index+1}:
    {' '}{x.status==='AUDITED'?x.issue_candidate_count+' warning candidate(s)':x.reason_code}
   </p>)}
   {batch.results?.some(x=>x.status==='AUDITED'&&x.issue_candidate_count>0)&&
    <button type="button" className="intel-ghost text-xs"
     data-testid="assistant-save-batch-audit-candidates" onClick={keepBatch}>
     Add batch warnings to session issue register
    </button>}
  </div>}
  {audit&&<div data-testid="assistant-saved-reply-audit-result" className="space-y-2">
   <p className="text-xs font-semibold">
    {audit.fresh_source_scope_count} current sources reauthorized · {audit.audit.cited_authorized_ids?.length||0} cited
   </p>
   <p className="text-xs">Automated warning candidates: {audit.audit.issue_triage?.issue_candidate_count||0}</p>
   {(audit.audit.issue_triage?.issue_candidates||[]).map((x,i)=>
    <p key={x.code+i} className="text-xs">{x.category.replaceAll('_',' ')}: {x.code.replaceAll('_',' ')}</p>)}
   {(audit.audit.issue_triage?.issue_candidate_count||0)>0&&<button type="button"
    className="intel-ghost text-xs" onClick={keep}
    data-testid="assistant-record-saved-reply-candidates">Add warning candidates to session register</button>}
   <p className="text-[11px] text-[#876532]">
    Automated source attribution only; no human-confirmed accuracy, legal sign-off or client approval.
   </p>
  </div>}
  {register.length>0&&<div className="border-t border-[#d9e2e9] pt-2 space-y-1">
   <p className="text-xs">Session QA issues: {register.length} distinct issue sets</p>
   <button type="button" className="intel-ghost text-xs"
    data-testid="assistant-export-saved-reply-issues" onClick={exportIssues}>
    Export sanitized issue JSON
   </button>
  </div>}
 </section>;
}
