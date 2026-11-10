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
assert.ok(app.includes('path="/casework"')&&app.includes('LegacyCaseworkRedirect'),
  'old assignment links redirect into the Intelligence Inbox, not a separate page');
assert.ok(!nav.includes("'/casework'")&&!nav.includes('Penugasan & Laporan'),
  'sidebar must not contain a separate Assignments & Reports module');
assert.ok(app.includes('demoLocation?<Navigate to="/social-listening" replace/>:<LegacyCaseworkRedirect/>'),
  'isolated training demo cannot enter live casework');
assert.ok(!nav.includes('casework'),'training and normal navigation omit the separate module');
assert.ok(casework.includes('/cases/')&&casework.includes('/reports/'),'case/report server actions');
assert.ok(casework.includes('verified_province'),'no automatic location authority');
assert.ok(casework.includes('Buat draf analisis dengan AI'),'explicit AI draft only');
assert.ok(casework.includes('Matriks')===false,'workflow UI does not impersonate a legal finding');
assert.ok(source.includes("t('prepare_from_source')")&&source.includes('/inbox?casework=1'),
  'assistant evidence sources open the in-Inbox assignment workflow');
assert.ok(inbox.includes('onOpenCasework({sourceType:')&&inbox.includes('selected.campaign_id'),
  'a selected Inbox post offers contextual assign and report actions');
assert.ok(inbox.includes('initialSource={caseworkRequest.sourceId?caseworkRequest:null}')&&
  inbox.includes('<Casework key={JSON.stringify(caseworkRequest)} embedded'),
  'case and report editor is embedded inside Intelligence Inbox');
assert.ok(inbox.includes("queue:'assigned_to_me'")&&inbox.includes("queue:'needs_my_review'"),
  'Inbox provides assigned work and report-approval filters without a new module');
assert.ok(!assistant.includes('Hybrid · Saved evidence + GPT context'),'no technical model banner');
assert.ok(display.includes('friendlySource'),'answer status labels routed to shared multilingual formatter');
assert.ok(read('src/lib/assistantResponseLocale.js').includes('UNVERIFIED_SOCIAL_SOURCE'),'technical source states formatted for display');
assert.ok(assistant.includes('AssistantActionDesk')&&assistant.includes('UserWorkspacePulse'),
    'assistant provides a visible operational workspace');
assert.ok(desk.includes('/assistant-handoff')&&desk.includes('confirm:true'),
    'officer confirmation is required for the one-step case and report handoff');
assert.ok(desk.includes('/preview?')&&desk.includes('recommended_department'),
    'the assistant verifies the source and pre-selects a department');
assert.ok(desk.includes("navigate('/inbox?casework=1&case_id=")&&desk.includes("tab=reports"),
    'AI handoff opens the prepared report within Intelligence Inbox');
assert.ok(desk.includes('isDemo()')&&desk.includes('options?.can_create'),
    'demo isolation and role access are enforced in the UI');
assert.ok(!desk.includes('base44.functions.invoke'),
    'handoff reuses existing analysis without extra paid model request');
assert.ok(casework.includes("params.get('case_id')")&&casework.includes("params.get('tab')")&&
    casework.includes('initialSource')&&casework.includes('initialCaseId'),
    'embedded workflow opens selected evidence, saved cases and report drafts immediately');
assert.ok(casework.includes('const opening=')&&casework.includes('p.recommended_department')&&
    casework.includes('previewAttempted.current=true'),
    'source selection preloads AI tags and department recommendation without retyping IDs');

assert.ok(casework.includes("const filteredCases=useMemo")&&casework.includes("queueFilter==='all'"),
  'officer queue filters use actual backend flags');
assert.ok(casework.includes('b.queue_counts')&&casework.includes("needs_my_review"),
  'casework counters display server-filtered pending approvals');
assert.ok(casework.includes('/acknowledge')&&casework.includes("detail?.can_acknowledge")&&
  casework.includes("Accept & start review"),
  'receiving officer can accept work without additional forms');
assert.ok(casework.includes("queueFilter==='needs_my_review')setTab('reports')"),
  'pending review queue goes straight to reports');
assert.ok(casework.includes("language==='en'")&&casework.includes("tr('All cases','Semua kasus')"),
  'new operational queue labels follow app language');
assert.ok(!desk.includes("navigate('/casework")&&!source.includes("to={'/casework?"),
  'no assistant action sends an officer to the standalone casework page');
assert.ok(inbox.includes('data-inbox-workflow-drawer')&&
  inbox.includes('max-w-[640px]')&&inbox.includes('min-h-0 flex-1 overflow-y-auto'),
  'Inbox workflow stays a narrow independently scrolling side panel, not an entire page');
assert.ok(casework.includes('data-inbox-queue-picker')&&casework.includes('data-inbox-empty-state'),
  'embedded workload uses a compact filter and useful empty state, not six cards');
assert.ok(casework.includes("{!embedded&&<section className=\"intel-card p-3 print:hidden\""),
  'standalone six-card queue dashboard never renders inside Inbox');
assert.ok(casework.includes('!emptyQueue&&<div')&&casework.includes('focused=embedded&&'),
  'empty queues do not render the two-column blank assignment workspace');
assert.ok(casework.includes('!embedded&&options?.can_create&&<button'),
  'generic new-assignment button is removed from Inbox; begin from a selected source');
assert.ok(casework.includes("tr('Assignment','Penugasan')")&&
  casework.includes("tr('Report','Laporan')")&&casework.includes("tr('Save assignment','Simpan penugasan')"),
  'the main assignment and report controls follow the selected interface language');
assert.ok(inbox.includes("caseworkRequest.sourceId?")&&
  inbox.includes("language==='en'?'Work with this post':'Tindak lanjut unggahan'"),
  'drawer heading responds to source-specific versus workload context');
console.log('In-Inbox assignment, report and approval integration checks passed');
