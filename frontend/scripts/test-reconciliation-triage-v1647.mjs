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
const version=read('../backend/app/main.py').split("'build_version':'")[1]?.split("'")[0];
assert.equal(version,'164.7');
assert.ok(read('src/components/intel/Shell.jsx').includes('data-build-version="'+version+'"'));
console.log('PASS v164.7 classify benign repeated findings vs actionable data inconsistencies');
