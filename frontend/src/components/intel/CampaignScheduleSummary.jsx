import { useEffect, useState } from 'react';
import { base44 } from '@/api/base44Client';

export default function CampaignScheduleSummary({campaign}){
 const [schedule,setSchedule]=useState(null),[history,setHistory]=useState([]);
 const [busy,setBusy]=useState(true),[error,setError]=useState('');
 useEffect(()=>{
  let active=true;
  setBusy(true);setSchedule(null);setHistory([]);setError('');
  Promise.all([
   base44.functions.invoke('socialListening',{action:'campaignSchedulePreview',id:campaign.id,data:{}}),
   base44.functions.invoke('socialListening',{action:'campaignHistory',id:campaign.id,data:{}})
  ]).then(([s,h])=>{
   if(!active)return;
   setSchedule(s.data.schedule);setHistory(h.data.history||[]);
  }).catch(e=>{
   if(active)setError(e.response?.data?.detail||e.response?.data?.error||e.message);
  }).finally(()=>{if(active)setBusy(false)});
  return ()=>{active=false};
 },[campaign.id]);
 if(busy)return <p className="text-xs text-[#77899b]">Checking campaign schedule…</p>;
 if(error)return <p role="alert" className="text-xs text-red-700">{error}</p>;
 if(!schedule)return null;
 return <div className="space-y-2 border-t border-slate-200 pt-3" aria-label="Campaign schedule and crawl history">
   <h4 className="font-semibold text-sm">Collection schedule</h4>
   <div className="grid sm:grid-cols-2 gap-2 text-xs">
     <div>Last successful crawl: <strong>{schedule.last_crawled_at||'Never'}</strong></div>
     <div>Next crawl: <strong>{schedule.next_crawl_at||'Not scheduled'}</strong></div>
     <div>Estimated credits per run: <strong>{schedule.estimated_credits_per_run}</strong></div>
     <div>Credits used (24 hours, all SocialCrawl usage): <strong>{schedule.credits_used_last_24h}</strong></div>
   </div>
   <p className="text-xs text-amber-800 font-semibold">Automatic paid crawling disabled pending explicit approval.</p>
   {schedule.blocked_reasons?.length>0&&<p className="text-xs text-[#77899b]">{schedule.blocked_reasons.join(' · ')}</p>}
   <h4 className="font-semibold text-sm mt-3">Collection history</h4>
   {history.length? <ul className="space-y-1 text-xs">{history.map(run=><li key={run.id}>
      {run.executed_at} · {run.status} · {run.result_count} new records · {run.credits_used} credits
      {run.error&&<span className="text-red-700"> — {run.error}</span>}
   </li>)}</ul>:<p className="text-xs text-[#77899b]">No collection runs recorded for this campaign.</p>}
 </div>
}
