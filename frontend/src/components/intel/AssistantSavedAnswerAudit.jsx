import {useEffect,useState} from 'react';

export default function AssistantSavedAnswerAudit({item,disabled=false}){
 const [answer,setAnswer]=useState('');
 const [busy,setBusy]=useState(false);
 const [result,setResult]=useState(null);
 const [error,setError]=useState('');
 useEffect(()=>{setAnswer('');setResult(null);setError('')},[item?.source_record_id]);
 async function run(){
  if(busy||disabled||!item?.source_record_id||!answer.trim())return;
  setBusy(true);setError('');setResult(null);
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw Error('An authorized session is required.');
   const response=await fetch('/api/assistant-evaluation/saved-answer-audit',{
    method:'POST',cache:'no-store',
    headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
    body:JSON.stringify({source_ids:[item.source_record_id],
                         question:item.question,answer})
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Source audit failed.');
   if(data.schema!=='BAWASLU_SAVED_ANSWER_AUDIT_V1608')throw Error('Unknown audit response schema.');
   setResult(data);
  }catch(e){setError(e.message||'Could not audit the submitted answer.')}
  finally{setBusy(false)}
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
   {busy?'Checking…':'Check against saved source (no AI call)'}
  </button>
  {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
  {result&&<div data-testid="assistant-saved-answer-audit-result" className="space-y-2">
   <p className="text-xs font-semibold">Audit: {result.review_required_checks} checks need review · {result.cited_count} authorized citation(s)</p>
   {result.rejected_unavailable_citation_count>0&&<p className="text-xs text-amber-800">
    {result.rejected_unavailable_citation_count} citation(s) were unavailable in the selected evidence.
   </p>}
   {(result.checks||[]).map(c=><p key={c.id} className="text-xs">
    <strong>{c.id.replaceAll('_',' ')} — {c.status}</strong>: {c.reason}
   </p>)}
   <p className="text-[11px] text-[#876532]">
    This is a deterministic source check, not an accuracy score or legal approval.
    The source's original claims remain unverified; independent officer assessment is required.
   </p>
  </div>}
 </div>
}
