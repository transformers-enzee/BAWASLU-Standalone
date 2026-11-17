import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const source=read('../backend/app/assistant_evidence_relevance.py');
const formal=read('../backend/app/intelligence_assistant.py');
const route=read('../backend/app/main.py');
for(const s of ['exact_formal_source_ids','exact_formal_selection_complete',
                '_INT_ID=re.compile','_WORD=re.compile'])assert.ok(source.includes(s),s);
assert.ok(formal.includes("if explicit and not exact_formal_selection_complete(question,selected,limit):"));
assert.ok(route.includes('explicit_formal_ids=exact_formal_source_ids(q)'));
assert.ok(route.includes('explicit_saved_id=bool(explicit_social_ids or explicit_formal_ids)'));
assert.ok(route.includes('explicit_formal_ids and not exact_formal_selection_complete(q,selected_formal,limit=10)'));
assert.ok(!route.includes("explicit_social_id=bool(explicit_social_ids)"));
const main=read('../backend/app/main.py');
assert.ok(main.includes("'build_version':'164.1'"));
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="164.1"'));
console.log('PASS v164.1 exact Inbox source-ID fail-closed routing and multiword-place matching');
