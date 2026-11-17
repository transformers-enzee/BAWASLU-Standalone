// Session-only evidence-review progress. Never used to score model accuracy.
export const REVIEW_STATES=Object.freeze([
  'PENDING_REVIEW','EVIDENCE_CHECK_IN_PROGRESS','REVIEW_BLOCKED',
  'EVIDENCE_CHECKED_FOLLOWUP_NEEDED','EVIDENCE_CHECKED_NO_FURTHER_ACTION'
]);
const REVIEW_STATE_SET=new Set(REVIEW_STATES);
const ROUTE=/^[A-Z_]{1,70}$/;
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function auditReplyKey(item){
  if(!UUID.test(item?.thread_id||'')||!Number.isInteger(item?.answer_message_index)||
    item.answer_message_index<1||item.answer_message_index>59)throw Error('Invalid saved reply identity');
  return item.thread_id+':'+item.answer_message_index;
}
export function createReviewEntry(item,status='PENDING_REVIEW',evidenceChecked=false){
  auditReplyKey(item);
  if(!REVIEW_STATE_SET.has(status))throw Error('Invalid review state');
  if(typeof evidenceChecked!=='boolean')throw Error('Invalid evidence attestation');
  if(status.startsWith('EVIDENCE_CHECKED_')&&(!evidenceChecked||item.status!=='AUDITED'))
    throw Error('Evidence review and authorized audit required for this outcome');
  if(!ROUTE.test(item.review_route||''))throw Error('Missing review route');
  return Object.freeze({
    thread_id:item.thread_id,answer_message_index:item.answer_message_index,
    audit_status:item.status,review_route:item.review_route,
    review_state:status,original_evidence_checked:evidenceChecked,
    attributed_to_verified_model_generation:false,formal_legal_signoff:false,
    formal_client_acceptance:false,accuracy_score:null
  });
}
export function exportReviewWorksheet(rows){
  if(!Array.isArray(rows)||rows.length===0||rows.length>5)
    throw Error('Select between one and five audited replies');
  const seen=new Set();
  const entries=rows.map(row=>{
    const key=auditReplyKey(row);
    if(seen.has(key))throw Error('Duplicate review entry');
    seen.add(key);
    // Re-validate even if the caller passes a forged entry.
    const recreated=createReviewEntry({
      thread_id:row.thread_id,answer_message_index:row.answer_message_index,
      status:row.audit_status,review_route:row.review_route
    },row.review_state,row.original_evidence_checked);
    return recreated;
  });
  return JSON.stringify({
    schema:'BAWASLU_LOCAL_SAVED_REPLY_REVIEW_WORKSHEET_V1629',
    scope:'CURRENT_BROWSER_SESSION_ONLY',entries,
    human_accuracy:null,verified_model_errors:0,
    formal_legal_signoff:false,formal_client_acceptance:false,
    contains_answer_text:false,contains_source_excerpts:false,
    reviewer_identity_verified:false,reviewer_attestation_is_self_reported:true,
    database_writes:0
  },null,2);
}
