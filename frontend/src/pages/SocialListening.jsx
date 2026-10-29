import CampaignPanel from '@/components/intel/CampaignPanel';

/** V10 monitoring home. Campaign collection, saved evidence, paid preflight,
 * and assessment operations are provided by the existing authenticated panel.
 * Legacy standalone discovery/queue/rules UI has intentionally been retired.
 */
export default function SocialListening(){
 return <main className="mx-auto max-w-[1460px] space-y-5 text-[#1a2d46]">
  <header className="flex flex-wrap items-start justify-between gap-3">
   <div><p className="text-[11px] font-extrabold uppercase tracking-[.15em] text-[#6d8994]">Monitoring &amp; Collection</p>
   <h1 className="mt-1 text-[27px] font-bold tracking-tight text-[#152c47]">Social Listening</h1>
   <p className="text-sm text-[#60768c]">Discover broad conversations. Track selected candidates.</p></div>
  </header>
  <nav aria-label="Monitoring campaign workflow" className="flex flex-wrap items-center gap-2 text-xs text-[#708394]">
   {['Set up monitoring','Monitoring Home','Campaign Dashboard'].map((name,i)=><span key={name} className="inline-flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-full bg-[#e2f4ee] font-semibold text-[#087564]">{i+1}</span>{name}{i<2&&<span className="ml-1 text-[#a0b1bb]">→</span>}</span>)}
  </nav>
  <CampaignPanel/>
 </main>;
}
