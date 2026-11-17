import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const backend=read('../backend/app/saved_reply_reviews.py');
const ui=read('src/components/intel/SavedReplyReviewWorksheet.jsx');
for(const code of ['review_ai_suggestions','SavedReplyReviewEvent','reply_fingerprint',
 'resolve_mixed_audit_sources','expected_version','rowcount!=1'])
 assert.ok(backend.includes(code),code);
for(const code of ['save-persistent-saved-reply-review','expected_version','saved_reply_changed'])
 assert.ok(ui.includes(code),code);
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1630);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v163.0 owner-scoped persistent reviews and history checks');
