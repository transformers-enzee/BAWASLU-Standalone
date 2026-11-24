import {useState} from 'react';
import ReactMarkdown from 'react-markdown';
import {useOutletContext} from 'react-router-dom';
import {ArrowRight,BookOpen,ClipboardList,Copy,Database,Download,Globe2,
        Lightbulb,LoaderCircle,Scale,ShieldCheck,Search,TriangleAlert} from 'lucide-react';

/* Independent UI, session-only state, never imports either existing assistant. */
const CHANNELS=[
 {id:'WEB_ONLY',label:'Public web only',description:'Current public pages, no saved records',icon:Globe2},
 {id:'WEB_AND_RECORDS',label:'Web + SmartRadar',description:'Public evidence and separate authorized saved observations',icon:Database},
 {id:'RECORDS_ONLY',label:'SmartRadar only',description:'Authorized records, no public search',icon:BookOpen},
];
const TASKS=[['AUTO','Auto'],['RESEARCH','Research'],['LEGAL','Legal'],['STRATEGY','Strategy'],
             ['PLAN','Action plan'],['DRAFT','Drafting']];
const SAMPLES=[
 'What recent election-supervision developments should BAWASLU verify this week?',
 'Which institution has authority over an election organizer ethics allegation?',
 'Compare neutral oversight options with trade-offs and verification gates.',
 'Prepare a leadership briefing with institutional implications and proposed actions.',
];
const SOURCE_STATUS={READ:'Read page',SNIPPET_ONLY:'Snippet only',
 INACCESSIBLE:'Inaccessible',SAVED_SNAPSHOT:'Saved snapshot — not independently verified'};
const CLAIM_STATUS={PRIMARY_SOURCE_REPORTED:'Officially reported',PUBLIC_SOURCE_REPORTED:'Public source reported',SAVED_OBSERVATION:'Saved observation',
 INDEPENDENTLY_CORROBORATED:'Multiple read sources',ATTRIBUTED_ALLEGATION:'Allegation reported',
 CONFLICTING:'Sources conflict',INFERRED:'Interpretation',UNRESOLVED:'Unresolved'};
const safeLink=url=>typeof url==='string'&&/^https:\/\/[a-z0-9]/i.test(url);
const btn='rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40';

