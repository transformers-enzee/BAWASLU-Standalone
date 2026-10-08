import Status from './Status';
import { useLanguage } from '@/lib/LanguageContext';

const listText=value=>Array.isArray(value)?value.filter(Boolean).join(' · '):value||'';
const actorText=value=>Array.isArray(value)?value.map(a=>typeof a==='string'?a:[a?.entity_name,a?.relationship_to_content].filter(Boolean).join(' · ')).filter(Boolean).join(', '):value||'';
const relationshipText=value=>Array.isArray(value)?value.map(r=>typeof r==='string'?r:(r?.subject_entity_name||'Actor')+' · '+(r?.relationship_type||'related to')+' · '+(r?.object_entity_name||r?.observed_account||'source')).filter(Boolean).join('; '):value||'';
const activityText=value=>typeof value==='string'?value:[value?.type,value?.description].filter(Boolean).join(' · ');
const narrativeText=value=>typeof value==='string'?value:[value?.label,value?.description].filter(Boolean).join(' · ');
const locationText=value=>typeof value==='string'?value:value?.location_text||'';

function Provenance({state,t}){
  if(!state?.decision)return null;
  const action=state.decision==='Human Modified'?t('human_modified'):state.decision==='Human Accepted'?t('human_accepted'):t('human_rejected');
  return <p className="mt-1 text-[10px] text-[#8293a4]">{t('human_label')} {action} · {state.reviewer||t('authorized_reviewer')}{state.decided_at?' · '+new Date(state.decided_at).toLocaleString('en-GB'):''}</p>;
}
function FieldState({state,t}){
  if(!state)return <p className="text-[#73879a]">{t('no_ai_suggestion')}</p>;
  if(state.state==='REJECTED')return <><p className="font-medium text-[#8b4b37]">{t('rejected_by_reviewer')}</p>{state.reason&&<p className="mt-1 text-[10px] text-[#8b6f65]">{t('reason')}: {state.reason}</p>}<Provenance state={state} t={t}/></>;
  if(state.state==='PENDING')return <p className="text-[#8a6d35]">{t('awaiting_human_review')}</p>;
  return null;
}
function ApprovedField({label,field,value,states,t}){
  const state=states[field];
  return <div><span className="intel-label">{label}</span>{state?.state==='APPROVED'?<><p className="whitespace-pre-wrap">{value||t('human_approved_unavailable')}</p><Provenance state={state} t={t}/></>:<FieldState state={state} t={t}/>}</div>;
}

export default function IntelligenceSummary({item}){
  const {t}=useLanguage();
  const x=item,projection=x.human_approved_triage||{},approved=projection.values||{},states=projection.field_states||{};
  const approvedCount=projection.approved_count||0;
  const actorKey=approved.actors!==undefined?'actors':approved.entity!==undefined?'entity':'actors';
  const locationKey=approved.location_signal!==undefined?'location_signal':approved.location!==undefined?'location':'location_signal';
  const jurisdiction=x.jurisdiction_confirmed?[x.regency_city,x.province].filter(Boolean).join(', ')||(x.jurisdiction_type==='National'?t('national')+' · '+t('nationwide'):x.jurisdiction_type):t('not_human_confirmed');
  const analytical=[
    [t('what_happened'),'summary',approved.summary||''],
    [t('who_involved'),actorKey,actorText(approved.actors||approved.entity)],
    [t('where_signal'),locationKey,locationText(approved.location_signal||approved.location)],
    [t('activity'),'activity',activityText(approved.activity)],
    [t('narrative'),'narrative',narrativeText(approved.narrative)],
    [t('extracted_relationship_not_ownership'),'relationships',relationshipText(approved.relationships)],
    [t('filter_supervision_signal'),'supervision_signal',approved.supervision_signal||''],
    [t('screening_confidence'),'screening_confidence',approved.screening_confidence||''],
    [t('why_attention'),'signal_reason',approved.signal_reason||''],
    [t('check_next'),'check_next',listText(approved.check_next)],
    [t('screening_evidence_basis'),'screening_evidence_basis',listText(approved.screening_evidence_basis)],
    [t('evidence_gaps'),'evidence_gaps',listText(approved.evidence_gaps)]
  ];
  return <section className="intel-card p-6 space-y-6">
    <div className="space-y-2"><h2 className="font-semibold text-lg">{t('intelligence_summary')}</h2><p className="font-medium">{x.title}</p><div className="flex flex-wrap items-center gap-2"><p className="text-[11px] font-bold uppercase tracking-wider text-[#267291]">{t('final_summary_human_only')}</p>{approvedCount>0&&<span className="text-[11px] rounded-full bg-[#eef5f8] px-2 py-1 text-[#42657a]">{approvedCount} {t('triage_fields_approved')}</span>}</div></div>
    <div className="space-y-3"><h3 className="text-xs font-bold uppercase tracking-wider text-[#53657b]">{t('human_approved_fields')}</h3><div className="grid sm:grid-cols-2 gap-4 text-sm">{analytical.map(([fieldLabel,field,value])=><ApprovedField key={fieldLabel} label={fieldLabel} field={field} value={value} states={states} t={t}/>)}
      <div><span className="intel-label">{t('priority')}</span>{states.priority?.state==='APPROVED'?<><Status value={approved.priority}/><Provenance state={states.priority} t={t}/></>:<FieldState state={states.priority} t={t}/>}</div>
      <div><span className="intel-label">{t('evidence_type_not_verification')}</span>{states.evidence_type?.state==='APPROVED'?<><Status value={approved.evidence_type}/><Provenance state={states.evidence_type} t={t}/></>:<FieldState state={states.evidence_type} t={t}/>}</div>
    </div></div>
    <div className="border-t pt-4 space-y-3"><div><h3 className="text-xs font-bold uppercase tracking-wider text-[#53657b]">{t('recorded_source_context')}</h3><p className="mt-1 text-[10px] text-[#8293a4]">{t('recorded_source_context_note')}</p></div><div className="grid sm:grid-cols-2 gap-4 text-sm">
      <div><span className="intel-label">{t('source_publisher')}</span><p>{x.observed_publisher_handle||x.author||x.source_name||t('not_recorded')}</p></div>
      <div><span className="intel-label">{t('confirmed_jurisdiction')}</span><p>{jurisdiction||t('not_recorded')}</p></div>
      <div><span className="intel-label">{t('human_confirmed_relationship')}</span><p>{x.entity_relationships?.filter(r=>r.review_status==='HUMAN_CONFIRMED').map(r=>r.relationship_type+' · '+r.evidence_basis).join('; ')||t('not_recorded')}</p></div>
      <div><span className="intel-label">{t('evidence_verification_status')}</span><Status value={x.verification_status}/></div>
    </div></div>
    {x.potential_issue_category&&<div className="border-t pt-3"><h3 className="text-xs font-bold uppercase tracking-wider">{t('legacy_assessment')}</h3><p className="text-sm mt-2">{t('historical_issue_category')}: {x.potential_issue_category}</p><p className="text-xs text-[#617789]">{t('historical_only_note')}</p></div>}
    <p className="text-xs text-[#8c9bab]">{t('summary_footer')}</p>
  </section>;
}
