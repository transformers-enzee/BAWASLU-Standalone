import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const helper=read('../backend/app/assistant_cross_module_inventory.py');
const model=read('../backend/app/assistant_orchestration.py');
const mapping=read('../backend/app/intelligence_assistant.py');
for(const x of ['def cross_module_inventory','explicit_source_links',
 'shared_source_is_not_independent_witness','selected_social_posts',
 'selected_inbox_records','unlinked_inbox_records','NOT two independent witnesses'])
 assert.ok(helper.includes(x),x);
assert.ok(mapping.includes("'origin_source_id':item.source_id"));
assert.ok(model.includes('"cross_module_inventory":cross_module_inventory(evidence)'));
assert.ok(model.includes('module_focus=cross_module_instruction(response_profile)'));
const version=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(version.replace('.',''))>=1639);
assert.ok(hasDynamicBuildVersion(read('src/components/intel/Shell.jsx'),version));
console.log('PASS v163.9 current selected social vs Inbox source identity, no false corroboration');
