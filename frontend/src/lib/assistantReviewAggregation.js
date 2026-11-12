/** v148.7 — Local-only consolidation of independent human answer-review sheets.
 *
 * No API, DB, model invocation or storage. Uploaded JSON packets and CSV sheets
 * are user-supplied assertions; identities, source truth and client approvals
 * cannot be verified cryptographically by this browser-only workflow.
 */
import {assistantReviewPacketId} from './assistantReviewPacket.js';

export const REVIEW_DIMENSIONS=[
 'citation_grounding','source_relevance','legal_uncertainty',
 'cross_module_consistency'
];
const requiredHeaders=[
 'packet_id','dimension','automated_status','human_score_0_1_NA',
 'evidence_reference','reviewer_note','reviewer_id','review_date_utc'
];
const adjudicationHeaders=[
 'adjudicated_score_0_1_NA','adjudicator_id','adjudication_note'
];
const MAX_CSV=2000000;
const MAX_ROWS=3000;

const scoreValue=value=>{
 const v=String(value??'').trim().toUpperCase();
 return v==='NA'?'N/A':v;
};
const goodScore=value=>['0','1','N/A'].includes(value);
const safeIdentity=value=>/^[A-Za-z0-9][A-Za-z0-9_.@-]{2,79}$/.test(value);
const validDate=value=>{
 const s=String(value||'').trim();
 return /^\d{4}-\d\d-\d\d(?:T\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d))?$/.test(s)
  &&!Number.isNaN(Date.parse(s));
};
const sorted=x=>[...x].sort();

export function parseReviewCsv(text){
 const raw=String(text??'').replace(/^\uFEFF/,'');
 if(raw.length>MAX_CSV)throw new Error('CSV exceeds the 2 MB local-import limit.');
 const rows=[],fields=[];
 let field='',inside=false,closed=false;
 const flushField=()=>{fields.push(field);field='';closed=false};
 const flushRow=()=>{
  flushField();
  if(fields.some(v=>v!==''))rows.push(fields.splice(0));
  else fields.splice(0);
  if(rows.length>MAX_ROWS+1)throw new Error('Too many CSV rows.');
 };
 for(let i=0;i<raw.length;i++){
  const c=raw[i];
  if(inside){
   if(c==='"'&&raw[i+1]==='"'){field+='"';i++}
   else if(c==='"'){inside=false;closed=true}
   else field+=c;
  }else if(c==='"'&&field===''&&!closed){inside=true}
  else if(c==='"'){throw new Error('Unexpected quote in CSV.')}
  else if(c===','){flushField()}
  else if(c==='\n'||c==='\r'){
   if(c==='\r'&&raw[i+1]==='\n')i++;
   flushRow();
  }else{
   if(closed&&!/\s/.test(c))throw new Error('Unexpected text after a quoted field.');
   field+=c;
  }
 }
 if(inside)throw new Error('Unclosed CSV quotation.');
 if(field!==''||fields.length||closed)flushRow();
 if(!rows.length)throw new Error('Scoring CSV has no header.');
 const header=rows.shift().map(x=>x.trim());
 if(new Set(header).size!==header.length)throw new Error('Duplicate CSV headers.');
 for(const h of requiredHeaders){
  if(!header.includes(h))throw new Error('Missing required CSV column: '+h);
 }
 const content=rows.map((cells,index)=>{
  if(cells.length!==header.length)throw new Error('CSV column mismatch on row '+(index+2));
  return Object.fromEntries(header.map((h,i)=>[h,cells[i].trim()]));
 });
 if(content.length!==4)throw new Error('Each review CSV must contain exactly four dimension rows.');
 if(new Set(content.map(row=>row.dimension)).size!==4||
    content.some(row=>!REVIEW_DIMENSIONS.includes(row.dimension))){
  throw new Error('Scoring CSV must contain one row for each of the four evaluation dimensions.');
 }
 const packetIds=new Set(content.map(row=>row.packet_id));
 if(packetIds.size!==1||!/^AR-[a-f0-9]{8}$/.test(content[0].packet_id)){
  throw new Error('All rows must refer to the same valid packet ID.');
 }
 const result=[];
 for(const row of content){
  const score=scoreValue(row.human_score_0_1_NA);
  const adjudication=scoreValue(row.adjudicated_score_0_1_NA);
  const reviewerId=row.reviewer_id||'';
  const note=row.reviewer_note||'';
  const evidence=row.evidence_reference||'';
  const adjudicatorId=row.adjudicator_id||'';
  const adjudicationNote=row.adjudication_note||'';
  const date=row.review_date_utc||'';
  if(score){
   if(!goodScore(score))throw new Error('Invalid reviewer score on '+row.dimension);
   if(!safeIdentity(reviewerId))throw new Error('Invalid or missing reviewer ID on '+row.dimension);
   if(!validDate(date))throw new Error('A real review date is required on '+row.dimension);
   if(note.length<12)throw new Error('Explain the human score (12+ characters) on '+row.dimension);
   if(score!=='N/A'&&!evidence)throw new Error('Cite inspected evidence on '+row.dimension);
  }else if(reviewerId||note||evidence||date){
   throw new Error('Partial reviewer row without a score on '+row.dimension);
  }
  if(adjudication){
   if(!goodScore(adjudication))throw new Error('Invalid adjudication score on '+row.dimension);
   if(!safeIdentity(adjudicatorId))throw new Error('Invalid adjudicator ID on '+row.dimension);
   if(adjudicationNote.length<12)throw new Error('Adjudication requires a reason on '+row.dimension);
  }else if(adjudicatorId||adjudicationNote){
   throw new Error('Partial adjudication row on '+row.dimension);
  }
  if(score||adjudication)result.push({
   packet_id:row.packet_id,dimension:row.dimension,score:score||null,
   reviewer_id:reviewerId,date,note,evidence_reference:evidence,
   adjudicated_score:adjudication||null,adjudicator_id:adjudicatorId,
   adjudication_note:adjudicationNote
  });
 }
 return {packet_id:content[0].packet_id,entries:result,
   schema_has_adjudication_fields:adjudicationHeaders.every(x=>header.includes(x))};
}

