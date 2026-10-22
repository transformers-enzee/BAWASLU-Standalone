import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Clock3, Globe2, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import ProvinceHeatmap from '@/components/intel/ProvinceHeatmap';

const fmtTime=value=>{if(!value)return 'Not available';const d=new Date(value);return Number.isNaN(d.getTime())?'Not available':d.toLocaleString('en-GB')};
const fmtNumber=value=>typeof value==='number'?value.toLocaleString():'Not available';
const evidenceLink=row=>row.record_type==='INTELLIGENCE_ITEM'
 ? '/intelligence/'+encodeURIComponent(row.id)
 : '/inbox?campaign_id='+encodeURIComponent(row.campaign_id)+'&result_id='+encodeURIComponent(row.result_id);
const day=(offset=0)=>{const d=new Date();d.setDate(d.getDate()+offset);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
const cleanSource=url=>{try{const x=new URL(url);return ['https:','http:'].includes(x.protocol)?x.href:null}catch{return null}};

function Panel({title,subtitle,children,to,action='View all',fillHeight=false}){
 return <section className={"intel-card p-4 md:p-5 space-y-3 min-w-0 "+(fillHeight?"h-full":"")}>
  <div className="flex flex-wrap items-start justify-between gap-2">
   <div><h2 className="text-base font-semibold text-[#173952]">{title}</h2>{subtitle&&<p className="text-xs text-slate-500 mt-1">{subtitle}</p>}</div>
   {to&&<Link to={to} className="text-xs font-semibold text-[#126d91] inline-flex items-center gap-1 hover:underline">{action}<ArrowUpRight size={13}/></Link>}
  </div>
  {children}
 </section>
}
function Stat({label,value,description,to}){
 return <Link to={to} className="intel-card px-3 py-3 md:px-4 md:py-4 min-w-0 hover:border-sky-300 transition-colors">
  <p className="text-xs text-[#607788] leading-snug min-h-[30px]">{label}</p>
  <p className="text-2xl md:text-3xl font-semibold tracking-tight tabular-nums text-[#173952] mt-1">{fmtNumber(value)}</p>
  <p className="text-[11px] text-slate-500 mt-1">{description}</p>
 </Link>
}
function MiniRecord({record,alert=false}){
 return <article className="border-t first:border-t-0 border-slate-100 py-3 first:pt-0 last:pb-0 space-y-1.5">
  <div className="flex flex-wrap gap-2 justify-between items-start">
   <p className="text-xs font-semibold text-[#173952]">{alert?record.category:record.campaign_name}</p>
   {alert&&<span className={'text-[10px] font-semibold rounded-full px-2 py-1 '+(record.review_status==='FURTHER_INVESTIGATION'?'bg-amber-100 text-amber-900':'bg-slate-100 text-slate-600')}>{record.review_status==='AWAITING_REVIEW'?'Awaiting human review':record.review_status==='FURTHER_INVESTIGATION'?'Further investigation':'Human flag retained'}</span>}
  </div>
  <p className="text-sm text-slate-700 line-clamp-2">{alert?(record.description||record.evidence_quote):record.summary||'AI assessment contains no written explanation.'}</p>
  <div className="text-[11px] text-slate-500 flex flex-wrap gap-x-3 gap-y-1">
   <span>{record.platform||'Unknown platform'}</span>
   <span>{record.author||'Unclassified author'}</span>
   {alert&&<span>{record.province} <span className="text-slate-400">(campaign scope)</span></span>}
   <span>{fmtTime(alert?record.detected_at:record.published_at)}{record.date_basis==='RECORD_CREATED'?' (recorded)':''}</span>
  </div>
  <div className="flex flex-wrap items-center gap-3">
   <Link to={evidenceLink(record)} className="text-xs font-semibold text-[#126d91] hover:underline">Open evidence in Inbox <ArrowUpRight size={12} className="inline"/></Link>
   {cleanSource(record.source_url)&&<a href={cleanSource(record.source_url)} target="_blank" rel="noopener noreferrer" className="text-xs text-slate-600 hover:underline">Original source ↗</a>}
  </div>
 </article>;
}

export default function Home(){
 const {access}=useOutletContext();
 const navigate=useNavigate();
 const [period,setPeriod]=useState('7d'),[dateFrom,setDateFrom]=useState(day(-6)),[dateTo,setDateTo]=useState(day());
 const [province,setProvince]=useState('');
 const [version,setVersion]=useState(0),[data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [question,setQuestion]=useState('');
 const [mapSource,setMapSource]=useState('social');
 const effectiveProvince=data?.scope?.can_select_national?province:'';
 const params=useMemo(()=>({period,province:effectiveProvince,...(period==='custom'?{date_from:dateFrom,date_to:dateTo}:{})}),[period,effectiveProvince,dateFrom,dateTo]);
 useEffect(()=>{
  let live=true;
  setLoading(true);setError('');
  base44.functions.invoke('commandCenter',params)
   .then(res=>{if(live)setData(res.data)})
   .catch(err=>{if(live){setError(err.response?.data?.error||err.message||'Command Center unavailable');setData(null)}})
   .finally(()=>{if(live)setLoading(false)});
  return()=>{live=false};
 },[params,version]);
 const metrics=data?.indicators||{};
 const activity=data?.activity||{};
 const trend=(activity.daily||[]).slice(-14);
 const trendMax=Math.max(1,...trend.map(x=>Number(x.count)||0));
 const canNational=access?.geographic_scope==='Nationwide';
 const statusDescription=data?.coverage?.warning;
 const effectiveMapSource=mapSource==='auto'?(data?.regional_intelligence?.length?'recorded':data?.regional_monitoring_coverage?.length?'coverage':data?.regional_inbox_signals?.length?'social':'recorded'):mapSource;
 return <div className="space-y-4 md:space-y-5" aria-label="BAWASLU Intelligence Command Center">
  <div className="flex flex-wrap gap-3 items-start justify-between">
   <div>
    <p className="text-[11px] uppercase tracking-[.18em] font-bold text-[#9a7e49]">Executive intelligence overview</p>
    <h1 className="intel-heading mt-1">Intelligence Command Center</h1>
    <p className="text-xs text-slate-500 mt-1">What is happening · What needs attention · Where to investigate</p>
   </div>
   <button type="button" onClick={()=>setVersion(x=>x+1)} disabled={loading} className="intel-ghost text-xs flex gap-2 items-center"><RefreshCw size={14}/> Refresh briefing</button>
  </div>
  <section className="intel-card p-3 flex flex-wrap gap-3 items-end" aria-label="Dashboard-wide filters">
   <label className="block text-xs min-w-[125px] flex-1"><span className="font-semibold text-slate-600">Monitoring period</span>
    <select className="intel-input mt-1 w-full" value={period} onChange={e=>setPeriod(e.target.value)}><option value="today">Today (UTC)</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option><option value="all">All dates</option><option value="custom">Custom dates</option></select>
   </label>
   {period==='custom'&&<><label className="block text-xs"><span>From (UTC)</span><input type="date" max={dateTo} className="intel-input mt-1" value={dateFrom} onChange={e=>setDateFrom(e.target.value)}/></label><label className="block text-xs"><span>To (UTC)</span><input type="date" min={dateFrom} max={day()} className="intel-input mt-1" value={dateTo} onChange={e=>setDateTo(e.target.value)}/></label></>}
   <label className="block text-xs min-w-[165px] flex-1"><span className="font-semibold text-slate-600">Geographic coverage</span>
    <select className="intel-input mt-1 w-full" value={canNational?province:''} disabled={!canNational||!data} onChange={e=>setProvince(e.target.value)}>
     <option value="">{canNational?'National · Indonesia':data?.scope?.label||'Your assigned region'}</option>
     {canNational&&(data?.available_provinces||[]).map(x=><option key={x.code} value={x.name}>{x.name}</option>)}
    </select>
   </label>
   <div className="text-[11px] text-slate-500 min-w-0"><p><Globe2 className="inline mr-1" size={12}/> {data?.scope?.label||'Authorized coverage'}</p><p className="mt-1"><Clock3 className="inline mr-1" size={12}/> Updated {fmtTime(data?.generated_at)}</p></div>
  </section>
  {error&&<div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"><strong>Unable to load intelligence overview.</strong><p className="mt-1">{error}</p><button className="mt-2 underline" onClick={()=>setVersion(x=>x+1)}>Retry</button></div>}
  {loading&&<div role="status" className="intel-card p-8 text-sm text-slate-500">Loading authorized intelligence and monitoring coverage…</div>}
  {!loading&&data&&<>
   <Panel title={'Executive Situation Briefing · '+data.scope.label} subtitle={'Location-specific monitoring · '+data.period.date_from+' to '+data.period.date_to}>
    <div className="grid lg:grid-cols-[1.35fr_1fr] gap-4">
     <div className="space-y-3">
      <div className="flex gap-3">
       <Sparkles size={18} className="shrink-0 text-[#126d91] mt-0.5"/>
       <div className="min-w-0">
        <p className="text-sm leading-6 text-[#283f52]">{data.briefing.text}</p>
        <p className="text-[11px] text-slate-500 mt-2">{data.briefing.limitation}</p>
       </div>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
       {(data.briefing.sources||[]).map((x,i)=><Link key={x.campaign_id+'-'+x.result_id} to={evidenceLink(x)} className="text-xs text-[#126d91] font-semibold">Supporting record {i+1} ↗</Link>)}
       {data.briefing.kind==='DATA_COVERAGE_NOTICE'&&<Link to="/social-listening" className="text-xs text-[#126d91] font-semibold">Explore captured evidence ↗</Link>}
      </div>
     </div>
     <section className="rounded-lg bg-[#f4f7fa] p-3 md:p-4 space-y-3" aria-label="BAWASLU representative review actions">
      <div>
       <h3 className="text-sm font-semibold text-[#173952]">For BAWASLU Representative</h3>
       <p className="text-xs text-slate-500 mt-1">Preliminary indicators and evidence work requiring review</p>
      </div>
      {(data.attention_actions||[]).length?(data.attention_actions||[]).map((x,i)=><div key={x.kind+'-'+i} className="bg-white rounded-md border border-[#e0e8ee] p-3 space-y-1.5">
       <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold text-[#263e51]">{x.title}</p>
        <span className="text-[10px] shrink-0 text-amber-800">{x.kind==='POTENTIAL_ISSUE'?'Preliminary alert':'Data coverage'}</span>
       </div>
       <p className="text-xs text-slate-600 line-clamp-2">{x.description}</p>
       <p className="text-[11px] text-slate-500">{x.recommended_action}</p>
       <Link to={x.kind==='POTENTIAL_ISSUE'?evidenceLink(x):'/social-listening'} className="inline-block text-xs font-semibold text-[#126d91]">Review supporting evidence →</Link>
      </div>):<p className="text-xs text-slate-600">No outstanding preliminary issue alerts or unassessed captured campaign posts were identified for the selected period. This is not a determination that no violations occurred.</p>}
      <Link to="/inbox" className="text-xs font-semibold text-[#126d91] inline-block">Open Intelligence Inbox →</Link>
     </section>
    </div>
   </Panel>
   <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 md:gap-3" aria-label="Intelligence indicators">
    <Stat label="Published social posts" value={activity.captured_mentions} description="Source publication in selected period" to="/social-listening"/>
    <Stat label="Newly collected posts" value={activity.newly_collected_mentions} description="Added to Social Listening in period" to="/social-listening"/>
    <Stat label="Relevant assessed posts" value={metrics.relevant_mentions} description="AI-assessed as relevant" to="/inbox"/>
    <Stat label="Potential issue alerts" value={metrics.potential_alerts} description="Preliminary, not confirmed" to="/inbox"/>
    <Stat label="Awaiting BAWASLU review" value={metrics.awaiting_review} description="Human assessment required" to="/inbox"/>
   </div>
   <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#e1e8ee] bg-[#f6f9fb] px-3 py-2 text-xs text-[#52697d]" role="note">
    <span><strong>Assessment coverage:</strong> {fmtNumber(data.coverage?.assessed_posts_in_period)} of {fmtNumber(data.coverage?.captured_posts_in_period)} campaign-linked posts <strong>published</strong> in this period have an AI assessment. {Number(data.coverage?.unassessed_posts_in_period||0)>0?'Unassessed does not mean no risk.':''}</span>
    <Link to="/social-listening" className="text-[#126d91] font-semibold hover:underline">Explore captured posts →</Link>
   </div>
   <div className="grid xl:grid-cols-[1.35fr_1fr] gap-3 md:gap-4 items-stretch">
    <Panel fillHeight title="Needs BAWASLU Attention" subtitle="Most recent undismissed preliminary issue signals from saved AI assessments · all dates" to="/inbox" action="Open Intelligence Inbox">
     {(data.alerts||[]).length?data.alerts.map(row=><MiniRecord key={row.result_id} record={row} alert/>):<p className="text-sm text-slate-500 py-3">No undismissed evidence-backed issue alerts were found in the selected period. This does not establish that no violations occurred.</p>}
    </Panel>
    <Panel fillHeight title="Latest Intelligence" subtitle="Latest saved AI-assessed posts and recorded Inbox items · all dates" to="/inbox">
     {(data.latest_intelligence||[]).length?data.latest_intelligence.slice(0,3).map(row=><MiniRecord key={row.record_type==='INTELLIGENCE_ITEM'?'intel-'+row.id:row.result_id} record={row}/>):<p className="text-sm text-slate-500 py-3">No assessed relevant intelligence is available for this period and geographic scope.</p>}
    </Panel>
   </div>
   <div className="grid xl:grid-cols-2 gap-3 md:gap-4 items-stretch">
    <Panel fillHeight title="Captured Social Activity" subtitle="Published-post activity · selected monitoring period" to="/social-listening" action="Open Social Listening">
     <div className="flex flex-wrap gap-3 text-xs text-slate-600"><span><strong>{fmtNumber(activity.captured_mentions)}</strong> published in period</span><span><strong>{fmtNumber(activity.newly_collected_mentions)}</strong> newly collected</span></div>
     <div className="flex h-28 items-end gap-1 rounded-lg bg-slate-50 px-3 py-2" aria-label="Captured social activity daily trend">
      {trend.length?trend.map((point,i)=><div key={i} className="flex-1 min-w-0 rounded-t bg-[#4384a3]" style={{height:Math.max(3,Math.round(100*(Number(point.count)||0)/trendMax))+'%'}} title={String(point.date||'')+': '+(point.count||0)+' posts'}/>):<span className="text-xs text-slate-500">No daily activity recorded</span>}
     </div>
     <p className="text-xs font-semibold text-slate-600">Top platforms</p>
     <div className="flex flex-wrap gap-2 text-xs">{(activity.top_platforms||[]).length?activity.top_platforms.slice(0,4).map(p=><span key={p.platform} className="rounded-full bg-slate-100 px-2 py-1">{p.platform} · {p.count}</span>):<span className="text-slate-500">No platform activity in this period</span>}</div>
     <p className="text-xs font-semibold text-slate-600">Recent captured evidence</p>
     {(activity.recent_captured||[]).slice(0,3).map(post=><article key={post.result_id} className="border-t border-slate-100 py-2 text-xs">
      <div className="flex justify-between gap-2"><strong>{post.platform}</strong><span className="text-slate-500">{fmtTime(post.published_at)}</span></div>
      <p className="mt-1 line-clamp-2">{post.preview||'No source text available'}</p>
      {cleanSource(post.source_url)&&<a className="text-[#126d91]" href={cleanSource(post.source_url)} target="_blank" rel="noopener noreferrer">Original post ↗</a>}
     </article>)}
    </Panel>
    <Panel fillHeight title="Regional Intelligence Overview" subtitle={effectiveMapSource==='social'?'Social Evidence Inbox · all-time authorized AI geographic signals':effectiveMapSource==='coverage'?'Social Listening · campaign monitoring coverage':'Recorded Intelligence Inbox · all-time authorized jurisdiction inventory'} to="/inbox" action="Open Intelligence Inbox">
     <div className="flex gap-2 text-xs" aria-label="Regional map data source">
      <button type="button" onClick={()=>setMapSource('social')} aria-pressed={effectiveMapSource==='social'} className={effectiveMapSource==='social'?'intel-button text-xs':'intel-ghost text-xs'}>Assessed social evidence</button>
      <button type="button" onClick={()=>setMapSource('coverage')} aria-pressed={effectiveMapSource==='coverage'} className={effectiveMapSource==='coverage'?'intel-button text-xs':'intel-ghost text-xs'}>Campaign coverage</button>
      <button type="button" onClick={()=>setMapSource('recorded')} aria-pressed={effectiveMapSource==='recorded'} className={effectiveMapSource==='recorded'?'intel-button text-xs':'intel-ghost text-xs'}>Recorded intelligence</button>
     </div>
     {effectiveMapSource==='coverage'&&!(data.regional_monitoring_coverage||[]).length&&<p role="note" className="text-xs text-amber-800">No selected campaigns have a provincial monitoring assignment in this period. National and unassigned posts cannot be placed on a province map. Choose Recorded intelligence to view known jurisdictions.</p>}
     {(()=>{const rows=effectiveMapSource==='social'?(data.regional_inbox_signals||[]):effectiveMapSource==='coverage'?(data.regional_monitoring_coverage||[]):(data.regional_intelligence||[]);const total=rows.reduce((n,x)=>n+Number(x.records||0),0);const mapped=rows.map(x=>({province:x.province,province_code:x.province_code,count:x.records,percentage:total?Number(x.records||0)*100/total:0}));return <div className="space-y-3">
      <p className="text-xs text-slate-600">{total} province-associated {effectiveMapSource==='social'?'AI-assessed social post signal(s) from all saved assessments':effectiveMapSource==='coverage'?'captured posts linked to region-scoped campaigns in the period':'recorded intelligence association(s), all time'} across {rows.length} province(s). Separate sources are never added together or treated as confirmed violation locations.</p>
      <div className="max-w-[720px] mx-auto"><ProvinceHeatmap distribution={mapped} totalPosts={total} unit="intelligence records" title="Indonesia · Intelligence distribution" subtitle={effectiveMapSource==='social'?'AI assessment geographic signals · all dates':effectiveMapSource==='coverage'?'Campaign monitoring jurisdiction · selected period':'Recorded intelligence geographic associations · all time'} footnote={effectiveMapSource==='social'?'Based on AI assessment location signals. Counts are source associations, not verified incident locations.':effectiveMapSource==='coverage'?'Based on campaign monitoring province, not verified source location or incident location. Nationwide campaigns have no provincial assignment.':'Based on authorized recorded intelligence jurisdictions and explicit place references. Some jurisdictions are unconfirmed; counts are associations, not verified incident locations.'}/></div>
      {!rows.length&&<p className="text-xs text-slate-500">No {effectiveMapSource==='social'?'assessed posts with recognized provincial location signals in this period':effectiveMapSource==='coverage'?'captured posts linked to province-scoped campaigns':'recorded intelligence with recognized provincial associations'}. This does not imply the area has no monitored activity.</p>}
     </div>})()}
    </Panel>
   </div>
   <div className="grid xl:grid-cols-2 gap-3 md:gap-4 items-stretch">
    <Panel fillHeight title="Watchlist Highlights" subtitle="Registered entities and their captured account activity" to="/watchlist" action="View full Watchlist">
     {(data.watchlist?.entries||[]).length?data.watchlist.entries.slice(0,3).map(x=><article key={x.watchlist_id} className="border-b border-slate-100 last:border-0 py-2.5 first:pt-0 space-y-1">
      <div className="flex justify-between gap-2"><p className="font-semibold text-sm">{x.name}</p><span className="text-[11px] text-slate-500">{x.platform}</span></div>
      <p className="text-xs text-slate-600 line-clamp-2">{x.summary||'Post text unavailable'}</p>
      <p className="text-[11px] text-slate-500">{x.province} · {fmtTime(x.last_post_at)}</p>
      <Link className="text-xs text-[#126d91] font-semibold" to={'/watchlist/'+x.watchlist_id+'/posts'}>View captured account posts →</Link>
     </article>):<div className="text-sm text-slate-500 py-2 space-y-2"><p>No matching posts from registered Watchlist accounts were captured in this period.</p><p>{fmtNumber(data.watchlist?.monitored_profiles)} profiles are visible in your authorized scope. Registered accounts do not imply successful collection.</p></div>}
    </Panel>
   
    <Panel fillHeight title="Channel Distribution" subtitle="Captured posts by social platform · selected publication period" to="/social-listening" action="View Social Listening">
     {(activity.top_platforms||[]).length?<div className="space-y-3">
      {(activity.top_platforms||[]).slice(0,5).map(channel=><div key={channel.platform} className="space-y-1">
       <div className="flex justify-between gap-3 text-xs"><span className="font-semibold text-[#173952]">{channel.platform}</span><span className="tabular-nums text-slate-600">{fmtNumber(channel.count)} · {activity.captured_mentions?Math.round(100*channel.count/activity.captured_mentions):0}%</span></div>
       <div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-[#4384a3] rounded-full" style={{width:(activity.captured_mentions?Math.min(100,100*channel.count/activity.captured_mentions):0)+'%'}}/></div>
      </div>)}
      <p className="text-xs text-slate-500">Platform shares use captured posts published in the selected period. They do not indicate confirmed violations.</p>
     </div>:<p className="text-sm text-slate-500 py-3">No captured social platform data for this period.</p>}
    </Panel>
   </div>
   <div className="rounded-lg border border-[#e1e8ee] bg-[#f6f9fb] px-3 py-2 text-xs text-[#52697d] flex flex-wrap justify-between gap-2" aria-label="Review workload summary">
    <span><strong>Review workload:</strong> {fmtNumber(metrics.awaiting_review)} awaiting human review · {fmtNumber(metrics.potential_alerts)} preliminary issue alerts · {fmtNumber(data.coverage?.unassessed_posts_in_period)} published posts awaiting assessment</span>
    <Link to="/inbox" className="text-[#126d91] font-semibold">Open Intelligence Inbox →</Link>
   </div>
   <Panel title="AI Assistant · Quick Investigation" subtitle="Ask questions grounded in authorized system records" to="/assistant" action="Open full assistant">
    <form onSubmit={e=>{e.preventDefault();if(question.trim())navigate('/assistant?q='+encodeURIComponent(question.trim()))}} className="flex flex-col sm:flex-row gap-2">
     <input className="intel-input flex-1 min-w-0" maxLength={400} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about recent evidence or pending intelligence…" aria-label="Question for Intelligence Assistant"/>
     <button type="submit" className="intel-button" disabled={!question.trim()}>Investigate <ArrowRight size={14}/></button>
    </form>
    <div className="flex flex-wrap gap-2 text-xs">{['What are the latest validated records?','What important evidence needs review?'].map(q=><Link key={q} className="intel-ghost text-xs" to={'/assistant?q='+encodeURIComponent(q)}>{q}</Link>)}</div>
    <p className="text-[11px] text-slate-500">Current Assistant covers accessible intelligence records; comprehensive cross-module synthesis is planned. It does not determine legal violations.</p>
   </Panel>
   <div className="flex items-start gap-2 text-[11px] text-slate-500 px-1">
    <ShieldCheck size={15} className="shrink-0 mt-0.5"/><div><p>{statusDescription}</p><p className="mt-1">Most recently collected assessed evidence: {fmtTime(data.latest_evidence_at)}. Identified signals and regional monitoring coverage are not conclusions of electoral misconduct. All findings require BAWASLU review.</p></div>
   </div>
  </>}
 </div>;
}
