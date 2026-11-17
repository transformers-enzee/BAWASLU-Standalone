import {useState,useEffect} from 'react';
import {auditReplyKey,createReviewEntry,exportReviewWorksheet} from '@/lib/savedReplyReviewWorksheet';

const LABELS={
 PENDING_REVIEW:'Pending review',
 EVIDENCE_CHECK_IN_PROGRESS:'Evidence check in progress',
 REVIEW_BLOCKED:'Review blocked or evidence unavailable',
 EVIDENCE_CHECKED_FOLLOWUP_NEEDED:'Evidence checked — needs follow-up',
 EVIDENCE_CHECKED_NO_FURTHER_ACTION:'Evidence checked — no further action proposed'
};
export default function SavedReplyReviewWorksheet({results=[]}){
 const [decisions,setDecisions]=useState({});
 const [checked,setChecked]=useState({});
 const [notice,setNotice]=useState('');
 const [error,setError]=useState('');
 const [saved,setSaved]=useState({});
 const [canSave,setCanSave]=useState(false);
 const [saving,setSaving]=useState(false);
 const [summary,setSummary]=useState(null);
 const [history,setHistory]=useState({});
 const [historyLoading,setHistoryLoading]=useState('');
 async function server(body){
  const token=window.localStorage.getItem('bawaslu_access_token')||'';
  if(!token)throw Error('Authorized session required');
  const response=await fetch('/api/assistant-evaluation/saved-reply-reviews',{
   method:body?'POST':'GET',cache:'no-store',
   headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
   ...(body?{body:JSON.stringify(body)}:{})
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(data.detail||'Review service unavailable');
  return data;
 }
 useEffect(()=>{
  let active=true;
  server().then(data=>{
   if(!active)return;
   setSaved(Object.fromEntries((data.records||[]).map(x=>[auditReplyKey(x),x])));
   setSummary(data);setCanSave(true);
  }).catch(()=>{if(active)setCanSave(false)});
  return ()=>{active=false};
 },[]);
 async function saveProgress(item){
  const key=auditReplyKey(item);
  const state=decisions[key]||saved[key]?.review_state||'PENDING_REVIEW';
  const evidence=Object.hasOwn(checked,key)?checked[key]:!!saved[key]?.evidence_checked;
  setError('');setNotice('');setSaving(true);
  try{
   createReviewEntry(item,state,evidence);
   if(saved[key]?.saved_reply_changed)throw Error('Saved reply changed; re-audit before updating');
   const response=await server({
    thread_id:item.thread_id,answer_message_index:item.answer_message_index,
    review_state:state,evidence_checked:evidence,expected_version:saved[key]?.version||0
   });
   setSaved(previous=>({...previous,[key]:response.record}));
   setHistory(previous=>({...previous,[key]:null}));
   const refreshed=await server();
   setSaved(Object.fromEntries((refreshed.records||[]).map(x=>[auditReplyKey(x),x])));
   setSummary(refreshed);
   setNotice('Review progress saved under your authenticated account. No legal approval given.');
  }catch(e){setError(e.message||'Save failed')}finally{setSaving(false)}
 }
 async function loadHistory(item){
  const key=auditReplyKey(item);
  setError('');setHistoryLoading(key);
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw Error('Authorized session required');
   const url='/api/assistant-evaluation/saved-reply-reviews/'+
    encodeURIComponent(item.thread_id)+'/'+item.answer_message_index+'/history';
   const response=await fetch(url,{headers:{Authorization:'Bearer '+token},cache:'no-store'});
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(data.detail||'History unavailable');
   setHistory(previous=>({...previous,[key]:data.events||[]}));
  }catch(e){setError(e.message||'Unable to inspect history')}
  finally{setHistoryLoading('')}
 }
 if(!results.length)return null;
 const rows=results.slice(0,5);
 function change(item,state){
   const key=auditReplyKey(item);
   setDecisions(previous=>({...previous,[key]:state}));
   setNotice('');setError('');
 }
 function exportLocal(){
   try{
     const entries=rows.map(item=>{
       const key=auditReplyKey(item);
       return createReviewEntry(item,decisions[key]||saved[key]?.review_state||'PENDING_REVIEW',Object.hasOwn(checked,key)?checked[key]:!!saved[key]?.evidence_checked);
     });
     const data=exportReviewWorksheet(entries);
     const blob=new Blob([data],{type:'application/json;charset=utf-8'});
     const url=URL.createObjectURL(blob),a=document.createElement('a');
     a.href=url;a.download='BAWASLU-saved-reply-review-worksheet-v1629.json';a.click();
     setTimeout(()=>URL.revokeObjectURL(url),10000);
     setNotice('Local session worksheet exported; no review was submitted or approved.');
   }catch(e){setError(e.message||'Cannot export review worksheet')}
 }
 return <div data-testid="saved-reply-review-worksheet" className="rounded-md border border-[#d9e2e9] bg-white p-3 space-y-3">
  <p className="text-xs font-semibold">Officer evidence-review worksheet</p>
  <p className="text-[11px] text-[#60748a]">Review original authorized sources before attesting. Eligible reviewers can save progress to their own account. This is operational progress, not formal legal sign-off or an accuracy score.</p>
  {!canSave&&<p className="text-xs text-amber-800">Persistent review requires an active reviewer grant. Local export remains available.</p>}
  {canSave&&summary&&<div data-testid="saved-reply-review-summary" className="text-xs text-[#60748a]">
   My saved reviews: {summary.review_count||0} · current evidence-checked: {summary.completed_current_count||0} · changed/needs recheck: {summary.stale_review_count||0}.
   These are operational progress counts, not model accuracy.
  </div>}
  {rows.map(item=>{
   const key=auditReplyKey(item),state=decisions[key]||saved[key]?.review_state||'PENDING_REVIEW';
   const hasEvidence=Object.hasOwn(checked,key)?!!checked[key]:!!saved[key]?.evidence_checked;
   return <div key={key} className="border-t border-[#e4e9ef] pt-2 space-y-1">
    <p className="text-xs font-medium">Saved thread {item.thread_id.slice(0,8)} · reply {item.answer_message_index+1}</p>
    <p className="text-[11px] text-[#60748a]">{item.status} · suggested: {(item.review_route||'').replaceAll('_',' ').toLowerCase()}</p>
    {saved[key]&&<p className="text-xs text-[#60748a]">Saved: {saved[key].review_state.replaceAll('_',' ')} · v{saved[key].version} · reviewer #{saved[key].reviewer_id}</p>}
    {saved[key]?.saved_reply_changed&&<p className="text-xs text-amber-800">Saved reply changed or became ineligible. Prior evidence-checked status is no longer current; this review cannot be updated until separately reconciled.</p>}
    {saved[key]&&!saved[key]?.saved_reply_changed&&<p className="text-xs text-[#60748a]">Effective state: {(saved[key].effective_review_state||saved[key].review_state).replaceAll('_',' ').toLowerCase()}</p>}
    <label className="flex gap-2 items-start text-xs">
     <input type="checkbox" checked={hasEvidence} disabled={item.status!=='AUDITED'}
      onChange={e=>{
       setChecked(previous=>({...previous,[key]:e.target.checked}));
       if(!e.target.checked&&state.startsWith('EVIDENCE_CHECKED_'))
         setDecisions(previous=>({...previous,[key]:'EVIDENCE_CHECK_IN_PROGRESS'}));
       setNotice('');setError('');
      }}/>
     I personally checked the original evidence available to my account (self-attestation).
    </label>
    <label className="block text-xs">Review progress
     <select data-testid="saved-reply-review-state" className="mt-1 w-full rounded-md border border-[#ccd7df] p-2 text-xs"
      value={state} onChange={e=>change(item,e.target.value)}>
      {Object.entries(LABELS).map(([value,label])=>
       <option key={value} value={value} disabled={value.startsWith('EVIDENCE_CHECKED_')&&(!hasEvidence||item.status!=='AUDITED')}>{label}</option>)}
     </select>
    </label>
    <button type="button" className="intel-ghost text-xs"
     data-testid="save-persistent-saved-reply-review"
     disabled={!canSave||saving||!!saved[key]?.saved_reply_changed}
     onClick={()=>saveProgress(item)}>{saving?'Saving…':'Save progress to account'}</button>
    {saved[key]&&<button type="button" className="intel-ghost text-xs"
     data-testid="open-saved-reply-review-history" disabled={historyLoading===key}
     onClick={()=>loadHistory(item)}>{historyLoading===key?'Loading…':'View review history'}</button>}
    {Array.isArray(history[key])&&<div data-testid="saved-reply-review-event-history" className="text-[11px] text-[#60748a]">
     {history[key].length===0?'No recorded events':history[key].map((event,i)=>
      <p key={event.version+':'+i}>Version {event.version}: {event.from_state.replaceAll('_',' ')} → {event.to_state.replaceAll('_',' ')} · reviewer #{event.actor_user_id}</p>)}
    </div>
   </div>;
  })}
  <button type="button" className="intel-ghost text-xs" data-testid="export-saved-reply-review-worksheet" onClick={exportLocal}>Export sanitized review worksheet</button>
  {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
  {notice&&<p role="status" className="text-xs text-[#146347]">{notice}</p>}
 </div>;
}
