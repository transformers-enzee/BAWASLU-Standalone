import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test('knowledge library resolves authorized national document metadata',async({page})=>{
 let reads=0;
 await page.route('**/api/assistant-knowledge/documents',async route=>{
  reads++;
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   documents:[{id:1,title:'BAWASLU_Sample_AI_Knowledge_Full_Text',filename:'sample.pdf',
    scope:'NATIONAL',province:'',pages:12,extracted_chars:24000,
    document_type:'OTHER',review_status:'UNREVIEWED',embedding_status:'NOT_INDEXED'}],
   can_upload:false,can_review:false,default_scope:'NATIONAL',default_province:'',paid_provider_called:false
  })});
 });
 await login(page);
 await page.goto('/assistant');
 const library=page.getByRole('region',{name:'Assistant PDF knowledge library'});
 await expect(library).toContainText('1 PDF');
 await expect(library).not.toContainText('Loading PDF library');
 await library.locator('button[aria-expanded]').click();
 await expect(library.getByText('BAWASLU_Sample_AI_Knowledge_Full_Text')).toBeVisible();
 await expect(library).toContainText('12 pages');
 expect(reads).toBeGreaterThanOrEqual(1);
});

test('knowledge library distinguishes unavailable metadata from a true zero PDF result',async({page})=>{
 await page.route('**/api/assistant-knowledge/documents',route=>
  route.fulfill({status:503,contentType:'application/json',
   body:JSON.stringify({detail:'Service temporarily unavailable'})}));
 await login(page);
 await page.goto('/assistant');
 const library=page.getByRole('region',{name:'Assistant PDF knowledge library'});
 await expect(library).toContainText('PDF unavailable');
 await expect(library).not.toContainText('0 PDF');
 await library.locator('button[aria-expanded]').click();
 await expect(library.getByRole('alert')).toContainText('Service temporarily unavailable');
});


test('Assistant distinguishes cited IDs from contextual source cards',async({page})=>{
 await page.route('**/api/functions/intelligenceAssistant',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   answer:'The saved report requires review. Source links are context, not proof.',
   records:[{
    id:'12',record_id:'SOCIAL-12',record_type:'SOCIAL_LISTENING',
    source_post_id:'12',campaign_id:1,platform:'Instagram',
    source_name:'Example account',source_excerpt:'Unverified local report',
    source_url:'https://example.invalid/post/12',
    verification_status:'UNVERIFIED_SOCIAL_SOURCE'
   }],
   response_profile:'SOCIAL_ANALYSIS',provider:{mode:'DETERMINISTIC_FALLBACK'},
   grounding:{selected_count:1,supporting_count:1,cited_count:0,
    source_card_count:1,source_card_basis:'CONTEXTUAL_SELECTED_SOURCE',
    grounding_audit:{
     audit_version:'ASSISTANT_GROUNDING_V1483',
     displayed_citation_count:0,cited_unreviewed_pdf_pages:0,
     legal_currentness_verified:false,claims_semantically_verified:false
    }},
   answer_language:'en',detected_tags:[],presentation_labels:{}
  })}));
 await login(page);
 await page.goto('/assistant');
 await page.locator('form input[maxlength="1000"]').fill('Summarize the saved BAWASLU post');
 await page.locator('form button[type="submit"]').click();
 const audit=page.getByTestId('assistant-grounding-integrity');
 await expect(audit).toBeVisible();
 await expect(audit).toContainText('0 source IDs cited');
 await expect(audit).toContainText('1 source cards available');
 await expect(audit).toContainText('Source cards are context only');
 await expect(audit).toContainText('not the truth of source claims');
});


