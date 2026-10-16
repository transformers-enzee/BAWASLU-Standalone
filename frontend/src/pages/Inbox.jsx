import { useMemo, useState } from 'react';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import { Link } from 'react-router-dom';
import Status from '@/components/intel/Status';
import { X, ChevronRight, Sparkles } from 'lucide-react';
import { PRIORITIES, Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const triagePending=x=>{const t=x.triage_review||x.triage_review_status||{};const state=typeof t==='string'?t:t.state;const generated=typeof t==='object'?t.generated:!!state;return generated&&state&&state!=='REVIEW COMPLETE';};

function initialFilters(){const q=new URLSearchParams(window.location.search),f={};for(const key of ['entity','verification_status','review_status','priority','province','regency_city','platform','evidence_type','reviewer','source_type','supervision_signal','date','search']){const value=q.get(key);if(value)f[key]=value}if(q.get('view'))f.view=q.get('view');return f}

export default function Inbox(){
 const {t,label}=useLanguage();
 const {items,loading,error}=useIntel(),{items:entities}=useRegistry();
 const [f,setF]=useState(initialFilters),[sort,setSort]=useState('updated-desc'),[showAdvanced,setShowAdvanced]=useState(false),[selected,setSelected]=useState(null),[detailTab,setDetailTab]=useState('post');
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
 const signal=x=>String(x.supervision_screening?.supervision_signal||'').toUpperCase();
 const potential=x=>signal(x)==='POTENTIAL REGULATORY ISSUE';
 const relevant=x=>validated(x)||pendingReview(x)||Boolean(x.supervision_screening?.supervision_signal&&signal(x)!=='NO SIGNAL IDENTIFIED');
 const locationMatched=x=>x.jurisdiction_confirmed===true||(x.geographic_assignments||[]).length>0;
 const candidateMatched=x=>(x.related_entities||[]).length>0;
 const viewMatch=(x,view)=>view==='relevant'?relevant(x):view==='location'?locationMatched(x):view==='candidate'?candidateMatched(x):view==='potential'?potential(x):true;
 const visible=sorted.filter(x=>viewMatch(x,f.inboxView));
 const potentialCount=visible.filter(potential).length;
 const breakdown=[{name:'Potential signal',count:potentialCount,color:'#c18b41'},{name:'Other records',count:visible.length-potentialCount,color:'#dce7ec'}];
 const sourceName=x=>x.observed_publisher_handle||x.source_name||x.source_type||x.platform||'—';
 const openRecord=x=>{setSelected(x);setDetailTab('post')};
 const chooseView=value=>setF(v=>({...v,inboxView:value}));
 const insightsSummary=visible.length===0?'No records match the current filters.':potentialCount>0?`${potentialCount} of ${visible.length} visible records have a potential regulatory issue signal. Human review is required before drawing conclusions.`:`No potential regulatory issue signals in the ${visible.length} visible records. This is not a verification of compliance.`;
 return <div className="space-y-3">
  <div className="flex flex-wrap items-end justify-between gap-2"><div><p className="text-[11px] uppercase tracking-[.13em] font-bold text-[#9a7e49]">{t('collection_triage')}</p><h1 className="intel-heading">{t('intelligence_inbox')}</h1></div><span className="text-xs text-[#728699]">{items.length} {recordScope}</span></div>
  <Notice error={error}/>
  <div className="grid grid-cols-2 md:grid-cols-[minmax(105px,1fr)_minmax(105px,1fr)_minmax(0,3fr)] gap-2">
   <div className="intel-card px-3 py-2"><p className="text-xs text-[#718598]">Posts shown</p><p className="text-2xl font-semibold tabular-nums">{visible.length}</p></div>
   <div className="intel-card px-3 py-2"><p className="text-xs text-[#718598]">Potential violations <span title="Unverified potential regulatory issue signals, not confirmed violations">ⓘ</span></p><p className="text-2xl font-semibold text-[#9e6e2d] tabular-nums">{potentialCount}</p></div>
   <div className="intel-card col-span-2 md:col-span-1 px-3 py-2 min-w-0"><p className="text-xs font-semibold text-[#536d80] flex items-center gap-1"><Sparkles size={13}/> Analysis summary</p><p className="text-xs text-[#60798b] mt-1 line-clamp-2" title={insightsSummary}>{insightsSummary}</p><p className="text-[10px] text-[#8799a6] mt-1">Derived from record signals · not a generated AI conclusion</p></div>
  </div>
  <div className="intel-card p-3 space-y-2">
   <div className="flex flex-wrap gap-1.5" role="group" aria-label="Post categories">
    {[['','All'],['relevant','Relevant'],['location','Location'],['candidate','Candidate'],['potential','Potential Violation']].map(([value,text])=><button type="button" key={value} aria-pressed={(f.inboxView||'')===value} onClick={()=>chooseView(value)} className={`rounded-full text-xs px-3 py-1.5 font-semibold ${(f.inboxView||'')===value?'bg-[#176e8e] text-white':'bg-[#f1f5f7] text-[#536d80] hover:bg-[#e5edf1]'}`}>{text}</button>)}
   </div>
   <div className="flex flex-wrap gap-2 items-center">
    <input className="intel-input min-w-[180px] flex-[2] !py-2" placeholder={t('search_placeholder')} aria-label={t('filter_search')} value={f.search||''} onChange={e=>pick('search',e.target.value)}/>
    <select className="intel-input flex-1 min-w-[150px] !py-2" aria-label={t('sort_intelligence_aria')} value={sort} onChange={e=>setSort(e.target.value)}><option value="updated-desc">{t('sort_recently_updated')}</option><option value="created-desc">{t('sort_newest_created')}</option><option value="created-asc">{t('sort_oldest_created')}</option><option value="priority">{t('sort_highest_priority')}</option><option value="id">{t('sort_intelligence_id')}</option></select>
    <button type="button" className="intel-ghost !py-2 text-xs" aria-expanded={showAdvanced} aria-controls="inbox-advanced-filters" onClick={()=>setShowAdvanced(v=>!v)}>{showAdvanced?'Hide filters':'More filters'} {activeFilters.length>0?`(${activeFilters.length})`:''}</button>
   </div>
   {showAdvanced&&<div id="inbox-advanced-filters" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-2 border-t border-[#e8edf0]">
    <input className="intel-input" type="date" aria-label={t('filter_date')} value={f.date||''} onChange={e=>pick('date',e.target.value)}/>
    {Object.entries(options).map(([key,values])=><select key={key} className="intel-input" aria-label={labelForKey[key]} value={f[key]||''} onChange={e=>pick(key,e.target.value)}><option value="">{t('all_prefix')} {labelForKey[key].toLowerCase()}</option>{values.map(v=><option key={v} value={v}>{label(v)}</option>)}</select>)}
    <select className="intel-input" aria-label={t('view')} value={f.view||''} onChange={e=>pick('view',e.target.value)}>{quickViews.map(([value,text])=><option key={value} value={value}>{text} ({counts[value]||0})</option>)}</select>
   </div>}
   {activeFilters.length>0&&<div className="flex flex-wrap gap-1.5 items-center">{activeFilters.filter(([key])=>key!=='inboxView').map(([key,value])=><button type="button" key={key} onClick={()=>clearOne(key)} className="rounded-full bg-[#f5f7f9] px-2.5 py-1 text-xs text-[#536d80]">{labelForKey[key]||key}: {label(value)} ×</button>)}<button type="button" className="text-xs text-[#146a8b]" onClick={()=>setF({})}>{t('clear_all_filters')}</button></div>}
  </div>
  {new URLSearchParams(window.location.search).get('jurisdiction')==='pending'&&<p role="status" className="text-sm">{t('submitted_jurisdiction')}</p>}
  <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,4fr)_minmax(185px,1fr)] items-start gap-3">
   <section aria-label="Intelligence posts" className="min-w-0 space-y-2">
    {loading?<p className="text-sm text-[#77899b]">{t('loading_intelligence')}</p>:error?null:visible.length===0?<div className="intel-card p-8 text-center text-sm text-[#73869a]">{t('no_match_current_filters')}</div>:visible.map(x=><article key={x.id} className="intel-card p-3 md:p-4 hover:border-[#b8d1db] transition-colors">
     <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap gap-1.5 items-center"><span className="text-[11px] font-semibold text-[#146a8b]">{x.intelligence_id}</span>{potential(x)&&<span className="rounded bg-[#fff4df] px-2 py-0.5 text-[10px] font-semibold text-[#956524]">Potential signal · unverified</span>}<Status value={x.review_status}/></div>
      <span className="text-[11px] text-[#8192a2]">{x.updated_date||x.created_date?new Date(x.updated_date||x.created_date).toLocaleDateString('en-GB'):''}</span>
     </div>
     <button type="button" onClick={()=>openRecord(x)} className="mt-2 text-left font-semibold text-[#223e51] hover:text-[#146a8b] line-clamp-2 w-full">{x.title||t('untitled_intelligence')}</button>
     <p className="mt-1 text-xs text-[#536d80] line-clamp-2 whitespace-pre-line">{x.original_content||x.english_translation||x.analyst_notes||'No post excerpt available'}</p>
     <div className="flex flex-wrap items-center justify-between gap-2 mt-2 border-t border-[#edf1f5] pt-2">
      <p className="text-[11px] text-[#73889a]">{sourceName(x)} · {x.platform||x.source_type||'—'} · {x.jurisdiction_confirmed===true?((x.geographic_assignments||[]).map(a=>a.regency_city||a.province).filter(Boolean).join(', ')||t('national')):t('jurisdiction_unresolved_short')}</p>
      <button type="button" onClick={()=>openRecord(x)} className="inline-flex items-center gap-1 text-xs font-semibold text-[#146a8b]">Preview <ChevronRight size={14}/></button>
     </div>
    </article>)}
   </section>
   <aside className="intel-card p-3 xl:sticky xl:top-4" aria-label="Post distribution">
    <h2 className="text-xs font-semibold text-[#435a6e]">Post distribution</h2>
    <p className="text-[11px] text-[#8192a3] mt-1">Current filtered results</p>
    <div className="flex justify-center py-3"><div role="img" aria-label={`${potentialCount} potential regulatory issue signals among ${visible.length} posts`} className="rounded-full w-24 h-24 grid place-items-center" style={{background:visible.length?`conic-gradient(#c18b41 0 ${potentialCount/visible.length*100}%, #dce7ec ${potentialCount/visible.length*100}% 100%)`:'#dce7ec'}}><div className="rounded-full w-[68px] h-[68px] bg-white flex flex-col items-center justify-center"><strong className="text-xl text-[#365269]">{visible.length}</strong><span className="text-[9px] text-[#8192a3]">posts</span></div></div></div>
    {breakdown.map(b=><div key={b.name} className="flex items-center justify-between gap-2 text-[11px] my-1"><span className="flex gap-1.5 items-center text-[#64798b]"><span className="w-2 h-2 rounded-full" style={{backgroundColor:b.color}}/>{b.name}</span><strong className="tabular-nums">{b.count}</strong></div>)}
    <p className="mt-3 text-[10px] text-[#8192a3]">Signals are not confirmed violations.</p>
   </aside>
  </div>
  {selected&&<div className="fixed inset-0 z-50 flex justify-end" role="presentation">
   <button type="button" className="absolute inset-0 bg-[#102b40]/40" aria-label="Close post preview" onClick={()=>setSelected(null)}/>
   <section role="dialog" aria-modal="true" aria-label="Intelligence post preview" className="relative z-10 bg-white w-full max-w-xl h-full shadow-2xl flex flex-col" onKeyDown={e=>{if(e.key==='Escape')setSelected(null)}}>
    <div className="p-4 border-b flex items-center justify-between gap-3"><div className="min-w-0"><p className="text-[11px] text-[#8192a3]">{selected.intelligence_id}</p><h2 className="font-semibold text-[#223e51] line-clamp-2">{selected.title||t('untitled_intelligence')}</h2></div><button type="button" autoFocus aria-label="Close preview" onClick={()=>setSelected(null)} className="p-2 rounded hover:bg-[#f1f5f7]"><X size={20}/></button></div>
    <div className="flex gap-2 p-3 border-b">{[['post','Original post'],['analysis','AI analysis'],['review','Human review']].map(([value,text])=><button key={value} type="button" onClick={()=>setDetailTab(value)} aria-pressed={detailTab===value} className={`text-xs font-semibold rounded px-3 py-2 ${detailTab===value?'bg-[#176e8e] text-white':'bg-[#f1f5f7] text-[#536d80]'}`}>{text}</button>)}</div>
    <div className="flex-1 overflow-y-auto p-4 space-y-3 text-sm text-[#425c70]">
     {detailTab==='post'?<><p className="text-xs text-[#73889a]">{sourceName(selected)} · {selected.platform||selected.source_type||'—'}</p><div className="whitespace-pre-wrap break-words">{selected.original_content||'Original post text is not available in this record.'}</div>{selected.original_url&&<a href={selected.original_url} target="_blank" rel="noopener noreferrer" className="text-[#146a8b] underline">Open original source ↗</a>}</>:detailTab==='analysis'?<><p className="text-xs font-semibold">AI suggestions · requires human confirmation</p><p>{selected.ai_suggestions?.summary||selected.ai_suggestions?.what_happened||selected.analyst_notes||'No AI analysis is available for this record.'}</p><p className="text-xs">Supervision signal: {selected.supervision_screening?.supervision_signal||'Not assessed'}</p></>:<><p>Review status: <strong>{selected.review_status||'Not recorded'}</strong></p><p>Evidence verification: {selected.verification_status||'UNVERIFIED'}</p><p>Assigned reviewer: {selected.assigned_reviewer||'Unassigned'}</p><p className="text-xs">Editing, evidence verification and decisions take place on the full record page.</p></>}
    </div>
    <div className="p-4 border-t"><Link to={'/intelligence/'+selected.id} className="intel-button w-full text-center block" onClick={()=>setSelected(null)}>Open full record and review</Link></div>
   </section>
  </div>}
 </div>;
}
