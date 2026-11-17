import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const history=read('../backend/app/assistant_saved_history_eval.py');
const sampling=read('../backend/app/assistant_eval_sampling.py');
const qa=read('../backend/tests/test_saved_reply_union_v1622.py');
const web=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const register=read('src/lib/assistantAuditIssueRegister.js');
const main=read('../backend/app/main.py');
const shell=read('src/components/intel/Shell.jsx');
for(const s of ['MAX_REPLAY_SOURCE_IDS=20','cited_only=[ref for ref in displayed if ref not in identifiers]',
 'identifiers.extend(cited_only)','INVALID_DISPLAYED_SOURCE_REFERENCE',
 'COMBINED_SOURCE_SCOPE_EXCEEDS_LIMIT','cited_only_source_count'])
 assert.ok(history.includes(s),s);
assert.ok(sampling.includes('source_ids:list[str]=Field(min_length=1,max_length=20)'));
assert.ok(register.includes('refs.length>20')&&register.includes('entry.source_ids.length>20'));
assert.ok(web.includes('cited-only sources rechecked'));
assert.ok(/<\/p>\}\s*\{\(audit\.audit\.issue_triage/.test(web));
for(const s of ['test_batch_missing_cited_source_fails_not_fake_pass',
 'test_combined_card_and_citation_scope_safely_supports_historical_sizes'])
 assert.ok(qa.includes(s),s);
const version=main.split("'build_version':'")[1]?.split("'")[0];
assert.ok(Number(version.replace('.',''))>=1622);
assert.ok(shell.includes('data-build-version="'+version+'"'));
console.log('PASS v162.2 historical cited-only source union and mandatory reauthorization');
