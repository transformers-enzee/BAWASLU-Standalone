export const triageFields=['summary','english_translation','entity','actor_evidence','content_type','activity','location','topic','narrative','relationships','inference','actors','location_signal','topics','inferences','screening_evidence_basis','screening_confidence','supervision_signal','signal_reason','check_next','priority','evidence_type','evidence_gaps','issue_category','suggested_evidence_state','analysis','reasoning','watchlist_match'];
export const humanDecisions=['Human Accepted','Human Modified','Human Rejected'];
export function triageReview(suggestions){
  const proposed=suggestions||{},decisions=proposed._decisions||{};
  const fields=triageFields.filter(key=>key==='watchlist_match'?!!proposed[key]?.id:typeof proposed[key]==='string'&&!!proposed[key].trim());
  const reviewed=fields.filter(key=>humanDecisions.includes(decisions[key]?.status)).length;
  const legacy=fields.length===0&&Object.keys(decisions).length>0;
  return {generated:fields.length>0||legacy,state:legacy?'IN REVIEW':!reviewed?'NOT STARTED':reviewed===fields.length?'REVIEW COMPLETE':'IN REVIEW',reviewed,total:fields.length,legacy};
}