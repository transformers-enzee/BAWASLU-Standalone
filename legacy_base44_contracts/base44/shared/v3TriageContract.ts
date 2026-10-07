import { parseStructuredReview } from './structuredTriage.ts';

export const v3ScalarFields=['summary','english_translation','content_type','supervision_signal','signal_reason','screening_confidence','priority','evidence_type','confidence'];
export const v3StructuredFields=['activity','actors','location_signal','narrative','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis'];
const arrayFields=new Set(['actors','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis']);
const objectFields={activity:['type','description','evidence_basis','evidence_type','confidence'],actors:['entity_id','entity_name','entity_type','relationship_to_content','evidence_basis','evidence_type','confidence'],location_signal:['location_text','evidence_basis','evidence_type','confidence'],narrative:['label','description','evidence_basis','evidence_type','confidence'],relationships:['subject_entity_id','subject_entity_name','relationship_type','object_entity_id','object_entity_name','observed_account','evidence_basis','evidence_type','confidence']};
export const v3Signals=['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'];
export const v3EvidenceTypes=['OBSERVED','INFERRED'];
export const v3Priorities=['Critical','High','Medium','Low'];
class ContractError extends Error{
  constructor(field,detail){
    super(`V3 AI Triage response invalid (${detail}). No proposals were saved; contact an administrator before retrying.`);
    this.rejected_field=field;
  }
}
const fail=(field,detail)=>{throw new ContractError(field,detail)};
// Diagnostics expose only the field, a short safe excerpt of the received value and the expected contract. No prompts, reasoning or configuration.
const show=value=>typeof value==='string'?JSON.stringify(value.trim().slice(0,200)):value===null?'null':value===undefined?'undefined':`(${typeof value}) ${JSON.stringify(String(value).slice(0,200))}`;
const enumRule=(field,value,allowed)=>fail(field,`${field} — received: ${show(value)} — expected one of: ${allowed.join(' | ')} — result: INVALID_ENUM`);
const emptyRule=(field,value)=>fail(field,`${field} — received: ${show(value)} — expected: a non-empty text value — result: EMPTY_REQUIRED_FIELD`);
const emptyListRule=field=>fail(field,`${field} — received: an empty list — expected: at least one entry — result: EMPTY_REQUIRED_LIST`);
function checkObject(key,object){
  const fields=objectFields[key];
  for(const field of fields)if(!Object.hasOwn(object,field)||typeof object[field]!=='string')fail(`${key}.${field}`,`${key}.${field} is missing or not text — received: ${show(object?.[field])} — expected: text — result: INVALID_TYPE`);
  if(!object.evidence_basis?.trim())emptyRule(`${key}.evidence_basis`,object.evidence_basis);
  if(!object.confidence?.trim())emptyRule(`${key}.confidence`,object.confidence);
  if(!v3EvidenceTypes.includes(object.evidence_type))enumRule(`${key}.evidence_type`,object.evidence_type,v3EvidenceTypes);
  if(key==='activity'&&(!object.type?.trim()||!object.description?.trim()))emptyRule('activity.type/activity.description',`${object.type?.trim()?'activity.description':'activity.type'} is empty — result: EMPTY_REQUIRED_FIELD`);
  if(key==='narrative'&&(!object.label?.trim()||!object.description?.trim()))emptyRule('narrative.label/narrative.description',`${object.label?.trim()?'narrative.description':'narrative.label'} is empty — result: EMPTY_REQUIRED_FIELD`);
  if(key==='location_signal'&&!object.location_text?.trim())emptyRule('location_signal.location_text',object.location_text);
  if(key==='actors'&&!object.entity_name?.trim())emptyRule('actors.entity_name',object.entity_name);
  if(key==='relationships'&&(!object.subject_entity_name?.trim()||!(object.object_entity_name?.trim()||object.observed_account?.trim())))emptyRule('relationships.subject/object',object.subject_entity_name?.trim()?'':'relationship lacks subject or object/account');
}
export function validateV3ModelResult(result){
  if(!result||typeof result!=='object'||Array.isArray(result))fail('model_output',`model output is not an object — received: ${show(result)} — result: INVALID_TYPE`);
  for(const key of v3ScalarFields)if(!Object.hasOwn(result,key)||typeof result[key]!=='string')fail(key,`${key} is missing or not text — received: ${show(result[key])} — expected: text — result: INVALID_TYPE`);
  for(const key of v3StructuredFields){
    if(!Object.hasOwn(result,key))fail(key,`${key} is missing — result: MISSING_REQUIRED_FIELD`);
    const value=result[key];
    if(arrayFields.has(key)){if(!Array.isArray(value))fail(key,`${key} — received: ${show(value)} — expected: a list — result: INVALID_TYPE`);}
    else if(!value||typeof value!=='object'||Array.isArray(value))fail(key,`${key} — received: ${show(value)} — expected: an object — result: INVALID_TYPE`);
    const objects=key==='actors'||key==='relationships'?value:key==='activity'||key==='location_signal'||key==='narrative'?Object.keys(value).length?[value]:[]:[];
    for(const object of objects)checkObject(key,object);
    try{if(objects.length||Array.isArray(value))parseStructuredReview(key,value)}catch{fail(key,`${key} has an invalid structure — result: INVALID_STRUCTURE`)}
    if(arrayFields.has(key)&&!['actors','relationships'].includes(key)&&value.some(entry=>typeof entry!=='string'||!entry.trim()))fail(key,`${key} contains an empty entry — result: EMPTY_REQUIRED_FIELD`);
  }
  if(!result.summary.trim())emptyRule('summary',result.summary);
  if(!result.confidence.trim())emptyRule('confidence',result.confidence);
  if(!result.screening_confidence.trim())emptyRule('screening_confidence',result.screening_confidence);
  if(!v3Signals.includes(result.supervision_signal))enumRule('supervision_signal',result.supervision_signal,v3Signals);
  if(!v3EvidenceTypes.includes(result.evidence_type))enumRule('evidence_type',result.evidence_type,v3EvidenceTypes);
  if(!v3Priorities.includes(result.priority))enumRule('priority',result.priority,v3Priorities);
  if(result.supervision_signal!=='NO SIGNAL IDENTIFIED'){
    if(!result.signal_reason.trim())emptyRule('signal_reason',result.signal_reason);
    if(!result.check_next.length)emptyListRule('check_next');
    if(!result.screening_evidence_basis.length)emptyListRule('screening_evidence_basis');
  }
  return result;
}
export function validateV3Proposal(proposal){
  if(proposal?._version!==3)fail('_version',`triage schema version 3 is required — received: ${show(proposal?._version)} — result: INVALID_VERSION`);
  const allowed=new Set([...v3ScalarFields,...v3StructuredFields,'_version','source_facts']);
  const unexpected=Object.keys(proposal).find(key=>!allowed.has(key));
  if(unexpected)fail(unexpected,`${unexpected} is an unexpected or legacy proposal field — result: UNEXPECTED_FIELD`);
  if(typeof proposal.source_facts!=='string')fail('source_facts',`source_facts is missing or not text — received: ${show(proposal.source_facts)} — expected: text — result: INVALID_TYPE`);
  for(const key of v3ScalarFields)if(!Object.hasOwn(proposal,key)||typeof proposal[key]!=='string')fail(key,`${key} is missing or not text — result: INVALID_TYPE`);
  for(const key of v3StructuredFields){
    if(!Object.hasOwn(proposal,key)||typeof proposal[key]!=='string')fail(key,`${key} is missing or not text — result: INVALID_TYPE`);
    if(!proposal[key])continue;
    let value;try{value=parseStructuredReview(key,proposal[key])}catch{fail(key,`${key} has invalid JSON or evidence — result: INVALID_STRUCTURE`)}
    const objects=key==='actors'||key==='relationships'?value:key==='activity'||key==='location_signal'||key==='narrative'?[value]:[];
    for(const object of objects)checkObject(key,object);
  }
  if(!proposal.summary.trim())emptyRule('summary',proposal.summary);
  if(!proposal.confidence.trim())emptyRule('confidence',proposal.confidence);
  if(!proposal.screening_confidence.trim())emptyRule('screening_confidence',proposal.screening_confidence);
  if(!v3Signals.includes(proposal.supervision_signal))enumRule('supervision_signal',proposal.supervision_signal,v3Signals);
  if(!v3EvidenceTypes.includes(proposal.evidence_type))enumRule('evidence_type',proposal.evidence_type,v3EvidenceTypes);
  if(!v3Priorities.includes(proposal.priority))enumRule('priority',proposal.priority,v3Priorities);
  if(proposal.supervision_signal!=='NO SIGNAL IDENTIFIED'){
    if(!proposal.signal_reason.trim())emptyRule('signal_reason',proposal.signal_reason);
    if(!proposal.check_next)emptyRule('check_next',proposal.check_next);
    if(!proposal.screening_evidence_basis)emptyRule('screening_evidence_basis',proposal.screening_evidence_basis);
  }
  return proposal;
}
export async function fingerprint(value){const bytes=new TextEncoder().encode(typeof value==='string'?value.trim():JSON.stringify(value));const digest=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');}
export async function verifyGeneration(entities,runId,userId,itemId,serviceAction,content,sourceUrl,proposal){
  if(typeof runId!=='string'||!runId)fail('generation_provenance','generation provenance is missing');
  const matches=await entities.TriageGeneration.filter({triage_run_id:runId});
  const meta=matches[0];
  if(matches.length!==1||!meta||meta.validation_outcome!=='GENERATED'||!meta.generated_at||meta.initiated_by_id!==userId||meta.intelligence_item_id!==(itemId||'')||meta.service_action!==serviceAction||meta.generator!=='assistIntelligence'||meta.triage_schema_version!==3||meta.source_fingerprint!==await fingerprint({content:content.trim(),source_url:sourceUrl||''})||meta.proposal_fingerprint!==await fingerprint(proposal))fail('generation_provenance','generation provenance does not match the source and proposals, or the attempt was not successfully validated');
  return meta;
}
export function generationAudit(meta){return Object.fromEntries(['triage_run_id','triage_schema_version','generator','generator_version','service_action','generated_at','proposal_field_names'].map(key=>[key,{new:meta[key]}]));}