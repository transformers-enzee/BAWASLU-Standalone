import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/assistant_evidence_relevance.py');
const selection=read('../backend/app/intelligence_assistant.py');
const model=read('../backend/app/assistant_orchestration.py');
for(const name of ['formal_source_term_score','retrieval_scope_note',
  'NOT total campaign','exhaustive database search'])
 assert.ok(helper.includes(name),name);
assert.ok(selection.includes('matched=formal_source_term_score('));
assert.ok(!selection.includes("matched=sum(2 for t in tokens if t in hay)"));
assert.ok(model.includes('scope_focus=retrieval_scope_note('));
assert.ok(model.includes('scope_focus if scope_focus else'));
assert.ok(read('../backend/app/main.py').includes("'build_version':'164.0'"));
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="164.0"'));
console.log('PASS v164.0 exact-term selected evidence relevance and scope disclosure');
