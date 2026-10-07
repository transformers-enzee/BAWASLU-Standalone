// One pre-provisioned, access-restricted sequence record. Compare-and-swap reserves each number atomically.
const sequenceId='6ab3435f9ed9bb83b43770e7';
export async function nextIntelligenceId(entities){
 const year=new Date().getUTCFullYear();
 for(let attempt=0;attempt<30;attempt++){
  const row=await entities.IntelligenceSequence.get(sequenceId);
  if(!row||!Number.isInteger(row.sequence)||row.year>year)throw Error('Intelligence identifier sequence unavailable');
  const number=row.year===year?row.sequence+1:1;
  if(number>999999)throw Error('Annual identifier capacity reached');
  const result=await entities.IntelligenceSequence.updateMany({id:sequenceId,sequence:row.sequence,year:row.year},{$set:{sequence:number,year}});
  if(result.updated===1)return `INT-${year}-${String(number).padStart(6,'0')}`;
 }
 throw Error('Identifier busy; please retry submission');
}