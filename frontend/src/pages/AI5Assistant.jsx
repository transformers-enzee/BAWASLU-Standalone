import {useState,useRef,useEffect} from 'react';
import {useOutletContext} from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {ArrowRight,Paperclip,Link2,Trash2,Plus,BriefcaseBusiness,Download,FileText,Loader2,Sparkles,ShieldCheck,Globe2,RotateCcw,Save,Share2,Bookmark,Mail,MessageCircle,Copy,Check,X,Pencil,MessagesSquare,History,Search,ChevronDown,ChevronUp} from 'lucide-react';

const MODES=[['WEB_ONLY','Web only','Public research; no saved SmartRadar records'],
 ['WEB_SMARTRADAR','Web + SmartRadar','Read public and authorised saved sources'],
 ['SMARTRADAR_ONLY','SmartRadar only','Authorised saved sources; no new public search']];
const makeId=()=>window.crypto?.randomUUID?.()||'00000000-0000-4000-8000-000000000001';
const headers=()=>({Authorization:'Bearer '+(window.localStorage.getItem('bawaslu_access_token')||'')});
async function request(url,options={}){
 const res=await fetch(url,{...options,headers:{...headers(),...(options.headers||{})}});
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+')');
 return data;
}
function Markdown({value,trail}){
 const rows=trail?.sources||[];
 const byId=new Map(rows.map(s=>[s.id,s]));
 const urls=new Set(rows.map(s=>s.resolved_url||s.url).filter(Boolean));
 const safe=String(value||'').replace(/\[\[([A-Z0-9:_-]{3,80})\]\]/g,(_,key)=>{
  const s=byId.get(key);if(!s)return '';
  const dest=s.url?.startsWith('https://')?(s.resolved_url||s.url):'#ai5-source-'+s.id;
  const label=String((s.title||s.id)+(s.published_at?' ('+String(s.published_at).slice(0,10)+')':'')).replace(/[\[\]]/g,'').slice(0,118);
  return '['+label+']('+dest+')';
 });
 return <div className="prose prose-sm max-w-none text-slate-900 prose-headings:text-[#173950]">
  <ReactMarkdown components={{
   a:({href,children})=>{
    const ok=urls.has(href)||(href?.startsWith('#ai5-source-')&&byId.has(href.slice(12)));
    return ok?<a href={href} target={href.startsWith('#')?undefined:'_blank'}
      rel={href.startsWith('#')?undefined:'noopener noreferrer'} className="break-all text-blue-800 underline">{children}</a>:<span>{children}</span>;
   },
   h1:({children})=><h2 className="mt-4 text-lg font-bold">{children}</h2>,
   h2:({children})=><h3 className="mt-3 text-base font-bold">{children}</h3>,
   p:({children})=><p className="my-2 whitespace-pre-wrap leading-6">{children}</p>,
   ul:({children})=><ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
   ol:({children})=><ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  }}>{safe}</ReactMarkdown>
 </div>;
}
function Trail({result}){
 const t=result.research_trail||{};
 return <details data-testid="ai5-research-trail" className="rounded-xl border border-slate-200 p-4">
  <summary className="cursor-pointer text-sm font-semibold text-[#173950]">Research Trail · consulted sources, dates and access</summary>
  <div className="mt-3 space-y-2 text-xs text-slate-700">
   <p>Source mode: <strong>{result.source_mode?.replaceAll('_',' ')}</strong> · Public search: <strong>{t.public_status||'Not selected'}</strong></p>
   <p>Public pages read: {t.read_public_count??0} · Saved records: {t.saved_count??0} · Uploaded/link sections: {t.attachment_count??0}</p>
   {t.searched_at&&<p>Research consulted: {t.searched_at} (not continuously updated)</p>}
   {t.evidence_intent&&<p>Evidence requested: <strong>{t.evidence_intent.replaceAll('_',' ')}</strong>{t.budget?.max_pages?' · Maximum selected pages: '+t.budget.max_pages:''}</p>}
   {t.comparative_coverage&&<p>Qualitative comparison coverage: <strong>{t.comparative_coverage.status}</strong>{t.comparative_coverage.reason?' · '+t.comparative_coverage.reason:''}</p>}
   {!!t.coverage?.length&&<div className="rounded border border-slate-200 p-2">
    <strong>Coverage of the requested question</strong>
    {(t.coverage||[]).map((x,i)=><p key={i}>{x.name}: <strong>{x.status}</strong>{x.reason?' · '+x.reason:''}</p>)}
   </div>}
   {(t.attempts||[]).map((x,i)=><div key={i} className="rounded border border-slate-200 p-2">
    <p>{x.phase}{x.dimension?' · '+x.dimension:''}: {x.status} · {x.discovered||0} leads{x.query?' · Query: '+x.query:''}{x.provider_queries?.length?' · Provider searched: '+x.provider_queries.join(' | '):''}</p>
    {!!x.leads?.length&&<details className="mt-1"><summary className="cursor-pointer">Discovered pages and reading status ({x.leads.length} shown)</summary>
     <ul className="mt-1 space-y-1">{x.leads.map((lead,j)=><li key={j}>
      <strong>{lead.selected?'Opened':'Not opened'}</strong>{lead.read_status?' · '+lead.read_status:''} · {lead.title||lead.url}
      {lead.reason?' · '+lead.reason:''}
      {lead.url?.startsWith('https://')&&<> · <a href={lead.url} target="_blank" rel="noopener noreferrer" className="text-blue-800 underline">Source</a></>}
     </li>)}</ul>
    </details>}
   </div>)}
   {!!t.answer_audit?.items?.length&&<div className="rounded border border-slate-200 p-2">
    <strong>Final answer coverage check</strong>
    {t.answer_audit.items.map((x,i)=><p key={i}>{x.request}: <strong>{x.status}</strong>{x.reason?' · '+x.reason:''}</p>)}
   </div>}
   {!!t.model_source_ids?.length&&<p>Sources passed to answer model: {t.model_source_ids.map(id=>(t.sources||[]).find(s=>s.id===id)?.title||id).join('; ')}</p>}
   {!!t.model_passages?.length&&<details className="rounded border border-slate-200 p-2">
    <summary className="cursor-pointer font-semibold">Readable public passages actually passed to the answer model ({t.model_passages.length})</summary>
    <div className="mt-2 space-y-2">
     {t.model_passages.map((p,i)=><div key={p.id||i} className="rounded bg-slate-50 p-2">
       <strong>{p.title||p.id}</strong> · {p.publication_date||'date unknown'} · {p.sent_characters||0} characters{p.document_type?' · '+p.document_type:''}
       {!!p.search_dimensions?.length&&<p>Search dimensions: {p.search_dimensions.join(', ')}</p>}
       <p className="mt-1 whitespace-pre-wrap">{p.excerpt_preview||'No preview'}</p>
     </div>)}
    </div>
   </details>}
   {!!t.excluded_source_ids?.length&&<p>Retrieved sources outside the model context limit: {t.excluded_source_ids.join(', ')}</p>}
   {!!t.cited_source_ids?.length&&<p>Sources cited in reply: {t.cited_source_ids.map(id=>(t.sources||[]).find(s=>s.id===id)?.title||id).join('; ')}</p>}
   {!!t.model_source_ids?.length&&<p>Supplied but not cited: {t.model_source_ids.filter(id=>!(t.cited_source_ids||[]).includes(id)).map(id=>(t.sources||[]).find(s=>s.id===id)?.title||id).join('; ')||'None'}</p>}
   {(t.warnings||[]).map((x,i)=><p key={i} className="rounded bg-amber-50 p-2 text-amber-900">{x}</p>)}
   {(t.sources||[]).map(s=><section key={s.id} id={'ai5-source-'+s.id} data-testid="ai5-source-row" className="scroll-mt-24 rounded-lg border border-slate-200 p-3">
    <div className="flex flex-wrap justify-between gap-2"><strong>{s.id} · {s.title}</strong>
     <span className="font-semibold">{s.read_status==='READ'?'Read / extracted':s.read_status==='SAVED_SNAPSHOT'?'Fixed saved record':s.read_status==='SNIPPET_ONLY'?'Snippet only, not read':'Inaccessible / not read'}</span></div>
    <p>Type: {s.type} · Provenance: {s.basis} · Published: {s.published_at||'unknown'}</p>
    {s.section&&<p>File section: {s.section}</p>}
    {s.document_type?.includes('PARTIAL')&&<p className="text-amber-900">Only part of this document was extracted: {s.document_type}</p>}
    {!!s.search_dimensions?.length&&<p>Discovered for: {s.search_dimensions.join(", ")}</p>}
    {s.reason&&<p className="text-amber-900">{s.reason}</p>}
    {s.url?.startsWith('https://')&&<a className="block break-all text-blue-800 underline" href={s.resolved_url||s.url} target="_blank" rel="noopener noreferrer">Open original source</a>}
   </section>)}
   {!t.sources?.length&&<p>No attributable supporting source for this turn.</p>}
   <p className="text-slate-500">Research results, saved records and supplied documents can contain mistakes or allegations. Verify before relying on them for official BAWASLU decisions.</p>
  </div>
 </details>;
}
function Response({item,conversationId,sourceMode,onFollowUp,onShare,onDraftChange,onDraftSave}){
 const a=item.answer||{},t=item.research_trail||{},table=a.table||{};
 const [draft,setDraft]=useState(a.draft||'');
 const [includeTrail,setIncludeTrail]=useState(false);
 const [working,setWorking]=useState('');
 const [error,setError]=useState('');
 async function download(ext){
  setWorking('Generating '+ext.toUpperCase()+'…');setError('');
  try{
   const r=await fetch('/api/ai-5/export/'+ext,{method:'POST',headers:{'Content-Type':'application/json',...headers()},
    body:JSON.stringify({conversationId,turnId:item.turn_id,sourceMode,editedText:a.draft?draft:'',includeResearchTrail:ext==='pdf'&&includeTrail})});
   if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.detail||'Export failed');}
   const blob=await r.blob();if(!blob.size)throw Error('Empty file');
   const url=URL.createObjectURL(blob),node=document.createElement('a');
   node.href=url;node.download='SmartRadar_AI5_'+item.turn_id.slice(0,10)+'.'+ext;
   document.body.appendChild(node);node.click();node.remove();
   setTimeout(()=>URL.revokeObjectURL(url),5000);
   setWorking(ext.toUpperCase()+' downloaded');
  }catch(ex){setError(String(ex.message||ex)+'. The conversation is unchanged.');setWorking('')}
 }
 return <article data-testid="ai5-response" className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-6">
  <div className="flex flex-wrap justify-between gap-2">
   <strong className="flex items-center gap-2 text-sm text-[#173950]"><Sparkles size={17}/> AI-5 · {item.mode==='GENERAL_RESEARCH'?'General Research':'BAWASLU Action · '+item.action_mode}</strong>
   <span className="text-xs text-slate-500">For review</span>
  </div>
  <div data-testid="ai5-answer"><Markdown value={a.body} trail={t}/></div>
  {!!table.columns?.length&&<section className="space-y-2">
   <h3 className="text-sm font-bold">{table.title||'Structured comparison'}</h3>
   <div className="overflow-x-auto rounded-lg border border-slate-200">
    <table className="w-full text-left text-xs"><thead><tr className="bg-slate-100">
     {table.columns.map((x,i)=><th key={i} className="p-2">{x}</th>)}</tr></thead>
     <tbody>{(table.rows||[]).map((row,i)=><tr key={i} className="border-t border-slate-200">
      {table.columns.map((_,j)=><td key={j} className="p-2 align-top"><Markdown value={row[j]||''} trail={t}/></td>)}</tr>)}</tbody>
    </table>
   </div>
  </section>}
  {!!a.draft&&<section className="space-y-2">
   <h3 className="text-sm font-bold">Editable deliverable · review before use</h3>
   <textarea aria-label="AI-5 editable draft" rows={9} value={draft} onChange={e=>{setDraft(e.target.value);onDraftChange?.(item.turn_id,e.target.value);}}
     onBlur={()=>onDraftSave?.(item.turn_id,draft)}
    className="w-full rounded-lg border border-slate-300 p-3 text-xs leading-6"/>
   <div className="flex flex-wrap gap-2">
    <button type="button" className="intel-ghost text-xs" onClick={()=>onFollowUp('Shorten the previous draft while retaining evidence caveats.',item.turn_id,draft)}>Shorten</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>onFollowUp('Change the audience for the earlier draft and preserve citations.',item.turn_id,draft)}>Change audience</button>
    <button type="button" className="intel-ghost text-xs" onClick={async()=>{try{await navigator.clipboard.writeText(draft);setWorking('Copied')}catch{setError('Copy unavailable')}}}>Copy</button>
   </div>
  </section>}
  {!!a.open_questions?.length&&<details className="text-xs"><summary className="cursor-pointer font-semibold">Open questions and assumptions</summary>
   <ul className="list-disc pl-5">{a.open_questions.map((x,i)=><li key={i}><Markdown value={x} trail={t}/></li>)}</ul>
  </details>}
  <div className="flex flex-wrap items-center gap-2">
   <span className="text-xs font-bold text-[#173950]">Download</span>
   {['pdf','docx','xlsx'].map(ext=><button type="button" key={ext} onClick={()=>download(ext)}
    disabled={working.startsWith('Generating')} className="intel-ghost text-xs">
    <Download size={14}/>{ext==='docx'?'Word':ext==='xlsx'?'Excel':'PDF'}</button>)}
   <label className="flex items-center gap-1.5 text-xs text-slate-700">
    <input type="checkbox" checked={includeTrail} onChange={e=>setIncludeTrail(e.target.checked)}
      aria-label="Include detailed Research Trail appendix in PDF"/> Research Trail appendix (PDF)
   </label>
   <button type="button" className="intel-ghost text-xs" onClick={()=>onShare?.(item.turn_id)}>
    <Share2 size={14}/> Share</button>
   <button type="button" className="intel-ghost text-xs" onClick={()=>onFollowUp('Challenge this conclusion and consider alternative interpretations.',item.turn_id)}>
    <RotateCcw size={13}/> Challenge finding</button>
  </div>
  {working&&<p role="status" className="text-xs text-slate-600">{working}</p>}
  {error&&<p role="alert" className="text-xs text-red-800">{error}</p>}
  <Trail result={item}/>
  <p className="text-[11px] text-slate-500">Exports are authenticated. AI-5 has not sent any messages or official actions.</p>
 </article>;
}

