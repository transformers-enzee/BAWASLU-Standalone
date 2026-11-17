import {useState} from 'react';
import {addAnswerAuditFindings,exportAnswerAuditIssueRegister} from '@/lib/assistantAuditIssueRegister';
import SavedReplyReviewWorksheet from './SavedReplyReviewWorksheet';

export default function AssistantSavedReplyAudit({disabled=false}){
 const [items,setItems]=useState([]);
 const [selected,setSelected]=useState('');
 const [batchSelected,setBatchSelected]=useState([]);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [audit,setAudit]=useState(null);
 const [register,setRegister]=useState([]);
 const [batch,setBatch]=useState(null);
 const [notice,setNotice]=useState('');
 const [pilot,setPilot]=useState(null);
 const [handoff,setHandoff]=useState(null);
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
 async function exportPilotHandoff(){
  setError('');setNotice('');setLoading(true);
  try{
   const data=await request('saved-reply-reviews/pilot-handoff');
   if(data.schema!=='BAWASLU_OWNED_PILOT_HANDOFF_V1634')
    throw Error('Unknown handoff format');
   setHandoff(data);
   const contents=JSON.stringify(data,null,2);
   const blob=new Blob([contents],{type:'application/json;charset=utf-8'});
   const url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download='BAWASLU-owned-pilot-handoff-v1634.json';a.click();
   setTimeout(()=>URL.revokeObjectURL(url),10000);
   setNotice('Sanitized owner-scoped pilot handoff exported. No accuracy or legal sign-off was inferred.');
  }catch(e){setError(e.message||'Pilot handoff unavailable')}
  finally{setLoading(false)}
 }
 async function loadPilot(){
  setLoading(true);setError('');setNotice('');setAudit(null);setBatch(null);setHandoff(null);
  try{
   const data=await request('saved-reply-reviews/pilot-queue');
   if(data.schema!=='BAWASLU_OWNED_SAVED_REPLY_PILOT_QUEUE_V1633')
    throw Error('Unknown pilot inventory format');
   setPilot(data);setItems(data.candidates||[]);
   setSelected('');setBatchSelected([]);
   setNotice('Pilot queue loaded for your account. Source permissions will be rechecked during audit.');
  }catch(e){setError(e.message||'Pilot queue unavailable')}
  finally{setLoading(false)}
 }
 function selectPilotBatch(){
  if(!pilot)return;
  const eligible=items.filter(x=>x.eligible&&![
   'EVIDENCE_CHECKED_NO_FURTHER_ACTION','INELIGIBLE_FOR_AUDIT'
  ].includes(x.pilot_review_state)).slice(0,5);
  setBatchSelected(eligible.map(x=>x.thread_id+':'+x.answer_message_index));
  setNotice('Selected up to five eligible replies by pilot workflow status. This is not random sampling.');
  setBatch(null);
 }
 async function load(){
  setError('');setAudit(null);setBatch(null);setLoading(true);setSelected('');setBatchSelected([]);setPilot(null);setHandoff(null);
  try{
   const data=await request('saved-reply-candidates');
   if(data.schema!=='BAWASLU_SAVED_REPLY_CANDIDATES_V1616')throw Error('Unknown reply inventory format');
   setItems(data.candidates||[]);
  }catch(e){setError(e.message||'Could not load owned replies')}
  finally{setLoading(false)}
 }
 function toggleBatch(item){
  const key=item.thread_id+':'+item.answer_message_index;
  setBatchSelected(previous=>{
   if(previous.includes(key))return previous.filter(x=>x!==key);
   if(previous.length>=5)return previous;
   return [...previous,key];
  });
  setBatch(null);setNotice('');
 }
 async function runBatch(){
  const selections=batchSelected.map(key=>items.find(x=>x.thread_id+':'+x.answer_message_index===key))
   .filter(Boolean)
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
  <button type="button" className="intel-ghost text-xs" data-testid="assistant-load-pilot-review-queue"
   disabled={disabled||loading} onClick={loadPilot}>Load my pilot review queue</button>
  {pilot&&<div className="text-xs text-[#60748a]" data-testid="assistant-pilot-review-summary">
   <p className="font-semibold">Pilot readiness: {pilot.candidate_count} owned saved replies, {pilot.eligible_count} eligible for audit.</p>
   {Object.entries(pilot.pilot_state_counts||{}).map(([state,count])=>
    <p key={state}>{state.replaceAll('_',' ').toLowerCase()}: {count}</p>)}
   <p>No cross-officer inventory, factual accuracy score, or fresh source authorization at listing time.</p>
   <button type="button" className="intel-ghost text-xs" data-testid="assistant-export-pilot-handoff"
    disabled={loading||disabled} onClick={exportPilotHandoff}>Export sanitized pilot handoff</button>
   <p>Handoff includes only a bounded inventory of your own saved reply metadata; it is not all historical replies and does not verify model accuracy or legal acceptance.</p>
   <button type="button" className="intel-ghost text-xs" data-testid="assistant-select-pilot-batch"
    disabled={loading||disabled||!pilot.recommended_next_batch_count}
    onClick={selectPilotBatch}>Select next eligible batch (up to 5)</button>
  </div>}
  {handoff&&<p data-testid="assistant-pilot-handoff-summary" className="text-xs text-[#60748a]">
   Exported {handoff.inventory_count} owned reply statuses · {handoff.followup_required_count} follow-up required · {handoff.blocked_or_recheck_count} blocked/recheck · {handoff.evidence_checked_no_action_count} evidence-checked no-action proposed.
  </p>}
  {items.length>0&&<div className="space-y-2">
   <p className="text-[11px] text-[#60748a]">
    Choose up to five saved replies for the batch ({batchSelected.length}/5 selected).
    An ineligible reply can be included to document its reason code; it will not
    bypass evidence authorization. No answers are generated and no accuracy score is inferred.
   </p>
   <div data-testid="assistant-batch-selection" className="max-h-44 overflow-auto space-y-1 rounded-md border border-[#d9e2e9] bg-white p-2">
    {items.map(x=>{
     const key=x.thread_id+':'+x.answer_message_index;
     const checked=batchSelected.includes(key);
     return <label key={key} className="flex items-start gap-2 text-xs">
      <input type="checkbox" checked={checked}
       disabled={disabled||loading||(!checked&&batchSelected.length>=5)}
       onChange={()=>toggleBatch(x)}/>
      <span>{x.thread_id.slice(0,8)} · reply {x.answer_message_index+1} ·
       {' '}{x.saved_source_count} replay sources · {x.cited_only_source_count||0} cited-only · {x.eligible?'Eligible for recheck':x.reason_code}
       {x.pilot_review_state&&' · Pilot: '+x.pilot_review_state.replaceAll('_',' ').toLowerCase()}</span>
     </label>;
    })}
   </div>
   <button type="button" className="intel-ghost text-xs"
    data-testid="assistant-run-saved-reply-batch"
    disabled={disabled||loading||batchSelected.length===0}
    onClick={runBatch}>{loading?'Checking…':'Audit '+batchSelected.length+' selected saved replies'}</button>
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
   <p className="text-[11px] text-[#60748a]">{batch.selected_reply_count} explicitly selected replies. No random or representative sampling.</p>
   {Object.entries(batch.reason_code_counts||{}).map(([code,count])=>
    <p className="text-xs text-amber-800" key={code}>{code.replaceAll('_',' ')}: {count} reply(s)</p>)}
   {Object.entries(batch.review_route_counts||{}).map(([code,count])=>
    <p className="text-xs text-[#60748a]" key={code}>
     {count} reply/replies assigned review step: {code.replaceAll('_',' ').toLowerCase()} (suggested only).
    </p>)}
   {Object.entries(batch.citation_coverage_counts||{}).map(([code,count])=>
    <p className="text-xs text-amber-800" key={code}>
     {count} audited reply/replies: {code.replaceAll('_',' ').toLowerCase()} — attribution format review only.
    </p>)}
   {batch.source_unavailable_review_count>0&&<p className="text-xs text-amber-800">
    {batch.source_unavailable_review_count} reply/replies could not be checked using current accessible evidence; this is not a confirmed answer error.
   </p>}
   <p className="text-[11px] text-[#876532]">
    Counts refer only to this bounded, self-selected session; warnings are not
    verified AI errors, legal conclusions or a representative accuracy score.
   </p>
   {Object.entries(batch.issue_category_occurrences||{}).map(([category,count])=>
    <p className="text-xs" key={category}>{category.replaceAll('_',' ')}:
     {' '}{count} automated warning occurrence(s)</p>)}
   {(batch.results||[]).map(x=><p className="text-xs" key={x.thread_id+':'+x.answer_message_index}>
    Saved thread {x.thread_id.slice(0,8)}, reply {x.answer_message_index+1}:
    {' '}{x.status==='AUDITED'?x.issue_candidate_count+' warning candidate(s) · '+(x.cited_only_source_count||0)+' cited-only sources rechecked':x.reason_code}
    {' · Suggested review: '+(x.review_route||'not available').replaceAll('_',' ').toLowerCase()}
   </p>)}
   {batch.results?.some(x=>x.status==='AUDITED'&&x.issue_candidate_count>0)&&
    <button type="button" className="intel-ghost text-xs"
     data-testid="assistant-save-batch-audit-candidates" onClick={keepBatch}>
     Add batch warnings to session issue register
    </button>}
  </div>}
  {batch&&<SavedReplyReviewWorksheet key={'batch:'+batch.results.map(x=>x.thread_id+':'+x.answer_message_index).join('|')} results={batch.results||[]}/>}
  {audit&&<SavedReplyReviewWorksheet key={'single:'+audit.thread_id+':'+audit.answer_message_index} results={[{thread_id:audit.thread_id,answer_message_index:audit.answer_message_index,status:'AUDITED',review_route:audit.review_route}]}/>}
  {audit&&<div data-testid="assistant-saved-reply-audit-result" className="space-y-2">
   <p className="text-xs font-semibold">
    {audit.fresh_source_scope_count} current sources reauthorized · {audit.audit.cited_authorized_ids?.length||0} cited
   </p>
   <p className="text-xs">Automated warning candidates: {audit.audit.issue_triage?.issue_candidate_count||0}</p>
   {audit.review_route&&<p className="text-xs text-[#60748a]">
    Suggested officer step: {audit.review_route.replaceAll('_',' ').toLowerCase()}. This is not an accuracy finding.
   </p>}
   {audit.historical_citation_coverage&&<p className="text-xs text-amber-800">
    Historical citation coverage: {audit.historical_citation_coverage.replaceAll('_',' ').toLowerCase()}.
    This is an attribution-format finding, not a factual-accuracy verdict.
   </p>}
   {audit.cited_only_source_count>0&&<p className="text-xs text-[#876532]">
    {audit.cited_only_source_count} cited source(s) were missing from the historical cards and individually reauthorized for review.
   </p>}
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
