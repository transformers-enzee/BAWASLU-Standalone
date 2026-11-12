import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const api=read('../backend/app/finding_assessments.py');
const caseApi=read('../backend/app/casework.py');
const ui=read('public/ui-freeze/finding-assessments-v1470.js');
const casePage=read('src/pages/Casework.jsx');
const inbox=read('src/pages/Inbox.jsx');
const app=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');

assert.ok(api.includes('contextual_casework_links')&&api.includes('source_actions'),
    'Finding assessment returns contextual, source-linked officer actions');
assert.ok(api.includes('can_view_case(case,permission,user_id)'),
    'Existing assignments checked against the user jurisdiction');
assert.ok(api.includes('source_id.in_(source_ids)')&&api.includes('campaign_id.in_(campaign_ids)'),
    'Related case lookup must be bound to relevant authorized social sources');
assert.ok(api.includes('"casework":1')&&api.includes('case_id'),
    'Existing case deep links do not create a replacement');
assert.ok(api.includes('officer_confirmation_required')&&api.includes('no_assignment_created'),
    'No automatic case creation or takedown on assessment read');
assert.ok(ui.includes('data-officer-casework')&&ui.includes('source.casework_url'),
    'Finding detail presents its source-specific handoff');
assert.ok(ui.includes('source.existing_case_id')&&ui.includes('Read-only access: assignment creation is not permitted'),
    'Existing officer cases are distinguished from possible new assignments');
assert.ok(!ui.includes("method:'POST'"),
    'No direct auto-case-creation HTTP action in the Command Centre drawer');
assert.ok(inbox.includes("q.get('source_id')")&&inbox.includes("q.get('campaign_id')"),
    'Inbox restores exact social source from contextual link');
assert.ok(inbox.includes("q.has('case_id')")&&inbox.includes('initialCaseId'),
    'Existing assignments are deep-linked into the embedded workflow');
assert.ok(caseApi.includes('def _authorized_cases_query')&&
    caseApi.includes('CaseAssignment.target_province == province'),
    'SQL authorization precedes the 300-row officer queue limit');
assert.ok(caseApi.includes('def _current_report_ids')&&
    caseApi.includes('report.status=="SUBMITTED"'),
    'Only latest submitted report versions appear in review queue');
assert.ok(caseApi.includes('A newer report exists; open the latest report for review'),
    'Outdated approval transitions must fail with a conflict');
assert.ok(casePage.includes('r.is_latest_version')&&
    casePage.includes('Superseded report version'),
    'Superseded reports are visible history, not approvable reports');
assert.ok(casePage.includes('!activeReport?.is_latest_version'),
    'Outdated report drafts are not editable in the UI');
const backendVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const frontendVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(backendVersion&&frontendVersion&&backendVersion===frontendVersion,
  'Build version matches both backend and frontend');
console.log('PASS v147.8 contextual officer follow-up, current-version report approval and SQL authorization contracts');
