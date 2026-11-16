import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const ui=read('src/pages/Casework.jsx');
const backend=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const key of ['expandedReportId','setExpandedReportId(old=>old===r.id?null:r.id)',
 'aria-expanded={expandedReportId===r.id}',
 "aria-controls={'casework-report-preview-'+r.id}",
 'casework-inline-report-preview','Full report content','Read-only report preview',
 "'executive_summary'","'findings'","'verification_notes'","'recommendations'",
 'Reviewer feedback']) assert.ok(ui.includes(key),key);
assert.ok(ui.indexOf('casework-inline-report-preview')>ui.indexOf("tr('View report','Baca laporan')"));
assert.ok(ui.includes("setEditReport(r.id);setForm("),"Returned report editor still reachable");
const bv=backend.split("'build_version':'")[1]?.split("'")[0];
const fv=shell.split('data-build-version="')[1]?.split('"')[0];
assert.equal(bv,fv);
assert.ok(Number(bv.split('.').join(''))>=1567,'Version must not regress below v156.7');
console.log('PASS v156.7 report view expands full read-only contents in place');
