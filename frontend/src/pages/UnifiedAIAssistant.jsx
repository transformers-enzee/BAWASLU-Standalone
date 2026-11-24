import {useMemo,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {ArrowRight,BookOpen,CheckCircle2,ClipboardCopy,Compass,FilePenLine,
 Globe2,Lightbulb,Loader2,Plus,Search,ShieldCheck,Sparkles,Target} from 'lucide-react';

const MODES=[
 {id:'WEB_ONLY',name:'Web only',detail:'Live public research only — no saved SmartRadar or PDF records'},
 {id:'WEB_SMARTRADAR',name:'Web + SmartRadar',detail:'Compare independently read public sources with authorised fixed records'},
 {id:'SMARTRADAR_ONLY',name:'SmartRadar only',detail:'Saved observations and authorised reference pages; no live search'}
];
const STARTERS=[
 'What are the latest official election-oversight developments in Indonesia?',
 'What changed in relevant official news over the past 2 weeks?',
 'Recommend three lawful strategies and a 30/60/90-day plan for an oversight challenge.',
 'Draft an executive memo identifying evidence gaps and next decisions.'
];
const PERSPECTIVES=[
 {id:'AUTO',name:'Auto'},
 {id:'EXECUTIVE',name:'Executive'},
 {id:'OPERATIONAL',name:'Operational'},
 {id:'RESEARCH',name:'Research'},
];
const WORKFLOWS=[
 {id:'AUTO',name:'Adapt automatically'},
 {id:'RESEARCH',name:'Research & analysis'},
 {id:'STRATEGY',name:'Strategy & action planning'},
 {id:'DRAFTING',name:'Drafting & revision'},
];
const STATUS_LABEL={
 READ:'Read · original page opened',SNIPPET_ONLY:'Snippet only · not read',
 INACCESSIBLE:'Inaccessible · not read',SAVED_SNAPSHOT:'Fixed saved snapshot',
 READ_SOURCES_AVAILABLE:'Readable sources available',
 NO_READABLE_PUBLIC_PAGES:'No readable public pages',
};
const basisLabel={LIVE_PUBLIC_LOOKUP:'Live when retrieved',FIXED_SAVED_SNAPSHOT:'Fixed saved record',SIMULATED_DEMO:'Simulated demo'};

function Citations({ids,sources}){
 const map=new Map((sources||[]).map(s=>[s.id,s]));
 const refs=(ids||[]).map(id=>map.get(id)).filter(Boolean);
 return refs.length?<span className="ml-1 inline-flex flex-wrap gap-1.5 align-middle">
   {refs.map(s=>s.url?.startsWith('https://')?<a key={s.id} href={s.resolved_url||s.url}
      target="_blank" rel="noopener noreferrer" title={s.title}
      className="rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-blue-800 hover:underline">
      {s.id} · {s.read_status==='READ'?'read':'saved'}</a>:
      <span key={s.id} title={s.title}
       className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600">{s.id} · saved</span>)}
  </span>:<span className="ml-2 text-[11px] text-amber-800">Inference — no validated citation</span>;
}
function Content({title,children}){
 return <section className="space-y-2"><h3 className="text-sm font-bold text-[#18384c]">{title}</h3>{children}</section>;
}
function SourceTrail({result}){
 const status=result.public_research||{};
 const sources=result.sources||[];
 return <details className="rounded-xl border border-slate-200 bg-white p-4" data-testid="unified-research-trail">
  <summary className="cursor-pointer text-sm font-semibold text-[#18384c]">Research Trail · consulted sources, dates and coverage</summary>
  <div className="mt-3 space-y-4 text-xs">
   <div className="rounded-lg bg-slate-50 p-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <strong>Live public research</strong><span className="font-semibold">{STATUS_LABEL[status.status]||status.status||'Not selected'}</span>
    </div>
    <p className="mt-1 text-slate-600">Retrieved: {status.as_of||'Not applicable'} · Public pages actually read: {status.read_count??0}</p>
    {status.date_window&&<p className="text-slate-600">Requested time window: {status.date_window.start}–{status.date_window.end} (Indonesia calendar days)</p>}
    {!!status.attempts?.length&&<p className="mt-2 text-slate-600">Search passes: {status.attempts.map(a=>a.phase+' — '+a.status+' ('+(a.discovered||0)+' leads)').join(' · ')}</p>}
    {!!status.queries?.length&&<p className="mt-2 text-slate-500">Actual search queries: {status.queries.join(' · ')}</p>}
   </div>
   <div className="grid gap-2 sm:grid-cols-3">
    {(result.source_consultation||[]).map(row=><div key={row.key} className="rounded-lg border border-slate-200 p-3">
      <strong>{row.label}</strong>
      <p className="mt-1 text-slate-600">{row.status} · {basisLabel[row.basis]||row.basis}</p>
      <p className="text-slate-500">{row.read_count??row.count??0} read/saved · {row.snippet_count??0} snippet-only · {row.inaccessible_count??0} inaccessible</p>
    </div>)}
   </div>
   {!sources.length&&<p className="text-amber-900">No eligible sources were found for this question. A web lookup is not equivalent to reading a page.</p>}
   {sources.map(s=><div key={s.id} className="rounded-lg border border-slate-200 p-3" data-testid="unified-source-row">
    <div className="flex flex-wrap justify-between gap-2">
      <strong className="text-slate-900">{s.id} · {s.title||'Untitled source'}</strong>
      <span className={s.read_status==='READ'?'font-semibold text-green-800':'text-amber-800'}>
       {STATUS_LABEL[s.read_status]||s.read_status}</span>
    </div>
    <p className="mt-1 text-slate-600">Type: {s.type} · Published: {s.published_at||'unknown'} · Updated: {s.updated_at||'unknown'} · Basis: {basisLabel[s.basis]||s.basis}</p>
    <p className="text-slate-600">Incident location: {s.location_verified?s.location:'not verified'}{s.duplicate_of?' · Possible duplicate of '+s.duplicate_of:''}{s.within_period===false?' · Outside requested period':''}</p>
    {s.reason&&<p className="mt-1 text-amber-800">{s.reason}</p>}
    {s.url?.startsWith('https://')&&<a href={s.resolved_url||s.url} target="_blank" rel="noopener noreferrer"
       className="mt-1 block break-all text-blue-800 underline">Open source page</a>}
    {!!s.excerpt&&<details className="mt-2 rounded bg-slate-50 p-2"><summary className="cursor-pointer font-medium">Original retrieved excerpt</summary>
       <p className="mt-2 whitespace-pre-wrap leading-5 text-slate-700">{s.excerpt}</p></details>}
   </div>)}
   <p className="text-slate-500">A source link or stored snapshot does not independently establish an allegation. Simulated fixtures are never presented as live evidence. Current legal authority and case consequences require officer verification.</p>
  </div>
 </details>;
}

function AssistantReply({data,index,edits,setEdits,onFollowUp}){
 const a=data.answer||{},management=data.workspace==='MANAGEMENT',sources=data.sources||[];
 const draft=edits[index]??a.draft??'';
 const [copyStatus,setCopyStatus]=useState('');
 const copy=async()=>{try{await navigator.clipboard.writeText(draft);setCopyStatus('Draft copied for staff review.');}
                      catch{setCopyStatus('Copy unavailable; select the text manually.');}};
 const action=(text)=>onFollowUp(text);
 return <article className="space-y-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-6" data-testid="unified-ai-answer">
  <div className="flex flex-wrap items-center justify-between gap-2">
   <div className="flex items-center gap-2 font-bold text-[#18384c]"><Sparkles size={18}/> AI Assistant · {management?'Management':'Operational'}</div>
   <div className="flex flex-wrap gap-2 text-xs">
    {management&&<span className="rounded-full border border-amber-200 px-2 py-1 text-amber-900">Attention: {a.attention||'Unassessed'}</span>}
    <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Confidence: {a.confidence||'Unassessed'}</span>
   </div>
  </div>
  <section className="space-y-2">
   <h3 className="text-sm font-bold text-[#18384c]">{management?'Executive conclusion':'What to do first'}</h3>
   <p className="whitespace-pre-wrap text-sm leading-6 text-slate-900">{a.lead||'No supported conclusion is available.'}</p>
   {!management&&a.first_step&&<p className="rounded-lg border-l-2 border-[#a52a2f] bg-[#fff8f7] p-3 text-sm font-semibold text-[#61262d]">{a.first_step}</p>}
  </section>
  {a.draft&&<Content title="Editable draft · staff review only">
    <textarea data-testid="unified-ai-draft" aria-label="Editable AI Assistant draft"
      rows={Math.min(20,Math.max(7,draft.split('\n').length+2))} value={draft}
      onChange={e=>setEdits(old=>({...old,[index]:e.target.value}))}
      className="w-full rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm leading-6"/>
    <div className="flex flex-wrap gap-2">
     <button type="button" className="intel-ghost text-xs" onClick={copy}><ClipboardCopy size={14}/> Copy</button>
     <button type="button" className="intel-ghost text-xs" onClick={()=>action('Shorten the draft while keeping sources, uncertainty and institutional limitations.')}>Shorten</button>
     <button type="button" className="intel-ghost text-xs" onClick={()=>action('Rewrite the draft for BAWASLU national leadership, retaining citations and caveats.')}>Change audience</button>
     <button type="button" className="intel-ghost text-xs" onClick={()=>action('Turn the draft into a professional email reply. Do not send it.')}>Turn into email</button>
    </div>
    {copyStatus&&<p role="status" className="text-xs text-slate-600">{copyStatus}</p>}
    <p className="text-xs text-amber-900">Not sent, approved, filed or assigned. Authorised staff must verify and decide.</p>
   </Content>}
  {!!a.findings?.length&&<Content title="Source-linked findings">
    {a.findings.map((f,i)=><div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3" data-testid="unified-finding">
     <p className="text-sm leading-6 text-slate-900">{f.claim}<Citations ids={f.source_ids} sources={sources}/></p>
     <p className="mt-1 text-[11px] text-slate-600">{String(f.evidence_class||'').replaceAll('_',' ')} · {String(f.support||'').replaceAll('_',' ')}</p>
     {f.uncertainty&&<p className="mt-1 text-xs text-amber-900">Uncertainty: {f.uncertainty}</p>}
    </div>)}
   </Content>}
  {(a.what_changed||a.why_it_matters)&&<Content title={management?'What changed and why it matters':'Assessment and implications'}>
    {a.what_changed&&<p className="whitespace-pre-wrap text-sm text-slate-700">{a.what_changed}</p>}
    {a.why_it_matters&&<p className="whitespace-pre-wrap text-sm text-slate-700">{a.why_it_matters}</p>}
   </Content>}
  {(a.geographic_implications||a.institutional_implications)&&<Content title="Geographic and institutional implications">
    {a.geographic_implications&&<p className="text-sm text-slate-700"><strong>Geography:</strong> {a.geographic_implications}</p>}
    {a.institutional_implications&&<p className="text-sm text-slate-700"><strong>Institution:</strong> {a.institutional_implications}</p>}
   </Content>}
  {!!a.options?.length&&<Content title="Strategic options and trade-offs">
    <div className="grid gap-2 md:grid-cols-2">{a.options.map((o,i)=><div key={i} className="rounded-lg border border-slate-200 p-3 text-sm">
     <strong>{o.title}</strong>
     <p className="mt-2 text-slate-700">Benefit: {o.benefit}</p>
     <p className="mt-1 text-amber-900">Trade-off: {o.tradeoff}</p>
     {o.reason&&<p className="mt-1 text-slate-600">Reasoning: {o.reason}</p>}
     <Citations ids={o.source_ids} sources={sources}/>
    </div>)}</div>
   </Content>}
  {a.recommendation&&<Content title={management?'Recommended institutional response':'Proposed response'}>
    <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{a.recommendation}</p>
   </Content>}
  {!!a.plan?.length&&<Content title="Proposed action plan · not assigned">
    {a.plan.map((p,i)=><div key={i} className="rounded-lg border border-slate-200 p-3" data-testid="unified-action">
     <p className="text-sm font-semibold">{i+1}. {p.task}<Citations ids={p.source_ids} sources={sources}/></p>
     <div className="mt-2 grid gap-2 text-xs text-slate-700 sm:grid-cols-2">
      <p><strong>Suggested owner role:</strong> {p.owner_role||'To be determined'}</p>
      <p><strong>Proposed milestone:</strong> {p.milestone||'To be agreed'}</p>
      <p><strong>Evidence needed:</strong> {p.evidence_needed||'To be confirmed'}</p>
      <p><strong>Management/officer review:</strong> {p.review_point||'Awaiting review'}</p>
     </div>
     {p.decision_gate&&<p className="mt-2 text-xs text-amber-900">Escalation or closure gate: {p.decision_gate}</p>}
    </div>)}
   </Content>}
  {!!a.legal_checks?.length&&<Content title="Potential rules, authority and deadlines to verify">
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{a.legal_checks.map((x,i)=><li key={i}>{x}</li>)}</ul>
   </Content>}
  {!!a.watch_next?.length&&<Content title="What to watch next">
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{a.watch_next.map((x,i)=><li key={i}>{x}</li>)}</ul>
   </Content>}
  {!!a.uncertainties?.length&&<Content title="Remaining uncertainty">
    <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">{a.uncertainties.map((x,i)=><li key={i}>{x}</li>)}</ul>
   </Content>}
  {!!data.warnings?.length&&<div role="note" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
    <strong>Research limitations</strong>
    {data.warnings.map((x,i)=><p key={i} className="mt-1">{x}</p>)}
   </div>}
  <SourceTrail result={data}/>
  <div className="flex flex-wrap gap-2">
   <button type="button" className="intel-ghost text-xs" onClick={()=>action('Compare at least two possible institutional strategies and recommend the most proportionate option with evidence gates.')}>Compare solutions</button>
   <button type="button" className="intel-ghost text-xs" onClick={()=>action('Turn the preceding findings into a proposed action plan with owner roles, milestones and review points.')}>Create action plan</button>
   <button type="button" className="intel-ghost text-xs" onClick={()=>action('Draft a BAWASLU leadership memo from the findings, preserving uncertainties and citations.')}>Draft memo</button>
  </div>
  <p className="text-[11px] text-slate-500">AI proposals are not legal determinations. No official action, assignment or communication has been executed.</p>
 </article>;
}

export default function UnifiedAIAssistant({workspace='OPERATIONAL'}){
 const {access}=useOutletContext()||{};
 const leader=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const [sourceMode,setSourceMode]=useState('WEB_ONLY');
 const [perspective,setPerspective]=useState('AUTO');
 const [workflow,setWorkflow]=useState('AUTO');
 const [question,setQuestion]=useState(new URLSearchParams(window.location.search).get('q')||'');
 const [messages,setMessages]=useState([]);
 const [edits,setEdits]=useState({});
 const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);
 const [pilot,setPilot]=useState(false);
 const level=access?.geographic_scope==='Nationwide'?'BAWASLU RI':
             access?.geographic_scope==='Province'?'BAWASLU province':
             access?.geographic_scope==='Regency/City'?'BAWASLU kabupaten/kota':'BAWASLU officer';
 const setMode=id=>{setSourceMode(id);setMessages([]);setEdits({});setError('');};
 const submit=async(text)=>{
  const q=String(text||'').trim();if(!q||busy)return;
  setBusy(true);setError('');setQuestion('');
  const before=messages;
  const last=before.map((m,i)=>({...m,index:i})).filter(m=>m.role==='assistant').at(-1);
  const previousDraft=last?.result?(edits[last.index]??last.result.answer?.draft??''):'';
  setMessages([...before,{role:'user',text:q}]);
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token&&!window.__BAWASLU_DEMO_REPLICA__)throw Error('Sign in before using authorised assistant services.');
   const response=await fetch('/api/ai-assistant/chat',{method:'POST',headers:{
    'Content-Type':'application/json','Authorization':'Bearer '+(window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':token)},
    body:JSON.stringify({question:q,workspace,sourceMode,perspective,workflow,previousDraft,
     history:before.slice(-10).map(m=>({role:m.role,
      text:m.role==='assistant'?String(m.result?.answer?.lead||'').slice(0,1100):m.text.slice(0,1100)}))})});
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Assistant request failed ('+response.status+').');
   setMessages([...before,{role:'user',text:q},{role:'assistant',text:data.answer?.lead||'',result:data}]);
  }catch(e){setMessages(before);setQuestion(q);setError(e.message||'Assistant unavailable');}
  finally{setBusy(false)}
 };
 if(workspace==='MANAGEMENT'&&!leader){
  return <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-5 text-sm">Management AI requires an authorised leadership role. Use the Operational workspace for officer-level decisions.</div>;
 }
 return <main className="mx-auto max-w-[1190px] space-y-5" data-testid="unified-ai-page">
  <header className="rounded-2xl bg-gradient-to-r from-[#173950] to-[#24566b] px-6 py-7 text-white">
   <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-sky-100"><Sparkles size={16}/> SmartRadar · {workspace==='MANAGEMENT'?'Management intelligence':'Operational intelligence'}</div>
   <h1 className="mt-2 text-3xl font-bold">AI Assistant</h1>
   <p className="mt-2 max-w-4xl text-sm text-sky-50">
     {workspace==='MANAGEMENT'?'Executive conclusions, evidence-backed choices, institutional strategy and leadership review.':
      'First actions, original evidence, jurisdiction checks, responsible reviewer roles and operational plans.'}
   </p>
   <p className="mt-3 text-xs text-sky-100">Current office: {level} · {access?.province||'Authorised jurisdiction'} · Reply language follows your question</p>
   {workspace==='MANAGEMENT'&&<Link to="/management" className="mt-3 inline-block text-xs font-semibold text-white underline">Management homepage and executive brief</Link>}
  </header>
  <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 md:p-5">
   <div>
    <h2 className="text-sm font-bold text-[#18384c]">Research source mode</h2>
    <p className="mt-1 text-xs text-slate-600">Web only excludes SmartRadar records even when live research is unavailable. Changing source mode begins a new conversation.</p>
    <div className="mt-3 grid gap-2 md:grid-cols-3" role="group" aria-label="AI Assistant research source mode" data-testid="unified-source-modes">
     {MODES.map(m=><button key={m.id} type="button" disabled={busy} onClick={()=>setMode(m.id)}
      aria-pressed={sourceMode===m.id} className={'rounded-xl border p-3 text-left '+(sourceMode===m.id?'border-[#9b2e34] bg-red-50':'border-slate-200 bg-slate-50 hover:bg-slate-100')}>
      <strong className="block text-sm">{m.name}</strong>
      <span className="mt-1 block text-xs text-slate-600">{m.detail}</span>
     </button>)}
    </div>
   </div>
   <div className="grid gap-3 sm:grid-cols-2">
    <label className="text-xs font-semibold text-slate-700">Optional answer perspective
     <select aria-label="Assistant perspective" value={perspective} disabled={busy} onChange={e=>setPerspective(e.target.value)}
      className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
      {PERSPECTIVES.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
     </select></label>
    <label className="text-xs font-semibold text-slate-700">Optional workflow
     <select aria-label="Assistant workflow" value={workflow} disabled={busy} onChange={e=>setWorkflow(e.target.value)}
      className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
      {WORKFLOWS.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
     </select></label>
   </div>
  </section>
  {!messages.length&&<section className="rounded-xl border border-slate-200 bg-white p-4">
   <h2 className="text-sm font-bold text-[#18384c]">Start with any question</h2>
   <div className="mt-3 grid gap-2 md:grid-cols-2">
    {STARTERS.map(q=><button key={q} type="button" onClick={()=>setQuestion(q)} className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">{q}<ArrowRight size={15} className="shrink-0"/></button>)}
   </div>
   <details className="mt-3 text-xs text-slate-700" open={pilot} onToggle={e=>setPilot(e.currentTarget.open)}>
    <summary className="cursor-pointer font-semibold">Controlled officer walkthrough · unverified demo source IDs</summary>
    <p className="mt-2">Bryan and Grace can review SOCIAL-740 and SOCIAL-1160 as explicitly unverified saved observations. This requires selecting SmartRadar only (not Web only) and authorised access. These IDs do not establish a violation or an escalation deadline.</p>
    <button type="button" className="intel-ghost mt-2 text-xs" onClick={()=>{setMode('SMARTRADAR_ONLY');setQuestion(workspace==='MANAGEMENT'?'Assess SOCIAL-740 and SOCIAL-1160 as unverified observations. What does leadership need to decide, what would justify escalation, and is management intervention warranted?':'Examine SOCIAL-740 and SOCIAL-1160 as unverified reports. What original evidence should the officer verify, where might it be obtained, who should review it, and when would escalation be justified?');}}>
     <BookOpen size={14}/> Prepare controlled review question
    </button>
   </details>
  </section>}
  <div className="space-y-4">
   {messages.map((m,i)=>m.role==='user'?
    <div key={i} className="ml-auto max-w-[830px] rounded-2xl bg-[#f4e7e8] p-4 text-sm text-[#52242a]">{m.text}</div>:
    <AssistantReply key={i} data={m.result} index={i} edits={edits} setEdits={setEdits} onFollowUp={setQuestion}/>)}
  </div>
  {error&&<div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
  <section className="sticky bottom-2 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
   <form onSubmit={e=>{e.preventDefault();submit(question)}} className="space-y-2">
    <textarea rows={2} maxLength={1600} value={question} onChange={e=>setQuestion(e.target.value)}
      aria-label="Ask AI Assistant" placeholder="Ask for research, an operational decision, a strategy, action plan, or a draft…"
      className="w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm"/>
    <div className="flex justify-between gap-2">
     <button className="intel-ghost text-xs" disabled={busy} type="button" onClick={()=>{setMessages([]);setEdits({});setQuestion('');setError('');}}><Plus size={14}/> New conversation</button>
     <button className="intel-button" type="submit" disabled={busy||!question.trim()}>
      {busy?<Loader2 size={16} className="animate-spin"/>:<ArrowRight size={16}/>}
      {busy?'Researching…':'Ask AI'}
     </button>
    </div>
   </form>
   <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><ShieldCheck size={12}/> All responses are provisional. Drafts, plans and recommendations require authorised human review. This conversation is session-only.</p>
  </section>
 </main>;
}
