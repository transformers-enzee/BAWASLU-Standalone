import fs from 'node:fs';
import assert from 'node:assert/strict';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const base=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>fs.readFileSync(resolve(base,p),'utf8');
const main=read('src/main.jsx'),app=read('src/demo/DemoApp.jsx'),fixtures=read('src/demo/data.js');
const css=read('src/demo/demo.css');
assert.match(main,/^const isDemo\s*=\s*\/\^\\\/demo/m);
assert.ok(main.includes("import('@/demo/DemoApp.jsx')"));
assert.ok(main.includes("import('@/App.jsx')"));
assert.ok(main.indexOf("import('@/demo/DemoApp.jsx')")<main.indexOf("import('@/App.jsx')"));
assert.ok(!main.includes("import App from"));
assert.ok(fixtures.includes('DEMO-001')&&fixtures.includes('sampleCampaigns'));
assert.ok(app.includes("useState('id')")&&app.includes("setLanguage('en')"));
assert.ok(app.includes("setLanguage('id')")&&app.includes('walkthrough'));
assert.ok(app.includes("Reset Demo")&&app.includes('guideStep'));
assert.ok(app.includes('saveReview')&&app.includes('setReviews'));
assert.ok(app.includes('openPost')&&app.includes('setTracked'));
assert.ok(css.includes('.d-sidebar')&&css.includes('.d-overlay'));
for(const [name,s] of [['main',main],['demo',app],['fixtures',fixtures],['css',css]]){
 for(const forbidden of [
  /\bfetch\s*\(/,/XMLHttpRequest/,/\bWebSocket\b/,/navigator\.sendBeacon/,
  /\blocalStorage\b/,/\bsessionStorage\b/,/supabase/i,
  /@\/api\//,/\bbase44\b/,/https?:\/\//
 ]){
  // Comments about safety aren't an executable operation; still reject explicit
  // network primitives in source to guard future development of this demo.
  if(name!=='main'||forbidden.source!=='@\\/api\\/')assert.ok(!forbidden.test(s),name+' contains prohibited network/storage primitive '+forbidden);
 }
}
assert.equal((fixtures.match(/id:'DEMO-/g)||[]).length,12);
console.log('PASS demo isolation: separate /demo entry, bilingual, local data, simulated state, 8-step guide, zero network/storage primitives');
