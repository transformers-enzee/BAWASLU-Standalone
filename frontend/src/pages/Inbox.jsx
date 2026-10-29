import { useEffect, useMemo, useRef, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { PRIORITIES, Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

const platformLabel=value=>({youtube:'YouTube',instagram:'Instagram',tiktok:'TikTok',facebook:'Facebook',threads:'Threads',x:'X',twitter:'X',reddit:'Reddit',linkedin:'LinkedIn'}[String(value||'').toLowerCase()]||String(value||'Unknown'));
const safeOriginalUrl=value=>{try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:null}catch{return null}};

function SocialEvidenceInbox(){
 const deepLink=new URLSearchParams(window.location.search);
 const requestedCampaign=deepLink.get('campaign_id')||'';
 const requestedPost=deepLink.get('result_id')||'';
 const [violationDiagnostics,setViolationDiagnostics]=useState(null);const [readiness,setReadiness]=useState(null),[readinessBusy,setReadinessBusy]=useState(false),[reconBusy,setReconBusy]=useState(false),[reconNotice,setReconNotice]=useState(''),[reconciliation,setReconciliation]=useState(null),[jobCounts,setJobCounts]=useState(null),[findings,setFindings]=useState([]),[campaigns,setCampaigns]=useState([]),[campaign,setCampaign]=useState(requestedCampaign),[view,setView]=useState('all'),[term,setTerm]=useState(''),[selected,setSelected]=useState(null),[unassessed,setUnassessed]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[backlog,setBacklog]=useState(null),[backlogBusy,setBacklogBusy]=useState(false),[backlogStatus,setBacklogStatus]=useState(''),[assessmentCounts,setAssessmentCounts]=useState(null),[processingStatus,setProcessingStatus]=useState('');
 const [watchProgress,setWatchProgress]=useState(false),[watchSnapshot,setWatchSnapshot]=useState(null);
 const watchBaseline=useRef(null);
 const [issueCategories,setIssueCategories]=useState([]),[manualCategory,setManualCategory]=useState(''),[manualRationale,setManualRationale]=useState('');
 const [reviewDecision,setReviewDecision]=useState(''),[reviewRationale,setReviewRationale]=useState(''),[reviewBusy,setReviewBusy]=useState(false),[reviewError,setReviewError]=useState(''),[reviewNotice,setReviewNotice]=useState('');
 useEffect(()=>{let active=true;setLoading(true);setError('');
 base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',data:{campaign_id:campaign,result_id:requestedPost}})
 .then(r=>{if(!active)return;setFindings(r.data.findings||[]);
 if(requestedPost&&campaign===requestedCampaign){
  const found=(r.data.findings||[]).find(item=>String(item.id)===requestedPost&&String(item.campaign_id)===requestedCampaign);
  if(found)setSelected(found);
 }
 setIssueCategories(r.data.issue_categories||[]);setCampaigns(r.data.campaigns||[]);setUnassessed(r.data.unassessed_count||0);setAssessmentCounts(r.data.assessment_counts||null);setViolationDiagnostics(r.data.violation_diagnostics||null);setJobCounts(r.data.job_counts||null);setReconciliation(r.data.reconciliation||null);setProcessingStatus(r.data.processing_status||'')})
 .catch(e=>{if(active)setError(e.response?.data?.detail||e.message||'Inbox unavailable')})
 .finally(()=>{if(active)setLoading(false)});
 return()=>{active=false}
 },[campaign]);
 useEffect(()=>{
  if(!watchProgress||!campaign)return;
  let cancelled=false,attempts=0;
  const refresh=async()=>{
   try{
    const response=await base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',data:{campaign_id:campaign}});
    if(cancelled)return;
    const payload=response.data||{};
    setFindings(payload.findings||[]);setAssessmentCounts(payload.assessment_counts||null);setViolationDiagnostics(payload.violation_diagnostics||null);
    setJobCounts(payload.job_counts||null);setUnassessed(payload.unassessed_count||0);
    setReconciliation(payload.reconciliation||null);setProcessingStatus(payload.processing_status||'');
    setWatchSnapshot(payload.job_counts||{});
    const current=payload.job_counts||{},previous=watchBaseline.current;
    if(previous&&((current.COMPLETED||0)>(previous.COMPLETED||0)||(current.FAILED||0)>(previous.FAILED||0))){
     setBacklogStatus('Job status changed. Results refreshed automatically.');watchBaseline.current={...current};
    }
   }catch(e){if(!cancelled)setBacklogStatus('Progress refresh failed: '+(e.response?.data?.detail||e.message||'Unknown error'))}
   attempts++;
   if(!cancelled&&attempts>=60){setWatchProgress(false);setBacklogStatus('Progress checking paused after five minutes. No assessment completion is implied.')}
  };
  refresh();
  const interval=window.setInterval(refresh,5000);
  return()=>{cancelled=true;window.clearInterval(interval)};
 },[watchProgress,campaign]);
 async function submitFlagReview(){
  if(!selected||!reviewDecision||reviewRationale.trim().length<10||reviewBusy)return;
  if(!window.confirm('Save this human review decision to the evidence audit trail?'))return;
  setReviewBusy(true);setReviewError('');setReviewNotice('');
  try{
   const payload={result_id:selected.id,assessment_version:selected.assessment_version,decision:reviewDecision,rationale:reviewRationale.trim()};
   await base44.functions.invoke('socialListening',{action:'campaignFlagReview',id:selected.campaign_id,data:payload});
   const updated={...selected,flag_review_status:reviewDecision,is_flagged:reviewDecision!=='FLAG_DISMISSED'};
   setSelected(updated);setFindings(previous=>previous.map(item=>item.id===selected.id&&item.campaign_id===selected.campaign_id?updated:item));
   setReviewDecision('');setReviewRationale('');setReviewNotice('Human review decision saved. Current status updated; original assessment preserved.');
  }catch(e){setReviewError(e.response?.data?.detail||e.message||'Unable to save review')}
  finally{setReviewBusy(false)}
 }
 async function submitManualFlag(){
  if(!selected||!manualCategory||manualRationale.trim().length<10||reviewBusy)return;
  if(!window.confirm('Create a human-origin preliminary flag requiring further investigation?'))return;
  setReviewBusy(true);setReviewError('');setReviewNotice('');
  try{
   await base44.functions.invoke('socialListening',{action:'campaignManualFlag',id:selected.campaign_id,
     data:{result_id:selected.id,assessment_version:selected.assessment_version,category_id:manualCategory,rationale:manualRationale.trim()}});
   const updated={...selected,flag_review_status:'FURTHER_INVESTIGATION',is_flagged:true};
   setSelected(updated);
   setFindings(previous=>previous.map(item=>item.id===selected.id&&item.campaign_id===selected.campaign_id?updated:item));
   setManualCategory('');setManualRationale('');
   setReviewNotice('Human-origin preliminary flag saved for further investigation; AI evidence unchanged.');
  }catch(e){setReviewError(e.response?.data?.detail||e.message||'Unable to save manual flag')}
  finally{setReviewBusy(false)}
 }
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
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentBacklogStart',id:campaign,data:{confirm_ai_cost:true}});setBacklogStatus('Request acknowledged. Tracking stored job status; processing is not guaranteed.');watchBaseline.current={...(jobCounts||{})};setWatchSnapshot(jobCounts||{});setWatchProgress(true);setBacklog(null)}
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
 const [sortDate,setSortDate]=useState('newest'),[dateFrom,setDateFrom]=useState(''),[dateTo,setDateTo]=useState('');
 const [jurisdiction,setJurisdiction]=useState('national'),[chosenLocation,setChosenLocation]=useState(''),[chosenRegency,setChosenRegency]=useState(''),[chosenCandidate,setChosenCandidate]=useState(''),[reviewStatusFilter,setReviewStatusFilter]=useState('');
 const locationAliases={'sumbar':'Sumatera Barat','sumatera barat':'Sumatera Barat','sumut':'Sumatera Utara','sumsel':'Sumatera Selatan','dki jakarta':'DKI Jakarta','jakarta':'DKI Jakarta','jabar':'Jawa Barat','jateng':'Jawa Tengah','jatim':'Jawa Timur','bali':'Bali'};
 const normalizedLocation=name=>{const value=String(name||'').trim();return locationAliases[value.toLocaleLowerCase('id-ID')]||value};
 const signalNames=signals=>(signals||[]).map(s=>typeof s==='string'?s:(s?.name||s?.province||s?.regency_city||s?.value||'')).map(x=>String(x).trim()).filter(Boolean);
 const locationsFor=x=>signalNames(x.location_signals).map(normalizedLocation);
 const structuredPlaces=x=>(x.location_signals||[]).filter(s=>s&&typeof s==='object'&&s.province&&s.regency_city).map(s=>({province:normalizedLocation(s.province),regency:String(s.regency_city).trim()}));
 const canonicalCandidate=name=>{const raw=String(name||'').trim(),key=raw.toLocaleLowerCase('id-ID');return {'prabowo':'Prabowo Subianto','prabowo subianto':'Prabowo Subianto','gibran':'Gibran Rakabuming Raka','gibran rakabuming':'Gibran Rakabuming Raka','gibran rakabuming raka':'Gibran Rakabuming Raka','cindymonica.id':'Cindy Monica','cindy monica':'Cindy Monica'}[key]||raw};
 const candidatesFor=x=>[...new Set(signalNames(x.candidate_signals).map(canonicalCandidate).filter(name=>name&&!name.startsWith('@')&&(!/^[a-z0-9_-]+[.][a-z0-9._-]+$/i.test(name)||name==='Cindy Monica')))];
 const unlocatedCount=useMemo(()=>findings.filter(x=>locationsFor(x).length===0).length,[findings]);
 const locations=useMemo(()=>[...new Set(findings.flatMap(locationsFor))].sort((a,b)=>a.localeCompare(b)),[findings]);
 const provinceNames=new Set(['Aceh','Sumatera Utara','Sumatera Barat','Riau','Kepulauan Riau','Jambi','Bengkulu','Sumatera Selatan','Kepulauan Bangka Belitung','Lampung','Banten','DKI Jakarta','Jawa Barat','Jawa Tengah','DI Yogyakarta','Jawa Timur','Bali','Nusa Tenggara Barat','Nusa Tenggara Timur','Kalimantan Barat','Kalimantan Tengah','Kalimantan Selatan','Kalimantan Timur','Kalimantan Utara','Sulawesi Utara','Gorontalo','Sulawesi Tengah','Sulawesi Barat','Sulawesi Selatan','Sulawesi Tenggara','Maluku','Maluku Utara','Papua','Papua Barat','Papua Selatan','Papua Tengah','Papua Pegunungan','Papua Barat Daya']);
 const groupedLocations=useMemo(()=>({country:locations.filter(x=>x.toLowerCase()==='indonesia'),provinces:locations.filter(x=>provinceNames.has(x)),other:locations.filter(x=>x.toLowerCase()!=='indonesia'&&!provinceNames.has(x))}),[locations]);
 const provinceFor=x=>locationsFor(x).filter(name=>provinceNames.has(name)).concat(structuredPlaces(x).map(s=>s.province)).filter((name,index,array)=>array.indexOf(name)===index);
 const regencies=useMemo(()=>chosenLocation?[...new Set(findings.flatMap(x=>structuredPlaces(x).filter(s=>s.province===chosenLocation).map(s=>s.regency)))].sort((a,b)=>a.localeCompare(b)):[],[findings,chosenLocation]);
 const uncategorizedCandidateCount=useMemo(()=>findings.filter(x=>candidatesFor(x).length===0).length,[findings]);
 const candidates=useMemo(()=>[...new Set(findings.flatMap(candidatesFor))].sort((a,b)=>a.localeCompare(b)),[findings]);
  const filtered=useMemo(()=>findings.filter(x=>{
  if(jurisdiction==='location'&&chosenLocation==='__unresolved__'&&provinceFor(x).length>0)return false;
  if(jurisdiction==='location'&&chosenLocation&&chosenLocation!=='__unresolved__'&&!provinceFor(x).includes(chosenLocation))return false;
  if(jurisdiction==='unresolved'&&locationsFor(x).length>0)return false;
  if(jurisdiction==='province'&&(!provinceFor(x).length||(chosenLocation&&!provinceFor(x).includes(chosenLocation))))return false;
  if(jurisdiction==='province'&&chosenRegency&&!structuredPlaces(x).some(s=>s.province===chosenLocation&&s.regency===chosenRegency))return false;
  if(jurisdiction==='other'&&chosenLocation&&!locationsFor(x).includes(chosenLocation))return false;
  if(chosenCandidate==='__no_candidate__'&&candidatesFor(x).length>0)return false;
  if(chosenCandidate&&chosenCandidate!=='__no_candidate__'&&!candidatesFor(x).includes(chosenCandidate))return false;
  if(view==='violation'&&!(x.is_flagged??((x.potential_issues||[]).length>0)))return false;
  if(reviewStatusFilter==='AWAITING_REVIEW'&&(x.flag_review_status||((x.is_flagged??((x.potential_issues||[]).length>0))?'AWAITING_REVIEW':'NONE'))!=='AWAITING_REVIEW')return false;
  if(reviewStatusFilter&&reviewStatusFilter!=='AWAITING_REVIEW'&&x.flag_review_status!==reviewStatusFilter)return false;
  const date=String(x.published_at||x.post_time||x.created_at||'').slice(0,10);
  if((dateFrom||dateTo)&&(!date||(dateFrom&&date<dateFrom)||(dateTo&&date>dateTo)))return false;
  return !term||(JSON.stringify([x.text_content,x.campaign_name,x.author_name,x.location_signals,x.candidate_signals,x.potential_issues]).toLowerCase().includes(term.toLowerCase()))
 }),[findings,view,term,jurisdiction,chosenLocation,chosenRegency,chosenCandidate,reviewStatusFilter,dateFrom,dateTo]);
 const ordered=useMemo(()=>[...filtered].sort((a,b)=>{const da=Date.parse(a.published_at||a.post_time||a.created_at||0)||0,db=Date.parse(b.published_at||b.post_time||b.created_at||0)||0;return sortDate==='newest'?db-da:da-db}),[filtered,sortDate]);
 const summary=useMemo(()=>{const counts={POSITIVE:0,NEGATIVE:0,NEUTRAL:0,UNCLASSIFIED:0};let engagement=0,views=0,engagementAvailable=0,viewsAvailable=0;for(const item of filtered){if(typeof item.engagement_total==='number'){engagement+=item.engagement_total;engagementAvailable++}if(typeof item.views==='number'){views+=item.views;viewsAvailable++}const raw=String(item.sentiment||'').toUpperCase();counts[['POSITIVE','NEGATIVE','NEUTRAL'].includes(raw)?raw:'UNCLASSIFIED']++}return {engagement,views,engagementAvailable,viewsAvailable,counts}},[filtered]);
 const platformCounts=useMemo(()=>{const grouped=new Map();for(const item of filtered){const raw=String(item.platform||'Unknown').trim();const name=platformLabel(raw);grouped.set(name,(grouped.get(name)||0)+1)}return [...grouped.entries()].map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));},[filtered]);
 const platformColors=['#147b9c','#d19550','#658e7e','#887cb2','#9b7184','#8296a5'];
 const buttons=[['all','All Relevant'],['violation','Potential Violation']];
 const [showAdvancedFilters,setShowAdvancedFilters]=useState(false);
 const issueGroups=signals=>Object.entries((signals||[]).reduce((groups,signal)=>{const category=String(signal.category_name||'Uncategorized potential issue');(groups[category] ||= []).push(signal);return groups;},{}));
 const activeFilters=[jurisdiction!=='national',Boolean(chosenLocation),Boolean(chosenRegency),Boolean(chosenCandidate),Boolean(reviewStatusFilter)].filter(Boolean).length;
 const reviewState=item=>item.flag_review_status==='FLAG_DISMISSED'?{label:'Dismissed · reviewed',cls:'text-slate-600'}:item.flag_review_status==='FLAG_CONFIRMED'?{label:'Flag confirmed · preliminary',cls:'text-amber-800'}:item.flag_review_status==='FURTHER_INVESTIGATION'?{label:'Further investigation',cls:'text-orange-700'}:(item.is_flagged??((item.potential_issues||[]).length>0))?{label:'Awaiting human review',cls:'text-amber-700'}:null;
 return <section className="space-y-4" aria-label="AI intelligence findings">
  <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-[minmax(180px,2fr)_minmax(105px,.75fr)_minmax(145px,1fr)_minmax(155px,1fr)_minmax(155px,1fr)] gap-2 items-end" aria-label="Campaign dates and totals">
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">Campaign<select className="intel-input mt-1 w-full h-10 min-w-0" aria-label="Filter campaign" value={campaign} onChange={e=>{setCampaign(e.target.value);setSelected(null)}}><option value="">All campaigns</option>{campaigns.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
   <div className="text-xs min-w-0 flex flex-col justify-end h-[70px]"><span>Posts shown</span><div className="intel-card mt-1 px-3 h-10 min-w-0 flex items-center"><strong className="text-lg font-semibold tabular-nums">{filtered.length}</strong></div></div>
   <div className="text-xs min-w-0 flex flex-col justify-end h-[70px]"><span title="Preliminary signals only, not confirmed violations">Potential violations</span><div className="intel-card mt-1 px-3 h-10 min-w-0 flex items-center"><strong className="text-lg font-semibold text-amber-700 tabular-nums">{filtered.filter(x=>x.is_flagged??((x.potential_issues||[]).length>0)).length}</strong><span className="ml-2 text-[10px] text-slate-500 whitespace-nowrap">Signals</span></div></div>
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">From date<input type="date" className="intel-input mt-1 w-full h-10 min-w-0" value={dateFrom} onChange={e=>setDateFrom(e.target.value)}/></label>
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">To date<input type="date" className="intel-input mt-1 w-full h-10 min-w-0" min={dateFrom||undefined} value={dateTo} onChange={e=>setDateTo(e.target.value)}/></label>
  </div>
  <div className="intel-card px-3 py-2" aria-label="Filter intelligence">
   <div className="flex flex-wrap xl:flex-nowrap items-end gap-2">
    <label className="text-xs flex-1 min-w-[125px]">Province<select className="intel-input mt-1 w-full" value={chosenLocation} onChange={e=>{setChosenLocation(e.target.value);setJurisdiction('location');setSelected(null)}}><option value="">All provinces</option>{groupedLocations.provinces.map(name=><option key={name} value={name}>{name}</option>)}</select></label>
    <label className="text-xs flex-1 min-w-[125px]">Candidate<select className="intel-input mt-1 w-full" value={chosenCandidate} onChange={e=>{setChosenCandidate(e.target.value);setSelected(null)}}><option value="">All candidates</option>{candidates.map(name=><option key={name} value={name}>{name}</option>)}</select></label>
    <label className="text-xs flex-1 min-w-[125px]">Sort by date<select className="intel-input mt-1 w-full" value={sortDate} onChange={e=>setSortDate(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
    <label className="flex items-center gap-2 text-xs font-medium whitespace-nowrap min-h-10"><input type="checkbox" checked={view==='violation'} onChange={e=>{setView(e.target.checked?'violation':'all');setSelected(null)}}/>Potential violation only</label>
   </div>
  </div>
  {error&&<p role="alert" className="text-sm text-red-600">{error}</p>}
  {loading?<p className="text-sm text-slate-500">Loading assessed campaign evidence…</p>:<div className="space-y-2">
   <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_260px] gap-3 items-stretch">
   <section aria-label="Scrollable intelligence posts" className="min-w-0 flex flex-col gap-2 xl:relative xl:min-h-[680px]">
    <div className="flex items-center justify-between text-xs text-slate-500 px-1"><span>Posts · {filtered.length} results</span></div>
    <div className="max-h-[680px] xl:max-h-none xl:absolute xl:inset-x-0 xl:top-6 xl:bottom-0 overflow-y-auto overscroll-contain pr-1 space-y-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden" tabIndex={0} aria-label="Post list, scroll to see more">
     {ordered.map(item=><button key={item.campaign_id+'-'+item.id} type="button" onClick={()=>{setSelected(item);setReviewDecision('');setReviewRationale('');setReviewError('');setReviewNotice('')}} className="w-full min-h-[84px] text-left intel-card p-3 space-y-1 hover:border-sky-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-500">
      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{item.campaign_name} · {platformLabel(item.platform)}</span>{reviewState(item)&&<span className={'text-xs font-semibold '+reviewState(item).cls}>{reviewState(item).label}</span>}</div>
      <p className="line-clamp-2 text-sm text-slate-700 whitespace-pre-wrap">{item.text_content||'No text available'}</p>
      <p className="text-xs text-[#146a8b]">View source and assessment →</p>
     </button>)}
     {!filtered.length&&<p className="intel-card p-5 text-sm text-slate-500">No campaign-assessed findings match this view yet. New Social Listening evidence will appear here after collection, assessment and relevance checks. The separate historical Intelligence and Smart Radar pilot records are not counted as campaign findings.</p>}
    </div>
   </section>
   <div className="grid grid-rows-2 gap-3 xl:sticky xl:top-4 min-w-0">
   <aside className="intel-card p-4 space-y-4 h-full min-h-0" aria-label="Inbox statistics">
    <div><h4 className="font-semibold text-sm">Statistics</h4><p className="text-xs text-slate-500 mt-1">Filtered assessed posts</p></div>
    <div className="grid grid-cols-2 gap-2">
      <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Views</p><strong className="text-lg tabular-nums">{summary.viewsAvailable?summary.views.toLocaleString():'—'}</strong><p className="text-[10px] text-slate-500">{summary.viewsAvailable} / {filtered.length} reported</p></div>
      <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Engagement</p><strong className="text-lg tabular-nums">{summary.engagementAvailable?summary.engagement.toLocaleString():'—'}</strong><p className="text-[10px] text-slate-500">{summary.engagementAvailable} / {filtered.length} reported</p></div>
    </div>
    <div className="space-y-2"><h5 className="text-xs font-semibold">Sentiment</h5>{[['POSITIVE','Positive','#0d9488'],['NEUTRAL','Neutral','#8195a5'],['NEGATIVE','Negative','#d97706'],['UNCLASSIFIED','Unclassified','#cbd5e1']].map(([key,label,color])=><div key={key} className="space-y-1"><div className="flex justify-between text-xs"><span>{label}</span><strong className="tabular-nums">{summary.counts[key]}</strong></div><div className="h-1.5 bg-slate-100 rounded-full overflow-hidden"><div className="h-full rounded-full" style={{width:filtered.length?(summary.counts[key]/filtered.length*100)+'%':'0%',backgroundColor:color}}/></div></div>)}</div>
    <p className="text-[11px] text-slate-500">Metrics are summed only where providers reported them. Missing values are not treated as zero. Sentiment is based on stored assessments.</p>
   </aside>
   <section className="intel-card p-3 h-full min-h-0" aria-label="Channel distribution"><h4 className="text-sm font-semibold text-[#365269]">Channel distribution</h4><div className="mt-3">
    
    <p className="text-[11px] text-slate-500 mt-1">Among current filtered posts</p>
    <div className="flex justify-center py-3"><div className="w-28 h-28 rounded-full grid place-items-center" role="img" aria-label={platformCounts.map(x=>x.name+': '+x.count).join(', ')||'No platform data'} style={{background:filtered.length?`conic-gradient(${platformCounts.map((x,i)=>{const start=platformCounts.slice(0,i).reduce((n,v)=>n+v.count,0)/filtered.length*100;const end=(platformCounts.slice(0,i).reduce((n,v)=>n+v.count,0)+x.count)/filtered.length*100;return platformColors[i%platformColors.length]+' '+start+'% '+end+'%'}).join(', ')})`:'#dce7ec'}}><div className="w-20 h-20 rounded-full bg-white flex flex-col items-center justify-center"><strong className="text-2xl text-[#365269]">{filtered.length}</strong><span className="text-[10px] text-slate-500">posts</span></div></div></div>
    <div className="space-y-3 flex-1">{platformCounts.map((item,i)=><div key={item.name} className="space-y-1"><div className="flex justify-between gap-1 text-xs"><span className="truncate text-[#536d80]">{item.name}</span><span className="font-semibold tabular-nums">{item.count}</span></div><div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden"><div className="h-full rounded-full" style={{width:filtered.length?item.count/filtered.length*100+'%':'0%',backgroundColor:platformColors[i%platformColors.length]}}/></div></div>)}{!platformCounts.length&&<p className="text-xs text-slate-500">No platforms in this view.</p>}</div>
    <p className="border-t pt-3 mt-4 text-[11px] text-slate-500">Distribution updates when you change filters. It counts posts, not confirmed violations.</p></div>
   </section>
   </div>
   </div>

  </div>}
  {selected&&<div className="fixed inset-0 z-50 flex justify-end"><button type="button" aria-label="Close finding preview" className="absolute inset-0 bg-slate-900/40" onClick={()=>setSelected(null)}/>
   <section role="dialog" aria-modal="true" aria-label="Finding details" className="relative bg-white w-full max-w-xl h-full shadow-2xl flex flex-col">
    <div className="p-4 border-b flex justify-between gap-3 items-center"><h3 className="font-semibold">Post preview · AI assessment</h3><button autoFocus type="button" className="intel-ghost text-xs" onClick={()=>setSelected(null)}>Close ×</button></div>
    <div className="p-4 overflow-y-auto space-y-3 text-sm">
     <section className="rounded-xl border border-[#dce6e8] bg-[#f5f9f9] p-4 space-y-2">
      <h4 className="font-bold text-sm text-[#184e48]">Original source provenance</h4>
      <p className="text-xs text-slate-600">Source post ID: <code className="break-all">{selected.id||'Not supplied'}</code></p>
      <p className="text-xs text-slate-600">Platform: {platformLabel(selected.platform)} · Publisher: {selected.observed_handle||selected.author_name||'Not recorded'}</p>
      <p className="text-xs text-slate-600">Published: {selected.published_at||'Publication time not recorded'}</p>
      {safeOriginalUrl(selected.canonical_url)?<a href={safeOriginalUrl(selected.canonical_url)} target="_blank" rel="noopener noreferrer" className="inline-block text-xs font-semibold text-[#147b67] hover:underline">Open original source ↗</a>:<p className="text-xs text-amber-700">Source URL not available; do not treat this record as independently verifiable.</p>}
     </section>
     <p className="text-xs text-slate-500">{selected.campaign_name} · {platformLabel(selected.platform)}</p><p className="whitespace-pre-wrap">{selected.text_content||'No text available'}</p><div className="border-t pt-3 space-y-2"><p><strong>Why relevant:</strong> {selected.explanation||'No explanation stored'}</p><p><strong>AI assessment:</strong> {selected.relevance_label} · Confidence: {selected.relevance_confidence||'Not provided'}</p><p><strong>Location signals:</strong> {signalNames(selected.location_signals).join(', ')||'None'}</p><p><strong>Topic suggestions (text-only):</strong> {(selected.processing_hints?.topic_suggestions||[]).join(', ')||'None'}</p><p><strong>Province mentions (not verified incident location):</strong> {(selected.processing_hints?.province_mentions||[]).join(', ')||'None'}</p><p><strong>Candidate signals:</strong> {signalNames(selected.candidate_signals).join(', ')||'None'}</p><p><strong>Potential issue categories:</strong> {[...new Set((selected.potential_issues||[]).map(x=>x.category_name).filter(Boolean))].join(', ')||'None flagged'}</p>{(selected.potential_issues||[]).length>0&&<div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-2" aria-label="Potential issue evidence"><h4 className="text-sm font-semibold">Why this was flagged · preliminary evidence</h4>{issueGroups(selected.potential_issues).map(([category,signals])=><div key={category} className="text-xs space-y-2"><p className="font-semibold">{category} · {signals.length} {signals.length===1?'signal':'signals'} · Unverified</p>{signals.map((signal,index)=><div key={index} className="pl-2 border-l-2 border-amber-400 space-y-1"><p className="font-medium">{signal.signal_type==='REPORTED_INCIDENT'?'Reported incident · '+(signal.time_context||'UNKNOWN').toLowerCase():'Potential violation'}</p>{signal.evidence_quote&&<blockquote className="whitespace-pre-wrap">Source excerpt: “{signal.evidence_quote}”</blockquote>}<p>{signal.explanation||'Requires human review against the original source.'}</p></div>)}</div>)}<p className="text-xs text-amber-800">Source-supported text is not proof of a legal violation. Verify independently before acting.</p></div>}{(selected.potential_issues||[]).some(x=>x.signal_provenance==='LEGACY_MISSING_TYPE')&&<p className="text-xs text-amber-700" role="note">Legacy AI signal (original type missing) · Source quotation validated · Human verification required</p>}<p className="text-xs text-slate-500">Assessment v{selected.assessment_version} · Model {selected.model_version||'unspecified'} · Human verification required</p></div>
    {<div className="border-t pt-3 space-y-3">
     <h4 className="font-semibold">Human flag review</h4>
     <p className="text-xs text-slate-500">Flag decisions do not establish legal violations and do not change the original AI assessment.</p>
     <p className="text-xs">Current status: <strong>{selected.flag_review_status||((selected.is_flagged||(selected.potential_issues||[]).length>0)?'Awaiting review':'Not flagged for violation')}</strong></p>
     {(selected.flag_review_history||[]).length>0&&<details className="text-xs"><summary className="cursor-pointer font-semibold">Review history ({selected.flag_review_history.length} most recent)</summary><ol className="mt-2 space-y-2">{selected.flag_review_history.map((entry,index)=><li key={index} className="border-l-2 border-slate-200 pl-2"><strong>{entry.decision.replaceAll('_',' ')}</strong> · Assessment v{entry.assessment_version} · {entry.reviewed_at?new Date(entry.reviewed_at).toLocaleString():'Date unavailable'}<p className="text-slate-500">{entry.rationale}</p></li>)}</ol></details>}
     {selected.can_review_flag&&!(selected.potential_issues||[]).length&&!selected.is_flagged&&<div className="border border-amber-200 rounded-lg p-3 space-y-2"><p className="text-xs font-semibold">Flag this relevant post manually</p><p className="text-xs text-slate-500">Preliminary human concern only — not a legal finding.</p><label htmlFor="manual-issue-category" className="text-xs">Issue category</label><select id="manual-issue-category" className="intel-input w-full" value={manualCategory} onChange={e=>setManualCategory(e.target.value)}><option value="">Select active category</option>{issueCategories.map(category=><option key={category.id} value={category.id}>{category.name}</option>)}</select><label htmlFor="manual-flag-rationale" className="text-xs">Reason (at least 10 characters)</label><textarea id="manual-flag-rationale" className="intel-input w-full" value={manualRationale} onChange={e=>setManualRationale(e.target.value)} maxLength={1500}/><button type="button" className="intel-button" disabled={reviewBusy||!manualCategory||manualRationale.trim().length<10} onClick={submitManualFlag}>Flag for investigation</button></div>}
     {selected.can_review_flag&&((selected.potential_issues||[]).length>0||selected.is_flagged)&&<><label className="block text-xs font-semibold" htmlFor="flag-review-decision">Decision</label>
      <select id="flag-review-decision" className="intel-input w-full" value={reviewDecision} onChange={e=>setReviewDecision(e.target.value)}><option value="">Select a decision</option><option value="FLAG_CONFIRMED">Confirm preliminary flag</option><option value="FLAG_DISMISSED">Dismiss preliminary flag</option><option value="FURTHER_INVESTIGATION">Request further investigation</option></select>
      <label className="block text-xs font-semibold" htmlFor="flag-review-rationale">Reason for decision (minimum 10 characters)</label>
      <textarea id="flag-review-rationale" className="intel-input w-full" rows={3} maxLength={1500} value={reviewRationale} onChange={e=>setReviewRationale(e.target.value)} placeholder="Explain the evidence supporting this decision"/>
      <button type="button" className="intel-button" disabled={reviewBusy||!reviewDecision||reviewRationale.trim().length<10} onClick={submitFlagReview}>{reviewBusy?'Saving…':'Save human review'}</button>
     </>}{!selected.can_review_flag&&<p className="text-xs text-slate-500">Human validation permission is required for review actions.</p>}
     {reviewError&&<p role="alert" className="text-xs text-red-700">{reviewError}</p>}
     {reviewNotice&&<p role="status" className="text-xs text-green-700">{reviewNotice}</p>}
    </div>}
   </div>
   </section>
  </div>}
  <details className="intel-card p-3" aria-label="AI operations and diagnostics"><summary className="cursor-pointer text-sm font-semibold py-1">AI operations &amp; diagnostics <span className="text-xs font-normal text-slate-500">· Internal tools</span></summary><div className="mt-3 space-y-3">
  <div className="intel-card p-3 space-y-2"><div className="flex flex-wrap items-center gap-2"><strong className="text-sm">AI backlog · controlled review</strong><button type="button" className="intel-ghost text-xs" disabled={backlogBusy||!campaign} onClick={previewBacklog}>Preview existing posts (free)</button></div>
  {backlog&&<div className="text-xs space-y-1"><p>{backlog.unassessed} pending links in this campaign · up to {backlog.batch_limit} AI requests this batch · 0 SocialCrawl credits.</p><p>AI provider: {backlog.ai_key_configured?'configured':'not configured'} · AI token costs vary by usage. No assessment is started by preview.</p><button className="intel-button text-xs" type="button" disabled={backlogBusy||!backlog.ai_key_configured||!backlog.batch_limit} onClick={startBacklog}>Confirm and assess up to {backlog.batch_limit} posts</button></div>}
  {backlogStatus&&<p className="text-xs" role="status">{backlogStatus}</p>}
  {(watchProgress||watchSnapshot)&&<div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2" role="status" aria-live="polite">
   <div className="flex justify-between gap-2 text-xs"><strong>Manual AI status</strong><span>{watchProgress?'Updating every 5 seconds':'Updates paused'}</span></div>
   <div className="flex flex-wrap gap-4 text-xs"><span>Pending: {watchSnapshot?.PENDING??'—'}</span><span>Processing: {watchSnapshot?.PROCESSING??'—'}</span><span>Completed: {watchSnapshot?.COMPLETED??'—'}</span><span>Failed: {watchSnapshot?.FAILED??'—'}</span></div>
   <p className="text-[11px] text-slate-500">Campaign-wide stored job counts, not a batch percentage. Status checks make no paid AI or crawl requests.</p>
   <button type="button" className="intel-ghost text-xs" onClick={()=>setWatchProgress(v=>!v)}>{watchProgress?'Pause updates':'Resume free updates'}</button>
  </div>}</div>
  {campaign&&<div className="intel-card p-3 space-y-2"><div className="flex flex-wrap gap-2 items-center"><strong className="text-sm">Automatic AI worker readiness · free check</strong><button type="button" className="intel-ghost text-xs" disabled={readinessBusy} onClick={async()=>{setReadinessBusy(true);try{const r=await base44.functions.invoke('socialListening',{action:'campaignAIWorkerReadiness',id:campaign,data:{}});setReadiness(r.data)}catch(e){setReadiness({error:e.response?.data?.detail||e.message})}finally{setReadinessBusy(false)}}}>Check readiness (free)</button></div>{readiness&&<p className="text-xs text-slate-600" role="status">{readiness.error||('Auto screening: '+(readiness.automatic_screening_enabled?'ON':'OFF')+' · Worker: '+(readiness.worker_enabled?'ON':'OFF')+' · Provider: '+(readiness.ai_provider_configured?'Configured':'Unavailable')+' · Database reservation: '+(readiness.database_supports_reservations?'Supported':'Unsupported')+' · Daily reserved: '+readiness.daily_reserved+'/'+readiness.daily_request_limit+' · Lifetime reserved: '+readiness.lifetime_reserved+'/'+readiness.lifetime_request_limit+' · '+(readiness.ready_to_process?'Ready if enabled':'Not enabled or limits incomplete'))}</p>}</div>}
  {jobCounts&&<div className="intel-card p-3 space-y-2" aria-label="AI job progress"><h3 className="text-sm font-semibold">AI job progress · stored status</h3><div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Pending','PENDING'],['Processing','PROCESSING'],['Completed','COMPLETED'],['Failed','FAILED']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{jobCounts[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">Job status is read-only and does not initiate provider calls. Reload to refresh.</p></div>}
  {reconciliation&&reconciliation.unassessed_without_job>0&&campaign&&<div className="intel-card p-3 flex flex-wrap items-center gap-3"><span className="text-xs text-slate-600">{reconciliation.unassessed_without_job} unassessed evidence records lack a job.</span><button type="button" className="intel-ghost text-xs" disabled={reconBusy} onClick={async()=>{setReconBusy(true);setReconNotice('');try{const r=await base44.functions.invoke('socialListening',{action:'campaignAssessmentJobReconcile',id:campaign,data:{}});setReconNotice((r.data.created_pending_jobs||0)+' missing pending job(s) created. Refresh to verify. No AI calls.')}catch(e){setReconNotice(e.response?.data?.detail||e.message)}finally{setReconBusy(false)}}}>Create missing jobs (free)</button>{reconNotice&&<span role="status" className="text-xs">{reconNotice}</span>}</div>}
  {reconciliation&&<div className="intel-card p-3 space-y-2" aria-label="AI assessment job reconciliation"><h3 className="text-sm font-semibold">Job / assessment reconciliation · read-only</h3><div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Unassessed without job','unassessed_without_job'],['Assessed without job','assessed_without_job'],['Pending job already assessed','pending_job_with_assessment'],['Completed job unassessed','completed_job_without_assessment']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{reconciliation[key]||0}</p></div>)}</div><p className="text-xs text-slate-500">Job and assessment counts use different records. These are reconciliation categories, not additional evidence. No data is changed or AI called.</p></div>}
  {violationDiagnostics&&<div className="intel-card p-3 space-y-2" aria-label="Potential violation diagnostics">
   <h3 className="text-sm font-semibold">Potential violation diagnostics · read only</h3>
   <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{[['Relevant assessments','assessed_relevant'],['Relevant with no accepted flag','relevant_without_signal'],['Relevant with valid flag','relevant_with_valid_signal'],['Relevant with rejected signals','relevant_with_rejected_signal'],['Raw AI signals','raw_signals'],['Rejected signals','rejected_signals'],['Active issue categories','active_issue_categories']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{violationDiagnostics[key]??0}</p></div>)}</div>
   {(violationDiagnostics.rejected_signals??0)>0&&<div className="border-t border-slate-200 pt-2"><p className="text-xs font-semibold mb-2">Why AI signals were rejected</p><div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{[['Invalid / inactive category','invalid_category'],['Invalid signal type','invalid_signal_type'],['Missing / short quote','missing_or_short_quote'],['Quote not in source','quote_not_in_source'],['Malformed signal','malformed_signal']].map(([label,key])=><div key={key} className="rounded-md bg-slate-50 p-2"><p className="text-xs text-slate-500">{label}</p><p className="font-semibold">{violationDiagnostics.rejection_reasons?.[key]??0}</p></div>)}</div></div>}
   {Object.keys(violationDiagnostics.rejected_type_values||{}).length>0&&<div className="border-t border-slate-200 pt-2" aria-label="Rejected stored signal types"><strong className="text-xs">Stored rejected signal types</strong><div className="flex flex-wrap gap-2 mt-2">{Object.entries(violationDiagnostics.rejected_type_values||{}).map(([type,count])=><span key={type} className="text-xs rounded-md bg-slate-50 border border-slate-200 px-2 py-1"><code>{type}</code>: {count}</span>)}</div><p className="text-xs text-slate-500 mt-1">Read only. Unknown types stay rejected until a source-supported compatibility rule is verified.</p></div>}
   <p className="text-xs text-slate-500">{violationDiagnostics.scope}. Unassessed, irrelevant and uncertain evidence is excluded from violation review. Rejected signals may have unsupported quotes or inactive categories. Zero accepted signals does not establish absence of actual violations. No provider credits used.</p>
  </div>}
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
 return <div className="space-y-6 max-w-[1350px] mx-auto">
 <header className="rounded-2xl bg-gradient-to-r from-[#132d45] to-[#116b58] text-white p-6 md:p-8">
  <p className="text-[11px] uppercase tracking-[.18em] text-[#aadbd1] font-extrabold">BAWASLU · Collection &amp; Triage</p>
  <h1 className="text-2xl md:text-3xl font-bold mt-2">{t('intelligence_inbox')}</h1>
  <p className="text-sm text-[#d0e8e2] mt-2">Review stored Social Listening evidence, distinguish AI suggestions from officer decisions, and preserve original sources.</p>
  <div className="mt-4 flex flex-wrap items-center gap-2 text-xs"><span className="rounded-full border border-white/30 bg-white/10 px-3 py-1.5">Source-linked findings</span><span className="rounded-full border border-white/30 bg-white/10 px-3 py-1.5">Human review audit trail</span><span className="rounded-full border border-white/30 bg-white/10 px-3 py-1.5">No implied legal verdict</span></div>
 </header>
 <Notice error={error}/>
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