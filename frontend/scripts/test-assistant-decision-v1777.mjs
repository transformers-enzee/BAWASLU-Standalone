import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const page=read('../src/pages/IntelligenceAssistant.jsx');
const panel=read('../src/components/intel/AssistantOfficerDecisionPanel.jsx');
const trail=read('../src/components/intel/AssistantWorkflowEvidence.jsx');
const main=read('../../backend/app/main.py');
const history=read('../../backend/app/assistant_history.py');
const model=read('../../backend/app/assistant_decision_intelligence.py');
for(const test of [
 "officer_decision:response.data.officer_decision||null",
 "AssistantOfficerDecisionPanel message={m}",
 "onDraftMemo={reviewableIndexes.has(i)",
])assert.ok(page.includes(test),'Missing page contract: '+test);
for(const test of [
 'assistant-officer-action-cards','assistant-recommended-decision','assistant-no-nexus',
 'assistant-legal-jurisdiction','assistant-copy-officer-plan',
 'assistant-download-review-packet','assistant-prepare-leadership-memo',
 'No assignment, filing, enforcement or communication is executed automatically',
])assert.ok(panel.includes(test),'Missing officer panel: '+test);
assert.ok(trail.includes('assistant-public-claim-ledger'));
assert.ok(trail.includes('assistant-decision-evidence-gap'));
assert.ok(main.includes('synthesize_public_decision('));
assert.ok(main.includes("'officer_decision':officer_decision"));
assert.ok(history.includes('"WEB_RESEARCH"'));
assert.ok(history.includes('"officer_decision":({'));
assert.ok(model.includes('NO_ESTABLISHED_NEXUS'));
assert.ok(model.includes('safe_decision(candidate,consulted_urls)'));
console.log('PASS v177.7 decision intelligence UI, review packet, permissions and source audit');
