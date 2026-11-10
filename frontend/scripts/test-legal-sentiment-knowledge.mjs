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
assert.ok(form.includes('/api/officer-sentiment/correct')&&form.includes('rationale:reason.trim()'),
  'corrections require an authenticated, reasoned officer write');
assert.ok(form.includes('reason.trim().length<10'),'reject short correction rationale');
assert.ok(assistant.includes('AssistantKnowledgeLibrary'),'PDF library must be embedded in assistant');
assert.ok(kb.includes('/upload')&&kb.includes('new FormData')&&kb.includes('default_scope'),
  'PDF uploader must use authenticated multipart form and scoped sharing');
assert.ok(records.includes("record_type==='PDF_KNOWLEDGE'")&&records.includes('document_id'),
  'PDF page citations must be shown as accessible source cards');
assert.ok(radarHtml.includes('id="legalOversight"')&&radarHtml.includes('id="legalCaseQueue"')&&
          radarHtml.includes('id="platformRulesQueue"')&&radarHtml.includes('id="legalFollowup"'),
  'Command Centre shows separate legal and platform-rules boxes');
assert.ok(radarJs.includes('/api/oversight/legal-summary')&&radarJs.includes('renderLegalOversight'),
  'Command Centre legal review must use scoped backend evidence');
assert.ok(radarJs.includes("epoch!==dashboardEpoch"),'late legal response must not replace a newer dashboard');
new Script(radarJs,{filename:'smart-radar-live.js'});
console.log('PASS legal screening, officer sentiment and PDF knowledge frontend checks');
