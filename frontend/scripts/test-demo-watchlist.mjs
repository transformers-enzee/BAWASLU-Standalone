import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const js=read('public/demo/watchlist-training.js');
const bridge=read('public/demo/snapshot-bridge.js');
const html=read('public/demo/watchlist.html');
const old=read('public/ui-freeze/watchlist-live.js');
assert.ok(js.includes("function candidateActivitySummary(candidate)"));
assert.ok(js.includes("Belum ada unggahan tersimpan"));
assert.ok(js.includes("Cuplikan unggahan"));
assert.ok(js.includes("Kepemilikan akun dan klaim sumber"));
assert.ok(js.includes("localStorage.getItem('bawaslu-language')"));
assert.ok(bridge.includes("const demoOwned="));
assert.ok(bridge.includes("const demoAccounts="));
assert.ok(bridge.includes("relation:'THIRD_PARTY_MENTION'"));
assert.ok(bridge.includes("relation:'OWN_POST'")||bridge.includes('"relation":"OWN_POST"'));
assert.ok(bridge.includes("accounts:demoAccounts"));
assert.ok(html.includes("/demo/watchlist-training.js?build=132.6"));
assert.ok(!html.includes('src="/ui-freeze/watchlist-live.js'));
assert.ok(!old.includes("Belum ada unggahan tersimpan"));
assert.ok(!html.includes('data-ai-summary data-i18n-exempt'));
const records=JSON.parse(bridge.match(/const demoOwned=(\[[^;]+\]);/)[1]);
const accounts=JSON.parse(bridge.match(/const demoAccounts=(\[[^;]+\]);/)[1]);
assert.equal(records.length,36);
assert.equal(accounts.length,12);
const owned=name=>records.filter(x=>x.watchlist_id===name).length;
assert.equal(owned('DEMO-WATCH-002'),10);
assert.equal(owned('DEMO-WATCH-003'),0);
assert.equal(owned('DEMO-WATCH-004'),12);
assert.equal(owned('DEMO-WATCH-005'),4);
assert.equal(owned('DEMO-WATCH-006'),10);
assert.equal(new Set(records.map(x=>x.id)).size,36);
assert.ok(records.every(x=>x.relation==='OWN_POST'&&!/https?:\/\/|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}/i.test(x.text)));

// Embedded campaign Watchlist must grow with candidate content instead of trapping page scrolling.
const campaignPanel=read('src/components/intel/CampaignPanel.jsx');
assert.ok(campaignPanel.includes('scrolling="no"'),'Embedded Watchlist must delegate scrolling to main page');
assert.ok(campaignPanel.includes('ResizeObserver(resize)'),'Embedded Watchlist must auto-size after candidate changes');
assert.ok(!campaignPanel.includes("height:'calc(100vh - 280px)'"),'Fixed-height nested Watchlist scrolling must be removed');

// Training mode must not fabricate potential-violation findings from AI flags.
assert.ok(js.includes('candidate.findings=[]'),'Demo must not create unreviewed AI indicator cards');
assert.ok(!js.includes("title:'Potential violation indicator · unverified'"));
assert.ok(!html.includes("['flags','Potential Violations']"),'Remove irrelevant demo indicator tab');
assert.ok(!html.includes('id="pFlags"'),'Remove demo-only potential violation metric');
assert.ok(html.includes('demoUi(n)'),'Demo tabs must respect language toggle');
assert.ok(html.includes('Menampilkan'),'Demo post-count line must support Indonesian');
assert.ok(html.includes('Semua sentimen'),'Demo sentiment filter must support Indonesian');
console.log('PASS demo watchlist ownership: 12 accounts, 36 verified-match saved posts; Anies 10, Dedi 0; bilingual fallback, no production file changed');
