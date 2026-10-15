import { useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';

const options=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin','online_news'];
const initial={name:'',description:'',primary_keywords:'',secondary_keywords:'',excluded_keywords:'',platforms:['tiktok'],language:'',date_from:'',date_to:'',interval_minutes:180,province:'',regency_city:''};
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
 const set=(key,value)=>setForm(x=>({...x,[key]:value}));
 async function refresh(){
  try{
   const r=await base44.functions.invoke('socialListening',{action:'listCampaigns',data:{}});
   setCampaigns(r.data.campaigns||[]);setTotal(r.data.total||0);setError('');
  }catch(e){setError(e.response?.data?.detail||e.response?.data?.error||e.message)}
  finally{setLoading(false)}
 }
 useEffect(()=>{refresh()},[]);
 function newCampaign(){setForm({...initial,platforms:['tiktok']});setEditing(null);setCreating(true);setSelected(null);setError('');setNotice('')}
 function editCampaign(c){
  setForm({name:c.name,description:c.description||'',
   primary_keywords:(c.primary_keywords||[]).join(', '),
   secondary_keywords:(c.secondary_keywords||[]).join(', '),
   excluded_keywords:(c.excluded_keywords||[]).join(', '),
   platforms:[...(c.platforms||[])],language:c.language||'',date_from:c.date_from||'',date_to:c.date_to||'',
   interval_minutes:c.interval_minutes||180,province:c.province||'',regency_city:c.regency_city||''});
  setEditing(c);setCreating(true);setSelected(null);setError('');setNotice('');
 }
 async function save(e){
  e.preventDefault();setSaving(true);setError('');setNotice('');
  const data={...form,primary_keywords:split(form.primary_keywords),
   secondary_keywords:split(form.secondary_keywords),excluded_keywords:split(form.excluded_keywords)};
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
 const visible=campaigns.filter(x=>(x.name+' '+x.description+' '+x.primary_keywords.join(' ')).toLowerCase().includes(query.toLowerCase()));
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
   <input className="intel-input" value={query} aria-label="Search campaigns" placeholder="Search campaigns" onChange={e=>setQuery(e.target.value)}/>
  </div>
  {error&&<p role="alert" className="intel-card p-3 text-red-700">{error}</p>}
  {notice&&<p role="status" className="intel-card p-3 text-green-700">{notice}</p>}
  {creating&&<form className="intel-card p-5 space-y-4" onSubmit={save} aria-label="Campaign editor">
   <h3 className="font-semibold">{editing?'Edit Campaign':'Create Campaign'}</h3>
   <div className="grid gap-3 md:grid-cols-2">
    <label className="text-sm">Campaign name *<input className="intel-input mt-1" value={form.name} maxLength={255} required onChange={e=>set('name',e.target.value)}/></label>
    <label className="text-sm">Language<select className="intel-input mt-1" value={form.language} onChange={e=>set('language',e.target.value)}>
       <option value="">All languages</option><option value="id">Bahasa Indonesia</option><option value="en">English</option><option value="ms">Bahasa Melayu</option>
    </select></label>
    <label className="text-sm">Main keywords * (comma-separated)<input className="intel-input mt-1" required value={form.primary_keywords} onChange={e=>set('primary_keywords',e.target.value)} placeholder="pemilu, gibran"/></label>
    <label className="text-sm">Secondary keywords<input className="intel-input mt-1" value={form.secondary_keywords} onChange={e=>set('secondary_keywords',e.target.value)} placeholder="wapres, kampanye"/></label>
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
   <div className="flex gap-2"><button className="intel-button" disabled={saving}>{saving?'Saving…':'Save Draft'}</button>
    <button type="button" className="intel-ghost" disabled={saving} onClick={()=>setCreating(false)}>Cancel</button></div>
  </form>}
  {loading?<p className="intel-card p-4">Loading campaigns…</p>:<div className="grid gap-3 md:grid-cols-2">
   {visible.map(c=><article className="intel-card p-5 space-y-3" key={c.id}>
    <div className="flex justify-between gap-2"><h3 className="font-semibold">{c.name}</h3><span className="text-xs text-[#77899b]">{displayStatus(c.status)}</span></div>
    <p className="text-sm text-[#77899b]">{c.description||'No description added'}</p>
    <p className="text-xs">Main keywords: {(c.primary_keywords||[]).join(', ')}</p>
    <p className="text-xs">Platforms: {(c.platforms||[]).join(', ')}</p>
    <p className="text-xs">Evidence: {c.evidence_count} · Runs: {c.run_count} · Last successful crawl: {presentDate(c.last_success_at)}</p>
    <div className="flex gap-2 flex-wrap"><button type="button" className="intel-ghost" onClick={()=>setSelected(c)}>View</button>
     <button type="button" className="intel-ghost" onClick={()=>editCampaign(c)}>Edit</button>
     {c.status==='DRAFT'&&<button type="button" className="intel-ghost" disabled={saving} onClick={()=>pause(c)}>Pause</button>}
    </div>
   </article>)}
   {!visible.length&&<p className="intel-card p-4 text-sm">No campaigns found. Create one to begin organizing monitoring.</p>}
  </div>}
  {selected&&!creating&&<div className="intel-card p-5 space-y-2">
   <h3 className="font-semibold">{selected.name} — Campaign Overview</h3>
   <p className="text-sm">Main keywords: {selected.primary_keywords.join(', ')}</p>
   <p className="text-sm">Secondary: {selected.secondary_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Excluded: {selected.excluded_keywords.join(', ')||'None'}</p>
   <p className="text-sm">Collection runs: {selected.run_count} · Evidence records: {selected.evidence_count}</p>
   <p className="text-xs text-[#77899b]">Trend dashboards, classification and scheduled crawling will be enabled in subsequent builds.</p>
   <button type="button" className="intel-ghost" onClick={()=>setSelected(null)}>Close</button>
  </div>}
 </section>
}
