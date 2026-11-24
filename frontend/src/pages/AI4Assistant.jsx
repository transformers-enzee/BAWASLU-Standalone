import {useRef,useState} from 'react';
import {useOutletContext} from 'react-router-dom';
import {ArrowRight,FileText,Link2,Loader2,Paperclip,Plus,ShieldCheck,Sparkles,Trash2} from 'lucide-react';

const MODES=[['WEB_ONLY','Web only','No SmartRadar database retrieval'],
 ['WEB_SMARTRADAR','Web + SmartRadar','Public research and authorised saved records'],
 ['SMARTRADAR_ONLY','SmartRadar only','Authorised saved records, no public search']];
const PERSPECTIVES=['AUTO','EXECUTIVE','OPERATIONAL','RESEARCH'];
const newId=()=>window.crypto?.randomUUID?.()||'00000000-0000-4000-8000-000000000001';
const token=()=>({Authorization:'Bearer '+(window.localStorage.getItem('bawaslu_access_token')||'')});
async function send(path,options={}){
 const r=await fetch(path,{...options,headers:{...token(),...(options.headers||{})}});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Request failed (HTTP '+r.status+')');
 return d;
}
function Citations({ids,trail}){
 const byId=new Map((trail.sources||[]).map(s=>[s.id,s]));
 return <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">{(ids||[]).map(id=>byId.get(id)).filter(Boolean).map(s=>
  s.url?.startsWith('https://')?<a key={s.id} href={s.resolved_url||s.url} target="_blank" rel="noopener noreferrer"
   className="rounded bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-sky-800 underline">{s.id}</a>:
   <a key={s.id} href={'#ai4-source-'+s.id} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-slate-800 underline">{s.id}</a>)}</span>;
}
function ResearchTrail({data}){
 const t=data.source_trail||{};
 return <details data-testid="ai4-research-trail" className="rounded-xl border border-slate-200 p-3">
  <summary className="cursor-pointer text-sm font-semibold">Research Trail · sources consulted and limitations</summary>
  <div className="mt-3 space-y-2 text-xs text-slate-700">
   <p>Source mode: {data.source_mode?.replaceAll('_',' ')} · Web status: <strong>{t.public_status||'Unavailable'}</strong></p>
   <p>Public pages read: {t.read_public_count??0} · Saved observations: {t.saved_count??0} · Attached excerpts: {t.attached_count??0}</p>
   {t.searched_at&&<p>Search consulted: {t.searched_at} (not continuously monitored)</p>}
   {t.period&&<p>Research period: {t.period.start} to {t.period.end}; publication is not necessarily incident date</p>}
   {!!t.queries?.length&&<p>Queries used: {t.queries.join(' · ')}</p>}
   {(t.warnings||[]).map((w,i)=><p key={i} className="rounded bg-amber-50 p-2 text-amber-900">{w}</p>)}
   {(t.sources||[]).map(s=><div id={'ai4-source-'+s.id} key={s.id} className="scroll-mt-24 rounded-lg border border-slate-200 p-3" data-testid="ai4-source-row">
    <div className="flex flex-wrap justify-between gap-2"><strong>{s.id} · {s.title}</strong>
     <span className="font-medium">{s.read_status==='READ'?'Read':s.read_status==='SAVED_SNAPSHOT'?'Saved snapshot':
      s.read_status==='SNIPPET_ONLY'?'Snippet only — not read':s.read_status==='INACCESSIBLE'?'Inaccessible':'Not read'}</span></div>
    <p className="mt-1">Provenance: {s.basis} · Published: {s.published_at||'unconfirmed'} · Updated: {s.updated_at||'unconfirmed'} · {s.section||'No section'}</p>
    <p>Incident location: {s.location_verified?s.location||'verified':'not established'}{s.duplicate_of?' · Possible duplicate: '+s.duplicate_of:''}</p>
    {s.reason&&<p className="text-amber-900">{s.reason}</p>}
    {s.url?.startsWith('https://')&&<a href={s.resolved_url||s.url} target="_blank" rel="noopener noreferrer" className="mt-1 block break-all text-blue-800 underline">Open original source</a>}
   </div>)}
   {!t.sources?.length&&<p>No attributable evidence was returned.</p>}
   <p className="text-slate-500">Source links, uploads and saved records do not themselves establish a violation or current legal authority. AI-4 file text is held only in a temporary server-process session for up to 12 hours.</p>
  </div>
 </details>;
}
function Reply({turn,revise}){
 const a=turn.answer||{},trail=turn.source_trail||{};
 const [draft,setDraft]=useState(a.draft||'');
 const [feedback,setFeedback]=useState({clarity:0,source_quality:0,usefulness:0,note:''});
 const [message,setMessage]=useState('');
 const [feedbackMessage,setFeedbackMessage]=useState('');
 async function saveFeedback(){
  setFeedbackMessage('Saving…');
  try{
   await send('/api/ai-4/feedback',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({conversation_id:turn.conversation_id,turn_id:turn.turn_id,...feedback})});
   setFeedbackMessage('Evaluation saved for this AI-4 conversation.');
  }catch(e){setFeedbackMessage(e.message)}
 }
 return <article className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" data-testid="ai4-response">
  <div className="flex flex-wrap justify-between gap-2 text-sm"><strong className="flex items-center gap-2 text-[#173950]"><Sparkles size={17}/> AI-4 · {turn.workspace==='MANAGEMENT'?'Management':'Operational'}</strong><span className="text-xs text-slate-500">Human review required</span></div>
  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-900" data-testid="ai4-lead">{a.lead||'No supported answer available.'}</p>
  {!!a.findings?.length&&<section className="space-y-2"><h3 className="text-sm font-bold">Findings</h3>
   {a.findings.map((f,i)=><p key={i} className="text-sm leading-6" data-testid="ai4-finding">{f.text}<Citations ids={f.source_ids} trail={trail}/></p>)}
  </section>}
  {!!a.comparison?.length&&<section className="space-y-2"><h3 className="text-sm font-bold">Realistic options and trade-offs</h3>
   <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="bg-slate-100">{['Option','Benefit','Trade-off','Role / timeframe'].map(x=><th key={x} className="p-2">{x}</th>)}</tr></thead>
    <tbody>{a.comparison.map((x,i)=><tr key={i} className="border-t border-slate-200">
     <td className="p-2 font-medium">{x.option}<Citations ids={x.source_ids} trail={trail}/></td><td className="p-2">{x.benefit}</td>
     <td className="p-2">{x.tradeoff}</td><td className="p-2">{x.responsible_role} · {x.timeframe}</td></tr>)}</tbody></table></div>
  </section>}
  {!!a.next_steps?.length&&<section className="space-y-2"><h3 className="text-sm font-bold">Proposed next actions · not assigned</h3>
   {a.next_steps.map((x,i)=><div key={i} className="rounded-lg bg-slate-50 p-3 text-sm" data-testid="ai4-action">
    <p>{i+1}. {x.action}<Citations ids={x.source_ids} trail={trail}/></p><p className="mt-1 text-xs text-slate-600">Owner role: {x.owner_role||'To confirm'} · Review: {x.review_point||'To confirm'}</p></div>)}
  </section>}
  {!!a.draft&&<section className="space-y-2"><h3 className="text-sm font-bold">Draft · for authorised review only</h3>
   <textarea aria-label="AI-4 editable draft" value={draft} onChange={e=>setDraft(e.target.value)} rows={8} className="w-full rounded-xl border border-slate-300 p-3 text-sm"/>
   <div className="flex flex-wrap gap-2">
    <button type="button" className="intel-ghost text-xs" onClick={async()=>{try{await navigator.clipboard.writeText(draft);setMessage('Draft copied.')}catch{setMessage('Copy unavailable')}}}>Copy</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>revise('Shorten the previous draft while preserving caveats and citations.',draft)}>Shorten</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>revise('Turn the previous draft into a Bawaslu email. Do not send it.',draft)}>Turn into email</button>
   </div>{message&&<p role="status" className="text-xs">{message}</p>}
  </section>}
  {a.clarifying_question&&<p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">To confirm: {a.clarifying_question}</p>}
  {!!a.uncertainties?.length&&<details className="text-xs"><summary className="cursor-pointer font-medium">Uncertainties and verification points</summary><ul className="list-disc pl-5">{a.uncertainties.map((x,i)=><li key={i}>{x}</li>)}</ul></details>}
  <ResearchTrail data={turn}/>
  <div className="flex flex-wrap gap-2">
   <button type="button" className="intel-ghost text-xs" onClick={()=>revise('Compare options with responsible roles, timelines and trade-offs.')}>Compare options</button>
   <button type="button" className="intel-ghost text-xs" onClick={()=>revise('Turn the findings into an operational action plan with reviewers and checkpoints.')}>Make action plan</button>
   <button type="button" className="intel-ghost text-xs" onClick={()=>revise('Draft a concise Bawaslu leadership memo preserving sources and caveats.')}>Draft memo</button>
  </div>
  <details className="rounded-lg border border-slate-200 p-3 text-xs" data-testid="ai4-feedback"><summary className="cursor-pointer font-semibold">Evaluation · clarity, sources and usefulness</summary>
   <div className="mt-3 grid gap-3 sm:grid-cols-3">{[['clarity','Clarity'],['source_quality','Source quality'],['usefulness','Useful for Bawaslu work']].map(([k,label])=>
    <label key={k} className="font-medium">{label}<select aria-label={'AI-4 '+label} value={feedback[k]} onChange={e=>setFeedback(o=>({...o,[k]:Number(e.target.value)}))}
     className="mt-1 block w-full rounded-lg border border-slate-300 p-2"><option value={0}>Choose 1–5</option>{[1,2,3,4,5].map(n=><option value={n} key={n}>{n}</option>)}</select></label>)}</div>
   <textarea aria-label="AI-4 evaluation comment" maxLength={400} rows={2} placeholder="Redacted reviewer notes only" value={feedback.note}
    onChange={e=>setFeedback(o=>({...o,note:e.target.value}))} className="mt-2 w-full rounded-lg border border-slate-300 p-2"/>
   <button type="button" className="intel-button mt-2" disabled={![feedback.clarity,feedback.source_quality,feedback.usefulness].every(Boolean)} onClick={saveFeedback}>Save feedback</button>
   {feedbackMessage&&<p role="status" className="mt-2">{feedbackMessage}</p>}
  </details>
  <p className="text-[11px] text-slate-500">No filing, official determination, assignment or external communication occurred.</p>
 </article>;
}
export default function AI4Assistant({workspace='OPERATIONAL'}){
 const {access}=useOutletContext()||{};
 const leader=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const [conversationId,setConversationId]=useState(newId);
 const [sourceMode,setSourceMode]=useState('WEB_ONLY');
 const [perspective,setPerspective]=useState('AUTO');
 const [question,setQuestion]=useState(new URLSearchParams(window.location.search).get('q')||'');
 const [messages,setMessages]=useState([]);
 const [attachments,setAttachments]=useState([]);
 const [busy,setBusy]=useState(false);
 const [processing,setProcessing]=useState(false);
 const [linkOpen,setLinkOpen]=useState(false);
 const [linkValue,setLinkValue]=useState('');
 const [error,setError]=useState('');
 const [previousDraft,setPreviousDraft]=useState('');
 const picker=useRef(null);
 function reset(){
  fetch('/api/ai-4/conversation/'+conversationId,{method:'DELETE',headers:token()}).catch(()=>{});
  setConversationId(newId());setMessages([]);setAttachments([]);setPreviousDraft('');
  setQuestion('');setError('');setLinkValue('');
 }
 function chooseMode(mode){
  if(mode===sourceMode)return;
  if((messages.length||attachments.length)&&!window.confirm('Changing source mode starts a new conversation and removes its attachments. Continue?'))return;
  if(messages.length||attachments.length)reset();
  setSourceMode(mode);
 }
 async function upload(e){
  const files=Array.from(e.target.files||[]);e.target.value='';if(!files.length)return;
  setProcessing(true);setError('');
  try{
   for(const file of files){
    const form=new FormData();form.append('conversation_id',conversationId);form.append('file',file);
    const r=await send('/api/ai-4/upload',{method:'POST',body:form});
    setAttachments(old=>[...old,r.attachment]);
   }
  }catch(err){setError(err.message)}finally{setProcessing(false)}
 }
 async function addLink(){
  setProcessing(true);setError('');
  try{
   const r=await send('/api/ai-4/link',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({conversation_id:conversationId,url:linkValue.trim()})});
   setAttachments(old=>[...old,r.attachment]);setLinkValue('');setLinkOpen(false);
  }catch(err){setError(err.message)}finally{setProcessing(false)}
 }
 async function removeAttachment(id){
  try{await send('/api/ai-4/attachments/'+conversationId+'/'+id,{method:'DELETE'});
   setAttachments(old=>old.filter(x=>x.id!==id));
  }catch(err){setError(err.message)}
 }
 async function submit(){
  if(!question.trim()||busy)return;
  const q=question.trim(),prior=messages;
  setBusy(true);setError('');setQuestion('');
  setMessages([...prior,{role:'user',text:q}]);
  try{
   const d=await send('/api/ai-4/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q,workspace,perspective,sourceMode,conversationId,previousDraft,
     history:prior.slice(-8).map(x=>({role:x.role,text:x.role==='assistant'?String(x.result?.answer?.lead||'').slice(0,1000):x.text.slice(0,1000)}))})});
   d.conversation_id=conversationId;
   setMessages([...prior,{role:'user',text:q},{role:'assistant',text:d.answer?.lead||'',result:d}]);
   setPreviousDraft('');
  }catch(err){setMessages(prior);setQuestion(q);setError(err.message)}finally{setBusy(false)}
 }
 if(workspace==='MANAGEMENT'&&!leader)return <div role="alert" className="rounded-lg border border-amber-200 p-5 text-sm">Management AI-4 requires authorised leadership access.</div>;
 return <main className="mx-auto max-w-[1160px] space-y-4 pb-8" data-testid="ai4-page">
  <header className="rounded-2xl bg-[#173950] px-6 py-6 text-white">
   <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-sky-200"><Sparkles size={16}/> SmartRadar · AI-4 evaluation</div>
   <h1 className="mt-2 text-3xl font-bold">AI Assistant (New)</h1>
   <p className="mt-2 text-sm text-sky-100">{workspace==='MANAGEMENT'?'Management · decisions, affected jurisdictions and strategic options':'Operational · original evidence, verification and first actions'}</p>
   <p className="mt-2 text-xs text-sky-200">{access?.geographic_scope||'Assigned Bawaslu office'} · {access?.province||'Authorised jurisdiction'} · Existing assistants remain available.</p>
  </header>
  <section className="rounded-xl border border-slate-200 bg-white p-4">
   <div role="group" aria-label="AI-4 source mode" data-testid="ai4-source-modes" className="grid gap-2 md:grid-cols-3">
    {MODES.map(([id,name,desc])=><button type="button" key={id} aria-pressed={sourceMode===id} onClick={()=>chooseMode(id)}
     className={'rounded-lg border p-3 text-left '+(sourceMode===id?'border-red-800 bg-red-50':'border-slate-200 bg-slate-50')}>
     <strong className="block text-sm">{name}</strong><span className="mt-1 block text-xs text-slate-600">{desc}</span></button>)}
   </div>
   <label className="mt-3 block text-xs font-semibold">Optional perspective
    <select aria-label="AI-4 perspective" value={perspective} onChange={e=>setPerspective(e.target.value)}
     className="mt-1 block w-full max-w-xs rounded-lg border border-slate-300 px-3 py-2 text-sm">
     {PERSPECTIVES.map(x=><option key={x} value={x}>{x.charAt(0)+x.slice(1).toLowerCase()}</option>)}
    </select>
   </label>
   <p className="mt-2 text-xs text-slate-500">Web only excludes automatic SmartRadar record retrieval. Your explicitly uploaded files and links are conversation evidence. Change modes only by starting a new conversation.</p>
  </section>
  {!messages.length&&<section className="rounded-xl border border-slate-200 bg-white p-4"><strong className="text-sm">Ask a Bawaslu work question</strong>
   <div className="mt-3 grid gap-2 sm:grid-cols-2">{[
    'Apa langkah pertama Bawaslu kabupaten/kota untuk memeriksa dugaan pelanggaran?',
    'What changed in the latest official Bawaslu announcements?',
    'Compare realistic response options and propose an action plan.',
    'Buat draf memo ringkas untuk pimpinan Bawaslu dengan catatan verifikasi.'
   ].map(x=><button type="button" key={x} onClick={()=>setQuestion(x)} className="rounded-lg border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">{x}</button>)}</div>
  </section>}
  <div className="space-y-4">{messages.map((m,i)=>m.role==='user'?
   <div key={i} className="ml-auto max-w-3xl rounded-2xl bg-red-50 p-4 text-sm leading-6">{m.text}</div>:
   <Reply key={i} turn={m.result} revise={(text,draft)=>{setQuestion(text);if(draft)setPreviousDraft(draft)}}/>)}</div>
  {error&&<div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
  <section className="sticky bottom-2 rounded-xl border border-slate-200 bg-white p-3 shadow-lg" data-testid="ai4-composer">
   {!!attachments.length&&<div className="mb-2 flex flex-wrap gap-2" data-testid="ai4-attachments">
    {attachments.map(x=><div key={x.id} className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs">
     {x.kind==='LINK'?<Link2 size={14}/>:<FileText size={14}/>}<span className="max-w-48 truncate">{x.title}</span>
     <span className="text-green-800">{x.status}{x.truncated?' · Partial':''}</span>
     <button type="button" aria-label={'Remove '+x.title} onClick={()=>removeAttachment(x.id)}><Trash2 size={13} className="text-red-800"/></button>
    </div>)}</div>}
   {processing&&<p role="status" className="mb-2 text-xs text-slate-600">Processing attachment and checking its contents…</p>}
   {linkOpen&&<div className="mb-2 flex gap-2">
    <input type="url" aria-label="Public HTTPS URL" value={linkValue} onChange={e=>setLinkValue(e.target.value)} placeholder="https://..."
     className="min-w-0 flex-1 rounded-lg border border-slate-300 p-2 text-sm"/>
    <button type="button" className="intel-button" disabled={processing||!linkValue.trim()} onClick={addLink}>Add</button>
    <button type="button" className="intel-ghost" onClick={()=>setLinkOpen(false)}>Cancel</button>
   </div>}
   <form onSubmit={e=>{e.preventDefault();submit()}} className="space-y-2">
    <textarea aria-label="Ask AI-4" rows={3} maxLength={2200} value={question} onChange={e=>setQuestion(e.target.value)}
     placeholder="Ask about a case, live news, strategy, an action plan or a draft..."
     className="w-full rounded-lg border border-slate-300 p-3 text-sm"/>
    <div className="flex flex-wrap justify-between gap-2">
     <div className="flex flex-wrap gap-1">
      <input ref={picker} className="hidden" type="file" accept=".pdf,.docx,.txt" multiple onChange={upload}/>
      <button type="button" disabled={busy||processing} className="intel-ghost text-xs" onClick={()=>picker.current?.click()}><Paperclip size={14}/> Upload document</button>
      <button type="button" disabled={busy||processing} className="intel-ghost text-xs" onClick={()=>setLinkOpen(v=>!v)}><Link2 size={14}/> Add link</button>
      <button type="button" disabled={busy} className="intel-ghost text-xs" onClick={reset}><Plus size={14}/> New conversation</button>
     </div>
     <button className="intel-button" type="submit" disabled={busy||processing||!question.trim()}>
      {busy?<Loader2 size={16} className="animate-spin"/>:<ArrowRight size={16}/>}{busy?'Working…':'Ask AI-4'}
     </button>
    </div>
   </form>
   <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck size={12}/> PDF, DOCX, TXT (up to 5 MB); public HTTPS links. Extracted text is ephemeral for up to 12 hours and may be lost after restart. No official action is executed.</p>
  </section>
 </main>;
}
