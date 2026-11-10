import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Script} from 'node:vm';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const captured=read('src/components/intel/CapturedPostList.jsx');
const inbox=read('src/pages/Inbox.jsx');
const form=read('src/components/intel/SentimentCorrection.jsx');
const kb=read('src/components/intel/AssistantKnowledgeLibrary.jsx');
const assistant=read('src/pages/IntelligenceAssistant.jsx');
const records=read('src/components/intel/AssistantRecords.jsx');
const radarHtml=read('public/ui-freeze/smart-radar-v6_2.html');
const radarJs=read('public/ui-freeze/smart-radar-live.js');
assert.ok(captured.includes('SentimentCorrection')&&captured.includes('can_correct_sentiment'),
  'Captured Posts must allow scoped officer sentiment correction');
assert.ok(inbox.includes('SentimentCorrection')&&inbox.includes('setFullStatistics'),
  'Inbox must allow correction and update visible counts');
assert.ok(form.includes('/api/officer-sentiment/correct')&&form.includes('Authorization:')&&
   form.includes('sentiment:label'), 'sentiment correction requires authenticated officer write');
assert.ok(!form.includes('rationale:')&&!form.includes('reason.trim()')&&
   !form.includes('Alasan perubahan')&&!form.includes('Reason for change'),
  'manual correction has no mandatory reason field');
assert.ok(form.includes("useLanguage()")&&form.includes("language==='en'"),
  'sentiment correction follows app language and defaults to Indonesian otherwise');
assert.ok(captured.includes("useLanguage()")&&captured.includes("isEnglish?'Negative':'Negatif'")&&
  captured.includes("t('All sentiments','Semua sentimen')"),
  'captured posts sentiment and filters follow current app language');
assert.ok(inbox.includes("language==='en'?'Sentiment corrected by officer':'Sentimen dikoreksi petugas'"),
  'Inbox correction status is translated by app language');
assert.ok(assistant.includes('AssistantKnowledgeLibrary'),'PDF library must be embedded in assistant');
assert.ok(kb.includes("semantic_index")&&kb.includes("semanticIndex")&&kb.includes("form.append('document_type'"),
 'explicit opt-in semantic indexing and document type are required');
assert.ok(kb.includes('/search-preview?')&&kb.includes('searchQuestion'),
 'search-preview tests PDF retrieval without a model completion');
assert.ok(kb.includes("'/semantic-index'")&&kb.includes("'/review'"),
 'existing documents can be indexed and reviewed by authorized officers');
assert.ok(kb.includes("OPENAI")===false,'never put an API key in the frontend');
assert.ok(records.includes('match_method')&&records.includes('review_status'),
 'assistant shows semantic match and review provenance on PDF citations');

assert.ok(kb.includes('/upload')&&kb.includes('new FormData')&&kb.includes('default_scope'),
  'PDF uploader must use authenticated multipart form and scoped sharing');
assert.ok(records.includes("record_type==='PDF_KNOWLEDGE'")&&records.includes('document_id'),
  'PDF page citations must be shown as accessible source cards');
assert.ok(radarHtml.includes('id="legalOversight"')&&radarHtml.includes('id="legalCaseQueue"')&&
          radarHtml.includes('id="platformRulesQueue"')&&radarHtml.includes('id="legalFollowup"'),
  'Command Centre shows separate legal and platform-rules boxes');
assert.ok(radarJs.includes('data?.platform_policy_screening')&&
   radarJs.includes('const platformCases=')&&radarJs.includes('review_categories')&&
   radarJs.includes('policy_url')&&radarJs.includes('Source-text signal')&&
   radarJs.includes('No direct threat'),
 'platform rule screening must use independent, source-specific evidence and official policy links');
assert.ok(!radarJs.includes("platform.innerHTML='<p class=\"small muted\">Platform-rule status: not assessed"),
 'platform review must not render the original generic legal-case list');
assert.ok(radarJs.includes('/api/oversight/legal-summary')&&radarJs.includes('renderLegalOversight'),
  'Command Centre legal review must use scoped backend evidence');
assert.ok(radarJs.includes("epoch!==dashboardEpoch"),'late legal response must not replace a newer dashboard');
new Script(radarJs,{filename:'smart-radar-live.js'});
console.log('PASS legal screening, officer sentiment and PDF knowledge frontend checks');
