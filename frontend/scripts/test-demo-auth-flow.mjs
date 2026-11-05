import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const main=read('src/main.jsx'),bridge=read('src/demo/realBridge.js');
const shell=read('src/components/intel/Shell.jsx'),app=read('src/App.jsx');
const widget=read('src/demo/DemoFeedbackWidget.jsx'),admin=read('src/pages/Administration.jsx');
// Public training route must open immediately, without collecting credentials.
assert.ok(main.includes('  openDemo();'));
assert.ok(!main.includes("import('@/demo/DemoTrainingLogin.jsx')"));
assert.ok(!main.includes('bawaslu_demo_training_session'));
assert.ok(main.includes("import('@/demo/realBridge.js')"));
assert.ok(shell.includes('<DemoFeedbackWidget/>'),'Every demo page exposes the feedback form');
assert.ok(!shell.includes("sessionStorage.removeItem('bawaslu_demo_training_session')"));
assert.ok(bridge.includes("DEMO_VISIBLE_CAMPAIGN_IDS=new Set(['DEMO-CAMPAIGN-01','DEMO-CAMPAIGN-04'])"));
assert.ok(app.includes("!['DEMO-CAMPAIGN-01','DEMO-CAMPAIGN-04'].includes(id)"));
assert.ok(widget.includes("'/api/demo-feedback'"));
assert.ok(widget.includes('Berikan Masukan')&&widget.includes('Kirim Masukan'));
assert.ok(admin.includes('<DemoFeedbackAdmin/>'),'Actual admin sees aggregated feedback');
console.log('PASS public no-login demo, bilingual feedback form, national-admin dashboard, preserved snapshot isolation');
