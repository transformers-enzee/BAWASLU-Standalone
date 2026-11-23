import {useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {ArrowRight,BookOpen,Check,ClipboardCopy,FilePenLine,Globe2,Lightbulb,
        Loader2,MessageSquareText,Plus,SearchCheck,ShieldCheck,Sparkles} from 'lucide-react';

const WORKFLOWS=[
 {id:'AUTO',title:'Auto',subtitle:'Adapt to your question',icon:Sparkles},
 {id:'RESEARCH',title:'Research & analysis',subtitle:'Find, compare, verify',icon:SearchCheck},
 {id:'STRATEGY',title:'Strategy & planning',subtitle:'Options, tactics, milestones',icon:Lightbulb},
 {id:'DRAFTING',title:'Draft & revise',subtitle:'Briefs, memos, emails',icon:FilePenLine},
];
const SOURCE_CHOICES=[
 {key:'smartRadar',label:'SmartRadar records',detail:'Authorised saved intelligence and social records'},
 {key:'publicWeb',label:'Public web / indexed social',detail:'Live attributed public search; not a complete social crawl'},
 {key:'legalReferences',label:'Legal / reference library',detail:'Authorised PDF passages; current law must be checked'},
];
const PROMPTS=[
 'What kinds of electoral violations fall within BAWASLU oversight?',
 'Compare documented candidate-qualification cases in other provinces.',
 'Propose three neutral oversight strategies, with trade-offs and review points.',
 'Draft a leadership memo from the research above, keeping all evidence caveats.',
];
const STATUS={
 CONSULTED:'Consulted',NOT_SELECTED:'Not selected',
 SELECTED_NOT_CONSULTED:'Selected · no source returned',
};
const BASIS={
 FIXED_SAVED_SNAPSHOT:'Saved snapshot',LIVE_PUBLIC_LOOKUP:'Live at query time',
 NOT_CONSULTED:'Not consulted',NOT_SELECTED:'Not selected',
 USER_SUPPLIED_UNVERIFIED:'User supplied · unverified',
};
function idsFor(sourceIds,sources){
 const known=new Map((sources||[]).map(s=>[s.id,s]));
 return (sourceIds||[]).filter(id=>known.has(id)).map(id=>known.get(id));
}
function SourceChips({ids,sources}){
 const items=idsFor(ids,sources);
 return items.length?<div className="mt-2 flex flex-wrap gap-1.5">
  {items.map(s=>s.url?.startsWith('https://')?
   <a key={s.id} href={s.url} target="_blank" rel="noreferrer noopener"
    className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-800 hover:underline"
    title={s.title}>{s.id} · source</a>:
   <span key={s.id} title={s.title}
    className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600">{s.id} · saved</span>)}
 </div>:<span className="mt-1 block text-[11px] text-amber-700">No validated supporting citation · inference only</span>;
}
function Result({data,index,draftEdits,setDraftEdits,onFollowUp}){
 const answer=data.answer||{},sources=data.sources||[];
 const draft=draftEdits[index]??answer.draft??'';
 const [copyState,setCopyState]=useState('');
 const copy=async()=>{
  try{await navigator.clipboard.writeText(draft);setCopyState('Copied');}
  catch{setCopyState('Unable to copy; select the draft text instead.');}
 };
 return <article className="space-y-4 rounded-2xl border border-[#d9e1e9] bg-white p-4 shadow-sm md:p-6"
  data-testid="ai-assistant-v2-result">
  <div className="flex flex-wrap items-center justify-between gap-2">
   <div className="flex items-center gap-2 text-[#19364c]"><Sparkles size={18}/><strong>AI Assistant</strong></div>
   <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
    {data.workflow==='RESEARCH'?'Research':data.workflow==='STRATEGY'?'Strategy & planning':'Draft & revise'} · review required
   </span>
  </div>
  {answer.draft&&<section className="space-y-2" data-testid="ai-assistant-v2-draft">
    <div className="flex flex-wrap items-center justify-between gap-2">
     <h3 className="font-semibold text-[#19364c]">Editable draft · not sent</h3>
     <button type="button" className="intel-ghost text-xs" onClick={copy}><ClipboardCopy size={14}/> Copy draft</button>
    </div>
    <textarea aria-label="Editable AI draft" value={draft} onChange={e=>setDraftEdits(old=>({...old,[index]:e.target.value}))}
     rows={Math.min(19,Math.max(7,draft.split('\n').length+2))}
     className="w-full rounded-xl border border-slate-300 bg-[#fbfcfd] p-3 text-sm leading-6 text-slate-800"/>
    {copyState&&<p role="status" className="text-xs text-slate-600">{copyState}</p>}
    <p className="text-xs text-amber-800">For authorised staff review only. No message, memo, approval or case action has been sent.</p>
    <div className="flex flex-wrap gap-2">
     <button className="intel-ghost text-xs" type="button" onClick={()=>onFollowUp('Shorten the preceding draft while preserving all source caveats and citations.')}>Shorten</button>
     <button className="intel-ghost text-xs" type="button" onClick={()=>onFollowUp('Rewrite the preceding draft for BAWASLU national leadership, preserving all caveats.')}>Executive audience</button>
     <button className="intel-ghost text-xs" type="button" onClick={()=>onFollowUp('Turn the preceding findings into a professional email reply draft. Do not send it.')}>Turn into email</button>
    </div>
   </section>}
  <section className="space-y-1">
   <h3 className="text-sm font-semibold text-[#19364c]">{answer.draft?'Supporting research assessment':'Research assessment'}</h3>
   <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{answer.summary||'No summary could be generated.'}</p>
   <p className="text-[11px] text-slate-500">AI synthesis. Confirm case-specific facts against the source-linked findings below.</p>
  </section>
  {!!answer.findings?.length&&<section className="space-y-3" data-testid="ai-assistant-v2-findings">
   <h3 className="font-semibold text-[#19364c]">Structured findings</h3>
   {answer.findings.map((f,i)=><div className="rounded-lg bg-slate-50 p-3" key={i}>
    <p className="text-sm leading-6 text-slate-800">{f.claim}</p>
    <SourceChips ids={f.source_ids} sources={sources}/>
    <p className="mt-2 text-[11px] text-slate-600">{String(f.evidence_class||'').replaceAll('_',' ')} · {f.support}</p>
    {f.uncertainty&&<p className="mt-1 text-xs text-amber-800">Limit: {f.uncertainty}</p>}
   </div>)}
  </section>}
  {!!answer.options?.length&&<section className="space-y-2" data-testid="ai-assistant-v2-strategies">
   <h3 className="font-semibold text-[#19364c]">Response options and trade-offs</h3>
   {answer.options.map((o,i)=><div key={i} className="rounded-lg border border-slate-200 p-3">
    <strong className="text-sm">{o.title}</strong>
    <p className="mt-1 text-sm">Potential value: {o.benefit}</p>
    <p className="mt-1 text-sm text-amber-900">Trade-off: {o.tradeoff}</p>
    <SourceChips ids={o.source_ids} sources={sources}/>
   </div>)}
  </section>}
  {!!answer.plan?.length&&<section className="space-y-2" data-testid="ai-assistant-v2-plan">
   <h3 className="font-semibold text-[#19364c]">Proposed action plan · not assigned</h3>
   {answer.plan.map((p,i)=><div className="rounded-lg border border-slate-200 p-3 text-sm" key={i}>
    <strong>{i+1}. {p.action}</strong>
    <p className="mt-1 text-slate-600">Suggested responsible role: {p.owner_role||'Requires designation'}</p>
    <p className="text-slate-600">Proposed milestone: {p.milestone||'To be agreed'}</p>
    <p className="text-slate-600">Review point: {p.review_point||'Requires approval'}</p>
    <SourceChips ids={p.source_ids} sources={sources}/>
   </div>)}
  </section>}
  {!!answer.uncertainties?.length&&<section className="space-y-1.5">
    <h3 className="font-semibold text-[#19364c]">What remains uncertain</h3>
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{answer.uncertainties.map((u,i)=><li key={i}>{u}</li>)}</ul>
   </section>}
  {!!data.warnings?.length&&<section role="note" className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3">
    <strong className="text-xs text-amber-950">Research limitations</strong>
    {data.warnings.map((w,i)=><p className="text-xs text-amber-900" key={i}>{w}</p>)}
   </section>}
  <details className="rounded-lg border border-slate-200 p-3" data-testid="ai-assistant-v2-research-trail">
   <summary className="cursor-pointer text-sm font-semibold text-[#19364c]">Research trail · sources actually consulted</summary>
   <div className="mt-3 space-y-3">
    {(data.consulted_sources||[]).map(s=><div className="border-b border-slate-100 pb-2" key={s.key}>
     <div className="flex items-center justify-between gap-2 text-xs"><strong>{s.label}</strong><span>{STATUS[s.status]||s.status}</span></div>
     <p className="mt-1 text-[11px] text-slate-600">{BASIS[s.basis]||s.basis} · {s.selected_count} sources</p>
     {s.warning&&<p className="text-[11px] text-amber-800">{s.warning}</p>}
    </div>)}
    <div className="space-y-2">
     {sources.map(s=><div key={s.id} className="rounded-lg bg-slate-50 p-2.5 text-xs">
      <strong>{s.id}</strong> — {s.title||'Untitled source'}
      <p className="mt-1 text-slate-600">Type: {s.type} · Date: {s.date||'unknown'} · Incident location: {s.location_verified?s.location:'not established'}{s.duplicate_of?' · Possible repeat of '+s.duplicate_of:''}</p>
      {s.url?.startsWith('https://')&&<a href={s.url} target="_blank" rel="noreferrer noopener" className="text-blue-700 underline">Open attributed source</a>}
     </div>)}
    </div>
    <p className="text-[11px] text-slate-500">Saved records are fixed snapshots. Public links are live at query time, not independently verified or continuously monitored. No simulated sources are presented as live records.</p>
   </div>
  </details>
 </article>;
}

export default function AIAssistantV2({workspace='OPERATIONS'}){
 const {access}=useOutletContext()||{};
 const leader=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const [workflow,setWorkflow]=useState('AUTO');
 const [perspective,setPerspective]=useState(workspace==='MANAGEMENT'?'MANAGEMENT':'AUTO');
 const [sources,setSources]=useState({smartRadar:true,publicWeb:true,legalReferences:true});
 const [question,setQuestion]=useState(new URLSearchParams(window.location.search).get('q')||'');
 const [messages,setMessages]=useState([]);
 const [draftEdits,setDraftEdits]=useState({});
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const [showSources,setShowSources]=useState(false);
 const activeSources=Object.values(sources).some(Boolean);
 const ask=async(text)=>{
  const q=String(text||'').trim();
  if(!q||busy||!activeSources)return;
  setBusy(true);setError('');setQuestion('');
  const before=messages;
  const userMessage={role:'user',text:q};
  setMessages([...before,userMessage]);
  const last=before.map((m,i)=>({...m,index:i})).filter(m=>m.role==='assistant').at(-1);
  const previousDraft=last?.result?(draftEdits[last.index]??last.result.answer?.draft??''):'';
  try{
   const token=window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw Error('Sign in to access authorised research.');
   const response=await fetch('/api/ai-assistant/chat',{method:'POST',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify({question:q,workflow,perspective,sources,previousDraft,
     history:before.slice(-10).map(m=>({role:m.role,
      text:m.role==='assistant'?(m.result?.answer?.summary||'').slice(0,1500):m.text.slice(0,1500)}))})});
   const data=await response.json().catch(()=>({}));
   if(!response.ok){
    const detail=data.detail||data.error;
    throw Error(typeof detail==='string'?detail:'Research service unavailable ('+response.status+').');
   }
   setMessages([...before,userMessage,{role:'assistant',text:data.answer?.summary||'',result:data}]);
  }catch(e){
   setMessages(before);setQuestion(q);setError(e.message||'AI Assistant unavailable.');
  }finally{setBusy(false)}
 };
 if(workspace==='MANAGEMENT'&&!leader){
  return <section role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm">Management AI requires authorized leadership access.</section>;
 }
 return <div className="mx-auto max-w-[1190px] space-y-5" data-testid="ai-assistant-v2-page">
  <header className="rounded-2xl bg-gradient-to-r from-[#801b24] to-[#a52a2f] p-6 text-white">
   <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-red-100"><Sparkles size={16}/> Separate research workspace</div>
   <h1 className="mt-2 text-3xl font-bold">AI Assistant</h1>
   <p className="mt-2 max-w-3xl text-sm text-red-50">Research and analyse. Develop strategies and plans. Draft and refine summaries, memos and emails — grounded in sources you are authorised to access.</p>
   <div className="mt-4 flex flex-wrap gap-2">
    <Link to={workspace==='MANAGEMENT'?'/management/assistant':'/assistant'}
     className="rounded-lg border border-white/40 px-3 py-2 text-xs hover:bg-white/10">BAWASLU Intelligence Assistant (existing)</Link>
    {leader&&<Link to="/management" className="rounded-lg border border-white/40 px-3 py-2 text-xs hover:bg-white/10">Management home & executive brief</Link>}
   </div>
  </header>
  <section className="rounded-xl border border-slate-200 bg-white p-4">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <h2 className="font-semibold text-[#19364c]">How would you like to work?</h2>
    <label className="text-xs text-slate-600">Answer perspective
     <select aria-label="AI Assistant answer perspective" value={perspective} onChange={e=>setPerspective(e.target.value)}
      disabled={busy} className="ml-2 rounded-lg border border-slate-300 bg-white px-2 py-2">
      <option value="AUTO">Auto</option>
      {leader&&<option value="MANAGEMENT">Management</option>}
      <option value="OPERATIONAL">Operational</option>
     </select>
    </label>
   </div>
   <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="AI Assistant workflows">
    {WORKFLOWS.map(w=><button key={w.id} type="button" disabled={busy} aria-pressed={workflow===w.id}
     onClick={()=>setWorkflow(w.id)} className={'rounded-xl border p-3 text-left transition-colors '+(workflow===w.id?'border-[#a52a2f] bg-[#fff5f4]':'border-slate-200 bg-slate-50 hover:bg-slate-100')}>
     <w.icon className="mb-2 text-[#84232c]" size={19}/>
     <strong className="block text-sm">{w.title}</strong>
     <span className="block text-xs text-slate-500">{w.subtitle}</span>
    </button>)}
   </div>
   <div className="mt-3 border-t border-slate-100 pt-3">
    <button type="button" onClick={()=>setShowSources(v=>!v)} aria-expanded={showSources}
     className="flex items-center gap-2 text-sm font-medium text-[#19364c]"><BookOpen size={16}/> Research sources
     <span className="text-xs font-normal text-slate-500">{Object.values(sources).filter(Boolean).length}/3 enabled · {showSources?'Hide':'Manage'}</span>
    </button>
    {showSources&&<div className="mt-3 grid gap-2 md:grid-cols-3" data-testid="ai-assistant-v2-sources">
     {SOURCE_CHOICES.map(s=><label key={s.key} className="flex gap-2 rounded-lg border border-slate-200 p-3">
      <input type="checkbox" className="mt-1" disabled={busy} checked={sources[s.key]}
       onChange={e=>setSources(old=>({...old,[s.key]:e.target.checked}))}/>
      <span className="text-xs"><strong className="block text-slate-900">{s.label}</strong><span className="mt-1 block text-slate-500">{s.detail}</span></span>
     </label>)}
    </div>}
    <p className="mt-2 text-xs text-slate-500">Only consulted sources appear as consulted. Public web search may incur provider costs and is skipped for questions containing private IDs or personal contact information.</p>
   </div>
  </section>
  <div className="space-y-3">
   {!messages.length&&<section className="rounded-xl border border-slate-200 bg-white p-4">
    <h2 className="mb-3 text-sm font-semibold text-slate-800">Try a question</h2>
    <div className="grid gap-2 md:grid-cols-2">
     {PROMPTS.map(p=><button className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-3 text-left text-sm hover:bg-slate-50"
      type="button" key={p} disabled={busy} onClick={()=>setQuestion(p)}>{p}<ArrowRight size={16}/></button>)}
    </div>
   </section>}
   {messages.map((m,i)=>m.role==='user'?
    <div key={i} className="ml-auto max-w-3xl rounded-xl bg-[#f6edf0] p-4 text-sm text-[#411e24]">{m.text}</div>:
    <Result key={i} data={m.result} index={i} draftEdits={draftEdits} setDraftEdits={setDraftEdits} onFollowUp={setQuestion}/>)}
  </div>
  {error&&<div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
  <section className="sticky bottom-3 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
   <form onSubmit={e=>{e.preventDefault();ask(question)}} className="space-y-2">
    <textarea rows={2} maxLength={1000} aria-label="Ask AI Assistant" value={question} onChange={e=>setQuestion(e.target.value)}
     placeholder="Ask anything relevant to election oversight, law, cases, strategy, plans or drafting…"
     className="w-full resize-y rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-[#84232c]"/>
    <div className="flex items-center justify-between">
     <button type="button" className="intel-ghost text-xs" disabled={busy} onClick={()=>{setMessages([]);setDraftEdits({});setError('');setQuestion('');}}>
      <Plus size={15}/> New conversation
     </button>
     <button type="submit" disabled={busy||!question.trim()||!activeSources} className="intel-button">
      {busy?<Loader2 className="animate-spin" size={16}/>:<ArrowRight size={16}/>}
      {busy?'Researching…':'Ask AI'}
     </button>
    </div>
   </form>
   <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck size={13}/> Research and proposed actions require officer review. Drafts are never automatically sent. This new conversation is session-only.</p>
  </section>
 </div>;
}
