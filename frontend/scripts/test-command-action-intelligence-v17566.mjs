import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const home=read('../src/pages/Home.jsx');
const panel=read('../src/components/intel/ActionIntelligencePanel.jsx');
const backend=read('../../backend/app/command_center.py');
const actions=read('../../backend/app/command_center_actions.py');
assert.ok(home.includes('<ActionIntelligencePanel model={data.action_intelligence}/>'));
for(const heading of ['1. Violation type','2. Geographical impact','3. Recommended action plan'])
  assert.ok(panel.includes(heading),heading);
assert.ok(panel.includes('Affected province(s): not established'));
assert.ok(panel.includes('No assignment created'));
assert.ok(panel.includes('Review source record'));
assert.ok(backend.includes('action_intelligence=build_action_intelligence('));
assert.ok(backend.includes('if not allowed(p,record):continue'));
assert.ok(actions.includes('"affected_provinces":[]'));
assert.ok(actions.includes('"officer_assigned":False'));
assert.ok(actions.includes('"generation_mode":"DETERMINISTIC_NO_PAID_AI"'));
console.log('Action Intelligence v175.66 static contracts passed');
