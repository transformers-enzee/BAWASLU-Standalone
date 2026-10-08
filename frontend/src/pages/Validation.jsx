import { useMemo, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { CheckCircle2, AlertTriangle, Search, ExternalLink } from 'lucide-react';
import { intel, useIntel } from '@/components/intel/useIntel';
import { Notice, err } from '@/components/intel/Fields';
import Status from '@/components/intel/Status';
import { useLanguage } from '@/lib/LanguageContext';

const queueStatuses=['Pending Review','Awaiting Validation','Request More Information','Escalate for Further Review'];
const decisions=['Validated as Relevant Intelligence','Request More Information','Not Relevant','Escalate for Further Review'];
const priorities=['Critical','High','Medium','Low'];

const dateLabel=value=>{
  if(!value)return '—';
  const d=new Date(value);
  return Number.isNaN(d.getTime())?'—':d.toLocaleString('en-GB',{year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'});
};

function jurisdictionNeedsConfirmation(item){
  if(item.jurisdiction_confirmed!==true)return true;
  if(!item.jurisdiction_type||item.jurisdiction_type==='Unresolved')return true;
  if(item.jurisdiction_type==='National')return false;
  if(item.jurisdiction_type==='Multi-Region')return !(item.geographic_assignments||[]).length;
  return !(item.province||item.province_code);
}

function readyForValidation(item){
  const jurisdictionBlocked=jurisdictionNeedsConfirmation(item);
  const geoBlocked=(item.geographic_mismatch?.status||item.geographic_mismatch_review?.status)==='pending';
  const triage=item.triage_review||{};
  const triageBlocked=triage.generated&&triage.state!=='REVIEW COMPLETE';
  return !jurisdictionBlocked&&!geoBlocked&&!triageBlocked;
}

export default function Validation(){
 const {t,label}=useLanguage();
 const {access}=useOutletContext();
 const {items,loading,error,refresh}=useIntel();
 const [search,setSearch]=useState('');
 const [status,setStatus]=useState('');
 const [priority,setPriority]=useState('');
 const [triage,setTriage]=useState('');
 const [drafts,setDrafts]=useState({});
 const [busyId,setBusyId]=useState('');
 const [actionError,setActionError]=useState('');
 const [success,setSuccess]=useState('');

 const canReview=access.permissions?.human_validation===true;
 const pending=useMemo(()=>items.filter(x=>queueStatuses.includes(x.review_status)),[items]);
 const filtered=useMemo(()=>pending.filter(x=>{
   const hay=[x.intelligence_id,x.title,x.source_name,x.author,...(x.related_entities||[])].filter(Boolean).join(' ').toLowerCase();
   if(search&& !hay.includes(search.toLowerCase()))return false;
   if(status&&x.review_status!==status)return false;
   if(priority&&x.priority!==priority)return false;
   if(triage&&((x.triage_review?.state||'NOT GENERATED')!==triage))return false;
   return true;
 }),[pending,search,status,priority,triage]);

 const readyCount=pending.filter(readyForValidation).length;
 const needsInfoCount=pending.filter(x=>x.review_status==='Request More Information').length;
 const escalatedCount=pending.filter(x=>x.review_status==='Escalate for Further Review').length;

 const patchDraft=(id,patch)=>setDrafts(old=>({...old,[id]:{...(old[id]||{}),...patch}}));

 async function submit(item){
   const draft=drafts[item.id]||{};
   if(!draft.decision)return;
   if(['Request More Information','Not Relevant','Escalate for Further Review'].includes(draft.decision)&&!(draft.review_notes||'').trim()){
     setActionError(t('validation_notes_required'));return;
   }
   setBusyId(item.id);setActionError('');setSuccess('');
   try{
     await intel('review',{decision:draft.decision,review_notes:draft.review_notes||''},item.id);
     setDrafts(old=>{const next={...old};delete next[item.id];return next});
     setSuccess(t('validation_decision_saved'));
     await refresh();
   }catch(e){setActionError(err(e))}
   finally{setBusyId('')}
 }

 return <div className="space-y-6">
  <div>
   <p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('validation_oversight')}</p>
   <h1 className="intel-heading">{t('validation_queue')}</h1>
   <p className="text-sm text-[#77899b] mt-2">{t('validation_intro')}</p>
  </div>

  <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('validation_total_queue')}</p><p className="text-2xl font-semibold mt-1">{pending.length}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('validation_ready')}</p><p className="text-2xl font-semibold mt-1">{readyCount}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('validation_needs_info')}</p><p className="text-2xl font-semibold mt-1">{needsInfoCount}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('validation_escalated')}</p><p className="text-2xl font-semibold mt-1">{escalatedCount}</p></div>
  </div>

  <div className="intel-card p-4 grid md:grid-cols-4 gap-3">
   <label className="md:col-span-1"><span className="sr-only">{t('validation_search')}</span><div className="relative"><Search size={15} className="absolute left-3 top-3 text-[#8293a4]"/><input className="intel-input pl-9" placeholder={t('validation_search')} value={search} onChange={e=>setSearch(e.target.value)}/></div></label>
   <select className="intel-input" value={status} onChange={e=>setStatus(e.target.value)}><option value="">{t('validation_all_statuses')}</option>{queueStatuses.map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
   <select className="intel-input" value={priority} onChange={e=>setPriority(e.target.value)}><option value="">{t('validation_all_priorities')}</option>{priorities.map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
   <select className="intel-input" value={triage} onChange={e=>setTriage(e.target.value)}><option value="">{t('validation_all_triage')}</option>{['NOT GENERATED','NOT STARTED','IN REVIEW','REVIEW COMPLETE'].map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
  </div>

  <Notice error={error||actionError}/>
  {success&&<p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{success}</p>}

  {loading?<p>{t('loading_queue')}</p>:<div className="space-y-4">
   {filtered.map(item=>{
    const draft=drafts[item.id]||{};
    const geoBlocked=(item.geographic_mismatch?.status||item.geographic_mismatch_review?.status)==='pending';
    const triageState=item.triage_review?.state||'NOT GENERATED';
    const triageBlocked=item.triage_review?.generated&&triageState!=='REVIEW COMPLETE';
    const jurisdictionBlocked=jurisdictionNeedsConfirmation(item);
    const blockers=[jurisdictionBlocked?t('validation_blocker_jurisdiction'):'',geoBlocked?t('validation_blocker_geography'):'',triageBlocked?t('validation_blocker_triage'):''].filter(Boolean);
    const finalBlocked=blockers.length>0;
    return <article key={item.id} className="intel-card p-5 md:p-6 space-y-5">
      <div className="flex flex-wrap justify-between gap-4">
       <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
         <Link className="text-xs font-semibold text-[#126d91] hover:underline" to={'/intelligence/'+item.id}>{item.intelligence_id}</Link>
         <Status value={item.review_status}/><Status value={item.priority}/>
        </div>
        <h2 className="font-semibold text-[#1f364a] mt-2">{item.title||t('untitled_intelligence')}</h2>
        <p className="text-xs text-[#718599] mt-1">{item.source_name||item.author||t('source_not_recorded')}</p>
       </div>
       <Link to={'/intelligence/'+item.id} className="intel-ghost self-start"><ExternalLink size={14}/>{t('validation_review_record')}</Link>
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 text-sm">
       <div><span className="intel-label">{t('validation_jurisdiction')}</span><p>{item.jurisdiction_confirmed?[item.regency_city,item.province].filter(Boolean).join(', ')||t('national'):t('jurisdiction_unresolved_short')}</p></div>
       <div><span className="intel-label">{t('validation_evidence')}</span><div className="flex flex-wrap gap-1.5"><Status value={item.evidence_type}/><Status value={item.verification_status}/></div></div>
       <div><span className="intel-label">{t('validation_triage_progress')}</span><p>{label(triageState)}{item.triage_review?.generated?` · ${item.triage_review.reviewed}/${item.triage_review.total}`:''}</p></div>
       <div><span className="intel-label">{t('validation_assigned_to')}</span><p>{item.assigned_reviewer||t('validation_unassigned')}</p></div>
      </div>

      <div className={blockers.length?'rounded-lg border border-amber-200 bg-amber-50 px-4 py-3':'rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3'}>
       <p className="text-xs font-semibold">{t('validation_blockers')}</p>
       {blockers.length?<div className="mt-1 space-y-1">{blockers.map(x=><p key={x} className="text-xs text-amber-800 flex items-center gap-1.5"><AlertTriangle size={13}/>{x}</p>)}</div>:<p className="mt-1 text-xs text-emerald-800 flex items-center gap-1.5"><CheckCircle2 size={13}/>{t('validation_no_blockers')}</p>}
      </div>

      {canReview&&<div className="border-t pt-4 space-y-3">
       <p className="text-xs font-bold uppercase tracking-wide text-[#53657b]">{t('validation_quick_decision')}</p>
       <div className="grid md:grid-cols-[minmax(0,280px)_1fr_auto] gap-3 items-start">
        <select className="intel-input" value={draft.decision||''} onChange={e=>patchDraft(item.id,{decision:e.target.value})}>
         <option value="">{t('select')} {t('validation_decision').toLowerCase()}</option>
         {decisions.map(x=><option key={x} value={x} disabled={x==='Validated as Relevant Intelligence'&&finalBlocked}>{label(x)}</option>)}
        </select>
        <textarea className="intel-input min-h-[88px]" placeholder={t('validation_notes_placeholder')} value={draft.review_notes||''} onChange={e=>patchDraft(item.id,{review_notes:e.target.value})}/>
        <button className="intel-button" disabled={busyId===item.id||!draft.decision||(draft.decision==='Validated as Relevant Intelligence'&&finalBlocked)} onClick={()=>submit(item)}>{busyId===item.id?t('saving'):t('validation_submit_decision')}</button>
       </div>
      </div>}

      <div className="flex flex-wrap justify-between gap-2 text-xs text-[#8192a3]">
       <span>{t('validation_last_updated')}: {dateLabel(item.updated_date)}</span>
       <span>{t('validation_governance_note')}</span>
      </div>
    </article>;
   })}
   {!filtered.length&&<div className="intel-card p-10 text-center text-sm text-[#73869a]">{t('validation_queue_empty')}</div>}
  </div>}
 </div>;
}