function CitationText({text,sources}){
 const byId=new Map((sources||[]).map(s=>[s.id,s]));
 return <>{String(text||'').split(/(\[(?:P|R)-\d+\])/g).map((part,i)=>{
  const ref=part.match(/^\[((?:P|R)-\d+)\]$/);
  const item=ref&&byId.get(ref[1]);
  if(!item)return <span key={i}>{part}</span>;
  return item.read_status==='READ'&&safeLink(item.url)?
   <a key={i} href={item.url} target="_blank" rel="noopener noreferrer"
    className="font-medium text-teal-800 underline" title={item.published_at||'Publication unknown'}>
    [{item.title||item.id}]</a>:
   <span key={i} title={item.title||''} className="font-semibold text-slate-600">[{item.id} · saved]</span>;
 })}</>;
}
// Render a full report rather than clipping it into the officer summary cards.
// Markdown is text-only: no raw HTML, images or arbitrary generated links.
function ReportMarkdown({text,sources}){
 const eligible=(sources||[]).filter(s=>s.read_status==='READ'&&safeLink(s.url));
 const allowed=new Map(eligible.map(s=>[s.id,s.url]));
 const urls=new Set(allowed.values());
 const linkify=value=>String(value||'').replace(/\[((?:P|R)-\d+)\](?!\()/g,(all,id)=>
  allowed.has(id)?'['+id+']('+allowed.get(id).replace(/[()]/g,c=>encodeURIComponent(c))+')':all);
 const permitted=url=>urls.has(url)||eligible.some(s=>s.url.replace(/[()]/g,c=>encodeURIComponent(c))===url)?url:'';
 const md=value=><ReactMarkdown skipHtml disallowedElements={['img']} urlTransform={permitted}
  components={{
   a:({href,children})=>href?<a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-teal-800 underline">{children}</a>:<span>{children}</span>,
   h1:({children})=><h2 className="mb-2 mt-5 text-xl font-bold">{children}</h2>,
   h2:({children})=><h3 className="mb-2 mt-5 text-lg font-bold text-slate-900">{children}</h3>,
   h3:({children})=><h4 className="mb-2 mt-4 font-semibold text-slate-900">{children}</h4>,
   p:({children})=><p className="my-3 leading-7">{children}</p>,
   ul:({children})=><ul className="my-3 list-disc space-y-2 pl-6">{children}</ul>,
   ol:({children})=><ol className="my-3 list-decimal space-y-2 pl-6">{children}</ol>,
   blockquote:({children})=><blockquote className="my-3 border-l-4 border-slate-300 pl-3">{children}</blockquote>,
   pre:({children})=><pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-3">{children}</pre>
  }}>{linkify(value)}</ReactMarkdown>;
 // Support GFM-style tables without adding a new dependency to the lockfile.
 const lines=String(text||'').split('\n'),blocks=[];
 let buf=[];
 const flush=()=>{if(buf.length){blocks.push({type:'text',value:buf.join('\n')});buf=[]}};
 const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(c=>c.trim().replace(/\\\|/g,'|'));
 for(let i=0;i<lines.length;i++){
  if(lines[i].includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])&&cells(lines[i+1]).every(c=>/^:?-{3,}:?$/.test(c))){
   flush();const head=cells(lines[i]);i++;const rows=[];
   while(i+1<lines.length&&lines[i+1].includes('|')&&lines[i+1].trim()){i++;rows.push(cells(lines[i]))}
   blocks.push({type:'table',head,rows});
  }else buf.push(lines[i]);
 }
 flush();
 return <div data-testid="officer-v3-full-report" className="min-w-0 break-words text-sm leading-7 text-slate-800">
  {blocks.map((b,i)=>b.type==='text'?<div key={i}>{md(b.value)}</div>:
   <div key={i} className="my-4 overflow-x-auto rounded-lg border border-slate-200">
    <table className="w-full border-collapse text-left text-sm"><thead className="bg-slate-50">
     <tr>{b.head.map((h,j)=><th key={j} className="min-w-24 border-b border-slate-200 px-3 py-2 align-top">{md(h)}</th>)}</tr>
    </thead><tbody>{b.rows.map((r,j)=><tr key={j} className="border-b border-slate-100">
     {b.head.map((_,k)=><td key={k} className="px-3 py-2 align-top">{md(r[k]||'')}</td>)}
    </tr>)}</tbody></table>
   </div>)}
 </div>;
}
function References({ids,sources}){
 const index=new Map((sources||[]).map(s=>[s.id,s]));
 const refs=(ids||[]).map(x=>index.get(x)).filter(Boolean);
 return <div className="mt-2 flex flex-wrap gap-2 text-xs">
  {refs.length?refs.map(src=>src.read_status==='READ'&&safeLink(src.url)?
   <a key={src.id} href={src.url} target="_blank" rel="noopener noreferrer"
    className="rounded-md bg-teal-50 px-2 py-1 text-teal-800 underline">
    {src.title||src.id} · {src.published_at||'undated'}</a>:
   <span key={src.id} className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">
    {src.id} · authorized snapshot</span>):
   <span className="text-amber-700">No source linked — reviewer must verify</span>}
 </div>;
}
function makeProduct(kind,r,data,question){
 const base=['OFFICER DECISION AI — DRAFT ONLY',
  'Question: '+question,'Mode: '+data.source_mode,
  'Research time: '+(data.research_trail?.retrieved_at||'unknown'),
  'Not an official finding, approval or assignment.',''];
 const claims=r.claims||[],actions=r.actions||[],laws=r.legal||[],options=r.options||[];
 let lines=[];
 if(kind==='MATRIX'){
  lines=['EVIDENCE MATRIX'];
  claims.forEach((c,i)=>lines.push((i+1)+'. '+c.claim,'  Status: '+c.status,
    '  Cited IDs: '+(c.source_ids||[]).join(', '),'  Gap: '+c.caveat));
 }else if(kind==='LEGAL'){
  lines=['LEGAL AND JURISDICTION REVIEW','Institutional nexus: '+r.relevance];
  laws.forEach((l,i)=>lines.push((i+1)+'. '+l.issue,'  Authority: '+l.institution,
    '  Provision: '+l.legal_reference,'  Applicability: '+l.applicability,
    '  Verify: '+l.verification_needed,'  Citations: '+(l.source_ids||[]).join(', ')));
 }else if(kind==='PLAN'){
  lines=['PROPOSED OFFICER ACTION PLAN','Decision: '+r.recommended_decision];
  actions.forEach((a,i)=>lines.push((i+1)+'. '+a.task,'  Reviewer: '+a.owner_role,
    '  Evidence: '+a.evidence_needed,'  Output: '+a.deliverable,
    '  Escalation or closure: '+a.decision_gate,'  Proposed target: '+(a.target_period||'To be agreed'),'  Success measure: '+(a.success_metric||'To be agreed')));
 }else{
  lines=['DRAFT LEADERSHIP MEMO','Subject: '+r.headline,'Key takeaway: '+r.key_takeaway,
    'BAWASLU implications: '+r.bawaslu_implication,
    'Recommended decision: '+r.recommended_decision,'Findings:'];
  claims.forEach((c,i)=>lines.push((i+1)+'. '+c.claim+' ['+(c.source_ids||[]).join(', ')+']'));
  lines.push('Options:');
  options.forEach((o,i)=>lines.push((i+1)+'. '+o.option+'; benefit '+o.benefit+'; trade-off '+o.tradeoff));
  lines.push('Proposed steps:');
  actions.forEach((a,i)=>lines.push((i+1)+'. '+a.task+' — '+a.owner_role));
 }
 return [...base,...lines,'','Unverified points:',...(r.limitations||[]).map(x=>'- '+x)].join('\n');
}

