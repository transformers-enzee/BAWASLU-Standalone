export const suggestionTypes={summary:'AI SUMMARY',english_translation:'AI TRANSLATION',entity:'ENTITY',location:'LOCATION',topic:'TOPIC',issue_category:'ISSUE CATEGORY',priority:'PRIORITY',suggested_evidence_state:'EVIDENCE STATE',analysis:'AI ANALYSIS',reasoning:'AI RATIONALE',watchlist_match:'WATCHLIST MATCH',source_facts:'SOURCE FACTS',actor_evidence:'ACTOR EVIDENCE',content_type:'CONTENT TYPE',activity:'ACTIVITY',narrative:'NARRATIVE',relationships:'RELATIONSHIP',inference:'INFERENCE',supervision_signal:'SUPERVISION SIGNAL',signal_reason:'SIGNAL REASON',check_next:'CHECK NEXT',evidence_type:'EVIDENCE TYPE',evidence_gaps:'EVIDENCE GAPS'};
export function auditTitle(ev,field,change){
 if(ev.action==='WATCHLIST_MATCH_REVIEWED')return `WATCHLIST MATCH — ${ev.changes?.decision?.new==='Link'?'ACCEPTED & LINKED':'REJECTED'}`;
 if(ev.action==='AI_SUGGESTION_DECIDED'||ev.action==='AI_SUGGESTIONS_REVIEWED'){
  const entry=field?{field,change}:Object.entries(ev.changes||{}).filter(([k])=>suggestionTypes[k]).map(([k,v])=>({field:k,change:v}))[0];
  if(entry){const status=entry.change?.status?.replace('Human ','').toUpperCase()||'REVIEWED';return `${suggestionTypes[entry.field]} — ${status}${entry.field==='watchlist_match'&&status!=='REJECTED'?' & LINKED':''}`;}
 }
 return ev.action.replaceAll('_',' ');
}