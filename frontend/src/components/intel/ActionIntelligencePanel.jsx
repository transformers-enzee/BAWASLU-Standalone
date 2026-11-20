import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ClipboardList, MapPin, Scale, ShieldAlert } from 'lucide-react';

function sourcePath(row){
  if(row.record_type==='INTELLIGENCE_ITEM' && /^\d+$/.test(String(row.item_id||'')))
    return '/intelligence/'+encodeURIComponent(row.item_id);
  if(/^\d+$/.test(String(row.campaign_id||''))&&/^\d+$/.test(String(row.result_id||'')))
    return '/inbox?campaign_id='+encodeURIComponent(row.campaign_id)+'&result_id='+encodeURIComponent(row.result_id);
  return '/inbox';
}
export default function ActionIntelligencePanel({model}){
  const [filter,setFilter]=useState('all');
  const rows=Array.isArray(model?.items)?model.items:[];
  const visible=rows.filter(row=>filter==='all'||(filter==='legal'?['GENERAL_CRIMINAL_LAW','INSTITUTIONAL_ETHICS'].includes(row.domain):row.domain==='UNCLASSIFIED'));
  return <section className="intel-card p-4 md:p-5 space-y-4" aria-label="AI Action Intelligence review cards">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <p className="text-[11px] uppercase tracking-[.18em] font-bold text-[#9a7e49]">BAWASLU · Action Intelligence</p>
        <h2 className="text-lg font-semibold text-[#173952]">Violation Type · Geographical Impact · Recommendations</h2>
        <p className="text-xs text-slate-600 mt-1">Officer-ready triage from existing saved AI assessments and intelligence records. Read-only; no new paid AI analysis.</p>
      </div>
      <span className="text-[11px] rounded-full bg-[#eaf3f7] text-[#295e7b] px-2 py-1">{model?.scope==='HQ'?'HQ / Nationwide':'Authorized Provincial / Local'}</span>
    </div>
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      <div className="rounded-lg bg-[#f4f8fa] p-3"><p className="text-[11px] text-slate-600">Review candidates in scope</p><strong className="block text-2xl">{model?.candidate_count??0}</strong></div>
      <div className="rounded-lg bg-[#f4f8fa] p-3"><p className="text-[11px] text-slate-600">Displayed cards</p><strong className="block text-2xl">{visible.length}</strong></div>
      <div className="rounded-lg bg-[#fff7ed] p-3 col-span-2 sm:col-span-1"><p className="text-[11px] text-amber-800">Confirmed violations</p><strong className="block text-sm mt-2 text-amber-900">Not assessed here</strong></div>
    </div>
    <div role="group" aria-label="Filter action cards" className="flex flex-wrap gap-2">
      {[['all','All'],['legal','Jurisdiction review'],['unclassified','Needs classification']].map(([key,label])=><button key={key} type="button" aria-pressed={filter===key} onClick={()=>setFilter(key)} className={filter===key?'intel-button text-xs':'intel-ghost text-xs'}>{label}</button>)}
    </div>
    {visible.length?<div className="grid xl:grid-cols-2 gap-3">{visible.map(row=><article key={row.record_type+row.id} className="rounded-xl border border-[#e1e8ee] p-4 space-y-3">
      <div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-[#176e8e]">{row.id}</span><span className="rounded-full bg-amber-50 px-2 py-1 text-[11px] text-amber-800">Officer review needed</span></div>
      <h3 className="text-sm font-semibold text-[#173952] line-clamp-2">{row.title}</h3>
      <div className="border-t border-slate-100 pt-2 space-y-1">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-[#294960]"><Scale size={14}/> 1. Violation type</p>
        <p className="text-sm font-semibold">{row.violation_type}</p>
        <p className="text-xs text-slate-600">{row.domain_label} · Status: not legally determined</p>
      </div>
      <div className="border-t border-slate-100 pt-2 space-y-1">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-[#294960]"><MapPin size={14}/> 2. Geographical impact</p>
        <p className="text-sm font-semibold">Affected province(s): not established</p>
        <p className="text-xs text-slate-600">Review scope: {row.review_geography}</p>
        <p className="text-[11px] text-amber-800">Monitoring/assigned geography is not proof of the incident location.</p>
      </div>
      <div className="border-t border-slate-100 pt-2 space-y-1.5">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-[#294960]"><ClipboardList size={14}/> 3. Recommended action plan</p>
        <ol className="list-decimal pl-5 text-xs text-slate-700 space-y-1">{(row.actions||[]).map((x,i)=><li key={i}>{x}</li>)}</ol>
        <p className="text-[11px] text-slate-500"><strong>Suggested reviewer:</strong> {row.owner_role_suggested}. No assignment created.</p>
      </div>
      <div className="rounded-lg bg-[#f7fafb] p-3 text-xs space-y-1">
        <strong>Saved evidence</strong>
        <p className="text-slate-600 line-clamp-3">{row.evidence_excerpt||'Excerpt unavailable — review original record.'}</p>
        <p className="text-[11px] text-slate-500">{row.source_provenance} · Flag: {row.officer_flag_status}</p>
      </div>
      <Link to={sourcePath(row)} className="inline-flex items-center gap-1 text-xs font-semibold text-[#176e8e]">Review source record <ArrowUpRight size={13}/></Link>
    </article>)}</div>:<p role="status" className="rounded-lg bg-[#f7fafb] p-5 text-sm text-slate-600">No source-linked review cards match this filter in your authorized scope. This is not evidence of no violations.</p>}
    <div role="note" className="flex items-start gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-600"><ShieldAlert size={15} className="shrink-0 mt-0.5"/><p>{model?.notice||'Evidence and classifications require officer verification.'} The dashboard does not create official cases, provincial assignments or referrals.</p></div>
  </section>;
}
