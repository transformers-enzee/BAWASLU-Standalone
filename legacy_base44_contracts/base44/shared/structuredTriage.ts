// The AI proposes structured values; only explicit analyst decisions promote them to approved fields.
const shapes={
 activity:['type','description','evidence_basis','evidence_type','confidence'],
 location_signal:['location_text','evidence_basis','evidence_type','confidence'],
 narrative:['label','description','evidence_basis','evidence_type','confidence'],
 actors:['entity_id','entity_name','entity_type','relationship_to_content','evidence_basis','evidence_type','confidence'],
 relationships:['subject_entity_id','subject_entity_name','relationship_type','object_entity_id','object_entity_name','observed_account','evidence_basis','evidence_type','confidence']
};
const arrays=['actors','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis'];
const objects=['activity','location_signal','narrative'];
export const structuredKeys=[...arrays,...objects];
const limits={actors:20,relationships:20,topics:20,evidence_gaps:20,inferences:20,check_next:20,screening_evidence_basis:20};
const text=(v,max=500)=>typeof v==='string'?v.trim().slice(0,max):'';
export function parseStructuredReview(key,raw){
 if(!structuredKeys.includes(key))throw Error('Unknown structured suggestion');
 let input=raw;
 if(typeof raw==='string'){try{input=JSON.parse(raw)}catch{throw Error(`Invalid structured ${key}: enter valid JSON`);}}
 const normalize=(value,fields)=>{
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error(`Invalid structured ${key}: expected an object`);
  const out=Object.fromEntries(fields.map(field=>[field,text(value[field],field==='description'||field==='evidence_basis'?1500:500)]));
  if(fields.includes('evidence_type')&&!['OBSERVED','INFERRED'].includes(out.evidence_type))throw Error(`${key} evidence_type must be OBSERVED or INFERRED`);
  return out;
 };
 if(objects.includes(key)){
  const out=normalize(input,shapes[key]);
  if(!text(out.description||out.location_text)||!out.evidence_basis)throw Error(`${key} needs a description/location and evidence basis`);
  return out;
 }
 if(!Array.isArray(input)||input.length>limits[key])throw Error(`Invalid structured ${key}: expected at most ${limits[key]} entries`);
 if(key==='actors'||key==='relationships')return input.map(entry=>{
  const out=normalize(entry,shapes[key]);
  if(key==='actors'&&!out.entity_name)throw Error('Each actor needs an entity name');
  if(key==='relationships'&&(!out.subject_entity_name||!(out.object_entity_name||out.observed_account)))throw Error('Each relationship needs a subject and object or observed account');
  if(!out.evidence_basis)throw Error(`Each ${key} entry needs an evidence basis`);
  // A proposed ID is not a confirmed registry link. The authoritative relationship remains separate.
  out.entity_id='';out.subject_entity_id='';out.object_entity_id='';
  return out;
 });
 if(input.some(v=>typeof v!=='string'||!v.trim()))throw Error(`${key} entries must be nonempty text`);
 return input.map(v=>text(v,1000));
}
export function formatStructuredProposal(key,value){
 if(value==null)return '';
 try{const parsed=parseStructuredReview(key,value);const serialized=JSON.stringify(parsed,null,2);return Array.isArray(parsed)&&!parsed.length?'':serialized.length<=12000?serialized:''}catch{return '';}
}