import {useState} from 'react';
import {ThumbsUp,ThumbsDown} from 'lucide-react';
export default function AssistantResponseFeedback({threadId,messageIndex,disabled=false}){
 const [rating,setRating]=useState(''),[note,setNote]=useState(''),[open,setOpen]=useState(false);
 const [busy,setBusy]=useState(false),[status,setStatus]=useState('');
 async function save(choice){
  if(!threadId||disabled)return;
  setRating(choice);setBusy(true);setStatus('');
  try{
   const token=window.localStorage.getItem('bawaslu_access_token');
   if(!token)throw Error('Sign in before submitting feedback.');
   const res=await fetch('/api/assistant-feedback',{
    method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify({thread_id:threadId,message_index:messageIndex,rating:choice,note:note.slice(0,600)})
   });
   const body=await res.json().catch(()=>({}));
   if(!res.ok)throw Error(body.detail||'Feedback was not saved');
   setStatus('Feedback saved for review. No official action was taken.');
   setOpen(choice==='NEEDS_IMPROVEMENT');
  }catch(e){setStatus(String(e.message||e))}
  finally{setBusy(false)}
 }
 return <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 text-xs" data-testid="smart-radar-response-feedback">
  <div className="flex flex-wrap items-center gap-2 text-slate-700">
   <span>Was this response useful?</span>
   <button type="button" className={'intel-ghost text-xs '+(rating==='HELPFUL'?'border-teal-600':'')} disabled={disabled||busy||!threadId}
    onClick={()=>save('HELPFUL')} aria-label="Helpful response"><ThumbsUp size={13}/> Helpful</button>
   <button type="button" className={'intel-ghost text-xs '+(rating==='NEEDS_IMPROVEMENT'?'border-amber-600':'')} disabled={disabled||busy||!threadId}
    onClick={()=>{setOpen(true);setRating('NEEDS_IMPROVEMENT')}} aria-label="Response needs improvement"><ThumbsDown size={13}/> Needs improvement</button>
  </div>
  {open&&<div className="flex flex-wrap gap-2">
   <input className="intel-input min-w-[200px] flex-1 text-xs" maxLength={600} value={note} disabled={busy}
     aria-label="Optional feedback reason" placeholder="What was missing or unsupported?" onChange={e=>setNote(e.target.value)}/>
   <button type="button" className="intel-button text-xs" disabled={busy} onClick={()=>save('NEEDS_IMPROVEMENT')}>Save feedback</button>
  </div>}
  {status&&<p role="status" className="text-xs text-slate-600">{status}</p>}
 </div>;
}
