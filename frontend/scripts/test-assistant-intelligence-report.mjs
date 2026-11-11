import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {findingSourceIds,withoutRepeatedFindingRefs} from '../src/lib/assistantFindingSources.js';
// The isolated frontend Docker build copies only frontend/, not backend/.
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8');
const page=read('../src/pages/IntelligenceAssistant.jsx');
const dashboard=read('../src/components/intel/AssistantInsights.jsx');
const findings=read('../src/components/intel/AssistantIntelligenceReport.jsx');
const records=read('../src/components/intel/AssistantRecords.jsx');
assert.ok(page.includes('AssistantIntelligenceReport')&&page.includes('featured_sources'),'report connected to chat');
assert.ok(page.includes("useState('DEEP')"),'deep intelligence default');
assert.ok(dashboard.includes('activity_by_date')&&dashboard.includes('platform_engagement'),'source-based charts connected');
assert.ok(dashboard.includes('engagement_coverage'),'metric coverage disclosed');
assert.ok(findings.includes("t('verification_heading')"),'officer actions presented');
assert.ok(findings.includes('withoutRepeatedFindingRefs')&&findings.includes('findingSourceIds')&&findings.includes('grid grid-cols-1 gap-3'),
  'investigation source chips survive bare citations with readable full-width cards');
const bare='SOCIAL-179 dan SOCIAL-158 melaporkan kendala akses Silon.';
assert.deepEqual(findingSourceIds(bare),['SOCIAL-179','SOCIAL-158']);
assert.ok(!withoutRepeatedFindingRefs(bare).includes('SOCIAL-'));
assert.match(withoutRepeatedFindingRefs(bare),/melaporkan kendala akses Silon/);
const bracketed='Kendala perlu diverifikasi [SOCIAL-179] [SOCIAL-158].';
assert.deepEqual(findingSourceIds(bracketed),['SOCIAL-179','SOCIAL-158']);
assert.ok(!withoutRepeatedFindingRefs(bracketed).includes('SOCIAL-'));
const many='SOCIAL-740, SOCIAL-296, SOCIAL-306, dan SOCIAL-352 mengutip sumber.';
assert.equal(findingSourceIds(many).length,4);
assert.match(withoutRepeatedFindingRefs(many),/mengutip sumber/);
assert.deepEqual(findingSourceIds('Sumber [SOCIAL-205] dan SOCIAL-205'),['SOCIAL-205']);
const generated='Klaim dokumen pendidikan. SOCIAL-205 dan rekaman serupa menyatakan dugaan pelapor.';
assert.match(withoutRepeatedFindingRefs(generated),/Unggahan yang dirujuk dan rekaman serupa menyatakan/);
assert.ok(!withoutRepeatedFindingRefs(generated).includes('sumber tersimpan'));
assert.match(withoutRepeatedFindingRefs('SOCIAL-296 dan SOCIAL-306 memberitakan klaim.'),/Dua unggahan yang dirujuk memberitakan/);
assert.match(withoutRepeatedFindingRefs('SOCIAL-740, SOCIAL-296, SOCIAL-306, dan SOCIAL-352 membahas kasus.'),/Beberapa unggahan yang dirujuk membahas/);
assert.match(withoutRepeatedFindingRefs('According to DOC-1-P6, the officer checks records.','en'),/the cited document page/);
assert.ok(page.includes('maxLength={1000}')&&page.includes('slice(0,120)'),
  'full investigation questions and bounded history titles are supported');
assert.ok(page.includes("'CROSS_MODULE_REVIEW'")&&page.includes('formal_selected_count'),
  'case and cross-module comparisons disclose missing relevant Inbox evidence');
assert.ok(page.includes("m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights"),
  'only sentiment/social analysis should show the numerical dashboard');
assert.ok(records.includes("t('sources_heading')"),'visual source gallery present');
assert.ok(records.includes('featured?.length?featured:records||[]'),'historical social evidence remains visible');
assert.ok(dashboard.includes('Every chart uses the same')&&dashboard.includes('snapshot.matched_pool_count'),
  'the social dashboard and AI narrative use one clearly disclosed set of posts');
assert.ok(dashboard.includes('data-advanced-social-metrics'),
  'additional engagement and date statistics are collapsed by default');
assert.ok(records.includes('rel="noopener noreferrer"'),'external links isolated');
console.log('Frontend intelligence report checks passed');

assert.ok(page.includes("m.response_profile!=='PDF_GUIDANCE'&&<AssistantDetectedTags")
    && page.includes("m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights"),
    'PDF-only responses cannot render candidate tags or social charts');

assert.ok(page.includes("m.response_profile==='ACTION_REQUEST'&&") &&
          page.includes("m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights"),
  'executive reports cannot trigger the assignment desk or unrelated analytics');

const assistantAnswer=read('./src/components/intel/AssistantAnswer.jsx');
assert.ok(assistantAnswer.includes("const heading=line.match") &&
          assistantAnswer.includes("const Heading=level===1?'h2':level===2?'h3':'h4'") &&
          assistantAnswer.includes("return <Heading key={j}"),
  'Markdown executive report section titles render as headings, not raw ## text');