function WorkProduct({data,question}){
 const [kind,setKind]=useState('PLAN'),[copied,setCopied]=useState(false),[edits,setEdits]=useState({});
 const r=data.report||{},value=edits[kind]??makeProduct(kind,r,data,question);
 const copy=async()=>{try{await navigator.clipboard.writeText(value);setCopied(true)}catch{setCopied(false)}};
 const download=()=>{
  const url=URL.createObjectURL(new Blob([value],{type:'text/plain;charset=utf-8'}));
  const el=document.createElement('a');el.href=url;el.download='officer-review-'+kind.toLowerCase()+'.txt';
  el.click();URL.revokeObjectURL(url);
 };
 return <section className="space-y-3 rounded-xl border border-[#e9d5d6] bg-[#fff9f8] p-4" data-testid="officer-v3-work-products">
  <div className="flex items-center gap-2"><ClipboardList size={18} className="text-[#85212d]"/>
   <h3 className="font-bold text-slate-900">Prepare an officer work product</h3></div>
  <p className="text-xs text-slate-600">Local drafts for officer review only. No assignments, emails, cases or external messages are created.</p>
  <div className="flex flex-wrap gap-2">{[['MATRIX','Evidence matrix'],['LEGAL','Legal brief'],
   ['PLAN','Action plan'],['MEMO','Leadership memo']].map(([id,label])=><button key={id} type="button"
    aria-pressed={kind===id} onClick={()=>{setKind(id);setCopied(false)}}
    className={'rounded-md border px-3 py-2 text-xs '+(kind===id?'border-[#85212d] bg-[#85212d] text-white':'border-slate-300 bg-white text-slate-700')}>{label}</button>)}</div>
  <textarea className="w-full resize-y rounded-lg border border-slate-300 bg-white p-3 font-mono text-xs leading-5"
   rows={10} aria-label="Prepared review document" value={value}
   onChange={e=>setEdits(old=>({...old,[kind]:e.target.value}))}/>
  <div className="flex gap-2"><button type="button" className={btn} onClick={copy}><Copy size={14} className="mr-1 inline"/>
   {copied?'Copied':'Copy document'}</button>
   <button type="button" className={btn} onClick={download}><Download size={14} className="mr-1 inline"/>Download TXT</button></div>
 </section>;
}

