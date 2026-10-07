const fields=['activity','actors','location_signal','narrative','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis'];
export function validateStructuredProposal(decisions,version){
 if(version!==3)return '';
 for(const [key,decision] of Object.entries(decisions)){
  if(!fields.includes(key)||decision.status==='Human Rejected')continue;
  try{const parsed=JSON.parse(decision.value);if(['activity','location_signal','narrative'].includes(key)?!parsed||Array.isArray(parsed)||typeof parsed!=='object':!Array.isArray(parsed))return `The modified ${key} needs a structured ${['activity','location_signal','narrative'].includes(key)?'object':'list'}.`;}catch{return `The modified ${key} needs valid structured JSON.`;}
 }
 return '';
}