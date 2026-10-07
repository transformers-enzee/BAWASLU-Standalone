import { parseStructuredReview } from './structuredTriage.ts';
const extraction=['actor_evidence','content_type','activity','narrative','relationships','inference','evidence_gaps'];
const signals=['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'];
export function approvedTriage(decisions,version=2,confirmedActors=[]){
 const value=key=>['Human Accepted','Human Modified'].includes(decisions?.[key]?.status)?decisions[key].value||'':'';
 if(version===3){
  const intelligence_extraction={};
  // The approved activity field is historically a human-approved activity description string.
  // Keep the complete structured proposal and decision value in ai_suggestions for provenance.
  if(value('activity'))intelligence_extraction.activity=parseStructuredReview('activity',value('activity')).description;
  if(value('narrative'))intelligence_extraction.narrative=parseStructuredReview('narrative',value('narrative')).label;
  if(value('relationships'))intelligence_extraction.relationships=parseStructuredReview('relationships',value('relationships')).map(relation=>`${relation.subject_entity_name} → ${relation.relationship_type||'related to'} → ${relation.object_entity_name||relation.observed_account}${relation.object_entity_name&&relation.observed_account&&relation.observed_account!==relation.object_entity_name?` (${relation.observed_account})`:''}`).join('; ');
  for(const key of ['actors','location_signal','topics','evidence_gaps','inferences'])if(value(key))intelligence_extraction[key]=parseStructuredReview(key,value(key));
  const confirmed=new Map(confirmedActors.filter(a=>a.id&&a.name).map(a=>[a.name.toLowerCase().trim(),a.id]));
   if(intelligence_extraction.actors)intelligence_extraction.actors=intelligence_extraction.actors.map(actor=>({...actor,entity_id:confirmed.get(actor.entity_name.toLowerCase().trim())||''}));
  if(value('content_type'))intelligence_extraction.content_type=value('content_type');
  if(['OBSERVED','INFERRED'].includes(value('evidence_type')))intelligence_extraction.evidence_type=value('evidence_type');
  const supervision_screening={};
  const signal=value('supervision_signal'),reason=value('signal_reason');
  const next=value('check_next')?parseStructuredReview('check_next',value('check_next')):[];
  const basis=value('screening_evidence_basis')?parseStructuredReview('screening_evidence_basis',value('screening_evidence_basis')):[];
  if(basis.length)supervision_screening.evidence_basis=basis;
  if(signals.includes(signal)&&(signal==='NO SIGNAL IDENTIFIED'||reason&&next.length&&basis.length))supervision_screening.supervision_signal=signal;
  if(reason)supervision_screening.signal_reason=reason;
  if(next.length)supervision_screening.check_next=next;
  if(value('screening_confidence'))supervision_screening.confidence=value('screening_confidence');
  return {intelligence_extraction,supervision_screening};
 }
 const intelligence_extraction=Object.fromEntries(extraction.map(k=>[k,value(k)]));
 const signal=value('supervision_signal'),reason=value('signal_reason'),next=value('check_next');
 const complete=signal==='NO SIGNAL IDENTIFIED'||!!(reason&&next);
 const supervision_screening={signal_reason:reason,check_next:next};
 if(complete&&signals.includes(signal))supervision_screening.supervision_signal=signal;
 if(['OBSERVED','INFERRED'].includes(value('evidence_type')))intelligence_extraction.evidence_type=value('evidence_type');
 return {intelligence_extraction,supervision_screening};
}