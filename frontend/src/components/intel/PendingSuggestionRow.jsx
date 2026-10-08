import { useState } from 'react';
import { useLanguage } from '@/lib/LanguageContext';

const noIssue='NO APPARENT ELECTION-SUPERVISION ISSUE';
const nameKey={
 source_facts:'triage_source_facts',
 actors:'suggestion_actors',
 location_signal:'suggestion_location',
 topics:'suggestion_topics',
 inferences:'suggestion_inferences',
 screening_evidence_basis:'suggestion_screening_basis',
 screening_confidence:'suggestion_screening_confidence',
 summary:'suggestion_summary',
 english_translation:'suggestion_translation',
 entity:'suggestion_entity',
 actor_evidence:'suggestion_actor_evidence',
 content_type:'suggestion_content_type',
 activity:'suggestion_activity',
 location:'suggestion_location',
 topic:'suggestion_topic',
 narrative:'suggestion_narrative',
 relationships:'suggestion_relationships',
 inference:'suggestion_inference',
 supervision_signal:'suggestion_supervision_signal',
 signal_reason:'suggestion_signal_reason',
 check_next:'suggestion_check_next',
 priority:'suggestion_priority',
 evidence_type:'suggestion_evidence_type',
 evidence_gaps:'suggestion_evidence_gaps',
 issue_category:'suggestion_issue_category',
 suggested_evidence_state:'suggestion_evidence_state',
 analysis:'suggestion_analysis',
 reasoning:'suggestion_reasoning'
};

export default function PendingSuggestionRow({name,value,decision,confidence,onDecide,busy}){
 const {t,label}=useLanguage();
 const [editing,setEditing]=useState(false),[changing,setChanging]=useState(false),[rejecting,setRejecting]=useState(false),[reason,setReason]=useState(''),[draft,setDraft]=useState('');
 const noIssueFound=name==='issue_category'&&(value===noIssue||value==='NO APPARENT ELECTION-SUPERVISION ISSUE IDENTIFIED');
 const showValue=noIssueFound?'NO APPARENT ELECTION-SUPERVISION ISSUE IDENTIFIED':value;
 const save=async(status,text,reasonText)=>{if(await onDecide(name,status,text,reasonText)){setEditing(false);setChanging(false);setRejecting(false);setReason('')}};
 const displayName=t(nameKey[name]||name);
 const statusText=decision?.status?label(decision.status):t('awaiting_human_review_label');

 return <div className="rounded-lg border border-[#e3eaf0] p-4 space-y-3">
  <div className="flex flex-wrap justify-between gap-2"><h4 className="text-xs font-bold uppercase tracking-wide text-[#53657b]">{displayName}</h4><span className="text-xs text-[#607b8a]">{statusText}</span></div>
  <p className="text-sm whitespace-pre-wrap break-words max-h-48 overflow-auto">{showValue}</p>
  {noIssueFound&&<p className="text-xs leading-5 text-[#617789]">{t('no_issue_triage_note')}</p>}
  {confidence&&<p className="text-xs text-[#667b8e]">{t('ai_confidence')}: {confidence}</p>}
  {decision?.status&&<p className="text-xs text-[#42657a] max-h-48 overflow-auto whitespace-pre-wrap break-words">{t('human_decision_label')}: {label(decision.status)}{decision.status!=='Human Rejected'&&decision.value?' · '+t('final_value')+': '+(decision.value===noIssue?'NO APPARENT ELECTION-SUPERVISION ISSUE IDENTIFIED':decision.value):''}{decision.status==='Human Rejected'&&decision.reason?' · '+t('reason')+': '+decision.reason:''}</p>}

  {decision?.status&&!changing
   ?<button type="button" disabled={busy} className="text-xs font-semibold text-[#126d91] hover:underline" onClick={()=>setChanging(true)}>{t('change_decision')}</button>
   :<div className="flex flex-wrap gap-2">
     <button type="button" disabled={busy} className="intel-ghost" onClick={()=>save('Human Accepted')}>{t('accept')}</button>
     <button type="button" disabled={busy} className="intel-ghost" onClick={()=>{setDraft(decision?.value||value);setEditing(true)}}>{t('modify')}</button>
     <button type="button" disabled={busy} className="intel-ghost" onClick={()=>{setEditing(false);setRejecting(true)}}>{t('reject')}</button>
     {changing&&<button type="button" className="intel-ghost" onClick={()=>{setChanging(false);setEditing(false)}}>{t('cancel_change')}</button>}
    </div>
  }

  {rejecting&&<div className="space-y-2"><label className="intel-label" htmlFor={'reject-'+name}>{t('reason_rejection')}</label><textarea id={'reject-'+name} className="intel-input" maxLength={500} value={reason} onChange={e=>setReason(e.target.value)} rows={2}/><button type="button" disabled={busy||reason.trim().length<5} className="intel-button" onClick={()=>save('Human Rejected','',reason)}>{t('save_rejection')}</button> <button type="button" className="intel-ghost" onClick={()=>setRejecting(false)}>{t('cancel')}</button></div>}

  {editing&&<div className="space-y-2"><textarea className="intel-input" aria-label={displayName} value={draft} onChange={e=>setDraft(e.target.value)} rows={name==='english_translation'?5:2}/><button type="button" disabled={busy||!draft.trim()} className="intel-button" onClick={()=>save('Human Modified',draft)}>{t('save_modified_value')}</button> <button type="button" className="intel-ghost" onClick={()=>setEditing(false)}>{t('cancel')}</button></div>}
 </div>;
}
