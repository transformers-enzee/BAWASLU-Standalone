import Status from './Status';
import { activityLabel, narrativeLabel, locationLabel, actorLabels, relationshipLabels, screeningNext, gapsLabel } from './actorPictureView';

const listText=value=>Array.isArray(value)?value.filter(Boolean).join(' · '):value||'';
const actorText=value=>Array.isArray(value)?value.map(a=>typeof a==='string'?a:[a?.entity_name,a?.relationship_to_content].filter(Boolean).join(' · ')).filter(Boolean).join(', '):value||'';
const relationshipText=value=>Array.isArray(value)?value.map(r=>typeof r==='string'?r:`${r?.subject_entity_name||'Actor'} · ${r?.relationship_type||'related to'} · ${r?.object_entity_name||r?.observed_account||'source'}`).filter(Boolean).join('; '):value||'';
const activityText=value=>typeof value==='string'?value:[value?.type,value?.description].filter(Boolean).join(' · ');
const narrativeText=value=>typeof value==='string'?value:[value?.label,value?.description].filter(Boolean).join(' · ');
const locationText=value=>typeof value==='string'?value:value?.location_text||'';

export default function IntelligenceSummary({item}){
  const x=item,e=x.intelligence_extraction||{},s=x.supervision_screening||{},approved=x.human_approved_triage?.values||{},provenance=x.human_approved_triage?.provenance||{};
  const happened=approved.summary||x.ai_summary;
  const actors=actorText(approved.actors||approved.entity)||[...(x.related_entities||[]),...actorLabels(e)].filter(Boolean).join(', ');
  const where=locationText(approved.location_signal||approved.location)||locationLabel(e,x);
  const activity=activityText(approved.activity)||activityLabel(e);
  const narrative=narrativeText(approved.narrative)||narrativeLabel(e);
  const relationships=relationshipText(approved.relationships)||relationshipLabels(e).join('; ')||(typeof e.relationships==='string'?e.relationships:'');
  const signal=approved.supervision_signal||s.supervision_signal;
  const screeningConfidence=approved.screening_confidence||s.confidence;
  const signalReason=approved.signal_reason||s.signal_reason;
  const checkNext=listText(approved.check_next)||screeningNext(s);
  const evidenceBasis=listText(approved.screening_evidence_basis)||(Array.isArray(s.evidence_basis)?s.evidence_basis.join(' · '):'');
  const gaps=listText(approved.evidence_gaps)||gapsLabel(e);
  const priority=approved.priority||x.priority;
  const rows=[
    ['What happened',happened,'summary'],
    ['Who is involved',actors,approved.actors?'actors':approved.entity?'entity':''],
    ['Where',where,approved.location_signal?'location_signal':approved.location?'location':''],
    ['Activity',activity,approved.activity?'activity':''],
    ['Narrative',narrative,approved.narrative?'narrative':''],
    ['Source / Publisher',x.observed_publisher_handle||x.author||x.source_name,''],
    ['Human-confirmed monitored relationship',x.entity_relationships?.filter(r=>r.review_status==='HUMAN_CONFIRMED').map(r=>`${r.relationship_type} · ${r.evidence_basis}`).join('; '),''],
    ['Extracted relationship · not ownership',relationships,approved.relationships?'relationships':''],
    ['Supervision signal',signal,approved.supervision_signal?'supervision_signal':''],
    ['Screening confidence',screeningConfidence,approved.screening_confidence?'screening_confidence':''],
    ['Why attention may be warranted',signalReason,approved.signal_reason?'signal_reason':''],
    ['What to check next',checkNext,approved.check_next?'check_next':''],
    ['Screening evidence basis',evidenceBasis,approved.screening_evidence_basis?'screening_evidence_basis':''],
    ['Evidence gaps',gaps,approved.evidence_gaps?'evidence_gaps':'']
  ];
  const approvedCount=x.human_approved_triage?.approved_count||0;
  return <section className="intel-card p-6 space-y-4"><h2 className="font-semibold text-lg">Intelligence Summary</h2><p className="font-medium">{x.title}</p><div className="flex flex-wrap items-center gap-2"><p className="text-[11px] font-bold uppercase tracking-wider text-[#267291]">FINAL SUMMARY · HUMAN-APPROVED ONLY</p>{approvedCount>0&&<span className="text-[11px] rounded-full bg-[#eef5f8] px-2 py-1 text-[#42657a]">{approvedCount} triage field{approvedCount===1?'':'s'} human-approved</span>}</div><div className="grid sm:grid-cols-2 gap-4 text-sm">{rows.map(([label,value,key])=><div key={label}><span className="intel-label">{label}</span><p className="whitespace-pre-wrap">{value||'Not yet human-approved / recorded'}</p>{key&&provenance[key]&&<p className="mt-1 text-[10px] text-[#8293a4]">Human {provenance[key].decision==='Human Modified'?'modified':'accepted'} · {provenance[key].reviewer||'authorized reviewer'}{provenance[key].decided_at?` · ${new Date(provenance[key].decided_at).toLocaleString('en-GB')}`:''}</p>}</div>)}<div><span className="intel-label">Priority</span><Status value={priority}/>{approved.priority&&provenance.priority&&<p className="mt-1 text-[10px] text-[#8293a4]">Human {provenance.priority.decision==='Human Modified'?'modified':'accepted'} · {provenance.priority.reviewer||'authorized reviewer'}</p>}</div></div>{x.potential_issue_category&&<div className="border-t pt-3"><h3 className="text-xs font-bold uppercase tracking-wider">LEGACY ASSESSMENT</h3><p className="text-sm mt-2">Historical potential issue category: {x.potential_issue_category}</p><p className="text-xs text-[#617789]">Historical value only; not a current supervision signal or finding.</p></div>}{signal&&<p className="text-xs text-[#617789]">This supervision signal does not establish a violation. Regulatory assessment is separate.</p>}<p className="text-xs text-[#8c9bab]">Only accepted or human-modified triage outcomes can appear here. Rejected and pending AI suggestions are excluded. Original source evidence and AI proposals remain unchanged.</p></section>;
}
