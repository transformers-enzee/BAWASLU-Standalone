import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const files={
  shared:read('../../backend/app/assistant_orchestration.py'),
  legacy:read('../../backend/app/main.py'),
  v2:read('../../backend/app/ai_assistant_v2.py'),
  trail:read('../src/components/intel/AssistantWorkflowEvidence.jsx')
};
for(const key of ['PROVIDER_HTTP_','PROVIDER_INCOMPLETE_','PROVIDER_NO_ATTRIBUTABLE_URLS','PROVIDER_TIMEOUT','PROVIDER_SEARCH_TOOL_NOT_EXECUTED','OPENAI_WEB_SEARCH_MODEL'])
 assert.ok(files.shared.includes(key),'Shared web diagnostics missing: '+key);
for(const key of ['diagnostics=web_diagnostics','discovery_status','search_status'])
 assert.ok(files.legacy.includes(key),'Existing Assistant diagnostics missing: '+key);
for(const key of ['diagnostics=web_diagnostics','web_discovery_status','web_search_status'])
 assert.ok(files.v2.includes(key),'AI Assistant diagnostics missing: '+key);
assert.ok(files.trail.includes('Web research status:'));
assert.ok(files.shared.includes('When external_public_research is supplied'),'Executive report must admit independently read web pages');
assert.ok(!files.shared.includes('no online research or PDF assumptions'),'Conflicting internal-only executive instruction must be removed');
console.log('PASS v178.7: search failure diagnostics wired through both assistants');
