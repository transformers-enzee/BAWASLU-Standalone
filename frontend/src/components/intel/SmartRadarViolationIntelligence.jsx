import { useEffect, useMemo, useState } from 'react';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import ActionIntelligencePanel from '@/components/intel/ActionIntelligencePanel';

/** Only visible to active view_intelligence users inside AccessGate.
 * The server enforces access scope for every request. No paid AI calls,
 * officer actions, province claims or cached cross-account data.
 */
export default function SmartRadarViolationIntelligence({access}){
  const [period,setPeriod]=useState('30d');
  const [province,setProvince]=useState('');
  const [reload,setReload]=useState(0);
  const [model,setModel]=useState(null);
  const [provinces,setProvinces]=useState([]);
  const [scope,setScope]=useState(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const national=access?.geographic_scope==='Nationwide';
  const filters=useMemo(()=>({period,province:national?province:''}),[period,province,national]);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError('');setModel(null);
    base44.functions.invoke('commandCenter',filters)
      .then(result=>{
        if(!active)return;
        const data=result.data||{};
        setModel(data.action_intelligence||null);
        setProvinces(data.available_provinces||[]);
        setScope(data.scope||null);
      })
      .catch(err=>{if(active)setError(err.response?.data?.error||err.message||'Unable to read authorized intelligence');})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false};
  },[filters,reload,access?.id,access?.province,access?.geographic_scope]);
  return <div className="p-4 md:p-7 space-y-4 bg-[#faf9f8] min-h-[65vh]" aria-label="Violation Intelligence workspace">
    <header className="rounded-xl bg-[#912d36] text-white p-5 md:p-7">
      <p className="text-[11px] tracking-[.18em] uppercase font-bold text-[#f9dde0]">BAWASLU · Action Intelligence</p>
      <h1 className="text-2xl md:text-3xl font-bold mt-2">Violation Intelligence</h1>
      <p className="text-sm text-[#fff0f1] mt-2">1. Violation Type · 2. Geographical Impact · 3. Recommended Action</p>
      <p className="text-xs mt-3 text-[#f6dcde]">Read-only evidence review for authorized HQ and provincial officers. AI flags are not official legal findings.</p>
    </header>
    <div className="intel-card p-4 flex flex-wrap gap-3 items-end" aria-label="Violation Intelligence filters">
      <label className="text-xs font-semibold text-[#40586b] min-w-[160px]">Reporting period
        <select className="intel-input mt-1 w-full" value={period} onChange={event=>setPeriod(event.target.value)}>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="all">All historical dates</option>
        </select>
      </label>
      <label className="text-xs font-semibold text-[#40586b] min-w-[200px] flex-1">Authorized geography
        <select className="intel-input mt-1 w-full" disabled={!national||loading} value={national?province:''} onChange={event=>setProvince(event.target.value)}>
          <option value="">{national?'National · Indonesia':scope?.label||access?.province||'Assigned region'}</option>
          {national&&provinces.map(item=><option value={item.name} key={item.code}>{item.name}</option>)}
        </select>
      </label>
      <button type="button" className="intel-ghost flex items-center gap-2 text-xs" onClick={()=>setReload(x=>x+1)} disabled={loading}><RefreshCw size={14}/> Refresh</button>
      <p className="text-xs text-[#607486] flex items-center gap-1"><ShieldCheck size={15}/> {scope?.label||'Access-controlled results'}</p>
    </div>
    {loading?<div role="status" className="intel-card p-6 text-sm text-slate-600">Loading authorized violation review candidates…</div>:error?<div role="alert" className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-800">Violation Intelligence is unavailable: {error}</div>:<ActionIntelligencePanel model={model}/>}
    <p className="text-xs text-slate-500">Source classifications and geographical review scopes are preliminary. No violation, incident location, provincial assignment, or formal case is established by the dashboard.</p>
  </div>;
}
