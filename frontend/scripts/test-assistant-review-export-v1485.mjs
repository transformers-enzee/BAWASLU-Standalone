import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 buildAssistantReviewPacket,assistantReviewScorecardCsv
} from '../src/lib/assistantReviewPacket.js';

const here=new URL('../',import.meta.url);
const read=name=>readFileSync(new URL(name,here),'utf8');
const ui=read('src/pages/IntelligenceAssistant.jsx');
const e2e=read('e2e/assistant-knowledge-library.spec.js');
const app=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');

const answer={
 role:'assistant',text:'A saved Riau report requires review. [SOCIAL-11]',
 response_profile:'SOCIAL_ANALYSIS',answer_language:'en',
 provider:{mode:'OPENAI_GROUNDED',api_key:'NEVER_INCLUDE_THIS_SECRET'},
 records:[
  {record_id:'SOCIAL-11',record_type:'SOCIAL_LISTENING',
   source_excerpt:'=HYPERLINK("https://evil.test","click")',
   source_url:'https://example.invalid/post/11',sentiment:'NEGATIVE',
   private_note:'DO_NOT_EXPORT',api_token:'DO_NOT_EXPORT',campaign_id:1},
  {record_id:'DOC-9-P1',record_type:'PDF_KNOWLEDGE',
   source_excerpt:'An unreviewed test document',review_status:'UNREVIEWED',
   source_url:'javascript:alert(1)',document_id:9,page:1}
 ],
 grounding:{
  grounding_audit:{displayed_citation_ids:['SOCIAL-11']},
  answer_quality:{
   framework:'ASSISTANT_ANSWER_READINESS_V1484',
   checks:[
    {id:'citation_grounding',status:'PASS',reason:'IDs match'},
    {id:'source_relevance',status:'REVIEW_REQUIRED',reason:'Needs a human check'},
    {id:'legal_uncertainty',status:'NOT_APPLICABLE'},
    {id:'cross_module_consistency',status:'NOT_APPLICABLE'}
   ]
  }
 }
};
const initial=buildAssistantReviewPacket({
 question:'What is happening in Riau?',answer,
 exportedAt:'2026-11-12T05:00:00.000Z',buildVersion:'148.5'
});
const restored=buildAssistantReviewPacket({
 question:'What is happening in Riau?',answer,
 exportedAt:'2026-11-12T05:02:00.000Z',buildVersion:'148.5'
});
assert.equal(initial.schema_version,'BAWASLU_ASSISTANT_REVIEW_V1485');
assert.equal(initial.packet_id,restored.packet_id,'Same exact response gets matching packet ID');
assert.equal(initial.app_build_version,'148.5');
assert.equal(initial.review_state,'AWAITING_HUMAN_ASSESSMENT');
assert.equal(initial.officer_approved,false);
assert.equal(initial.legal_findings_confirmed,false);
assert.equal(initial.human_accuracy,null);
assert.equal(initial.human_gold_answers_evaluated,0);
assert.equal(initial.human_scorecard.checks.length,4);
assert.ok(initial.human_scorecard.checks.every(c=>
 c.human_score===null && c.reviewer_note==='' && c.evidence_reference===''));
assert.equal(initial.evidence_snapshot.selected_records_in_chat,2);
assert.equal(initial.evidence_snapshot.exported_records.length,2);
assert.equal(initial.evidence_snapshot.exported_records[1].source_url,'');
assert.ok(!JSON.stringify(initial).includes('DO_NOT_EXPORT'));
assert.ok(!JSON.stringify(initial).includes('NEVER_INCLUDE_THIS_SECRET'));
assert.equal(initial.cited_source_ids[0],'SOCIAL-11');
assert.equal(initial.automated_checks.checks[1].automated_status,'REVIEW_REQUIRED');
assert.equal(initial.automated_checks.measured_model_accuracy,false);
assert.equal(initial.evidence_snapshot.source_permissions_rechecked_at_export,false);

const many=buildAssistantReviewPacket({question:'Riau',answer:{
 ...answer,records:Array.from({length:29},(_,i)=>({
   record_id:'SOCIAL-'+String(i+1),record_type:'SOCIAL_LISTENING'
 }))
}});
assert.equal(many.evidence_snapshot.selected_records_in_chat,29);
assert.equal(many.evidence_snapshot.exported_records.length,25);
assert.equal(many.evidence_snapshot.truncated,true);
const csv=assistantReviewScorecardCsv(initial);
assert.ok(csv.startsWith('\ufeff'));
assert.equal(csv.trim().split(/\r?\n/).length,5,'Four unscored rows and a header');
assert.ok(csv.includes('human_score_0_1_NA'));
assert.ok(csv.includes('"source_relevance"'));
assert.ok(!csv.includes('"REVIEW_REQUIRED","1"'));
const injected={...initial,packet_id:'=2+2'};
assert.ok(assistantReviewScorecardCsv(injected).includes('"\'=2+2"'),
 'Formula-like values must be escaped on CSV export');
assert.throws(()=>buildAssistantReviewPacket({question:'Riau',answer:{role:'assistant',text:''}}));
assert.throws(()=>assistantReviewScorecardCsv({schema_version:'UNKNOWN'}));
assert.ok(ui.includes('data-testid="assistant-human-review-export"')&&
 ui.includes("exportAnswerReview(i,'json')")&&
 ui.includes("exportAnswerReview(i,'csv')"),
 'Explicit per-answer export controls exist in Assistant');
assert.ok(e2e.includes('Assistant review packet exports preserve blank human scores'),
 'Browser QA covers local reviewer download');
const backendVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const frontendVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(backendVersion&&backendVersion===frontendVersion);
assert.ok(/^\d+\.\d+$/.test(backendVersion),'Build version format is valid');
console.log('PASS v148.5 explicit client-side review packet, blank human scoring sheet and source minimization');
