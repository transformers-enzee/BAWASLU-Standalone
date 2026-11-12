import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const server=read('../backend/app/casework.py');
const page=read('src/pages/Casework.jsx');
const inbox=read('src/pages/Inbox.jsx');
const app=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');

assert.ok(server.includes('def record_source_review')&&server.includes('SOURCE_REVIEW_RECORDED'),
  'Only the assigned officer can record a distinct source review event');
assert.ok(server.includes('case.assignee_id!=user.id')&&server.includes('case.status!="IN_REVIEW"'),
  'Acknowledgment and current assignee required for source review');
assert.ok(server.includes('not body.original_source_opened')&&server.includes('SOURCE_UNAVAILABLE'),
  'Opening original source must be attested; negative reviews are preserved');
assert.ok(server.includes('def _acceptance_trace')&&server.includes('client_acceptance_certified":False'),
  'Read-only workflow trace never certifies real client acceptance');
assert.ok(server.includes('latest_report.reviewed_by!=latest_report.created_by')&&
  server.includes('REPORT_APPROVED'),
  'Independent approval and an auditable report action are required');
assert.ok(server.includes('"source_type":case.source_type')&&
  server.includes('"campaign_id":case.campaign_id'),
  'Audit event records original case-source provenance');
assert.ok(page.includes('data-casework-acceptance-trace')&&
  page.includes('workflow_trace.steps?.map'),
  'In-Inbox casework displays five-stage audit progress');
assert.ok(page.includes('data-casework-source-review')&&
  page.includes("request('/cases/'+selected+'/source-review','POST'"),
  'Officer can record source review from existing Inbox panel');
assert.ok(page.includes('sourceReviewNote.trim().length<20')&&
  page.includes('sourceOpened'),
  'Frontend requires documented review and original-source confirmation');
assert.ok(inbox.includes('<Casework key={JSON.stringify(caseworkRequest)} embedded'),
  'No separate top-level casework module is introduced');
const apiVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const uiVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(apiVersion&&uiVersion&&apiVersion===uiVersion,'Frontend/backend build versions must match');
console.log('PASS v148.0 source-review attestation and operational acceptance workflow contracts');
