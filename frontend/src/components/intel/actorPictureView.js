export const activityLabel=e=>typeof e?.activity==='string'?e.activity:[e?.activity?.type,e?.activity?.description].filter(Boolean).join(' · ');
export const narrativeLabel=e=>typeof e?.narrative==='string'?e.narrative:[e?.narrative?.label,e?.narrative?.description].filter(Boolean).join(' · ');
export const locationLabel=(e,record)=>e?.location_signal?.location_text||record.location_text||record.regency_city||record.province||'';
export const actorLabels=e=>Array.isArray(e?.actors)?e.actors.map(a=>[a.entity_name,a.relationship_to_content].filter(Boolean).join(' · ')).filter(Boolean):[];
export const relationshipLabels=e=>Array.isArray(e?.relationships)?e.relationships.map(r=>`${r.subject_entity_name||'Actor'} · ${r.relationship_type||'related to'} · ${r.object_entity_name||r.observed_account||'source'}`).filter(Boolean):[];
export const screeningNext=s=>Array.isArray(s?.check_next)?s.check_next.join(' · '):s?.check_next||'';
export const gapsLabel=e=>Array.isArray(e?.evidence_gaps)?e.evidence_gaps.join(' · '):e?.evidence_gaps||'';