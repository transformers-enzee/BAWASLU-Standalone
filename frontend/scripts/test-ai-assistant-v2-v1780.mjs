import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const app=read('../src/App.jsx');
const nav=read('../src/components/intel/AccessNavigation.jsx');
const home=read('../src/pages/ManagementHome.jsx');
const main=read('../../backend/app/main.py');
const replacement=read('../src/pages/UnifiedAIAssistant.jsx');
const legacy=read('../../backend/app/ai_assistant_v2.py');
// Historical v178.0 contract is RETIRED as of v179.1. Preserve its source
// for rollback, but neither default route nor router may execute it.
assert.ok(app.includes('UnifiedAIAssistant workspace="OPERATIONAL"'));
assert.ok(app.includes('UnifiedAIAssistant workspace="MANAGEMENT"'));
assert.ok(nav.includes("['/ai-assistant','AI Assistant'"));
assert.ok(nav.includes("['/management/ai-assistant','AI Assistant'"));
assert.ok(!nav.includes('retired.has(path)'),'No assistant may be hidden by a retirement filter');
for(const path of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4',
                  '/management/assistant','/management/ai-assistant',
                  '/management/ai-assistant-v2-new','/management/ai-4'])
 assert.ok(nav.includes("'"+path+"'"),'Previous assistant is missing from navigation: '+path);
assert.ok(home.includes('/management/ai-assistant'),'Management homepage link');
assert.ok(main.includes('app.include_router(unified_ai_router)'));
assert.ok(!main.includes('app.include_router(ai_assistant_v2_router)'),
  'Retired handler must no longer serve normal AI Assistant requests');
assert.ok(legacy.includes('@router.post("/chat")'),'Legacy module preserved for safe migration only');
for(const id of ['unified-ai-page','unified-research-trail','unified-ai-draft',
                 'unified-action','WEB_ONLY','WEB_SMARTRADAR','SMARTRADAR_ONLY'])
 assert.ok(replacement.includes(id),'Replacement missing: '+id);
console.log('PASS: primary AI Assistant route preserved, all prior assistants visible alongside AI-4');