test('Assistant shows four answer readiness checks without claiming human accuracy',async({page})=>{
 await page.route('**/api/functions/intelligenceAssistant',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   answer:'One saved source discusses Riau; an officer must check the original. [SOCIAL-12]',
   records:[{
    id:'12',record_id:'SOCIAL-12',record_type:'SOCIAL_LISTENING',
    source_post_id:'12',campaign_id:1,platform:'Instagram',
    source_name:'Example account',source_excerpt:'Riau local election discussion',
    source_url:'https://example.invalid/post/12',
    verification_status:'UNVERIFIED_SOCIAL_SOURCE'
   }],
   response_profile:'SOCIAL_ANALYSIS',provider:{mode:'OPENAI_GROUNDED'},
   grounding:{selected_count:1,supporting_count:1,cited_count:1,
    source_card_count:1,source_card_basis:'CITED_SOURCE',
    grounding_audit:{audit_version:'ASSISTANT_GROUNDING_V1483',
     displayed_citation_count:1,cited_unreviewed_pdf_pages:0,
     legal_currentness_verified:false,claims_semantically_verified:false},
    answer_quality:{
     framework:'ASSISTANT_ANSWER_READINESS_V1484',
     evaluation_type:'DETERMINISTIC_HEURISTICS_NOT_HUMAN_ACCURACY',
     passed_checks:1,review_required_checks:1,not_applicable_checks:2,
     human_accuracy:null,human_gold_answers_evaluated:0,
     checks:[
       {id:'citation_grounding',status:'PASS'},
       {id:'source_relevance',status:'REVIEW_REQUIRED'},
       {id:'legal_uncertainty',status:'NOT_APPLICABLE'},
       {id:'cross_module_consistency',status:'NOT_APPLICABLE'}
     ]
    }
   },
   answer_language:'en',detected_tags:[],presentation_labels:{}
  })}));
 await login(page);
 await page.goto('/assistant');
 await page.locator('form input[maxlength="1000"]').fill('Summarize the saved post from Riau');
 await page.locator('form button[type="submit"]').click();
 const qa=page.getByTestId('assistant-answer-quality');
 await expect(qa).toBeVisible();
 await expect(qa.locator('summary')).toContainText('1 require review');
 await qa.locator('summary').click();
 await expect(qa).toContainText('Rule-based checks, not an accuracy score or human validation.');
 await expect(qa).toContainText('source relevance');
 await expect(qa).toContainText('REVIEW REQUIRED');
 await expect(qa).toContainText('cross module consistency');
 await expect(qa).toContainText('Source truth and legal conclusions still require an authorized officer.');
});


test('Assistant review packet exports preserve blank human scores',async({page})=>{
 await page.route('**/api/functions/intelligenceAssistant',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   answer:'An unverified Riau report requires officer checking. [SOCIAL-11]',
   records:[{
    record_id:'SOCIAL-11',record_type:'SOCIAL_LISTENING',source_post_id:'11',
    platform:'Instagram',campaign_id:90,source_name:'Example account',
    source_excerpt:'Riau saved post alleging an electoral irregularity',
    source_url:'https://example.invalid/post/11',
    private_note:'DO_NOT_EXPORT'
   }],
   response_profile:'SOCIAL_ANALYSIS',
   provider:{mode:'OPENAI_GROUNDED'},
   grounding:{
    grounding_audit:{
     displayed_citation_ids:['SOCIAL-11'],cited_unreviewed_pdf_pages:0,
     claims_semantically_verified:false
    },
    answer_quality:{
     framework:'ASSISTANT_ANSWER_READINESS_V1484',review_required_checks:1,
     checks:[
      {id:'citation_grounding',status:'PASS',reason:'Identifier matches'},
      {id:'source_relevance',status:'REVIEW_REQUIRED',reason:'Review source'},
      {id:'legal_uncertainty',status:'NOT_APPLICABLE'},
      {id:'cross_module_consistency',status:'NOT_APPLICABLE'}
     ]
    }
   },
   answer_language:'en',detected_tags:[],presentation_labels:{}
  })}));
 await login(page);
 await page.goto('/assistant');
 await page.locator('form input[maxlength="1000"]').fill('What is happening in Riau?');
 await page.locator('form button[type="submit"]').click();
 const review=page.getByTestId('assistant-human-review-export');
 await expect(review).toBeVisible();
 await expect(review).toContainText('Reviewer scores are blank and no approval has occurred');
 const jsonEvent=page.waitForEvent('download');
 await review.getByTestId('assistant-review-json').click();
 const json=await jsonEvent;
 expect(json.suggestedFilename()).toMatch(/^BAWASLU-assistant-review-AR-[a-f0-9]{8}\.json$/);
 const {readFile}=await import('node:fs/promises');
 const snapshot=JSON.parse(await readFile(await json.path(),'utf8'));
 expect(snapshot.schema_version).toBe('BAWASLU_ASSISTANT_REVIEW_V1485');
 expect(snapshot.question).toBe('What is happening in Riau?');
 expect(snapshot.human_accuracy).toBeNull();
 expect(snapshot.officer_approved).toBe(false);
 expect(snapshot.human_scorecard.checks).toHaveLength(4);
 expect(snapshot.human_scorecard.checks.every(c=>c.human_score===null)).toBe(true);
 expect(snapshot.evidence_snapshot.exported_records[0].record_id).toBe('SOCIAL-11');
 expect(JSON.stringify(snapshot)).not.toContain('DO_NOT_EXPORT');
 const csvEvent=page.waitForEvent('download');
 await review.getByTestId('assistant-review-csv').click();
 const csv=await csvEvent;
 expect(csv.suggestedFilename().replace('.csv','.json')).toBe(json.suggestedFilename());
 const sheet=await readFile(await csv.path(),'utf8');
 expect(sheet).toContain('human_score_0_1_NA');
 expect(sheet).toContain('source_relevance');
 expect(sheet).toContain('REVIEW_REQUIRED');
 expect(sheet.trim().split(/\r?\n/)).toHaveLength(5);
});


