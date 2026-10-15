import { useEffect, useMemo, useState } from 'react';
import { base44 } from '@/api/base44Client';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { PRIORITIES, Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

function SocialEvidenceInbox(){
 const [findings,setFindings]=useState([]),[campaigns,setCampaigns]=useState([]),[campaign,setCampaign]=useState(''),[view,setView]=useState('all'),[term,setTerm]=useState(''),[selected,setSelected]=useState(null),[unassessed,setUnassessed]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[backlog,setBacklog]=useState(null),[backlogBusy,setBacklogBusy]=useState(false),[backlogStatus,setBacklogStatus]=useState(''),[assessmentCounts,setAssessmentCounts]=useState(null),[processingStatus,setProcessingStatus]=useState('');
 useEffect(()=>{let active=true;setLoading(true);setError('');
 base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',data:{campaign_id:campaign}})
 .then(r=>{if(!active)return;setFindings(r.data.findings||[]);setCampaigns(r.data.campaigns||[]);setUnassessed(r.data.unassessed_count||0);setAssessmentCounts(r.data.assessment_counts||null);setProcessingStatus(r.data.processing_status||'')})
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
 const filtered=useMemo(()=>findings.filter(x=>{
  if(view==='location'&&!(x.location_signals||[]).length)return false;
  if(view==='candidate'&&!(x.candidate_signals||[]).length)return false;
  if(view==='violation'&&!(x.potential_issues||[]).length)return false;
  return !term||(JSON.stringify([x.text_content,x.campaign_name,x.author_name,x.location_signals,x.candidate_signals,x.potential_issues]).toLowerCase().includes(term.toLowerCase()))
 }),[findings,view,term]);
 const buttons=[['all','All Relevant'],['location','Location'],['candidate','Candidate'],['violation','Potential Violation']];
 return <section className="space-y-4" aria-label="AI intelligence findings">
  <div className="flex flex-wrap justify-between gap-3 items-center"><div><h2 className="text-xl font-semibold">AI-screened intelligence findings</h2><p className="text-sm text-slate-500">Campaign evidence assessed for contextual relevance · no manual promotion required</p></div>
   <select className="intel-input" aria-label="Filter campaign" value={campaign} onChange={e=>{setCampaign(e.target.value);setSelected(null)}}><option value="">All campaigns</option>{campaigns.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
  </div>
  <div className="intel-card p-3 space-y-2"><div className="flex flex-wrap items-center gap-2"><strong className="text-sm">AI backlog · controlled review</strong><button type="button" className="intel-ghost text-xs" disabled={backlogBusy||!campaign} onClick={previewBacklog}>Preview existing posts (free)</button></div>
  {backlog&&<div className="text-xs space-y-1"><p>{backlog.unassessed} pending links in this campaign · up to {backlog.batch_limit} AI requests this batch · 0 SocialCrawl credits.</p><p>AI provider: {backlog.ai_key_configured?'configured':'not configured'} · AI token costs vary by usage. No assessment is started by preview.</p><button className="intel-button text-xs" type="button" disabled={backlogBusy||!backlog.ai_key_configured||!backlog.batch_limit} onClick={startBacklog}>Confirm and assess up to {backlog.batch_limit} posts</button></div>}
  {backlogStatus&&<p className="text-xs" role="status">{backlogStatus}</p>}</div>
  {assessmentCounts&&<div className="intel-card p-3 space-y-2" aria-label="AI assessment diagnostics"><h3 className="text-sm font-semibold">Assessment diagnostics · stored results</h3><div className="grid grid-cols-2 sm:grid-cols-5 gap-2">{[['Pending','PENDING'],['Relevant','RELEVANT'],['Irrelevant','IRRELEVANT'],['Uncertain','UNCERTAIN'],['Other','OTHER']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{assessmentCounts[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">{processingStatus}. This panel never triggers AI calls; failures cannot yet be counted reliably.</p></div>}
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
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">{buttons.map(([key,label])=><button type="button" key={key} className={view===key?'intel-button':'intel-ghost'} aria-pressed={view===key} onClick={()=>{setView(key);setSelected(null)}}>{label} ({findings.filter(x=>key==='all'||key==='location'&&x.location_signals?.length||key==='candidate'&&x.candidate_signals?.length||key==='violation'&&x.potential_issues?.length).length})</button>)}</div>
  <div className="intel-card p-4 space-y-2"><p className="font-semibold">AI brief · {buttons.find(x=>x[0]===view)?.[1]}</p><p className="text-sm text-slate-600">{filtered.length} assessed relevant findings in this view. {view==='violation'?'These are preliminary potential issue signals mapped to active Administration categories, not confirmed violations.':'Only evidence with a recorded contextual relevance assessment appears here.'}</p><p className="text-xs text-amber-800">{unassessed} campaign evidence links are unassessed and excluded from relevant findings. No unsupported AI summary is generated.</p></div>
  <input className="intel-input w-full" value={term} onChange={e=>setTerm(e.target.value)} placeholder="Search findings, candidates, locations or issues" aria-label="Search relevant findings"/>
  {error&&<p role="alert" className="text-sm text-red-600">{error}</p>}
  {loading?<p className="text-sm text-slate-500">Loading assessed campaign evidence…</p>:<div className="grid lg:grid-cols-2 gap-4"><div className="space-y-2">{filtered.slice(0,80).map(item=><button key={item.campaign_id+'-'+item.id} type="button" onClick={()=>setSelected(item)} className="w-full text-left intel-card p-4 space-y-2"><p className="text-xs text-slate-500">{item.campaign_name} · {item.platform} · {item.relevance_label}</p><p className="line-clamp-3 text-sm">{item.text_content||'No text available'}</p><p className="text-xs text-slate-500">{item.potential_issues.length?'Potential issue signal · '+item.potential_issues.map(x=>x.category_name).join(', '):'View contextual assessment →'}</p></button>)}{!filtered.length&&<p className="text-sm text-slate-500">No AI-assessed relevant findings in this view. Unassessed posts remain in Social Listening.</p>}</div>
  <div className="intel-card p-4"><h3 className="font-semibold mb-3">Finding details</h3>{selected?<div className="space-y-3 text-sm"><p className="whitespace-pre-wrap">{selected.text_content}</p><p><strong>Why relevant:</strong> {selected.explanation||'No explanation stored'}</p><p><strong>AI assessment:</strong> {selected.relevance_label} · Confidence: {selected.relevance_confidence||'Not provided'}</p><p><strong>Location signals:</strong> {JSON.stringify(selected.location_signals)}</p><p><strong>Candidate signals:</strong> {JSON.stringify(selected.candidate_signals)}</p><p><strong>Potential issue categories:</strong> {selected.potential_issues.map(x=>x.category_name).join(', ')||'None flagged'}</p>{selected.canonical_url&&<a className="text-blue-700 underline" href={selected.canonical_url} target="_blank" rel="noopener noreferrer">Open original source</a>}<p className="text-xs text-slate-500">Assessment v{selected.assessment_version} · Model {selected.model_version||'unspecified'}</p></div>:<p className="text-sm text-slate-500">Select a relevant finding to see the source, AI assessment and category signals.</p>}</div></div>}
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