import { useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';
import CampaignScheduleSummary from '@/components/intel/CampaignScheduleSummary';
import KeywordTags from '@/components/intel/KeywordTags';

const options=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin','online_news'];
const initial={name:'',description:'',primary_keywords:[],secondary_keywords:[],excluded_keywords:'',platforms:['tiktok'],language:'',date_from:'',date_to:'',interval_minutes:180,province:'',regency_city:''};
const split=v=>String(v||'').split(',').map(s=>s.trim()).filter(Boolean);
const presentDate=v=>v?new Date(v).toLocaleString('en-GB'):'Not scheduled';
const displayStatus=s=>s==='PAUSED'?'Paused':'Draft';

export default function CampaignPanel(){
 const [campaigns,setCampaigns]=useState([]);
 const [loading,setLoading]=useState(true),[saving,setSaving]=useState(false);
 const [creating,setCreating]=useState(false),[editing,setEditing]=useState(null);
 const [form,setForm]=useState({...initial}),[selected,setSelected]=useState(null);
 const [query,setQuery]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [total,setTotal]=useState(0);
 const [statusFilter,setStatusFilter]=useState('all');
 const [evidence,setEvidence]=useState([]),[evidenceLoading,setEvidenceLoading]=useState(false),[evidenceError,setEvidenceError]=useState('');
 async function viewEvidence(c){
  setSelected(c);setEvidence([]);setEvidenceError('');setEvidenceLoading(true);
  try{const r=await base44.functions.invoke('socialListening',{action:'campaignEvidence',id:c.id,data:{}});setEvidence(r.data.evidence||[])}
  catch(e){setEvidenceError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setEvidenceLoading(false)}
 }
 const [creditEstimate,setCreditEstimate]=useState(null),[estimating,setEstimating]=useState(false),[estimateError,setEstimateError]=useState('');
 const clearEstimate=()=>{setCreditEstimate(null);setEstimateError('')};
 async function checkCredits(){
  setEstimating(true);setEstimateError('');setCreditEstimate(null);
  try{
   const r=await base44.functions.invoke('socialListening',{action:'campaignCostPreview',data:{
     ...form,primary_keywords:form.primary_keywords,
     secondary_keywords:form.secondary_keywords,excluded_keywords:split(form.excluded_keywords)
   }});
   setCreditEstimate(r.data);
  }catch(e){setEstimateError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setEstimating(false)}
 }

 const set=(key,value)=>{clearEstimate();setForm(x=>({...x,[key]:value}))};
 async function refresh(){
  try{
   const r=await base44.functions.invoke('socialListening',{action:'listCampaigns',data:{}});
   setCampaigns(r.data.campaigns||[]);setTotal(r.data.total||0);setError('');
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setLoading(false)}
 }
 useEffect(()=>{refresh()},[]);
 function newCampaign(){clearEstimate();setForm({...initial,platforms:['tiktok']});setEditing(null);setCreating(true);setSelected(null);setError('');setNotice('')}
 function editCampaign(c){
  clearEstimate();setForm({name:c.name,description:c.description||'',
   primary_keywords:[...(c.primary_keywords||[])],
   secondary_keywords:[...(c.secondary_keywords||[])],
   excluded_keywords:(c.excluded_keywords||[]).join(', '),
   platforms:[...(c.platforms||[])],language:c.language||'',date_from:c.date_from||'',date_to:c.date_to||'',
   interval_minutes:c.interval_minutes||180,province:c.province||'',regency_city:c.regency_city||''});
  setEditing(c);setCreating(true);setSelected(null);setError('');setNotice('');
 }
 async function save(e){
  e.preventDefault();setSaving(true);setError('');setNotice('');
  const data={...form,primary_keywords:form.primary_keywords,
   secondary_keywords:form.secondary_keywords,excluded_keywords:split(form.excluded_keywords)};
  try{
   const action=editing?'updateCampaign':'createCampaign';
   const r=await base44.functions.invoke('socialListening',{action,id:editing?.id,data});
   setNotice('Campaign saved as draft. Automatic paid crawls remain disabled until scheduling is approved.');
   setSelected(r.data.campaign);setCreating(false);setEditing(null);await refresh();
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
  <div className="intel-card p-5 space-y-3">
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
  </div>
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
    <label className="text-sm">End date<input className="intel-input mt-1" type="date" value={form.date_to} onChange={e=>set('date_to',e.target.value)}/></label>
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
      <p className="text-xs">Estimate, not a guaranteed final charge. Actual provider usage may differ.</p>
      <p className="text-xs">Scheduled paid crawling is disabled. This preview is not approval to run.</p>
    </div>}
   </div>
   <div className="flex gap-2"><button className="intel-button" disabled={saving||!form.primary_keywords.length}>{saving?'Saving…':'Save Draft'}</button>
    <button type="button" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>Cancel</button></div>
    </form>
   </div>
  </div>}
  {loading?<p className="intel-card p-4">Loading campaigns…</p>:<div className="intel-card overflow-x-auto"><table className="w-full text-left text-sm" aria-label="Campaign list"><thead className="bg-slate-50 text-xs uppercase text-slate-600"><tr><th className="p-3">Campaign</th><th className="p-3">Dates</th><th className="p-3">Status</th><th className="p-3">Evidence</th><th className="p-3">Actions</th></tr></thead><tbody>{visible.map(c=><tr key={c.id} className="border-t border-slate-100"><td className="p-3"><strong>{c.name}</strong><div className="text-xs text-slate-500">{(c.primary_keywords||[]).join(' · ')}</div></td><td className="p-3 text-xs">{c.date_from||'Any'} — {c.date_to||'Any'}</td><td className="p-3">{displayStatus(c.status)}</td><td className="p-3">{c.evidence_count}</td><td className="p-3"><div className="flex flex-wrap gap-2"><button type="button" className="intel-ghost" onClick={()=>viewEvidence(c)}>View Evidence</button><button type="button" className="intel-ghost" onClick={()=>editCampaign(c)}>Edit</button>{c.status==='DRAFT'&&<button type="button" className="intel-ghost" disabled={saving} onClick={()=>pause(c)}>Pause</button>}</div></td></tr>)}</tbody></table>{!visible.length&&<p className="p-4 text-sm">No campaigns match your filters.</p>}</div>}
  {selected&&!creating&&<div className="intel-card p-5 space-y-2">
   <h3 className="font-semibold">{selected.name} — Campaign Overview</h3>
   <p className="text-sm">Main keywords: {selected.primary_keywords.join(', ')}</p>
   <p className="text-sm">Secondary: {selected.secondary_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Excluded: {selected.excluded_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Collection runs: {selected.run_count} · Evidence records: {selected.evidence_count}</p>
   <CampaignScheduleSummary campaign={selected} />
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
   <button type="button" className="intel-ghost" onClick={()=>setSelected(null)}>Close</button>
  </div>}
 </section>
}
