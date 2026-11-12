import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 buildAssistantReviewPacket,assistantReviewScorecardCsv
} from '../src/lib/assistantReviewPacket.js';
import {
 REVIEW_DIMENSIONS,parseReviewCsv,validateReviewPacket,
 aggregateAssistantReviews,aggregateSummaryJson
} from '../src/lib/assistantReviewAggregation.js';

const answer={
 role:'assistant',text:'A saved Riau source remains unverified. [SOCIAL-21]',
 records:[{record_id:'SOCIAL-21',record_type:'SOCIAL_LISTENING',
   source_excerpt:'Riau electoral oversight allegation',
   private_note:'DO_NOT_COPY_THIS',source_url:'https://example.invalid/post/21'}],
 grounding:{
  grounding_audit:{displayed_citation_ids:['SOCIAL-21']},
  answer_quality:{checks:REVIEW_DIMENSIONS.map(id=>({
    id,status:'REVIEW_REQUIRED',reason:'Requires human source review'
  }))}
 }
};
const packet=buildAssistantReviewPacket({
 question:'What happened in Riau?',answer,
 exportedAt:'2026-11-12T00:00:00.000Z',buildVersion:'148.7'
});
assert.equal(validateReviewPacket(packet).packet_id,packet.packet_id);
const header=assistantReviewScorecardCsv(packet).replace(/^\ufeff/,'').split('\r\n')[0];
const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
const csv=(reviewer,ratings={},adjudication={})=>
 '\ufeff'+[header,...REVIEW_DIMENSIONS.map(d=>{
  const score=ratings[d]??'';
  const adj=adjudication[d]??'';
  const note=score?'Officer checked the original evidence thoroughly.':'';
  const aid=adj?'third_officer':'';
  const values=[
   packet.packet_id,d,'REVIEW_REQUIRED',score,
   score&&score!=='N/A'?'SOCIAL-21':'',note,score?reviewer:'',
   score?'2026-11-12T04:35:00Z':'',
   adj,aid,adj?'Independent decision after source review.':''
  ];
  return values.map(quote).join(',');
 })].join('\r\n')+'\r\n';

const none=aggregateAssistantReviews([packet],[]);
assert.equal(none.packet_count,1);
assert.equal(none.dimension_stats[0].score_1_support_rate_percent,null);
assert.equal(none.dimension_stats[0].awaiting_review,1);
assert.equal(none.human_accuracy_percentage,null);
assert.equal(none.identities_verified,false);
assert.equal(none.source_permissions_rechecked,false);
assert.equal(none.client_acceptance_certified,false);
assert.equal(none.all_processing_in_browser,true);
assert.equal(none.paid_model_called,false);

const one=parseReviewCsv(csv('officer_a',{citation_grounding:'1'}));
assert.equal(one.entries.length,1);
assert.equal(one.entries[0].reviewer_id,'officer_a');
const preliminary=aggregateAssistantReviews([packet],[one]);
assert.equal(preliminary.dimension_stats[0].consensus_scored,0);
assert.equal(preliminary.dimension_stats[0].score_1_support_rate_percent,null);
assert.equal(preliminary.cases[0].status,'AWAITING_TWO_REVIEWERS');
const copied=aggregateAssistantReviews([packet],[one,one]);
assert.equal(copied.dimension_stats[0].consensus_scored,0,
 'Uploading the same officer twice is not independent review');

const both=['citation_grounding','source_relevance','legal_uncertainty',
 'cross_module_consistency'];
const pass=Object.fromEntries(both.map(d=>[d,'1']));
const agree=aggregateAssistantReviews([packet],[
 csv('officer_a',pass),csv('officer_b',pass)
]);
assert.ok(agree.errors.length===0);
assert.deepEqual(agree.dimension_stats.map(x=>x.consensus_scored),[1,1,1,1]);
assert.ok(agree.dimension_stats.every(x=>x.score_1_support_rate_percent===100));
assert.ok(agree.dimension_stats.every(x=>x.independent_pairs===1));
assert.ok(agree.dimension_stats.every(x=>x.reviewer_agreement_percent===100));
assert.equal(agree.human_accuracy_percentage,null,
 'Self-declared consensus is not verified model accuracy');