function SharedAnswers({snapshot}){
 const answers=snapshot?.answers||[];
 return <div className="space-y-4">
  {answers.map((t,i)=><article key={t.turn_id||i} className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
   <div className="rounded-lg bg-slate-50 p-3 text-sm"><strong>Question {i+1}:</strong> {t.question}</div>
   <Markdown value={t.answer?.body} trail={{sources:t.sources||[]}}/>
   {!!t.answer?.table?.columns?.length&&<div className="overflow-auto">
    <h3 className="mb-2 text-sm font-semibold">{t.answer.table.title||'Comparison'}</h3>
    <table className="w-full border text-left text-xs"><thead><tr>{t.answer.table.columns.map((c,k)=><th key={k} className="border p-2">{c}</th>)}</tr></thead>
     <tbody>{(t.answer.table.rows||[]).map((row,j)=><tr key={j}>{row.map((v,k)=><td className="border p-2 align-top" key={k}>
      <Markdown value={v} trail={{sources:t.sources||[]}}/></td>)}</tr>)}</tbody></table>
   </div>}
   {!!t.answer?.draft&&<section><h3 className="text-sm font-semibold">Draft (read-only)</h3><Markdown value={t.answer.draft} trail={{sources:t.sources||[]}}/></section>}
   {!!t.answer?.open_questions?.length&&<details className="text-xs"><summary>Evidence limits</summary>
    {t.answer.open_questions.map((q,k)=><Markdown key={k} value={q} trail={{sources:t.sources||[]}}/>)}</details>}
   {!!t.research_trail&&<details className="rounded-lg border border-slate-200 p-3 text-xs"><summary className="cursor-pointer font-semibold">Research Trail</summary>
    <Trail result={{source_mode:'WEB_ONLY',research_trail:t.research_trail}}/>
   </details>}
  </article>)}
 </div>;
}

