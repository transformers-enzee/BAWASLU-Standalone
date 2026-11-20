import {readBackendVersion,readShellVersion,hasDynamicBuildVersion} from './runtime-build-contract.mjs';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const page=read('src/pages/IntelligenceAssistant.jsx');
assert.ok(page.includes('function prepareFreshSourceCheck(index)'), 'Operational refresh must be available');
assert.ok(page.includes('data-testid="assistant-historical-source-caution"'));
assert.ok(page.includes('data-testid="assistant-prepare-fresh-source-check"'));
assert.ok(page.includes("reviewableIndexes.has(i)&&m.response_profile==='ACTION_REQUEST'"),
 'Saved historical action response cannot initiate live casework without a fresh answer');
const block=page.slice(page.indexOf('function prepareFreshSourceCheck(index)'),page.indexOf('function scoreThisAnswer(index)'));
for(const token of ['setActive(null)','setMessages([])','setReviewableIndexes(new Set())',
 'setQuestion(prompt.slice(0,1000))',"setAnalysisMode('DATA')"])
 assert.ok(block.includes(token),'Fresh question needs isolation and saved evidence mode: '+token);
assert.ok(!block.includes('base44.functions.invoke'), 'Preparing a question must use zero AI calls');
assert.ok(!block.includes('historyRequest('),'Historical source refresh must not overwrite the previous chat');
const banner=page.slice(page.indexOf('data-testid="assistant-historical-source-caution"'),
 page.indexOf('m.grounding?.grounding_audit&&!showQa'));
assert.ok(banner.includes('until you press Send'),'Clear opt-in needed for paid AI call');
const main=read('../backend/app/main.py'),shell=read('src/components/intel/Shell.jsx');
const version=readBackendVersion(main);
assert.ok(Number(version.replace('.',''))>=1636);
assert.ok(hasDynamicBuildVersion(shell,version));
assert.ok(shell.includes('aria-label="Build version">v'+version));
console.log('PASS v163.6 safe historical Assistant reply labeling, fresh-question preparation and action gate');
