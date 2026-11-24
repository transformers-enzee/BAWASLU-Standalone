import {useState,useRef} from 'react';
import {useOutletContext} from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {ArrowRight,Paperclip,Link2,Trash2,Plus,BriefcaseBusiness,Download,FileText,Loader2,Sparkles,ShieldCheck,Globe2,RotateCcw} from 'lucide-react';

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
function Response({item,conversationId,sourceMode,onFollowUp}){
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
   <textarea aria-label="AI-5 editable draft" rows={9} value={draft} onChange={e=>setDraft(e.target.value)}
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
   <button type="button" className="intel-ghost text-xs" onClick={()=>onFollowUp('Challenge this conclusion and consider alternative interpretations.',item.turn_id)}>
    <RotateCcw size={13}/> Challenge finding</button>
  </div>
  {working&&<p role="status" className="text-xs text-slate-600">{working}</p>}
  {error&&<p role="alert" className="text-xs text-red-800">{error}</p>}
  <Trail result={item}/>
  <p className="text-[11px] text-slate-500">Exports are authenticated. AI-5 has not sent any messages or official actions.</p>
 </article>;
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
 const chooser=useRef(null);
 function reset(){
  fetch('/api/ai-5/conversation/'+conversationId,{method:'DELETE',headers:headers()}).catch(()=>{});
  setConversationId(makeId());setMessages([]);setAttachments([]);setQuestion('');
  setMode('GENERAL_RESEARCH');setSourceMode('WEB_ONLY');setRefTurn(null);setEditedRefDraft('');setError('');
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
  }catch(e){setMessages(old);setQuestion(q);setError(e.message)}
  finally{setBusy(false)}
 }
 function followup(value,id,draft=''){setQuestion(value);setRefTurn(id);setEditedRefDraft(draft);}
 if(workspace==='MANAGEMENT'&&!leader)return <div role="alert" className="rounded-lg border border-amber-200 p-5">Management access requires authorised leadership. Use AI-5 in Operations for General Research.</div>;
 return <main data-testid="ai5-page" className="mx-auto max-w-[1160px] space-y-4 pb-6">
  <header className="rounded-2xl bg-[#173950] px-6 py-6 text-white">
   <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-sky-100"><Sparkles size={16}/> Independent SmartRadar assistant</p>
   <h1 className="mt-2 text-3xl font-bold">AI-5 Assistant</h1>
   <p className="mt-2 text-sm text-sky-100">Explore any topic, follow a new angle, and create working documents. Apply findings to BAWASLU when you choose.</p>
  </header>
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
    sourceMode={sourceMode} onFollowUp={followup}/>)}</div>
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
   <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck size={12}/> PDF/DOCX/TXT up to 5 MB and public HTTPS links. Extracted attachment text is provided to the configured AI model when answering, not to public search. Conversations are temporary (up to 12 hours) and may be lost on restart.</p>
  </section>
 </main>;
}
