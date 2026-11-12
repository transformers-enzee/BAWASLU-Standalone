import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const backend=read('../backend/app/management_reporting.py');
const template=read('../backend/app/management_report_templates.py');
const ui=read('src/components/intel/ManagementBriefings.jsx');
const app=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');

assert.ok(backend.includes('def monitoring_snapshot_from_findings'), 'Pure monitoring view required');
assert.ok(backend.includes('live_inbox_findings(db, access)'), 'Reuse authorized saved Inbox only');
assert.ok(backend.includes('_utc_publication_time'), 'No capture-time/publication-time mixing');
assert.ok(backend.includes('groups.setdefault(sid')&&backend.includes('grouped["signals"].update(signals)'),
  'Deduplicate cross-finding source links without dropping other signals');
assert.ok(backend.includes('if not (start<=published<=end)'), 'Rolling UTC date window');
assert.ok(backend.includes('source_publication_time_conflicts')&&
  backend.includes('source_sentiment_conflicts'),
  'Report source metadata conflicts instead of arbitrarily choosing first link');
assert.ok(backend.includes('inbox_truncation_status":"UNKNOWN"'),
  'Never claim complete provider collection from a sample');
assert.ok(backend.includes('source_basis":"PERMISSION_SCOPED_SAVED_INTELLIGENCE_INBOX"'),
  'Provenance must remain visible');
assert.ok(backend.includes('if include_monitoring:'),
  'Casework-only report is the default for speed');
assert.ok(backend.includes('X-Report-Monitoring'),
  'Export must disclose the monitoring sample flag');
assert.ok(template.includes('monitoring_enabled')&&template.includes('monitoring_summary'),
  'Exports reflect optional monitoring with explicit caveats');
assert.ok(template.includes('unapproved')||template.includes('DRAFT_NOT_APPROVED'),
  'Report remains an unsigned internal draft');
assert.ok(ui.includes('data-testid="briefing-monitoring-option"')&&
  ui.includes('include_monitoring:String(includeMonitoring)'),
  'Explicit opt-in not an unbounded default backend query');
assert.ok(ui.includes('data-testid="briefing-signal-overlap"')&&
  ui.includes('monitoring.source_publication_time_conflicts'),
  'Management UI must explain non-additive preliminary signals and conflicts');
assert.ok(ui.includes('data-testid="briefing-intelligence-monitoring"')&&
  ui.includes('monitoring.publication_date_unknown'),
  'Onscreen monitoring distinguishes missing source dates');
const backendVersion=app.match(/'build_version':'(\d+\.\d+)'/)?.[1];
const frontendVersion=shell.match(/data-build-version="(\d+\.\d+)"/)?.[1];
assert.ok(backendVersion&&frontendVersion&&backendVersion===frontendVersion,
  'Backend and frontend version must match');
console.log('PASS v148.2 optional sampled monitoring, date-bound integrity and export provenance');
