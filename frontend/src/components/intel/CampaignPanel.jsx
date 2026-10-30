import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, ImageOff, Smile, Meh, Frown, CircleHelp } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { base44 } from '@/api/base44Client';
import KeywordTags from '@/components/intel/KeywordTags';
import ProvinceHeatmap from '@/components/intel/ProvinceHeatmap';
import AssessmentPilotPreview from '@/components/intel/AssessmentPilotPreview';
import CapturedPostList from '@/components/intel/CapturedPostList';
import TopicThemes from '@/components/intel/TopicThemes';

const options=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin','online_news'];
const initial={name:'',description:'',primary_keywords:[],secondary_keywords:[],excluded_keywords:[],platforms:['tiktok'],language:'',date_from:'',date_to:'',interval_minutes:120,province:'',regency_city:''};
const split=v=>String(v||'').split(',').map(s=>s.trim()).filter(Boolean);
const presentDate=v=>v?new Date(v).toLocaleString('en-GB'):'Not scheduled';
const displayStatus=s=>s==='PAUSED'?'Paused':'Draft';
const platformLabel=value=>({youtube:'YouTube',instagram:'Instagram',tiktok:'TikTok',facebook:'Facebook',threads:'Threads',x:'X',twitter:'X',reddit:'Reddit',linkedin:'LinkedIn'}[String(value||'').toLowerCase()]||String(value||'Unknown'));
function SentimentBar({values}){
 const categories=[{name:'Negative',color:'#dc4545'},{name:'Neutral',color:'#eab308'},{name:'Positive',color:'#16a34a'}];
 const counts=categories.map(x=>({...x,count:Number(values?.[x.name]??values?.[x.name.toUpperCase()]??values?.[x.name.toLowerCase()]??0)}));
 const total=counts.reduce((sum,x)=>sum+x.count,0);
 const unclassified=Number(values?.Unclassified??values?.UNCLASSIFIED??0);
 return <div className="pt-2 space-y-2" aria-label="Sentiment overview"><div className="flex items-center justify-between gap-2"><h6 className="text-xs font-semibold">Sentiment overview</h6><span className="text-[11px] text-slate-500">{total.toLocaleString()} classified · {unclassified.toLocaleString()} unclassified</span></div><div className="flex h-3 overflow-hidden rounded-full bg-slate-200" role="img" aria-label={total?counts.map(x=>x.name+': '+x.count).join(', '):'No sentiment data available'}>{counts.filter(x=>x.count>0).map(x=><div key={x.name} style={{width:(x.count/total*100)+'%',backgroundColor:x.color}} title={x.name+': '+x.count}/>)}</div><div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-600">{counts.map(x=><span key={x.name} className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-sm" style={{backgroundColor:x.color}}/>{x.name} {x.count.toLocaleString()}{total?' ('+(x.count/total*100).toFixed(1)+'%)':''}</span>)}</div></div>;
}
function ChannelDonut({values}){
 const entries=Object.entries(values||{}).filter(([,n])=>n>0).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
 const total=entries.reduce((n,[,v])=>n+v,0);
 const palette=['#285f82','#bc9b62','#339b92','#815ca7','#d2735c','#6d84a1','#69865f','#b95b83'];
 let offset=0;
 const segments=entries.map(([name,count],i)=>{const start=offset;offset+=count/total*100;return {name,count,percent:count/total*100,color:palette[i%palette.length],start,end:offset}});
 const gradient=total?'conic-gradient('+segments.map(s=>s.color+' '+s.start+'% '+s.end+'%').join(', ')+')':'conic-gradient(#e2e8f0 0% 100%)';
 return <div className="flex flex-col sm:flex-row items-center gap-5"><div aria-label="Channel distribution donut" role="img" className="relative w-40 h-40 shrink-0 rounded-full" style={{background:gradient}}><div className="absolute inset-8 rounded-full bg-white flex flex-col items-center justify-center"><strong className="text-xl">{total}</strong><span className="text-xs text-slate-500">captured</span></div></div><ul className="text-xs flex-1 space-y-2 w-full">{segments.map(s=><li key={s.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded" style={{background:s.color}}/><span className="flex-1 break-words">{platformLabel(s.name)}</span><strong>{s.count} ({s.percent.toFixed(1)}%)</strong></li>)}{!total&&<li>No channel evidence yet</li>}</ul></div>
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
 const [trackedCount,setTrackedCount]=useState(null);
 const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false);
 const [creating,setCreating]=useState(false),[editing,setEditing]=useState(null);
 const [form,setForm]=useState({...initial}),[selected,setSelected]=useState(null);
 const [query,setQuery]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [discoverCampaign,setDiscoverCampaign]=useState(null),[discoverPreview,setDiscoverPreview]=useState(null);
 const [discoverRun,setDiscoverRun]=useState(null),[discoverBusy,setDiscoverBusy]=useState(false),[discoverError,setDiscoverError]=useState('');
 async function checkDiscover(c){
   setDiscoverCampaign(c);setDiscoverPreview(null);setDiscoverRun(null);setDiscoverError('');setDiscoverBusy(true);
   try{const r=await base44.functions.invoke('socialListening',{action:'campaignDiscoverPreview',id:c.id,data:{}});
     setDiscoverPreview(r.data)}
   catch(e){setDiscoverError(e.response?.data?.detail||e.message||'Discover credit preview failed')}
   finally{setDiscoverBusy(false)}
 }
 async function launchDiscover(){
   if(!discoverCampaign||!discoverPreview||discoverBusy)return;
   if(!window.confirm('Run a separate paid SocialCrawl Discover search? Up to '+discoverPreview.credit_cap+' credits, at most 50 kept posts, plus OpenAI enrichment charges. No scheduled crawl is enabled.'))return;
   setDiscoverBusy(true);setDiscoverError('');
   try{const r=await base44.functions.invoke('socialListening',{action:'campaignDiscoverStart',id:discoverCampaign.id,
      data:{confirm_cost:true,signature:discoverPreview.signature}});setDiscoverRun(r.data)}
   catch(e){setDiscoverError(e.response?.data?.detail||e.message||'Unable to start Discover')}
   finally{setDiscoverBusy(false)}
 }
 async function refreshDiscover(){
   if(!discoverCampaign||!discoverRun)return;
   setDiscoverBusy(true);
   try{const r=await base44.functions.invoke('socialListening',{action:'campaignDiscoverStatus',
     id:discoverCampaign.id,data:{run_id:discoverRun.run_id}});setDiscoverRun(r.data);
     if(['COMPLETED','PARTIAL'].includes(r.data.status))await refresh()}
   catch(e){setDiscoverError(e.response?.data?.detail||e.message||'Status unavailable')}
   finally{setDiscoverBusy(false)}
 }

 const [total,setTotal]=useState(0);
 const [sampleText,setSampleText]=useState(''),[keywordPreview,setKeywordPreview]=useState(null),[previewBusy,setPreviewBusy]=useState(false),[previewError,setPreviewError]=useState('');
 const keywordPreviewRequest=useRef(0);
 function resetKeywordPreview(){keywordPreviewRequest.current+=1;setSampleText('');setKeywordPreview(null);setPreviewError('');setPreviewBusy(false)}
 async function checkKeywordPreview(){if(!selected||!sampleText.trim())return;const request=++keywordPreviewRequest.current;setPreviewBusy(true);setPreviewError('');setKeywordPreview(null);try{const response=await base44.functions.invoke('socialListening',{action:'campaignKeywordPreview',id:selected.id,data:{text:sampleText}});if(request===keywordPreviewRequest.current)setKeywordPreview(response.data.screening)}catch(e){if(request===keywordPreviewRequest.current)setPreviewError(e.response?.data?.detail||e.response?.data?.error||e.message)}finally{if(request===keywordPreviewRequest.current)setPreviewBusy(false)}}
 const [campaignSection,setCampaignSection]=useState('overview');
 const [statusFilter,setStatusFilter]=useState('all');
 const [trendMetric,setTrendMetric]=useState('posts');
 const [chartDay,setChartDay]=useState(null);
 const [evidence,setEvidence]=useState([]),[evidenceLoading,setEvidenceLoading]=useState(false),[evidenceError,setEvidenceError]=useState('');
 const [capturedSentimentFilter,setCapturedSentimentFilter]=useState('ALL'),[capturedSentimentSort,setCapturedSentimentSort]=useState('HOTTEST');
 const [capturedSourceFilter,setCapturedSourceFilter]=useState('ALL'),[capturedTextFilter,setCapturedTextFilter]=useState('');
 const [thumbnailRecoveryBusy,setThumbnailRecoveryBusy]=useState(false),[thumbnailRecoveryMessage,setThumbnailRecoveryMessage]=useState('');
 const [mediaPreviewBusy,setMediaPreviewBusy]=useState(false),[mediaPreview,setMediaPreview]=useState(null),[mediaPreviewError,setMediaPreviewError]=useState('');
 const [topAccountsMetric,setTopAccountsMetric]=useState('engagement');
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

 
 const [humanVerifiedFile,setHumanVerifiedFile]=useState(null);
 const [humanVerifiedPreview,setHumanVerifiedPreview]=useState(null);
 const [humanVerifiedResult,setHumanVerifiedResult]=useState(null);
 const [humanVerifiedBusy,setHumanVerifiedBusy]=useState(false);
 const [humanVerifiedError,setHumanVerifiedError]=useState('');
 async function humanVerifiedRequest(stage){
  if(!selected?.id||!humanVerifiedFile||humanVerifiedBusy)return;
  if(stage==='start'&&!window.confirm('Import all reviewed records into Social Listening for '+selected.name+'? Only the Relevant records will enter Intelligence Inbox. Existing evidence is preserved; no AI credits are used.'))return;
  setHumanVerifiedBusy(true);setHumanVerifiedError('');
  try{
   const form=new FormData();form.append('file',humanVerifiedFile);
   const token=localStorage.getItem('bawaslu_access_token')||'';
   const response=await fetch('/api/social-listening/human-verified/'+stage+'?campaign_id='+encodeURIComponent(selected.id),{
     method:'POST',headers:{Authorization:'Bearer '+token},body:form,cache:'no-store'});
   const payload=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(payload.detail||payload.error||'Workbook '+stage+' failed');
   if(stage==='preview'){setHumanVerifiedPreview(payload);setHumanVerifiedResult(null);}
   else {setHumanVerifiedResult(payload);await viewEvidence(selected);}
  }catch(err){setHumanVerifiedError(err.message||'Unable to import human-reviewed workbook');}
  finally{setHumanVerifiedBusy(false)}
 }

 const [externalRun,setExternalRun]=useState(null),[externalImportBusy,setExternalImportBusy]=useState(false),[externalImportError,setExternalImportError]=useState('');
 async function startExternalImport(){
  if(!selected||!externalFile||externalImportBusy||!externalPreview?.validation)return;
  if(!window.confirm('Import this ZocialEye file into '+selected.name+'? This adds provider records and links them to this campaign. No SocialCrawl credits are used.'))return;
  setExternalImportBusy(true);setExternalImportError('');
  try{setExternalRun(await base44.externalImport.start(selected.id,externalFile))}
  catch(e){setExternalImportError(e.response?.data?.error||e.message)}
  finally{setExternalImportBusy(false)}
 }
 async function refreshExternalImport(){
  if(!externalRun)return;
  try{setExternalRun(await base44.externalImport.status(externalRun.run_id))}
  catch(e){setExternalImportError(e.message)}
 }
 useEffect(()=>{
  if(!externalRun?.run_id||!['QUEUED','RUNNING'].includes(externalRun.status))return;
  const interval=setInterval(async()=>{
   try{const status=await base44.externalImport.status(externalRun.run_id);setExternalRun(status);
    if(status.status==='COMPLETED'&&selected){const response=await Promise.all([base44.functions.invoke('socialListening',{action:'campaignEvidence',id:selected.id,data:{keyword:appliedKeyword}}),base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,data:{date_from:analyticsFrom,date_to:analyticsTo,keyword:appliedKeyword}})]);setEvidence(response[0].data.evidence||[]);setDashboard(response[1].data)}}
   catch(e){setExternalImportError(e.message||'Import status unavailable')}
  },5000);
  return()=>clearInterval(interval);
 },[externalRun?.run_id,externalRun?.status,selected?.id]);
 const [externalFile,setExternalFile]=useState(null),[externalPreview,setExternalPreview]=useState(null),[externalBusy,setExternalBusy]=useState(false),[externalError,setExternalError]=useState('');
 async function previewExternalFile(){
  if(!selected||!externalFile||externalBusy)return;
  setExternalBusy(true);setExternalError('');setExternalPreview(null);
  try{const data=await base44.externalImport.preview(selected.id,externalFile);setExternalPreview(data)}
  catch(e){setExternalError(e.response?.data?.error||e.message||'Import preview failed')}
  finally{setExternalBusy(false)}
 }
 const [aiBusy,setAiBusy]=useState(false),[aiError,setAiError]=useState(''),[batchPreview,setBatchPreview]=useState(null),[batchNotice,setBatchNotice]=useState('');
 const [sentimentBatchSize,setSentimentBatchSize]=useState(10);
 const [everywhereQuery,setEverywhereQuery]=useState('');
 const [metricRepairBusy,setMetricRepairBusy]=useState(false),[metricRepairNotice,setMetricRepairNotice]=useState(''),[metricRepairError,setMetricRepairError]=useState('');
 const [manualPreview,setManualPreview]=useState(null),[manualBusy,setManualBusy]=useState(false),[manualDuplicate,setManualDuplicate]=useState(false),[manualNotice,setManualNotice]=useState('');
 const [analyticsFrom,setAnalyticsFrom]=useState(''),[analyticsTo,setAnalyticsTo]=useState(''),[analyticsKeyword,setAnalyticsKeyword]=useState(''),[appliedKeyword,setAppliedKeyword]=useState(''),[analyticsBusy,setAnalyticsBusy]=useState(false);
 const visibleCapturedPosts=evidence.filter(item=>{
  const day=String(item.published_at||'').slice(0,10);
  const dateOk=!(analyticsFrom||analyticsTo)||(day&&(!analyticsFrom||day>=analyticsFrom)&&(!analyticsTo||day<=analyticsTo));
  const channel=String(item.platform||'').toLowerCase().replace(/[\s_-]/g,'');
  const news=channel.includes('news')||channel==='online';
  const sourceOk=capturedSourceFilter==='ALL'||(capturedSourceFilter==='NEWS'?news:!news);
  const search=capturedTextFilter.trim().toLocaleLowerCase();
  const textOk=!search||[item.text_content,item.author_name,item.id].some(value=>String(value||'').toLocaleLowerCase().includes(search));
  const label=String(item.sentiment||'UNCLASSIFIED').toUpperCase();
  return dateOk&&sourceOk&&textOk&&(capturedSentimentFilter==='ALL'||(capturedSentimentFilter==='UNCLASSIFIED'?!['POSITIVE','NEUTRAL','NEGATIVE'].includes(label):label===capturedSentimentFilter));
 }).sort((a,b)=>capturedSentimentSort==='CLASSIFIED_FIRST'?(Number(['POSITIVE','NEUTRAL','NEGATIVE'].includes(String(b.sentiment||'').toUpperCase()))-Number(['POSITIVE','NEUTRAL','NEGATIVE'].includes(String(a.sentiment||'').toUpperCase()))):0);
 async function viewEvidence(c){
  setCampaignSection(['watchlist','posts'].includes(new URLSearchParams(window.location.search).get('tab'))?new URLSearchParams(window.location.search).get('tab'):'overview');
  setCapturedSentimentFilter('ALL');setCapturedSentimentSort('HOTTEST');setCapturedSourceFilter('ALL');setCapturedTextFilter('');resetKeywordPreview();setManualPreview(null);setManualDuplicate(false);setManualNotice('');setSelected(c);setExternalFile(null);setExternalPreview(null);setHumanVerifiedFile(null);setHumanVerifiedPreview(null);setHumanVerifiedResult(null);setHumanVerifiedError('');setExternalRun(null);setExternalImportError('');setExternalError('');setPostLookup('');setLookupPost(null);setLookupError('');setEvidence([]);setChartDay(null);setDashboard(null);setDashboardError('');setAnalyticsFrom('');setAnalyticsTo('');setAnalyticsKeyword('');setAppliedKeyword('');setEvidenceError('');setEvidenceLoading(true);
  try{
   const results=await Promise.allSettled([
    base44.functions.invoke('socialListening',{action:'campaignEvidence',id:c.id,data:{}}),
    base44.functions.invoke('socialListening',{action:'campaignDashboard',id:c.id,data:{}})
   ]);
   if(results[0].status==='fulfilled')setEvidence(results[0].value.data.evidence||[]);
   else setEvidenceError(results[0].reason?.response?.data?.detail||results[0].reason?.message||'Unable to load evidence');
   if(results[1].status==='fulfilled')setDashboard(results[1].value.data);
   else setDashboardError(results[1].reason?.response?.data?.detail||results[1].reason?.message||'Dashboard request failed');
  }finally{setEvidenceLoading(false)}
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
 async function refreshSentimentViews(){
  if(!selected)return;
  const [d,e]=await Promise.all([
    base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,
      data:{date_from:analyticsFrom,date_to:analyticsTo,keyword:appliedKeyword}}),
    base44.functions.invoke('socialListening',{action:'campaignEvidence',id:selected.id,
      data:{keyword:appliedKeyword}})
  ]);
  setDashboard(d.data);setEvidence(e.data.evidence||[]);
 }
 async function checkBatch(){
  if(!selected)return;
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignSentimentBatchPreview',id:selected.id,data:{sample_limit:sentimentBatchSize}});setBatchPreview(r.data);setAiError('')}
  catch(e){setAiError(e.response?.data?.detail||e.message)}
 }
 async function runBatch(){
  if(!selected||aiBusy||!batchPreview?.estimated_ai_calls)return;
  if(!window.confirm('Process '+batchPreview.estimated_ai_calls+' posts? OpenAI API charges may apply; exact monetary cost is unknown.'))return;
  setAiBusy(true);setAiError('');let completed=0;
  for(const result_id of batchPreview.selected_ids){
   try{const r=await base44.functions.invoke('socialListening',{action:'campaignSentimentClassify',id:selected.id,data:{result_id,confirm_ai_cost:true,retry_unclassified:true}});completed++;
      setEvidence(old=>old.map(x=>x.id===result_id?{...x,sentiment:r.data.sentiment,sentiment_details:{confidence:r.data.confidence,explanation:r.data.explanation,model:r.data.model}}:x))}
   catch(e){setAiError('Batch stopped: '+(e.response?.data?.detail||e.message));break}
  }
  setBatchNotice(completed+' post(s) processed. The campaign chart reflects saved labels.');
  setBatchPreview(null);
  if(completed){try{await refreshSentimentViews()}catch(e){setAiError('Analysis was saved but refresh failed: '+(e.response?.data?.detail||e.message))}}
  setAiBusy(false);
 }
 async function analyzeAllCampaignSentiment(){
  if(!selected||aiBusy)return;
  let preview;
  try{
    preview=(await base44.functions.invoke('socialListening',{
      action:'campaignSentimentBatchPreview',id:selected.id,
      data:{sample_limit:20,all_remaining:true,retry_unclassified:true}})).data;
  }catch(e){setAiError('Unable to inspect campaign: '+(e.response?.data?.detail||e.message));return}
  const ids=preview.selected_ids||[];
  if(!ids.length){setBatchNotice('No eligible posts with source text in this campaign.');return}
  if(!window.confirm('Analyze '+ids.length+' campaign posts with missing or Unclassified sentiment using OpenAI? Estimated '+ids.length+' billable API requests. '+(preview.missing_text||0)+' posts without text cannot be assessed. Every result is saved as a new assessment version. Continue?'))return;
  setAiBusy(true);setAiError('');
  let processed=0,classified=0,uncertain=0,failed=0;
  for(const result_id of ids){
    try{
      const response=await base44.functions.invoke('socialListening',{
        action:'campaignSentimentClassify',id:selected.id,
        data:{result_id,confirm_ai_cost:true}});
      processed++;
      if(String(response.data.sentiment).toUpperCase()==='UNCLASSIFIED')uncertain++;else classified++;
      setBatchNotice('OpenAI all-post analysis: '+processed+' / '+ids.length+' processed; '+classified+' classified, '+uncertain+' uncertain.');
    }catch(e){
      failed++;
      setAiError('Analysis stopped at '+processed+' / '+ids.length+' posts: '+(e.response?.data?.detail||e.message)+'. Previously processed assessments were saved.');
      break;
    }
  }
  setBatchPreview(null);
  setBatchNotice('All-post AI analysis: '+processed+'/'+ids.length+' attempted; '+classified+' assigned Positive/Neutral/Negative, '+uncertain+' uncertain, '+failed+' failed. Existing assessments remain in history.');
  try{await refreshSentimentViews()}catch(e){setAiError('Analysis saved, refresh failed: '+(e.response?.data?.detail||e.message))}
  setAiBusy(false);
 }
 async function classifyNextPost(){
  if(!selected||aiBusy)return;
  const item=evidence.find(x=>(!x.sentiment||x.sentiment==='Unclassified')&&!x.sentiment_details?.status);
  if(!item){setAiError('No unclassified post available in the loaded evidence.');return}
  if(!window.confirm('Analyze one post with AI? OpenAI API usage may incur a charge.'))return;
  setAiBusy(true);setAiError('');
  try{
   const res=await base44.functions.invoke('socialListening',{action:'campaignSentimentClassify',id:selected.id,data:{result_id:item.id,confirm_ai_cost:true}});
   setEvidence(old=>old.map(x=>x.id===item.id?{...x,sentiment:res.data.sentiment,
     sentiment_details:{confidence:res.data.confidence,explanation:res.data.explanation,
       model:res.data.model,status:res.data.sentiment==='Unclassified'?'ASSESSED_UNCLASSIFIED':'CLASSIFIED'}}:x));
   await refreshSentimentViews();
  }catch(e){setAiError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setAiBusy(false)}
 }
 async function applyAnalyticsDates(){
  if(!selected)return;
  if(analyticsFrom&&analyticsTo&&analyticsFrom>analyticsTo){setDashboardError('Start date must not be after end date.');return}
  setAnalyticsBusy(true);setDashboardError('');
  try{const keyword=analyticsKeyword.trim();const params={date_from:analyticsFrom,date_to:analyticsTo,keyword};const [r,e]=await Promise.all([base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,data:params}),base44.functions.invoke('socialListening',{action:'campaignEvidence',id:selected.id,data:{keyword}})]);setDashboard(r.data);setEvidence(e.data.evidence||[]);setAppliedKeyword(keyword)}
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
 useEffect(()=>{if(campaignId)return;let active=true;base44.functions.invoke('registry',{action:'list',data:{}}).then(r=>{if(active)setTrackedCount((r.data.items||[]).filter(x=>String(x.type||'').toLowerCase()==='candidate'&&x.status==='Active').length)}).catch(()=>{if(active)setTrackedCount(null)});return ()=>{active=false}},[campaignId]);
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
  e.preventDefault();
  if(invalidCampaignDates){setError('Start date cannot be after end date. Please correct the campaign dates.');return}
  setSaving(true);setError('');setNotice('');
  const fields=['name','description','primary_keywords','secondary_keywords','excluded_keywords','platforms','language','date_from','date_to','province','regency_city'];
  const data=editing
   ? Object.fromEntries(fields.filter(key=>JSON.stringify(form[key])!==JSON.stringify(editing[key]??(Array.isArray(form[key])?[]:''))).map(key=>[key,form[key]]))
   : {...form};
  try{
   if(editing&&!Object.keys(data).length){
    setNotice('No campaign changes to save.');setCreating(false);setEditing(null);return;
   }
   const action=editing?'updateCampaign':'createCampaign';
   await base44.functions.invoke('socialListening',{action,id:editing?.id,data});
   await refresh();
   setNotice('Campaign saved as draft. Automatic paid crawls remain disabled until scheduling is approved.');
   setSelected(null);setCreating(false);setEditing(null);
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message||'Campaign save failed')}
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
 return <section className="v10-campaign space-y-5" aria-label="Monitoring campaigns">
  {campaignId&&<style>{`.v10-campaign .intel-card {border-radius:13px}`}</style>}

  <header className="flex flex-wrap items-start justify-between gap-4">
    <div><p className="text-[11px] font-extrabold uppercase tracking-[.13em] text-[#6d8994]">Monitoring &amp; Collection</p>
    <h1 className="mt-1 text-[27px] font-bold tracking-tight text-[#152c47]">Social Listening</h1>
    <p className="mt-1 text-sm text-[#60768c]">Discover broad conversations. Track selected candidates.</p></div>
    {!campaignId&&<button type="button" className="rounded-xl border border-[#11816d] bg-[#11816d] px-5 py-3 text-sm font-semibold text-white hover:bg-[#0d685a]" onClick={newCampaign}>＋ Create campaign</button>}
  </header>
  <div className="rounded-xl border border-[#d7e8e2] bg-[#f4fbf8] px-4 py-3 text-xs leading-6 text-[#295e57]"><b>Live BAWASLU monitoring.</b> Campaigns, captured posts, classifications and candidate tracking show saved authorized records. No sample or demonstration posts have been added.</div>
  <nav className="flex flex-wrap items-center gap-x-3 gap-y-2 py-1" aria-label="Monitoring workflow steps">
   {['Set up monitoring','Monitoring Home','Campaign Dashboard'].map((label,i)=><span key={label} className={'inline-flex items-center gap-2 text-xs '+((creating?i===0:campaignId?i===2:i===1)?'font-bold text-[#117c6c]':'text-[#708394]')}>
    <span className={'grid h-6 w-6 place-items-center rounded-full '+((creating?i===0:campaignId?i===2:i===1)?'bg-[#117c6c] text-white':'bg-[#e3eaee] text-[#708394]')}>{i+1}</span>{label}{i<2&&<span className="ml-2 text-[#a0b1bb]">→</span>}
   </span>)}
  </nav>
  {!creating&&error&&<p role="alert" className="intel-card p-3 text-red-700">{error}</p>}
  {notice&&<p role="status" className="intel-card p-3 text-green-700">{notice}</p>}
  {creating&&<section className="rounded-xl border border-[#dce5ed] bg-white p-4 sm:p-6">
   <div className="w-full">
    <form className="p-5 sm:p-7 space-y-4" onSubmit={save} aria-label="Campaign editor">
   <div className="flex items-center justify-between gap-4">
    <div><h2 id="campaign-modal-title" className="text-xl font-semibold text-[#152c47]">{editing?'Edit monitoring campaign':'Create a monitoring campaign'}</h2><p className="text-sm text-[#60768c]">Choose keywords and collection coverage, then save your campaign to open its dashboard.</p></div>
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
   {editing&&(form.primary_keywords.length>30||form.secondary_keywords.length>30||form.excluded_keywords.length>30)&&<p className="text-xs text-amber-800">Legacy imported keywords are preserved when unchanged. You can save the campaign description without deleting them; newly modified keyword lists must meet the 30-keyword limit.</p>}
   {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
   <div className="flex gap-2"><button className="intel-button" disabled={saving||invalidCampaignDates||!form.primary_keywords.length}>{saving?'Saving…':'Save Draft'}</button>
    <button type="button" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>Cancel</button></div>
    </form>
   </div>
  </section>}
  {!campaignId&&!creating&&<section className="space-y-4">
   <div className="flex flex-wrap items-center justify-between gap-3 pt-1"><div><h2 className="text-xl font-semibold text-[#152c47]">Your monitoring campaigns</h2><p className="text-sm text-[#60768c]">Open a campaign to see the dashboard, captured posts and candidate tracking.</p></div>
   {campaigns.length>0&&<button type="button" className="rounded-xl bg-[#11816d] px-4 py-3 text-sm font-semibold text-white" onClick={()=>navigate('/social-listening/campaigns/'+campaigns[0].id+'?tab=watchlist')}>◎ Candidate Watchlist</button>}</div>
   <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
    {[[total,'Monitoring campaigns'],[campaigns.reduce((n,c)=>n+Number(c.evidence_count||0),0),'Campaign-linked source posts'],[new Set(campaigns.flatMap(c=>c.platforms||[])).size,'Configured source platforms'],[trackedCount===null?'—':trackedCount,'Actively tracked candidates']].map(([value,label])=><div key={label} className="rounded-xl border border-[#dce5ed] bg-white px-4 py-5"><strong className="block text-[26px] font-bold tabular-nums text-[#152c47]">{typeof value==='number'?value.toLocaleString():value}</strong><span className="text-[11px] text-[#60768c]">{label}</span></div>)}
   </div>
   <section className="rounded-[13px] border border-[#dce5ed] bg-white p-5" aria-label="Campaign list">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold text-[#19324a]">Monitoring campaigns</h3><input type="search" className="w-full max-w-[320px] rounded-lg border border-[#ccdae3] bg-white px-3 py-3 text-sm text-[#1a2d46]" placeholder="Search campaigns" aria-label="Search campaigns" value={query} onChange={e=>setQuery(e.target.value)}/></div>
    {loading?<p className="text-sm text-[#60768c]">Loading campaigns…</p>:<div className="space-y-3">{visible.map(c=><article key={c.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#dce5ed] bg-white px-4 py-5 hover:border-[#90c7bd]">
      <div className="min-w-0"><h4 className="text-base font-semibold text-[#19324a]">{c.name} <span className="ml-1 rounded-full bg-[#e8f4ef] px-2 py-1 text-[10px] font-bold text-[#207558]">{displayStatus(c.status)}</span></h4><p className="mt-1 text-xs text-[#60768c]">Keywords: {(c.primary_keywords||[]).join(', ')||'None'} · {(c.platforms||[]).map(platformLabel).join(', ')||'No platforms configured'}</p><p className="mt-1 text-xs text-[#60768c]">{Number(c.evidence_count||0).toLocaleString()} captured posts</p></div>
      <div className="flex flex-wrap gap-2"><button type="button" className="rounded-lg border border-[#11816d] bg-[#11816d] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0d685a]" onClick={()=>navigate('/social-listening/campaigns/'+c.id)}>Open Dashboard →</button><button type="button" className="intel-ghost" disabled={discoverBusy||c.status!=='DRAFT'} onClick={()=>checkDiscover(c)}>Discover · 50 posts</button><button type="button" className="intel-ghost" onClick={()=>editCampaign(c)}>Edit</button>{c.status==='DRAFT'&&<button type="button" className="intel-ghost" disabled={saving} onClick={()=>pause(c)}>Pause</button>}</div>
     </article>)}{discoverCampaign&&<div className="rounded-xl border border-teal-300 bg-teal-50 p-4 text-sm space-y-2" role="region" aria-label="Separate SocialCrawl Discover run">
  <div className="flex justify-between gap-3"><strong>Prism Discover · {discoverCampaign.name} · 50 posts maximum</strong><button className="intel-ghost text-xs" onClick={()=>{setDiscoverCampaign(null);setDiscoverPreview(null);setDiscoverRun(null)}}>Close</button></div>
  <p className="text-xs">Independent of Manual SocialCrawl. First 5 main keywords only, 7-day search window and hard cap of {discoverPreview?.credit_cap||100} provider credits. OpenAI enrichment is separately billed. No automatic schedule.</p>
  {discoverBusy&&<p role="status">Checking provider…</p>}
  {discoverError&&<p role="alert" className="text-red-700">{discoverError}</p>}
  {discoverPreview&&!discoverRun&&<div className="space-y-2"><p className="text-xs">Provider preview: {JSON.stringify(discoverPreview.estimate).slice(0,950)}</p>
    <p className="text-xs">Keywords: {(discoverPreview.keywords_used||[]).join(', ')} ({(discoverPreview.keywords_total||0)} configured) · Platforms: {(discoverPreview.platforms||[]).join(', ')} · {discoverPreview.incremental?'Incremental since last run':'Initial collection'}</p>
    <button type="button" className="intel-button text-xs" disabled={discoverBusy} onClick={launchDiscover}>Confirm paid Discover run</button>
  </div>}
  {discoverRun&&<div className="space-y-2" role="status"><p>Run #{discoverRun.run_id} · {discoverRun.status} · {discoverRun.posts_saved||0} saved posts · {discoverRun.credits_used||0} SocialCrawl credits · {discoverRun.ai_analyzed_posts||0} AI-analyzed · {discoverRun.ai_pending_posts||0} AI-pending</p><button type="button" className="intel-ghost text-xs" onClick={refreshDiscover} disabled={discoverBusy}>Refresh run status</button></div>}
 </div>}{!visible.length&&<p className="rounded-xl border border-dashed border-[#bcd0d5] p-8 text-center text-sm text-[#60768c]">No campaigns match your search.</p>}</div>}
   </section>
   <section className="rounded-xl border border-[#c7e5dc] bg-[#f4fbf8] p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><h3 className="font-semibold text-[#19324a]">New here? Start with a campaign.</h3><p className="mt-2 text-xs text-[#60768c]">Create a campaign to choose keywords and platforms, then open its dashboard to explore saved records and use Candidate Watchlist.</p></div><button type="button" className="rounded-lg bg-[#11816d] px-4 py-2.5 text-sm font-semibold text-white" onClick={newCampaign}>＋ Create a campaign</button></div></section>
  </section>}
  {campaignId&&selected&&!creating&&<div className="v10-detail space-y-4">
   <button type="button" className="intel-ghost" onClick={()=>navigate("/social-listening?tab=campaigns")}>← Back to campaigns</button>
   <h3 className="text-2xl font-bold text-[#152c47]">{selected.name} — Campaign Overview</h3>
   <div className="flex flex-wrap gap-2" aria-label="Campaign keyword summaries">
    {[['Main keywords',selected.primary_keywords],['Subkeywords',selected.secondary_keywords],['Excluded',selected.excluded_keywords]].map(([label,terms])=><details key={label} className="group min-w-[150px] max-w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"><summary className="cursor-pointer font-medium text-slate-700">{label} <strong className="ml-1 text-teal-700">{(terms||[]).length}</strong><span className="ml-1 text-slate-400 group-open:hidden">· View</span></summary><div className="mt-2 flex max-h-44 max-w-[680px] flex-wrap gap-1 overflow-y-auto">{(terms||[]).length?(terms||[]).map((term,i)=><span key={i} className="rounded border border-slate-200 bg-white px-2 py-1 break-words">{term}</span>):<span>None</span>}</div></details>)}
   </div>
   <p className="text-sm">Collection runs: {selected.run_count} · Evidence records: {selected.evidence_count}</p>

   <details className="rounded-lg border border-teal-200 bg-teal-50/40 p-3 text-xs" aria-label="Human-verified relevance import">
    <summary className="cursor-pointer font-semibold text-teal-900">Admin · Import human-reviewed source posts (Social Listening → Inbox)</summary>
    <p className="mt-2 text-slate-600">All spreadsheet records enter the selected campaign's Captured Posts. Only rows marked Relevant appear in Intelligence Inbox. Human labels are preserved, no AI or crawl credits are spent, and repeat imports do not duplicate sample IDs.</p>
    <input type="file" accept=".xlsx" aria-label="Human-verified Excel workbook" className="mt-3 block" onChange={e=>{setHumanVerifiedFile(e.target.files?.[0]||null);setHumanVerifiedPreview(null);setHumanVerifiedResult(null);setHumanVerifiedError('')}}/>
    <div className="mt-3 flex gap-2 flex-wrap">
      <button type="button" className="intel-ghost text-xs" disabled={!humanVerifiedFile||humanVerifiedBusy} onClick={()=>humanVerifiedRequest('preview')}>{humanVerifiedBusy?'Checking…':'Preview human labels'}</button>
      <button type="button" className="intel-button text-xs" disabled={!humanVerifiedFile||!humanVerifiedPreview||humanVerifiedBusy} onClick={()=>humanVerifiedRequest('start')}>Confirm and import to campaign</button>
    </div>
    {humanVerifiedPreview&&<p className="mt-2 text-teal-900">Preview: <strong>{humanVerifiedPreview.total} total</strong> · {humanVerifiedPreview.relevant} Relevant → Inbox · {humanVerifiedPreview.irrelevant} Irrelevant → Social Listening only. Source URL count: {humanVerifiedPreview.unique_direct_urls}. No records written yet.</p>}
    {humanVerifiedResult&&<p className="mt-2 font-semibold text-teal-900" role="status">Imported: {humanVerifiedResult.inserted} new sources, {humanVerifiedResult.already_present} already present; {humanVerifiedResult.saved_human_assessments} human assessments saved. {humanVerifiedResult.relevant} Relevant / {humanVerifiedResult.irrelevant} Irrelevant.</p>}
    {humanVerifiedError&&<p role="alert" className="mt-2 text-red-700">{humanVerifiedError}</p>}
   </details>
   <nav className="flex flex-wrap border-b border-[#dce5ed] gap-2 mt-3" aria-label="Selected campaign sections">{[['overview','Overview'],['posts','Captured Posts'],['watchlist','Candidate Watchlist']].map(([id,label])=><button type="button" key={id} className={'px-4 py-3 border-b-[3px] text-sm font-semibold '+(campaignSection===id?'text-[#087564] border-[#0d8a73] bg-[#f0faf6]':'text-[#627b8a] border-transparent')} onClick={()=>setCampaignSection(id)}>{label}</button>)}</nav>
    {campaignSection==='posts'&&<CapturedPostList campaignId={selected.id}/>}
   {campaignSection==='watchlist'&&<iframe title="Candidate Watchlist within selected campaign" src={"/ui-freeze/watchlist-v2_2.html?campaign_id="+encodeURIComponent(selected.id)} className="block w-full border-0 bg-[#edf2f4]" style={{height:'calc(100vh - 280px)',minHeight:700}}/>}
   <div className={campaignSection==='overview'?'contents':'hidden'} data-campaign-body={campaignSection}>

   {dashboardError&&<p role="alert" className="text-sm text-red-700">{dashboardError}</p>}
   {evidenceLoading&&!dashboard&&<p role="status" className="intel-card p-4 text-sm text-slate-600">Loading monitoring dashboard… Large campaigns can take longer to calculate.</p>}
   {!evidenceLoading&&!dashboard&&<div className="intel-card p-4 flex flex-wrap items-center gap-3" role="status"><span className="text-sm text-amber-800">Dashboard analytics could not load. Campaign data is still available.</span><button type="button" className="intel-button text-xs" onClick={async()=>{setDashboardError('');setEvidenceLoading(true);try{const response=await base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,data:{date_from:analyticsFrom,date_to:analyticsTo,keyword:appliedKeyword}});setDashboard(response.data)}catch(e){setDashboardError(e.response?.data?.detail||e.message||'Dashboard request failed')}finally{setEvidenceLoading(false)}}}>Retry dashboard</button></div>}

   {campaignSection==='overview'&&dashboard&&<section aria-label="Campaign monitoring dashboard" data-active-campaign-tab={campaignSection} className="rounded-[13px] border border-[#dce5ed] bg-white p-5 space-y-4">
    <h4 className="text-lg font-semibold text-[#19324a]">Monitoring dashboard</h4><p className="text-sm text-[#60768c]">Review the overall conversation here. Open Captured Posts to inspect original evidence, or Candidate Watchlist to monitor selected people.</p>
    <div className="flex flex-wrap gap-3 items-end" aria-label="Campaign analytics date filters"><label className="text-xs">From date<input type="date" className="intel-input mt-1" value={analyticsFrom} onChange={e=>setAnalyticsFrom(e.target.value)}/></label><label className="text-xs">To date<input type="date" className="intel-input mt-1" value={analyticsTo} onChange={e=>setAnalyticsTo(e.target.value)}/></label><label className="text-xs min-w-[180px] flex-1">Keyword<select className="intel-input mt-1 w-full" value={analyticsKeyword} onChange={e=>setAnalyticsKeyword(e.target.value)}><option value="">All keywords</option>{[...new Set([...(selected.primary_keywords||[]),...(selected.secondary_keywords||[])].map(x=>String(x||'').trim()).filter(Boolean))].map(term=><option value={term} key={term}>{term}</option>)}</select></label><button type="button" className="intel-ghost" disabled={analyticsBusy} onClick={applyAnalyticsDates}>{analyticsBusy?'Filtering…':'Apply filters'}</button></div>
    <p className="text-xs text-slate-500">Keyword dropdown filters by campaign keywords in post text (case-insensitive). Date filters use publication dates. Dashboard analytics cover up to the latest 5,000 matching evidence records. No crawl credits used.</p>{appliedKeyword&&<p className="text-xs font-medium text-teal-700">Showing results containing: “{appliedKeyword}”</p>}
    <section className="rounded-2xl border border-[#bdded6] bg-gradient-to-br from-[#eff9f6] to-white px-5 py-5" aria-label="AI Analysis of the selected mentions">
     <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-extrabold uppercase tracking-[.15em] text-[#167867]">BAWASLU Intelligence Briefing</p><h5 className="mt-1 text-xl font-bold text-[#19324a]">AI Analysis</h5><p className="text-xs text-[#60768c]">Overview of saved AI classifications and captured mentions for the selected period.</p></div><span className="rounded-lg border border-[#c8dfd9] bg-white px-3 py-2 text-xs text-[#126f61]">{analyticsFrom||analyticsTo?(analyticsFrom||'Start')+' – '+(analyticsTo||'Latest'):'All selected dates'}</span></div>
     <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">{[['Mentions reviewed',dashboard.statistics?.messages],['Source accounts',dashboard.statistics?.accounts],['Sentiment classified',dashboard.sentiment_classified_count]].map(([label,num])=><div key={label} className="rounded-xl border border-[#cfe4de] bg-white p-4"><strong className="block text-[26px] font-bold text-[#153a47]">{Number(num||0).toLocaleString()}</strong><span className="text-xs text-[#64798c]">{label}</span></div>)}</div>
     <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"><div className="rounded-xl border border-[#d7e8e2] bg-white p-4"><h6 className="mb-2 font-semibold text-[#19324a]">Campaign keyword matches</h6>{Object.entries(dashboard.main_keywords||{}).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([name,num])=><div key={name} className="flex justify-between gap-3 py-1 text-xs"><span className="break-words">{name}</span><strong>{num}</strong></div>)}{!Object.keys(dashboard.main_keywords||{}).length&&<p className="text-xs text-[#60768c]">No tracked keywords found in the selected posts.</p>}</div>
     <div className="rounded-xl border border-[#d7e8e2] bg-white p-4"><h6 className="mb-2 font-semibold text-[#19324a]">Overall sentiment</h6><div className="flex flex-wrap gap-3 text-xs"><span>🔴 Negative <b>{dashboard.sentiment?.Negative||0}</b></span><span>🟡 Neutral <b>{dashboard.sentiment?.Neutral||0}</b></span><span>🟢 Positive <b>{dashboard.sentiment?.Positive||0}</b></span></div><p className="mt-3 text-xs text-[#60768c]">{Number(dashboard.sentiment?.Unclassified||0).toLocaleString()} mentions have no saved sentiment classification.</p></div></div>
     <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="rounded-lg border-l-[3px] border-[#db9e39] bg-[#fff8ee] px-3 py-2 text-xs text-[#6b552f]">For BAWASLU: these are saved mention signals, not confirmed legal violations. Human evidence review remains required.</p><button type="button" className="rounded-lg border border-[#c8dfd9] bg-white px-3 py-2 text-xs font-semibold text-[#126f61]" onClick={()=>setCampaignSection('posts')}>View supporting posts →</button></div>
    </section>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <section className="rounded-lg border p-4 space-y-2" aria-label="Social Listening statistics"><h5 className="font-semibold text-teal-700">Statistics</h5><div className="grid grid-cols-2 xl:grid-cols-4 gap-2">{[['Messages',dashboard.statistics?.messages],['Engagements',dashboard.statistics?.engagement],['Accounts',dashboard.statistics?.accounts],['Views',dashboard.statistics?.views]].map(([label,value])=><div key={label} className="min-w-0 rounded-lg border px-2 py-3 text-center"><strong className="block text-lg font-semibold tabular-nums">{Number(value||0).toLocaleString()}</strong><p className="break-words text-[10px] leading-tight text-slate-500">{label}</p></div>)}</div><SentimentBar values={dashboard.sentiment}/><div className="flex flex-wrap justify-between gap-2"><p className="text-xs text-slate-500">Saved campaign AI assessments only. Neutral differs from Unclassified.</p><button type="button" className="intel-ghost text-xs" disabled={analyticsBusy||aiBusy} onClick={async()=>{setAnalyticsBusy(true);try{await refreshSentimentViews()}catch(e){setDashboardError(e.response?.data?.detail||e.message)}finally{setAnalyticsBusy(false)}}}>Refresh saved sentiment (free)</button></div><p className="text-xs text-slate-500">Views and engagements may be incomplete when platforms do not supply them.</p></section>

      <section className="rounded-lg border p-4 space-y-2" aria-label="Channel distribution"><h5 className="font-semibold">Channel distribution</h5><ChannelDonut values={dashboard.platforms}/></section>
      <section className="min-w-0 rounded-lg border p-4 space-y-3 lg:col-span-2" aria-label="Campaign trend by platform">
<h5 className="font-semibold">Social Listening by platform</h5>
<div className="flex gap-2" role="group" aria-label="Trend metric">{['posts','engagement','views'].map(k=><button key={k} type="button" aria-pressed={trendMetric===k} className={trendMetric===k?'intel-button':'intel-ghost'} onClick={()=>setTrendMetric(k)}>{k==='posts'?'Posts':k==='engagement'?'Engagement':'Views'}</button>)}</div>
{dashboard.daily_platform_trend?.length?<div className="h-80 w-full min-w-0 lg:h-96" role="img" aria-label={trendMetric+' trend by platform'}><ResponsiveContainer width="100%" height="100%">
<LineChart data={dashboard.daily_platform_trend} onClick={point=>{if(point?.activeLabel)openChartDate(String(point.activeLabel))}} margin={{top:12,right:14,left:-18,bottom:12}}>
<CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0"/><XAxis dataKey="date" tick={{fontSize:10}} minTickGap={26}/><YAxis allowDecimals={false} tick={{fontSize:11}}/><Tooltip/><Legend verticalAlign="bottom"/>
{Object.keys(dashboard.platforms||{}).map((platform,index)=><Line key={platform} type="monotone" dataKey={platform+'__'+trendMetric} name={platformLabel(platform)} stroke={['#285f82','#bc9b62','#339b92','#815ca7','#d2735c','#6d84a1','#69865f','#b95b83'][index%8]} dot={{r:3}} activeDot={{r:6}} connectNulls/>)}
</LineChart>
</ResponsiveContainer></div>:<p className="text-xs text-slate-500">No dated posts in this period</p>}
<p className="text-xs text-slate-500">Click a date on the chart to see its hottest posts. Only stored provider metrics are counted; missing data is not estimated.</p>
</section>
    {campaignSection==='overview'&&dashboard&&<TopicThemes data={dashboard.topics_and_themes}/>}
{chartDay&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-3" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setChartDay(null)}}>
 <div className="w-full max-w-xl max-h-[85vh] overflow-hidden rounded-xl bg-white shadow-xl flex flex-col" role="dialog" aria-modal="true" aria-label={'Top posts for '+chartDay.date}>
  <div className="flex items-center justify-between gap-3 border-b p-4">
   <div><h5 className="font-semibold">Top posts · {chartDay.date}</h5><p className="text-xs text-slate-500">{chartDay.total} stored posts on this date</p></div>
   <button type="button" className="intel-ghost text-sm" aria-label="Close date posts" onClick={()=>setChartDay(null)}>Close ×</button>
  </div>
  <p className="px-4 py-2 border-b text-xs text-slate-500">Ranked automatically using engagement and views.</p>
  <div className="overflow-y-auto p-4 space-y-3">
   {chartDay.loading?<p className="text-sm">Loading saved posts…</p>:chartDay.error?<p role="alert" className="text-sm text-red-700">{chartDay.error}</p>:chartDay.posts.length?chartDay.posts.map((post,index)=><div key={post.id} className="rounded-lg border p-3 space-y-2 text-sm">
    <div className="flex justify-between gap-3"><strong className="capitalize">{index+1}. {platformLabel(post.platform)} · {post.author_name||'Author unknown'}</strong><span className="text-xs text-slate-500">Post #{post.id}</span></div>
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
 <div className="flex items-center justify-between gap-2"><h5 className="font-semibold">Captured posts & sources</h5><button type="button" onClick={classifyNextPost} disabled={aiBusy||!evidence.some(x=>x.sentiment==="Unclassified"&&!x.sentiment_details?.status)} className="intel-ghost text-xs">{aiBusy?"Analyzing…":"AI classify 1 post"}</button></div><button type="button" className="intel-ghost text-xs" disabled={mediaPreviewBusy} onClick={previewMediaCapability}>{mediaPreviewBusy?'Checking media options…':'Check Instagram media options (free)'}</button>
 {mediaPreviewError&&<p className="text-xs text-red-600" role="alert">{mediaPreviewError}</p>}
 {mediaPreview&&<div className="rounded-md border bg-slate-50 p-3 text-xs space-y-1" aria-label="Instagram media capability preview">
  <p className="font-semibold">Instagram media enrichment · preview only</p>
  <p>{mediaPreview.counts?.instagram_missing||0} posts missing thumbnails; {mediaPreview.counts?.instagram_with_url||0} posts with a stored image URL; {mediaPreview.counts?.already_cached||0} cached images.</p>
  <p>{mediaPreview.counts?.post_url_available||0} eligible Instagram post URLs. Estimated post-detail requests: {mediaPreview.potential_calls||0}; estimated maximum at 1 credit each: {mediaPreview.potential_credit_estimate||0} credits.</p>
  <p className="text-amber-800">Image-field availability has not been validated. Paid enrichment is disabled. No SocialCrawl credits are used by this preview.</p>
 </div>}
 <button type="button" className="intel-ghost text-xs" disabled={thumbnailRecoveryBusy} onClick={recoverThumbnails}>{thumbnailRecoveryBusy?'Checking images…':'Recover stored thumbnails (free)'}</button>
 {thumbnailRecoveryMessage&&<p className="text-xs text-slate-600" role="status">{thumbnailRecoveryMessage}</p>}
 <div className="flex flex-wrap items-end gap-2"><label className="text-xs">Sentiment batch size<select aria-label="Sentiment batch size" className="intel-input mt-1" value={sentimentBatchSize} disabled={aiBusy} onChange={e=>{setSentimentBatchSize(Number(e.target.value));setBatchPreview(null)}}>{[1,5,10,20].map(n=><option key={n} value={n}>{n} posts</option>)}</select></label><button type="button" className="intel-ghost text-xs" disabled={aiBusy} onClick={checkBatch}>Preview sentiment AI (free)</button></div>
 {batchPreview&&<div className="rounded-md bg-slate-50 p-3 text-xs space-y-2"><p>{batchPreview.estimated_ai_calls} potentially billable OpenAI requests for existing posts (up to {batchPreview.sample_limit}; no new crawl). Token costs are unknown. No processing starts until you confirm.</p><button type="button" disabled={aiBusy||!batchPreview.estimated_ai_calls} className="intel-button" onClick={runBatch}>Confirm sentiment analysis</button></div>}
 <button type="button" className="intel-button text-xs" disabled={aiBusy||!selected} onClick={analyzeAllCampaignSentiment}>{aiBusy?'Analyzing…':'Temporary: Analyze all Unclassified posts with OpenAI'}</button>
 <p className="text-xs text-slate-500">Explicit confirmation required. Only missing/Unclassified posts are sent to OpenAI; existing classified labels remain unchanged. Ambiguous or missing-text records are reported, not silently assigned Neutral.</p>
 {batchNotice&&<p role="status" className="text-xs">{batchNotice}</p>}
 {aiError&&<p role="alert" className="text-xs text-red-700">{aiError}</p>}
 <button type="button" className="intel-ghost text-xs" disabled={!evidence.length} onClick={exportEvidenceCsv}>Export top posts to CSV (up to 200)</button> <button type="button" className="intel-ghost text-xs" onClick={async()=>{try{await base44.externalImport.downloadCampaign(selected.id)}catch(e){setEvidenceError(e.message)}}}>Export all campaign records (CSV)</button>
 <button type="button" className="intel-ghost text-xs" disabled={metricRepairBusy} onClick={async()=>{setMetricRepairBusy(true);setMetricRepairError('');setMetricRepairNotice('');try{const response=await base44.externalImport.repairMetrics(selected.id);setMetricRepairNotice('Metrics restored for '+response.repaired+' records. Dashboard refreshed.');const [ev,d]=await Promise.all([base44.functions.invoke('socialListening',{action:'campaignEvidence',id:selected.id,data:{keyword:appliedKeyword}}),base44.functions.invoke('socialListening',{action:'campaignDashboard',id:selected.id,data:{date_from:analyticsFrom,date_to:analyticsTo,keyword:appliedKeyword}})]);setEvidence(ev.data.evidence||[]);setDashboard(d.data)}catch(e){setMetricRepairError(e.response?.data?.error||e.message||'Metric repair failed')}finally{setMetricRepairBusy(false)}}}>{metricRepairBusy?'Restoring metrics…':'Admin: restore imported metrics'}</button>
 {metricRepairNotice&&<p role="status" className="text-xs text-teal-700">{metricRepairNotice}</p>}
 {metricRepairError&&<p role="alert" className="text-xs text-red-700">{metricRepairError}</p>}
 <div className="rounded-lg border border-slate-200 p-3 space-y-2" aria-label="Find campaign post by ID">
  <label htmlFor="campaign-post-lookup" className="block text-xs font-semibold">Find any campaign post by Post ID</label>
  <form onSubmit={e=>{e.preventDefault();findPostById()}} className="flex gap-2">
   <input id="campaign-post-lookup" className="intel-input min-w-0 flex-1" inputMode="numeric" pattern="[0-9]+" placeholder="e.g. 649" value={postLookup} onChange={e=>setPostLookup(e.target.value)}/>
   <button type="submit" className="intel-button text-xs" disabled={lookupBusy||!/^\d+$/.test(postLookup.trim())}>{lookupBusy?'Finding…':'Find post'}</button>
  </form>
  {lookupError&&<p role="alert" className="text-xs text-amber-700">{lookupError}</p>}
  {lookupPost&&<div className="rounded-lg bg-slate-50 border p-3 text-xs space-y-2">
   <div className="flex flex-wrap items-center gap-2"><strong>Post #{lookupPost.id} · {platformLabel(lookupPost.platform)}</strong><span className="text-slate-600">{lookupPost.assessment_status==='ASSESSED'?'Previously assessed':'Unassessed'}</span></div>
   <p className="whitespace-pre-wrap break-words max-h-44 overflow-y-auto">{lookupPost.text_content||'No source text available'}</p>
   {/^https:\/\//i.test(lookupPost.canonical_url||'')&&<a href={lookupPost.canonical_url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">Open original source ↗</a>}
   <div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost text-xs" disabled={singleBusy||lookupPost.assessment_status==='ASSESSED'} onClick={()=>previewSingle(lookupPost,false)}>Analyze with AI</button><button type="button" className="intel-ghost text-xs" disabled={singleBusy||lookupPost.assessment_status!=='ASSESSED'} onClick={()=>previewSingle(lookupPost,true)}>Reanalyze with AI</button></div>
  </div>}
 </div>
 <details className="rounded-lg border border-slate-200 p-3 text-xs space-y-3" aria-label="External provider import preview">
  <summary className="font-semibold cursor-pointer">Admin · External provider Excel/CSV import</summary>
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
    {externalPreview.validation&&<div className="border-t pt-2 space-y-1">
     <strong>Full-file validation · {externalPreview.validation.total_rows?.toLocaleString()||0} records scanned</strong>
     <p>Missing content: {externalPreview.validation.missing_content||0} · Missing URLs: {externalPreview.validation.missing_url||0} · Invalid URLs: {externalPreview.validation.invalid_url||0} · Missing dates: {externalPreview.validation.missing_date||0}</p>
     <p className="font-semibold">Eligible records: {externalPreview.validation.eligible_rows||0} · Ineligible: {externalPreview.validation.ineligible_rows||0} · Unknown platforms: {externalPreview.validation.unknown_platform||0}</p>
     <p>Repeated provider IDs: {externalPreview.validation.duplicate_provider_ids||0} · Repeated URLs: {externalPreview.validation.repeated_urls||0} · URL matches in current database: {externalPreview.validation.url_matches_existing_database||0}</p>
     <p>Comments identified: {externalPreview.validation.comment||0} · Posts/unknown: {externalPreview.validation.post_or_unknown||0} · Comments without parent post URL: {externalPreview.validation.comment_missing_parent_url||0}</p>
     <p>Platforms: {Object.entries(externalPreview.platform_distribution||{}).map(([name,count])=>platformLabel(name)+' '+count.toLocaleString()).join(' · ')}</p>
     <p className="text-amber-800">{externalPreview.duplicate_note}</p>
    </div>}
    <p className="text-slate-600">Provider IDs identify unique source records. Repeated URLs are not automatically discarded. Empty-content records will be skipped.</p>
    <button type="button" className="intel-ghost text-xs" disabled={externalImportBusy||!externalFile} onClick={startExternalImport}>{externalImportBusy?'Starting import…':'Confirm & start admin import'}</button>
    {externalImportError&&<p role="alert" className="text-red-700">{externalImportError}</p>}
    {externalRun&&<section aria-label="Live import progress" role="status" className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
     {(()=>{const p=externalRun.progress||{};const total=Number(p.total_rows||externalPreview?.total_source_rows||externalPreview?.validation?.total_rows||0);const done=Number(p.processed||0);const remaining=total?Math.max(0,total-done):null;const percent=total?Math.min(100,done/total*100):0;const stalled=externalRun.stalled===true;const fmt=n=>Number(n||0).toLocaleString();return <>
      <div className="flex flex-wrap items-center justify-between gap-2"><h5 className="font-semibold">Import #{externalRun.run_id}</h5><span className={'rounded-full px-2 py-1 text-xs font-semibold '+(stalled?'bg-amber-100 text-amber-900':externalRun.status==='COMPLETED'?'bg-green-100 text-green-800':'bg-blue-50 text-blue-800')}>{stalled?'No progress for 3+ minutes':externalRun.status==='RUNNING'?'Importing records…':externalRun.status}</span></div>
      <div className="flex items-end justify-between gap-2"><span className="text-sm font-medium">{fmt(done)} {total?'of '+fmt(total):'records'} processed</span><strong className="tabular-nums text-lg">{total?percent.toFixed(1)+'%':'In progress'}</strong></div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Records processed" aria-valuemin={0} aria-valuenow={done} aria-valuemax={total||undefined}><div className="h-full rounded-full bg-teal-600 transition-all" style={{width:percent+'%'}}/></div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">{[['Remaining',remaining===null?'Calculating…':fmt(remaining)],['Inserted',fmt(p.inserted)],['Linked',fmt(p.linked)],['Skipped',fmt(p.skipped)],['Already present',fmt(p.already_present)]].map(([label,value])=><div key={label} className="min-w-0 rounded-lg border p-2"><p className="text-xs text-slate-500">{label}</p><strong className="break-words tabular-nums">{value}</strong></div>)}</div>
      {stalled&&<p role="alert" className="text-sm text-amber-800">Progress has not changed for over three minutes. The import may be interrupted. Do not start another import until the worker is checked.</p>}
      {externalRun.status==='RUNNING'&&!stalled&&<p className="text-xs text-slate-500">Updates automatically every 5 seconds. You do not need to refresh the page.</p>}
      {externalRun.error&&<p className="text-sm text-red-700">{externalRun.error}</p>}
      {externalRun.status==='INTERRUPTED'&&<p className="text-sm text-amber-800">The job is interrupted. After confirming it is no longer running, re-upload the same file to resume without duplicate provider IDs.</p>}
      <button type="button" className="intel-ghost text-xs" onClick={refreshExternalImport}>Refresh import progress</button>
     </>})()}
    </section>}
  </div>}
 </details>
 <div className="flex flex-wrap gap-2 items-end"><label className="text-xs font-semibold">Source type<select aria-label="Filter captured posts by source type" className="intel-input mt-1 block" value={capturedSourceFilter} onChange={e=>setCapturedSourceFilter(e.target.value)}><option value="ALL">All sources</option><option value="SOCIAL">Social media</option><option value="NEWS">Online News</option></select></label><label className="text-xs font-semibold">Find captured text<input aria-label="Find captured text" type="search" className="intel-input mt-1 block" value={capturedTextFilter} placeholder="Text, author or ID" onChange={e=>setCapturedTextFilter(e.target.value)}/></label><label className="text-xs font-semibold">Sentiment filter<select aria-label="Filter captured posts by sentiment" className="intel-input mt-1 block" value={capturedSentimentFilter} onChange={e=>setCapturedSentimentFilter(e.target.value)}>{[['ALL','All sentiments'],['POSITIVE','Positive'],['NEUTRAL','Neutral'],['NEGATIVE','Negative'],['UNCLASSIFIED','Unclassified']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label className="text-xs font-semibold">Sort posts<select aria-label="Sort captured posts" className="intel-input mt-1 block" value={capturedSentimentSort} onChange={e=>setCapturedSentimentSort(e.target.value)}><option value="HOTTEST">Hottest first</option><option value="CLASSIFIED_FIRST">Classified first</option></select></label><span className="text-xs text-slate-500">{visibleCapturedPosts.length} matching / {evidence.length} loaded</span></div>
 <p className="text-xs text-slate-500">Source, search and sentiment filters use only saved posts. No provider or AI calls.</p>
 {evidenceError&&<p role="alert" className="text-xs text-red-700">{evidenceError}</p>}
 {evidenceLoading?<p className="text-xs">Loading evidence…</p>:evidence.length?<div className="max-h-96 overflow-y-auto space-y-2">
 {visibleCapturedPosts.slice(0,40).map(item=>{
 const valid=/^https:\/\//i.test(item.canonical_url||'');
 return <div key={item.id} className="space-y-1"><a href={valid?item.canonical_url:undefined} target={valid?'_blank':undefined} rel="noopener noreferrer" aria-label={valid?'Open original '+item.platform+' post':'Source URL unavailable'} className={'flex items-center gap-2 rounded-xl border border-slate-200 p-2.5 text-xs transition-colors '+(valid?'hover:border-blue-300 hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500':'cursor-default')}>
  <SourceThumbnail url={item.thumbnail_url} platform={item.platform}/>
  <div className="min-w-0 flex-1 space-y-1"><div className="flex items-center gap-2"><strong className="capitalize">{platformLabel(item.platform)} · {item.content_type||'Post'}</strong><span className="text-slate-500">{item.published_at?String(item.published_at).slice(0,10):'Undated'}</span></div><p className="line-clamp-3 text-slate-700 whitespace-pre-wrap break-words">{item.text_content||'No source text'}</p></div>
  <SentimentMarker value={item.sentiment} details={item.sentiment_details}/>
 </a><button type="button" className="intel-ghost text-xs" disabled={singleBusy} onClick={()=>previewSingle(item,false)}>Analyze with AI · Post #{item.id}</button><button type="button" className="intel-ghost text-xs" disabled={singleBusy} onClick={()=>previewSingle(item,true)}>Reanalyze with AI · Post #{item.id}</button></div>})}{!visibleCapturedPosts.length&&<p className="text-xs p-3 text-slate-500">No loaded posts match the selected source, search, date or sentiment filters.</p>}</div>:<p className="text-xs text-slate-500">No captured evidence yet</p>}
 {singlePreview&&<div className="rounded-lg border border-amber-300 p-3 space-y-2 text-xs" role="status"><strong>Post #{singlePreview.result_id} · {singlePreview.reanalysis?'Versioned AI reanalysis':'AI analysis'} cost preview</strong><p>Exactly {singlePreview.estimated_ai_requests} AI request · SocialCrawl credits: {singlePreview.socialcrawl_credits} · {singlePreview.estimated_ai_cost}.</p><button type="button" className="intel-button" disabled={singleBusy||!singlePreview.ai_key_configured} onClick={startSingle}>Confirm paid AI analysis for this post</button><button type="button" className="intel-ghost ml-2" onClick={()=>setSinglePreview(null)}>Cancel</button>{!singlePreview.ai_key_configured&&<p>AI provider key not configured.</p>}</div>}
 {singleNotice&&<p role="status" className="text-xs">{singleNotice}</p>}
 <p className="text-xs text-slate-500">Up to 40 matching posts displayed from the loaded 200 hottest stored posts (up to 5,000 scanned). Filters do not search outside the loaded set.</p>
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
<ProvinceHeatmap distribution={dashboard.province_connected_distribution||[]} totalPosts={dashboard.statistics?.messages||0}/>
 <section className="rounded-lg border p-4 space-y-3" aria-label="Campaign word cloud">
 <div className="flex items-center justify-between gap-3"><h5 className="font-semibold">Word cloud</h5><span className="text-xs text-slate-500" title="Larger words occur more often in captured evidence. Common Indonesian, Malay and English filler words are removed.">Term frequency · stored posts</span></div>
 {dashboard.word_cloud?.length?<div className="min-h-64 flex flex-wrap items-center content-center justify-center gap-x-4 gap-y-3 px-3 py-5" aria-label="Word cloud terms">{dashboard.word_cloud.map((term,index)=>{const max=Math.max(...dashboard.word_cloud.map(x=>x.count),1);const ratio=term.count/max;return <span key={term.word} title={term.word+': '+term.count+' occurrences'} className="font-medium leading-tight" style={{fontSize:(12+ratio*27)+'px',color:term.secondary?'#b7791f':['#0c5963','#237e86','#326b88','#426c78'][index%4],fontWeight:term.secondary?700:500}}>{term.word}</span>})}</div>:<p className="min-h-56 flex items-center justify-center text-sm text-slate-500">No configured campaign keywords appear in the selected evidence.</p>}
 <p className="text-xs text-slate-500">Only configured main and secondary keywords are shown. Sizes reflect recorded mentions in the selected date range. Gold indicates secondary keywords. No additional SocialCrawl or AI calls.</p>
 </section>
 <section className="rounded-lg border p-4 space-y-3" aria-label="Top social accounts">
  <div className="flex flex-wrap items-center justify-between gap-2"><h5 className="font-semibold">Top accounts</h5><div className="flex gap-1" role="group" aria-label="Rank accounts"><button type="button" className={topAccountsMetric==='engagement'?'intel-button text-xs':'intel-ghost text-xs'} onClick={()=>setTopAccountsMetric('engagement')}>Post engagement</button><button type="button" className={topAccountsMetric==='followers'?'intel-button text-xs':'intel-ghost text-xs'} onClick={()=>setTopAccountsMetric('followers')}>Account followers</button></div></div>
  {(()=>{const accounts=topAccountsMetric==='engagement'?dashboard.top_accounts_engagement:dashboard.top_accounts_followers;const key=topAccountsMetric==='engagement'?'engagement':'followers';const badges={facebook:'f',instagram:'◎',tiktok:'♪',youtube:'▶',x:'X',threads:'@'};return accounts?.length?<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-7 gap-2" aria-label="Top accounts, scroll horizontally">{accounts.slice(0,7).map((item,i)=><div key={item.platform+'-'+item.account} className="min-w-0 flex flex-col items-center text-center gap-1.5 py-3"><div className="relative"><div className="w-16 h-16 lg:w-20 lg:h-20 rounded-full border-2 border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden text-2xl font-semibold text-slate-600" aria-label={'Profile placeholder for '+item.account}>{String(item.account||'?').replace(/^@/,'').slice(0,2).toUpperCase()}</div><span className="absolute -top-1 -right-1 h-7 w-7 rounded-full bg-teal-600 border-2 border-white text-white text-sm font-bold flex items-center justify-center" title={platformLabel(item.platform)}>{badges[String(item.platform).toLowerCase()]||'•'}</span></div><p className="text-sm text-slate-500 w-full truncate" title={item.account}>{item.account}</p><strong className="text-teal-600 tabular-nums">{Number(item[key]||0).toLocaleString()}</strong><span className="text-xs text-slate-400">{topAccountsMetric==='engagement'?'engagements':'followers'}</span></div>)}</div>:<p className="text-sm text-slate-500">{topAccountsMetric==='followers'?'Follower counts are not available for the selected accounts.':'No account engagement available for this selection.'}</p>})()}
  <p className="text-xs text-slate-500">Engagement ranks accounts by summed reported engagement on captured posts, not by account popularity. Followers reflect reported account-level counts when supplied.</p>
 </section>
   </section>}
   <details className="rounded-lg border border-slate-200 p-4 space-y-3">
    <summary className="cursor-pointer font-semibold text-sm">Keyword screening preview (free)</summary>
    <div className="mt-3 space-y-3 text-sm" aria-label="Campaign keyword screening preview">
      <p className="text-xs text-slate-600">Test saved campaign keywords against example text. Local keyword matching only; no paid crawl or AI assessment.</p>
      <label className="block text-xs font-medium">Sample social post
        <textarea className="intel-input w-full mt-1" aria-label="Sample social post" rows={3} value={sampleText} onChange={e=>{setSampleText(e.target.value);setKeywordPreview(null);setPreviewError('')}}/>
      </label>
      <button type="button" className="intel-ghost text-xs" disabled={previewBusy||!sampleText.trim()} onClick={checkKeywordPreview}>{previewBusy?'Checking…':'Preview keyword match'}</button>
      {keywordPreview&&<p role="status" className="text-xs text-slate-700">{keywordPreview.matched?'Matches campaign keywords':'Does not match campaign keywords'} · Secondary context: {(keywordPreview.secondary_keywords||[]).join(', ')||'None'} · Excluded terms: {(keywordPreview.excluded_keywords||[]).join(', ')||'None'}</p>}
      {previewError&&<p role="alert" className="text-xs text-red-700">{previewError}</p>}
    </div>
   </details>
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
   {campaignSection==='overview'&&<details className="rounded-xl border border-[#dce5ed] bg-white p-4"><summary className="cursor-pointer text-sm font-semibold text-[#19324a]">AI assessment tools and source review</summary><div className="mt-3"><AssessmentPilotPreview campaign={selected}/></div></details>}
   {evidenceError&&<p role="alert" className="text-red-700 text-sm">{evidenceError}</p>}
  </div>
  </div>}
 </section>
}