export function validateReviewPacket(value){
 if(!value||value.schema_version!=='BAWASLU_ASSISTANT_REVIEW_V1485')
  throw new Error('Unsupported or invalid review packet schema.');
 if(typeof value.question!=='string'||typeof value.assistant_answer!=='string'||
    !value.question.trim()||!value.assistant_answer.trim())
  throw new Error('The review packet must contain the original question and answer.');
 const expected=assistantReviewPacketId(value.question,value.assistant_answer);
 if(value.packet_id!==expected||!/^AR-[a-f0-9]{8}$/.test(expected))
  throw new Error('Packet ID does not match the supplied question and answer.');
 const dims=value.human_scorecard?.checks;
 if(!Array.isArray(dims)||dims.length!==4||
    sorted(dims.map(x=>x.id)).join('|')!==sorted(REVIEW_DIMENSIONS).join('|'))
  throw new Error('Review packet lacks the four expected scoring dimensions.');
 // Non-cryptographic ID detects accidental mismatches only.
 return {
  packet_id:value.packet_id,
  question:value.question,
  answer:value.assistant_answer,
  answer_length:value.assistant_answer.length,
  evidence_count:Number(value.evidence_snapshot?.exported_records?.length||0),
  truncated:!!value.evidence_snapshot?.truncated||!!value.assistant_answer_truncated
 };
}

const reviewState=(entries)=>{
 const byPerson=new Map();
 const conflictingReviewers=new Set();
 const adjudications=[];
 for(const e of entries){
  if(e.score){
   const former=byPerson.get(e.reviewer_id);
   if(former&&JSON.stringify([former.score,former.note,former.evidence_reference,former.date])!==
     JSON.stringify([e.score,e.note,e.evidence_reference,e.date])){
    conflictingReviewers.add(e.reviewer_id);
   }else byPerson.set(e.reviewer_id,e);
  }
  if(e.adjudicated_score)adjudications.push(e);
 }
 const ratings=[...byPerson.values()];
 const identities=new Set(byPerson.keys());
 const base={reviewer_count:ratings.length,conflicting_reviewers:conflictingReviewers.size,
   final_score:null,agreement:false,adjudicated:false,
   status:'AWAITING_TWO_REVIEWERS'};
 if(conflictingReviewers.size)return {...base,status:'CONFLICTING_SHEETS'};
 if(ratings.length<2)return base;
 if(ratings.length>2)return {...base,status:'EXTRA_REVIEWERS_NEED_RESOLUTION'};
 const [left,right]=ratings;
 const agreement=left.score===right.score;
 const scores=adjudications.filter(e=>e.adjudicator_id&&
   !identities.has(e.adjudicator_id));
 const invalidAdjudication=adjudications.length!==scores.length;
 if(agreement){
  // Two independent ratings agree. An unnecessary adjudication cannot
  // silently override their consensus.
  if(adjudications.length)return {...base,agreement:true,
    status:'UNNEEDED_ADJUDICATION_REQUIRES_REVIEW'};
  return {...base,agreement:true,final_score:left.score,
    status:left.score==='N/A'?'AGREED_NOT_APPLICABLE':'AGREED'};
 }
 if(invalidAdjudication)return {...base,status:'ADJUDICATOR_NOT_INDEPENDENT'};
 if(scores.length===0)return {...base,status:'DISAGREEMENT_UNRESOLVED'};
 const distinct=new Set(scores.map(e=>e.adjudicator_id+':'+e.adjudicated_score+
   ':'+e.adjudication_note));
 if(distinct.size!==1)return {...base,status:'CONFLICTING_ADJUDICATIONS'};
 return {...base,adjudicated:true,final_score:scores[0].adjudicated_score,
   status:scores[0].adjudicated_score==='N/A'?'ADJUDICATED_NOT_APPLICABLE':'ADJUDICATED'};
};

