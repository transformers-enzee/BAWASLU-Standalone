import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Clock3, Globe2, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import ProvinceHeatmap from '@/components/intel/ProvinceHeatmap';

const fmtTime=value=>{if(!value)return 'Not available';const d=new Date(value);return Number.isNaN(d.getTime())?'Not available':d.toLocaleString('en-GB')};
const fmtNumber=value=>typeof value==='number'?value.toLocaleString():'Not available';
const evidenceLink=row=>'/inbox?campaign_id='+encodeURIComponent(row.campaign_id)+'&result_id='+encodeURIComponent(row.result_id);
const day=(offset=0)=>{const d=new Date();d.setDate(d.getDate()+offset);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
const cleanSource=url=>{try{const x=new URL(url);return ['https:','http:'].includes(x.protocol)?x.href:null}catch{return null}};

function Panel({title,subtitle,children,to,action='View all'}){
 return <section className="intel-card p-4 md:p-5 space-y-3 min-w-0">
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
   <span>{fmtTime(alert?record.detected_at:record.published_at)}</span>
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
 const canNational=access?.geographic_scope==='Nationwide';
 const regions=data?.regions||[];
 const regionalDistribution=regions.map(x=>({...x,percentage:data?.indicators?.relevant_mentions?100*x.count/data.indicators.relevant_mentions:0}));
 const statusDescription=data?.coverage?.warning;
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
    <select className="intel-input mt-1 w-full" value={period} onChange={e=>setPeriod(e.target.value)}><option value="today">Today (UTC)</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option><option value="custom">Custom dates</option></select>
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
   <Panel title="Executive Intelligence Briefing" subtitle={'Based on stored assessments · '+data.period.date_from+' to '+data.period.date_to}>
    <div className="flex gap-3">
     <Sparkles size={18} className="shrink-0 text-[#126d91] mt-0.5"/>
     <div className="space-y-3 min-w-0">
      <p className="text-sm leading-6 text-[#283f52]">{data.briefing.text}</p>
      <p className="text-[11px] text-slate-500">{data.briefing.limitation}</p>
      <div className="flex flex-wrap items-center gap-3">
       {(data.briefing.sources||[]).map((x,i)=><Link key={x.campaign_id+'-'+x.result_id} to={evidenceLink(x)} className="text-xs text-[#126d91] font-semibold">Supporting record {i+1} ↗</Link>)}
       {data.briefing.kind==='DATA_COVERAGE_NOTICE'&&<Link to="/social-listening" className="text-xs text-[#126d91] font-semibold">Explore collected evidence ↗</Link>}
      </div>
     </div>
    </div>
   </Panel>
   <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 md:gap-3" aria-label="Intelligence indicators">
    <Stat label="Relevant mentions" value={metrics.relevant_mentions} description="Distinct AI-assessed posts" to="/inbox"/>
    <Stat label="Potential issue alerts" value={metrics.potential_alerts} description="Preliminary, not confirmed" to="/inbox"/>
    <Stat label="Awaiting BAWASLU review" value={metrics.awaiting_review} description="Requires human assessment" to="/inbox"/>
    <Stat label="Emerging issues" value={metrics.emerging_issues} description="Clustering not yet enabled" to="/social-listening"/>
   </div>
   <div className="grid xl:grid-cols-[1.35fr_1fr] gap-3 md:gap-4">
    <Panel title="Needs BAWASLU Attention" subtitle="Prioritized preliminary indicators from actual assessed evidence" to="/inbox" action="Open Intelligence Inbox">
     {(data.alerts||[]).length?data.alerts.map(row=><MiniRecord key={row.result_id} record={row} alert/>):<p className="text-sm text-slate-500 py-3">No undismissed evidence-backed issue alerts were found in the selected period. This does not establish that no violations occurred.</p>}
    </Panel>
    <Panel title="Latest Intelligence" subtitle="Most recently published posts with relevant AI assessments" to="/inbox">
     {(data.latest_intelligence||[]).length?data.latest_intelligence.map(row=><MiniRecord key={row.result_id} record={row}/>):<p className="text-sm text-slate-500 py-3">No assessed relevant intelligence is available for this period and geographic scope.</p>}
    </Panel>
   </div>
   <div className="grid xl:grid-cols-[1.2fr_1fr] gap-3 md:gap-4">
    <Panel title="Regional Intelligence Overview" subtitle="Categorized by campaign monitoring scope—not confirmed post origin" to="/social-listening">
     {regions.length?<div className="space-y-2">
      <div className="overflow-x-auto"><table className="text-sm w-full"><thead><tr className="text-[11px] text-slate-500 text-left border-b"><th className="py-2">Province</th><th className="py-2 text-right">Relevant posts</th><th className="py-2 text-right">Issue alerts</th></tr></thead><tbody>{regions.slice(0,8).map(r=><tr key={r.province_code} className="border-b last:border-b-0 border-slate-100"><td className="py-2">{canNational?<button type="button" className="text-[#126d91] hover:underline" onClick={()=>setProvince(r.province)}>{r.province}</button>:r.province}</td><td className="py-2 text-right tabular-nums">{fmtNumber(r.count)}</td><td className="py-2 text-right tabular-nums">{fmtNumber(r.flagged)}</td></tr>)}</tbody></table></div>
      <details className="text-xs text-[#126d91]"><summary className="cursor-pointer font-semibold">View province map</summary><div className="mt-2"><ProvinceHeatmap distribution={regionalDistribution} totalPosts={metrics.relevant_mentions||0} title="Campaign monitoring coverage" subtitle="AI-assessed posts by campaign target province" footnote="Shading is based on campaign monitoring coverage, not post origin or proven electoral risk. Campaigns may overlap. Unknown / unclassified records are omitted from the map."/></div></details>
     </div>:<p className="text-sm text-slate-500 py-2">No reliable campaign-scoped province breakdown is available for the selected period.</p>}
     <p className="text-xs text-slate-500">{fmtNumber(data.unknown_region_mentions)} relevant post(s) associated with campaigns without a classified monitoring province. No inferred publisher locations are displayed.</p>
    </Panel>
    <Panel title="Watchlist Highlights" subtitle="Registered entities and their captured account activity" to="/watchlist" action="View full Watchlist">
     {(data.watchlist?.entries||[]).length?data.watchlist.entries.map(x=><article key={x.watchlist_id} className="border-b border-slate-100 last:border-0 py-2.5 first:pt-0 space-y-1">
      <div className="flex justify-between gap-2"><p className="font-semibold text-sm">{x.name}</p><span className="text-[11px] text-slate-500">{x.platform}</span></div>
      <p className="text-xs text-slate-600 line-clamp-2">{x.summary||'Post text unavailable'}</p>
      <p className="text-[11px] text-slate-500">{x.province} · {fmtTime(x.last_post_at)}</p>
      <Link className="text-xs text-[#126d91] font-semibold" to={'/watchlist/'+x.watchlist_id+'/posts'}>View captured account posts →</Link>
     </article>):<div className="text-sm text-slate-500 py-2 space-y-2"><p>No matching posts from registered Watchlist accounts were captured in this period.</p><p>{fmtNumber(data.watchlist?.monitored_profiles)} profiles are visible in your authorized scope. Registered accounts do not imply successful collection.</p></div>}
    </Panel>
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
