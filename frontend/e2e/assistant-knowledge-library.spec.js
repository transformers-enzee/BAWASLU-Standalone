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