function ShareDialog({initial,conversationId,messages,onClose,onShared}){
 const answers=messages.filter(m=>m.role==='assistant').map(m=>m.data);
 const answerLabel=(answer,index)=>{
  const position=messages.findIndex(m=>m.role==='assistant'&&m.data.turn_id===answer.turn_id);
  const previous=messages[position-1];
  return 'Answer '+(index+1)+' · '+String(previous?.role==='user'?previous.text:(answer.answer?.title||'Research')).slice(0,70);
 };
 const [scope,setScope]=useState(initial.scope);
 const [turnId,setTurnId]=useState(initial.turnId||answers.at(-1)?.turn_id||'');
 const [recipients,setRecipients]=useState('');
 const [includeTrail,setIncludeTrail]=useState(false);
 const [expiryDays,setExpiryDays]=useState(7);
 const [preview,setPreview]=useState(null);
 const [created,setCreated]=useState(null);
 const [working,setWorking]=useState('');
 const [error,setError]=useState('');
 const addresses=recipients.split(/[,;\n]/).map(x=>x.trim()).filter(Boolean);
 const data=()=>({conversationId,scope,turnId,recipients:addresses,
                   includeResearchTrail:includeTrail,expiryDays});
 function invalidate(next){setPreview(null);setCreated(null);setError('');next?.()}
 async function check(){
  setWorking('Checking recipients and evidence…');setError('');setCreated(null);
  try{const r=await request('/api/ai-5/shared/preview',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(data())});
   setPreview(r);
  }catch(e){setError(e.message);setPreview(null)}
  finally{setWorking('')}
 }
 async function create(){
  if(!preview?.can_share)return;
  setWorking('Creating a frozen, read-only copy…');setError('');
  try{const r=await request('/api/ai-5/shared',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({...data(),previewDigest:preview.preview_digest})});
   const link=window.location.origin+'/ai-5?share='+encodeURIComponent(r.token);
   setCreated({...r,link});onShared?.();
  }catch(e){setError(e.message);setPreview(null)}
  finally{setWorking('')}
 }
 async function copyLink(){
  try{await navigator.clipboard.writeText(created.link);setWorking('Link copied')}
  catch{setError('Copy not available. Select and copy the link below.')}
 }
 function draftMail(){
  const subject='SmartRadar AI-5 — shared research';
  const body='A read-only SmartRadar research copy was shared with you. Sign in with your authorised account to open it:\n'+created.link+'\nExpires: '+created.expires_at;
  window.location.href='mailto:'+addresses.join(',')+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
 }
 function draftWhatsApp(){
  const body='SmartRadar AI-5 read-only research (sign-in required): '+created.link+'\nExpires: '+created.expires_at;
  window.open('https://wa.me/?text='+encodeURIComponent(body),'_blank','noopener,noreferrer');
 }
 return <div role="dialog" aria-modal="true" aria-label="Share AI-5 content"
    className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/60 p-3">
  <div className="max-h-[95vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-5 shadow-2xl space-y-3">
   <div className="flex items-center justify-between gap-2">
    <h2 className="flex items-center gap-2 text-lg font-bold text-[#173950]"><Share2 size={19}/> Share AI-5 research</h2>
    <button type="button" aria-label="Close share" onClick={onClose}><X size={20}/></button>
   </div>
   <p className="text-sm text-slate-600">Create a frozen read-only copy for selected signed-in colleagues. Uploaded files and restricted SmartRadar data cannot be shared through this flow.</p>
   <div className="grid gap-3 sm:grid-cols-2">
    <label className="text-xs font-semibold">Content to share
     <select value={scope} onChange={e=>invalidate(()=>setScope(e.target.value))} className="mt-1 w-full rounded border p-2 text-sm">
      <option value="ANSWER">This answer only</option><option value="CONVERSATION">Conversation so far</option>
     </select></label>
    {scope==='ANSWER'&&<label className="text-xs font-semibold">Choose answer
     <select value={turnId} onChange={e=>invalidate(()=>setTurnId(e.target.value))}
       className="mt-1 w-full rounded border p-2 text-sm">
      {answers.map((a,i)=><option key={a.turn_id} value={a.turn_id}>{answerLabel(a,i)}</option>)}
     </select></label>}
   </div>
   <label className="block text-xs font-semibold">Colleague emails (comma or new line separated)
    <textarea rows={2} value={recipients} onChange={e=>invalidate(()=>setRecipients(e.target.value))}
     placeholder="analyst@organisation.gov, reviewer@organisation.gov"
     className="mt-1 w-full rounded border p-2 text-sm"/></label>
   <div className="flex flex-wrap gap-3 text-xs">
    <label className="flex items-center gap-2"><input type="checkbox" checked={includeTrail}
      onChange={e=>invalidate(()=>setIncludeTrail(e.target.checked))}/> Include Research Trail</label>
    <label className="flex items-center gap-2">Link expires after
     <select value={expiryDays} onChange={e=>invalidate(()=>setExpiryDays(Number(e.target.value)))}
      className="rounded border p-1"><option value={1}>1 day</option><option value={7}>7 days</option><option value={30}>30 days</option></select>
    </label>
   </div>
   <div className="flex gap-2">
    <button type="button" className="intel-button" disabled={!addresses.length||!!working} onClick={check}>Preview & check access</button>
    <button type="button" className="intel-ghost" onClick={onClose}>Close</button>
   </div>
   {preview&&<div className="space-y-2 rounded-xl border border-slate-200 p-3">
    <h3 className="text-sm font-semibold">Exactly what recipients will receive ({preview.selected_count} answer(s))</h3>
    <p className="text-xs">Recipients: {preview.recipients?.join(', ')}</p>
    {!!preview.blocked_recipients?.length&&<p role="alert" className="rounded bg-amber-50 p-2 text-xs text-red-800">Access blocked: {preview.blocked_recipients.join('; ')}</p>}
    {!!preview.blocked_content?.length&&<div role="alert" className="rounded bg-amber-50 p-2 text-xs text-red-800">
      <strong>Content blocked — narrow to an eligible answer:</strong>
      {preview.blocked_content.map((x,i)=><p key={i}>{x.question} — {x.reason}</p>)}
    </div>}
    <div className="max-h-72 overflow-auto border-t pt-3"><SharedAnswers snapshot={preview.preview}/></div>
    <button type="button" className="intel-button" disabled={!preview.can_share||!!working||!!created}
     onClick={create}>Create read-only share</button>
   </div>}
   {created&&<div className="space-y-2 rounded-xl bg-emerald-50 p-3 text-sm">
    <p><Check size={15} className="inline"/> Shared copy created. Expires {new Date(created.expires_at).toLocaleString()}. You can revoke it under Shared links.</p>
    <input readOnly aria-label="Read-only share link" value={created.link} className="w-full rounded border p-2 text-xs"/>
    <div className="flex flex-wrap gap-2">
     <button className="intel-ghost text-xs" type="button" onClick={copyLink}><Copy size={14}/> Copy link</button>
     <button className="intel-ghost text-xs" type="button" onClick={draftMail}><Mail size={14}/> Email draft</button>
     <button className="intel-ghost text-xs" type="button" onClick={draftWhatsApp}><MessageCircle size={14}/> WhatsApp draft</button>
    </div>
   </div>}
   {working&&<p role="status" className="text-xs">{working}</p>}
   {error&&<p role="alert" className="text-xs text-red-800">{error}</p>}
  </div>
 </div>;
}