test('Assistant consolidates independently scored local review sheets without calling an API',async({page})=>{
 const {buildAssistantReviewPacket,assistantReviewScorecardCsv}=await import('../src/lib/assistantReviewPacket.js');
 const packet=buildAssistantReviewPacket({
  question:'What happened in Riau?',
  answer:{role:'assistant',text:'Riau discussion needs verification. [SOCIAL-44]',
   records:[{record_id:'SOCIAL-44',record_type:'SOCIAL_LISTENING',
     source_excerpt:'Local oversight record in Riau'}],
   grounding:{grounding_audit:{displayed_citation_ids:['SOCIAL-44']},
    answer_quality:{checks:[{id:'citation_grounding',status:'PASS'}]}}},
  buildVersion:'148.7',exportedAt:'2026-11-12T05:00:00Z'
 });
 const header=assistantReviewScorecardCsv(packet).replace(/^\ufeff/,'').split('\r\n')[0];
 const escape=value=>'"'+String(value??'').replace(/"/g,'""')+'"';
 const sheet=(reviewer,score)=>'\ufeff'+[
  header,
  ...['citation_grounding','source_relevance','legal_uncertainty',
      'cross_module_consistency'].map(d=>
     [packet.packet_id,d,'PASS',d==='citation_grounding'?score:'',
      d==='citation_grounding'?'SOCIAL-44':'',
      d==='citation_grounding'?'Officer checked source excerpt and context.':'',
      d==='citation_grounding'?reviewer:'',
      d==='citation_grounding'?'2026-11-12T05:10:00Z':'',
      '','',''].map(escape).join(',')
   )
 ].join('\r\n')+'\r\n';
 const networkWrites=[];
 page.on('request',request=>{
  if(request.method()!=='GET'&&request.url().includes('assistant-review'))
   networkWrites.push(request.url());
 });
 await login(page);
 await page.goto('/assistant');
 const panel=page.getByTestId('assistant-review-consolidation');
 await panel.getByRole('button',{name:/Human answer-review consolidation/}).click();
 await expect(panel).toContainText('All files stay in this browser session.');
 await panel.getByTestId('assistant-review-file-input').setInputFiles([
  {name:'Riau-response.json',mimeType:'application/json',
   buffer:Buffer.from(JSON.stringify(packet))},
  {name:'review-officer-a.csv',mimeType:'text/csv',
   buffer:Buffer.from(sheet('officer_one','1'))},
  {name:'review-officer-b.csv',mimeType:'text/csv',
   buffer:Buffer.from(sheet('officer_two','1'))}
 ]);
 const result=panel.getByTestId('assistant-review-consolidation-result');
 await expect(result).toContainText('1 evidence packets');
 await expect(result).toContainText('2 scored sheets accepted');
 const citation=panel.getByTestId('assistant-review-dimension-citation_grounding');
 await expect(citation).toContainText('100%');
 await expect(citation).toContainText('1/1 supported');
 await expect(citation).toContainText('Reviewer agreement: 100%');
 const legal=panel.getByTestId('assistant-review-dimension-legal_uncertainty');
 await expect(legal).toContainText('0/0 supported');
 await expect(result).toContainText('not a verified AI accuracy rate');
 const download=page.waitForEvent('download');
 await panel.getByTestId('assistant-review-summary-export').click();
 const file=await download;
 expect(file.suggestedFilename()).toBe('BAWASLU-human-review-aggregate-v1487.json');
 const {readFile}=await import('node:fs/promises');
 const summary=JSON.parse(await readFile(await file.path(),'utf8'));
 expect(summary.packet_count).toBe(1);
 expect(summary.human_accuracy_percentage).toBeNull();
 expect(summary.dimension_stats[0].consensus_scored).toBe(1);
 expect(summary.dimension_stats[1].consensus_scored).toBe(0);
 expect(summary.client_acceptance_certified).toBe(false);
 expect(JSON.stringify(summary)).not.toContain('Local oversight record in Riau');
 expect(JSON.stringify(summary)).not.toContain('officer_one');
 expect(networkWrites).toEqual([]);
});

test('Assistant local review rejects unsupported unpaired scoring sheets',async({page})=>{
 await login(page);
 await page.goto('/assistant');
 const panel=page.getByTestId('assistant-review-consolidation');
 await panel.getByRole('button',{name:/Human answer-review consolidation/}).click();
 const csv='packet_id,dimension,automated_status,human_score_0_1_NA,evidence_reference,reviewer_note,reviewer_id,review_date_utc\n'+
  ['citation_grounding','source_relevance','legal_uncertainty','cross_module_consistency']
   .map(d=>'AR-00000000,'+d+',PASS,,,,,').join('\n')+'\n';
 await panel.getByTestId('assistant-review-file-input').setInputFiles([
  {name:'unpaired-review.csv',mimeType:'text/csv',buffer:Buffer.from(csv)}
 ]);
 await expect(panel.getByTestId('assistant-review-import-errors'))
  .toContainText('Missing matching JSON evidence packet');
 await expect(panel.getByTestId('assistant-review-dimension-citation_grounding'))
  .toContainText('0/0 supported');
});


test('Assistant prepares real-source evaluation questions without calling the AI model',async({page})=>{
 const prepared=[];
 page.on('request',req=>{
  if(req.url().includes('/api/functions/intelligenceAssistant'))prepared.push(req.url());
 });
 await page.route('**/api/assistant-evaluation/questions?target=*',route=>
  route.fulfill({status:200,contentType:'application/json',
   body:JSON.stringify({
    framework:'BAWASLU_ASSISTANT_EVALUATION_PLAN_V1488',
    target_questions:24,prepared_questions:1,shortfall:23,
    category_available_sources:{POTENTIAL_VIOLATION_SIGNAL:1,PUBLIC_CONCERN:0},
    category_selected_questions:{POTENTIAL_VIOLATION_SIGNAL:1},
    missing_categories:['PUBLIC_CONCERN'],
    questions:[{
      question_number:1,category:'POTENTIAL_VIOLATION_SIGNAL',
      source_record_id:'SOCIAL-42',source_url:'https://example.invalid/post/42',
      platform:'Instagram',
      question:'For saved relevant Social Listening source [SOCIAL-42] on Instagram, describe alleged conduct; do not determine a violation.'
    }],
    negative_control:{source_record_id:'SOCIAL-0',
      question:'Review saved source [SOCIAL-0] and explicitly state no matching source exists.',
      excluded_from_real_source_count:true}
   })}));
 await login(page);
 await page.goto('/assistant');
 const panel=page.getByTestId('assistant-evaluation-sampler');
 await expect(panel).toBeVisible();
 await expect(panel.getByTestId('assistant-evaluation-generate')).toHaveCount(0);
 await panel.getByRole('button',{name:/Prepare real-source Assistant evaluation questions/}).click();
 await panel.getByTestId('assistant-evaluation-generate').click();
 const result=panel.getByTestId('assistant-evaluation-sampler-result');
 await expect(result).toContainText('1/24 real-source questions prepared');
 await expect(result).toContainText('23 not available');
 await expect(result).toContainText('Public concern');
 await expect(result).toContainText('non-random sample');
 expect(prepared).toHaveLength(0);
 await panel.getByTestId('assistant-evaluation-use-question').first().click();
 await expect(page.locator('form input[maxlength="1000"]'))
  .toHaveValue(/SOCIAL-42/);
 await expect(panel.getByTestId('assistant-evaluation-question-prepared'))
  .toContainText('press Send yourself');
 expect(prepared).toHaveLength(0);
 const download=page.waitForEvent('download');
 await panel.getByTestId('assistant-evaluation-export').click();
 const file=await download;
 expect(file.suggestedFilename()).toBe('BAWASLU-assistant-evaluation-questions-v1488.json');
 const {readFile}=await import('node:fs/promises');
 const data=JSON.parse(await readFile(await file.path(),'utf8'));
 expect(data.questions).toHaveLength(1);
 expect(data.questions[0].source_record_id).toBe('SOCIAL-42');
 expect(data.negative_control.excluded_from_real_source_count).toBe(true);
 expect(prepared).toHaveLength(0);
});

test('Assistant evaluation preparation does not reveal sources without authorization',async({page})=>{
 await page.route('**/api/assistant-evaluation/questions?target=*',route=>
  route.fulfill({status:403,contentType:'application/json',
    body:JSON.stringify({detail:'Intelligence evaluation requires view permission'})}));
 await login(page);
 await page.goto('/assistant');
 const panel=page.getByTestId('assistant-evaluation-sampler');
 await panel.getByRole('button',{name:/Prepare real-source Assistant evaluation questions/}).click();
 await panel.getByTestId('assistant-evaluation-generate').click();
 await expect(panel.getByRole('alert')).toContainText('view permission');
 await expect(panel.getByTestId('assistant-evaluation-sampler-result')).toHaveCount(0);
 await expect(panel.getByTestId('assistant-evaluation-use-question')).toHaveCount(0);
});

test('Assistant locally completes a genuine scoring worksheet without submitting a model call',async({page})=>{
 const {buildAssistantReviewPacket}=await import('../src/lib/assistantReviewPacket.js');
 const {REVIEW_DIMENSIONS,parseReviewCsv}=await import('../src/lib/assistantReviewAggregation.js');
 const scoringPacket=buildAssistantReviewPacket({
  question:'Review saved source [SOCIAL-901]',
  answer:{
   role:'assistant',text:'The source alleges an issue that is not independently verified. [SOCIAL-901]',
   records:[{record_id:'SOCIAL-901',record_type:'SOCIAL_LISTENING',
    source_url:'https://example.invalid/post/901',
    source_excerpt:'Unverified public post excerpt'}],
   grounding:{grounding_audit:{displayed_citation_ids:['SOCIAL-901']},
    answer_quality:{checks:REVIEW_DIMENSIONS.map(id=>({id,status:'REVIEW_REQUIRED'}))}}
  },buildVersion:'149.2'
 });
 let modelCalls=0;
 await page.route('**/api/functions/intelligenceAssistant',route=>{
  modelCalls++;
  return route.fulfill({status:500,body:'Unexpected model call'});
 });
 await login(page);
 await page.goto('/assistant');
 const panel=page.getByTestId('assistant-human-scoring');
 await expect(panel).toBeVisible();
 await panel.getByRole('button',{name:/Prepare independent officer scoring sheet/}).click();
 await panel.getByTestId('assistant-human-scoring-file').setInputFiles({
  name:'review-packet.json',mimeType:'application/json',
  buffer:Buffer.from(JSON.stringify(scoringPacket))
 });
 const workspace=panel.getByTestId('assistant-human-scoring-workspace');
 await expect(workspace).toContainText(scoringPacket.packet_id);
 await expect(panel.getByTestId('assistant-human-scoring-export')).toBeDisabled();
 await panel.getByTestId('assistant-reviewer-id').fill('officer_a');
 for(const id of REVIEW_DIMENSIONS){
  await panel.getByTestId('assistant-score-'+id).selectOption('1');
  await panel.getByTestId('assistant-evidence-'+id).fill('SOCIAL-901');
  await panel.getByTestId('assistant-note-'+id).fill('Original source inspected by the reviewer.');
 }
 await expect(panel.getByTestId('assistant-human-scoring-progress')).toContainText('4/4');
 await expect(panel.getByTestId('assistant-human-scoring-export')).toBeDisabled();
 await panel.getByTestId('assistant-scoring-confirm').check();
 const downloadPromise=page.waitForEvent('download');
 await panel.getByTestId('assistant-human-scoring-export').click();
 const result=await downloadPromise;
 expect(result.suggestedFilename()).toBe('BAWASLU-officer-scoring-'+scoringPacket.packet_id+'.csv');
 const {readFile}=await import('node:fs/promises');
 const content=await readFile(await result.path(),'utf8');
 const parsed=parseReviewCsv(content);
 expect(parsed.entries).toHaveLength(4);
 expect(parsed.entries.every(entry=>entry.reviewer_id==='officer_a')).toBe(true);
 expect(parsed.entries.every(entry=>entry.evidence_reference==='SOCIAL-901')).toBe(true);
 expect(content).not.toContain('Unverified public post excerpt');
 expect(modelCalls).toBe(0);
});