export function aggregateAssistantReviews(packetValues=[],sheetValues=[]){
 const errors=[];
 const packets=new Map();
 for(const item of packetValues){
  try{
   const p=validateReviewPacket(item);
   const earlier=packets.get(p.packet_id);
   if(earlier&&JSON.stringify(earlier)!==JSON.stringify(p))
     throw new Error('Conflicting JSON packets share an ID.');
   packets.set(p.packet_id,p);
  }catch(e){errors.push('Packet rejected: '+e.message)}
 }
 const submissions=[];
 for(const sheet of sheetValues){
  try{
   const parsed=typeof sheet==='string'?parseReviewCsv(sheet):sheet;
   if(!parsed||!Array.isArray(parsed.entries))throw new Error('Invalid scoring sheet.');
   if(!packets.has(parsed.packet_id))throw new Error(
     'Missing matching JSON evidence packet for '+String(parsed.packet_id));
   submissions.push(parsed);
  }catch(e){errors.push('Scoring sheet rejected: '+e.message)}
 }
 const entries=new Map();
 for(const parsed of submissions){
  for(const entry of parsed.entries){
   if(!REVIEW_DIMENSIONS.includes(entry.dimension))continue;
   const key=parsed.packet_id+'\0'+entry.dimension;
   const current=entries.get(key)||[];
   current.push(entry);
   entries.set(key,current);
  }
 }
 const cases=[];
 const stats=REVIEW_DIMENSIONS.map(dimension=>({
  dimension,packet_count:packets.size,
  consensus_scored:0,consensus_supported:0,consensus_unsupported:0,
  agreed_not_applicable:0,awaiting_review:0,
  disagreement_unresolved:0,adjudicated:0,
  independent_agreements:0,independent_pairs:0,
  score_1_support_rate_percent:null,reviewer_agreement_percent:null
 }));
 for(const packet of packets.values()){
  for(const [index,dimension] of REVIEW_DIMENSIONS.entries()){
   const row=reviewState(entries.get(packet.packet_id+'\0'+dimension)||[]);
   const metric=stats[index];
   const counted=['AGREED','ADJUDICATED'].includes(row.status);
   if(counted){
    metric.consensus_scored++;
    if(row.final_score==='1')metric.consensus_supported++;
    else metric.consensus_unsupported++;
   }else if(row.final_score==='N/A'){
    metric.agreed_not_applicable++;
   }else{
    metric.awaiting_review++;
    if(row.reviewer_count>=2&&(!row.agreement||
       row.status==='CONFLICTING_SHEETS'))metric.disagreement_unresolved++;
   }
   if(row.status.startsWith('ADJUDICATED'))metric.adjudicated++;
   if(row.reviewer_count===2&&!row.conflicting_reviewers){
    metric.independent_pairs++;
    if(row.agreement)metric.independent_agreements++;
   }
   cases.push({packet_id:packet.packet_id,dimension,
    status:row.status,reviewer_count:row.reviewer_count,
    final_score:row.final_score});
  }
 }
 for(const m of stats){
  if(m.consensus_scored>0)m.score_1_support_rate_percent=
    Math.round(m.consensus_supported*1000/m.consensus_scored)/10;
  if(m.independent_pairs>0)m.reviewer_agreement_percent=
    Math.round(m.independent_agreements*1000/m.independent_pairs)/10;
 }
 return {
  framework:'BAWASLU_OFFLINE_HUMAN_REVIEW_AGGREGATION_V1487',
  packet_count:packets.size,scoring_sheets_accepted:submissions.length,
  dimension_stats:stats,cases,errors,
  has_any_consensus_score:stats.some(x=>x.consensus_scored>0),
  human_accuracy_percentage:null,
  score_basis:'TWO_SELF_DECLARED_DISTINCT_REVIEWERS_OR_INDEPENDENT_ADJUDICATOR',
  identities_verified:false,source_permissions_rechecked:false,
  packet_authenticity_cryptographically_verified:false,
  client_acceptance_certified:false,legal_currentness_verified:false,
  all_processing_in_browser:true,server_upload_performed:false,
  paid_model_called:false
 };
}

export function aggregateSummaryJson(result){
 if(!result||result.framework!=='BAWASLU_OFFLINE_HUMAN_REVIEW_AGGREGATION_V1487')
   throw new Error('Invalid review consolidation.');
 // Do not copy question/answer/evidence, reviewer names or reviewer notes to
 // this compact aggregate. Keep the original packets in authorized custody.
 return JSON.stringify({
  schema_version:result.framework,
  created_at_utc:new Date().toISOString(),
  packet_count:result.packet_count,
  scoring_sheets_accepted:result.scoring_sheets_accepted,
  dimension_stats:result.dimension_stats,
  cases:result.cases,
  errors:result.errors,
  human_accuracy_percentage:null,
  client_acceptance_certified:false,
  identities_verified:false,
  packet_authenticity_cryptographically_verified:false
 },null,2);
}
