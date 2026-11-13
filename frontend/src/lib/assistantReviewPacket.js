/** v148.5 — Local, explicitly requested officer answer-review exports.
 * Packet contents are copied only from evidence already visible to this
 * authenticated Assistant user; no API request or automatic upload is made.
 * Blank human scoring fields MUST NOT imply approval or measured accuracy.
 */
const DIMENSIONS=[
  ['citation_grounding','Citation grounding'],
  ['source_relevance','Topical source relevance'],
  ['legal_uncertainty','Legal uncertainty'],
  ['cross_module_consistency','Cross-module consistency']
];
const asText=(value,max=1600)=>String(value??'').slice(0,max);
const safeHttpUrl=value=>{
  try{
    const url=new URL(String(value||''));
    return ['http:','https:'].includes(url.protocol)?url.href:'';
  }catch{return ''}
};
const nonCryptoFingerprint=value=>{
  let hash=2166136261;
  for(const c of String(value)){hash^=c.codePointAt(0);hash=Math.imul(hash,16777619)}
  return (hash>>>0).toString(16).padStart(8,'0');
};
export const assistantReviewPacketId=(question,answer)=>
  'AR-'+nonCryptoFingerprint(String(question??'')+'\0'+String(answer??''));

const sourceView=row=>({
  record_id:asText(row.record_id||row.intelligence_id||row.id,120),
  record_type:asText(row.record_type,60),
  title:asText(row.title,220),
  source_excerpt:asText(row.source_excerpt,600),
  source_url:safeHttpUrl(row.source_url),
  source_name:asText(row.source_name,120),
  source_post_id:asText(row.source_post_id,60),
  campaign_id:row.campaign_id??null,
  platform:asText(row.platform,60),
  publication_date:asText(row.publication_date,70),
  sentiment:asText(row.sentiment,25),
  document_id:row.document_id??null,
  page:row.page??null,
  document_type:asText(row.document_type,60),
  review_status:asText(row.review_status,60),
  verification_status:asText(row.verification_status,70)
});
const legalReviewSnapshot=(raw,cited)=>{
  if(!raw?.applicable)return null;
  const authorized=new Set(Array.isArray(cited)?cited.map(x=>String(x)):[]);
  const allowedCodes=new Set(['LEGAL_OUTCOME_OR_ACTION','ELIGIBLE_LEGAL_SOURCE_MISSING','CITATION_INTEGRITY',
    'ARTICLE_OR_CLAIM_ATTRIBUTION','PASSAGE_POLARITY','NUMERIC_OR_DATE','ELECTION_SCOPE',
    'DOCUMENT_REVIEW_PENDING','SOURCE_RELEVANCE','VERSION_OR_EFFECTIVE_DATE']);
  const issues=(Array.isArray(raw.issues)?raw.issues:[]).filter(x=>allowedCodes.has(x?.code)).slice(0,10).map(x=>({
    code:x.code,priority:['P1','P2','P3'].includes(x.priority)?x.priority:'P3',
    source_ids:(Array.isArray(x.source_ids)?x.source_ids:[]).map(x=>asText(x,120)).filter(x=>authorized.has(x)).slice(0,12),
    signal_count:Number.isInteger(x.signal_count)?Math.max(0,Math.min(99,x.signal_count)):0
  }));
  return {schema:'BAWASLU_LEGAL_REVIEW_SUMMARY_V1529',
    officer_review_required:true,legal_findings_confirmed:false,
    legal_currentness_verified:false,source_truth_verified:false,
    review_priority_is_legal_severity:false,issues};
};
const csvEscape=value=>{
  let s=String(value??'');
  // Prevent Excel/Sheets CSV formula injection from source or answer text.
  if(/^[\s]*[=+@-]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
};
const csvRow=fields=>fields.map(csvEscape).join(',');

export function buildAssistantReviewPacket({question,answer,buildVersion='unknown',exportedAt}={}){
  const q=asText(question,1000);
  const response=answer||{};
  const originalAnswer=String(response.text??'');
  const answerText=originalAnswer.slice(0,100000);
  if(!q||!answerText||response.role!=='assistant'){
    throw new Error('An existing question and Assistant answer are required.');
  }
  const records=Array.isArray(response.records)?response.records:[];
  const rawChecks=response.grounding?.answer_quality?.checks||[];
  const review=Object.fromEntries(rawChecks.map(c=>[c.id,c]));
  const cited=response.grounding?.grounding_audit?.displayed_citation_ids||[];
  const packetId=assistantReviewPacketId(q,answerText);
  const snapshot={
    schema_version:'BAWASLU_ASSISTANT_REVIEW_V1485',
    packet_id:packetId,
    packet_id_is_cryptographic_signature:false,
    export_time_utc:asText(exportedAt||new Date().toISOString(),40),
    app_build_version:asText(buildVersion,30),
    review_state:'AWAITING_HUMAN_ASSESSMENT',
    officer_approved:false,
    legal_findings_confirmed:false,
    human_accuracy:null,
    human_gold_answers_evaluated:0,
    note:'Downloaded by an authorized logged-in user. Source excerpts can be sensitive: store securely and do not distribute outside permitted channels.',
    question:q,
    assistant_answer:answerText,
    assistant_answer_truncated:originalAnswer.length>answerText.length,
    question_truncated:String(question??'').length>q.length,
    response_profile:asText(response.response_profile,60),
    response_language:asText(response.answer_language,16),
    provider_mode:asText(response.provider?.mode,60),
    model_identifier:asText(response.provider?.model,100),
    cited_source_ids:Array.isArray(cited)?cited.map(x=>asText(x,120)).slice(0,40):[],
    evidence_snapshot:{
      selected_records_in_chat:records.length,
      exported_records:records.slice(0,25).map(sourceView),
      truncated:records.length>25,
      excerpts_truncated_to_characters:600,
      evidence_truth_verified:false,
      source_permissions_rechecked_at_export:false,
      source_access_basis:'ALREADY_VISIBLE_AUTHORIZED_ASSISTANT_CHAT',
      source_refs_are_not_officer_approved:true
    },
    legal_review_snapshot:legalReviewSnapshot(response.grounding?.answer_quality?.legal_review_summary,cited),
    automated_checks:{
      framework:asText(response.grounding?.answer_quality?.framework,80),
      diagnostic_only:true,
      measured_model_accuracy:false,
      checks:DIMENSIONS.map(([id,label])=>({
        id,label,
        automated_status:asText(review[id]?.status||'NOT_RUN',25),
        automated_reason:asText(review[id]?.reason,400)
      }))
    },
    human_scorecard:{
      rubric:'Score each dimension 0 (incorrect/unsupported), 1 (correct/supported), or N/A; cite observed primary evidence.',
      reviewer_id:'',
      reviewed_at_utc:null,
      adjudicator_id:'',
      adjudicated_at_utc:null,
      reviewed_source_ids:[],
      checks:DIMENSIONS.map(([id,label])=>({
        id,label,human_score:null,evidence_reference:'',reviewer_note:''
      }))
    }
  };
  return snapshot;
}

export function assistantReviewScorecardCsv(packet){
  if(!packet||packet.schema_version!=='BAWASLU_ASSISTANT_REVIEW_V1485'){
    throw new Error('Invalid reviewer packet.');
  }
  const header=['packet_id','dimension','automated_status','human_score_0_1_NA',
    'evidence_reference','reviewer_note','reviewer_id','review_date_utc',
    'adjudicated_score_0_1_NA','adjudicator_id','adjudication_note'];
  const rows=(packet.human_scorecard?.checks||[]).map(check=>{
    const automated=(packet.automated_checks?.checks||[]).find(item=>item.id===check.id);
    return [packet.packet_id,check.id,automated?.automated_status||'NOT_RUN','','','','','','','',''];
  });
  return '\ufeff'+[csvRow(header),...rows.map(csvRow)].join('\r\n')+'\r\n';
}

export function downloadAssistantReviewFile(packet,format='json'){
  if(!packet||packet.schema_version!=='BAWASLU_ASSISTANT_REVIEW_V1485'){
    throw new Error('Invalid reviewer packet.');
  }
  if(!['json','csv'].includes(format))throw new Error('Invalid review export format.');
  const filename='BAWASLU-assistant-review-'+packet.packet_id+'.'+format;
  const body=format==='json'?JSON.stringify(packet,null,2):assistantReviewScorecardCsv(packet);
  const blob=new Blob([body],{type:format==='json'
    ?'application/json;charset=utf-8':'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download=filename;link.click();
  // The source remains on the client's device only after explicit click.
  setTimeout(()=>URL.revokeObjectURL(url),10000);
  return filename;
}
