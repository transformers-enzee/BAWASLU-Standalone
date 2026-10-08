import Status from './Status';

const listText=value=>Array.isArray(value)?value.filter(Boolean).join(' · '):value||'';
const actorText=value=>Array.isArray(value)?value.map(a=>typeof a==='string'?a:[a?.entity_name,a?.relationship_to_content].filter(Boolean).join(' · ')).filter(Boolean).join(', '):value||'';
const relationshipText=value=>Array.isArray(value)?value.map(r=>typeof r==='string'?r:`${r?.subject_entity_name||'Actor'} · ${r?.relationship_type||'related to'} · ${r?.object_entity_name||r?.observed_account||'source'}`).filter(Boolean).join('; '):value||'';
const activityText=value=>typeof value==='string'?value:[value?.type,value?.description].filter(Boolean).join(' · ');
const narrativeText=value=>typeof value==='string'?value:[value?.label,value?.description].filter(Boolean).join(' · ');
const locationText=value=>typeof value==='string'?value:value?.location_text||'';

function FieldState({state}){
  if(!state)return <p className="text-[#73879a]">No AI suggestion generated</p>;
  if(state.state==='REJECTED')return <><p className="font-medium text-[#8b4b37]">Rejected by human reviewer</p>{state.reason&&<p className="mt-1 text-[10px] text-[#8b6f65]">Reason: {state.reason}</p>}<Provenance state={state}/></>;
  if(state.state==='PENDING')return <p className="text-[#8a6d35]">Awaiting human review</p>;
  return null;
}
function Provenance({state}){
  if(!state?.decision)return null;
  return <p className="mt-1 text-[10px] text-[#8293a4]">Human {state.decision==='Human Modified'?'modified':state.decision==='Human Accepted'?'accepted':'rejected'} · {state.reviewer||'authorized reviewer'}{state.decided_at?` · ${new Date(state.decided_at).toLocaleString('en-GB')}`:''}</p>;
}
function ApprovedField({label,field,value,states}){
  const state=states[field];
  return <div><span className="intel-label">{label}</span>{state?.state==='APPROVED'?<><p className="whitespace-pre-wrap">{value||'Human-approved value not available'}</p><Provenance state={state}/></>:<FieldState state={state}/>}</div>;
}

export default function IntelligenceSummary({item}){
  const x=item,projection=x.human_approved_triage||{},approved=projection.values||{},states=projection.field_states||{};
  const approvedCount=projection.approved_count||0;
  const actorKey=approved.actors!==undefined?'actors':approved.entity!==undefined?'entity':'actors';
  const locationKey=approved.location_signal!==undefined?'location_signal':approved.location!==undefined?'location':'location_signal';
  const jurisdiction=x.jurisdiction_confirmed?[x.regency_city,x.province].filter(Boolean).join(', ')||(x.jurisdiction_type==='National'?'National · Nationwide':x.jurisdiction_type):'Not human-confirmed';
  const analytical=[
    ['What happened','summary',approved.summary||''],
    ['Who is involved',actorKey,actorText(approved.actors||approved.entity)],
    ['Where / location signal',locationKey,locationText(approved.location_signal||approved.location)],
    ['Activity','activity',activityText(approved.activity)],
    ['Narrative','narrative',narrativeText(approved.narrative)],
    ['Extracted relationship · not ownership','relationships',relationshipText(approved.relationships)],
    ['Supervision signal','supervision_signal',approved.supervision_signal||''],
    ['Screening confidence','screening_confidence',approved.screening_confidence||''],
    ['Why attention may be warranted','signal_reason',approved.signal_reason||''],
    ['What to check next','check_next',listText(approved.check_next)],
    ['Screening evidence basis','screening_evidence_basis',listText(approved.screening_evidence_basis)],
    ['Evidence gaps','evidence_gaps',listText(approved.evidence_gaps)]
  ];
  return <section className="intel-card p-6 space-y-6">
    <div className="space-y-2"><h2 className="font-semibold text-lg">Intelligence Summary</h2><p className="font-medium">{x.title}</p><div className="flex flex-wrap items-center gap-2"><p className="text-[11px] font-bold uppercase tracking-wider text-[#267291]">FINAL SUMMARY · HUMAN-APPROVED ONLY</p>{approvedCount>0&&<span className="text-[11px] rounded-full bg-[#eef5f8] px-2 py-1 text-[#42657a]">{approvedCount} triage field{approvedCount===1?'':'s'} human-approved</span>}</div></div>

    <div className="space-y-3"><h3 className="text-xs font-bold uppercase tracking-wider text-[#53657b]">Human-approved analytical fields</h3><div className="grid sm:grid-cols-2 gap-4 text-sm">{analytical.map(([label,field,value])=><ApprovedField key={label} label={label} field={field} value={value} states={states}/>)}
      <div><span className="intel-label">Priority</span>{states.priority?.state==='APPROVED'?<><Status value={approved.priority}/><Provenance state={states.priority}/></>:<FieldState state={states.priority}/>}</div>
      <div><span className="intel-label">Evidence Type · not verification</span>{states.evidence_type?.state==='APPROVED'?<><Status value={approved.evidence_type}/><Provenance state={states.evidence_type}/></>:<FieldState state={states.evidence_type}/>}</div>
    </div></div>

    <div className="border-t pt-4 space-y-3"><div><h3 className="text-xs font-bold uppercase tracking-wider text-[#53657b]">Recorded source & confirmed context</h3><p className="mt-1 text-[10px] text-[#8293a4]">These values come from source metadata or separate human confirmation. They are not AI-triage approvals.</p></div><div className="grid sm:grid-cols-2 gap-4 text-sm">
      <div><span className="intel-label">Source / Publisher</span><p>{x.observed_publisher_handle||x.author||x.source_name||'Not recorded'}</p></div>
      <div><span className="intel-label">Confirmed jurisdiction</span><p>{jurisdiction||'Not recorded'}</p></div>
      <div><span className="intel-label">Human-confirmed monitored relationship</span><p>{x.entity_relationships?.filter(r=>r.review_status==='HUMAN_CONFIRMED').map(r=>`${r.relationship_type} · ${r.evidence_basis}`).join('; ')||'Not recorded'}</p></div>
      <div><span className="intel-label">Evidence verification status</span><Status value={x.verification_status}/></div>
    </div></div>

    {x.potential_issue_category&&<div className="border-t pt-3"><h3 className="text-xs font-bold uppercase tracking-wider">LEGACY ASSESSMENT</h3><p className="text-sm mt-2">Historical potential issue category: {x.potential_issue_category}</p><p className="text-xs text-[#617789]">Historical value only; not a current supervision signal or finding.</p></div>}
    <p className="text-xs text-[#8c9bab]">Human-accepted or human-modified triage outcomes appear as approved values. Human-rejected fields are shown as rejected, genuinely undecided suggestions are shown as awaiting review, and fields never proposed by AI are shown separately. Original source evidence and AI proposals remain unchanged.</p>
  </section>;
}
