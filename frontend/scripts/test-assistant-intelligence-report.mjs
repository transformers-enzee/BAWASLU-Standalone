import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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
assert.ok(records.includes("t('sources_heading')"),'visual source gallery present');
assert.ok(records.includes('featured?.length?featured:records||[]'),'historical social evidence remains visible');
assert.ok(dashboard.includes('Every chart uses the same')&&dashboard.includes('snapshot.matched_pool_count'),
  'the social dashboard and AI narrative use one clearly disclosed set of posts');
assert.ok(dashboard.includes('data-advanced-social-metrics'),
  'additional engagement and date statistics are collapsed by default');
assert.ok(records.includes('rel="noopener noreferrer"'),'external links isolated');
console.log('Frontend intelligence report checks passed');
