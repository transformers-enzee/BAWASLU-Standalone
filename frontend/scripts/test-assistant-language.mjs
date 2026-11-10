import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {textFor,friendlySource} from '../src/lib/assistantResponseLocale.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const page=read('src/pages/IntelligenceAssistant.jsx');
const tags=read('src/components/intel/AssistantDetectedTags.jsx');
const visuals=read('src/components/intel/AssistantInsights.jsx');
const report=read('src/components/intel/AssistantIntelligenceReport.jsx');
const sources=read('src/components/intel/AssistantRecords.jsx');
const action=read('src/components/intel/AssistantActionDesk.jsx');
const hook=read('src/lib/useTranslatedPresentationText.jsx');
const text=read('src/components/intel/TranslatedAssistantAnswer.jsx');
assert.equal(textFor('id',{},'tags_heading'),'Entitas dan isu yang teridentifikasi');
assert.equal(textFor('en',{},'tags_heading'),'Detected entities and issues');
assert.equal(textFor('es',{tags_heading:'Entidades y asuntos'},'tags_heading'),'Entidades y asuntos');
assert.ok(friendlySource('UNVERIFIED_SOCIAL_SOURCE','en',{}).includes('not independently verified'));
assert.ok(friendlySource('UNVERIFIED_SOCIAL_SOURCE','id',{}).includes('belum diverifikasi'));
assert.ok(page.includes('detected_tags:response.data.detected_tags'));
assert.ok(page.includes('answer_language:response.data.answer_language'));
assert.ok(page.includes('AssistantDetectedTags'));
assert.ok(tags.includes('source_ids')&&tags.includes('tags_notice'));
assert.ok(report.includes('language=')&&report.includes("t('findings_heading')"));
assert.ok(visuals.includes('numberLocale(language)')&&visuals.includes("t('stats_heading')"));
assert.ok(sources.includes('numberLocale(language)')&&sources.includes("t('original_source')"));
assert.ok(action.includes("t('submit_action')")&&action.includes("t('action_intro')"));
assert.ok(hook.includes('!answerLanguage&&'),'existing translations must not override answer language');
assert.ok(text.includes('useTranslatedPresentationText(clean,language)'),
  'saved answer language bypasses app-language translation');
assert.ok(page.includes("response_profile:response.data.response_profile"),
 'the assistant must retain the deterministic response profile with each answer');
assert.ok(page.includes("m.response_profile==='ACTION_REQUEST'")&&
  !page.includes("i===messages.length-1&&<AssistantActionDesk"),
 'case assignment controls are only offered for explicit action requests');
assert.ok(page.includes("m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights"),
 'social statistical charts render only for social-intelligence requests');
assert.ok(page.includes("m.response_profile!=='PDF_GUIDANCE'&&<AssistantDetectedTags")&&
  page.includes("m.response_profile!=='PDF_GUIDANCE'&&<AssistantIntelligenceReport"),
 'pure PDF guidance excludes candidate/issue tags and full intelligence reports');
assert.ok(page.includes("compactPdf={m.response_profile==='PDF_GUIDANCE'}")&&
  sources.includes('data-compact-pdf-references')&&sources.includes('pdfs.slice(0,4)'),
 'PDF answers show compact clickable page references instead of multi-card excerpts');
console.log('Assistant multilingual/tagging integration checks passed');
