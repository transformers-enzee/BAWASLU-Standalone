import { useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useRegistry, registry } from '@/components/intel/useIntel';
import { Notice } from '@/components/intel/Fields';
import ActorIntelligence from '@/components/intel/ActorIntelligence';
import { useLanguage } from '@/lib/LanguageContext';

export default function WatchlistProfile(){
 const {id}=useParams(),navigate=useNavigate(),{access}=useOutletContext();
 const {items,accounts,relationships,loading,error,refresh}=useRegistry(),{t,label}=useLanguage();
 const [confirmStop,setConfirmStop]=useState(false),[stopping,setStopping]=useState(false),[stopError,setStopError]=useState('');
 const canManage=access?.permissions?.manage_watchlist===true;
 async function stopTracking(){
  if(!canManage||stopping)return;
  setStopping(true);setStopError('');
  try{
   await registry('updateWatchlist',{status:'Inactive'},id);
   await refresh();setConfirmStop(false);navigate('/watchlist');
  }catch(e){setStopError(e?.response?.data?.error||e?.message||'Unable to stop tracking.')}
  finally{setStopping(false)}
 }
 if(loading)return <p className="text-sm text-[#77899b]">{t('watchlist_profile_loading')}</p>;
 const item=items.find(x=>x.id===id);
 if(!item)return <Notice error={error||t('watchlist_profile_unavailable')}/>;
 return <div className="space-y-5 max-w-[1350px] mx-auto rounded-2xl bg-white p-4 md:p-8 shadow-sm">
  <Link to="/watchlist" className="text-sm font-semibold text-[#147b66]">← Back to all tracked candidates</Link>
  <section className="rounded-2xl border border-[#dce6e8] overflow-hidden">
   <div className="bg-gradient-to-r from-[#132d45] to-[#116b58] text-white p-6 md:p-8 flex flex-wrap items-center justify-between gap-5">
    <div className="flex items-center gap-4"><div className="h-16 w-16 rounded-full bg-white/20 border border-white/30 grid place-items-center text-3xl font-bold">{(item.name||'C')[0]}</div><div><p className="text-[11px] font-extrabold uppercase tracking-[.18em] text-[#aadbd1]">BAWASLU · Candidate Profile V2.2</p><h1 className="text-2xl md:text-3xl font-bold mt-1">{item.name}</h1><p className="text-sm text-[#d0e8e2] mt-1">{label(item.type)} · {[item.regency_city,item.province].filter(Boolean).join(', ')||'National'} · {label(item.status)}</p></div></div>
    {canManage&&item.status==='Active'&&<button type="button" onClick={()=>setConfirmStop(true)} className="rounded-lg border border-white/50 bg-white/15 text-white px-4 py-2.5 font-semibold text-sm hover:bg-white/25">Stop Tracking</button>}
   </div>
   <div className="p-5 md:p-6 space-y-5">
    <div className="rounded-xl border border-[#cde7dd] bg-[#f0f8f6] p-5"><strong className="text-[#175c4e]">✦ Candidate Activity Summary</strong><p className="text-sm leading-7 mt-2 text-slate-700">{item.description||'No approved narrative summary is recorded for this candidate yet. Review captured source posts and associated intelligence before reaching a conclusion.'}</p><p className="text-xs text-slate-500 mt-2">Registry summary; not a generated or verified AI conclusion.</p></div>
   <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
    {[[accounts.filter(a=>a.watchlist_id===id).length,'Tracked Accounts'],[relationships.filter(r=>r.from_id===id||r.to_id===id).length,'Registered Relationships'],[item.related_topics?.length||0,'Linked Topics'],[label(item.status),'Tracking Status']].map(([value,heading])=><div key={heading} className="rounded-xl border border-[#dce6e8] p-4 bg-white"><strong className="text-xl font-bold text-[#164e48]">{value}</strong><p className="text-xs text-[#627783] mt-1">{heading}</p></div>)}
   </div>
   <div className="grid sm:grid-cols-2 gap-4 text-sm">
    {[
      [t('province'),item.province],
      [t('regency_city'),item.regency_city],
      [t('related_election'),item.related_election],
      [t('related_entity'),item.related_entity],
      [t('topics'),item.related_topics?.join(', ')],
      [t('monitoring_priority'),label(item.priority)],
      [t('monitoring_status'),label(item.status)],
      [t('notes'),item.notes]
    ].map(([fieldLabel,value])=><div key={fieldLabel}><span className="intel-label">{fieldLabel}</span><p className="whitespace-pre-wrap">{value||'—'}</p></div>)}
   </div>
   <div><span className="intel-label">{t('public_accounts')}</span>{accounts.filter(a=>a.watchlist_id===id).map(a=><a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="block text-sm text-[#126d91] break-all">{a.platform||'Web'} · {a.handle||a.url}</a>)}{!accounts.some(a=>a.watchlist_id===id)&&<p className="text-sm">{t('none_recorded')}</p>}</div>
   <div><span className="intel-label">{t('registry_relationships')}</span>{relationships.filter(r=>r.from_id===id).map(r=><p key={r.id} className="text-sm">{label(r.relationship_type)} · {items.find(w=>w.id===r.to_id)?.name||t('watchlist_entry')}</p>)}{!relationships.some(r=>r.from_id===id)&&<p className="text-sm">{t('none_recorded')}</p>}</div>
   <p className="text-xs text-[#607b8a]">{t('watchlist_disclaimer')}</p>
   </div>
  </section>
  <nav aria-label="Candidate profile sections" className="flex flex-wrap gap-2 border-b border-[#dbe6e7] pb-3">
    <a href="#candidate-evidence" className="rounded-lg bg-[#147b67] px-4 py-2 text-white text-xs font-semibold">Activity &amp; Sentiment</a>
    <Link to={'/watchlist/'+id+'/posts'} className="rounded-lg border border-[#d2dee1] px-4 py-2 text-[#147b67] text-xs font-semibold">Own Posts / Captured Evidence →</Link>
    <Link to={'/inbox?entity='+encodeURIComponent(item.name)} className="rounded-lg border border-[#d2dee1] px-4 py-2 text-[#147b67] text-xs font-semibold">Related Intelligence →</Link>
  </nav>
  <div id="candidate-evidence"><ActorIntelligence actorId={id} accounts={accounts}/></div>
  {confirmStop&&<div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/60 p-4" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget&&!stopping)setConfirmStop(false)}}>
   <div role="alertdialog" aria-modal="true" aria-labelledby="stop-tracking-title" aria-describedby="stop-tracking-description" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
    <h2 id="stop-tracking-title" className="text-xl font-bold text-slate-900">Stop tracking {item.name}?</h2>
    <p id="stop-tracking-description" className="mt-3 text-sm leading-6 text-slate-600">This changes the candidate's monitoring status to Inactive. Original source posts, evidence and prior review records are preserved. It does not delete intelligence.</p>
    {stopError&&<p role="alert" className="mt-3 text-sm text-red-700">{stopError}</p>}
    <div className="mt-6 flex justify-end gap-2"><button type="button" disabled={stopping} onClick={()=>setConfirmStop(false)} className="intel-ghost">Cancel</button><button type="button" disabled={stopping} onClick={stopTracking} className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{stopping?'Saving…':'Yes, stop tracking'}</button></div>
   </div>
  </div>}
 </div>
}
