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
 const [processingSummary,setProcessingSummary]=useState(null);
 const [summaryReadiness,setSummaryReadiness]=useState(null),[summaryBusy,setSummaryBusy]=useState(false),[summaryError,setSummaryError]=useState('');
 const [qaHistory,setQAHistory]=useState(null),[qaBusy,setQABusy]=useState(false),[qaError,setQAError]=useState('');
 const [acceptance,setAcceptance]=useState(null),[acceptanceBusy,setAcceptanceBusy]=useState(false),[acceptanceError,setAcceptanceError]=useState('');
 const [groupPreview,setGroupPreview]=useState(null),[groupRows,setGroupRows]=useState([]),[groupBusy,setGroupBusy]=useState(false),[groupNotice,setGroupNotice]=useState(''),[groupError,setGroupError]=useState(''),[groupExpanded,setGroupExpanded]=useState(false),[groupEvidence,setGroupEvidence]=useState(null);
 const [jurisdictionPreview,setJurisdictionPreview]=useState(null),[jurisdictionBusy,setJurisdictionBusy]=useState(false),[jurisdictionMessage,setJurisdictionMessage]=useState('');
 const [usageDiagnostics,setUsageDiagnostics]=useState(null),[usageBusy,setUsageBusy]=useState(false),[usageError,setUsageError]=useState('');
 const [violationDiagnostics,setViolationDiagnostics]=useState(null);const [readiness,setReadiness]=useState(null),[readinessBusy,setReadinessBusy]=useState(false),[reconBusy,setReconBusy]=useState(false),[reconNotice,setReconNotice]=useState(''),[reconciliation,setReconciliation]=useState(null),[jobCounts,setJobCounts]=useState(null),[findings,setFindings]=useState([]),[campaigns,setCampaigns]=useState([]),[campaign,setCampaign]=useState(requestedCampaign),[view,setView]=useState('all'),[term,setTerm]=useState(''),[selected,setSelected]=useState(null),[unassessed,setUnassessed]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[backlog,setBacklog]=useState(null),[backlogBusy,setBacklogBusy]=useState(false),[backlogStatus,setBacklogStatus]=useState(''),[assessmentCounts,setAssessmentCounts]=useState(null),[processingStatus,setProcessingStatus]=useState('');
 const [watchProgress,setWatchProgress]=useState(false),[watchSnapshot,setWatchSnapshot]=useState(null);
 const watchBaseline=useRef(null);
 const [issueCategories,setIssueCategories]=useState([]),[manualCategory,setManualCategory]=useState(''),[manualRationale,setManualRationale]=useState(''),[manualCue,setManualCue]=useState(null);
 const [correctionType,setCorrectionType]=useState('TOPICS'),[correctionTopics,setCorrectionTopics]=useState([]),[correctionQuote,setCorrectionQuote]=useState(''),[correctionConcern,setCorrectionConcern]=useState(''),[correctionRationale,setCorrectionRationale]=useState(''),[correctionBusy,setCorrectionBusy]=useState(false),[correctionMessage,setCorrectionMessage]=useState('');
 const [reviewDecision,setReviewDecision]=useState(''),[reviewRationale,setReviewRationale]=useState(''),[reviewBusy,setReviewBusy]=useState(false),[reviewError,setReviewError]=useState(''),[reviewNotice,setReviewNotice]=useState('');
 useEffect(()=>{let active=true;setLoading(true);setError('');
 base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',data:{campaign_id:campaign,result_id:requestedPost}})
 .then(r=>{if(!active)return;setFindings(r.data.findings||[]);
 if(requestedPost&&campaign===requestedCampaign){
  const found=(r.data.findings||[]).find(item=>String(item.id)===requestedPost&&String(item.campaign_id)===requestedCampaign);
  if(found)setSelected(found);
 }
 setIssueCategories(r.data.issue_categories||[]);setCampaigns(r.data.campaigns||[]);setUnassessed(r.data.unassessed_count||0);setAssessmentCounts(r.data.assessment_counts||null);setViolationDiagnostics(r.data.violation_diagnostics||null);setJobCounts(r.data.job_counts||null);setReconciliation(r.data.reconciliation||null);setProcessingStatus(r.data.processing_status||'');setProcessingSummary(r.data.classification_processing||null)})
 .catch(e=>{if(active)setError(e.response?.data?.detail||e.message||'Inbox unavailable')})
 .finally(()=>{if(active)setLoading(false)});
 return()=>{active=false}
 },[campaign]);
 useEffect(()=>{
  // Read-only overview: source evidence is immediately visible on campaign
  // selection, but saving a proposal still needs an explicit officer click.
  let cancelled=false;
  setGroupPreview(null);setGroupRows([]);setGroupEvidence(null);
  setGroupError('');setGroupExpanded(false);
  if(!campaign)return()=>{cancelled=true};
  Promise.allSettled([
   base44.functions.invoke('socialListening',{
     action:'campaignFindingGroupsPreview',id:campaign,data:{}}),
   base44.functions.invoke('socialListening',{
     action:'campaignFindingGroupsList',id:campaign,data:{}})
  ]).then(results=>{
    if(cancelled)return;
    if(results[0].status==='fulfilled'){
      const preview=results[0].value.data;
      setGroupPreview(preview);
      if(preview.proposal_count>0)setGroupExpanded(true);
    }
    if(results[1].status==='fulfilled'){
      const groups=results[1].value.data.groups||[];
      setGroupRows(groups);if(groups.length)setGroupExpanded(true);
    }
    if(results.every(x=>x.status==='rejected'))
      setGroupError('Group evidence preview unavailable. Retry using Preview groups.');
  });
  return()=>{cancelled=true};
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
    setReconciliation(payload.reconciliation||null);setProcessingStatus(payload.processing_status||'');setProcessingSummary(payload.classification_processing||null);
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
 async function refreshReviewedPost(post,expectedStatus=null){
  try{
   const response=await base44.functions.invoke('socialListening',{
    action:'campaignIntelligenceInbox',
    data:{campaign_id:String(post.campaign_id),result_id:String(post.id)}});
   const refreshed=(response.data.findings||[]).find(item=>
    String(item.id)===String(post.id)&&String(item.campaign_id)===String(post.campaign_id));
   if(refreshed){
    // Avoid overwriting a server-acknowledged decision with an older cached response.
    if(expectedStatus&&refreshed.flag_review_status!==expectedStatus)return;
    setSelected(refreshed);
    setFindings(previous=>previous.map(item=>
     String(item.id)===String(post.id)&&String(item.campaign_id)===String(post.campaign_id)
       ?refreshed:item));
   }
  }catch(_ignored){
   // Saved officer decisions remain saved even if the follow-up read fails.
  }
 }
 function selectKeywordCueForReview(lead){
  if(!selected?.can_review_flag||selected.is_flagged||(selected.potential_issues||[]).length)return;
  if(!issueCategories.some(item=>String(item.id)===String(lead.category_id))){
   setReviewError('This issue category is no longer active. Refresh the Inbox.');
   return;
  }
  setManualCategory(String(lead.category_id));
  setManualCue({post_id:String(selected.id),campaign_id:String(selected.campaign_id),
   category_id:String(lead.category_id),source_quote:lead.evidence_quote||''});
  setManualRationale('');
  setReviewError('');
 }
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
   await refreshReviewedPost(selected,reviewDecision);
  }catch(e){setReviewError(e.response?.data?.detail||e.message||'Unable to save review')}
  finally{setReviewBusy(false)}
 }
 async function submitManualFlag(){
  if(!selected||!manualCategory||manualRationale.trim().length<10||reviewBusy)return;
  if(!window.confirm('Create a human-origin preliminary flag requiring further investigation?'))return;
  setReviewBusy(true);setReviewError('');setReviewNotice('');
  try{
   const verifiedCue=manualCue&&manualCue.post_id===String(selected.id)&&
     manualCue.campaign_id===String(selected.campaign_id)&&
     manualCue.category_id===String(manualCategory)?manualCue.source_quote:'';
   await base44.functions.invoke('socialListening',{action:'campaignManualFlag',id:selected.campaign_id,
     data:{result_id:selected.id,assessment_version:selected.assessment_version,category_id:manualCategory,
       rationale:manualRationale.trim(),...(verifiedCue?{source_quote:verifiedCue}:{})}});
   const updated={...selected,flag_review_status:'FURTHER_INVESTIGATION',is_flagged:true};
   setSelected(updated);
   setFindings(previous=>previous.map(item=>item.id===selected.id&&item.campaign_id===selected.campaign_id?updated:item));
   setManualCategory('');setManualRationale('');setManualCue(null);
   setReviewNotice('Human-origin preliminary flag saved for further investigation; AI evidence unchanged.');
   await refreshReviewedPost(selected,'FURTHER_INVESTIGATION');
  }catch(e){setReviewError(e.response?.data?.detail||e.message||'Unable to save manual flag')}
  finally{setReviewBusy(false)}
 }

 async function loadUsageDiagnostics(){
  if(!campaign){setUsageError('Select a campaign to view AI usage.');return;}
  setUsageBusy(true);setUsageError('');
  try{const r=await base44.functions.invoke('socialListening',{
    action:'campaignUsageDiagnostics',id:campaign,data:{}});
   setUsageDiagnostics(r.data);
  }catch(e){setUsageError(e.response?.data?.detail||e.message)}
  finally{setUsageBusy(false)}
 }

 async function previewIncidentJurisdiction(){
  if(!selected)return;
  setJurisdictionBusy(true);setJurisdictionMessage('');setJurisdictionPreview(null);
  try{
   const r=await base44.functions.invoke('socialListening',{action:'campaignJurisdictionPreview',
    id:selected.campaign_id,data:{result_id:selected.id}});
   setJurisdictionPreview(r.data);
  }catch(e){setJurisdictionMessage(e.response?.data?.detail||e.message)}
  finally{setJurisdictionBusy(false)}
 }
 async function confirmIncidentJurisdiction(decision){
  if(!selected||!jurisdictionPreview)return;
  const possible=jurisdictionPreview.source_context_provinces_unverified||[];
  if(decision==='CONFIRMED'&&possible.length!==1){
   setJurisdictionMessage('Incident location is ambiguous or missing. Confirmation is not allowed.');return;
  }
  const rationale=window.prompt('Explain which explicit source passage supports your jurisdiction decision (at least 10 characters):');
  if(rationale===null)return;
  if(rationale.trim().length<10){setJurisdictionMessage('Provide at least 10 characters.');return;}
  if(!window.confirm('Store the officer jurisdiction review? This does not change regional access permissions.'))return;
  setJurisdictionBusy(true);setJurisdictionMessage('');
  try{
   const r=await base44.functions.invoke('socialListening',{
    action:'campaignJurisdictionReview',id:selected.campaign_id,
    data:{result_id:selected.id,decision,province:decision==='CONFIRMED'?possible[0]:'',
          rationale:rationale.trim()}});
   setJurisdictionPreview(r.data);
   const review=r.data.latest_review;
   const updated={...selected,incident_jurisdiction_review:review,
     incident_jurisdiction_verified:review.incident_jurisdiction_verified};
   setSelected(updated);
   setFindings(all=>all.map(item=>item.id===updated.id&&item.campaign_id===updated.campaign_id?updated:item));
   setJurisdictionMessage('Officer jurisdiction decision saved; source permissions unchanged.');
  }catch(e){setJurisdictionMessage(e.response?.data?.detail||e.message)}
  finally{setJurisdictionBusy(false)}
 }
 async function saveOfficerClassification(){
  if(!selected||correctionBusy)return;
  if(!window.confirm('Save a new officer-reviewed assessment version? The original AI assessment will remain unchanged.'))return;
  setCorrectionBusy(true);setCorrectionMessage('');
  try{
   const payload={result_id:selected.id,expected_version:selected.assessment_version,
    correction_type:correctionType,rationale:correctionRationale.trim(),
    ...(correctionType==='TOPICS'?{topics:correctionTopics}:{source_quote:correctionQuote.trim(),concern:correctionConcern.trim()})};
   await base44.functions.invoke('socialListening',{action:'campaignOfficerClassificationCorrection',
     id:selected.campaign_id,data:payload});
   const response=await base44.functions.invoke('socialListening',{action:'campaignIntelligenceInbox',
     data:{campaign_id:selected.campaign_id,result_id:selected.id}});
   const record=(response.data.findings||[]).find(x=>String(x.id)===String(selected.id));
   if(record){setSelected(record);setFindings(rows=>rows.map(x=>String(x.id)===String(record.id)&&String(x.campaign_id)===String(record.campaign_id)?record:x));}
   setCorrectionMessage('Officer correction saved as a new assessment version.');
  }catch(e){setCorrectionMessage(e.response?.data?.detail||e.response?.data?.error||e.message||'Correction failed')}
  finally{setCorrectionBusy(false)}
 }
 async function loadSummaryReadiness(){
  if(!campaign)return;
  setSummaryBusy(true);setSummaryError('');
  try{
   const result=await base44.functions.invoke('socialListening',{
    action:'campaignSummaryReadiness',id:campaign,data:{}});
   setSummaryReadiness(result.data);
  }catch(e){setSummaryError(e.response?.data?.detail||e.message)}
  finally{setSummaryBusy(false)}
 }
 async function loadAcceptance(){
  if(!campaign)return;
  setAcceptanceBusy(true);setAcceptanceError('');
  try{const r=await base44.functions.invoke('socialListening',{
    action:'campaignAcceptanceSnapshot',id:campaign,data:{}});
    setAcceptance(r.data);
  }catch(e){setAcceptanceError(e.response?.data?.detail||e.message)}
  finally{setAcceptanceBusy(false)}
 }
 async function loadQAHistory(){
  setQABusy(true);setQAError('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignQAHistorySummary',data:{}});setQAHistory(r.data)}
  catch(e){setQAError(e.response?.data?.detail||e.message)}
  finally{setQABusy(false)}
 }
 function focusPlayerEvidence(resultId){
  const item=findings.find(row=>String(row.id)===String(resultId));
  if(item){setSelected(item);setError('')}
  else setError('This evidence is outside the current visible Inbox page.');
 }
 async function previewFindingGroups(){
  if(!campaign){setGroupError('Select a campaign to preview groups.');return;}
  setGroupBusy(true);setGroupError('');setGroupNotice('');setGroupExpanded(true);
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsPreview',id:campaign,data:{}});setGroupPreview(r.data)}
  catch(e){setGroupError(e.response?.data?.detail||e.message)}
  finally{setGroupBusy(false)}
 }
 async function loadFindingGroups(){
  if(!campaign){setGroupError('Select a campaign first.');return;}
  setGroupBusy(true);setGroupError('');setGroupExpanded(true);
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsList',id:campaign,data:{}});setGroupRows(r.data.groups||[])}
  catch(e){setGroupError(e.response?.data?.detail||e.message)}
  finally{setGroupBusy(false)}
 }
 async function saveFindingGroups(){
  if(!groupPreview?.proposal_count||!campaign)return;
  if(!window.confirm('Save provisional incident, narrative and duplicate groups for human review? This uses only existing evidence and no AI credits.'))return;
  setGroupBusy(true);setGroupError('');
  try{
   const r=await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsSave',id:campaign,data:{confirm_save:true}});
   setGroupNotice(r.data.newly_saved+' review group(s) saved, '+r.data.already_saved+' already stored.');
   const listing=await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsList',id:campaign,data:{}});
   setGroupRows(listing.data.groups||[]);
  }catch(e){setGroupError(e.response?.data?.detail||e.message)}
  finally{setGroupBusy(false)}
 }
 async function inspectGroupEvidence(group){
  if(!campaign||!group)return;
  setGroupBusy(true);setGroupError('');
  try{
   const r=await base44.functions.invoke('socialListening',{
    action:'campaignFindingGroupSources',id:campaign,data:{group_id:group.id}});
   setGroupEvidence(r.data);
  }catch(e){setGroupEvidence(null);setGroupError(e.response?.data?.detail||e.message)}
  finally{setGroupBusy(false)}
 }
 async function reviewFindingGroup(group,decision){
  if(!campaign||!group)return;
  const rationale=window.prompt('Explain why the source posts belong together, or why they must remain separate (at least 10 characters):');
  if(rationale===null)return;
  if(rationale.trim().length<10){setGroupError('Enter at least 10 characters of review rationale.');return;}
  setGroupBusy(true);setGroupError('');
  try{
   await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsReview',id:campaign,
    data:{group_id:group.id,decision,rationale:rationale.trim()}});
   setGroupNotice('Grouping decision saved to the audit trail. This is not a legal violation determination.');
   const r=await base44.functions.invoke('socialListening',{action:'campaignFindingGroupsList',id:campaign,data:{}});
   setGroupRows(r.data.groups||[]);
  }catch(e){setGroupError(e.response?.data?.detail||e.message)}
  finally{setGroupBusy(false)}
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
const [sortDate,setSortDate]=useState('newest'),[dateFrom,setDateFrom]=useState(''),[dateTo,setDateTo]=useState(''),[sentimentFilter,setSentimentFilter]=useState('ALL');
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
   if(sentimentFilter!=='ALL'&&(['POSITIVE','NEUTRAL','NEGATIVE'].includes(String(x.sentiment||'').toUpperCase())?String(x.sentiment||'').toUpperCase():'UNCLASSIFIED')!==sentimentFilter)return false;
  if(reviewStatusFilter==='AWAITING_REVIEW'&&(x.flag_review_status||((x.is_flagged??((x.potential_issues||[]).length>0))?'AWAITING_REVIEW':'NONE'))!=='AWAITING_REVIEW')return false;
  if(reviewStatusFilter&&reviewStatusFilter!=='AWAITING_REVIEW'&&x.flag_review_status!==reviewStatusFilter)return false;
  const date=String(x.published_at||x.post_time||x.created_at||'').slice(0,10);
  if((dateFrom||dateTo)&&(!date||(dateFrom&&date<dateFrom)||(dateTo&&date>dateTo)))return false;
  return !term||(JSON.stringify([x.text_content,x.campaign_name,x.author_name,x.location_signals,x.candidate_signals,x.potential_issues]).toLowerCase().includes(term.toLowerCase()))
 }),[findings,view,term,sentimentFilter,jurisdiction,chosenLocation,chosenRegency,chosenCandidate,reviewStatusFilter,dateFrom,dateTo]);
 const ordered=useMemo(()=>[...filtered].sort((a,b)=>{const da=Date.parse(a.published_at||a.post_time||a.created_at||0)||0,db=Date.parse(b.published_at||b.post_time||b.created_at||0)||0;return sortDate==='newest'?db-da:da-db}),[filtered,sortDate]);
 const summary=useMemo(()=>{const counts={POSITIVE:0,NEGATIVE:0,NEUTRAL:0,UNCLASSIFIED:0};let engagement=0,views=0,engagementAvailable=0,viewsAvailable=0;for(const item of filtered){if(typeof item.engagement_total==='number'){engagement+=item.engagement_total;engagementAvailable++}if(typeof item.views==='number'){views+=item.views;viewsAvailable++}const raw=String(item.sentiment||'').toUpperCase();counts[['POSITIVE','NEGATIVE','NEUTRAL'].includes(raw)?raw:'UNCLASSIFIED']++}return {engagement,views,engagementAvailable,viewsAvailable,counts}},[filtered]);
 const platformCounts=useMemo(()=>{const grouped=new Map();for(const item of filtered){const raw=String(item.platform||'Unknown').trim();const name=platformLabel(raw);grouped.set(name,(grouped.get(name)||0)+1)}return [...grouped.entries()].map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));},[filtered]);
 const platformColors=['#147b9c','#d19550','#658e7e','#887cb2','#9b7184','#8296a5'];
 const buttons=[['all','All Relevant'],['violation','Potential Violation']];
 const [showAdvancedFilters,setShowAdvancedFilters]=useState(false);
 const issueGroups=signals=>Object.entries((signals||[]).reduce((groups,signal)=>{const category=String(signal.category_name||'Uncategorized potential issue');(groups[category] ||= []).push(signal);return groups;},{}));
 const activeFilters=[jurisdiction!=='national',Boolean(chosenLocation),Boolean(chosenRegency),Boolean(chosenCandidate),Boolean(reviewStatusFilter),sentimentFilter!=='ALL'].filter(Boolean).length;
 const reviewState=item=>item.flag_review_status==='FLAG_DISMISSED'?{label:'Dismissed · reviewed',cls:'text-slate-600'}:item.flag_review_status==='FLAG_CONFIRMED'?{label:'Flag confirmed · preliminary',cls:'text-amber-800'}:item.flag_review_status==='FURTHER_INVESTIGATION'?{label:'Further investigation',cls:'text-orange-700'}:(item.is_flagged??((item.potential_issues||[]).length>0))?{label:'Awaiting human review',cls:'text-amber-700'}:null;
 return <section className="space-y-4" aria-label="AI intelligence findings">
  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-end" aria-label="Campaign dates and totals">
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">Campaign<select className="intel-input mt-1 w-full h-10 min-w-0" aria-label="Filter campaign" value={campaign} onChange={e=>{setCampaign(e.target.value);setSelected(null)}}><option value="">All campaigns</option>{campaigns.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">From date<input type="date" className="intel-input mt-1 w-full h-10 min-w-0" value={dateFrom} onChange={e=>setDateFrom(e.target.value)}/></label>
   <label className="text-xs min-w-0 flex flex-col justify-end h-[70px]">To date<input type="date" className="intel-input mt-1 w-full h-10 min-w-0" min={dateFrom||undefined} value={dateTo} onChange={e=>setDateTo(e.target.value)}/></label>
  </div>
  <div className="intel-card px-3 py-2" aria-label="Filter intelligence">
   <div className="flex flex-wrap xl:flex-nowrap items-end gap-2">
    <label className="text-xs flex-1 min-w-[125px]">Province<select className="intel-input mt-1 w-full" value={chosenLocation} onChange={e=>{setChosenLocation(e.target.value);setJurisdiction('location');setSelected(null)}}><option value="">All provinces</option>{groupedLocations.provinces.map(name=><option key={name} value={name}>{name}</option>)}</select></label>
    <label className="text-xs flex-1 min-w-[125px]">Candidate<select className="intel-input mt-1 w-full" value={chosenCandidate} onChange={e=>{setChosenCandidate(e.target.value);setSelected(null)}}><option value="">All candidates</option>{candidates.map(name=><option key={name} value={name}>{name}</option>)}</select></label>
    <label className="text-xs flex-1 min-w-[125px]">Sentiment<select className="intel-input mt-1 w-full" aria-label="Filter by sentiment" value={sentimentFilter} onChange={e=>{setSentimentFilter(e.target.value);setSelected(null)}}><option value="ALL">All sentiments</option><option value="POSITIVE">Positive</option><option value="NEUTRAL">Neutral</option><option value="NEGATIVE">Negative</option><option value="UNCLASSIFIED">Unclassified</option></select></label>
     <label className="text-xs flex-1 min-w-[125px]">Sort by date<select className="intel-input mt-1 w-full" value={sortDate} onChange={e=>setSortDate(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
  <label className="flex items-center gap-2 text-xs font-medium whitespace-nowrap min-h-10"><input type="checkbox" checked={view==='violation'} onChange={e=>{setView(e.target.checked?'violation':'all');setSelected(null)}}/>Potential violation only</label>
   </div>
  </div>
  {processingSummary&&<section className="intel-card p-3 space-y-2" aria-label="Processing and QA diagnostics">
   <h3 className="text-sm font-semibold">Processing and QA diagnostics</h3>
   <p className="text-xs text-slate-500">Detailed classification screening stays in Command Centre. These controls are for assessment quality, coverage and acceptance checks.</p>
   <details className="text-xs"><summary className="cursor-pointer font-semibold">Coverage and evidence diagnostics</summary><p className="mt-2 text-slate-600">Missing source URLs: {processingSummary.processing_diagnostics?.missing_field_counts?.canonical_url??0} · Unclassified sentiment: {processingSummary.processing_diagnostics?.missing_field_counts?.sentiment??0} · Attention cues with a source quote: {processingSummary.processing_diagnostics?.posts_with_source_quoted_attention_evidence??0} · Officer follow-up requested: {processingSummary.processing_diagnostics?.human_follow_up_requested??0}. Source-specific model usage is available separately. Dollar costs remain unavailable unless reported by the provider.</p></details>
   <div className="space-y-2">
     <button type="button" className="intel-ghost text-xs" disabled={qaBusy} onClick={loadQAHistory}>Compare saved Shahrin QA results (admin · free)</button>
     {qaHistory&&<div className="text-xs space-y-2">
       <p>Historical predictions only; holdout data excluded. Target: {qaHistory.target_accuracy_percent}%.</p>
       {qaHistory.reference_signoff&&<section className="rounded border border-amber-200 p-2 space-y-1">
         <strong>Analyst-label sign-off: {qaHistory.reference_signoff.analyst_approved}/{qaHistory.reference_signoff.total_imported}</strong>
         <p>{qaHistory.reference_signoff.remaining_unsigned} labels still need a human decision; {qaHistory.reference_signoff.duplicate_source_unresolved} approved duplicate-source records still need source-relation reconciliation. Imported category labels are not automatically approved.</p>
         <a className="underline" href="/smart-radar/qa">Open the authenticated QA Lab for analyst review</a>
       </section>}
       {(qaHistory.analyst_reviewed_accuracy||[]).length>0&&<div className="rounded border p-2">
         <strong>Accuracy on analyst-approved labels only (not historical score)</strong>
         {qaHistory.analyst_reviewed_accuracy.slice(0,8).map((row,i)=><p key={i}>{row.prompt_version}: {row.matched}/{row.reviewed_posts} ({row.accuracy_percent}%) · {row.official_acceptance_eligible?'Reference coverage adequate':'Not ready for formal acceptance'}</p>)}
       </div>}<div className="max-h-52 overflow-y-auto"><table className="w-full text-left"><thead><tr><th>Version</th><th>Correct</th><th>Accuracy</th><th>Reference status</th></tr></thead><tbody>{(qaHistory.versions||[]).map(v=><tr key={v.prompt_version+v.model}><td>{v.prompt_version}</td><td>{v.correct}/{v.evaluated}</td><td>{v.accuracy_percent??'N/A'}%</td><td>{v.unsigned_reference_labels?'Pending sign-off':'Approved labels'}</td></tr>)}</tbody></table></div></div>}
     {qaHistory?.error_patterns?.length>0&&<details className="rounded border p-2">
      <summary className="cursor-pointer font-semibold">Most common saved category confusions · no new AI inference</summary>
      <p>Historical Shahrin labels still await sign-off. Sealed holdout excluded.</p>
      <div className="max-h-48 overflow-auto mt-2"><table className="w-full text-left"><thead><tr><th>Version</th><th>Expected</th><th>Predicted</th><th>Errors</th></tr></thead><tbody>
       {qaHistory.error_patterns.map((x,i)=><tr key={i}><td>{x.prompt_version} · {x.cohort}</td><td>{x.expected_category}</td><td>{x.predicted_category}</td><td>{x.error_count}</td></tr>)}
      </tbody></table></div>
     </details>}
     {qaError&&<p role="alert" className="text-red-700">{qaError}</p>}
   </div>
   {campaign&&<div className="space-y-2 border-t pt-2">
      <button type="button" className="intel-ghost text-xs" disabled={summaryBusy} onClick={loadSummaryReadiness}>Inspect #12 AI summary readiness (free)</button>
      {summaryReadiness&&<div className="text-xs rounded border p-2 space-y-1">
       <strong>#12 remains IN PROGRESS until real saved AI drafts are verified.</strong>
       <p>{summaryReadiness.posts_with_valid_saved_ai_drafts} / {summaryReadiness.visible_relevant_posts} relevant saved posts contain source-matched AI drafts. {summaryReadiness.posts_with_development_chatgpt_samples||0} are GPT-6 development samples; {summaryReadiness.posts_with_pipeline_ai_drafts||0} have app-pipeline drafts. {summaryReadiness.posts_needing_ai_drafts} still lack drafts.</p>
       <p>Development drafts do not count as app-pipeline acceptance or human approval.</p>
       <p>Suggested representative pilot source IDs: {(summaryReadiness.suggested_small_pilot_ids||[]).join(', ')||'None'}.</p>
       <p>Viewing this evidence never calls an AI provider. Source excerpts are NOT AI summaries.</p>
      </div>}
      {summaryError&&<p role="alert" className="text-red-700 text-xs">{summaryError}</p>}
      <button type="button" className="intel-ghost text-xs" disabled={acceptanceBusy} onClick={loadAcceptance}>Load production acceptance evidence (free)</button>
      {acceptance&&<div className="space-y-2">
       <p className="text-xs">{acceptance.relevant_posts} relevant saved / {acceptance.authorized_posts} authorized posts · {acceptance.unassessed_posts} unassessed · {acceptance.saved_groups_count} saved groups. No item below represents formal officer sign-off.</p>
       <div className="rounded border p-2 space-y-1 text-xs">
        <strong>Unfinished production acceptance — concrete next actions</strong>
        {(acceptance.next_actions||[]).map((item,i)=><p key={i}>
         <b>#{item.item} · {item.status.replaceAll('_',' ')}:</b> {item.instruction}
        </p>)}
        <p className="text-slate-500">Not marked DONE until all required evidence and approvals exist.</p>
       </div>
       <div className="max-h-72 overflow-y-auto space-y-1">{(acceptance.items||[]).map(x=><div key={x.number} className="rounded border p-2 text-xs">
        <strong>#{x.number} · {x.name}</strong> — {x.production_state.replaceAll('_',' ')} · {x.supporting_records} supporting record(s)
        <p className="text-slate-600">{x.note}</p></div>)}</div>
      </div>}
      {acceptanceError&&<p role="alert" className="text-xs text-red-700">{acceptanceError}</p>}
    </div>}
   {campaign&&<div className="space-y-2"><button type="button" className="intel-ghost text-xs" disabled={usageBusy} onClick={loadUsageDiagnostics}>Load AI usage and failure diagnostics (free)</button>{usageDiagnostics&&<p className="text-xs text-slate-600">Posts assessed: {usageDiagnostics.posts_with_assessment_version} / {usageDiagnostics.authorized_source_posts} · Failed jobs: {usageDiagnostics.failed_jobs} · Provider-reported tokens: {usageDiagnostics.ai_usage?.input_tokens_reported??0} input / {usageDiagnostics.ai_usage?.output_tokens_reported??0} output · Costs: {usageDiagnostics.ai_usage?.cost_status||'UNAVAILABLE'} · Missing source text: {usageDiagnostics.missing_fields?.content??0}</p>}{usageError&&<p role="alert" className="text-xs text-red-700">{usageError}</p>}</div>}
  </section>}
  {campaign&&<section className="intel-card p-3 space-y-3" aria-label="Persistent candidate, incident and narrative review">
   <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="text-sm font-semibold">Source-linked grouping review</h3><p className="text-xs text-slate-500">Exact duplicates, incident clusters and Emerging Narratives · saved separately from legal findings.</p></div><div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost text-xs" disabled={groupBusy} onClick={previewFindingGroups}>Preview groups (free)</button><button type="button" className="intel-ghost text-xs" disabled={groupBusy} onClick={loadFindingGroups}>Saved groups</button></div></div>
   {groupPreview&&<div className="text-xs space-y-2">
    <p>{groupPreview.proposal_count} proposed group(s) · {groupPreview.eligible_posts} relevant assessed posts for incident/narrative analysis · {groupPreview.exact_duplicate_source_posts} source posts checked for exact duplication regardless of assessment.
      {groupPreview.source_window_truncated?' Only the first 300 linked posts were scanned.':''}</p>
    <p className="text-slate-600">Read-only evidence preview. No group is accepted or saved automatically. Missing narrative candidates can be valid when independent relevant sources are insufficient.</p>
    {!!groupPreview.proposal_evidence?.length&&<div className="space-y-2 max-h-64 overflow-y-auto">
      {groupPreview.proposal_evidence.map((proposal,i)=><article key={i} className="rounded border border-slate-200 p-2">
        <strong>{proposal.type.replaceAll('_',' ')} · {proposal.sources.length} source(s)</strong>
        <div className="space-y-1 mt-1">{proposal.sources.slice(0,4).map(source=><div key={source.id} className="bg-slate-50 rounded p-2">
          <p className="text-slate-800 whitespace-pre-wrap break-words">{source.text_excerpt||'No source text supplied'}</p>
          <p className="text-slate-500">Source {source.id} · {source.author_name||'Unknown author'} · {source.relevance_label==='NOT_REQUIRED_FOR_EXACT_DUPLICATE'?'Relevance not required':source.relevance_label}</p>
          {safeOriginalUrl(source.canonical_url)&&<a className="underline" href={safeOriginalUrl(source.canonical_url)} target="_blank" rel="noreferrer">Inspect original source</a>}
        </div>)}</div>
      </article>)}
    </div>}
    {groupPreview.proposal_count>0&&<button type="button" className="intel-button text-xs" disabled={groupBusy} onClick={saveFindingGroups}>Save provisional groups for officer review</button>}
  </div>}
   {groupExpanded&&groupRows.length===0&&!groupBusy&&<p className="text-xs text-slate-500">No saved review groups yet. Preview existing assessed posts, then save proposed groups before officer review.</p>}
   {!!groupRows.length&&<div className="space-y-2 max-h-64 overflow-y-auto">{groupRows.map(row=><div className="rounded-lg border border-slate-200 p-2 text-xs flex flex-wrap justify-between gap-2" key={row.id}><div><strong>{row.group_type.replaceAll('_',' ')} · {row.label}</strong><p className="text-slate-600">Source posts: {row.source_ids.length} · {row.review_status}</p>
<p className="text-slate-500">{row.proposed_by_automation?'Automatically staged, unreviewed proposal · officer decision required':'Officer-created proposal · review status above'}</p><p className="text-slate-500">Human grouping decisions do not establish a legal violation.</p><button type="button" className="intel-ghost text-xs mt-1" disabled={groupBusy} onClick={()=>inspectGroupEvidence(row)}>View all group evidence</button><div className="flex flex-wrap gap-1 mt-1">{row.source_ids.map(id=><button key={id} type="button" className="intel-ghost text-xs" onClick={()=>{const source=findings.find(x=>String(x.id)===String(id)&&String(x.campaign_id)===String(row.campaign_id));if(source){setSelected(source);setReviewDecision('');setReviewRationale('');setReviewError('');setReviewNotice('')}else{setGroupError('This source is outside the currently loaded Inbox findings. Open the matching campaign evidence view to inspect it.')}}}>Inspect source {id}</button>)}</div></div>{groupEvidence?.group_id===row.id&&<div className="basis-full space-y-2 border-t pt-2" aria-label="Source evidence for review">{groupEvidence.sources.map(src=><article key={src.id} className="border rounded p-2"><strong>Source {src.id} · {src.relevance_label}</strong><p className="whitespace-pre-wrap break-words mt-1">{src.text_content||'Source text unavailable'}</p><p className="text-slate-500">{src.author_name||'Unknown author'} · {src.published_at||'Date unavailable'}</p>{safeOriginalUrl(src.canonical_url)&&<a className="underline" href={safeOriginalUrl(src.canonical_url)} target="_blank" rel="noreferrer">Open original source</a>}</article>)}</div>}{row.review_status==='PROPOSED'&&<div className="flex gap-2"><button className="intel-ghost text-xs" disabled={groupBusy} onClick={()=>reviewFindingGroup(row,'ACCEPTED')}>Accept group</button><button className="intel-ghost text-xs" disabled={groupBusy} onClick={()=>reviewFindingGroup(row,'REJECTED')}>Reject group</button></div>}</div>)}</div>}
   {groupNotice&&<p className="text-xs text-emerald-700" role="status">{groupNotice}</p>}{groupError&&<p className="text-xs text-red-700" role="alert">{groupError}</p>}
  </section>}
  {error&&<p role="alert" className="text-sm text-red-600">{error}</p>}
  {loading?<p className="text-sm text-slate-500">Loading assessed campaign evidence…</p>:<div className="space-y-2">
   <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_260px] gap-3 items-stretch">
   <section aria-label="Scrollable intelligence posts" className="min-w-0 flex flex-col gap-2 xl:relative xl:min-h-[680px]">
    <div className="flex items-center justify-between text-xs text-slate-500 px-1"><span>Posts · {filtered.length} results</span></div>
    <div className="max-h-[680px] xl:max-h-none xl:absolute xl:inset-x-0 xl:top-6 xl:bottom-0 overflow-y-auto overscroll-contain pr-1 space-y-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden" tabIndex={0} aria-label="Post list, scroll to see more">
     {ordered.map(item=><button key={item.campaign_id+'-'+item.id} type="button" onClick={()=>{setSelected(item);setReviewDecision('');setReviewRationale('');setReviewError('');setReviewNotice('')}} className="w-full min-h-[84px] text-left intel-card p-3 space-y-1 hover:border-sky-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-500">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
         <div className="text-xs text-slate-500">{item.campaign_name} · {platformLabel(item.platform)}</div>
         {String(item.model_version||'').toLowerCase()==='mock-fixture'&&<span className="inline-flex rounded border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] text-violet-800">Synthetic QA example</span>}
         <p className="line-clamp-2 text-sm text-slate-700 whitespace-pre-wrap">{item.text_content||'No text available'}</p>
         <p className="text-xs text-[#146a8b]">View source and assessment →</p>
        </div>
        <div className="shrink-0 flex flex-col gap-1 items-end text-right" aria-label="Saved flag and sentiment indicators">
         <span className={'rounded-md border px-2 py-1 text-[11px] font-semibold '+((item.is_flagged??((item.potential_issues||[]).length>0))?'bg-amber-50 border-amber-300 text-amber-800':'bg-slate-50 border-slate-200 text-slate-600')}>{(item.is_flagged??((item.potential_issues||[]).length>0))?'⚑ Flagged · unverified':'Not flagged'}</span>
         <span className={'rounded-md border px-2 py-1 text-[11px] font-semibold '+(String(item.sentiment||'').toUpperCase()==='POSITIVE'?'bg-teal-50 border-teal-200 text-teal-800':String(item.sentiment||'').toUpperCase()==='NEGATIVE'?'bg-orange-50 border-orange-200 text-orange-800':'bg-slate-50 border-slate-200 text-slate-600')}>{['POSITIVE','NEUTRAL','NEGATIVE'].includes(String(item.sentiment||'').toUpperCase())?String(item.sentiment).toUpperCase():'UNCLASSIFIED'}</span>
         {reviewState(item)&&<span className={'text-[10px] max-w-[125px] '+reviewState(item).cls}>{reviewState(item).label}</span>}
        </div>
       </div>
     </button>)}
     {!filtered.length&&<p className="intel-card p-5 text-sm text-slate-500">No campaign-assessed findings match this view yet. New Social Listening evidence will appear here after collection, assessment and relevance checks. The separate historical Intelligence and Smart Radar pilot records are not counted as campaign findings.</p>}
    </div>
   </section>
   <div className="grid grid-rows-2 gap-3 xl:sticky xl:top-4 min-w-0">
   <aside className="intel-card p-4 space-y-4 h-full min-h-0" aria-label="Inbox statistics">
    <div><h4 className="font-semibold text-sm">Statistics</h4><p className="text-xs text-slate-500 mt-1">Filtered assessed posts</p></div>
    <div className="grid grid-cols-2 gap-2">
      <div className="rounded-lg bg-teal-50 p-3"><p className="text-xs text-teal-900">Posts shown</p><strong className="text-lg tabular-nums">{filtered.length}</strong><p className="text-[10px] text-slate-500">Relevant, filtered</p></div>
      <div className="rounded-lg bg-amber-50 p-3"><p className="text-xs text-amber-900">Potential violations</p><strong className="text-lg tabular-nums">{filtered.filter(x=>x.is_flagged??((x.potential_issues||[]).length>0)).length}</strong><p className="text-[10px] text-slate-500">Preliminary signals</p></div>
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
      {String(selected.model_version||'').toLowerCase()==='mock-fixture'&&<div role="note" className="rounded-lg border border-violet-200 bg-violet-50 p-3 text-xs text-violet-900"><strong>Synthetic QA example.</strong> This is not a real social-media post. Officer review is required; do not treat this fixture as election evidence.</div>}
     <section className="rounded-xl border border-[#dce6e8] bg-[#f5f9f9] p-4 space-y-2">
      <h4 className="font-bold text-sm text-[#184e48]">Original source provenance</h4>
      <p className="text-xs text-slate-600">Source post ID: <code className="break-all">{selected.id||'Not supplied'}</code></p>
      <p className="text-xs text-slate-600">Platform: {platformLabel(selected.platform)} · Publisher: {selected.observed_handle||selected.author_name||'Not recorded'}</p>
      <p className="text-xs text-slate-600">Published: {selected.published_at||'Publication time not recorded'}</p>
      {safeOriginalUrl(selected.canonical_url)?<a href={safeOriginalUrl(selected.canonical_url)} target="_blank" rel="noopener noreferrer" className="inline-block text-xs font-semibold text-[#147b67] hover:underline">Open original source ↗</a>:<p className="text-xs text-amber-700">Source URL not available; do not treat this record as independently verifiable.</p>}
     </section>
     <p className="text-xs text-slate-500">{selected.campaign_name} · {platformLabel(selected.platform)}</p><p className="whitespace-pre-wrap">{selected.text_content||'No text available'}</p><div className="border-t pt-3 space-y-2"><p><strong>Why relevant:</strong> {selected.explanation||'No explanation stored'}</p><p><strong>AI assessment:</strong> {selected.relevance_label} · Confidence: {selected.relevance_confidence||'Not provided'}</p><p><strong>Saved sentiment:</strong> {selected.sentiment||'UNCLASSIFIED'} · Confidence: {selected.sentiment_confidence||'Not provided'}{selected.sentiment_explanation?' · '+selected.sentiment_explanation:''} · {selected.sentiment_model?'AI processed':'Not sentiment-assessed'}</p><p><strong>Location signals:</strong> {signalNames(selected.location_signals).join(', ')||'None'}</p>
     <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-2" aria-label="Officer incident jurisdiction review">
      <p><strong>Human incident location:</strong> {selected.incident_jurisdiction_review?.incident_jurisdiction_verified?selected.incident_jurisdiction_review.incident_province:'Not verified'} · {selected.incident_jurisdiction_review?.decision||'UNREVIEWED'} · Profile location does not establish incident jurisdiction.</p>
      <button type="button" className="intel-ghost text-xs" disabled={jurisdictionBusy} onClick={previewIncidentJurisdiction}>Preview source-grounded location (free)</button>
      {jurisdictionPreview&&<div className="space-y-1"><p>Explicit incident-context provinces: {(jurisdictionPreview.source_context_provinces_unverified||[]).join(', ')||'None identified'} · Assessment relevant: {jurisdictionPreview.source_post_relevance_assessed?'Yes':'No'}</p>{selected.can_review_flag&&jurisdictionPreview.source_post_relevance_assessed&&<div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost text-xs" disabled={jurisdictionBusy||(jurisdictionPreview.source_context_provinces_unverified||[]).length!==1} onClick={()=>confirmIncidentJurisdiction('CONFIRMED')}>Verify incident province</button><button type="button" className="intel-ghost text-xs" disabled={jurisdictionBusy} onClick={()=>confirmIncidentJurisdiction('REJECTED')}>Reject location cue</button></div>}</div>}
      {jurisdictionMessage&&<p role="status" className="text-slate-600">{jurisdictionMessage}</p>}
     </div><p><strong>Communication context (review hint):</strong> {selected.processing_hints?.communication_context?.category||'UNRESOLVED'} · Actionability not established; existing AI and human decisions remain unchanged.</p><p><strong>Topic suggestions (text-only):</strong> {(selected.processing_hints?.topic_suggestions||[]).join(', ')||'None'}</p><p><strong>Province mentions (not verified incident location):</strong> {(selected.processing_hints?.province_mentions||[]).join(', ')||'None'}</p><p><strong>Candidate signals:</strong> {signalNames(selected.candidate_signals).join(', ')||'None'}</p>{(selected.topic_labels||[]).length>0&&<p><strong>AI topic classification:</strong> {selected.topic_labels.join(', ')} · Based on saved assessment, not keyword hints.</p>}
     {selected.can_review_flag&&<section className="rounded-lg border border-teal-200 p-3 space-y-2" aria-label="Officer classification corrections">
      <h4 className="font-semibold">Officer topic / Public Concerns correction</h4>
      <p className="text-xs text-slate-500">Creates a new audited assessment version. Does not replace the original AI output or prove wrongdoing.</p>
      <select aria-label="Correction type" className="intel-input w-full" value={correctionType} onChange={e=>setCorrectionType(e.target.value)}><option value="TOPICS">Correct topic classification</option><option value="PUBLIC_CONCERN">Record source-grounded Public Concern</option></select>
      {correctionType==='TOPICS'?<div className="space-y-1">{['Electoral Operations','BAWASLU Reputation'].map(topic=><label className="flex gap-2 items-center text-xs" key={topic}><input type="checkbox" checked={correctionTopics.includes(topic)} onChange={e=>setCorrectionTopics(old=>e.target.checked?[...old,topic]:old.filter(x=>x!==topic))}/>{topic}</label>)}<p className="text-xs text-slate-500">Leave both unchecked to remove unsupported topic labels.</p></div>:<><textarea aria-label="Verbatim concern evidence" className="intel-input w-full" value={correctionQuote} onChange={e=>setCorrectionQuote(e.target.value)} placeholder="Copy a verbatim source excerpt (15+ characters)" rows={2}/><input aria-label="Public concern description" className="intel-input w-full" value={correctionConcern} onChange={e=>setCorrectionConcern(e.target.value)} placeholder="Concise description of the public concern"/></>}
      <textarea aria-label="Officer correction rationale" className="intel-input w-full" rows={2} value={correctionRationale} onChange={e=>setCorrectionRationale(e.target.value)} placeholder="Independent review rationale (15+ characters)" />
      <button type="button" className="intel-button" disabled={correctionBusy||correctionRationale.trim().length<15||(correctionType==='PUBLIC_CONCERN'&&(correctionQuote.trim().length<15||correctionConcern.trim().length<10))} onClick={saveOfficerClassification}>{correctionBusy?'Saving…':'Save officer classification review'}</button>
      {correctionMessage&&<p role="status" className="text-xs">{correctionMessage}</p>}
     </section>}
     {(selected.public_concern_signals||[]).length>0&&<section className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1"><strong>Public Concerns · unverified source quotations</strong>{selected.public_concern_signals.map((item,i)=><p key={i} className="text-xs">“{item.evidence_quote}” · {item.concern}</p>)}</section>}
     {selected.attention_assessment?.status==='AI_ASSESSMENT_UNVERIFIED'&&<p><strong>AI Needs Attention suggestion:</strong> Seriousness {selected.attention_assessment.seriousness} · Urgency {selected.attention_assessment.urgency} · Human triage required, not an automatic order.</p>}
     {(selected.player_summaries||[]).length>0&&<section className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1" aria-label="AI player summary drafts"><strong>Source-referenced AI summary drafts</strong>{selected.player_summaries.map((item,i)=><p key={i} className="text-xs"><strong>{item.player}:</strong> {item.summary} <span className="text-slate-500">Evidence: “{item.source_quote}” · Human verification required</span></p>)}</section>}
     <p><strong>Canonical Watchlist candidate IDs:</strong> {(selected.canonical_candidate_ids||[]).join(', ')||'Not resolved'} · Alias matches require human verification.</p><p><strong>Potential issue categories:</strong> {[...new Set((selected.potential_issues||[]).map(x=>x.category_name).filter(Boolean))].join(', ')||'None flagged'}</p>{(selected.issue_review_leads||[]).length>0&&<div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs" role="note" aria-label="Text-only review cues"><p className="font-semibold">Keyword review cues (not violation flags)</p><p>{[...new Set(selected.issue_review_leads.map(x=>x.category_name).filter(Boolean))].join(', ')}</p><p>Text patterns require independent confirmation and do not enter the Potential Violations or Needs Attention queues automatically.</p>
      {selected.can_review_flag&&!selected.is_flagged&&!(selected.potential_issues||[]).length&&
       <div className="space-y-2 mt-2">{selected.issue_review_leads.map((lead,i)=>
        <div key={i} className="border-t border-slate-200 pt-2"><p className="italic">“{lead.evidence_quote}”</p>
         <button type="button" className="intel-ghost text-xs" disabled={reviewBusy}
          onClick={()=>selectKeywordCueForReview(lead)}>Escalate source cue for officer review</button>
        </div>)}</div>}
     </div>}{(selected.potential_issues||[]).length>0&&<div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-2" aria-label="Potential issue evidence"><h4 className="text-sm font-semibold">Why this was flagged · preliminary evidence</h4>{issueGroups(selected.potential_issues).map(([category,signals])=><div key={category} className="text-xs space-y-2"><p className="font-semibold">{category} · {signals.length} {signals.length===1?'signal':'signals'} · Unverified</p>{signals.map((signal,index)=><div key={index} className="pl-2 border-l-2 border-amber-400 space-y-1"><p className="font-medium">{signal.signal_type==='REPORTED_INCIDENT'?'Reported incident · '+(signal.time_context||'UNKNOWN').toLowerCase():'Potential violation'}</p>{signal.evidence_quote&&<blockquote className="whitespace-pre-wrap">Source excerpt: “{signal.evidence_quote}”</blockquote>}<p>{signal.explanation||'Requires human review against the original source.'}</p></div>)}</div>)}<p className="text-xs text-amber-800">Source-supported text is not proof of a legal violation. Verify independently before acting.</p></div>}{(selected.potential_issues||[]).some(x=>x.signal_provenance==='LEGACY_MISSING_TYPE')&&<p className="text-xs text-amber-700" role="note">Legacy AI signal (original type missing) · Source quotation validated · Human verification required</p>}<p className="text-xs text-slate-500">Assessment v{selected.assessment_version} · Model {selected.model_version||'unspecified'} · Human verification required</p></div>
    {<div className="border-t pt-3 space-y-3">
     <h4 className="font-semibold">Human flag review</h4>
     <p className="text-xs text-slate-500">Flag decisions do not establish legal violations and do not change the original AI assessment.</p>
     <p className="text-xs">Current status: <strong>{selected.flag_review_status||((selected.is_flagged||(selected.potential_issues||[]).length>0)?'Awaiting review':'Not flagged for violation')}</strong></p>
     {(selected.flag_review_history||[]).length>0&&<details className="text-xs"><summary className="cursor-pointer font-semibold">Review history ({selected.flag_review_history.length} most recent)</summary><ol className="mt-2 space-y-2">{selected.flag_review_history.map((entry,index)=><li key={index} className="border-l-2 border-slate-200 pl-2"><strong>{entry.decision.replaceAll('_',' ')}</strong> · Assessment v{entry.assessment_version} · {entry.reviewed_at?new Date(entry.reviewed_at).toLocaleString():'Date unavailable'}<p className="text-slate-500">{entry.rationale}</p></li>)}</ol></details>}
     {selected.can_review_flag&&!(selected.potential_issues||[]).length&&!selected.is_flagged&&<div className="border border-amber-200 rounded-lg p-3 space-y-2"><p className="text-xs font-semibold">Flag this relevant post manually</p><p className="text-xs text-slate-500">Preliminary human concern only — not a legal finding.</p><label htmlFor="manual-issue-category" className="text-xs">Issue category</label><select id="manual-issue-category" className="intel-input w-full" value={manualCategory} onChange={e=>setManualCategory(e.target.value)}><option value="">Select active category</option>{issueCategories.map(category=><option key={category.id} value={category.id}>{category.name}</option>)}</select><label htmlFor="manual-flag-rationale" className="text-xs">Reason (at least 10 characters)</label>{manualCue?.post_id===String(selected.id)&&manualCue?.campaign_id===String(selected.campaign_id)&&
      manualCue?.category_id===String(manualCategory)&&
      <p className="text-xs text-amber-800">Selected unverified source cue: “{manualCue.source_quote}” · This does not verify a legal violation.</p>}
     <textarea id="manual-flag-rationale" className="intel-input w-full" value={manualRationale} onChange={e=>setManualRationale(e.target.value)} maxLength={1500} placeholder="Your independent evidence assessment and reason for further investigation (required)"/><button type="button" className="intel-button" disabled={reviewBusy||!manualCategory||manualRationale.trim().length<10} onClick={submitManualFlag}>Flag for investigation</button></div>}
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
   {auditOpen&&<p className="text-xs text-slate-600">Human correction records a new assessment version. Routine suggestions never silently change the AI label.</p>}
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