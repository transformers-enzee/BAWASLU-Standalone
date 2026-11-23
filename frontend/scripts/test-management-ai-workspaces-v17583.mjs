import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const app=read('../src/App.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const home=read('../src/pages/ManagementHome.jsx');
const chat=read('../src/pages/IntelligenceAssistant.jsx');
const selector=read('../src/components/intel/AssistantWorkflowControls.jsx');
const evidence=read('../src/components/intel/AssistantWorkflowEvidence.jsx');
const server=read('../../backend/app/main.py');
const workflows=read('../../backend/app/assistant_workflows.py');
const orchestra=read('../../backend/app/assistant_orchestration.py');
const history=read('../../backend/app/assistant_history.py');
for(const path of [
 'path="/management" element={<ManagementHome />}',
 'path="/management/assistant" element={<IntelligenceAssistant workspace="MANAGEMENT" />}',
 'path="/assistant" element={<IntelligenceAssistant workspace="OPERATIONS" />}',
])assert.ok(app.includes(path),'Management and operations route missing: '+path);
for(const field of [
 'data-testid="management-workspace-navigation"',
 'data-testid="operations-workspace-navigation"',
 "['/management','Management Home'",
 "['/assistant','intelligence_assistant'",
])assert.ok(nav.includes(field),'Workspace navigation missing: '+field);
for(const field of [
 'data-testid="management-workspace-home"',
 'data-testid="executive-brief"',
 "'/api/management-reporting/briefing?period='",
 'No authorized human casework assignments were recorded',
 'not an official legal finding',
 'counts_complete_for_window',
 'source_url',
])assert.ok(home.includes(field),'Executive brief must be evidence-based: '+field);
for(const field of [
 "['RESEARCH','Research & Analysis'",
 "['STRATEGY_DRAFTING','Strategy & Drafting'",
 "'smartRadar','SmartRadar / saved BAWASLU intelligence'",
 "'publicWeb','Public web / public social'",
 "'legalReferences','Official legal/reference sources'",
 'data-testid="assistant-authorized-source-selection"',
 'not a live crawl',
 'may incur OpenAI search costs',
])assert.ok(selector.includes(field),'Assistant mode/source selector missing: '+field);
for(const field of [
 "workflowMode,sourceSelection",
 "analysisMode:'DATA'",
 'source_consultation:response.data.source_consultation',
 'structured_findings:response.data.structured_findings',
 'decision_plan:response.data.decision_plan',
 'draft_policy:response.data.draft_policy',
 'data-testid="assistant-draft-revision-shortcuts"',
 "Shorten memo",
 "Turn into email",
 'fresh={reviewableIndexes.has(i)}',
])assert.ok(chat.includes(field),'Conversation feature missing: '+field);
for(const field of [
 'data-testid="assistant-consulted-sources"',
 'data-testid="assistant-source-linked-findings"',
 'data-testid="assistant-management-decision-plan"',
 'data-testid="assistant-draft-review-required"',
 'Historical answer snapshot',
 'not a live source check',
])assert.ok(evidence.includes(field),'Source-linked rendering missing: '+field);
for(const field of [
 'normalize_workflow_request(body)',
 "if not general and response_profile!=PDF_GUIDANCE and source_choice['smartRadar']:",
 "if source_choice['legalReferences'] and",
 "not source_choice['smartRadar'] and not source_choice['legalReferences']",
 "source_consultation(source_choice,evidence,cited,meta.get('external_research_urls')",
 "structured_findings(visible_findings,evidence,cited)",
 'allow_public_web=source_choice',
])assert.ok(server.includes(field),'Server source enforcement missing: '+field);
for(const field of [
 "def normalize_workflow_request(",
 "def structured_findings(",
 "def retrieval_question_for_revision(",
 "def source_consultation(",
 "DRAFT_ONLY_STAFF_REVIEW_AND_SEND",
])assert.ok(workflows.includes(field),'Structured source contract missing: '+field);
assert.ok(orchestra.includes('workflow_system_directive(workflow_mode)'));
assert.ok(orchestra.includes('bool(allow_public_web)'));
assert.ok(orchestra.includes('"decision_plan":['));
assert.ok(history.includes('"source_consultation":['));
assert.ok(history.includes('"structured_findings":['));
assert.ok(history.includes('"decision_plan":['));
console.log('PASS BAWASLU v175.83: Management/Operations separation and source-grounded AI modes');
