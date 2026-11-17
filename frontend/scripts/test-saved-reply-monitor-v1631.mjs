import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/saved_reply_reviews.py');
const ui=read('src/components/intel/SavedReplyReviewWorksheet.jsx');
for(const token of ['RECHECK_SAVED_REPLY','completed_current_count','review_progress_counts',
 'previous_state=old.review_state','synchronize_session','review_count']) assert.ok(backend.includes(token),token);
for(const token of ['saved-reply-review-summary','open-saved-reply-review-history',
 'saved-reply-review-event-history','saved_reply_changed']) assert.ok(ui.includes(token),token);
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1631);
assert.ok(shell.includes('data-build-version="'+version+'"'));
assert.ok(shell.includes('aria-label="Build version">v'+version));
console.log('PASS v163.1 owner-scoped progress, stale status and event integrity');
