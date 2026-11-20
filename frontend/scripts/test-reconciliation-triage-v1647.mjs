import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const metric=read('../backend/app/monitoring_metric_reconciliation.py');
const count=read('../backend/app/monitoring_count_integrity.py');
for(const term of ['actionable_metric_discrepancies','PRESENTATION_REPEAT_ONLY',
 'METADATA_CONFLICT','METRIC_MISMATCH','recommended_next_check',
 'presentation_duplicate_occurrences'])assert.ok(metric.includes(term),term);
for(const term of ['actionable_count_discrepancies','PRESENTATION_REPEAT_ONLY',
 'MISSING_OR_UNEXPECTED_SOURCE','presentation_duplicate_occurrences'])
 assert.ok(count.includes(term),term);
assert.ok(metric.includes('not actionable'));
assert.ok(count.includes('"internal_count_reconciliation_passed":not actionable'));
const version=readBackendVersion(read('../backend/app/main.py'));
assert.ok(Number(version.replace('.',''))>=1647);
assert.ok(hasDynamicBuildVersion(read('src/components/intel/Shell.jsx'),version));
console.log('PASS v164.7 classify benign repeated findings vs actionable data inconsistencies');
