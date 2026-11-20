import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/saved_reply_reviews.py');
const ui=read('src/components/intel/SavedReplyReviewWorksheet.jsx');
for(const s of ['review_action_counts','needs_attention_count','last_owner_review_activity_at',
 'history_truncated','MOST_RECENT_50','id.desc()'])assert.ok(backend.includes(s),s);
for(const s of ['refresh-saved-review-progress','saved-review-history-truncated',
 'review_action_required','summary.review_action_counts'])assert.ok(ui.includes(s),s);
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=readBackendVersion(main);
assert.ok(Number(version.replace('.',''))>=1632);
assert.ok(hasDynamicBuildVersion(shell,version));
assert.ok(shell.includes('aria-label="Build version">v'+version));
console.log('PASS v163.2 operational reviewer activity, stale history, last-50 window');