function NumericSeries({series,sources}){
 return <section className="space-y-4" data-testid="officer-v3-numeric-series">
  <h3 className="text-lg font-semibold text-slate-900">Source-matched quantitative analysis</h3>
  {series.map((item,i)=>{
   const max=Math.max(1,...item.rows.map(x=>x.value));
   return <figure key={i} className="rounded-xl border border-slate-200 bg-white p-4">
    <figcaption className="font-semibold text-slate-900">{item.title}</figcaption>
    <p className="mb-3 text-xs text-slate-600">{item.election_type} · {item.period} · {item.case_status} · {item.unit}</p>
    {item.rows.map((row,j)=><div key={j} className="mb-2">
     <div className="flex justify-between gap-2 text-sm"><span>{row.label}</span><strong>{row.value.toLocaleString()}</strong></div>
     <div className="h-3 overflow-hidden rounded bg-slate-100"><div className="h-3 bg-teal-700" style={{width:(100*row.value/max)+'%'}}/></div>
    </div>)}
    <References ids={[...new Set(item.rows.map(row=>row.source_id))]} sources={sources}/>
    <p className="mt-2 text-xs text-slate-500">Source-matched values only; not a complete national dataset. Grouping and comparability require review.</p>
    <details className="mt-2 text-xs"><summary className="cursor-pointer">Original numeric evidence</summary>
     {item.rows.map((row,j)=><p key={j} className="mt-1">{row.source_id}: {row.source_quote}</p>)}</details>
   </figure>;
  })}
 </section>;
}
function Brief({data,question}){
 const r=data.report||{},audit=data.research_trail||{},sources=audit.sources||[];
 return <article className="space-y-5" data-testid="officer-v3-result">
  {data.task==='DRAFT'&&r.draft&&<section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="officer-v3-draft">
   <h3 className="font-bold text-slate-900">Requested draft · not sent</h3>
   <p className="mt-2 whitespace-pre-wrap text-sm leading-6"><CitationText text={r.draft} sources={sources}/></p>
  </section>}
  {data.source_mode!=='RECORDS_ONLY'&&audit.web_status!=='READ'&&
   <div role="alert" className="flex gap-2 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
    <TriangleAlert size={19} className="shrink-0"/>
    <span>Live public research was unavailable or returned no readable pages ({audit.web_status||'unknown'}).
     Any saved observations cannot verify current events.</span>
   </div>}
  <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <span className="text-xs font-bold uppercase tracking-widest text-[#85212d]">{data.research_depth==='DEEP'?'Deep research & strategic intelligence':data.research_depth==='QUICK'?'Quick answer':'Evidence-led research'}</span>
    {data.task==='LEGAL'&&data.research_depth!=='DEEP'&&<span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
     {r.relevance==='DIRECT'?'Direct nexus proposed':r.relevance==='POSSIBLE'?'Possible BAWASLU nexus':'Jurisdiction not established'}</span>}
   </div>
   <h2 className="mt-4 text-xl font-bold text-slate-900">{r.headline||'Officer briefing'}</h2>
   {data.research_depth!=='DEEP'&&<div className="mt-4 border-t border-slate-200 pt-4">
    <p className="text-xs font-bold uppercase tracking-wider text-[#85212d]">Key takeaway</p>
    <p className="mt-2 text-base font-semibold leading-7 text-slate-900"><CitationText text={r.key_takeaway} sources={sources}/></p>
    <p className="mt-2 text-sm leading-6 text-slate-700"><CitationText text={r.bawaslu_implication} sources={sources}/></p>
    <p className="mt-3 text-sm"><strong>Recommended decision:</strong> <CitationText text={r.recommended_decision} sources={sources}/></p>
   </div>}
   <ReportMarkdown text={r.answer} sources={sources}/>
  </section>
  {!!r.numeric_series?.length&&<NumericSeries series={r.numeric_series} sources={sources}/>}
  {!!r.claims?.length&&<details className="space-y-3 rounded-xl border border-slate-200 bg-white p-4" data-testid="officer-v3-claims" open={data.research_depth!=='DEEP'}>
   <summary className="cursor-pointer text-lg font-bold text-slate-900">Claim evidence and review notes</summary>
   {r.claims.map((claim,i)=><div key={i} className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex justify-between gap-3 text-xs"><strong className="text-[#85212d]">Finding {i+1}</strong>
     <span className="text-slate-500">{CLAIM_STATUS[claim.status]||'Unresolved'}</span></div>
    <p className="mt-2 text-sm leading-6 text-slate-800"><CitationText text={claim.claim} sources={sources}/></p>
    <References ids={claim.source_ids} sources={sources}/>
    {claim.caveat&&<p className="mt-2 text-xs text-slate-600">Verification: {claim.caveat}</p>}
   </div>)}
  </details>}
  {!!r.actions?.length&&<details className="space-y-3 rounded-xl border border-slate-200 bg-white p-4" data-testid="officer-v3-actions" open={data.research_depth!=='DEEP'}>
   <summary className="cursor-pointer text-lg font-bold text-slate-900">Proposed officer next steps</summary>
   {r.actions.map((a,i)=><div key={i} className="rounded-xl border border-[#e7d5d6] bg-white p-4">
    <div className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#85212d] text-xs font-bold text-white">{i+1}</span>
     <div className="space-y-1 text-xs text-slate-700">
      <strong className="block text-sm text-slate-900">{a.task}</strong>
      <p>Proposed reviewer: {a.owner_role}</p><p>Required evidence: {a.evidence_needed}</p>
      <p>Expected output: {a.deliverable}</p>
      {a.target_period&&<p>Proposed management target: {a.target_period}</p>}
      {a.priority_reason&&<p>Priority rationale: {a.priority_reason}</p>}
      {a.success_metric&&<p>Success measure: {a.success_metric}</p>}
      <p className="font-semibold text-[#85212d]">Escalation / closure gate: {a.decision_gate}</p>
      <References ids={a.source_ids} sources={sources}/>
     </div></div>
   </div>)}
  </details>}
  <details className="rounded-xl border border-slate-200 bg-white p-4" open={data.research_depth!=='DEEP'}>
   <summary className="cursor-pointer font-semibold">Prepare or download an officer work product</summary>
   <div className="mt-3"><WorkProduct data={data} question={question}/></div>
  </details>
  <details className="rounded-xl border border-slate-200 bg-white p-4" data-testid="officer-v3-research-trail">
   <summary className="cursor-pointer font-bold text-[#19364c]">Research Trail · sources, law, alternatives and audit</summary>
   <div className="mt-4 space-y-4 text-sm text-slate-700">
    <p>Research time: {audit.retrieved_at||'unknown'} · Web status: {audit.web_status||'unknown'} · Read pages: {audit.public_read_count||0} · Saved observations: {audit.saved_count||0}</p>
    <p className="text-xs text-slate-500">Actual provider queries: {(audit.search_queries||[]).join(' · ')||'No search query recorded'}</p>
    {!!data.requested_dimensions?.length&&<p>Requested analysis: {data.requested_dimensions.join(' · ')}</p>}
    {!!audit.coverage?.length&&<section className="space-y-1" data-testid="officer-v3-coverage">
     <h4 className="font-semibold">Requested objective coverage (not proof of completeness)</h4>
     {audit.coverage.map(row=><p key={row.objective} className="text-xs">{row.objective}: {row.status==='READABLE_LEADS'?'Readable leads':'Research incomplete'} · {row.read_count} readable sources · {row.attempts} attempts</p>)}
    </section>}
    {!!audit.search_passes?.length&&<div className="space-y-2" data-testid="officer-v3-research-passes">
     <h4 className="font-semibold">Research objectives and coverage</h4>
     {audit.search_passes.map((pass,i)=><div key={i} className="rounded bg-slate-50 p-2 text-xs">
      <strong>{pass.objective}</strong> · attempt {pass.attempt||1} · {pass.status} · {pass.discovered} discovered · {pass.read_count} readable
     </div>)}</div>}
    <section className="space-y-2"><h4 className="font-semibold">Public pages and saved observations</h4>
     {sources.length?sources.map(s=><div key={s.id} className="rounded-md bg-slate-50 p-3 text-xs" data-testid="officer-v3-source-row">
      <div className="flex justify-between gap-2"><strong>{s.id} · {s.title||'Source'}</strong>
       <span className={s.read_status==='READ'?'font-semibold text-teal-800':'font-semibold text-amber-800'}>
        {SOURCE_STATUS[s.read_status]||s.read_status}</span></div>
      <p className="mt-1">Published: {s.published_at||'unknown'} · Updated: {s.updated_at||'unknown'}</p>
      {s.reason&&<p className="text-slate-600">{s.reason}</p>}
      {s.document_type&&<p>Document: {s.document_type}{s.units_inspected?' · units inspected: '+s.units_inspected:''}</p>}
      {s.extraction_notes&&<p className="text-slate-600">{s.extraction_notes}</p>}
      {s.extraction_code&&<p>Extraction diagnostic: {s.extraction_code}{s.extraction_method?' · '+s.extraction_method:''}</p>}
      {s.objective&&<p className="text-slate-500">Research focus: {s.objective}</p>}
      {s.kind==='SAVED_RECORD'&&<p>Scoped saved observation: {s.record_id}</p>}
      {safeLink(s.url)&&<a href={s.url} target="_blank" rel="noopener noreferrer" className="break-all text-teal-800 underline">Open original</a>}
     </div>):<p>No consulted source available.</p>}
    </section>
    {!!r.legal?.length&&<section className="space-y-2"><h4 className="font-semibold">Applicable authority · human verification required</h4>
     {r.legal.map((l,i)=><div key={i} className="rounded-md border border-slate-200 p-3 text-xs">
      <strong>{l.issue} — {l.institution}</strong><p>Reference: {l.legal_reference}</p>
      <p>Applicability: {l.applicability}</p><p className="text-amber-800">Verify: {l.verification_needed}</p>
      {l.instrument_version&&<p>Instrument version: {l.instrument_version}</p>}
      {l.source_quote&&<p>Matched primary text excerpt: {l.source_quote}</p>}
      {l.practical_gap&&<p>Practical gap: {l.practical_gap}</p>}
      {l.proposed_reform&&<p>Proposed reform: {l.proposed_reform}</p>}
      {l.reform_owner&&<p>Responsible institution: {l.reform_owner}</p>}
      {l.tradeoff&&<p>Trade-off: {l.tradeoff}</p>}
      <References ids={l.source_ids} sources={sources}/></div>)}
    </section>}
    {!!r.options?.length&&<section className="space-y-2"><h4 className="font-semibold">Options and trade-offs</h4>
     {r.options.map((o,i)=><div key={i} className="rounded-md border border-slate-200 p-3 text-xs">
      <strong>{o.option}</strong><p>Benefit: {o.benefit}</p><p>Trade-off: {o.tradeoff}</p>
      <p>Review trigger: {o.change_trigger}</p><References ids={o.source_ids} sources={sources}/>
     </div>)}</section>}
    {!!r.limitations?.length&&<section><h4 className="font-semibold">Evidence gaps</h4>
     <ul className="list-disc pl-5 text-xs">{r.limitations.map((g,i)=><li key={i}>{g}</li>)}</ul></section>}
    <div className="rounded-md bg-slate-50 p-3 text-xs">
     <p>Structured claims with linked sources: {r.quality?.attributed_claims||0} · Without source links: {r.quality?.unsupported_claims||0}</p>
     {r.report_audit&&<div className="mt-2" data-testid="officer-v3-report-audit">
      <p>Numeric text lines matched to cited excerpts: {r.report_audit.numeric_lines_matched}/{r.report_audit.numeric_lines_checked}. This is not full claim verification.</p>
      {!!r.report_audit.review_flags?.length&&<details><summary className="cursor-pointer">Numeric text requiring review (may include proposed targets)</summary>
       {r.report_audit.review_flags.map((f,i)=><p key={i} className="mt-2">{f.reason}: {f.passage}</p>)}</details>}
     </div>}
     <p>Officer-verified legal applicability: No · Automated actions: None · Previous assistant history: Not accessed</p>
    </div>
   </div>
  </details>
 </article>;
}

export default function OfficerDecisionAssistant({workspace='OPERATIONS'}){
 const {access}=useOutletContext()||{};
 const leader=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const [mode,setMode]=useState('WEB_ONLY'),[task,setTask]=useState('AUTO');
 const [perspective,setPerspective]=useState(workspace==='MANAGEMENT'?'LEADERSHIP':'AUTO');
 const [question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [data,setData]=useState(null),[asked,setAsked]=useState('');
 async function ask(value){
  const q=String(value||'').trim();
  if(!q||busy)return;
  setBusy(true);setError('');setData(null);
  try{
   const token=window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':window.localStorage.getItem('bawaslu_access_token')||'';
   if(!token)throw new Error('Please sign in to use the independent assistant.');
   const response=await fetch('/api/officer-decision-ai/analyze',{
    method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify({question:q,source_mode:mode,task,perspective})});
   const value=await response.json().catch(()=>({}));
   if(!response.ok)throw new Error(typeof value.detail==='string'?value.detail:'Research unavailable ('+response.status+').');
   if(value.module!=='OFFICER_DECISION_AI_INDEPENDENT_V3')throw new Error('Unexpected API response.');
   setAsked(q);setData(value);
  }catch(e){setError(e.message||'Research temporarily unavailable')}
  finally{setBusy(false)}
 }
 if(workspace==='MANAGEMENT'&&!leader)return <div role="alert">Leadership authorization required.</div>;
 return <div className="mx-auto max-w-[1160px] space-y-5 pb-12" data-testid="officer-v3-page">
  <header className="rounded-2xl bg-[#761b27] p-7 text-white">
   <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-red-100"><ShieldCheck size={16}/> Independent new module</div>
   <h1 className="mt-3 text-2xl font-bold md:text-3xl">AI Assistant V2 <span className="font-normal text-red-100">· Deep Research & Strategic Intelligence</span></h1>
   <p className="mt-2 max-w-3xl text-sm leading-6 text-red-50">Adaptive public research, document analysis, evidence-led reports and practical BAWASLU recommendations. Every question starts fresh.</p>
  </header>
  <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
   <div className="flex flex-wrap justify-between gap-3"><div>
    <h2 className="text-lg font-bold text-slate-900">Ask a research or oversight question</h2>
    <p className="mt-1 text-xs text-slate-500">The authorized live provider receives only your public-search question, never saved SmartRadar source text.</p>
   </div><label className="text-xs text-slate-600">Perspective
    <select aria-label="Officer Decision AI perspective" value={perspective} onChange={e=>setPerspective(e.target.value)}
     disabled={busy} className="ml-2 rounded-md border border-slate-300 bg-white p-2">
     <option value="AUTO">Auto</option><option value="OFFICER">Officer</option>
     {leader&&<option value="LEADERSHIP">Leadership</option>}
    </select></label></div>
   <div className="mt-4 grid gap-2 sm:grid-cols-3" role="group" aria-label="New AI source modes" data-testid="officer-v3-source-modes">
    {CHANNELS.map(m=><button key={m.id} type="button" disabled={busy} onClick={()=>setMode(m.id)}
     aria-pressed={mode===m.id} className={'rounded-xl border p-4 text-left '+(mode===m.id?'border-[#85212d] bg-[#fff6f5]':'border-slate-200 bg-slate-50')}>
     <m.icon size={19} className="text-[#85212d]"/><strong className="mt-2 block text-sm text-slate-900">{m.label}</strong>
     <span className="mt-1 block text-xs text-slate-600">{m.description}</span></button>)}
   </div>
   <div className="mt-4"><p className="mb-2 text-xs font-semibold uppercase text-slate-500">Response type · research depth selected automatically</p>
    <div className="flex flex-wrap gap-2">{TASKS.map(([id,label])=><button key={id} type="button"
     disabled={busy} aria-pressed={task===id} onClick={()=>setTask(id)}
     className={'rounded-full border px-3 py-1.5 text-xs '+(task===id?'border-[#85212d] bg-[#85212d] text-white':'border-slate-200 text-slate-700')}>{label}</button>)}</div>
   </div>
   <form onSubmit={e=>{e.preventDefault();ask(question)}} className="mt-4">
    <label htmlFor="officer-v3-question" className="mb-2 block text-sm font-semibold text-slate-900">Your question</label>
    <textarea id="officer-v3-question" aria-label="Ask the new Officer Decision AI" value={question}
     onChange={e=>setQuestion(e.target.value)} disabled={busy} maxLength={1000} rows={3}
     className="w-full rounded-lg border border-slate-300 p-3 text-sm" placeholder="What changed and what should BAWASLU do?"/>
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
     <button className={btn} type="button" onClick={()=>{setQuestion('');setData(null);setAsked('');setError('')}} disabled={busy}>Clear and start fresh</button>
     <button className="inline-flex items-center gap-2 rounded-lg bg-[#85212d] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
      type="submit" disabled={busy||!question.trim()}>
      {busy?<LoaderCircle className="animate-spin" size={17}/>:<Search size={17}/>}
      {busy?'Researching sources and composing your report…':'Generate officer brief'}<ArrowRight size={15}/></button>
    </div>
   </form>
   {!data&&!busy&&<div className="mt-5 grid gap-2 sm:grid-cols-2" data-testid="officer-v3-starters">
    {SAMPLES.map(item=><button key={item} type="button" onClick={()=>setQuestion(item)}
     className="rounded-lg border border-slate-200 p-3 text-left text-xs text-slate-700 hover:bg-slate-50">
     <Lightbulb size={15} className="mr-2 inline text-[#85212d]"/>{item}</button>)}</div>}
  </section>
  {error&&<p role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
  {data&&<Brief key={asked} data={data} question={asked}/>}
  <p className="flex gap-2 text-xs text-slate-500"><ShieldCheck size={15}/>
   New, read-only research engine. No existing assistant conversation, draft, prompt or history is imported.</p>
 </div>;
}
