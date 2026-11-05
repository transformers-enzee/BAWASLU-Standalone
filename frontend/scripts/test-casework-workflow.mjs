import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const app=read('src/App.jsx');
const nav=read('src/components/intel/AccessNavigation.jsx');
const casework=read('src/pages/Casework.jsx');
const assistant=read('src/pages/IntelligenceAssistant.jsx');
const source=read('src/components/intel/AssistantRecords.jsx');
const inbox=read('src/pages/Inbox.jsx');
const display=read('src/components/intel/TranslatedAssistantAnswer.jsx');
const desk=read('src/components/intel/AssistantActionDesk.jsx');
assert.ok(app.includes('path="/casework"')&&app.includes('Casework'),'casework route');
assert.ok(nav.includes("'/casework'")&&nav.includes('Penugasan & Laporan'),'side navigation');
assert.ok(app.includes('demoLocation?<Navigate to="/social-listening" replace/>:<Casework />'),'isolated training demo cannot enter live casework');
assert.ok(nav.includes("path!=='/casework'"),'training demo hides assignment navigation');
assert.ok(casework.includes('/cases/')&&casework.includes('/reports/'),'case/report server actions');
assert.ok(casework.includes('verified_province'),'no automatic location authority');
assert.ok(casework.includes('Buat draf analisis dengan AI'),'explicit AI draft only');
assert.ok(casework.includes('Matriks')===false,'workflow UI does not impersonate a legal finding');
assert.ok(source.includes("t('prepare_from_source')"),'assistant-to-casework deep link');
assert.ok(inbox.includes('Buat penugasan & laporan')&&inbox.includes('selected.campaign_id'),'Inbox-to-casework evidence link');
assert.ok(!assistant.includes('Hybrid · Saved evidence + GPT context'),'no technical model banner');
assert.ok(display.includes('UNVERIFIED_SOCIAL_SOURCE')&&display.includes('AI_RELEVANCE_NOT_LEGAL_VERIFICATION'),'technical statuses translated for users');
assert.ok(assistant.includes('AssistantActionDesk')&&assistant.includes('UserWorkspacePulse'),
    'assistant provides a visible operational workspace');
assert.ok(desk.includes('/assistant-handoff')&&desk.includes('confirm:true'),
    'officer confirmation is required for the one-step case and report handoff');
assert.ok(desk.includes('/preview?')&&desk.includes('recommended_department'),
    'the assistant verifies the source and pre-selects a department');
assert.ok(desk.includes('navigate(')&&desk.includes("tab=reports"),
    'handoff opens the prepared report');
assert.ok(desk.includes('isDemo()')&&desk.includes('options?.can_create'),
    'demo isolation and role access are enforced in the UI');
assert.ok(!desk.includes('base44.functions.invoke'),
    'handoff reuses existing analysis without extra paid model request');
assert.ok(casework.includes("params.get('case_id')")&&casework.includes("params.get('tab')"),
    'casework opens the assigned case and ready report immediately');
assert.ok(casework.includes('const opening=')&&casework.includes('p.recommended_department'),
    'casework opens the prepared draft and preselects the saved source department');

console.log('Casework and reporting frontend checks passed');
