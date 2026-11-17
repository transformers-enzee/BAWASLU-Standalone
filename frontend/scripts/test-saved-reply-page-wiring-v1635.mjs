import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {canShowAssistantQa} from '../src/lib/assistantQaVisibility.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const page=read('src/pages/IntelligenceAssistant.jsx');
const audit=read('src/components/intel/AssistantSavedReplyAudit.jsx');
const version=read('../backend/app/main.py').split("'build_version':'")[1]?.split("'")[0];
const shell=read('src/components/intel/Shell.jsx');
assert.ok(Number(version.replace('.',''))>=1635);
assert.ok(shell.includes('data-build-version="'+version+'"'));
assert.ok(shell.includes('aria-label="Build version">v'+version));
assert.ok(page.includes("import AssistantSavedReplyAudit from '@/components/intel/AssistantSavedReplyAudit'"));
assert.equal((page.match(/<AssistantSavedReplyAudit\s+disabled=\{busy\|\|historyBusy\}\s*\/>/g)||[]).length,1,
 'Saved reply QA must be mounted once, and disabled during active Assistant/history operations');
const section=page.indexOf('data-testid="assistant-qa-tools-content"');
const mounted=page.indexOf('<AssistantSavedReplyAudit disabled={busy||historyBusy}/>');
const closed=page.indexOf('   </div>}\n  </section>}',section);
assert.ok(section>=0&&mounted>section&&closed>mounted,'Saved reply audit must be inside admin QA panel');
assert.ok(page.includes('const showQa=canViewQa&&qaOpen;'));
assert.ok(page.includes('{showQa&&<div data-testid="assistant-qa-tools-content"'));
for(const s of ['assistant-load-pilot-review-queue','assistant-select-pilot-batch',
 'assistant-export-pilot-handoff','assistant-run-saved-reply-audit'])
 assert.ok(audit.includes(s),'Mounted component is missing UI control '+s);
const admin={status:'Active',role:'National Administrator',permissions:{view_intelligence:true,administration:true}};
assert.equal(canShowAssistantQa(admin),true);
assert.equal(canShowAssistantQa(admin,{demo:true}),false);
assert.equal(canShowAssistantQa({...admin,role:'Provincial Analyst'}),false);
assert.equal(canShowAssistantQa({...admin,permissions:{view_intelligence:true,administration:false}}),false);
console.log('PASS v163.5 saved-reply pilot QA panel mounting, admin gate, controls and release version');
