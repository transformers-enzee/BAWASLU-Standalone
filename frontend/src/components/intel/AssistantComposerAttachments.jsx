import {useEffect,useRef,useState} from 'react';
import {Paperclip,FileUp,Link2,X,ExternalLink,Loader2} from 'lucide-react';

function token(){
 const value=window.localStorage.getItem('bawaslu_access_token');
 if(!value)throw Error('Your login session has expired. Sign in again.');
 return value;
}
async function call(path,method='GET',body=null,isFile=false){
 const response=await fetch('/api/assistant-attachments'+path,{
  method,cache:'no-store',
  headers:{Authorization:'Bearer '+token(),...(!isFile&&body?{'Content-Type':'application/json'}:{})},
  ...(body?{body:isFile?body:JSON.stringify(body)}:{})
 });
 const result=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Attachment request failed ('+response.status+')');
 return result;
}
export function attachmentRequest(path,method='GET',body=null,isFile=false){
 return call(path,method,body,isFile);
}
export default function AssistantComposerAttachments({
 threadId,ensureThread,items,setItems,disabled=false,selected=true
}){
 const [open,setOpen]=useState(false),[link,setLink]=useState(''),[working,setWorking]=useState([]),[failure,setFailure]=useState('');
 const inputRef=useRef(null);
 useEffect(()=>{
  let alive=true;
  setItems([]);
  if(threadId)call('/'+encodeURIComponent(threadId)).then(res=>{
   if(alive)setItems(res.attachments||[]);
  }).catch(err=>{if(alive)setFailure(err.message)});
  return()=>{alive=false};
 },[threadId,setItems]);
 const busy=working.length>0;
 async function saveFile(file){
  const id=crypto.randomUUID();
  setWorking(a=>[...a,{id,title:file.name,status:'SCANNING_AND_EXTRACTING'}]);
  try{
   if(!['.pdf','.docx','.txt'].some(x=>file.name.toLowerCase().endsWith(x)))throw Error('Unsupported file type. Choose PDF, DOCX or TXT.');
   if(file.size>5*1024*1024)throw Error('File exceeds 5 MB.');
   const session=await ensureThread();
   const body=new FormData();body.append('thread_id',session);body.append('file',file);
   const result=await call('/upload','POST',body,true);
   setItems(old=>old.some(x=>x.id===result.id)?old:[...old,result]);
   setFailure('');
  }catch(e){setFailure(file.name+': '+e.message)}
  finally{setWorking(a=>a.filter(x=>x.id!==id))}
 }
 async function saveLink(){
  if(!link.trim()||disabled)return;
  const id=crypto.randomUUID();
  setWorking(a=>[...a,{id,title:link,status:'RETRIEVING'}]);
  try{
   const value=new URL(link.trim());
   if(value.protocol!=='https:')throw Error('Only HTTPS links are permitted');
   const session=await ensureThread();
   const result=await call('/link','POST',{thread_id:session,url:value.toString()});
   setItems(old=>old.some(x=>x.id===result.id)?old:[...old,result]);
   setLink('');setOpen(false);setFailure('');
  }catch(e){setFailure(e.message)}
  finally{setWorking(a=>a.filter(x=>x.id!==id))}
 }
 async function remove(item){
  try{
   await call('/'+encodeURIComponent(item.thread_id)+'/'+encodeURIComponent(item.id),'DELETE');
   setItems(old=>old.filter(x=>x.id!==item.id));setFailure('');
  }catch(e){setFailure('Removal failed: '+e.message)}
 }
 return <div className="w-full space-y-2" data-testid="smart-radar-attachment-composer">
  <div className="flex flex-wrap items-center gap-2">
   <button type="button" className="intel-ghost text-xs" disabled={disabled} aria-expanded={open}
    onClick={()=>setOpen(x=>!x)}><Paperclip size={15}/> Attach</button>
   <span className="text-[11px] text-slate-600">Private to this conversation · up to 8 sources · PDF, DOCX, TXT or HTTPS link</span>
  </div>
  {open&&<div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
   <div className="flex flex-wrap gap-2">
    <button type="button" className="intel-ghost text-xs" disabled={disabled||busy} onClick={()=>inputRef.current?.click()}><FileUp size={14}/> Upload document</button>
    <input ref={inputRef} type="file" className="sr-only" accept=".pdf,.docx,.txt" multiple
     onChange={e=>{const files=Array.from(e.target.files||[]);e.target.value='';files.forEach(saveFile)}}/>
    <label className="flex min-w-[210px] flex-1 items-center gap-2 text-xs"><Link2 size={14}/><input type="url" value={link} className="intel-input flex-1" placeholder="https://public.example/page" disabled={disabled} onChange={e=>setLink(e.target.value)}/></label>
    <button type="button" className="intel-button text-xs" disabled={disabled||!link.trim()} onClick={saveLink}>Add link</button>
   </div>
   <p className="text-xs text-slate-600">Documents are malware-scanned and text-extracted before use. Password-protected and scanned PDFs may need an unlocked/text-readable copy. A link may be blocked, require login or not contain readable HTML; upload the file or paste a short excerpt instead.</p>
  </div>}
  {(items.length>0||working.length>0)&&<div className="flex flex-wrap gap-2" aria-label="Attachments for this conversation">
   {items.map(item=><div key={item.id} className="flex max-w-full items-center gap-2 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-xs" data-testid="assistant-attachment-ready">
    {item.kind==='LINK'?<Link2 size={13}/>:<FileUp size={13}/>}
    <span className="max-w-[220px] truncate" title={item.title}>{item.title}</span>
    <span className="text-teal-800">Ready · {item.sections} sections</span>
    {item.url&&<a href={item.url} target="_blank" rel="noopener noreferrer" aria-label="Open original public page"><ExternalLink size={13}/></a>}
    <button type="button" aria-label={'Remove '+item.title} disabled={disabled} onClick={()=>remove(item)}><X size={14}/></button>
   </div>)}
   {working.map(item=><div key={item.id} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"><Loader2 size={13} className="animate-spin"/>{item.title} · {item.status}</div>)}
  </div>}
  {failure&&<div role="alert" className="text-xs text-red-700">{failure}</div>}
  {!selected&&items.length>0&&<p role="status" className="text-xs text-amber-800">Conversation attachments are currently deselected from AI retrieval. They remain private and can be re-enabled.</p>}
  {busy&&<p role="status" className="text-xs text-slate-700">Attachment processing in progress. Send is blocked until processing completes.</p>}
 </div>;
}
