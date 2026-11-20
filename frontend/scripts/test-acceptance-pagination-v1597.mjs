import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/assistant_acceptance_submissions.py');
const ui=read('src/pages/AcceptanceReview.jsx');
const qa=read('../backend/tests/test_assistant_acceptance_pagination_v1597.py');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const k of ['before_id:int|None=None','query.filter(AssistantAcceptanceEvidence.id<before_id)',
                  'limit(101)','next_before_id','more_older_records',
                  'PAGE_OF_UP_TO_100_SUBMISSIONS_ONLY','private, no-store'])
 assert.ok(api.includes(k),k);
for(const k of ['?before_id=','cursorTrail','Older records','Newer records',
                  'Counts are page-scoped','onClick={()=>refresh(beforeId)}'])
 assert.ok(ui.includes(k),k);
for(const k of ['test_multiple_pages_cover_every_record_without_duplicates',
                  'test_pagination_keeps_query_count_bounded',
                  'test_invalid_cursor_rejected']) assert.ok(qa.includes(k),k);
const v=readBackendVersion(main);
assert.ok(Number(v.replace('.',''))>=1597);
assert.ok(hasDynamicBuildVersion(shell,v));
console.log('PASS v159.7 bounded historical acceptance pagination and safeguards');
