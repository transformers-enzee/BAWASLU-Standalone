import { useState } from 'react';
import { auditTitle, suggestionTypes as types } from './auditLabels';
import { useLanguage } from '@/lib/LanguageContext';

const nameKeys={original_content:'audit_field_source_text',publication_datetime:'audit_field_publication_date',original_language:'audit_field_original_language',author:'author',title:'headline',source_name:'audit_field_publisher'};
const fieldName=(k,t)=>t(nameKeys[k]||'')||k.replaceAll('_',' ');
const stamp=ev=>new Date(ev.occurred_at||ev.created_date).toLocaleString('en-GB',{timeZone:'Asia/Kuala_Lumpur'});
const short=(v,t)=>{const s=typeof v==='object'?JSON.stringify(v):String(v??t('not_recorded'));return s.length>140?s.slice(0,140)+'…':s};
const safeKey=k=>!(/(^|_)id$|^to$|^merged_into$|^duplicate_of$/.test(k));

function AuditEntry({ev,field,change,t}){
 const [open,setOpen]=useState(false),ai=!!field,source=ev.action==='SOURCE_RECOVERED',watch=ev.action==='WATCHLIST_MATCH_REVIEWED';
 const status=watch?(ev.changes?.decision?.new==='Link'?'Human Accepted':'Human Rejected'):change?.status;
 const title=auditTitle(ev,field,change,t);
 const proposed=watch?ev.changes?.name?.previous:change?.previous,final=watch?ev.changes?.name?.new:change?.new;
 const generic=Object.entries(ev.changes||{}).filter(([k])=>safeKey(k));
 const mismatch=ev.action==='GEOGRAPHIC_MISMATCH_REVIEWED';

 return <div className="pl-4 border-l-2 border-[#c7dbe2] pb-5 last:pb-0 space-y-1">
  <p className="text-sm font-semibold">{title}</p>
  <p className="text-xs text-[#8092a3]">{stamp(ev)} · {t('actor')}: {ev.actor_name||t('unknown')}{ev.source_record?' · '+ev.source_record:''}</p>

  {(ai||watch)?<>
   <p className="text-xs text-[#617789]">
    {t('decision_label')}: {status}
    {change?.prior_decision?' · '+t('changed_from')+' '+change.prior_decision:''}
    {status==='Human Rejected'&&(change?.reason||ev.changes?.reason?.new)?' · '+t('reason')+': '+(change?.reason||ev.changes?.reason?.new):''}
    {status!=='Human Rejected'&&final?' · '+t('final_value')+': '+short(final,t):''}
   </p>
   <button type="button" className="text-xs text-[#126d91]" onClick={()=>setOpen(!open)}>{open?t('hide_changes'):t('view_changes')}</button>
   {open&&<div className="rounded-lg bg-[#f7fafb] p-3 text-xs text-[#405669] space-y-2 break-words max-h-80 overflow-auto">
    <p>{t('suggestion_type')}: {types[field]||(watch?t('watchlist_match_label'):field)}</p>
    <p>{t('ai_proposed')}{typeof proposed==='string'&&proposed.endsWith('…')?' ('+t('historical_excerpt')+')':''}: <span className="whitespace-pre-wrap">{proposed??t('not_recorded')}</span></p>
    <p>{t('human_decision')}: {status?.replace('Human ','')||t('not_recorded')}{change?.prior_decision?' ('+t('changed_from')+' '+change.prior_decision+')':''}</p>
    {status==='Human Rejected'&&<p>{t('rejection_reason')}: {change?.reason||ev.changes?.reason?.new||t('not_recorded')}</p>}
    {(change?.confidence||ev.changes?.confidence?.new)&&<p>{t('ai_confidence')}: {change?.confidence||ev.changes?.confidence?.new}</p>}
    <p>{status==='Human Modified'?t('human_final'):t('final_value')}{typeof final==='string'&&final.endsWith('…')?' ('+t('historical_excerpt')+')':''}: {status==='Human Rejected'?t('not_recorded'):<span className="whitespace-pre-wrap">{final??t('not_recorded')}</span>}</p>
    <p>{t('actor')}: {ev.actor_name||t('unknown')} · {t('timestamp_label')}: {stamp(ev)}</p>
   </div>}
  </>:<>
   {mismatch&&<p className="text-xs text-[#617789]">{ev.changes?.decision?.new} · {t('reviewed_by')}: {ev.changes?.reviewer?.new} · {t('reason')}: {ev.changes?.reason?.new}</p>}
   {source&&<p className="text-xs text-[#617789]">{t('recovered_label')}: {generic.filter(([k])=>k!=='method').map(([k])=>fieldName(k,t)).join(' · ')}</p>}
   <button type="button" className="text-xs text-[#126d91]" onClick={()=>setOpen(!open)}>{open?t('hide_changes'):t('view_changes')}</button>
   {open&&<div className="rounded-lg bg-[#f7fafb] p-3 text-xs text-[#617789] space-y-2">{generic.map(([k,v])=><p key={k} className="break-words">{fieldName(k,t)}: {mismatch?<span className="whitespace-pre-wrap">{typeof v?.new==='object'?JSON.stringify(v.new):String(v?.new??t('not_recorded'))}</span>:k==='original_content'?t('recovered_label')+' ('+t('original_source')+')':short(v?.previous,t)+' → '+short(v?.new,t)}</p>)}</div>}
  </>}
 </div>;
}

export default function AuditTimeline({events}){
 const {t}=useLanguage();
 const rows=events.flatMap(ev=>ev.action==='AI_SUGGESTION_DECIDED'||ev.action==='AI_SUGGESTIONS_REVIEWED'
  ?Object.entries(ev.changes||{}).filter(([k])=>types[k]).map(([field,change])=>({ev,field,change,id:ev.id+'-'+field}))
  :[{ev,id:ev.id}]);
 return <section className="intel-card p-6"><h2 className="font-semibold text-lg mb-4">{t('activity_timeline')}</h2>{rows.map(row=><AuditEntry key={row.id} {...row} t={t}/>)}{!rows.length&&<p className="text-sm text-[#8293a4]">{t('no_activity_recorded')}</p>}</section>;
}
