import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/finding_case_progress.py');
const finding=read('../backend/app/finding_assessments.py');
const management=read('../backend/app/management_reporting.py');
const template=read('../backend/app/management_report_templates.py');
const plugin=read('public/ui-freeze/finding-assessments-v1470.js');
const report=read('src/components/intel/ManagementBriefings.jsx');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const signal of ['BAWASLU_CASEWORK_AUDIT_PROGRESS_V1534','_acceptance_trace',
                     'row_number().over','latest_report_version_only','no_casework_action_created']){
 assert.ok(backend.includes(signal),signal);
}
assert.ok(finding.includes('summarize_authorized_case_progress(db,selected_cases)'));
assert.ok(finding.includes('action.get("workflow_progress")'));
assert.ok(finding.includes('can_create=has(permission,"add_intelligence")'));
assert.ok(plugin.includes('data-testid="finding-casework-audit-progress"'));
assert.ok(plugin.includes('caseworkProgressHtml(row.workflow_progress)'));
assert.ok(plugin.includes('caseworkProgressHtml(source.workflow_progress)'));
assert.ok(plugin.includes('not proof of source truth'));
assert.ok(management.includes('"source_review_event_not_observed_in_window"'));
assert.ok(management.includes('"additional_database_queries":0'));
assert.ok(template.includes('absence')||template.includes('Absence')||template.includes('Absence is'));
assert.ok(report.includes('data-testid="briefing-casework-progress"'));
assert.ok(report.includes('source_review_event_not_observed_in_window'));
const version=main.match(/'build_version':'(\d+\.\d+)'/)?.[1];
assert.ok(version);
const [major,minor]=version.split('.').map(Number);
assert.ok(major>153||(major===153&&minor>=4));
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v153.4 authorized casework audit progress, report follow-up, release contracts');
