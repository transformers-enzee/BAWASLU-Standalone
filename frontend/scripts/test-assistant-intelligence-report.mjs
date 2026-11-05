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
assert.ok(findings.includes('Tindakan verifikasi yang disarankan'),'officer actions presented');
assert.ok(records.includes('Unggahan sumber dan bukti visual'),'visual source gallery present');
assert.ok(records.includes('rel="noopener noreferrer"'),'external links isolated');
console.log('Frontend intelligence report checks passed');
