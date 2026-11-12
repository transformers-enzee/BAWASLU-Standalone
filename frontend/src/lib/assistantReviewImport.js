export function officerReviewImportProblem(data){
 if(!data||typeof data!=='object'||Array.isArray(data))
  return 'This file is not an AI answer-evidence packet. Export review evidence (.json) beneath a newly generated Assistant answer.';
 if(data.framework==='BAWASLU_ASSISTANT_EVALUATION_PLAN_V1488'||(Array.isArray(data.questions)&&data.negative_control))
  return 'This is a prepared question plan, not an answered AI review packet. Select a saved-source question, press Send, then use Score this answer or Export review evidence (.json).';
 if(data.schema_version==='BAWASLU_OFFLINE_HUMAN_REVIEW_AGGREGATION_V1487'||
    data.framework==='BAWASLU_OFFLINE_HUMAN_REVIEW_AGGREGATION_V1487'||
    (Array.isArray(data.dimension_stats)&&Array.isArray(data.cases)))
  return 'This is an aggregate human-review summary, not an original AI answer packet. Import the BAWASLU-assistant-review-AR-xxxxxxxx.json file.';
 if(data.schema_version==='BAWASLU_ASSISTANT_REVIEW_V1485')return '';
 if(Array.isArray(data.messages)||Array.isArray(data.threads))
  return 'This looks like conversation history, not an original review packet. Export review evidence (.json) beneath a newly generated answer.';
 return 'Unrecognized JSON export. Import the original BAWASLU-assistant-review-AR-xxxxxxxx.json answer packet, not a question plan or score summary.';
}
