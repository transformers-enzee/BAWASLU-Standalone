import { useEffect, useRef, useState } from 'react';
import { base44 } from '@/api/base44Client';
import CampaignScheduleSummary from '@/components/intel/CampaignScheduleSummary';
import KeywordTags from '@/components/intel/KeywordTags';

const options=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin','online_news'];
const initial={name:'',description:'',primary_keywords:[],secondary_keywords:[],excluded_keywords:'',platforms:['tiktok'],language:'',date_from:'',date_to:'',interval_minutes:180,province:'',regency_city:''};
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

export default function CampaignPanel(){
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
 const [evidence,setEvidence]=useState([]),[evidenceLoading,setEvidenceLoading]=useState(false),[evidenceError,setEvidenceError]=useState('');
 const [dashboard,setDashboard]=useState(null),[dashboardError,setDashboardError]=useState('');
 const [manualPreview,setManualPreview]=useState(null),[manualBusy,setManualBusy]=useState(false),[manualDuplicate,setManualDuplicate]=useState(false),[manualNotice,setManualNotice]=useState('');
 const [analyticsFrom,setAnalyticsFrom]=useState(''),[analyticsTo,setAnalyticsTo]=useState(''),[analyticsBusy,setAnalyticsBusy]=useState(false);
 async function viewEvidence(c){
  resetKeywordPreview();setManualPreview(null);setManualDuplicate(false);setManualNotice('');setSelected(c);setEvidence([]);setDashboard(null);setDashboardError('');setAnalyticsFrom('');setAnalyticsTo('');setEvidenceError('');setEvidenceLoading(true);
  try{const [r,d]=await Promise.all([base44.functions.invoke('socialListening',{action:'campaignEvidence',id:c.id,data:{}}),base44.functions.invoke('socialListening',{action:'campaignDashboard',id:c.id,data:{}})]);setEvidence(r.data.evidence||[]);setDashboard(d.data)}
  catch(e){setEvidenceError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setEvidenceLoading(false)}
 }
 async function previewManualCrawl(){
  if(!selected)return;setManualBusy(true);setManualPreview(null);setManualNotice('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignManualPreflight',id:selected.id,data:{}});setManualPreview(r.data);setManualDuplicate(false)}
  catch(e){setManualNotice(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setManualBusy(false)}
 }
 async function executeManualCrawl(){
  if(!selected||!manualPreview?.can_run)return;setManualBusy(true);setManualNotice('');
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignManualRun',id:selected.id,data:{confirm_cost:true,confirmed_credits:manualPreview.estimated_credits,acknowledge_duplicate:manualDuplicate}});
   setManualPreview(null);setManualNotice('Completed: '+r.data.result_count+' new results, '+r.data.linked_evidence+' linked campaign evidence. Actual credits: '+r.data.run.credits_used+'.');
   await refresh();await viewEvidence(selected);
  }catch(e){setManualNotice(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setManualBusy(false)}
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
     secondary_keywords:form.secondary_keywords,excluded_keywords:split(form.excluded_keywords)
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
 useEffect(()=>{refresh()},[]);
 function newCampaign(){resetKeywordPreview();clearEstimate();setForm({...initial,platforms:['tiktok']});setEditing(null);setCreating(true);setSelected(null);setError('');setNotice('')}
 function editCampaign(c){
  resetKeywordPreview();clearEstimate();setForm({name:c.name,description:c.description||'',
   primary_keywords:[...(c.primary_keywords||[])],
   secondary_keywords:[...(c.secondary_keywords||[])],
   excluded_keywords:(c.excluded_keywords||[]).join(', '),
   platforms:[...(c.platforms||[])],language:c.language||'',date_from:c.date_from||'',date_to:c.date_to||'',
   interval_minutes:c.interval_minutes||180,province:c.province||'',regency_city:c.regency_city||''});
  setEditing(c);setCreating(true);setSelected(null);setError('');setNotice('');
 }
 async function save(e){
  e.preventDefault();if(invalidCampaignDates){setError('Start date cannot be after end date. Please correct the campaign dates.');return}setSaving(true);setError('');setNotice('');
  const data={...form,primary_keywords:form.primary_keywords,
   secondary_keywords:form.secondary_keywords,excluded_keywords:split(form.excluded_keywords)};
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
  {!selected&&<div className="intel-card p-5 space-y-3">
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
    <label className="text-sm">Excluded keywords<input className="intel-input mt-1" value={form.excluded_keywords} onChange={e=>set('excluded_keywords',e.target.value)} placeholder="music, concert"/></label>
    <label className="text-sm">Monitoring interval<select className="intel-input mt-1" value={form.interval_minutes} onChange={e=>set('interval_minutes',Number(e.target.value))}>
       <option value={60}>Every hour</option><option value={180}>Every 3 hours</option><option value={360}>Every 6 hours</option><option value={720}>Every 12 hours</option><option value={1440}>Daily</option>
    </select></label>
    <label className="text-sm">Start date<input className="intel-input mt-1" type="date" value={form.date_from} onChange={e=>set('date_from',e.target.value)}/></label>
    <label className="text-sm">End date<input className="intel-input mt-1" type="date" aria-invalid={invalidCampaignDates} value={form.date_to} onChange={e=>set('date_to',e.target.value)}/></label>
    {invalidCampaignDates&&<p role="alert" className="md:col-span-2 text-sm text-red-700">Start date cannot be after end date. Please correct the campaign dates.</p>}
    <label className="text-sm">Province (optional; regional access still applies)<input className="intel-input mt-1" value={form.province} onChange={e=>set('province',e.target.value)}/></label>
    <label className="text-sm">Regency / City<input className="intel-input mt-1" value={form.regency_city} onChange={e=>set('regency_city',e.target.value)}/></label>
   </div>
   <label className="block text-sm">Description<textarea rows={2} className="intel-input mt-1 w-full" value={form.description} onChange={e=>set('description',e.target.value)}/></label>
   <fieldset className="space-y-2"><legend className="text-sm font-semibold">Platforms *</legend>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{options.map(p=><label key={p} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.platforms.includes(p)} onChange={e=>set('platforms',e.target.checked?[...form.platforms,p]:form.platforms.filter(x=>x!==p))}/>{p}</label>)}</div>
   </fieldset>
   <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 space-y-2" aria-label="Campaign credit preflight">
    <p className="text-sm font-semibold text-amber-950">SocialCrawl credit estimate — before running</p>
    <p className="text-xs text-amber-900">A cost preview does not call SocialCrawl or use credits. Always review the latest estimate before authorizing a paid run.</p>
    <button type="button" className="intel-ghost" disabled={estimating||saving||!form.name.trim()||!form.primary_keywords.length||!form.platforms.length} onClick={checkCredits}>{estimating?'Calculating…':'Check estimated credits'}</button>
    {estimateError&&<p role="alert" className="text-xs text-red-700">{estimateError}</p>}
    {creditEstimate&&<div role="status" className="text-sm text-amber-950">
      Estimated cost: <strong>{creditEstimate.estimated_credits} credits per run</strong>
      {Array.isArray(creditEstimate.components)&&creditEstimate.components.length>0&&<ul className="mt-2 space-y-1 text-xs" aria-label="Estimated credits by source">{creditEstimate.components.map((part,index)=><li key={part.endpoint||index} className="flex justify-between gap-3"><span>{part.label||part.endpoint}</span><strong>{part.credits} credits</strong></li>)}</ul>}
      <p className="text-xs">Estimate, not a guaranteed final charge. Actual provider usage may differ.</p>
      <p className="text-xs">Scheduled paid crawling is disabled. This preview is not approval to run.</p>
    </div>}
   </div>
   <div className="flex gap-2"><button className="intel-button" disabled={saving||invalidCampaignDates||!form.primary_keywords.length}>{saving?'Saving…':'Save Draft'}</button>
    <button type="button" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>Cancel</button></div>
    </form>
   </div>
  </div>}
  {!selected&&(loading?<p className="intel-card p-4">Loading campaigns…</p>:<div className="intel-card overflow-x-auto"><table className="w-full text-left text-sm" aria-label="Campaign list"><thead className="bg-slate-50 text-xs uppercase text-slate-600"><tr><th className="p-3">Campaign</th><th className="p-3">Dates</th><th className="p-3">Status</th><th className="p-3">Evidence</th><th className="p-3">Actions</th></tr></thead><tbody>{visible.map(c=><tr key={c.id} className="border-t border-slate-100"><td className="p-3"><strong>{c.name}</strong><div className="text-xs text-slate-500">{(c.primary_keywords||[]).join(' · ')}</div></td><td className="p-3 text-xs">{c.date_from||'Any'} — {c.date_to||'Any'}</td><td className="p-3">{displayStatus(c.status)}</td><td className="p-3">{c.evidence_count}</td><td className="p-3"><div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost" onClick={()=>viewEvidence(c)}>View Evidence</button><button type="button" className="intel-ghost" onClick={()=>editCampaign(c)}>Edit</button>{c.status==='DRAFT'&&<button type="button" className="intel-ghost" disabled={saving} onClick={()=>pause(c)}>Pause</button>}</div></td></tr>)}</tbody></table>{!visible.length&&<p className="p-4 text-sm">No campaigns match your filters.</p>}</div>)}
  {selected&&!creating&&<div className="intel-card p-5 space-y-2">
   <button type="button" className="intel-ghost" onClick={()=>{setSelected(null);setManualPreview(null)}}>← Back to campaigns</button>
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
      <section className="rounded-lg border p-4 space-y-2" aria-label="Channel distribution"><h5 className="font-semibold">Channel distribution</h5><ChannelDonut values={dashboard.platforms}/></section>
      <section className="rounded-lg border p-4 space-y-2" aria-label="Posts and comments trend"><h5 className="font-semibold">Posts & comments over time</h5>{dashboard.daily_trend?.length?<div className="space-y-2">{dashboard.daily_trend.map(point=><div key={point.date} className="text-xs"><div className="flex justify-between"><span>{point.date}</span><span>{point.posts||0} posts · {point.comments||0} comments</span></div><div className="flex mt-1 h-3 rounded bg-slate-100 overflow-hidden"><div className="bg-[#285f82]" style={{width:(100*(point.posts||0)/Math.max(1,...dashboard.daily_trend.map(x=>x.count)))+'%'}}/><div className="bg-[#bc9b62]" style={{width:(100*(point.comments||0)/Math.max(1,...dashboard.daily_trend.map(x=>x.count)))+'%'}}/></div></div>)}</div>:<p className="text-xs text-slate-500">No dated evidence in this period</p>}<div className="flex gap-3 text-xs"><span>■ Posts</span><span className="text-amber-700">■ Comments</span></div></section>
      <section className="rounded-lg border p-4 space-y-2" aria-label="Captured posts"><h5 className="font-semibold">Captured posts & sources</h5>{evidenceLoading?<p className="text-xs">Loading evidence…</p>:evidence.length?<div className="max-h-72 overflow-y-auto space-y-2">{evidence.filter(item=>{const day=String(item.published_at||'').slice(0,10);return !(analyticsFrom||analyticsTo)||(day&&(!analyticsFrom||day>=analyticsFrom)&&(!analyticsTo||day<=analyticsTo))}).slice(0,40).map(item=><article key={item.id} className="border-b pb-2 text-xs"><p className="font-semibold">{item.platform} · {item.content_type||'post'} · {item.published_at||'Undated'}</p><p className="line-clamp-3 whitespace-pre-wrap">{item.text_content||'No source text'}</p>{/^https:\/\//i.test(item.canonical_url||'')&&<a href={item.canonical_url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">Open original source ↗</a>}</article>)}</div>:<p className="text-xs text-slate-500">No captured evidence yet</p>}<p className="text-xs text-slate-500">Showing up to 40 of the latest 200 linked records.</p></section>
      <section className="rounded-lg border p-4 space-y-2" aria-label="Sentiment analysis"><h5 className="font-semibold">Sentiment analysis</h5><div className="grid grid-cols-2 gap-2 text-xs">{['Positive','Neutral','Negative','Unclassified'].map(name=><div key={name} className="rounded bg-slate-50 p-3"><span>{name}</span><strong className="block text-lg">{dashboard.sentiment?.[name]||0}</strong></div>)}</div><p className="text-xs text-slate-600">AI sentiment classification is not yet active. Existing records remain Unclassified; no sentiment is inferred.</p></section>
    </div>
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
    <p className="text-xs text-slate-600">Manual runs only. Maximum estimated charge: 5 credits per run. Scheduled crawling remains disabled.</p>
    <button type="button" className="intel-ghost" disabled={manualBusy||selected.status!=='DRAFT'} onClick={previewManualCrawl}>Check manual crawl cost (free)</button>
    {manualPreview&&<div className="space-y-2 text-sm" role="status"><p>Estimated cost: <strong>{manualPreview.estimated_credits} credits</strong> (limit {manualPreview.credit_limit})</p>
      {(manualPreview.components||[]).map((x,i)=><p key={i} className="text-xs">{x.label}: {x.credits} credits</p>)}
      {manualPreview.duplicate_recent&&<label className="flex gap-2 items-center text-xs"><input type="checkbox" checked={manualDuplicate} onChange={e=>setManualDuplicate(e.target.checked)}/> I understand this repeats a recent search</label>}
      <button type="button" className="intel-button" disabled={manualBusy||!manualPreview.can_run||(manualPreview.duplicate_recent&&!manualDuplicate)} onClick={executeManualCrawl}>Confirm and run paid crawl ({manualPreview.estimated_credits} estimated credits)</button>
      {!manualPreview.can_run&&<p role="alert" className="text-red-700">Credit limit exceeded; reduce selected platforms.</p>}
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
   <h4 className="font-semibold">Campaign evidence</h4>
   <p className="text-xs text-slate-600">Only already-linked evidence is shown; viewing this page does not trigger SocialCrawl or spend credits.</p>
   {evidenceLoading&&<p role="status">Loading evidence…</p>}
   {evidenceError&&<p role="alert" className="text-red-700">{evidenceError}</p>}
   {!evidenceLoading&&!evidenceError&&!evidence.length&&<p className="text-sm text-slate-600">No evidence linked yet. Saving a campaign does not run paid collection.</p>}
   {evidence.map(item=><article key={item.id} className="rounded-lg border border-slate-200 p-3 space-y-1 text-sm"><p className="text-xs text-slate-600">{item.platform} · {item.author_name||'Unknown author'} · {item.published_at||'Date unavailable'}</p><p className="whitespace-pre-wrap break-words">{item.text_content||'No source text'}</p>{item.canonical_url&&item.canonical_url.startsWith('https://')&&<a href={item.canonical_url} target="_blank" rel="noopener noreferrer" className="underline">Open original source</a>}<div className="text-xs space-y-1">
     {Array.isArray(item.matched_fields)?<p className="text-slate-600">Legacy keyword-match metadata: {item.matched_fields.join(', ')||'Not recorded'}</p>:
      <div className="flex flex-wrap gap-2 items-center">
       <span className="font-semibold">Main matches:</span>{(item.matched_fields?.main_keywords||[]).length?item.matched_fields.main_keywords.map(k=><span key={k} className="rounded-full bg-cyan-50 px-2 py-1 text-cyan-900">{k}</span>):<span>Not recorded</span>}
       {(item.matched_fields?.secondary_keywords||[]).length>0&&<><span className="font-semibold">Context:</span>{item.matched_fields.secondary_keywords.map(k=><span key={k} className="rounded-full bg-amber-50 px-2 py-1 text-amber-900">{k}</span>)}</>}
      </div>}
    <p className="text-slate-500">Evidence match is a preliminary signal, not an assessed violation.</p></div></article>)}
   <p className="text-xs text-[#77899b]">Trend dashboards and AI classification will be enabled in subsequent builds.</p>
   <button type="button" className="intel-ghost" onClick={()=>{resetKeywordPreview();setSelected(null)}}>Close</button>
  </div>}
 </section>
}