function SharedReadOnly({token}){
 const [view,setView]=useState(null);
 const [error,setError]=useState('');
 useEffect(()=>{
  let active=true;
  request('/api/ai-5/shared/view/'+encodeURIComponent(token)).then(x=>{if(active)setView(x)})
   .catch(e=>{if(active)setError(e.message)});
  return ()=>{active=false};
 },[token]);
 return <main className="mx-auto max-w-[1120px] space-y-4 pb-6">
  <header className="rounded-xl bg-[#173950] p-5 text-white"><h1 className="text-xl font-bold">SmartRadar AI-5 · Shared research</h1>
   <p className="mt-1 text-xs">Sign-in required · Frozen read-only copy · No access to the original conversation</p></header>
  {error&&<div role="alert" className="rounded border border-red-300 bg-red-50 p-4 text-red-900">{error}</div>}
  {!view&&!error&&<p role="status">Verifying your access…</p>}
  {view&&<><div className="rounded border border-slate-200 bg-white p-3 text-xs">
   Read-only share · Expires {new Date(view.expires_at).toLocaleString()} · {view.snapshot.scope==='ANSWER'?'One selected answer':'Conversation snapshot'}
   </div><SharedAnswers snapshot={view.snapshot}/></>}
 </main>;
}

export default function AI5Assistant({workspace='OPERATIONAL'}){
 const {access}=useOutletContext()||{};
 const leader=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const [conversationId,setConversationId]=useState(makeId);
 const [mode,setMode]=useState('GENERAL_RESEARCH');
 const [actionMode,setActionMode]=useState(workspace==='MANAGEMENT'?'MANAGEMENT':'OPERATIONAL');
 const [sourceMode,setSourceMode]=useState('WEB_ONLY');
 const [question,setQuestion]=useState(new URLSearchParams(window.location.search).get('q')||'');
 const [messages,setMessages]=useState([]);
 const [attachments,setAttachments]=useState([]);
 const [busy,setBusy]=useState(false);
 const [processing,setProcessing]=useState(false);
 const [linkOpen,setLinkOpen]=useState(false);
 const [linkValue,setLinkValue]=useState('');
 const [error,setError]=useState('');
 const [refTurn,setRefTurn]=useState(null);
 const [editedRefDraft,setEditedRefDraft]=useState('');
 const [savedChats,setSavedChats]=useState([]);
 const [currentSavedId,setCurrentSavedId]=useState(null);
 const [saveStatus,setSaveStatus]=useState('');
 const [showSaved,setShowSaved]=useState(false);
 const [savedSearch,setSavedSearch]=useState('');
 const [savedLoading,setSavedLoading]=useState(true);
 const [savedLoadError,setSavedLoadError]=useState('');
 const [sharedLinks,setSharedLinks]=useState([]);
 const [showShares,setShowShares]=useState(false);
 const [shareDialog,setShareDialog]=useState(null);
 const [draftRevisions,setDraftRevisions]=useState({});
 const [reopenNote,setReopenNote]=useState('');
 const shareToken=new URLSearchParams(window.location.search).get('share');
 const chooser=useRef(null);
 useEffect(()=>{
  if(shareToken)return;
  let active=true;
  request('/api/ai-5/saved')
    .then(r=>{if(active){setSavedChats(r.saved_chats||[]);setSavedLoadError('')}})
    .catch(()=>{if(active)setSavedLoadError("Couldn't load saved chats")})
    .finally(()=>{if(active)setSavedLoading(false)});
  request('/api/ai-5/shared').then(r=>{if(active)setSharedLinks(r.shares||[])}).catch(()=>{});
  return ()=>{active=false};
 },[shareToken]);
 async function refreshSaved(){
  setSavedLoadError('');
  try{
   const r=await request('/api/ai-5/saved');
   setSavedChats(r.saved_chats||[]);
  }catch(e){
   setSavedLoadError("Couldn't load saved chats");
   throw e;
  }finally{setSavedLoading(false)}
 }
 async function refreshShares(){
  const r=await request('/api/ai-5/shared');setSharedLinks(r.shares||[]);
 }
 async function saveChat(){
  if(!messages.length||busy)return;
  if(currentSavedId){
   setSaveStatus('Saving…');setError('');
   try{
    const r=await request('/api/ai-5/saved/'+encodeURIComponent(currentSavedId)+'/sync',{method:'POST'});
    setSaveStatus(r.status==='SAVED'?'Saved':'Couldn’t save');
    await refreshSaved();
   }catch(e){setSaveStatus('Couldn’t save');setError(e.message)}
   return;
  }
  const proposed=messages.find(m=>m.role==='user')?.text?.slice(0,100)||'AI-5 research';
  const title=window.prompt('Name this saved chat',proposed);
  if(title===null)return;
  setSaveStatus('Saving…');setError('');
  try{
   const r=await request('/api/ai-5/saved',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({conversationId,title,draftRevisions})});
   setCurrentSavedId(r.id);setSaveStatus('Saved');
   await refreshSaved();
  }catch(e){setSaveStatus('Couldn’t save');setError(e.message)}
 }
 async function reopen(id){
  if(busy)return;
  setProcessing(true);setError('');
  try{
   const r=await request('/api/ai-5/saved/'+encodeURIComponent(id));
   setConversationId(r.conversation_id);setMessages(r.messages||[]);
   setAttachments([]);setCurrentSavedId(r.id);setSaveStatus('Saved');
   const last=[...(r.messages||[])].reverse().find(m=>m.role==='assistant')?.data;
   if(last){setMode(last.mode||'GENERAL_RESEARCH');setSourceMode(last.source_mode||'WEB_ONLY');
    setActionMode(last.action_mode||'OPERATIONAL')}
   setQuestion('');setRefTurn(null);setEditedRefDraft('');
   setDraftRevisions({});setShowSaved(false);setReopenNote(r.attachments_note||'');
  }catch(e){setError(e.message);setSaveStatus('Couldn’t reopen')}
  finally{setProcessing(false)}
 }
 async function renameChat(item){
  const title=window.prompt('Rename saved chat',item.title);if(title===null)return;
  try{await request('/api/ai-5/saved/'+encodeURIComponent(item.id),{
    method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({title})});
    await refreshSaved();
  }catch(e){setError(e.message)}
 }
 async function deleteChat(item){
  if(!window.confirm('Delete saved chat "'+item.title+'"? Any shared links from this chat will also be revoked.'))return;
  try{await request('/api/ai-5/saved/'+encodeURIComponent(item.id),{method:'DELETE'});
   await refreshSaved();await refreshShares();
   if(item.id===currentSavedId)reset();
  }catch(e){setError(e.message)}
 }
 async function saveDraft(turnId,draft){
  if(!currentSavedId)return;
  setSaveStatus('Saving…');
  try{await request('/api/ai-5/saved/'+encodeURIComponent(currentSavedId)+'/draft',{
   method:'PATCH',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({turnId,editedDraft:draft})});
   setSaveStatus('Saved');
  }catch(e){setSaveStatus('Couldn’t save');setError(e.message)}
 }
 async function revokeShare(id){
  if(!window.confirm('Revoke this link? Colleagues will immediately lose access.'))return;
  try{await request('/api/ai-5/shared/'+encodeURIComponent(id),{method:'DELETE'});
   await refreshShares();
  }catch(e){setError(e.message)}
 }
 async function copyOldShare(token){
  const link=window.location.origin+'/ai-5?share='+encodeURIComponent(token);
  try{await navigator.clipboard.writeText(link);setSaveStatus('Link copied')}
  catch{setError('Copy unavailable: '+link)}
 }
 function reset(){
  fetch('/api/ai-5/conversation/'+conversationId,{method:'DELETE',headers:headers()}).catch(()=>{});
  setConversationId(makeId());setMessages([]);setAttachments([]);setQuestion('');
  setMode('GENERAL_RESEARCH');setSourceMode('WEB_ONLY');setRefTurn(null);setEditedRefDraft('');setError('');
  setCurrentSavedId(null);setSaveStatus('');setDraftRevisions({});setReopenNote('');
 }
 async function upload(event){
  const items=Array.from(event.target.files||[]);event.target.value='';
  if(!items.length)return;
  setProcessing(true);setError('');
  try{
   for(const file of items){const data=new FormData();data.append('conversation_id',conversationId);data.append('file',file);
    const r=await request('/api/ai-5/upload',{method:'POST',body:data});
    setAttachments(v=>[...v,r.attachment]);}
  }catch(e){setError(e.message)}finally{setProcessing(false)}
 }
 async function addLink(){
  setProcessing(true);setError('');
  try{const r=await request('/api/ai-5/link',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation_id:conversationId,url:linkValue.trim()})});
   setAttachments(v=>[...v,r.attachment]);setLinkOpen(false);setLinkValue('');
  }catch(e){setError(e.message)}finally{setProcessing(false)}
 }
 async function remove(aid){
  try{await request('/api/ai-5/attachments/'+conversationId+'/'+aid,{method:'DELETE'});
   setAttachments(v=>v.filter(x=>x.id!==aid));
  }catch(e){setError(e.message)}
 }
 async function submit(){
  const q=question.trim();if(!q||busy)return;
  const old=messages;setMessages([...old,{role:'user',text:q}]);setBusy(true);setQuestion('');setError('');
  try{
   const r=await request('/api/ai-5/chat',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q,mode,actionMode,sourceMode,conversationId,
      referenceTurnId:refTurn,editedDraft:editedRefDraft})});
   setMessages([...old,{role:'user',text:q},{role:'assistant',data:r}]);setRefTurn(null);setEditedRefDraft('');
   if(currentSavedId){
    setSaveStatus(r.save_status==='SAVED'?'Saved':'Couldn’t save');
    if(r.save_status!=='SAVED')setError(r.save_error||'This new answer was not saved.');
    else refreshSaved().catch(()=>{});
   }
  }catch(e){setMessages(old);setQuestion(q);setError(e.message)}
  finally{setBusy(false)}
 }
 function followup(value,id,draft=''){setQuestion(value);setRefTurn(id);setEditedRefDraft(draft);}
 if(shareToken)return <SharedReadOnly token={shareToken}/>;
 if(workspace==='MANAGEMENT'&&!leader)return <div role="alert" className="rounded-lg border border-amber-200 p-5">Management access requires authorised leadership. Use AI-5 in Operations for General Research.</div>;
 return <main data-testid="ai5-page" className="mx-auto max-w-[1160px] space-y-4 pb-6">
  <header className="rounded-2xl bg-[#173950] px-6 py-6 text-white">
   <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-sky-100"><Sparkles size={16}/> Independent SmartRadar assistant</p>
   <h1 className="mt-2 text-3xl font-bold">AI-5 Assistant</h1>
   <p className="mt-2 text-sm text-sky-100">Explore any topic, follow a new angle, and create working documents. Apply findings to BAWASLU when you choose.</p>
   <div className="mt-5 flex flex-wrap items-center gap-2">
    <button type="button" data-testid="ai5-new-chat-header" disabled={busy||processing}
     onClick={reset} className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-bold text-[#173950] shadow-sm transition hover:bg-sky-50">
     <Plus size={17}/> New chat</button>
    <button type="button" data-testid="ai5-save-chat" disabled={!messages.length||busy||processing}
     onClick={saveChat} className={'inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-semibold transition '+
       (!messages.length?'cursor-not-allowed border-white/20 text-sky-100/60':
        currentSavedId?'border-sky-200 bg-sky-100 text-[#173950] hover:bg-white':
        'border-white bg-white/10 text-white hover:bg-white/20')}>
     {currentSavedId?<Check size={17}/>:<Save size={17}/>}
     {currentSavedId?(saveStatus==='Couldn’t save'?'Retry save':'Saved'):'Save chat'}</button>
    <button type="button" data-testid="ai5-share-chat" aria-label="Share chat" disabled={!messages.length||busy||processing}
     onClick={()=>setShareDialog({scope:'CONVERSATION',turnId:null})}
     className="inline-flex items-center gap-2 rounded-lg border border-white/40 px-3 py-2.5 text-sm font-medium text-white transition hover:bg-white/10">
     <Share2 size={16}/> Share</button>
    {messages.length>0&&<span data-testid="ai5-save-status" role="status" className={'rounded-lg px-3 py-2 text-xs font-semibold '+
     (saveStatus==='Couldn’t save'?'bg-red-100 text-red-900':
      currentSavedId&&saveStatus!=='Saving…'?'bg-emerald-50 text-emerald-950':'bg-white/10 text-white')}>
     {saveStatus==='Couldn’t save'?'Couldn’t save · Retry above':
      saveStatus==='Saving…'?'Saving…':
      currentSavedId?'Saved automatically after each reply':
      'Not saved · Save to return later'}
    </span>}
   </div>
  </header>
  <nav aria-label="AI-5 Saved Chats" data-testid="ai5-saved-chats"
   className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div className="flex items-start gap-3">
     <span className="rounded-lg bg-sky-50 p-2 text-[#173950]"><History size={21}/></span>
     <div>
      <h2 className="text-base font-bold text-[#173950]">Your conversations</h2>
      <p className="mt-0.5 text-xs text-slate-600">Open a saved chat to pick up where you left off. Only you can see your saved chats.</p>
     </div>
    </div>
    <div className="flex items-center gap-2">
     <button type="button" data-testid="ai5-saved-navigation"
      onClick={()=>{setShowSaved(v=>!v);setSavedSearch('');refreshSaved().catch(()=>{})}}
      className="intel-ghost inline-flex items-center gap-1.5 text-xs font-semibold">
      {showSaved?'Show recent':'View all chats'} {showSaved?<ChevronUp size={14}/>:<ChevronDown size={14}/>}</button>
     <button type="button" onClick={()=>{setShowShares(v=>!v);refreshShares().catch(()=>{})}}
      className="intel-ghost inline-flex items-center gap-1.5 text-xs">
      <Share2 size={14}/> Shared links</button>
    </div>
   </div>
   {showSaved&&savedChats.length>3&&<label className="mt-3 flex items-center gap-2 rounded-lg border border-slate-200 px-3 text-slate-500">
     <Search size={16}/><input value={savedSearch} onChange={e=>setSavedSearch(e.target.value)}
      aria-label="Search saved chats" placeholder="Search your saved conversations"
      className="min-w-0 flex-1 bg-transparent py-2 text-sm text-slate-900 outline-none"/>
   </label>}
   <div className="mt-3 space-y-2">
    {savedLoading&&<p role="status" className="p-3 text-xs text-slate-600">Loading your saved conversations…</p>}
    {savedLoadError&&<div role="alert" className="flex items-center gap-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">
      {savedLoadError}<button type="button" className="font-semibold underline" onClick={()=>refreshSaved().catch(()=>{})}>Retry</button>
     </div>}
    {!savedLoading&&!savedLoadError&&savedChats.length===0&&<div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3">
      <p className="text-sm text-slate-600">Your saved conversations will appear here. Save a chat to find it again after signing out.</p>
      {!!messages.length&&<button type="button" className="intel-button text-xs" onClick={saveChat}>
       <Save size={14}/> Save current chat</button>}
     </div>}
    {(showSaved?savedChats.filter(x=>x.title.toLowerCase().includes(savedSearch.toLowerCase())):savedChats.slice(0,3)).map(item=>
     <div key={item.id} data-testid="ai5-saved-chat-item" className={'flex items-center gap-2 rounded-lg border p-2 transition '+
       (currentSavedId===item.id?'border-sky-300 bg-sky-50':'border-slate-100 bg-slate-50/60 hover:bg-slate-50')}>
      <button type="button" className="flex min-w-0 flex-1 items-center gap-3 rounded-md p-1 text-left"
       onClick={()=>reopen(item.id)} disabled={processing||busy} aria-label={'Open saved chat '+item.title}>
       <MessagesSquare size={17} className="shrink-0 text-slate-500"/>
       <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-[#173950]">{item.title}</span>
        <span className="block text-xs text-slate-500">{currentSavedId===item.id?'Current chat · ':''}
         Updated {new Date(item.updated_at).toLocaleString()}</span>
       </span>
       {currentSavedId===item.id&&<span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-emerald-800"><Check size={13}/> Open</span>}
      </button>
      <button type="button" className="rounded-md border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-100"
       aria-label={'Rename '+item.title} title="Rename chat" onClick={()=>renameChat(item)}><Pencil size={15}/></button>
      <button type="button" className="rounded-md border border-slate-200 bg-white p-2 text-slate-600 hover:bg-red-50"
       aria-label={'Delete '+item.title} title="Delete saved chat" onClick={()=>deleteChat(item)}><Trash2 size={15}/></button>
     </div>)}
    {showSaved&&savedChats.length>0&&savedSearch.trim()&&!savedChats.some(x=>x.title.toLowerCase().includes(savedSearch.toLowerCase()))&&
     <p className="p-3 text-xs text-slate-500">No saved chats match your search.</p>}
    {!showSaved&&savedChats.length>3&&<button type="button" className="px-2 py-1 text-xs font-semibold text-[#173950] underline"
     onClick={()=>setShowSaved(true)}>See all {savedChats.length} saved chats</button>}
   </div>
  </nav>
  {showShares&&<section aria-label="AI-5 Shared links" className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
   <h2 className="text-sm font-bold">Shared links · Read-only copies</h2>
   {!sharedLinks.length&&<p className="text-xs text-slate-500">No shared links yet.</p>}
   {sharedLinks.map(item=><div key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-2">
    <div><p className="text-xs font-semibold">{item.scope==='ANSWER'?'One answer':'Conversation snapshot'} · {item.revoked?'Revoked':item.expired?'Expired':'Active'}</p>
     <p className="text-xs text-slate-600">Expires {new Date(item.expires_at).toLocaleString()}</p></div>
    <div className="flex gap-2">
     {!item.revoked&&!item.expired&&<button type="button" className="intel-ghost text-xs" onClick={()=>copyOldShare(item.token)}><Copy size={13}/> Copy link</button>}
     {!item.revoked&&<button type="button" className="intel-ghost text-xs" onClick={()=>revokeShare(item.id)}><X size={13}/> Revoke</button>}
    </div>
   </div>)}
  </section>}
  {!!reopenNote&&<p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">{reopenNote}</p>}
  <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
   <div>
    <h2 className="mb-2 text-xs font-bold uppercase tracking-wide">Conversation mode — change without losing context</h2>
    <div data-testid="ai5-modes" role="group" aria-label="AI-5 conversation mode" className="grid gap-2 sm:grid-cols-2">
     <button type="button" disabled={busy} aria-pressed={mode==='GENERAL_RESEARCH'} onClick={()=>setMode('GENERAL_RESEARCH')}
      className={'rounded-xl border p-3 text-left '+(mode==='GENERAL_RESEARCH'?'border-blue-700 bg-sky-50':'border-slate-200 bg-slate-50')}>
      <strong className="flex items-center gap-2 text-sm"><Globe2 size={17}/> General Research</strong>
      <span className="mt-1 block text-xs text-slate-600">Any topic or angle, no BAWASLU framing by default</span>
     </button>
     <button type="button" disabled={busy} aria-pressed={mode==='BAWASLU_ACTION'} onClick={()=>setMode('BAWASLU_ACTION')}
      data-testid="ai5-use-bawaslu"
      className={'rounded-xl border p-3 text-left '+(mode==='BAWASLU_ACTION'?'border-[#9b2e34] bg-red-50':'border-slate-200 bg-slate-50')}>
      <strong className="flex items-center gap-2 text-sm"><BriefcaseBusiness size={17}/> Use for BAWASLU</strong>
      <span className="mt-1 block text-xs text-slate-600">Apply the conversation to your office's authorised work</span>
     </button>
    </div>
    {mode==='BAWASLU_ACTION'&&<div data-testid="ai5-action-options" className="mt-2 rounded-lg bg-slate-50 p-3">
     <label className="text-xs font-semibold">BAWASLU Action emphasis
      <select aria-label="BAWASLU Action emphasis" value={actionMode} onChange={e=>setActionMode(e.target.value)}
       className="mt-1 block w-full max-w-lg rounded-lg border border-slate-300 bg-white p-2 text-sm">
       <option value="OPERATIONAL">Operational — verification, owners, next steps</option>
       {leader&&<option value="MANAGEMENT">Management — implications, options, decisions</option>}
      </select>
     </label>
     <p className="mt-1 text-xs text-slate-600">Current authorised jurisdiction: {access?.geographic_scope||'Assigned scope'} · {access?.province||'—'}</p>
    </div>}
   </div>
   <div>
    <h2 className="mb-2 text-xs font-bold uppercase tracking-wide">Source access — independent of conversation mode</h2>
    <div data-testid="ai5-source-modes" role="group" aria-label="AI-5 source mode" className="grid gap-2 sm:grid-cols-3">
     {MODES.map(([value,name,caption])=><button type="button" key={value} disabled={busy}
      aria-pressed={sourceMode===value} onClick={()=>{setSourceMode(value);setRefTurn(null);setEditedRefDraft('')}}
      className={'rounded-lg border p-3 text-left '+(sourceMode===value?'border-red-800 bg-red-50':'border-slate-200 bg-slate-50')}>
      <strong className="block text-sm">{name}</strong><span className="mt-1 block text-xs text-slate-600">{caption}</span>
     </button>)}
    </div>
    <p className="mt-2 text-[11px] text-slate-500">Web only never accesses saved SmartRadar records, including evidence from previous mixed-source turns. You can keep the conversation while changing this setting.</p>
   </div>
  </section>
  {!messages.length&&<section className="rounded-xl border border-slate-200 bg-white p-4">
   <strong className="text-sm">Ask anything in your own words</strong>
   <div className="mt-3 grid gap-2 sm:grid-cols-2">{[
    'Explain quantum computing to a beginner in three sentences.',
    'Compare the latest research on urban heat islands.',
    'Challenge the assumption that social media represents public opinion.',
    'Summarise my attached document and identify its main uncertainties.'
   ].map(x=><button type="button" key={x} onClick={()=>setQuestion(x)}
    className="rounded-lg border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">{x}</button>)}</div>
  </section>}
  <div className="space-y-4">{messages.map((m,i)=>m.role==='user'?
   <div key={i} className="ml-auto max-w-3xl rounded-2xl bg-red-50 p-4 text-sm">{m.text}</div>:
   <Response key={m.data.turn_id||i} item={m.data} conversationId={conversationId}
    sourceMode={m.data.source_mode||sourceMode} onFollowUp={followup}
    onShare={id=>setShareDialog({scope:'ANSWER',turnId:id})}
    onDraftChange={(id,text)=>setDraftRevisions(v=>({...v,[id]:text}))}
    onDraftSave={saveDraft}/>)}</div>
  {error&&<p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
  <section data-testid="ai5-composer" className="sticky bottom-2 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
   {!!attachments.length&&<div data-testid="ai5-attachments" className="mb-2 flex flex-wrap gap-2">
    {attachments.map(a=><div key={a.id} className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs">
     {a.kind==='LINK'?<Link2 size={13}/>:<FileText size={13}/>}
     <span className="max-w-44 truncate">{a.title}</span>
     <span className="text-green-800">{a.status}{a.truncated?' · Partial':''}</span>
     <button type="button" aria-label={'Remove '+a.title} onClick={()=>remove(a.id)}><Trash2 size={13}/></button>
    </div>)}
   </div>}
   {processing&&<p role="status" className="mb-2 text-xs">Processing attachment securely…</p>}
   {linkOpen&&<div className="mb-2 flex gap-2">
    <input type="url" aria-label="AI-5 public HTTPS URL" placeholder="https://..." value={linkValue}
     onChange={e=>setLinkValue(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-300 p-2 text-sm"/>
    <button type="button" className="intel-button" disabled={processing||!linkValue.trim()} onClick={addLink}>Add</button>
    <button type="button" className="intel-ghost" onClick={()=>setLinkOpen(false)}>Cancel</button>
   </div>}
   {messages.length>0&&<div className={'mb-2 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2 text-xs '+
       (currentSavedId?'bg-emerald-50 text-emerald-950':'bg-amber-50 text-amber-950')}>
     <span className="inline-flex items-center gap-2">
      {currentSavedId?<Check size={15}/>:<Bookmark size={15}/>}
      {currentSavedId?'Saved conversation · New replies are saved automatically':
       'This conversation isn’t saved yet. Save it to return after signing out.'}
     </span>
     <button type="button" className="font-semibold underline" disabled={busy||processing} onClick={saveChat}>
      {currentSavedId?'Sync now':'Save this chat'}
     </button>
    </div>}
   <form className="space-y-2" onSubmit={e=>{e.preventDefault();submit()}}>
    <textarea rows={3} maxLength={3200} aria-label="Ask AI-5" value={question}
     onChange={e=>setQuestion(e.target.value)}
     placeholder="Ask anything, challenge a finding, return to an earlier draft, or request a document…"
     className="w-full rounded-lg border border-slate-300 p-3 text-sm"/>
    <div className="flex flex-wrap items-center justify-between gap-2">
     <div className="flex flex-wrap gap-1">
      <input className="hidden" type="file" accept=".pdf,.docx,.txt" multiple ref={chooser} onChange={upload}/>
      <button type="button" className="intel-ghost text-xs" disabled={busy||processing} onClick={()=>chooser.current?.click()}><Paperclip size={14}/> Upload document</button>
      <button type="button" className="intel-ghost text-xs" disabled={busy||processing} onClick={()=>setLinkOpen(x=>!x)}><Link2 size={14}/> Add link</button>
      <button type="button" className="intel-ghost text-xs" disabled={busy} onClick={reset}><Plus size={14}/> New conversation</button>
     </div>
     <button type="submit" className="intel-button" disabled={busy||processing||!question.trim()}>
      {busy?<Loader2 size={16} className="animate-spin"/>:<ArrowRight size={16}/>}
      {busy?'Researching…':'Ask AI-5'}
     </button>
    </div>
   </form>
   <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck size={12}/> PDF/DOCX/TXT up to 5 MB and public HTTPS links. Extracted attachment text is provided to the configured AI model when answering, not to public search. Unsaved conversations remain temporary (up to 12 hours). Save chat to keep your turns, drafts and citations beyond the session. Uploaded files themselves are not retained.</p>
  </section>
  {shareDialog&&<ShareDialog key={shareDialog.scope+String(shareDialog.turnId||'')}
    initial={shareDialog} conversationId={conversationId} messages={messages}
    onClose={()=>setShareDialog(null)} onShared={()=>refreshShares().catch(()=>{})}/>}
 </main>;
}
