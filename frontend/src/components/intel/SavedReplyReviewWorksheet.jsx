import {useState} from 'react';
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
       return createReviewEntry(item,decisions[key]||'PENDING_REVIEW',!!checked[key]);
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
  <p className="text-xs font-semibold">Officer evidence-review worksheet (session only)</p>
  <p className="text-[11px] text-[#60748a]">Review the original authorized evidence outside this summary before recording an evidence-checked outcome. Entries are not stored on the server, are not formal decisions, and do not verify model accuracy or identity.</p>
  {rows.map(item=>{
   const key=auditReplyKey(item),state=decisions[key]||'PENDING_REVIEW';
   const hasEvidence=!!checked[key];
   return <div key={key} className="border-t border-[#e4e9ef] pt-2 space-y-1">
    <p className="text-xs font-medium">Saved thread {item.thread_id.slice(0,8)} · reply {item.answer_message_index+1}</p>
    <p className="text-[11px] text-[#60748a]">{item.status} · suggested: {(item.review_route||'').replaceAll('_',' ').toLowerCase()}</p>
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
   </div>;
  })}
  <button type="button" className="intel-ghost text-xs" data-testid="export-saved-reply-review-worksheet" onClick={exportLocal}>Export sanitized review worksheet</button>
  {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
  {notice&&<p role="status" className="text-xs text-[#146347]">{notice}</p>}
 </div>;
}
