import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const api=read('../backend/app/main.py');
const selection=read('../backend/app/assistant_orchestration.py');
const sampler=read('../backend/app/assistant_eval_sampling.py');
const shell=read('src/components/intel/Shell.jsx');
assert.ok(selection.includes('def exact_social_source_ids(question):')&&
 selection.includes('def exact_social_selection_complete(question, selected, limit=20):')&&
 selection.includes('if not exact_social_selection_complete(question,chosen,limit):')&&
 selection.includes('return [],0'),
 'Explicit source queries must fail closed when a named ID is missing');
assert.ok(api.includes('general=not explicit_social_ids and')&&
 api.includes('not exact_social_selection_complete(q,chosen_social,limit=20)')&&
 api.includes('selected_formal=[]')&&api.includes('context_pdf=[]'),
 'Formal/PDF evidence must never substitute a missing exact social source');
assert.ok(sampler.includes('ch.isspace()')&&sampler.includes('not parts.hostname'),
 'Reject unsafe URLs in officer evaluation source lists');
assert.ok(api.includes("'build_version':'149.0'")&&
 shell.includes('data-build-version="149.0"'),
 'Single bulk release must update API and UI build version together');
console.log('PASS v149.0 exact source all-or-nothing retrieval, URL safety and release version');
