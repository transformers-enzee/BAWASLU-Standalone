/** Pure presentation-only source provenance. No authorization or factual verdict. */
export function evidenceCardId(record){
 const value=record?.record_id??record?.id??record?.intelligence_id??'';
 return String(value).trim();
}
export function mergeSocialCards(records=[],featured=[]){
 const social=[...records,...featured].filter(r=>r?.record_type==='SOCIAL_LISTENING');
 const output=[],seen=new Map();
 for(const r of social){
  const id=evidenceCardId(r);
  if(id&&seen.has(id)){
   const i=seen.get(id);
   output[i]={...r,...output[i]};
   continue;
  }
  if(id)seen.set(id,output.length);
  output.push(r);
 }
 return output;
}
export function citationPresentation(record,citationIds=[]){
 const id=evidenceCardId(record);
 const cited=Boolean(id&&citationIds.includes(id));
 return {id,cited,kind:cited?'CITED_IN_ANSWER':'CONTEXT_ONLY'};
}
export function canPrepareCaseworkFromCard(record,freshAnswer){
 return Boolean(freshAnswer&&record?.record_type==='SOCIAL_LISTENING'&&
  /^\d+$/.test(String(record.source_post_id??''))&&
  /^\d+$/.test(String(record.campaign_id??'')));
}
