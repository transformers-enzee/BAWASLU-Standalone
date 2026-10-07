import { useEffect, useState } from 'react';
import { registry } from '@/components/intel/useIntel';
export default function UserAccessHistory({userId}){
 const [events,setEvents]=useState([]),[loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;registry('accessHistory',{},userId).then(r=>{if(active)setEvents(r.events||[])}).finally(()=>{if(active)setLoading(false)});return ()=>{active=false}},[userId]);
 return <section className="border-t border-border pt-4"><h3 className="text-sm font-semibold">Access history</h3>
  {loading?<p className="text-xs text-muted-foreground mt-2">Loading history...</p>:events.length?events.map(ev=><div key={ev.id} className="text-xs border-b border-border py-2"><strong>{ev.action.replaceAll('_',' ')}</strong><span className="text-muted-foreground"> · {ev.actor_name} · {new Date(ev.occurred_at||ev.created_date).toLocaleString('en-GB')}</span>{ev.action==='USER_ACCESS_UPDATED'&&<p className="mt-1 text-muted-foreground">{ev.changes?.assignment?.previous?.access_role||'Unassigned'} → {ev.changes?.assignment?.new?.access_role||'Unassigned'} · {ev.changes?.assignment?.new?.province||'Nationwide'}{ev.changes?.assignment?.new?.regency_city?` / ${ev.changes.assignment.new.regency_city}`:' / All Regency/Cities'} · {ev.changes?.assignment?.new?.status}</p>}</div>):<p className="text-xs text-muted-foreground mt-2">No access changes recorded.</p>}
 </section>;
}