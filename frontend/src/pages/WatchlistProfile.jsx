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
 return <div className="space-y-5 max-w-4xl">
  <Link to="/watchlist" className="text-sm text-[#126d91]">← {t('watchlist')}</Link>
  <section className="intel-card p-6 space-y-5">
   <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs uppercase font-bold text-[#53657b]">{t('watchlist_profile_label')}</p><h1 className="intel-heading mt-2">{item.name}</h1><p className="text-sm text-[#607b8a]">{label(item.type)}</p></div>{canManage&&item.status==='Active'&&<button type="button" onClick={()=>setConfirmStop(true)} className="intel-ghost border border-red-200 text-red-700">Stop Tracking</button>}</div>
   <p className="text-sm">{item.description||t('no_description')}</p>
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
  </section>
  <Link to={'/watchlist/'+id+'/posts'} className="intel-button inline-flex">View captured account posts →</Link>
  <ActorIntelligence actorId={id} accounts={accounts}/>
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
