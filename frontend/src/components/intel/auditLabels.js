export const suggestionTypes={summary:'AI SUMMARY',english_translation:'AI TRANSLATION',entity:'ENTITY',location:'LOCATION',topic:'TOPIC',issue_category:'ISSUE CATEGORY',priority:'PRIORITY',suggested_evidence_state:'EVIDENCE STATE',analysis:'AI ANALYSIS',reasoning:'AI RATIONALE',watchlist_match:'WATCHLIST MATCH',source_facts:'SOURCE FACTS',actor_evidence:'ACTOR EVIDENCE',content_type:'CONTENT TYPE',activity:'ACTIVITY',narrative:'NARRATIVE',relationships:'RELATIONSHIP',inference:'INFERENCE',supervision_signal:'SUPERVISION SIGNAL',signal_reason:'SIGNAL REASON',check_next:'CHECK NEXT',evidence_type:'EVIDENCE TYPE',evidence_gaps:'EVIDENCE GAPS'};

const fieldKey={
 summary:'suggestion_summary',
 english_translation:'suggestion_translation',
 entity:'suggestion_entity',
 location:'suggestion_location',
 topic:'suggestion_topic',
 issue_category:'suggestion_issue_category',
 priority:'suggestion_priority',
 suggested_evidence_state:'suggestion_evidence_state',
 analysis:'suggestion_analysis',
 reasoning:'suggestion_reasoning',
 watchlist_match:'possible_watchlist_match',
 source_facts:'triage_source_facts',
 actor_evidence:'suggestion_actor_evidence',
 content_type:'suggestion_content_type',
 activity:'suggestion_activity',
 narrative:'suggestion_narrative',
 relationships:'suggestion_relationships',
 inference:'suggestion_inference',
 supervision_signal:'suggestion_supervision_signal',
 signal_reason:'suggestion_signal_reason',
 check_next:'suggestion_check_next',
 evidence_type:'suggestion_evidence_type',
 evidence_gaps:'suggestion_evidence_gaps'
};

const actionKey={
 UPDATED:'audit_updated',
 CREATED:'audit_created',
 SOURCE_ACCOUNT_UPDATED:'audit_source_account_updated',
 SOURCE_ACCOUNT_ADDED:'audit_source_account_added',
 SOURCE_ACCOUNT_REMOVED:'audit_source_account_removed',
 RELATIONSHIP_ADDED:'audit_relationship_added',
 RELATIONSHIP_REMOVED:'audit_relationship_removed',
 SOURCE_RECOVERED:'audit_source_recovered',
 GEOGRAPHIC_MISMATCH_REVIEWED:'audit_geographic_reviewed',
 WATCHLIST_UPDATED:'audit_watchlist_updated'
};

const identity=x=>x;
const statusText=(status,t)=>{
 const raw=(status||'REVIEWED').replace('Human ','').toUpperCase();
 if(raw==='ACCEPTED')return t('audit_accepted');
 if(raw==='MODIFIED')return t('audit_modified');
 if(raw==='REJECTED')return t('audit_rejected');
 return t('audit_reviewed');
};

export function auditTitle(ev,field,change,t=identity){
 if(ev.action==='WATCHLIST_MATCH_REVIEWED'){
  const linked=ev.changes?.decision?.new==='Link';
  return t('possible_watchlist_match')+' — '+(linked?t('audit_accepted')+' & '+t('audit_linked'):t('audit_rejected'));
 }
 if(ev.action==='AI_SUGGESTION_DECIDED'||ev.action==='AI_SUGGESTIONS_REVIEWED'){
  const entry=field?{field,change}:Object.entries(ev.changes||{}).filter(([k])=>suggestionTypes[k]).map(([k,v])=>({field:k,change:v}))[0];
  if(entry){
   const status=statusText(entry.change?.status,t);
   return t(fieldKey[entry.field]||entry.field)+' — '+status+(entry.field==='watchlist_match'&&entry.change?.status!=='Human Rejected'?' & '+t('audit_linked'):'');
  }
 }
 if(actionKey[ev.action])return t(actionKey[ev.action]);
 return ev.action.replaceAll('_',' ');
}
