import { triageSections, structuredTriageSections, legacyTriageFields } from './triageSections';

const scalar=['summary','english_translation','content_type','supervision_signal','signal_reason','screening_confidence','priority','evidence_type','confidence'];
const structured=['activity','actors','location_signal','narrative','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis'];
const arrays=new Set(['actors','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis']);
const fields={activity:['type','description','evidence_basis','evidence_type','confidence'],actors:['entity_id','entity_name','entity_type','relationship_to_content','evidence_basis','evidence_type','confidence'],location_signal:['location_text','evidence_basis','evidence_type','confidence'],narrative:['label','description','evidence_basis','evidence_type','confidence'],relationships:['subject_entity_id','subject_entity_name','relationship_type','object_entity_id','object_entity_name','observed_account','evidence_basis','evidence_type','confidence']};
export function validV3(s){
  if(s?._version!==3||scalar.some(k=>typeof s[k]!=='string')||structured.some(k=>typeof s[k]!=='string')||typeof s.source_facts!=='string')return false;
  const allowed=new Set([...scalar,...structured,'source_facts','_version','_triage_run_id','_decisions','watchlist_match']);
  if(Object.keys(s).some(key=>!allowed.has(key)))return false;
  if(!s.summary.trim()||!s.confidence.trim()||!s.screening_confidence.trim()||!['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'].includes(s.supervision_signal)||!['OBSERVED','INFERRED'].includes(s.evidence_type)||!['Critical','High','Medium','Low'].includes(s.priority))return false;
  for(const key of structured){
    if(!s[key])continue;
    let value;try{value=JSON.parse(s[key])}catch{return false}
    if(arrays.has(key)!==Array.isArray(value)||!value||typeof value!=='object')return false;
    const objects=key==='actors'||key==='relationships'?value:fields[key]?[value]:[];
    for(const object of objects){
      if(!object||Array.isArray(object)||typeof object!=='object'||fields[key].some(field=>typeof object[field]!=='string')||!object.evidence_basis?.trim()||!object.confidence?.trim()||!['OBSERVED','INFERRED'].includes(object.evidence_type))return false;
      if(key==='activity'&&(!object.type.trim()||!object.description.trim())||key==='narrative'&&(!object.label.trim()||!object.description.trim())||key==='location_signal'&&!object.location_text.trim()||key==='actors'&&!object.entity_name.trim()||key==='relationships'&&(!object.subject_entity_name.trim()||!(object.object_entity_name.trim()||object.observed_account.trim())))return false;
    }
    if(arrays.has(key)&&!fields[key]&&value.some(entry=>typeof entry!=='string'||!entry.trim()))return false;
  }
  return s.supervision_signal==='NO SIGNAL IDENTIFIED'||!!(s.signal_reason.trim()&&s.check_next&&s.screening_evidence_basis);
}
export function triagePresentation(s){
  if(s?._version===3)return validV3(s)?{sections:structuredTriageSections,invalid:false}:{sections:[],invalid:true};
  if(s?._version===2)return {sections:triageSections,invalid:false};
  return {sections:[{title:'Legacy AI Triage',fields:legacyTriageFields}],invalid:false};
}