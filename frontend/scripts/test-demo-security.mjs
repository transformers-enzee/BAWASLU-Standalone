import assert from 'node:assert/strict';
import fs from 'node:fs';
import {snapshot,demoAllEvidence,demoCampaigns,demoWatchlist} from '../src/demo/currentSnapshot.js';
const text=fs.readFileSync(new URL('../src/demo/realBridge.js',import.meta.url),'utf8');
const main=fs.readFileSync(new URL('../src/main.jsx',import.meta.url),'utf8');
const client=fs.readFileSync(new URL('../src/api/base44Client.js',import.meta.url),'utf8');
const built=fs.readFileSync(new URL('../public/demo/smart-radar.html',import.meta.url),'utf8');
assert.equal(snapshot.length,300);
assert.equal(demoAllEvidence.length,557);
assert.equal(demoCampaigns.length,5);
assert.equal(demoWatchlist.length,7);
assert.equal(new Set(snapshot.map(x=>x.id)).size,300);
assert.equal(new Set(snapshot.map(x=>x.sourceId)).size,295,'300 saved assessments link to 295 distinct sources');
assert.ok(snapshot.every(x=>String(x.id).startsWith('DEMO-')&&String(x.sourceId).startsWith('DEMO-SOURCE-')&&String(x.campaignId).startsWith('DEMO-CAMPAIGN-')));
assert.ok(snapshot.every(x=>/^Akun publik contoh |^Sumber berita contoh /.test(x.author)));
for(const p of snapshot){
 for(const value of [p.text,p.explanation]){
  assert.ok(!/https?:\/\/|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{15,17}\b/.test(value),'Sensitive source data not redacted: '+p.id);
 }
}
assert.ok(text.includes("['GET','HEAD'].includes(method)"),'Static non-GET requests must be blocked');
assert.ok(text.includes("XMLHttpRequest.prototype.open"),'XHR must be denied for APIs');
assert.ok(text.includes("navigator.sendBeacon=()=>false"));
assert.ok(client.includes("window.__BAWASLU_DEMO_REPLICA__ ? ''"),'Live access token must never be read in demo');
assert.ok(main.includes("connect-src 'self'"),'CSP must keep traffic on static host');
assert.ok(built.includes('bawaslu-demo-snapshot'));
assert.ok(!/supabase\.co/i.test(built),'No production Supabase URL in public Command Centre');
assert.ok(fs.readFileSync(new URL('../public/ui-freeze/bawaslu-interface-locale.js',import.meta.url),'utf8').includes('"LEVEL 3 · What officers have reviewed"'));
console.log('PASS isolated demo safeguards: sanitized records, no production identifiers, no network mutations, no live auth token');
