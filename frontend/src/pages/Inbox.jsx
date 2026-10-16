import { useEffect, useMemo, useState } from 'react';
import { base44 } from '@/api/base44Client';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { PRIORITIES, Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

function SocialEvidenceInbox(){
 const [readiness,setReadiness]=useState(null),[readinessBusy,setReadinessBusy]=useState(false),[reconBusy,setReconBusy]=useState(false),[reconNotice,setReconNotice]=useState(''),[reconciliation,setReconciliation]=useState(null),[jobCounts,setJobCounts]=useState(null),[findings,setFindings]=useState([]),[campaigns,setCampaigns]=useState([]),[campaign,setCampaign]=useState(''),[view,setView]=useState('all'),[term,setTerm]=useState(''),[selected,setSelected]=useState(null),[unassessed,setUnassessed]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[backlog,setBacklog]=useState(null),[backlogBusy,setBacklogBusy]=useState(false),[backlogStatus,setBacklogStatus]=useState(''),[assessmentCounts,setAssessmentCounts]=useState(null),[processingStatus,setProcessingStatus]=useState('');
 useEffect(()=>{let active=true;setLoading(true);setError('');
 base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',data:{campaign_id:campaign}})
 .then(r=>{if(!active)return;setFindings(r.data.findings||[]);setCampaigns(r.data.campaigns||[]);setUnassessed(r.data.unassessed_count||0);setAssessmentCounts(r.data.assessment_counts||null);setJobCounts(r.data.job_counts||null);setReconciliation(r.data.reconciliation||null);setProcessingStatus(r.data.processing_status||'')})
 .catch(e=>{if(active)setError(e.response?.data?.detail||e.message||'Inbox unavailable')})
 .finally(()=>{if(active)setLoading(false)});
 return()=>{active=false}
 },[campaign]);
 async function previewBacklog(){
  if(!campaign){setBacklogStatus('Select a campaign first.');return}
  setBacklogBusy(true);setBacklogStatus('');setBacklog(null);
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentBacklogPreview',id:campaign,data:{}});setBacklog(r.data)}
  catch(e){setBacklogStatus(e.response?.data?.detail||e.message)}
  finally{setBacklogBusy(false)}
 }
 async function startBacklog(){
  if(!backlog||!window.confirm('Use up to '+backlog.batch_limit+' billable AI requests to assess existing campaign evidence? No SocialCrawl credits will be used.'))return;
  setBacklogBusy(true);setBacklogStatus('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentBacklogStart',id:campaign,data:{confirm_ai_cost:true}});setBacklogStatus('Up to '+r.data.batch_limit+' AI assessments queued. Refresh this page shortly to view completed findings.');setBacklog(null)}
  catch(e){setBacklogStatus(e.response?.data?.detail||e.message)}
  finally{setBacklogBusy(false)}
 }
 const [auditRows,setAuditRows]=useState([]),[auditOpen,setAuditOpen]=useState(false),[auditBusy,setAuditBusy]=useState(false),[auditError,setAuditError]=useState(''),[correctionNotes,setCorrectionNotes]=useState({});
 async function loadAudit(){
  setAuditBusy(true);setAuditError('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentAudit',id:campaign||undefined,data:{}});setAuditRows(r.data.assessments||[]);setAuditOpen(true)}
  catch(e){setAuditError(e.response?.data?.detail||e.message||'Cannot load audit')}
  finally{setAuditBusy(false)}
 }
 async function correctAssessment(x,decision){
  const rationale=correctionNotes[x.campaign_id+'-'+x.result_id]||'';
  if(rationale.trim().length<10){setAuditError('Provide at least 10 characters explaining this correction.');return}
  if(!window.confirm('Save a human relevance correction while retaining the original AI assessment?'))return;
  setAuditBusy(true);setAuditError('');
  try{await base44.functions.invoke('socialListening',{action:'campaignAssessmentCorrection',id:x.campaign_id,data:{result_id:x.result_id,decision,rationale}});await loadAudit()}
  catch(e){setAuditError(e.response?.data?.detail||e.message||'Correction failed')}
  finally{setAuditBusy(false)}
 }
 const [chosenLocation,setChosenLocation]=useState(''),[chosenCandidate,setChosenCandidate]=useState('');
 const locationAliases={'sumbar':'Sumatera Barat','sumatera barat':'Sumatera Barat','sumut':'Sumatera Utara','sumsel':'Sumatera Selatan','dki jakarta':'DKI Jakarta','jakarta':'DKI Jakarta','jabar':'Jawa Barat','jateng':'Jawa Tengah','jatim':'Jawa Timur','bali':'Bali'};
 const normalizedLocation=name=>{const value=String(name||'').trim();return locationAliases[value.toLocaleLowerCase('id-ID')]||value};
 const signalNames=signals=>(signals||[]).map(s=>typeof s==='string'?s:(s?.name||s?.province||s?.regency_city||s?.value||'')).map(x=>String(x).trim()).filter(Boolean);
 const locationsFor=x=>signalNames(x.location_signals).map(normalizedLocation);
 const candidatesFor=x=>signalNames(x.candidate_signals).filter(name=>!/^@?[a-z0-9._-]+\.[a-z0-9._-]+$/i.test(name)&&!/^@/.test(name));
 const locations=useMemo(()=>[...new Set(findings.flatMap(locationsFor))].sort((a,b)=>a.localeCompare(b)),[findings]);
 const candidates=useMemo(()=>[...new Set(findings.flatMap(candidatesFor))].sort((a,b)=>a.localeCompare(b)),[findings]);
 const filtered=useMemo(()=>findings.filter(x=>{
  if(view==='location'&&chosenLocation&&!locationsFor(x).includes(chosenLocation))return false;
  if(view==='candidate'&&chosenCandidate&&!candidatesFor(x).includes(chosenCandidate))return false;
  if(view==='violation'&&!(x.potential_issues||[]).length)return false;
  return !term||(JSON.stringify([x.text_content,x.campaign_name,x.author_name,x.location_signals,x.candidate_signals,x.potential_issues]).toLowerCase().includes(term.toLowerCase()))
 }),[findings,view,term,chosenLocation,chosenCandidate]);
 const buttons=[['all','All Relevant'],['location','Location'],['candidate','Candidate'],['violation','Potential Violation']];
 return <section className="space-y-4" aria-label="AI intelligence findings">
  <div className="flex flex-wrap justify-between gap-3 items-center"><div><h2 className="text-xl font-semibold">AI-screened intelligence findings</h2><p className="text-sm text-slate-500">Campaign evidence assessed for contextual relevance · no manual promotion required</p></div>
   <select className="intel-input" aria-label="Filter campaign" value={campaign} onChange={e=>{setCampaign(e.target.value);setSelected(null)}}><option value="">All campaigns</option>{campaigns.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
  </div>
  <div className="grid grid-cols-2 md:grid-cols-[1fr_1fr_3fr] gap-2">
   <div className="intel-card p-3"><p className="text-xs text-slate-500">Posts shown</p><p className="text-2xl font-semibold tabular-nums">{filtered.length}</p></div>
   <div className="intel-card p-3"><p className="text-xs text-slate-500">Potential violations · signals only</p><p className="text-2xl font-semibold text-amber-700 tabular-nums">{filtered.filter(x=>(x.potential_issues||[]).length>0).length}</p></div>
   <div className="intel-card col-span-2 md:col-span-1 p-3"><p className="text-xs font-semibold">AI assessment summary</p><p className="mt-1 text-xs text-slate-600 line-clamp-2">{filtered.length===0?'No assessed findings match this selection.':filtered.filter(x=>(x.potential_issues||[]).length).length+' of '+filtered.length+' viewed findings contain AI-flagged potential issues. These are not confirmed violations.'}</p><p className="text-[10px] text-slate-500 mt-1">Summary of stored assessments, not a new AI request</p></div>
  </div>
  <div className="intel-card p-3 space-y-2" aria-label="Find and filter intelligence">
   <div className="flex flex-wrap gap-1.5">{buttons.map(([key,label])=><button type="button" key={key} className={view===key?'rounded-full bg-[#176e8e] text-white px-3 py-1.5 text-xs font-semibold':'rounded-full bg-slate-100 text-slate-600 px-3 py-1.5 text-xs font-semibold hover:bg-slate-200'} aria-pressed={view===key} onClick={()=>{setView(key);setSelected(null)}}>{label}</button>)}</div>
   <div className="flex flex-wrap gap-2"><input className="intel-input flex-1 min-w-[190px]" value={term} onChange={e=>setTerm(e.target.value)} placeholder="Search posts, candidates, locations or issues" aria-label="Search relevant findings"/>
    {view==='location'&&<select className="intel-input" aria-label="Select location" value={chosenLocation} onChange={e=>{setChosenLocation(e.target.value);setSelected(null)}}><option value="">All locations</option>{locations.map(name=><option key={name} value={name}>{name}</option>)}</select>}
    {view==='candidate'&&<select className="intel-input" aria-label="Select candidate" value={chosenCandidate} onChange={e=>{setChosenCandidate(e.target.value);setSelected(null)}}><option value="">All candidates</option>{candidates.map(name=><option key={name} value={name}>{name}</option>)}</select>}
   </div>
   {(view==='location'||view==='candidate')&&<p className="text-[11px] text-slate-500">AI-extracted entities and locations are unverified signals, not authoritative assignments.</p>}
  </div>
  {error&&<p role="alert" className="text-sm text-red-600">{error}</p>}
  {loading?<p className="text-sm text-slate-500">Loading assessed campaign evidence…</p>:<div className="grid grid-cols-1 xl:grid-cols-[minmax(0,4fr)_minmax(170px,1fr)] gap-3 items-start">
   <div className="space-y-2">{filtered.slice(0,80).map(item=><button key={item.campaign_id+'-'+item.id} type="button" onClick={()=>setSelected(item)} className="w-full text-left intel-card p-3 space-y-1.5 hover:border-sky-300">
    <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{item.campaign_name} · {item.platform} · {item.relevance_label}</span>{(item.potential_issues||[]).length>0&&<span className="text-amber-700 font-semibold">Potential issue · unverified</span>}</div>
    <p className="line-clamp-3 text-sm text-slate-700 whitespace-pre-wrap">{item.text_content||'No text available'}</p>
    <p className="text-xs text-[#146a8b]">View source and assessment →</p>
   </button>)}{!filtered.length&&<p className="intel-card p-5 text-sm text-slate-500">No AI-assessed relevant findings in this view. Unassessed posts remain in Social Listening.</p>}{filtered.length>80&&<p className="text-xs text-slate-500">Showing the first 80 matching posts.</p>}</div>
   <aside className="intel-card p-3 xl:sticky xl:top-4" aria-label="Post distribution"><h3 className="text-xs font-semibold">Distribution</h3><p className="text-[11px] text-slate-500 mt-1">Current filtered posts</p>
    <div className="flex justify-center py-3"><div className="w-24 h-24 rounded-full grid place-items-center" role="img" aria-label={filtered.filter(x=>(x.potential_issues||[]).length).length+' potential issue signals out of '+filtered.length+' posts'} style={{background:filtered.length?'conic-gradient(#c18b41 0 '+(filtered.filter(x=>(x.potential_issues||[]).length).length/filtered.length*100)+'%, #dce7ec 0)':'#dce7ec'}}><div className="w-[68px] h-[68px] rounded-full bg-white grid place-items-center"><span className="text-xl font-semibold">{filtered.length}</span></div></div></div>
    <p className="text-[11px] text-slate-600">Flagged: {filtered.filter(x=>(x.potential_issues||[]).length).length}</p><p className="text-[11px] text-slate-600">Other: {filtered.filter(x=>!(x.potential_issues||[]).length).length}</p><p className="mt-2 text-[10px] text-slate-500">Signals are not confirmed violations.</p>
   </aside>
  </div>}
  {selected&&<div className="fixed inset-0 z-50 flex justify-end"><button type="button" aria-label="Close finding preview" className="absolute inset-0 bg-slate-900/40" onClick={()=>setSelected(null)}/>
   <section role="dialog" aria-modal="true" aria-label="Finding details" className="relative bg-white w-full max-w-xl h-full shadow-2xl flex flex-col">
    <div className="p-4 border-b flex justify-between gap-3 items-center"><h3 className="font-semibold">Post preview · AI assessment</h3><button autoFocus type="button" className="intel-ghost text-xs" onClick={()=>setSelected(null)}>Close ×</button></div>
    <div className="p-4 overflow-y-auto space-y-3 text-sm"><p className="text-xs text-slate-500">{selected.campaign_name} · {selected.platform}</p><p className="whitespace-pre-wrap">{selected.text_content||'No text available'}</p><div className="border-t pt-3 space-y-2"><p><strong>Why relevant:</strong> {selected.explanation||'No explanation stored'}</p><p><strong>AI assessment:</strong> {selected.relevance_label} · Confidence: {selected.relevance_confidence||'Not provided'}</p><p><strong>Location signals:</strong> {signalNames(selected.location_signals).join(', ')||'None'}</p><p><strong>Candidate signals:</strong> {signalNames(selected.candidate_signals).join(', ')||'None'}</p><p><strong>Potential issue categories:</strong> {(selected.potential_issues||[]).map(x=>x.category_name).join(', ')||'None flagged'}</p>{selected.canonical_url&&<a className="text-blue-700 underline" href={selected.canonical_url} target="_blank" rel="noopener noreferrer">Open original source ↗</a>}<p className="text-xs text-slate-500">Assessment v{selected.assessment_version} · Model {selected.model_version||'unspecified'} · Human verification required</p></div></div>
   </section>
  </div>}
  <details className="intel-card p-3" aria-label="AI operations and diagnostics"><summary className="cursor-pointer text-sm font-semibold py-1">AI operations &amp; diagnostics <span className="text-xs font-normal text-slate-500">· Internal tools</span></summary><div className="mt-3 space-y-3">
  <div className="intel-card p-3 space-y-2"><div className="flex flex-wrap items-center gap-2"><strong className="text-sm">AI backlog · controlled review</strong><button type="button" className="intel-ghost text-xs" disabled={backlogBusy||!campaign} onClick={previewBacklog}>Preview existing posts (free)</button></div>
  {backlog&&<div className="text-xs space-y-1"><p>{backlog.unassessed} pending links in this campaign · up to {backlog.batch_limit} AI requests this batch · 0 SocialCrawl credits.</p><p>AI provider: {backlog.ai_key_configured?'configured':'not configured'} · AI token costs vary by usage. No assessment is started by preview.</p><button className="intel-button text-xs" type="button" disabled={backlogBusy||!backlog.ai_key_configured||!backlog.batch_limit} onClick={startBacklog}>Confirm and assess up to {backlog.batch_limit} posts</button></div>}
  {backlogStatus&&<p className="text-xs" role="status">{backlogStatus}</p>}</div>
  {campaign&&<div className="intel-card p-3 space-y-2"><div className="flex flex-wrap gap-2 items-center"><strong className="text-sm">Automatic AI worker readiness · free check</strong><button type="button" className="intel-ghost text-xs" disabled={readinessBusy} onClick={async()=>{setReadinessBusy(true);try{const r=await base44.functions.invoke('socialListening',{action:'campaignAIWorkerReadiness',id:campaign,data:{}});setReadiness(r.data)}catch(e){setReadiness({error:e.response?.data?.detail||e.message})}finally{setReadinessBusy(false)}}}>Check readiness (free)</button></div>{readiness&&<p className="text-xs text-slate-600" role="status">{readiness.error||('Auto screening: '+(readiness.automatic_screening_enabled?'ON':'OFF')+' · Worker: '+(readiness.worker_enabled?'ON':'OFF')+' · Provider: '+(readiness.ai_provider_configured?'Configured':'Unavailable')+' · Database reservation: '+(readiness.database_supports_reservations?'Supported':'Unsupported')+' · Daily reserved: '+readiness.daily_reserved+'/'+readiness.daily_request_limit+' · Lifetime reserved: '+readiness.lifetime_reserved+'/'+readiness.lifetime_request_limit+' · '+(readiness.ready_to_process?'Ready if enabled':'Not enabled or limits incomplete'))}</p>}</div>}
  {jobCounts&&<div className="intel-card p-3 space-y-2" aria-label="AI job progress"><h3 className="text-sm font-semibold">AI job progress · stored status</h3><div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Pending','PENDING'],['Processing','PROCESSING'],['Completed','COMPLETED'],['Failed','FAILED']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{jobCounts[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">Job status is read-only and does not initiate provider calls. Reload to refresh.</p></div>}
  {reconciliation&&reconciliation.unassessed_without_job>0&&campaign&&<div className="intel-card p-3 flex flex-wrap items-center gap-3"><span className="text-xs text-slate-600">{reconciliation.unassessed_without_job} unassessed evidence records lack a job.</span><button type="button" className="intel-ghost text-xs" disabled={reconBusy} onClick={async()=>{setReconBusy(true);setReconNotice('');try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentJobReconcile',id:campaign,data:{}});setReconNotice((r.data.created_pending_jobs||0)+' missing pending job(s) created. Refresh to verify. No AI calls.')}catch(e){setReconNotice(e.response?.data?.detail||e.message)}finally{setReconBusy(false)}}}>Create missing jobs (free)</button>{reconNotice&&<span role="status" className="text-xs">{reconNotice}</span>}</div>}
  {reconciliation&&<div className="intel-card p-3 space-y-2" aria-label="AI assessment job reconciliation"><h3 className="text-sm font-semibold">Job / assessment reconciliation · read-only</h3><div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Unassessed without job','unassessed_without_job'],['Assessed without job','assessed_without_job'],['Pending job already assessed','pending_job_with_assessment'],['Completed job unassessed','completed_job_without_assessment']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{reconciliation[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">Job and assessment counts use different records. These are reconciliation categories, not additional evidence. No data is changed or AI called.</p></div>}
  {assessmentCounts&&<div className="intel-card p-3 space-y-2" aria-label="AI assessment diagnostics"><h3 className="text-sm font-semibold">Assessment diagnostics · stored results</h3><div className="grid grid-cols-2 sm:grid-cols-5 gap-2">{[['Pending','PENDING'],['Relevant','RELEVANT'],['Irrelevant','IRRELEVANT'],['Uncertain','UNCERTAIN'],['Other','OTHER']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{assessmentCounts[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">{processingStatus}. This panel never triggers AI calls.</p></div>}
  <div className="intel-card p-3 space-y-3"><div className="flex flex-wrap gap-2 items-center"><strong className="text-sm">Assessment audit</strong><button type="button" className="intel-ghost text-xs" disabled={auditBusy} onClick={loadAudit}>{auditBusy?'Loading…':'Review AI decisions (free)'}</button></div>
   {auditError&&<p role="alert" className="text-sm text-red-600">{auditError}</p>}
   {auditOpen&&<div className="max-h-96 overflow-y-auto space-y-3">{auditRows.map(x=><div key={x.campaign_id+'-'+x.result_id} className="border rounded-lg p-3 space-y-2 text-sm">
    <p className="text-xs text-slate-500">{x.campaign_name} · {x.relevance_label} · {x.confidence||'No confidence'} · v{x.assessment_version} · {x.model_version}</p>
    <p className="whitespace-pre-wrap">{x.text_content}</p><p><strong>Reason:</strong> {x.explanation||'No AI explanation recorded'}</p>
    <p className="text-xs">Main: {(x.main_keywords||[]).join(', ')||'None'} · Secondary: {(x.secondary_keywords||[]).join(', ')||'None'}</p>
    {x.canonical_url&&<a className="text-blue-700 underline" href={x.canonical_url} target="_blank" rel="noopener noreferrer">Original source</a>}
    {x.can_correct&&<div className="space-y-2"><textarea className="intel-input w-full" rows={2} placeholder="Reason for human correction (minimum 10 characters)" value={correctionNotes[x.campaign_id+'-'+x.result_id]||''} onChange={e=>setCorrectionNotes(v=>({...v,[x.campaign_id+'-'+x.result_id]:e.target.value}))}/><div className="flex flex-wrap gap-2">{['RELEVANT','IRRELEVANT','UNCERTAIN'].map(d=><button type="button" className="intel-ghost text-xs" disabled={auditBusy} key={d} onClick={()=>correctAssessment(x,d)}>Correct to {d}</button>)}</div></div>}
   </div>)}{!auditRows.length&&<p className="text-sm text-slate-500">No stored assessments found.</p>}</div>}
  </div>
  <p className="text-xs text-slate-500">Uncertain assessments are retained in Assessment Audit; they are not silently rejected. AI batch status is not yet durable, so accepted requests should not be interpreted as completed until stored counts change.</p>

  </div></details>
 </section>
}
const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const triagePending=x=>{const t=x.triage_review||x.triage_review_status||{};const state=typeof t==='string'?t:t.state;const generated=typeof t==='object'?t.generated:!!state;return generated&&state&&state!=='REVIEW COMPLETE';};

function initialFilters(){const q=new URLSearchParams(window.location.search),f={};for(const key of ['entity','verification_status','review_status','priority','province','regency_city','platform','evidence_type','reviewer','source_type','supervision_signal','date','search']){const value=q.get(key);if(value)f[key]=value}if(q.get('view'))f.view=q.get('view');return f}

export default function Inbox(){
 const {t,label}=useLanguage();
 const {items,loading,error}=useIntel(),{items:entities}=useRegistry();
 const [f,setF]=useState(initialFilters),[sort,setSort]=useState('updated-desc');
 const pick=(key,value)=>setF(v=>({...v,[key]:value}));
 const unique=key=>[...new Set(items.flatMap(x=>['province','regency_city'].includes(key)?(x.geographic_assignments||[]).map(a=>a[key]).filter(Boolean):[x[key]]).filter(Boolean))].sort();
 const options={province:unique('province'),regency_city:unique('regency_city'),entity:entities.map(x=>x.name),platform:unique('platform'),evidence_type:['OBSERVED','INFERRED'],verification_status:['UNVERIFIED','HUMAN_VERIFIED'],supervision_signal:['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'],priority:PRIORITIES,reviewer:unique('assigned_reviewer'),review_status:unique('review_status'),source_type:unique('source_type')};
 const quickViews=[['',t('all_intelligence')],['pending-review',t('pending_review')],['validated',t('validated')],['unverified',t('unverified')],['jurisdiction-unresolved',t('jurisdiction_unresolved')],['triage-pending',t('ai_triage_waiting')]];
 const labelForKey={search:t('filter_search'),date:t('filter_date'),entity:t('filter_entity'),verification_status:t('filter_verification'),review_status:t('filter_review_status'),priority:t('filter_priority'),province:t('filter_province'),regency_city:t('filter_regency_city'),platform:t('filter_platform'),evidence_type:t('filter_evidence_type'),reviewer:t('filter_reviewer'),source_type:t('filter_source_type'),supervision_signal:t('filter_supervision_signal')};
 const filtered=useMemo(()=>items.filter(x=>{const text=(x.intelligence_id+' '+x.title+' '+x.original_content+' '+(x.related_entities||[]).join(' ')+' '+x.province+' '+x.regency_city+' '+(x.geographic_assignments||[]).map(a=>a.province+' '+a.regency_city).join(' ')).toLowerCase();const specialOk=!f.view||(f.view==='pending-review'&&pendingReview(x))||(f.view==='validated'&&validated(x))||(f.view==='unverified'&&(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED')||(f.view==='jurisdiction-unresolved'&&x.jurisdiction_confirmed!==true)||(f.view==='triage-pending'&&triagePending(x));return specialOk&&(!f.search||text.includes(f.search.toLowerCase()))&&(!f.date||x.created_date?.slice(0,10)===f.date)&&Object.keys(options).every(k=>!f[k]||(k==='entity'?x.related_entities?.includes(f[k]):k==='reviewer'?x.assigned_reviewer===f[k]:k==='supervision_signal'?x.supervision_screening?.supervision_signal===f[k]:k==='evidence_type'?(x.evidence_type||(['OBSERVED','INFERRED'].includes(x.evidence_state)?x.evidence_state:''))===f[k]:k==='verification_status'?(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))===f[k]:['province','regency_city'].includes(k)?(x.geographic_assignments||[]).some(a=>a[k]===f[k]):x[k]===f[k]))}),[items,f]);
 const sorted=useMemo(()=>[...filtered].sort((a,b)=>{if(sort==='updated-desc')return new Date(b.updated_date||b.created_date||0)-new Date(a.updated_date||a.created_date||0);if(sort==='created-desc')return new Date(b.created_date||0)-new Date(a.created_date||0);if(sort==='created-asc')return new Date(a.created_date||0)-new Date(b.created_date||0);if(sort==='priority'){const rank={Critical:4,High:3,Medium:2,Low:1};return(rank[b.priority]||0)-(rank[a.priority]||0)}if(sort==='id')return String(a.intelligence_id||'').localeCompare(String(b.intelligence_id||''));return 0}),[filtered,sort]);
 const counts=useMemo(()=>({'':items.length,'pending-review':items.filter(pendingReview).length,validated:items.filter(validated).length,unverified:items.filter(x=>(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED').length,'jurisdiction-unresolved':items.filter(x=>x.jurisdiction_confirmed!==true).length,'triage-pending':items.filter(triagePending).length}),[items]);
 const needsAction=useMemo(()=>items.filter(x=>x.jurisdiction_confirmed!==true||(x.geographic_mismatch?.status||x.geographic_mismatch_review?.status)==='pending'||triagePending(x)||pendingReview(x)).length,[items]);
 const activeFilters=Object.entries(f).filter(([k,v])=>k!=='view'&&v),clearOne=key=>setF(v=>({...v,[key]:''})),currentView=quickViews.find(([value])=>value===(f.view||''))?.[1]||t('all_intelligence');
 const recordScope=items.length===1?t('record_authorized_scope'):t('records_authorized_scope');
 return <div className="space-y-6"><div><p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('collection_triage')}</p><h1 className="intel-heading">{t('intelligence_inbox')}</h1><p className="text-sm text-[#77899b] mt-2">{t('inbox_workspace')} · {currentView} · {sorted.length} {t(sorted.length===1?'result':'results')} · {items.length} {recordScope}</p></div><Notice error={error}/>
 <SocialEvidenceInbox/>
 <details className="intel-card p-4"><summary className="cursor-pointer font-semibold">Legacy intelligence records and administrative review</summary><div className="mt-4 space-y-4"><div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3"><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_needs_action')}</p><p className="text-2xl font-semibold mt-1">{needsAction}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_pending_review')}</p><p className="text-2xl font-semibold mt-1">{counts['pending-review']}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_unresolved_jurisdiction')}</p><p className="text-2xl font-semibold mt-1">{counts['jurisdiction-unresolved']}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_triage_pending')}</p><p className="text-2xl font-semibold mt-1">{counts['triage-pending']}</p></div></div><p className="text-xs text-[#8192a3]">{t('inbox_summary_note')}</p>
 <div className="intel-card p-4"><div className="flex flex-wrap gap-2">{quickViews.map(([value,text])=><button key={value||'all'} type="button" className={(f.view||'')===value?'intel-button':'intel-ghost'} onClick={()=>pick('view',value)}>{text} <span className="opacity-70">({counts[value]||0})</span></button>)}</div></div>
 <div className="intel-card p-5 space-y-4"><div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3"><input className="intel-input sm:col-span-2" placeholder={t('search_placeholder')} aria-label={t('filter_search')} value={f.search||''} onChange={e=>pick('search',e.target.value)}/><input className="intel-input" type="date" aria-label={t('filter_date')} value={f.date||''} onChange={e=>pick('date',e.target.value)}/>
 {Object.entries(options).map(([key,values])=><select key={key} className="intel-input" aria-label={labelForKey[key]} value={f[key]||''} onChange={e=>pick(key,e.target.value)}><option value="">{t('all_prefix')} {labelForKey[key].toLowerCase()}</option>{values.map(v=><option key={v} value={v}>{label(v)}</option>)}</select>)}
 <select className="intel-input" aria-label={t('sort_intelligence_aria')} value={sort} onChange={e=>setSort(e.target.value)}><option value="updated-desc">{t('sort_recently_updated')}</option><option value="created-desc">{t('sort_newest_created')}</option><option value="created-asc">{t('sort_oldest_created')}</option><option value="priority">{t('sort_highest_priority')}</option><option value="id">{t('sort_intelligence_id')}</option></select></div>
 {(activeFilters.length>0||f.view)&&<div className="flex flex-wrap items-center gap-2">{f.view&&<span className="rounded-full bg-[#eaf4f7] px-3 py-1 text-xs font-semibold text-[#176e8e]">{t('view')}: {currentView}</span>}{activeFilters.map(([key,value])=><button key={key} type="button" onClick={()=>clearOne(key)} className="rounded-full bg-[#f5f7f9] px-3 py-1 text-xs text-[#536d80] hover:bg-[#edf2f5]">{labelForKey[key]||key}: {label(value)} ×</button>)}<button className="text-xs font-semibold text-[#126b8b]" onClick={()=>setF({})}>{t('clear_all_filters')}</button></div>}</div>
 {new URLSearchParams(window.location.search).get('jurisdiction')==='pending'&&<p role="status" className="text-sm">{t('submitted_jurisdiction')}</p>}
 {loading?<p className="text-sm text-[#77899b]">{t('loading_intelligence')}</p>:error?null:<IntelligenceTable items={sorted}/>}</div></details></div>;
}