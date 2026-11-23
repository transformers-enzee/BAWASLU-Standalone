export default function AssistantModeControls({mode,setMode,perspective,setPerspective,workspace='OPERATIONAL',access,busy}){
 const leadership=['National Administrator','National Leadership','Provincial Administrator'].includes(access?.role);
 const office=[access?.geographic_scope,access?.province,access?.regency_city].filter(Boolean).join(' · ');
 return <section className="intel-card space-y-3 p-4" data-testid="smart-radar-assistant-active-mode">
  <div className="flex flex-wrap items-center justify-between gap-3">
   <div>
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">SmartRadar AI Research, Strategy & Productivity Assistant</p>
    <h2 className="mt-1 font-semibold text-[#19364c]">{mode==='MANAGEMENT'?'Management mode':'Operational mode'} <span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs font-normal">Active</span></h2>
    <p className="mt-1 text-xs text-slate-600">Workspace: {workspace==='MANAGEMENT'?'Management':'Operations'} · {office||'Authorized jurisdiction from your officer profile'}</p>
   </div>
   <label className="text-xs font-semibold text-slate-600">Active mode
    <select className="mt-1 block rounded-lg border border-slate-300 bg-white p-2 text-sm" value={mode}
      onChange={e=>setMode(e.target.value)} disabled={busy} aria-label="SmartRadar active analytical mode">
     <option value="OPERATIONAL">Operational</option>
     {leadership&&<option value="MANAGEMENT">Management</option>}
    </select>
   </label>
  </div>
  <p className="text-xs text-slate-600">{mode==='MANAGEMENT'
   ?'Start with the decision leadership needs, changing risks, affected jurisdictions, options, trade-offs and escalation conditions.'
   :'Start with the first officer action, source evidence, verification gaps, relevant rules and reviewer responsibilities.'}</p>
  <div className="flex flex-wrap items-center gap-2">
   <label className="text-xs font-medium text-slate-600">Perspective
    <select className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" value={perspective}
      aria-label="SmartRadar answer perspective" disabled={busy} onChange={e=>setPerspective(e.target.value)}>
     <option value="AUTO">Auto</option><option value="EXECUTIVE">Executive</option>
     <option value="OPERATIONAL">Operational</option><option value="RESEARCH">Research</option>
    </select>
   </label>
   <span className="text-xs text-slate-500">Perspective changes emphasis, not role access or workspace workflow.</span>
  </div>
 </section>;
}
