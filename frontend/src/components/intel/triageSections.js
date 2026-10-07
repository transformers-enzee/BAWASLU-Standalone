export const triageSections=[
  {title:'Source Understanding',fields:['english_translation','summary']},
  {title:'Intelligence Extraction',fields:['entity','actor_evidence','content_type','activity','location','topic','narrative','relationships','inference']},
  {title:'Supervision Screening',fields:['supervision_signal','signal_reason','check_next','priority']},
  {title:'Evidence Assessment',fields:['evidence_type','evidence_gaps']}
];
export const structuredTriageSections=[
 {title:'Source Understanding',fields:['english_translation','summary']},
 {title:'Intelligence Extraction',fields:['actors','content_type','activity','location_signal','topics','narrative','relationships','inferences']},
 {title:'Supervision Screening',fields:['supervision_signal','signal_reason','check_next','screening_evidence_basis','screening_confidence','priority']},
 {title:'Evidence Assessment',fields:['evidence_type','evidence_gaps']}
];
export const legacyTriageFields=['summary','english_translation','entity','location','topic','issue_category','priority','suggested_evidence_state','analysis','reasoning'];
export const suggestionNames={source_facts:'Source facts (read-only provenance)',actors:'Actors · structured suggestions',location_signal:'Location signal · not jurisdiction',topics:'Topics · structured suggestions',inferences:'Inferences · not source facts',screening_evidence_basis:'Screening evidence basis',screening_confidence:'Screening confidence',summary:'What happened · factual summary',english_translation:'English translation',entity:'Actors / entities',actor_evidence:'Actor evidence / excerpt',content_type:'Content type · only if evidenced',activity:'Observable activity',location:'Location signal · not jurisdiction',topic:'Topic',narrative:'Narrative · intelligence context',relationships:'Relationship to source · not ownership',inference:'INFERENCE · not source fact',supervision_signal:'Supervision signal · not a finding',signal_reason:'Why this may warrant attention',check_next:'What should be checked next',priority:'Priority',evidence_type:'Evidence type · not verification',evidence_gaps:'Evidence gaps',issue_category:'Legacy potential issue category',suggested_evidence_state:'Legacy evidence state',analysis:'Legacy AI analysis',reasoning:'Legacy reasoning'};