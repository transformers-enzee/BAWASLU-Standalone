/** v149.2: offline officer-authored scoring sheets for genuinely reviewed answers.
 * An imported packet and local form cannot prove reviewer identity or approval.
 * No server, model, storage or network operations occur in this module.
 */
import {REVIEW_DIMENSIONS,validateReviewPacket,parseReviewCsv} from './assistantReviewAggregation.js';

export const blankOfficerScores=()=>Object.fromEntries(
 REVIEW_DIMENSIONS.map(id=>[id,{score:'',evidence_reference:'',reviewer_note:''}])
);
const knownScore=s=>['0','1','N/A'].includes(s);
const reviewerIdValid=id=>/^[A-Za-z0-9][A-Za-z0-9_.@-]{2,79}$/.test(id);
const humanScore=row=>String(row?.score||'').trim().toUpperCase();
const encodeCell=value=>{
 let valueText=String(value??'');
 // Prevent spreadsheet applications from interpreting review content as formulas.
 if(/^\s*[=+@-]/.test(valueText))valueText="'"+valueText;
 return '"'+valueText.replace(/"/g,'""')+'"';
};
const csvLine=values=>values.map(encodeCell).join(',');

export function officerScoreCompletion(packet,ratings,reviewerId){
 const errors=[];
 try{validateReviewPacket(packet)}catch(e){errors.push(e.message)}
 if(!reviewerIdValid(String(reviewerId||'').trim()))
  errors.push('Enter a reviewer ID of 3 to 80 letters, numbers or permitted separators.');
 let completed=0;
 for(const id of REVIEW_DIMENSIONS){
  const row=ratings?.[id]||{};
  const score=humanScore(row);
  const note=String(row.reviewer_note||'').trim();
  const evidence=String(row.evidence_reference||'').trim();
  if(!knownScore(score)){errors.push(id+': select 0, 1 or N/A.');continue}
  if(note.length<12)errors.push(id+': explain the rating in at least 12 characters.');
  if(score!=='N/A'&&!evidence)errors.push(id+': cite the original evidence examined.');
  if(note.length>=12&&(score==='N/A'||!!evidence))completed++;
 }
 return {completed,total:REVIEW_DIMENSIONS.length,errors,ready:errors.length===0};
}

export function completedOfficerScoringCsv(packet,ratings,reviewerId,reviewedAtUtc){
 const reviewer=String(reviewerId||'').trim();
 const checked=officerScoreCompletion(packet,ratings,reviewer);
 if(!checked.ready)throw Error(checked.errors.join(' '));
 const stamp=String(reviewedAtUtc||'');
 if(!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(stamp)||
    Number.isNaN(Date.parse(stamp)))
  throw Error('A valid UTC review timestamp is required.');
 const header=[
  'packet_id','dimension','automated_status','human_score_0_1_NA',
  'evidence_reference','reviewer_note','reviewer_id','review_date_utc',
  'adjudicated_score_0_1_NA','adjudicator_id','adjudication_note'
 ];
 const automated=packet.automated_checks?.checks||[];
 const rows=REVIEW_DIMENSIONS.map(id=>{
  const row=ratings[id];
  return [packet.packet_id,id,automated.find(x=>x.id===id)?.automated_status||'NOT_RUN',
    humanScore(row),String(row.evidence_reference||'').trim(),
    String(row.reviewer_note||'').trim(),reviewer,stamp,'','',''];
 });
 const csv='\ufeff'+[csvLine(header),...rows.map(csvLine)].join('\r\n')+'\r\n';
 // The reviewer export must be importable by the existing v148.7 consolidator.
 const parsed=parseReviewCsv(csv);
 if(parsed.entries.length!==4||parsed.packet_id!==packet.packet_id)
  throw Error('The completed sheet did not pass consolidation format checks.');
 return csv;
}
