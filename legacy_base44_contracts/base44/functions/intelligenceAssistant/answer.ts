import { sourceReadView } from '../../shared/intelligenceSource.ts';
export const noEvidence = 'Insufficient validated intelligence to answer this question.';
const approved = d => ['Human Accepted','Human Modified'].includes(d?.status);
const safeFinal = (item, field, suggestion) => {
  const proposal=item.ai_suggestions?.[suggestion];
  const decision=item.ai_suggestions?._decisions?.[suggestion];
  const current=Array.isArray(item[field])?item[field].join(', '):item[field];
  return proposal && !approved(decision) && current===proposal ? null : item[field];
};
export function project(item){
  const source=sourceReadView(item),confirmedOwner=source.source_identity.status==='REGISTERED_ACCOUNT_CONFIRMED'&&!!item.owned_channel?.account_id;
  const jurisdiction=item.jurisdiction_type==='National'?'National':(item.geographic_assignments||[]).map(a=>[a.regency_city,a.province].filter(Boolean).join(', ')).join(' · ')||[item.regency_city,item.province].filter(Boolean).join(', ');
  return {id:item.id,intelligence_id:item.intelligence_id,title:item.title||'Untitled record',jurisdiction,review_status:item.review_status,evidence_type:item.evidence_type||(['OBSERVED','INFERRED'].includes(item.evidence_state)?item.evidence_state:'Not classified'),verification_status:item.verification_status||(item.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'),priority:safeFinal(item,'priority','priority')||'Not specified',date:item.collection_datetime||item.created_date||'',summary:String(safeFinal(item,'ai_summary','summary')||'').slice(0,300),candidate:confirmedOwner?item.owned_channel.candidate_name||'':'',owned_platform:confirmedOwner?item.owned_channel.platform||'':'',issue:item.supervision_screening?.supervision_signal||'',topics:safeFinal(item,'related_topics','topic')||[],entities:safeFinal(item,'related_entities','entity')||[],locations:(item.geographic_assignments||[]).map(a=>a.regency_city||a.province).filter(Boolean)};
}
export function matches(item,term){
  if(!term)return true;
  const words=term.toLowerCase().replace(/[^\p{L}\p{N} -]/gu,' ').split(/\s+/).map(x=>x.replace(/-related$/,'')).filter(x=>x.length>2&&!['intelligence','record','records','about','related','topic','entity','issues','from','show','latest','validated','province','jurisdiction'].includes(x));
  if(!words.length)return true;
  const text=[item.intelligence_id,item.title,item.summary,item.issue,item.jurisdiction,item.priority,item.candidate,item.owned_platform,...item.topics,...item.entities].join(' ').toLowerCase();
  return words.every(word=>text.includes(word));
}
const priorityOrder=['Critical','High','Medium','Low'];
const plural=(n,word)=>`${n} ${word}${n===1?'':'s'}`;
const describe=r=>{
  const text=(r.summary||'').trim();
  return text ? text.replace(/\s+/g,' ').replace(/\.\s+.*/s,'.').slice(0,220).replace(/[.!?\s]+$/,'') : '';
};
export function answerFor(records,intent,includeUnvalidated,period={}){
  if(!records.length)return noEvidence;
  const validated=records.filter(r=>r.review_status==='Validated as Relevant Intelligence').length;
  const subject=includeUnvalidated?`${plural(records.length,'accessible intelligence record')} (${plural(validated,'human-validated record')})`:`${plural(records.length,'validated intelligence record')}`;
  const periodText=period.days||period.date?' in the requested period':'';
  const single=records.length===1;
  const singleLabel=includeUnvalidated&&records[0].review_status!=='Validated as Relevant Intelligence'?'unvalidated':'validated';
  const ownedNote=single&&records[0].candidate?` The record is attributed to ${records[0].candidate}'s registered ${records[0].owned_platform||'owned-channel'} account.`:'';
  const evidence=[...new Set(records.map(r=>`${r.evidence_type} / ${r.verification_status}`))];
  const unverified=single&&records[0].verification_status==='UNVERIFIED'?' Its supporting evidence remains UNVERIFIED.':'';
  let direct='',observations=[];
  if(intent==='count')direct=`${subject.charAt(0).toUpperCase()+subject.slice(1)} ${single?'matches':'match'} the query${periodText} in the retrieved set.${unverified}`;
  else if(intent==='priority'){
    const rank=records.filter(r=>priorityOrder.includes(r.priority)).sort((a,b)=>priorityOrder.indexOf(a.priority)-priorityOrder.indexOf(b.priority));
    if(!rank.length)return noEvidence;
    const top=rank.filter(r=>r.priority===rank[0].priority);
    direct=single?`The only matching ${singleLabel} intelligence record, ${records[0].intelligence_id}, has ${rank[0].priority} priority.${unverified}`:`The highest priority among the matching intelligence is ${rank[0].priority}. ${top.map(r=>r.intelligence_id).join(', ')} ${top.length===1?'is':'are'} the supporting ${top.length===1?'record':'records'} at that level.`;
  } else if(['issues','topics','entities','locations','compare'].includes(intent)){
    const field=intent==='issues'?'issue':intent==='topics'?'topics':intent==='entities'?'entities':'locations';
    const tally=new Map();
    for(const r of records){const values=field==='locations'?(r.locations.length?r.locations:[r.jurisdiction]):Array.isArray(r[field])?r[field]:[r[field]];for(const value of new Set(values.filter(Boolean))){const ids=tally.get(value)||[];ids.push(r.intelligence_id);tally.set(value,ids);}}
    if(!tally.size)return noEvidence;
    const ranked=[...tally].sort((a,b)=>b[1].length-a[1].length);
    const leading=ranked.filter(([,ids])=>ids.length===ranked[0][1].length);
    const label=field==='issue'?'supervision signal':field==='locations'?'location':field==='topics'?'topic':'entity';
    if(single){
      const detail=describe(records[0]);
      direct=`One ${singleLabel} intelligence record${periodText} concerns ${ranked.map(([name])=>name).slice(0,2).join(' and ')}.${detail?` The human-approved summary states: ${detail}`:''}${unverified}`;
    }else{
      direct=leading.length===1?`The most frequently represented ${label} is ${leading[0][0]}, appearing in ${plural(leading[0][1].length,'matching record')}.`:`The matching intelligence has no single leading ${label}: ${leading.slice(0,3).map(([name])=>name).join(', ')} each appear in ${plural(ranked[0][1].length,'record')}.`;
      observations=ranked.slice(0,3).map(([name,ids])=>`${name} is represented in ${plural(ids.length,'record')} (${ids.join(', ')}).`);
    }
  }else{
    if(single){const detail=describe(records[0]);direct=`One ${singleLabel} intelligence record was identified${periodText}: ${records[0].intelligence_id}${detail?` — ${detail}`:` (${records[0].title})`}.${unverified}`;}
    else{direct=`${subject.charAt(0).toUpperCase()+subject.slice(1)} were identified${periodText}. These are individual intelligence records, not evidence of a broader trend.`;observations=records.slice(0,3).map(r=>`${r.intelligence_id}: ${describe(r)||r.title}.`);}
  }
  if(ownedNote)direct+=ownedNote;
  const sections=[`ANSWER / INTELLIGENCE SUMMARY\n${direct}`];
  if(observations.length)sections.push(`KEY OBSERVATIONS\n${observations.join('\n')}`);
  if(!single&&(evidence.length>1||records.some(r=>r.verification_status==='UNVERIFIED'||r.evidence_type==='INFERRED')||includeUnvalidated))sections.push(`EVIDENCE STATUS\n${includeUnvalidated?`${plural(validated,'record')} human-validated; ${plural(records.length-validated,'record')} not yet validated. `:''}${evidence.map(state=>`${plural(records.filter(r=>`${r.evidence_type} / ${r.verification_status}`===state).length,'record')} marked ${state}`).join('; ')}. Human validation and evidence verification are separate assessments.`);
  if(intent==='count'||records.length===10)sections.push('LIMITATION\nResults come from a bounded set of recent, accessible records and are not an exhaustive historical count.');
  return sections.join('\n\n');
}