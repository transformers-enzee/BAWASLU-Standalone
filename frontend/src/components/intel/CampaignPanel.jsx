import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, ImageOff, Smile, Meh, Frown, CircleHelp } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { base44 } from '@/api/base44Client';
import CampaignScheduleSummary from '@/components/intel/CampaignScheduleSummary';
import KeywordTags from '@/components/intel/KeywordTags';

const options=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin','online_news'];
const initial={name:'',description:'',primary_keywords:[],secondary_keywords:[],excluded_keywords:[],platforms:['tiktok'],language:'',date_from:'',date_to:'',interval_minutes:120,province:'',regency_city:''};
const split=v=>String(v||'').split(',').map(s=>s.trim()).filter(Boolean);
const presentDate=v=>v?new Date(v).toLocaleString('en-GB'):'Not scheduled';
const displayStatus=s=>s==='PAUSED'?'Paused':'Draft';
function ChannelDonut({values}){
 const entries=Object.entries(values||{}).filter(([,n])=>n>0);
 const total=entries.reduce((n,[,v])=>n+v,0);
 const palette=['#285f82','#bc9b62','#339b92','#815ca7','#d2735c','#6d84a1','#69865f','#b95b83'];
 let offset=0;
 const segments=entries.map(([name,count],i)=>{const start=offset;offset+=count/total*100;return {name,count,percent:count/total*100,color:palette[i%palette.length],start,end:offset}});
 const gradient=total?'conic-gradient('+segments.map(s=>s.color+' '+s.start+'% '+s.end+'%').join(', ')+')':'conic-gradient(#e2e8f0 0% 100%)';
 return <div className="flex flex-col sm:flex-row items-center gap-5"><div aria-label="Channel distribution donut" role="img" className="relative w-40 h-40 shrink-0 rounded-full" style={{background:gradient}}><div className="absolute inset-8 rounded-full bg-white flex flex-col items-center justify-center"><strong className="text-xl">{total}</strong><span className="text-xs text-slate-500">captured</span></div></div><ul className="text-xs flex-1 space-y-2 w-full">{segments.map(s=><li key={s.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded" style={{background:s.color}}/><span className="flex-1 break-words">{s.name}</span><strong>{s.count} ({s.percent.toFixed(1)}%)</strong></li>)}{!total&&<li>No channel evidence yet</li>}</ul></div>
}

function SentimentMarker({value,details}){
 const key=String(value||'Unclassified').toLowerCase();
 const config=key==='positive'?{Icon:Smile,cls:'text-green-700',label:'Positive'}:key==='neutral'?{Icon:Meh,cls:'text-amber-600',label:'Neutral'}:key==='negative'?{Icon:Frown,cls:'text-red-700',label:'Negative'}:{Icon:CircleHelp,cls:'text-slate-400',label:'Unclassified'};
 const Icon=config.Icon;
 return <span className={config.cls+' flex shrink-0 flex-col items-center gap-1'} title={'Sentiment: '+config.label+(details?.confidence?' · Confidence: '+details.confidence:'')+(details?.explanation?' · '+details.explanation:'')+(details?.model?' · Model: '+details.model:'')}><Icon size={24}/><span className="text-[10px]">{config.label}</span></span>;
}
function SourceThumbnail({url,platform}){
 const [failed,setFailed]=useState(false);
 return <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100 flex items-center justify-center">
  {url&&!failed?<img src={url} alt="" loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-cover" onError={()=>setFailed(true)}/>:<div className="flex flex-col items-center gap-1 text-slate-400" aria-label="Thumbnail unavailable"><ImageOff size={18}/><span className="text-[9px] capitalize">{platform||'Source'}</span></div>}
 </div>;
}
export default function CampaignPanel({campaignId=null}){
 const navigate=useNavigate();
 const [campaigns,setCampaigns]=useState([]);
 const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false);
 const [creating,setCreating]=useState(false),[editing,setEditing]=useState(null);
 const [form,setForm]=useState({...initial}),[selected,setSelected]=useState(null);
 const [query,setQuery]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [total,setTotal]=useState(0);
 const [sampleText,setSampleText]=useState(''),[keywordPreview,setKeywordPreview]=useState(null),[previewBusy,setPreviewBusy]=useState(false),[previewError,setPreviewError]=useState('');
 const keywordPreviewRequest=useRef(0);
 function resetKeywordPreview(){keywordPreviewRequest.current+=1;setSampleText('');setKeywordPreview(null);setPreviewError('');setPreviewBusy(false)}
 async function checkKeywordPreview(){if(!selected||!sampleText.trim())return;const request=++keywordPreviewRequest.current;setPreviewBusy(true);setPreviewError('');setKeywordPreview(null);try{const response=await base44.functions.invoke('socialListening',{action:'campaignKeywordPreview',id:selected.id,data:{text:sampleText}});if(request===keywordPreviewRequest.current)setKeywordPreview(response.data.screening)}catch(e){if(request===keywordPreviewRequest.current)setPreviewError(e.response?.data?.detail||e.response?.data?.error||e.message)}finally{if(request===keywordPreviewRequest.current)setPreviewBusy(false)}}
 const [statusFilter,setStatusFilter]=useState('all');
 const [trendMetric,setTrendMetric]=useState('posts');
 const [chartDay,setChartDay]=useState(null);
 const [evidence,setEvidence]=useState([]),[evidenceLoading,setEvidenceLoading]=useState(false),[evidenceError,setEvidenceError]=useState('');
 const [thumbnailRecoveryBusy,setThumbnailRecoveryBusy]=useState(false),[thumbnailRecoveryMessage,setThumbnailRecoveryMessage]=useState('');
 const [mediaPreviewBusy,setMediaPreviewBusy]=useState(false),[mediaPreview,setMediaPreview]=useState(null),[mediaPreviewError,setMediaPreviewError]=useState('');
 const [dashboard,setDashboard]=useState(null),[dashboardError,setDashboardError]=useState('');
 const [singlePreview,setSinglePreview]=useState(null),[singleBusy,setSingleBusy]=useState(false),[singleNotice,setSingleNotice]=useState('');
 const [postLookup,setPostLookup]=useState(''),[lookupBusy,setLookupBusy]=useState(false),[lookupError,setLookupError]=useState(''),[lookupPost,setLookupPost]=useState(null);
 async function findPostById(){
  if(!selected||lookupBusy)return;
  setLookupBusy(true);setLookupError('');setLookupPost(null);setSinglePreview(null);
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignEvidenceById',id:selected.id,data:{result_id:postLookup.trim()}});
   if(r.data.found)setLookupPost(r.data.post);else setLookupError('Post not found in this campaign or unavailable to your account.');
  }catch(e){setLookupError(e.response?.data?.detail||e.message||'Post lookup failed')}
  finally{setLookupBusy(false)}
 }

 const [externalFile,setExternalFile]=useState(null),[externalPreview,setExternalPreview]=useState(null),[externalBusy,setExternalBusy]=useState(false),[externalError,setExternalError]=useState('');
 async function previewExternalFile(){
  if(!selected||!externalFile||externalBusy)return;
  setExternalBusy(true);setExternalError('');setExternalPreview(null);
  try{const data=await base44.externalImport.preview(selected.id,externalFile);setExternalPreview(data)}
  catch(e){setExternalError(e.response?.data?.error||e.message||'Import preview failed')}
  finally{setExternalBusy(false)}
 }
 const [aiBusy,setAiBusy]=useState(false),[aiError,setAiError]=useState(''),[batchPreview,setBatchPreview]=useState(null),[batchNotice,setBatchNotice]=useState('');
 const [everywhereQuery,setEverywhereQuery]=useState('');
 const [manualPreview,setManualPreview]=useState(null),[manualBusy,setManualBusy]=useState(false),[manualDuplicate,setManualDuplicate]=useState(false),[manualNotice,setManualNotice]=useState('');
 const [analyticsFrom,setAnalyticsFrom]=useState(''),[analyticsTo,setAnalyticsTo]=useState(''),[analyticsBusy,setAnalyticsBusy]=useState(false);
 async function viewEvidence(c){
  resetKeywordPreview();setManualPreview(null);setManualDuplicate(false);setManualNotice('');setSelected(c);setExternalFile(null);setExternalPreview(null);setExternalError('');setPostLookup('');setLookupPost(null);setLookupError('');setEvidence([]);setChartDay(null);setDashboard(null);setDashboardError('');setAnalyticsFrom('');setAnalyticsTo('');setEvidenceError('');setEvidenceLoading(true);
  try{const [r,d]=await Promise.all([base44.functions.invoke('socialListening',{action:'campaignEvidence',id:c.id,data:{}}),base44.functions.invoke('socialListening',{action:'campaignDashboard',id:c.id,data:{}})]);setEvidence(r.data.evidence||[]);setDashboard(d.data)}
  catch(e){setEvidenceError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setEvidenceLoading(false)}
 }
 function exportEvidenceCsv(){
  if(!selected||!evidence.length)return;
  const fields=['id','platform','content_type','published_at','author_name','text_content','canonical_url','review_state','sentiment','engagement_total','views','likes','comments','shares'];
  const escape=v=>'"'+String(v??'').replace(/^[=+@-]/,'\t$&').replace(/"/g,'""')+'"';
  const content=[fields.join(','),...evidence.map(x=>fields.map(k=>escape(x[k])).join(','))].join('\r\n');
  const blob=new Blob(['\uFEFF'+content],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob);const link=document.createElement('a');
  link.href=url;link.download='bawaslu-campaign-'+selected.id+'-evidence.csv';link.click();
  URL.revokeObjectURL(url);
 }
 async function openChartDate(day){
  if(!selected||!day)return;
  setChartDay({date:day,loading:true,posts:[],error:'',truncated:false,total:0});
  try{
   const response=await base44.functions.invoke('socialListening',{action:'campaignDateTopPosts',id:selected.id,data:{date:day}});
   setChartDay({date:day,loading:false,posts:response.data.evidence||[],total:response.data.total||0,
                truncated:Boolean(response.data.truncated),error:''});
  }catch(e){setChartDay({date:day,loading:false,posts:[],error:e.response?.data?.detail||e.message||'Could not load posts',total:0,truncated:false})}
 }
 async function previewSingle(item,reanalysis=false){
  if(!selected||singleBusy)return;
  setSingleBusy(true);setSingleNotice('');setSinglePreview(null);
  try{const r=await base44.functions.invoke('socialListening',{action:reanalysis?'campaignSingleReanalysisPreview':'campaignSingleAssessmentPreview',id:selected.id,data:{result_id:item.id}});setSinglePreview(r.data)}
  catch(e){setSingleNotice(e.response?.data?.detail||e.message||'Preview unavailable')}
  finally{setSingleBusy(false)}
 }
 async function startSingle(){
  if(!selected||!singlePreview||singleBusy)return;
  if(!window.confirm('Confirm exactly one billable AI assessment for post #'+singlePreview.result_id+'? SocialCrawl credits: 0.'))return;
  setSingleBusy(true);setSingleNotice('');
  try{
   await base44.functions.invoke('socialListening',{action:singlePreview.reanalysis?'campaignSingleReanalysisStart':'campaignSingleAssessmentStart',id:selected.id,data:{result_id:singlePreview.result_id,confirm_ai_cost:true}});
   setSingleNotice('Single-post assessment accepted for post #'+singlePreview.result_id+'. Check Intelligence Inbox after processing.');
   setSinglePreview(null);
  }catch(e){setSingleNotice(e.response?.data?.detail||e.message||'Start failed')}
  finally{setSingleBusy(false)}
 }
 async function previewMediaCapability(){
  if(!selected||mediaPreviewBusy)return;
  setMediaPreviewBusy(true);setMediaPreview(null);setMediaPreviewError('');
  try{
   const response=await base44.functions.invoke('socialListening',{action:'campaignMediaCapabilityPreview',id:selected.id,data:{}});
   setMediaPreview(response.data);
  }catch(e){setMediaPreviewError(e.response?.data?.detail||e.message||'Preview unavailable')}
  finally{setMediaPreviewBusy(false)}
 }
 async function recoverThumbnails(){
  if(!selected||thumbnailRecoveryBusy)return;
  setThumbnailRecoveryBusy(true);setThumbnailRecoveryMessage('');
  try{
   const response=await base44.functions.invoke('socialListening',{action:'campaignThumbnailRecovery',id:selected.id,data:{}});
   const result=response.data;
   setThumbnailRecoveryMessage(result.recovered+' images saved; '+result.unavailable+' unavailable; '+result.already_saved+' already stored. Reasons: '+(Object.entries(result.failure_reasons||{}).map(([name,count])=>name.replaceAll('_',' ')+': '+count).join(', ')||'none')+'.'+(' Metadata: '+(result.source_metadata?.with_thumbnail_field||0)+' records with stored thumbnail field, '+(result.source_metadata?.without_thumbnail_field||0)+' without. Platforms: '+Object.entries(result.source_metadata?.platforms_checked||{}).map(([k,v])=>k+' '+v).join(', ')+'. Shapes: '+Object.entries(result.source_metadata?.payload_shapes||{}).map(([k,v])=>k+' ('+v+')').join(', ')+'. Post fields: '+(Object.keys(result.source_metadata?.post_fields||{}).join(', ')||'none')+'. Media fields: '+(Object.keys(result.source_metadata?.post_media_fields||{}).join(', ')||'none')+'.' )+(result.remaining?' Additional records not checked.':''));
   const latest=await base44.functions.invoke('socialListening',{action:'campaignEvidence',id:selected.id,data:{}});
   setEvidence(latest.data.evidence||[]);
  }catch(e){setThumbnailRecoveryMessage(e.response?.data?.detail||e.message||'Recovery unavailable')}
  finally{setThumbnailRecoveryBusy(false)}
 }
 async function previewManualCrawl(){
  if(!selected)return;setManualBusy(true);setManualPreview(null);setManualNotice('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignManualPreflight',id:selected.id,data:{everywhere_query:everywhereQuery}});setManualPreview(r.data);setManualDuplicate(false)}
  catch(e){setManualNotice(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setManualBusy(false)}
 }
 async function executeManualCrawl(){
  if(!selected||!manualPreview?.can_run)return;setManualBusy(true);setManualNotice('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignManualRun',id:selected.id,data:{confirm_cost:true,confirmed_credits:manualPreview.estimated_credits,acknowledge_duplicate:manualDuplicate,everywhere_query:manualPreview.query,confirmed_query:manualPreview.query}});
   setManualPreview(null);setManualNotice('Completed: '+r.data.result_count+' new results, '+r.data.linked_evidence+' linked campaign evidence. Actual credits: '+r.data.credits_used+'.');
   await refresh();await viewEvidence(selected);
  }catch(e){setManualNotice(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setManualBusy(false)}
 }
 async function checkBatch(){
  if(!selected)return;
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignSentimentBatchPreview',id:selected.id,data:{}});setBatchPreview(r.data);setAiError('')}
  catch(e){setAiError(e.response?.data?.detail||e.message)}
 }
 async function runBatch(){
  if(!selected||aiBusy||!batchPreview?.estimated_ai_calls)return;
  if(!window.confirm('Process '+batchPreview.estimated_ai_calls+' posts? OpenAI API charges may apply; exact monetary cost is unknown.'))return;
  setAiBusy(true);setAiError('');let completed=0;
  for(const result_id of batchPreview.selected_ids){
   try{const r=await base44.functions.invoke('socialListening',{action:'campaignSentimentClassify',id:selected.id,data:{result_id,confirm_ai_cost:true}});completed++;
      setEvidence(old=>old.map(x=>x.id===result_id?{...x,sentiment:r.data.sentiment,sentiment_details:{confidence:r.data.confidence,explanation:r.data.explanation,model:r.data.model}}:x))}
   catch(e){setAiError('Batch stopped: '+(e.response?.data?.detail||e.message));break}
  }
  setBatchNotice(completed+' post(s) classified.');setBatchPreview(null);setAiBusy(false);
 }
 async function classifyNextPost(){
  if(!selected||aiBusy)return;
  const item=evidence.find(x=>!x.sentiment||x.sentiment==='Unclassified');
  if(!item){setAiError('No unclassified post available in the loaded evidence.');return}
  if(!window.confirm('Analyze one post with AI? OpenAI API usage may incur a charge.'))return;
  setAiBusy(true);setAiError('');
  try{
   const res=await base44.functions.invoke('socialListening',{action:'campaignSentimentClassify',id:selected.id,data:{result_id:item.id,confirm_ai_cost:true}});
   setEvidence(old=>old.map(x=>x.id===item.id?{...x,sentiment:res.data.sentiment}:x));
  }catch(e){setAiError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setAiBusy(false)}
 }
 async function applyAnalyticsDates(){
  if(!selected)return;
  if(analyticsFrom&&analyticsTo&&analyticsFrom>analyticsTo){setDashboardError('Start date must not be after end date.');return}
  setAnalyticsBusy(true);setDashboardError('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,data:{date_from:analyticsFrom,date_to:analyticsTo}});setDashboard(r.data)}
  catch(e){setDashboardError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setAnalyticsBusy(false)}
 }
 const [creditEstimate,setCreditEstimate]=useState(null),[estimating,setEstimating]=useState(false),[estimateError,setEstimateError]=useState('');
 const previewRequestId=useRef(0);
 const clearEstimate=()=>{previewRequestId.current+=1;setCreditEstimate(null);setEstimateError('');setEstimating(false)};
 async function checkCredits(){
  const requestId=++previewRequestId.current;
  setEstimating(true);setEstimateError('');setCreditEstimate(null);
  try{
   const r=await base44.functions.invoke('socialListening',{action:'campaignCostPreview',data:{
     ...form,primary_keywords:form.primary_keywords,
     secondary_keywords:form.secondary_keywords,excluded_keywords:form.excluded_keywords
   }});
   if(requestId===previewRequestId.current)setCreditEstimate(r.data);
  }catch(e){if(requestId===previewRequestId.current)setEstimateError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{if(requestId===previewRequestId.current)setEstimating(false)}
 }

 const invalidCampaignDates=Boolean(form.date_from&&form.date_to&&form.date_from>form.date_to);
 const set=(key,value)=>{clearEstimate();setForm(x=>({...x,[key]:value}))};
 async function refresh(){
  try{
   const r=await base44.functions.invoke('socialListening',{action:'listCampaigns',data:{}});
   setCampaigns(r.data.campaigns||[]);setTotal(r.data.total||0);setError('');
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setLoading(false)}
 }
 useEffect(()=>{if(!campaignId){refresh();return}let active=true;setLoading(true);base44.functions.invoke('socialListening',{action:'getCampaign',id:campaignId,data:{}}).then(r=>{if(active)viewEvidence(r.data.campaign)}).catch(e=>{if(active)setError(e.response?.data?.detail||e.response?.data?.error||e.message)}).finally(()=>{if(active)setLoading(false)});return ()=>{active=false}},[campaignId]);
 function newCampaign(){resetKeywordPreview();clearEstimate();setForm({...initial,platforms:['tiktok']});setEditing(null);setCreating(true);setSelected(null);setError('');setNotice('')}
 function editCampaign(c){
  resetKeywordPreview();clearEstimate();setForm({name:c.name,description:c.description||'',
   primary_keywords:[...(c.primary_keywords||[])],
   secondary_keywords:[...(c.secondary_keywords||[])],
   excluded_keywords:[...(c.excluded_keywords||[])],
   platforms:[...(c.platforms||[])],language:c.language||'',date_from:c.date_from||'',date_to:c.date_to||'',
   interval_minutes:120,province:c.province||'',regency_city:c.regency_city||''});
  setEditing(c);setCreating(true);setSelected(null);setError('');setNotice('');
 }
 async function save(e){
  e.preventDefault();if(invalidCampaignDates){setError('Start date cannot be after end date. Please correct the campaign dates.');return}setSaving(true);setError('');setNotice('');
  const data={...form,primary_keywords:form.primary_keywords,
   secondary_keywords:form.secondary_keywords,excluded_keywords:form.excluded_keywords};
  try{
   const action=editing?'updateCampaign':'createCampaign';
   const r=await base44.functions.invoke('socialListening',{action,id:editing?.id,data});
   setNotice('Campaign saved as draft. Automatic paid crawls remain disabled until scheduling is approved.');
   setSelected(null);setCreating(false);setEditing(null);await refresh();
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setSaving(false)}
 }
 async function pause(c){
  if(c.status==='PAUSED')return;
  setSaving(true);setError('');
  try{
   await base44.functions.invoke('socialListening',{action:'updateCampaign',id:c.id,data:{status:'PAUSED'}});
   await refresh();setNotice('Campaign paused');
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setSaving(false)}
 }
 const visible=campaigns.filter(x=>(statusFilter==='all'||x.status===statusFilter)&&(x.name+' '+x.description+' '+x.primary_keywords.join(' ')).toLowerCase().includes(query.toLowerCase()));
 return <section className="space-y-5" aria-label="Monitoring campaigns">
  {!campaignId&&<div className="intel-card p-5 space-y-3">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div><h2 className="text-lg font-semibold">Monitoring Campaigns</h2>
      <p className="text-sm text-[#77899b]">Organize ongoing listening by topic, candidate and keyword.</p></div>
    <button type="button" className="intel-button" onClick={newCampaign}>+ New Campaign</button>
   </div>
   <p className="text-xs text-[#8b6e39]">Campaigns are drafts for now. Automatic crawling will activate after credit limits and scheduling QA are completed.</p>
   <div className="flex flex-wrap gap-4 text-sm">
    <span><strong>{total}</strong> campaigns</span><span><strong>{campaigns.filter(x=>x.status==='PAUSED').length}</strong> paused</span>
   </div>
   <div className="flex flex-wrap gap-2"><input className="intel-input flex-1" value={query} aria-label="Search campaigns" placeholder="Search campaigns" onChange={e=>setQuery(e.target.value)}/><select className="intel-input" aria-label="Campaign status filter" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="all">All statuses</option><option value="DRAFT">Draft</option><option value="PAUSED">Paused</option></select></div>
  </div>}
  {error&&<p role="alert" className="intel-card p-3 text-red-700">{error}</p>}
  {notice&&<p role="status" className="intel-card p-3 text-green-700">{notice}</p>}
  {creating&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 sm:p-6" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setCreating(false)}}>
   <div role="dialog" aria-modal="true" aria-labelledby="campaign-modal-title" className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl">
    <form className="p-5 sm:p-7 space-y-4" onSubmit={save} aria-label="Campaign editor">
   <div className="flex items-center justify-between gap-4">
    <h3 id="campaign-modal-title" className="text-lg font-semibold">{editing?'Edit Campaign':'Create Campaign'}</h3>
    <button type="button" aria-label="Close campaign popup" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>✕</button>
   </div>
   <div className="grid gap-3 md:grid-cols-2">
    <label className="text-sm">Campaign name *<input className="intel-input mt-1" value={form.name} maxLength={255} required onChange={e=>set('name',e.target.value)}/></label>
    <label className="text-sm">Language<select className="intel-input mt-1" value={form.language} onChange={e=>set('language',e.target.value)}>
       <option value="">All languages</option><option value="id">Bahasa Indonesia</option><option value="en">English</option><option value="ms">Bahasa Melayu</option>
    </select></label>
    <KeywordTags label="Main keywords" required items={form.primary_keywords} onChange={tags=>set('primary_keywords',tags)} />
    <KeywordTags label="Secondary keywords" items={form.secondary_keywords} onChange={tags=>set('secondary_keywords',tags)} />
    <KeywordTags label="Excluded keywords" items={form.excluded_keywords} onChange={tags=>set('excluded_keywords',tags)}/>
    <label className="text-sm">Start date<input className="intel-input mt-1" type="date" value={form.date_from} onChange={e=>set('date_from',e.target.value)}/></label>
    <label className="text-sm">End date<input className="intel-input mt-1" type="date" aria-invalid={invalidCampaignDates} value={form.date_to} onChange={e=>set('date_to',e.target.value)}/></label>
    {invalidCampaignDates&&<p role="alert" className="md:col-span-2 text-sm text-red-700">Start date cannot be after end date. Please correct the campaign dates.</p>}
    <label className="text-sm">Province (optional; regional access still applies)<input className="intel-input mt-1" value={form.province} onChange={e=>set('province',e.target.value)}/></label>
    <label className="text-sm">Regency / City<input className="intel-input mt-1" value={form.regency_city} onChange={e=>set('regency_city',e.target.value)}/></label>
   </div>
   <label className="block text-sm">Description<textarea rows={2} className="intel-input mt-1 w-full" value={form.description} onChange={e=>set('description',e.target.value)}/></label>
   <fieldset className="space-y-2"><legend className="text-sm font-semibold">Platforms *</legend>
    <label className="flex gap-2 items-center rounded-lg border p-3 text-sm font-medium"><input type="checkbox" aria-label="All platforms - Search Everywhere" checked={form.platforms.includes("search_everywhere")} onChange={e=>set("platforms",e.target.checked?["search_everywhere"]:["tiktok"])}/> All platforms · Search Everywhere <span className="text-xs font-normal text-slate-600">20 credits per query · preview only for now</span></label>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{options.map(p=><label key={p} className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={form.platforms.includes("search_everywhere")} checked={form.platforms.includes(p)} onChange={e=>set('platforms',e.target.checked?[...form.platforms,p]:form.platforms.filter(x=>x!==p))}/>{p}</label>)}</div>
   </fieldset>
   <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 space-y-2" aria-label="Campaign credit preflight">
    <p className="text-sm font-semibold text-amber-950">SocialCrawl credit estimate — before running</p>
    <p className="text-xs text-amber-900">A cost preview does not call SocialCrawl or use credits. Always review the latest estimate before authorizing a paid run.</p>
    <button type="button" className="intel-ghost" disabled={estimating||saving||!form.name.trim()||!form.primary_keywords.length||!form.platforms.length} onClick={checkCredits}>{estimating?'Calculating…':'Check estimated credits'}</button>
    {estimateError&&<p role="alert" className="text-xs text-red-700">{estimateError}</p>}
    {creditEstimate&&<div role="status" className="text-sm text-amber-950">
      Estimated cost: <strong>{creditEstimate.estimated_credits} credits per run</strong>
      {Array.isArray(creditEstimate.components)&&creditEstimate.components.length>0&&<ul className="mt-2 space-y-1 text-xs" aria-label="Estimated credits by source">{creditEstimate.components.map((part,index)=><li key={part.endpoint||index} className="flex justify-between gap-3"><span>{part.label||part.endpoint}</span><strong>{part.credits} credits</strong></li>)}</ul>}
      <p className="text-xs">{creditEstimate.billing_warning||"Estimate, not a guaranteed final charge. Actual provider usage may differ."}</p>
      <p className="text-xs">Scheduled paid crawling is disabled. This preview is not approval to run.</p>
    </div>}
   </div>
   <div className="flex gap-2"><button className="intel-button" disabled={saving||invalidCampaignDates||!form.primary_keywords.length}>{saving?'Saving…':'Save Draft'}</button>
    <button type="button" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>Cancel</button></div>
    </form>
   </div>
  </div>}
  {!campaignId&&(loading?<p className="intel-card p-4">Loading campaigns…</p>:<div className="intel-card overflow-x-auto"><table className="w-full text-left text-sm" aria-label="Campaign list"><thead className="bg-slate-50 text-xs uppercase text-slate-600"><tr><th className="p-3">Campaign</th><th className="p-3">Dates</th><th className="p-3">Status</th><th className="p-3">Evidence</th><th className="p-3">Actions</th></tr></thead><tbody>{visible.map(c=><tr key={c.id} className="border-t border-slate-100"><td className="p-3"><strong>{c.name}</strong><div className="text-xs text-slate-500">{(c.primary_keywords||[]).join(' · ')}</div></td><td className="p-3 text-xs">{c.date_from||'Any'} — {c.date_to||'Any'}</td><td className="p-3">{displayStatus(c.status)}</td><td className="p-3">{c.evidence_count}</td><td className="p-3"><div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost" onClick={()=>navigate(`/social-listening/campaigns/${c.id}`)}>Open Dashboard</button><button type="button" className="intel-ghost" onClick={()=>editCampaign(c)}>Edit</button>{c.status==='DRAFT'&&<button type="button" className="intel-ghost" disabled={saving} onClick={()=>pause(c)}>Pause</button>}</div></td></tr>)}</tbody></table>{!visible.length&&<p className="p-4 text-sm">No campaigns match your filters.</p>}</div>)}
  {campaignId&&selected&&!creating&&<div className="intel-card p-5 space-y-2">
   <button type="button" className="intel-ghost" onClick={()=>navigate("/social-listening?tab=campaigns")}>← Back to campaigns</button>
   <h3 className="font-semibold text-xl">{selected.name} — Campaign Overview</h3>
   <p className="text-sm">Main keywords: {selected.primary_keywords.join(', ')}</p>
   <p className="text-sm">Secondary: {selected.secondary_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Excluded: {selected.excluded_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Collection runs: {selected.run_count} · Evidence records: {selected.evidence_count}</p>
   {dashboardError&&<p role="alert" className="text-sm text-red-700">{dashboardError}</p>}
   {dashboard&&<section aria-label="Campaign monitoring dashboard" className="rounded-lg border border-slate-200 p-4 space-y-3">
    <h4 className="font-semibold">Monitoring dashboard</h4>
    <div className="flex flex-wrap gap-3 items-end" aria-label="Campaign analytics date filters"><label className="text-xs">From date<input type="date" className="intel-input mt-1" value={analyticsFrom} onChange={e=>setAnalyticsFrom(e.target.value)}/></label><label className="text-xs">To date<input type="date" className="intel-input mt-1" value={analyticsTo} onChange={e=>setAnalyticsTo(e.target.value)}/></label><button type="button" className="intel-ghost" disabled={analyticsBusy} onClick={applyAnalyticsDates}>{analyticsBusy?'Filtering…':'Apply date filter'}</button></div>
    <p className="text-xs text-slate-500">Date filtering uses source publication dates. Records without dates are omitted when a date filter is applied.</p>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <section className="rounded-lg border p-4 space-y-2" aria-label="Social Listening statistics"><h5 className="font-semibold text-teal-700">Statistics</h5><div className="grid grid-cols-2 md:grid-cols-4 gap-3">{[['Messages',dashboard.statistics?.messages],['Engagements',dashboard.statistics?.engagement],['Accounts',dashboard.statistics?.accounts],['Main keyword messages',dashboard.statistics?.main_keyword_messages],['Sub keyword messages',dashboard.statistics?.secondary_keyword_messages],['Sub keyword not found',dashboard.statistics?.secondary_not_found_messages],['Views',dashboard.statistics?.views]].map(([label,value])=><div key={label} className="rounded-lg border p-3"><strong className="text-xl">{Number(value||0).toLocaleString()}</strong><p className="text-xs text-slate-500">{label}</p></div>)}</div><p className="text-xs text-slate-500">Based on stored evidence. Views and engagements may be incomplete when platforms do not supply them.</p></section>
<section className="rounded-lg border p-4 space-y-2" aria-label="Channel distribution"><h5 className="font-semibold">Channel distribution</h5><ChannelDonut values={dashboard.platforms}/></section>
      <section className="min-w-0 rounded-lg border p-4 space-y-3 lg:col-span-2" aria-label="Campaign trend by platform">
<h5 className="font-semibold">Social Listening by platform</h5>
<div className="flex gap-2" role="group" aria-label="Trend metric">{['posts','engagement','views'].map(k=><button key={k} type="button" aria-pressed={trendMetric===k} className={trendMetric===k?'intel-button':'intel-ghost'} onClick={()=>setTrendMetric(k)}>{k==='posts'?'Posts':k==='engagement'?'Engagement':'Views'}</button>)}</div>
{dashboard.daily_platform_trend?.length?<div className="h-80 w-full min-w-0 lg:h-96" role="img" aria-label={trendMetric+' trend by platform'}><ResponsiveContainer width="100%" height="100%"><LineChart data={dashboard.daily_platform_trend} onClick={point=>{if(point?.activeLabel)openChartDate(String(point.activeLabel))}} margin={{top:12,right:14,left:-18,bottom:12}}>
<CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0"/><XAxis dataKey="date" tick={{fontSize:10}} minTickGap={26}/><YAxis allowDecimals={false} tick={{fontSize:11}}/><Tooltip/><Legend verticalAlign="bottom"/>
{Object.keys(dashboard.platforms||{}).map((platform,index)=><Line key={platform} type="monotone" dataKey={platform+'__'+trendMetric} name={platform} stroke={['#285f82','#bc9b62','#339b92','#815ca7','#d2735c','#6d84a1','#69865f','#b95b83'][index%8]} dot={false} connectNulls/>)}
</LineChart></ResponsiveContainer></div>:<p className="text-xs text-slate-500">No dated posts in this period</p>}
<p className="text-xs text-slate-500">Click a date on the chart to see its hottest posts. Only stored provider metrics are counted; missing data is not estimated.</p>
</section>
{chartDay&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-3" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setChartDay(null)}}>
 <div className="w-full max-w-xl max-h-[85vh] overflow-hidden rounded-xl bg-white shadow-xl flex flex-col" role="dialog" aria-modal="true" aria-label={'Top posts for '+chartDay.date}>
  <div className="flex items-center justify-between gap-3 border-b p-4">
   <div><h5 className="font-semibold">Top posts · {chartDay.date}</h5><p className="text-xs text-slate-500">{chartDay.total} stored posts on this date</p></div>
   <button type="button" className="intel-ghost text-sm" aria-label="Close date posts" onClick={()=>setChartDay(null)}>Close ×</button>
  </div>
  <p className="px-4 py-2 border-b text-xs text-slate-500">Ranked automatically using engagement and views.</p>
  <div className="overflow-y-auto p-4 space-y-3">
   {chartDay.loading?<p className="text-sm">Loading saved posts…</p>:chartDay.error?<p role="alert" className="text-sm text-red-700">{chartDay.error}</p>:chartDay.posts.length?chartDay.posts.map((post,index)=><div key={post.id} className="rounded-lg border p-3 space-y-2 text-sm">
    <div className="flex justify-between gap-3"><strong className="capitalize">{index+1}. {post.platform} · {post.author_name||'Author unknown'}</strong><span className="text-xs text-slate-500">Post #{post.id}</span></div>
    <p className="whitespace-pre-wrap break-words text-slate-700">{post.text_content||'No post text available'}</p>
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
     <span>Engagements: {post.engagement_total==null?'Unavailable':Number(post.engagement_total).toLocaleString()}</span>
     <span>Views: {post.views==null?'Unavailable':Number(post.views).toLocaleString()}</span>
     {post.likes!=null&&<span>Likes: {Number(post.likes).toLocaleString()}</span>}
     {post.comments!=null&&<span>Comments: {Number(post.comments).toLocaleString()}</span>}
     {post.shares!=null&&<span>Shares: {Number(post.shares).toLocaleString()}</span>}
    </div>
    {/^https:\/\//i.test(post.canonical_url||'')&&<a className="inline-flex items-center gap-1 text-xs text-[#285f82] underline" href={post.canonical_url} target="_blank" rel="noopener noreferrer">Open original source <ExternalLink size={12}/></a>}
   </div>):<p className="text-sm text-slate-500">No saved posts found for this date.</p>}
   {chartDay.truncated&&<p className="text-xs text-amber-700">Results are limited to the latest 5,000 campaign records.</p>}
  </div>
 </div>
</div>}

      <section className="rounded-lg border p-4 space-y-3" aria-label="Captured posts">
 <div className="flex items-center justify-between gap-2"><h5 className="font-semibold">Captured posts & sources</h5><button type="button" onClick={classifyNextPost} disabled={aiBusy||!evidence.some(x=>x.sentiment==="Unclassified")} className="intel-ghost text-xs">{aiBusy?"Analyzing…":"AI classify 1 post"}</button></div><button type="button" className="intel-ghost text-xs" disabled={mediaPreviewBusy} onClick={previewMediaCapability}>{mediaPreviewBusy?'Checking media options…':'Check Instagram media options (free)'}</button>
 {mediaPreviewError&&<p className="text-xs text-red-600" role="alert">{mediaPreviewError}</p>}
 {mediaPreview&&<div className="rounded-md border bg-slate-50 p-3 text-xs space-y-1" aria-label="Instagram media capability preview">
  <p className="font-semibold">Instagram media enrichment · preview only</p>
  <p>{mediaPreview.counts?.instagram_missing||0} posts missing thumbnails; {mediaPreview.counts?.instagram_with_url||0} posts with a stored image URL; {mediaPreview.counts?.already_cached||0} cached images.</p>
  <p>{mediaPreview.counts?.post_url_available||0} eligible Instagram post URLs. Estimated post-detail requests: {mediaPreview.potential_calls||0}; estimated maximum at 1 credit each: {mediaPreview.potential_credit_estimate||0} credits.</p>
  <p className="text-amber-800">Image-field availability has not been validated. Paid enrichment is disabled. No SocialCrawl credits are used by this preview.</p>
 </div>}
 <button type="button" className="intel-ghost text-xs" disabled={thumbnailRecoveryBusy} onClick={recoverThumbnails}>{thumbnailRecoveryBusy?'Checking images…':'Recover stored thumbnails (free)'}</button>
 {thumbnailRecoveryMessage&&<p className="text-xs text-slate-600" role="status">{thumbnailRecoveryMessage}</p>}
 <button type="button" className="intel-ghost text-xs" disabled={aiBusy} onClick={checkBatch}>Preview batch AI</button>
 {batchPreview&&<div className="rounded-md bg-slate-50 p-3 text-xs space-y-2"><p>{batchPreview.estimated_ai_calls} possible billable AI calls (max 3). Token costs vary and are not quoted in advance.</p><button type="button" disabled={aiBusy||!batchPreview.estimated_ai_calls} className="intel-button" onClick={runBatch}>Confirm AI batch</button></div>}
 {batchNotice&&<p role="status" className="text-xs">{batchNotice}</p>}
 {aiError&&<p role="alert" className="text-xs text-red-700">{aiError}</p>}
 <button type="button" className="intel-ghost text-xs" disabled={!evidence.length} onClick={exportEvidenceCsv}>Export top posts to CSV (up to 200)</button>
 <div className="rounded-lg border border-slate-200 p-3 space-y-2" aria-label="Find campaign post by ID">
  <label htmlFor="campaign-post-lookup" className="block text-xs font-semibold">Find any campaign post by Post ID</label>
  <form onSubmit={e=>{e.preventDefault();findPostById()}} className="flex gap-2">
   <input id="campaign-post-lookup" className="intel-input min-w-0 flex-1" inputMode="numeric" pattern="[0-9]+" placeholder="e.g. 649" value={postLookup} onChange={e=>setPostLookup(e.target.value)}/>
   <button type="submit" className="intel-button text-xs" disabled={lookupBusy||!/^\d+$/.test(postLookup.trim())}>{lookupBusy?'Finding…':'Find post'}</button>
  </form>
  {lookupError&&<p role="alert" className="text-xs text-amber-700">{lookupError}</p>}
  {lookupPost&&<div className="rounded-lg bg-slate-50 border p-3 text-xs space-y-2">
   <div className="flex flex-wrap items-center gap-2"><strong>Post #{lookupPost.id} · {lookupPost.platform}</strong><span className="text-slate-600">{lookupPost.assessment_status==='ASSESSED'?'Previously assessed':'Unassessed'}</span></div>
   <p className="whitespace-pre-wrap break-words max-h-44 overflow-y-auto">{lookupPost.text_content||'No source text available'}</p>
   {/^https:\/\//i.test(lookupPost.canonical_url||'')&&<a href={lookupPost.canonical_url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">Open original source ↗</a>}
   <div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost text-xs" disabled={singleBusy||lookupPost.assessment_status==='ASSESSED'} onClick={()=>previewSingle(lookupPost,false)}>Analyze with AI</button><button type="button" className="intel-ghost text-xs" disabled={singleBusy||lookupPost.assessment_status!=='ASSESSED'} onClick={()=>previewSingle(lookupPost,true)}>Reanalyze with AI</button></div>
  </div>}
 </div>
 <details className="rounded-lg border border-slate-200 p-3 text-xs space-y-3" aria-label="External provider import preview">
  <summary className="font-semibold cursor-pointer">Admin · External provider Excel/CSV import (preview only)</summary>
  <p className="mt-2 text-slate-600">Upload an export from ZocialEye for this campaign. Preview only: no crawl, AI processing, or database import occurs.</p>
  <input type="file" aria-label="ZocialEye Excel or CSV file" accept=".xlsx,.csv" onChange={e=>{setExternalFile(e.target.files?.[0]||null);setExternalPreview(null);setExternalError('')}}/>
  <button type="button" className="intel-ghost text-xs" disabled={!externalFile||externalBusy} onClick={previewExternalFile}>{externalBusy?'Inspecting workbook…':'Preview columns and counts'}</button>
  {externalError&&<p role="alert" className="text-red-700">{externalError}</p>}
  {externalPreview&&<div className="border rounded-lg bg-slate-50 p-3 space-y-2">
    <strong>Preview only · {externalPreview.records_inserted} records imported · {externalPreview.socialcrawl_credits} SocialCrawl credits</strong>
    <p>Recommended sheet: {externalPreview.recommended_sheet||'N/A'} · Available source rows: {externalPreview.estimated_rows_in_recommended_sheet?.toLocaleString()||0}</p>
    <p className="text-amber-800">{externalPreview.warning}</p>
    <div className="max-h-52 overflow-y-auto space-y-1">{(externalPreview.sheets||[]).map(sheet=><p key={sheet.name}>{sheet.name}: {sheet.data_rows.toLocaleString()} rows · {sheet.columns.length} columns</p>)}</div>
    <p>Mapped fields: {Object.entries(externalPreview.mapped_fields||{}).map(([target,source])=>target+' ← '+source).join(' · ')||'None identified'}</p>
    <p>Sample source rows checked: {externalPreview.sampled_rows||0} · Missing URL: {externalPreview.sample_missing_url||0} · Missing content: {externalPreview.sample_missing_text||0}</p>
    <p className="text-slate-600">Commit/import is intentionally unavailable in this build pending mapping and duplicate QA.</p>
  </div>}
 </details>
 <p className="text-xs text-slate-500">Hottest posts first · automatically combines engagements and views.</p>
 {evidenceError&&<p role="alert" className="text-xs text-red-700">{evidenceError}</p>}
 {evidenceLoading?<p className="text-xs">Loading evidence…</p>:evidence.length?<div className="max-h-96 overflow-y-auto space-y-2">
 {evidence.filter(item=>{const day=String(item.published_at||'').slice(0,10);return !(analyticsFrom||analyticsTo)||(day&&(!analyticsFrom||day>=analyticsFrom)&&(!analyticsTo||day<=analyticsTo))}).slice(0,40).map(item=>{
 const valid=/^https:\/\//i.test(item.canonical_url||'');
 return <div key={item.id} className="space-y-1"><a href={valid?item.canonical_url:undefined} target={valid?'_blank':undefined} rel="noopener noreferrer" aria-label={valid?'Open original '+item.platform+' post':'Source URL unavailable'} className={'flex items-center gap-2 rounded-xl border border-slate-200 p-2.5 text-xs transition-colors '+(valid?'hover:border-blue-300 hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500':'cursor-default')}>
  <SourceThumbnail url={item.thumbnail_url} platform={item.platform}/>
  <div className="min-w-0 flex-1 space-y-1"><div className="flex items-center gap-2"><strong className="capitalize">{item.platform} · {item.content_type||'Post'}</strong><span className="text-slate-500">{item.published_at?String(item.published_at).slice(0,10):'Undated'}</span></div><p className="line-clamp-3 text-slate-700 whitespace-pre-wrap break-words">{item.text_content||'No source text'}</p></div>
  <SentimentMarker value={item.sentiment} details={item.sentiment_details}/>
 </a><button type="button" className="intel-ghost text-xs" disabled={singleBusy} onClick={()=>previewSingle(item,false)}>Analyze with AI · Post #{item.id}</button><button type="button" className="intel-ghost text-xs" disabled={singleBusy} onClick={()=>previewSingle(item,true)}>Reanalyze with AI · Post #{item.id}</button></div>})}</div>:<p className="text-xs text-slate-500">No captured evidence yet</p>}
 {singlePreview&&<div className="rounded-lg border border-amber-300 p-3 space-y-2 text-xs" role="status"><strong>Post #{singlePreview.result_id} · {singlePreview.reanalysis?'Versioned AI reanalysis':'AI analysis'} cost preview</strong><p>Exactly {singlePreview.estimated_ai_requests} AI request · SocialCrawl credits: {singlePreview.socialcrawl_credits} · {singlePreview.estimated_ai_cost}.</p><button type="button" className="intel-button" disabled={singleBusy||!singlePreview.ai_key_configured} onClick={startSingle}>Confirm paid AI analysis for this post</button><button type="button" className="intel-ghost ml-2" onClick={()=>setSinglePreview(null)}>Cancel</button>{!singlePreview.ai_key_configured&&<p>AI provider key not configured.</p>}</div>}
 {singleNotice&&<p role="status" className="text-xs">{singleNotice}</p>}
 <p className="text-xs text-slate-500">Top 40 displayed from the 200 hottest stored posts (up to 5,000 scanned). Engagement and views are combined automatically; missing metrics are not estimated.</p>
 </section>
 <section className="rounded-lg border p-4 space-y-3" aria-label="Campaign demographics">
 <h5 className="font-semibold">Demographics & data coverage</h5>
 <p className="text-xs text-slate-600">Availability of supported metadata in selected campaign evidence, not a demographic profile of viewers or voters.</p>
 <div className="grid grid-cols-2 gap-2 text-sm">
 {[['Country metadata','country_available'],['Language metadata','language_available']].map(([label,key])=><div key={key} className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><strong>{dashboard.demographics_coverage?.[key]||0} / {dashboard.demographics_coverage?.records||0}</strong><p className="text-xs text-slate-500">records</p></div>)}
 </div>
 {Object.keys(dashboard.geographies||{}).length>0&&<div className="space-y-1 text-xs"><p className="font-semibold">Recorded country signals</p>{Object.entries(dashboard.geographies).map(([key,count])=><p key={key}>{key}: {count}</p>)}</div>}
 {Object.keys(dashboard.source_languages||{}).length>0&&<div className="space-y-1 text-xs"><p className="font-semibold">Recorded content languages</p>{Object.entries(dashboard.source_languages).map(([key,count])=><p key={key}>{key}: {count}</p>)}</div>}
 <p className="text-xs text-slate-500">Age and gender: unavailable. Not inferred from names, photos, profiles, or post text.</p>
 </section>
    </div>
<section className="rounded-lg border p-4 space-y-3" aria-label="Campaign word cloud">
 <div className="flex items-center justify-between gap-3"><h5 className="font-semibold">Word cloud</h5><span className="text-xs text-slate-500" title="Larger words occur more often in captured evidence. Common Indonesian, Malay and English filler words are removed.">Term frequency · stored posts</span></div>
 {dashboard.word_cloud?.length?<div className="min-h-64 flex flex-wrap items-center content-center justify-center gap-x-4 gap-y-3 px-3 py-5" aria-label="Word cloud terms">{dashboard.word_cloud.map((term,index)=>{const max=Math.max(...dashboard.word_cloud.map(x=>x.count),1);const ratio=term.count/max;return <span key={term.word} title={term.word+': '+term.count+' occurrences'} className="font-medium leading-tight" style={{fontSize:(12+ratio*27)+'px',color:term.secondary?'#b7791f':['#0c5963','#237e86','#326b88','#426c78'][index%4],fontWeight:term.secondary?700:500}}>{term.word}</span>})}</div>:<p className="min-h-56 flex items-center justify-center text-sm text-slate-500">No configured campaign keywords appear in the selected evidence.</p>}
 <p className="text-xs text-slate-500">Only configured main and secondary keywords are shown. Sizes reflect recorded mentions in the selected date range. Gold indicates secondary keywords. No additional SocialCrawl or AI calls.</p>
 </section>
    <div className="grid grid-cols-2 gap-3 text-sm"><div className="rounded-md bg-slate-50 p-3">Evidence records <strong className="block text-xl">{dashboard.evidence_count}</strong></div><div className="rounded-md bg-slate-50 p-3">Collection runs <strong className="block text-xl">{dashboard.run_count}</strong></div></div>
    {dashboard.truncated&&<p className="text-xs text-amber-800">Statistics cover only the latest 5,000 campaign evidence links.</p>}
    {[
     ['Evidence by platform',dashboard.platforms],
     ['Review status',dashboard.review_states],
     ['Main keyword matches',dashboard.main_keywords],
     ['Secondary keyword matches',dashboard.secondary_keywords]
    ].map(([label,values])=><div key={label}><h5 className="text-sm font-semibold">{label}</h5>{Object.entries(values||{}).length?<div className="space-y-1 mt-2">{Object.entries(values).sort((x,y)=>y[1]-x[1]).map(([name,count])=><div key={name} className="flex gap-3 items-center text-xs"><span className="w-32 break-words">{name}</span><div className="h-2 flex-1 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-[#285f82]" style={{width:(100*count/Math.max(1,...Object.values(values)))+'%'}} /></div><strong>{count}</strong></div>)}</div>:<p className="text-xs text-slate-500 mt-1">No evidence yet</p>}</div>)}
    <p className="text-xs text-slate-500">Based on stored, access-scoped evidence. Keyword matches are not verified election violations. No SocialCrawl credits used.</p>
   </section>}
   <section className="rounded-lg border border-slate-200 p-4 space-y-3" aria-label="Manual campaign crawl">
    <h4 className="font-semibold">Manual SocialCrawl collection</h4>
    <p className="text-xs text-slate-600">Manual runs only. Native search limit: 5 estimated credits per run. Search Everywhere: 20 credits per confirmed query. Scheduled crawling remains disabled.</p>
    {selected.platforms?.includes('search_everywhere')&&<label className="block text-sm">Search Everywhere query (one request, 20 credits)<input className="intel-input mt-1 w-full" value={everywhereQuery} maxLength={512} placeholder={selected.primary_keywords?.length===1?selected.primary_keywords[0]:'Enter the exact topic query for all keywords'} onChange={e=>{setEverywhereQuery(e.target.value);setManualPreview(null)}}/><span className="text-xs text-slate-500">A single query does not guarantee every keyword is covered. Review this text before authorizing payment.</span></label>}
    <button type="button" className="intel-ghost" disabled={manualBusy||selected.status!=='DRAFT'} onClick={previewManualCrawl}>Check manual crawl cost (free)</button>
    {manualPreview&&<div className="space-y-2 text-sm" role="status"><p>Estimated cost: <strong>{manualPreview.estimated_credits} credits</strong> (limit {manualPreview.credit_limit})</p><p className="text-xs text-slate-600">{manualPreview.retrieval_mode==='SEARCH_EVERYWHERE_PREVIEW'?'One Search Everywhere request for: '+manualPreview.query+'. Multi-keyword coverage is not guaranteed.':`Each main keyword is searched separately (OR retrieval); overlapping posts are deduplicated. ${manualPreview.keyword_searches?.length||0} searches planned.`}</p>
      {(manualPreview.components||[]).map((x,i)=><p key={i} className="text-xs">{x.label}: {x.credits} credits</p>)}
      {manualPreview.duplicate_recent&&<label className="flex gap-2 items-center text-xs"><input type="checkbox" checked={manualDuplicate} onChange={e=>setManualDuplicate(e.target.checked)}/> I understand this repeats a recent search</label>}
      <button type="button" className="intel-button" disabled={manualBusy||!manualPreview.can_run||(manualPreview.duplicate_recent&&!manualDuplicate)} onClick={executeManualCrawl}>Confirm and run paid crawl ({manualPreview.estimated_credits} estimated credits)</button>
      {!manualPreview.can_run&&<p role="alert" className="text-red-700">{manualPreview.blocked_reason||"Credit limit exceeded; reduce selected platforms."}</p>}
    </div>}
    {manualNotice&&<p role="status" className="text-sm">{manualNotice}</p>}
   </section>
   <CampaignScheduleSummary campaign={selected} />
   <div className="rounded-lg border border-slate-200 p-4 space-y-3" aria-label="Campaign keyword screening preview">
    <h4 className="font-semibold">Test keyword matching (no credits)</h4>
    <p className="text-xs text-slate-600">Paste sample source text. At least one main keyword must appear, and excluded keywords block the match. Secondary keywords add context but are not required. This local preview does not call SocialCrawl.</p>
    <label className="block text-sm">Sample social post<textarea className="intel-input mt-1 w-full" rows={3} maxLength={5000} value={sampleText} onChange={e=>{keywordPreviewRequest.current+=1;setSampleText(e.target.value);setKeywordPreview(null);setPreviewBusy(false);setPreviewError('')}} /></label>
    <button type="button" className="intel-ghost" disabled={previewBusy||!sampleText.trim()} onClick={checkKeywordPreview}>{previewBusy?'Checking…':'Preview keyword match'}</button>
    {previewError&&<p role="alert" className="text-red-700 text-sm">{previewError}</p>}
    {keywordPreview&&<div role="status" className="rounded-md bg-slate-50 p-3 text-sm space-y-1"><p className="font-semibold">{keywordPreview.matched?'Matches campaign keywords':'Does not match campaign keywords'}</p><p>Main matches: {(keywordPreview.main_keywords||[]).join(', ')||'None'}</p><p>Secondary context: {(keywordPreview.secondary_keywords||[]).join(', ')||'None'}</p><p>Excluded matches: {(keywordPreview.excluded_keywords||[]).join(', ')||'None'}</p><p className="text-xs text-slate-600">Preliminary literal keyword match only — not evidence of an election violation.</p></div>}
   </div>
   {evidenceError&&<p role="alert" className="text-red-700 text-sm">{evidenceError}</p>}
  </div>}
 </section>
}
