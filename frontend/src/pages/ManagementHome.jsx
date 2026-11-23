import {useEffect,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {FileText,ShieldCheck,AlertTriangle,Search,ArrowRight} from 'lucide-react';

const number=value=>Number(value||0).toLocaleString('en-GB');
const safeDate=value=>value?new Date(value).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'}):'—';

export default function ManagementHome(){
 const {access}=useOutletContext()||{};
 const [period,setPeriod]=useState('weekly'),[snapshot,setSnapshot]=useState(null);
 const [error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{
  let active=true;const controller=new AbortController();
  setLoading(true);setError('');
  const token=window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':window.localStorage.getItem('bawaslu_access_token')||'';
  fetch('/api/management-reporting/briefing?period='+encodeURIComponent(period)+'&language=id',{
   headers:{Authorization:'Bearer '+token},cache:'no-store',signal:controller.signal
  }).then(async response=>{
   if(!response.ok)throw Error(response.status===401?'Session expired. Please sign in again.':'Management brief unavailable ('+response.status+').');
   return response.json();
  }).then(data=>{if(active)setSnapshot(data)}).catch(e=>{if(active&&e.name!=='AbortError')setError(e.message)})
   .finally(()=>{if(active)setLoading(false)});
  return()=>{active=false;controller.abort()};
 },[period]);
 const metrics=snapshot?.metrics||{},consistency=snapshot?.management_consistency||{},
  queue=snapshot?.followup_queue||{},quality=snapshot?.casework_progress||{};
 const cases=snapshot?.recent_cases||[];
 const missing=Number(metrics.assignments_without_reports||0);
 const issue=Number(queue.attention_count??consistency.followup_attention_count??0);
 const scope=snapshot?.scope?.geographic_scope==='Province'?
  'Authorized province: '+(snapshot?.scope?.province||'Unspecified'):
  'Authorized national scope';
 return <div className="mx-auto max-w-[1250px] space-y-6" data-testid="management-workspace-home">
  <header className="rounded-2xl bg-gradient-to-r from-[#173950] to-[#245369] px-6 py-7 text-white">
   <p className="text-[11px] font-bold uppercase tracking-[.18em] text-[#cce7ed]">BAWASLU · MANAGEMENT WORKSPACE</p>
   <h1 className="mt-2 text-3xl font-bold">Management Command Home</h1>
   <p className="mt-2 max-w-[780px] text-sm text-[#dceef1]">Decision support for authorized management. This is a fixed snapshot of saved officer casework, not a live web or social crawl and not an official legal finding.</p>
   <div className="mt-4 flex flex-wrap gap-2 text-xs"><span className="rounded-full border border-white/30 px-3 py-1">Saved casework · fixed as of request</span><span className="rounded-full border border-white/30 px-3 py-1">{scope}</span><span className="rounded-full border border-white/30 px-3 py-1">No AI/provider credits</span></div>
  </header>
  <div className="flex flex-wrap items-center justify-between gap-3">
   <div><h2 className="text-xl font-bold text-[#19364c]">Executive brief</h2><p className="text-xs text-slate-600">Permission-scoped casework metrics; report status is not source verification</p></div>
   <label className="text-sm text-slate-700">Reporting period <select className="ml-2 rounded-md border border-slate-300 bg-white px-3 py-2" value={period} onChange={e=>setPeriod(e.target.value)}><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="daily">Daily</option></select></label>
  </div>
  {loading&&<p role="status" className="rounded-lg border border-slate-200 bg-white p-5 text-sm">Loading authorized management brief…</p>}
  {error&&<div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm"><strong>Management data unavailable.</strong> {error} No metrics have been assumed.</div>}
  {snapshot&&!loading&&<>
   <section aria-label="Executive management indicators" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
    {[
     ['Assignments in period',metrics.assignments],
     ['Active assignments',metrics.active_assignments],
     ['Without reports',metrics.assignments_without_reports],
     ['Approved officer reports',metrics.approved_reports]
    ].map(([label,value])=><div key={label} className="rounded-xl border border-slate-200 bg-white p-4"><strong className="block text-2xl text-[#173950]">{number(value)}</strong><span className="mt-1 block text-xs text-slate-600">{label}</span></div>)}
   </section>
   <section className="grid gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(270px,1fr)]">
    <article className="rounded-xl border border-slate-200 bg-white p-5 space-y-4" data-testid="executive-brief">
     <div className="flex items-center gap-2"><FileText size={19}/><h3 className="font-bold">Executive assessment · saved casework</h3></div>
     <p className="text-sm text-slate-700">Reporting window: {safeDate(snapshot.window_start_utc)}–{safeDate(snapshot.window_end_utc)}. {scope}. The figures cover authorized assignments created in the selected period; previews may display fewer individual cases.</p>
     {!metrics.assignments?<p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">No authorized human casework assignments were recorded in this period. This does not mean there were no social signals, allegations, electoral incidents, or legal violations.</p>:<>
      <p className="text-sm"><strong>Casework position:</strong> {number(metrics.assignments)} assignments; {number(metrics.active_assignments)} still active; {number(metrics.approved_reports)} with approved latest officer reports. An approval records workflow status, not independent proof of an allegation.</p>
      <p className="text-sm"><strong>Priority review:</strong> {issue>0?number(issue)+' follow-up items require responsible-officer attention.':'No follow-up attention items were flagged by the saved casework queue.'} {missing>0?number(missing)+' assignments currently have no linked report.':'Every assignment has at least one linked report in this period.'}</p>
      <p className="text-sm"><strong>Decision gate:</strong> Verify original sources, jurisdiction and legal applicability before escalation or public communication. No report here substitutes for an authorized determination.</p>
     </>}
     <p className="border-t border-slate-200 pt-3 text-xs text-slate-500">Data basis: {snapshot.data_basis}; distinct linked sources: {number(metrics.unique_linked_sources)}; period count completeness: {snapshot.counts_complete_for_window?'complete for this scoped window':'not confirmed'}. Location breakdown uses verified casework location only.</p>
     <div className="flex flex-wrap gap-2">
      <Link to="/management/assistant?q=Prepare%20a%20neutral%20executive%20summary%20of%20authorized%20election-oversight%20records%20with%20citations%20and%20uncertainties" className="intel-button"><Search size={16}/> Research with AI <ArrowRight size={15}/></Link>
      <Link to="/assistant" className="intel-ghost">Operational assistant</Link>
     </div>
    </article>
    <aside className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
     <div className="flex items-center gap-2"><ShieldCheck size={18}/><h3 className="font-bold">Management review checkpoints</h3></div>
     <p className="text-sm text-slate-700"><strong>1 · Evidence owner:</strong> Case officer verifies original links, duplicate reports, publication dates and any missing incident location.</p>
     <p className="text-sm text-slate-700"><strong>2 · Legal reviewer:</strong> Authorized reviewer checks applicable law, currentness and jurisdiction before any recommendation is treated as a finding.</p>
     <p className="text-sm text-slate-700"><strong>3 · Management review:</strong> Confirm responsible department, milestone and next review point before instructions are issued.</p>
     <p className="text-xs text-slate-500"><AlertTriangle size={13} className="inline mr-1"/> These are suggested review roles, not actual assignments or approvals.</p>
    </aside>
   </section>
   <section className="rounded-xl border border-slate-200 bg-white p-5">
    <h3 className="mb-3 font-bold text-[#19364c]">Recently recorded casework · source links</h3>
    {cases.length?<div className="space-y-3">{cases.slice(0,6).map(row=><div key={row.id} className="rounded-lg border border-slate-100 p-3">
     <div className="flex flex-wrap justify-between gap-2"><strong className="text-sm">{row.title||'Untitled assignment'}</strong><span className="text-xs text-slate-500">{row.status||'Unknown status'} · {row.verified_province||'Location unverified'}</span></div>
     <p className="mt-1 text-xs text-slate-600">Case #{row.id} · {row.department||'Responsible team unconfirmed'} · Source: {row.source_type||'Unknown'} {row.source_id||'No ID'}</p>
     {row.source_url?.startsWith('https://')&&<a href={row.source_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-xs font-semibold text-[#0c6e70] underline">Open original source</a>}
    </div>)}</div>:<p className="text-sm text-slate-600">No human casework records to display in the selected period.</p>}
    <p className="mt-3 text-xs text-slate-500">Only saved source URLs are displayed. This page does not validate the original page, its truthfulness, or its current availability.</p>
   </section>
  </>}
  <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600">Management and operational workspaces are separate views of the same permission-controlled BAWASLU records. AI suggestions and drafts require authorized staff review before use.</div>
 </div>;
}
