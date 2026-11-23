import {useState} from 'react';
export default function AssistantAttachmentCitation({sourceId,threadId}){
 const [content,setContent]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const match=/^ATT-([a-f0-9]{32})-S(\d+)$/.exec(sourceId||'');
 if(!match)return <span>[{sourceId}]</span>;
 const raw=match[1],id=[raw.slice(0,8),raw.slice(8,12),raw.slice(12,16),raw.slice(16,20),raw.slice(20)].join('-');
 async function open(){
  if(!threadId){setError('Historical citation requires reopening its authorized conversation.');return}
  if(content){setContent(null);return}
  setBusy(true);setError('');
  try{
   const token=window.localStorage.getItem('bawaslu_access_token');
   if(!token)throw Error('Sign in to inspect attached source text.');
   const res=await fetch('/api/assistant-attachments/'+encodeURIComponent(threadId)+'/'+id+
     '/content?section='+encodeURIComponent(match[2]),{
     headers:{Authorization:'Bearer '+token},cache:'no-store'
   });
   const d=await res.json().catch(()=>({}));
   if(!res.ok)throw Error(d.detail||'Source unavailable or permission changed');
   setContent(d);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <span className="inline-block align-middle">
  <button type="button" onClick={open} disabled={busy}
   className="rounded border border-teal-300 px-1 py-0.5 text-[11px] font-semibold text-teal-800 hover:bg-teal-50"
   aria-label={'Open authorized attachment citation '+sourceId}>[{sourceId}]</button>
  {content&&<div className="my-2 max-w-[650px] rounded-lg border border-slate-200 bg-white p-3 text-left text-xs">
   <p className="font-semibold">{content.title} · {content.section}</p>
   {content.url&&<a href={content.url} target="_blank" rel="noopener noreferrer" className="block break-all text-teal-800 underline">{content.url}</a>}
   <p className="mt-1 font-medium text-amber-800">User-supplied source · not independently verified or accepted into a case record</p>
   <p className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap">{content.text}</p>
  </div>}
  {error&&<span role="alert" className="ml-1 text-xs text-red-700">{error}</span>}
 </span>;
}
