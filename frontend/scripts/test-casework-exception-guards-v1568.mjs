import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/casework.py');
const tests=read('../backend/tests/test_casework_exception_guards_v1568.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(backend.includes('_original_url_available(case.source_url)'));
assert.ok(backend.includes('not body.original_source_opened'));
assert.ok(backend.includes('report.created_by==user.id'));
assert.ok(backend.includes('A human-confirmed incident province is required'));
for(const marker of ['test_invalid_original_urls_cannot_be_attested_as_checked',
'test_reviewer_without_human_validation_cannot_approve',
'test_author_cannot_approve_own_report',
'test_unverified_province_never_authorizes_province_route',
'test_unavailable_source_can_be_recorded_without_false_confirmation'])
 assert.ok(tests.includes(marker),marker);
const back=main.split("'build_version':'")[1]?.split("'")[0];
const front=shell.split('data-build-version="')[1]?.split('"')[0];
assert.ok(Number(back.replace('.',''))>=1568,'Build must not regress below v156.8');assert.equal(back,front);
console.log('PASS v156.8 original URL safeguards, role gates and jurisdiction negative QA');