const summary=aggregateSummaryJson(agree);
assert.ok(!summary.includes('DO_NOT_COPY_THIS'));
assert.ok(!summary.includes('Officer checked the original evidence'));
assert.ok(!summary.includes('https://example.invalid'));
assert.ok(!summary.includes('officer_a'));
assert.equal(JSON.parse(summary).client_acceptance_certified,false);

const uncertain=aggregateAssistantReviews([packet],[
 csv('officer_a',{citation_grounding:'1'}),
 csv('officer_b',{citation_grounding:'0'})
]);
assert.equal(uncertain.dimension_stats[0].score_1_support_rate_percent,null);
assert.equal(uncertain.dimension_stats[0].disagreement_unresolved,1);
assert.equal(uncertain.cases[0].status,'DISAGREEMENT_UNRESOLVED');
assert.equal(uncertain.dimension_stats[0].reviewer_agreement_percent,0);

const adjudicated=aggregateAssistantReviews([packet],[
 csv('officer_a',{citation_grounding:'1'}),
 csv('officer_b',{citation_grounding:'0'}),
 csv('',{},{citation_grounding:'0'})
]);
assert.equal(adjudicated.cases[0].status,'ADJUDICATED');
assert.equal(adjudicated.cases[0].final_score,'0');
assert.equal(adjudicated.dimension_stats[0].consensus_scored,1);
assert.equal(adjudicated.dimension_stats[0].consensus_supported,0);
assert.equal(adjudicated.dimension_stats[0].score_1_support_rate_percent,0);
assert.equal(adjudicated.dimension_stats[0].adjudicated,1);

const notApplicable=aggregateAssistantReviews([packet],[
 csv('officer_a',{legal_uncertainty:'N/A'}),
 csv('officer_b',{legal_uncertainty:'N/A'})
]);
const legal=notApplicable.dimension_stats[2];
assert.equal(legal.agreed_not_applicable,1);
assert.equal(legal.consensus_scored,0);
assert.equal(legal.score_1_support_rate_percent,null);

let selfAdjudication=csv('',{},{citation_grounding:'1'})
 .replaceAll('"third_officer"','"officer_a"');
const conflict=aggregateAssistantReviews([packet],[
 csv('officer_a',{citation_grounding:'1'}),
 csv('officer_b',{citation_grounding:'0'}),
 selfAdjudication
]);
assert.equal(conflict.cases[0].status,'ADJUDICATOR_NOT_INDEPENDENT');
assert.equal(conflict.dimension_stats[0].consensus_scored,0);

const malformed=csv('officer_a',{citation_grounding:'1'})
 .replace('"2026-11-12T04:35:00Z"','"not-a-date"');
assert.throws(()=>parseReviewCsv(malformed),/review date/i);
const withoutEvidence=csv('officer_a',{citation_grounding:'1'})
 .replace('"SOCIAL-21"','""'); // first "SOCIAL-21" occurs in evidence cell only
assert.throws(()=>parseReviewCsv(withoutEvidence),/inspected evidence/i);
assert.throws(()=>parseReviewCsv('not,a,review'),/Missing required CSV column/);
assert.throws(()=>parseReviewCsv('"unfinished'),/Unclosed CSV/);
const wrongPacket=JSON.parse(JSON.stringify(packet));
wrongPacket.assistant_answer='Different answer injected after export';
assert.throws(()=>validateReviewPacket(wrongPacket),/does not match/);
const rejected=aggregateAssistantReviews([wrongPacket],[one]);
assert.equal(rejected.packet_count,0);
assert.ok(rejected.errors.length>=2);
assert.equal(rejected.has_any_consensus_score,false);

const app=readFileSync(new URL('../../backend/app/main.py',import.meta.url),'utf8');
const shell=readFileSync(new URL('../src/components/intel/Shell.jsx',import.meta.url),'utf8');
const page=readFileSync(new URL('../src/pages/IntelligenceAssistant.jsx',import.meta.url),'utf8');
const e2e=readFileSync(new URL('../e2e/assistant-knowledge-library.spec.js',import.meta.url),'utf8');
const apiVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const uiVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(apiVersion&&apiVersion===uiVersion);
assert.ok(page.includes('<AssistantReviewConsolidation/>'));
assert.ok(e2e.includes('Assistant consolidates independently scored local review sheets'));
console.log('PASS v148.7 offline independent officer scoring, dispute gating, adjudication, CSV parsing and privacy');
