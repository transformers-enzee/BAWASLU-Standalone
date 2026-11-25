import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {CheckCircle2,AlertTriangle,FlaskConical,PlayCircle} from 'lucide-react';

const AUTH=()=>({Authorization:'Bearer '+(window.localStorage.getItem('bawaslu_access_token')||'')});
async function request(url,body){
 const res=await fetch(url,{method:body?'POST':'GET',cache:'no-store',headers:{...AUTH(),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'QA request unsuccessful');
 return data;
}
const LABEL={primary_issue:'Main issue',violation_type:'Possible violation',allegation_status:'Allegation status',verification_status:'Verification status',evidence_strength:'Evidence strength',review_priority:'Review priority',candidate_role:'Person’s role',event_location:'Event location',location_basis:'Location source',jurisdiction_status:'Jurisdiction',location_confidence:'Location confidence',election_type:'Election type',competent_authority:'Responsible office',duplicate_cluster_id:'Related posts',incident_cluster_id:'Incident group',corroborating_sources:'Independent corroboration',sentiment:'Sentiment',sentiment_target:'Sentiment target',human_review_status:'Officer review status',contradicting_sources:'Contradictory sources',source_authenticity:'Source authenticity'};
const WORDS={substantiated_by_authority:'Proven by authority',allegation:'Unverified allegation',inconclusive:'Not established',unverified:'Not verified',verified:'Verified',uncorroborated:'No independent confirmation',needs_verification:'Needs verification',money_politics:'Possible money politics',none:'No particular violation',unknown:'Unknown',uncertain:'Uncertain',in_scope:'In scope',requires_review:'Requires jurisdiction review',quoted_denial:'Person denying the allegation',accused:'Person accused',public_criticism:'General public criticism',account_profile:'Profile location, not event location',PILKADES:'Village-head election'};
const format=v=>v==null?'Not provided':WORDS[String(v)]||String(v).replaceAll('_',' ');
const label=k=>LABEL[k]||k.replaceAll('_',' ');
const panel='rounded-xl border border-slate-200 bg-white p-4 sm:p-5';
const primary='rounded-lg bg-[#851b29] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50';
const secondary='rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 disabled:opacity-50';

export default function AssessmentQAWorkbench(){
 const [catalog,setCatalog]=useState(null),[live,setLive]=useState(null),[caseId,setCaseId]=useState(''),
 [result,setResult]=useState(null),[mode,setMode]=useState(''),[busy,setBusy]=useState(''),[error,setError]=useState(''),[feedback,setFeedback]=useState('');
 const selected=catalog?.cases.find(x=>x.id===caseId);
 const ready=Boolean(live?.enabled&&live?.daily_remaining>0&&live?.total_remaining>0);
 async function refresh(){
  setError('');
  try{const c=await request('/api/intelligence-assessment-qa/catalog');setCatalog(c);
    setCaseId(prev=>c.cases.some(x=>x.id===prev)?prev:c.cases[0]?.id||'');
    setLive(await request('/api/intelligence-assessment-live-qa/status').catch(()=>null));
  }catch(e){setError(e.message);setCatalog(null)}
 }
 useEffect(()=>{refresh()},[]);
 function choose(id){setCaseId(id);setResult(null);setMode('');setError('');setFeedback('')}
 async function preview(){
   setBusy('demo');setResult(null);setError('');setFeedback('');
   try{setResult(await request('/api/intelligence-assessment-qa/evaluate',{case_id:selected.id,predictions:selected.sample_predictions}));setMode('example')}
   catch(e){setError(e.message)}finally{setBusy('')}
 }
 async function actual(){
   if(!selected||selected.id==='approved-override')return;
   if(!window.confirm('Run one paid AI assessment of this fictional post? This uses OpenAI credits and a limited QA budget. No officer records are modified.'))return;
   setBusy('live');setResult(null);setError('');setFeedback('');
   try{const r=await request('/api/intelligence-assessment-live-qa/run',{case_id:selected.id});
     setResult({...r.comparison,ai_summary:r.summary,recommended_check:r.recommended_check,model:r.model,quote_valid:r.evidence_quote_verified});setMode('real')}
   catch(e){setError(e.message)}finally{setBusy('');request('/api/intelligence-assessment-live-qa/status').then(setLive).catch(()=>setLive(null))}
 }
 const matches=result?.details.filter(x=>x.status==='MATCH')||[];
 const problems=result?.details.filter(x=>x.status!=='MATCH')||[];
 return <main data-testid="intelligence-assessment-qa-workbench" data-i18n-exempt="true" className="mx-auto max-w-6xl space-y-5 pb-8">
  <header className="space-y-2">
   <Link to="/administration" className="text-sm text-slate-600 underline">Back to Administration</Link>
   <p className="text-xs font-bold uppercase tracking-widest text-[#851b29] flex items-center gap-2"><FlaskConical size={16}/> SmartRadar quality assurance</p>
   <h1 className="text-2xl font-bold">AI Assessment Testing Centre</h1>
   <p className="text-sm text-slate-600">Choose a case, run a check, and see which answers need improvement. No JSON editing required.</p>
  </header>
  <section data-testid="assessment-qa-synthetic-warning" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
   <AlertTriangle size={20} className="shrink-0"/><p><strong>Safe testing:</strong> All posts are fictional. Free examples do not use AI. Real AI tests use credits only after you confirm. Reference answers are illustrative, not officer-approved gold labels. No real cases or officer decisions change.</p>
  </section>
  {error&&<p role="alert" data-testid="assessment-qa-error" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
  {!catalog&&!error&&<p role="status">Loading cases…</p>}
  {catalog&&<div className="grid gap-4 lg:grid-cols-[260px_1fr]">
   <aside className={panel+' h-fit'} aria-label="Choose a test scenario">
    <h2 className="font-semibold">1. Choose a scenario</h2>
    <div className="mt-3 space-y-2">{catalog.cases.map((c,i)=>
     <button key={c.id} data-testid={'assessment-case-'+c.id} aria-current={c.id===caseId?'true':undefined} onClick={()=>choose(c.id)}
       className={'block w-full rounded-lg border p-3 text-left text-sm '+(caseId===c.id?'border-[#851b29] bg-[#fff5f5]':'border-slate-200 hover:bg-slate-50')}>
       <span className="text-xs text-slate-500">Test {i+1} of {catalog.cases.length}</span><span className="block font-semibold mt-1">{c.title}</span>
     </button>)}</div>
   </aside>
   <div className="space-y-4">
    {selected&&<section data-testid="assessment-source-card" className={panel+' space-y-3'}>
     <h2 className="font-semibold">2. Read the fictional social post</h2>
     <p className="bg-slate-50 rounded-lg p-4 text-sm leading-6">{selected.source_text}</p>
     <h3 className="font-semibold text-sm">What should the AI understand?</h3>
     <ul className="space-y-2" data-testid="assessment-expected-summary">{Object.entries(selected.expected).map(([key,v])=>
      <li key={key} className="flex gap-2 text-sm"><CheckCircle2 className="text-slate-500 shrink-0 mt-0.5" size={15}/><span><strong>{label(key)}:</strong> {format(v)}</span></li>)}</ul>
     <p className="text-xs text-slate-600">Why it matters: {selected.review_note}</p>
    </section>}
    {selected&&<section className={panel+' space-y-3'}>
     <h2 className="font-semibold">3. Test the assessment</h2>
     <p className="text-sm text-slate-600">{selected.id==='approved-override'?'This checks approved correction precedence without AI.':'Choose a real AI test, or try a free prepared example first.'}</p>
     <div className="flex flex-wrap gap-2">
      {selected.id!=='approved-override'&&<button data-testid="assessment-run-real-ai" className={primary+' inline-flex gap-2 items-center'} disabled={!ready||!!busy} onClick={actual}>
       <PlayCircle size={17}/>{busy==='live'?'Assessing…':'Run actual AI assessment'}</button>}
      <button data-testid="assessment-try-free-example" className={secondary} disabled={!!busy} onClick={preview}>{busy==='demo'?'Checking…':selected.id==='approved-override'?'Test correction rules (free)':'Preview example (free)'}</button>
     </div>
     {selected.id!=='approved-override'&&<p data-testid="assessment-ai-availability" className="text-xs text-slate-600">
      {ready?`Real AI ready · ${live.daily_remaining} calls left today · ${live.total_remaining} total calls left`:
       'Real AI is disabled or the capped budget is exhausted. The free example remains available. Paid QA needs explicit staging configuration.'}</p>}
     <p className="text-xs text-amber-800">Live QA uses the configured model and synthetic cases. It is not yet the full real-post assessment pipeline.</p>
    </section>}
    {result&&<section data-testid="assessment-qa-results" aria-live="polite" className={panel+' space-y-4'}>
     <h2 className="font-semibold">4. What did the assessment get right or wrong?</h2>
     <p className="text-xs text-slate-600">{mode==='real'?'Real model response (may use paid credits)':'Prepared offline comparison — no AI model was called'}</p>
     <div className="grid grid-cols-2 gap-3">
      <div className="rounded-lg bg-emerald-50 p-3"><strong className="text-2xl text-emerald-800">{matches.length}</strong><p className="text-xs">Expected answers matched</p></div>
      <div className="rounded-lg bg-amber-50 p-3"><strong className="text-2xl text-amber-900">{problems.length}</strong><p className="text-xs">Wrong or missing answers</p></div>
     </div>
     {mode==='real'&&<div className="rounded-lg bg-slate-50 p-3 text-sm space-y-2">
      <p><strong>What AI said:</strong> {result.ai_summary}</p><p><strong>Suggested officer check:</strong> {result.recommended_check}</p>
      <p className="text-xs text-slate-500">Model: {result.model} · Evidence quote {result.quote_valid?'verified in source':'not verifiable'}</p></div>}
     {problems.length>0&&<div className="space-y-2"><h3 className="font-semibold text-sm">What needs improvement</h3>
      {problems.map(row=><div key={row.field} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
       <p className="font-semibold">{label(row.field)}</p>
       <p>Assessment said: <strong>{format(row.actual)}</strong></p><p>Expected: <strong>{format(row.expected)}</strong></p>
      </div>)}</div>}
     <details className="border border-slate-200 rounded-lg p-3"><summary className="cursor-pointer text-sm font-semibold">Show {matches.length} matching answers</summary>
      <div className="mt-2 space-y-1">{matches.map(row=><p key={row.field} className="text-sm"><strong>{label(row.field)}:</strong> {format(row.actual)}</p>)}</div></details>
     {result.override_preview&&<div data-testid="assessment-override-preview" className="rounded-lg bg-slate-50 p-3 text-sm space-y-1">
      <strong>Officer correction demonstration</strong><p>AI originally: {format(result.override_preview.ai_value)}</p>
      <p>Pending approval: {format(result.override_preview.unapproved_effective_value)}</p>
      <p>After approval: {format(result.override_preview.approved_effective_value)}</p>
      <p className="text-xs text-slate-500">In-memory preview only; no real correction saved.</p></div>}
     <p className="text-xs text-slate-600">Comparison uses illustrative expected answers, not validated AI accuracy or a legal finding.</p>
     <div className="border-t pt-3 space-y-2"><p className="text-sm font-semibold">How would you rate this result?</p>
      <button className={secondary+(feedback==='good'?' ring-2 ring-emerald-500':'')} onClick={()=>setFeedback('good')}>Looks acceptable</button>{' '}
      <button className={secondary+(feedback==='bad'?' ring-2 ring-amber-500':'')} onClick={()=>setFeedback('bad')}>Needs improvement</button>
      {feedback&&<p role="status" className="text-xs text-slate-600">Noted on this screen only. Feedback is not saved or used for training.</p>}
     </div>
    </section>}
    <details data-testid="assessment-developer-diagnostics" className={panel}>
      <summary className="cursor-pointer text-sm font-semibold">Developer diagnostics (optional)</summary>
      <p className="text-xs text-slate-600 mt-2">The previous JSON comparison tool is preserved separately for technical QA.</p>
      <Link className="inline-block mt-2 text-sm font-semibold underline text-[#851b29]" to="/administration/assessment-qa/diagnostics">Open advanced diagnostics</Link>
    </details>
   </div>
  </div>}
 </main>;
}
