import { useEffect, useMemo, useState } from 'react';
import { base44 } from '@/api/base44Client';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { PRIORITIES, Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

function SocialEvidenceInbox(){
 const [items,setItems]=useState([]),[status,setStatus]=useState('DISCOVERED'),[busy,setBusy]=useState(''),[notice,setNotice]=useState(''),[error,setError]=useState(''),[notes,setNotes]=useState({});
 async function refresh(next=status){
  setError('');
  try{const response=await base44.functions.invoke('socialListening',{action:'queue',data:{state:next}});setItems(response.data.results||[])}
  catch(e){setError(e.response?.data?.detail||e.message||'Unable to load social evidence')}
 }
 useEffect(()=>{refresh(status)},[status]);
 async function decide(item,decision){
  setBusy(item.id);setNotice('');setError('');
  try{
   await base44.functions.invoke('socialListening',{action:'review',id:item.id,data:{decision,notes:notes[item.id]||''}});
   setNotice('Review decision saved. Intelligence promotion remains a separate human action.');await refresh();
  }catch(e){setError(e.response?.data?.detail||e.message||'Review failed')}
  finally{setBusy('')}
 }
 async function promote(item){
  if(!window.confirm('Create an intelligence record from this human-reviewed social evidence?'))return;
  setBusy(item.id);setNotice('');setError('');
  try{await base44.functions.invoke('socialListening',{action:'promote',id:item.id,data:{}});setNotice('Evidence promoted to Intelligence Inbox. Refresh the intelligence list to view it.');await refresh()}
  catch(e){setError(e.response?.data?.detail||e.message||'Promotion failed')}
  finally{setBusy('')}
 }
 return <section className="intel-card p-5 space-y-3" aria-label="Social evidence review queue">
  <div><h2 className="font-semibold text-lg">Social Listening evidence review</h2><p className="text-xs text-slate-500">Source evidence is not validated intelligence. Review each post before promoting it; no automatic promotion or paid crawl.</p></div>
  <div className="flex flex-wrap gap-2">{[['DISCOVERED','New evidence'],['RELEVANT','Relevant'],['MONITOR','Monitor'],['NOT_RELEVANT','Not relevant'],['PROMOTED','Promoted']].map(([key,label])=><button type="button" key={key} onClick={()=>setStatus(key)} className={status===key?'intel-button':'intel-ghost'}>{label}</button>)}</div>
  {error&&<p className="text-sm text-red-600" role="alert">{error}</p>}{notice&&<p className="text-sm text-teal-700" role="status">{notice}</p>}
  <div className="max-h-80 overflow-y-auto space-y-2">{items.slice(0,30).map(item=><div key={item.id} className="rounded-lg border p-3 space-y-2 text-sm">
   <div className="flex justify-between gap-2"><strong className="capitalize">{item.platform||'Social'} · {item.author_name||'Unknown source'}</strong><span className="text-xs text-slate-500">{item.review_state}</span></div>
   <p className="line-clamp-3 whitespace-pre-wrap">{item.text_content||'No source text'}</p>
   {item.canonical_url&&<a href={item.canonical_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-700 underline">View original source</a>}
   {item.review_state!=='PROMOTED'&&<><textarea className="intel-input w-full" rows={2} placeholder="Reviewer notes (required when not relevant)" value={notes[item.id]||''} onChange={e=>setNotes(v=>({...v,[item.id]:e.target.value}))}/>
   <div className="flex flex-wrap gap-2">{['RELEVANT','MONITOR','NOT_RELEVANT'].map(decision=><button type="button" key={decision} className="intel-ghost text-xs" disabled={!!busy} onClick={()=>decide(item,decision)}>{decision.replaceAll('_',' ')}</button>)}
   {['RELEVANT','MONITOR'].includes(item.review_state)&&<button type="button" className="intel-button text-xs" disabled={!!busy} onClick={()=>promote(item)}>Promote to Intelligence</button>}</div></>}
  </div>)}{items.length===0&&!error&&<p className="text-sm text-slate-500">No evidence in this review state.</p>}</div>
  <p className="text-xs text-slate-500">Showing up to 30 records from the authorized Social Listening review queue. Promotions require explicit confirmation.</p>
 </section>
}
const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const triagePending=x=>{const t=x.triage_review||x.triage_review_status||{};const state=typeof t==='string'?t:t.state;const generated=typeof t==='object'?t.generated:!!state;return generated&&state&&state!=='REVIEW COMPLETE';};

function initialFilters(){const q=new URLSearchParams(window.location.search),f={};for(const key of ['entity','verification_status','review_status','priority','province','regency_city','platform','evidence_type','reviewer','source_type','supervision_signal','date','search']){const value=q.get(key);if(value)f[key]=value}if(q.get('view'))f.view=q.get('view');return f}

export default function Inbox(){
 const {t,label}=useLanguage();
 const {items,loading,error}=useIntel(),{items:entities}=useRegistry();
 const [f,setF]=useState(initialFilters),[sort,setSort]=useState('updated-desc');
 const pick=(key,value)=>setF(v=>({...v,[key]:value}));
 const unique=key=>[...new Set(items.flatMap(x=>['province','regency_city'].includes(key)?(x.geographic_assignments||[]).map(a=>a[key]).filter(Boolean):[x[key]]).filter(Boolean))].sort();
 const options={province:unique('province'),regency_city:unique('regency_city'),entity:entities.map(x=>x.name),platform:unique('platform'),evidence_type:['OBSERVED','INFERRED'],verification_status:['UNVERIFIED','HUMAN_VERIFIED'],supervision_signal:['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'],priority:PRIORITIES,reviewer:unique('assigned_reviewer'),review_status:unique('review_status'),source_type:unique('source_type')};
 const quickViews=[['',t('all_intelligence')],['pending-review',t('pending_review')],['validated',t('validated')],['unverified',t('unverified')],['jurisdiction-unresolved',t('jurisdiction_unresolved')],['triage-pending',t('ai_triage_waiting')]];
 const labelForKey={search:t('filter_search'),date:t('filter_date'),entity:t('filter_entity'),verification_status:t('filter_verification'),review_status:t('filter_review_status'),priority:t('filter_priority'),province:t('filter_province'),regency_city:t('filter_regency_city'),platform:t('filter_platform'),evidence_type:t('filter_evidence_type'),reviewer:t('filter_reviewer'),source_type:t('filter_source_type'),supervision_signal:t('filter_supervision_signal')};
 const filtered=useMemo(()=>items.filter(x=>{const text=(x.intelligence_id+' '+x.title+' '+x.original_content+' '+(x.related_entities||[]).join(' ')+' '+x.province+' '+x.regency_city+' '+(x.geographic_assignments||[]).map(a=>a.province+' '+a.regency_city).join(' ')).toLowerCase();const specialOk=!f.view||(f.view==='pending-review'&&pendingReview(x))||(f.view==='validated'&&validated(x))||(f.view==='unverified'&&(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED')||(f.view==='jurisdiction-unresolved'&&x.jurisdiction_confirmed!==true)||(f.view==='triage-pending'&&triagePending(x));return specialOk&&(!f.search||text.includes(f.search.toLowerCase()))&&(!f.date||x.created_date?.slice(0,10)===f.date)&&Object.keys(options).every(k=>!f[k]||(k==='entity'?x.related_entities?.includes(f[k]):k==='reviewer'?x.assigned_reviewer===f[k]:k==='supervision_signal'?x.supervision_screening?.supervision_signal===f[k]:k==='evidence_type'?(x.evidence_type||(['OBSERVED','INFERRED'].includes(x.evidence_state)?x.evidence_state:''))===f[k]:k==='verification_status'?(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))===f[k]:['province','regency_city'].includes(k)?(x.geographic_assignments||[]).some(a=>a[k]===f[k]):x[k]===f[k]))}),[items,f]);
 const sorted=useMemo(()=>[...filtered].sort((a,b)=>{if(sort==='updated-desc')return new Date(b.updated_date||b.created_date||0)-new Date(a.updated_date||a.created_date||0);if(sort==='created-desc')return new Date(b.created_date||0)-new Date(a.created_date||0);if(sort==='created-asc')return new Date(a.created_date||0)-new Date(b.created_date||0);if(sort==='priority'){const rank={Critical:4,High:3,Medium:2,Low:1};return(rank[b.priority]||0)-(rank[a.priority]||0)}if(sort==='id')return String(a.intelligence_id||'').localeCompare(String(b.intelligence_id||''));return 0}),[filtered,sort]);
 const counts=useMemo(()=>({'':items.length,'pending-review':items.filter(pendingReview).length,validated:items.filter(validated).length,unverified:items.filter(x=>(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED').length,'jurisdiction-unresolved':items.filter(x=>x.jurisdiction_confirmed!==true).length,'triage-pending':items.filter(triagePending).length}),[items]);
 const needsAction=useMemo(()=>items.filter(x=>x.jurisdiction_confirmed!==true||(x.geographic_mismatch?.status||x.geographic_mismatch_review?.status)==='pending'||triagePending(x)||pendingReview(x)).length,[items]);
 const activeFilters=Object.entries(f).filter(([k,v])=>k!=='view'&&v),clearOne=key=>setF(v=>({...v,[key]:''})),currentView=quickViews.find(([value])=>value===(f.view||''))?.[1]||t('all_intelligence');
 const recordScope=items.length===1?t('record_authorized_scope'):t('records_authorized_scope');
 return <div className="space-y-6"><div><p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('collection_triage')}</p><h1 className="intel-heading">{t('intelligence_inbox')}</h1><p className="text-sm text-[#77899b] mt-2">{t('inbox_workspace')} · {currentView} · {sorted.length} {t(sorted.length===1?'result':'results')} · {items.length} {recordScope}</p></div><Notice error={error}/>
 <SocialEvidenceInbox/>
 <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3"><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_needs_action')}</p><p className="text-2xl font-semibold mt-1">{needsAction}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_pending_review')}</p><p className="text-2xl font-semibold mt-1">{counts['pending-review']}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_unresolved_jurisdiction')}</p><p className="text-2xl font-semibold mt-1">{counts['jurisdiction-unresolved']}</p></div><div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('inbox_triage_pending')}</p><p className="text-2xl font-semibold mt-1">{counts['triage-pending']}</p></div></div><p className="text-xs text-[#8192a3]">{t('inbox_summary_note')}</p>
 <div className="intel-card p-4"><div className="flex flex-wrap gap-2">{quickViews.map(([value,text])=><button key={value||'all'} type="button" className={(f.view||'')===value?'intel-button':'intel-ghost'} onClick={()=>pick('view',value)}>{text} <span className="opacity-70">({counts[value]||0})</span></button>)}</div></div>
 <div className="intel-card p-5 space-y-4"><div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3"><input className="intel-input sm:col-span-2" placeholder={t('search_placeholder')} aria-label={t('filter_search')} value={f.search||''} onChange={e=>pick('search',e.target.value)}/><input className="intel-input" type="date" aria-label={t('filter_date')} value={f.date||''} onChange={e=>pick('date',e.target.value)}/>
 {Object.entries(options).map(([key,values])=><select key={key} className="intel-input" aria-label={labelForKey[key]} value={f[key]||''} onChange={e=>pick(key,e.target.value)}><option value="">{t('all_prefix')} {labelForKey[key].toLowerCase()}</option>{values.map(v=><option key={v} value={v}>{label(v)}</option>)}</select>)}
 <select className="intel-input" aria-label={t('sort_intelligence_aria')} value={sort} onChange={e=>setSort(e.target.value)}><option value="updated-desc">{t('sort_recently_updated')}</option><option value="created-desc">{t('sort_newest_created')}</option><option value="created-asc">{t('sort_oldest_created')}</option><option value="priority">{t('sort_highest_priority')}</option><option value="id">{t('sort_intelligence_id')}</option></select></div>
 {(activeFilters.length>0||f.view)&&<div className="flex flex-wrap items-center gap-2">{f.view&&<span className="rounded-full bg-[#eaf4f7] px-3 py-1 text-xs font-semibold text-[#176e8e]">{t('view')}: {currentView}</span>}{activeFilters.map(([key,value])=><button key={key} type="button" onClick={()=>clearOne(key)} className="rounded-full bg-[#f5f7f9] px-3 py-1 text-xs text-[#536d80] hover:bg-[#edf2f5]">{labelForKey[key]||key}: {label(value)} ×</button>)}<button className="text-xs font-semibold text-[#126b8b]" onClick={()=>setF({})}>{t('clear_all_filters')}</button></div>}</div>
 {new URLSearchParams(window.location.search).get('jurisdiction')==='pending'&&<p role="status" className="text-sm">{t('submitted_jurisdiction')}</p>}
 {loading?<p className="text-sm text-[#77899b]">{t('loading_intelligence')}</p>:error?null:<IntelligenceTable items={sorted}/>}</div>;
}