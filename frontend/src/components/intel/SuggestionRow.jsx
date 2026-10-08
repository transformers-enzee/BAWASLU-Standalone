import { useState } from 'react';
import { suggestionNames as labels } from './triageSections';
import { useLanguage } from '@/lib/LanguageContext';

const labelKeys={
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

const fieldLabel=(key,t)=>({
 entity_name:t('structured_entity_name'),
 entity_type:t('structured_entity_type'),
 relationship_to_content:t('structured_relationship'),
 evidence_basis:t('structured_evidence_basis'),
 evidence_type:t('structured_evidence_type'),
 confidence:t('structured_confidence'),
 location_text:t('structured_location'),
 description:t('structured_description'),
 type:t('structured_type'),
 subject_entity_name:t('structured_subject'),
 relationship_type:t('structured_relationship_type'),
 object_entity_name:t('structured_object'),
 observed_account:t('structured_observed_account')
}[key]||key.replaceAll('_',' '));

function StructuredValue({value,t}){
 let parsed=value;
 if(typeof value==='string'){
  try{parsed=JSON.parse(value)}catch{return <p className="text-sm whitespace-pre-wrap break-words">{value||t('no_suggestion')}</p>}
 }
 if(Array.isArray(parsed))return <div className="space-y-2">{parsed.map((entry,i)=><div key={i} className="rounded-md bg-[#f7fafb] border border-[#e6edf1] p-3"><div className="text-[10px] uppercase tracking-wide text-[#8293a4] mb-2">{t('structured_item')} {i+1}</div><StructuredValue value={entry} t={t}/></div>)}</div>;
 if(parsed&&typeof parsed==='object')return <div className="grid gap-2">{Object.entries(parsed).filter(([,v])=>v!==''&&v!==null&&v!==undefined).map(([k,v])=><div key={k} className="grid sm:grid-cols-[150px_minmax(0,1fr)] gap-1 text-sm"><span className="text-[#6d8091] font-medium">{fieldLabel(k,t)}</span><span className="break-words whitespace-pre-wrap">{typeof v==='object'?JSON.stringify(v):String(v)}</span></div>)}</div>;
 return <p className="text-sm whitespace-pre-wrap break-words">{String(parsed??t('no_suggestion'))}</p>;
}

export default function SuggestionRow({name,value,decision,onDecision,confidence}){
 const {t,label}=useLanguage();
 const [edited,setEdited]=useState(value||''),[reason,setReason]=useState('');
 const displayName=t(labelKeys[name]||'')||labels[name]||name;
 const statuses=[
  ['Human Accepted',t('accept')],
  ['Human Modified',t('modify')],
  ['Human Rejected',t('reject')]
 ];
 return <div className="border-t pt-3 space-y-2">
  <div className="text-xs font-semibold text-[#53657b]">{displayName}{confidence&&<span className="font-normal"> · {t('ai_confidence')}: {label(confidence)}</span>}</div>
  <StructuredValue value={value} t={t}/>
  <div className="flex flex-wrap gap-2">{statuses.map(([status,text])=><button key={status} type="button" className={decision?.status===status?'intel-button':'intel-ghost'} onClick={()=>onDecision({status,value:status==='Human Modified'?edited:status==='Human Accepted'?value:'',reason:status==='Human Rejected'?reason.trim():''})}>{text}</button>)}</div>
  {decision?.status==='Human Rejected'&&<label className="block text-xs text-[#53657b]">{t('reason_rejection')}<textarea className="intel-input mt-1" maxLength={500} value={reason} onChange={e=>{setReason(e.target.value);onDecision({status:'Human Rejected',value:'',reason:e.target.value})}} rows={2}/></label>}
  {decision?.status==='Human Modified'&&<textarea className="intel-input" aria-label={displayName} value={edited} onChange={e=>{setEdited(e.target.value);onDecision({status:'Human Modified',value:e.target.value})}}/>}
  {decision&&<p className="text-xs text-[#59788a]">{label(decision.status)}{decision.status!=='Human Rejected'&&' · '+t('final_label')+': '+(decision.value||t('enter_value'))}</p>}
 </div>;
}
