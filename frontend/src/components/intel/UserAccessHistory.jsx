import { useEffect, useState } from 'react';
import { registry } from '@/components/intel/useIntel';
import { useLanguage } from '@/lib/LanguageContext';
export default function UserAccessHistory({userId}){
 const {t,label}=useLanguage();
 const [events,setEvents]=useState([]),[loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;registry('accessHistory',{},userId).then(r=>{if(active)setEvents(r.events||[])}).finally(()=>{if(active)setLoading(false)});return ()=>{active=false}},[userId]);
 return <section className="border-t border-border pt-4"><h3 className="text-sm font-semibold">{t('access_history')}</h3>
  {loading?<p className="text-xs text-muted-foreground mt-2">{t('loading_history')}</p>:events.length?events.map(ev=><div key={ev.id} className="text-xs border-b border-border py-2"><strong>{ev.action.replaceAll('_',' ')}</strong><span className="text-muted-foreground"> · {ev.actor_name} · {new Date(ev.occurred_at||ev.created_date).toLocaleString('en-GB')}</span>{ev.action==='USER_ACCESS_UPDATED'&&<p className="mt-1 text-muted-foreground">{ev.changes?.assignment?.previous?.access_role||t('unassigned')} → {ev.changes?.assignment?.new?.access_role||'Unassigned'} · {ev.changes?.assignment?.new?.province||t('nationwide')}{ev.changes?.assignment?.new?.regency_city?` / ${ev.changes.assignment.new.regency_city}`' / '+t('all_regencies_cities')} · {label(ev.changes?.assignment?.new?.status)}</p>}</div>):<p className="text-xs text-muted-foreground mt-2">{t('no_access_changes')}</p>}
 </section>;
}