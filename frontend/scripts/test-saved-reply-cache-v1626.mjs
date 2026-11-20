import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const core=read('../backend/app/assistant_eval_sampling.py');
const hist=read('../backend/app/assistant_saved_history_eval.py');
const ui=read('src/components/intel/AssistantSavedReplyAudit.jsx');
for(const s of ['"_assistant_eval_batch_cache"','"scoped_findings"','"scoped_formal"'])
 assert.ok(core.includes(s),s);
for(const s of ['batch_principal={**principal','saved_cards_without_displayed_citations','SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS'])
 assert.ok(hist.includes(s),s);
assert.ok(ui.includes('batch.citation_coverage_counts'));
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const ver=readBackendVersion(main);
assert.ok(Number(ver.replace('.',''))>=1626);
assert.ok(hasDynamicBuildVersion(shell,ver));
console.log('PASS v162.6 scoped batch evidence caching and uncited historical cards');
