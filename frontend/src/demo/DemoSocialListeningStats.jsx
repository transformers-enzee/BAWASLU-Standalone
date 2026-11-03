import {useLanguage} from '@/lib/LanguageContext';
import {demoCampaigns,demoWatchlist} from './currentSnapshot.js';

// Demo-only fixed source of truth: exactly the two instructor-approved campaigns.
// The full frozen evidence is retained for Intelligence Inbox and Command Centre.
const visibleIds=new Set(['DEMO-CAMPAIGN-01','DEMO-CAMPAIGN-04']);
const shown=demoCampaigns.filter(c=>visibleIds.has(c.id));
const totals=Object.freeze({
 campaigns:shown.length,
 posts:shown.reduce((sum,c)=>sum+Number(c.captured_count||0),0),
 platforms:new Set(shown.flatMap(c=>c.platforms||[])).size,
 candidates:demoWatchlist.filter(c=>c.type==='Candidate'&&c.status==='Active').length
});
export const DEMO_SOCIAL_LISTENING_COUNTS=totals;

export default function DemoSocialListeningStats(){
 const {language}=useLanguage(),id=language==='id';
 const cards=[
  [totals.campaigns,id?'Kampanye pemantauan':'Monitoring campaigns'],
  [totals.posts,id?'Unggahan sumber terkait kampanye':'Campaign-linked source posts'],
  [totals.platforms,id?'Platform sumber terkonfigurasi':'Configured source platforms'],
  [totals.candidates,id?'Kandidat yang aktif dipantau':'Actively tracked candidates']
 ];
 return <div data-demo-locale-owned="true" data-i18n-exempt="true" data-demo-social-stats="true" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
  {cards.map(([value,label])=><div key={label} className="rounded-xl border border-[#dce5ed] bg-white px-4 py-5">
   <strong className="block text-[26px] font-bold tabular-nums text-[#152c47]">{value.toLocaleString('id-ID')}</strong>
   <span className="text-[11px] text-[#60768c]">{label}</span>
  </div>)}
 </div>;
}
