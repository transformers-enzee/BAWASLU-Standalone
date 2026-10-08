import { useMemo, useState } from 'react';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { PRIORITIES, Notice } from '@/components/intel/Fields';

const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const triagePending=x=>{
  const t=x.triage_review||x.triage_review_status||{};
  const state=typeof t==='string'?t:t.state;
  const generated=typeof t==='object'?t.generated:!!state;
  return generated&&state&&state!=='REVIEW COMPLETE';
};

function initialFilters(){
  const q=new URLSearchParams(window.location.search);
  const f={};
  for(const key of ['entity','verification_status','review_status','priority','province','regency_city','platform','evidence_type','reviewer','source_type','supervision_signal','date','search']){
    const value=q.get(key);
    if(value)f[key]=value;
  }
  if(q.get('view'))f.view=q.get('view');
  return f;
}

const quickViews=[
  ['', 'All intelligence'],
  ['pending-review','Pending Review'],
  ['validated','Validated'],
  ['unverified','UNVERIFIED'],
  ['jurisdiction-unresolved','Jurisdiction Unresolved'],
  ['triage-pending','AI Triage Awaiting Review']
];

const labelForKey={
  search:'Search',date:'Date',entity:'Entity',verification_status:'Verification',review_status:'Review status',
  priority:'Priority',province:'Province',regency_city:'Regency / City',platform:'Platform',evidence_type:'Evidence type',
  reviewer:'Reviewer',source_type:'Source type',supervision_signal:'Supervision signal'
};

export default function Inbox(){
  const {items,loading,error}=useIntel(),{items:entities}=useRegistry();
  const [f,setF]=useState(initialFilters);
  const [sort,setSort]=useState('updated-desc');
  const pick=(key,value)=>setF(v=>({...v,[key]:value}));
  const unique=key=>[...new Set(items.flatMap(x=>['province','regency_city'].includes(key)?(x.geographic_assignments||[]).map(a=>a[key]).filter(Boolean):[x[key]]).filter(Boolean))].sort();
  const options={
    province:unique('province'),regency_city:unique('regency_city'),entity:entities.map(x=>x.name),
    platform:unique('platform'),evidence_type:['OBSERVED','INFERRED'],verification_status:['UNVERIFIED','HUMAN_VERIFIED'],
    supervision_signal:['NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'],
    priority:PRIORITIES,reviewer:unique('assigned_reviewer'),review_status:unique('review_status'),source_type:unique('source_type')
  };

  const filtered=useMemo(()=>items.filter(x=>{
    const text=(x.intelligence_id+' '+x.title+' '+x.original_content+' '+(x.related_entities||[]).join(' ')+' '+x.province+' '+x.regency_city+' '+(x.geographic_assignments||[]).map(a=>a.province+' '+a.regency_city).join(' ')).toLowerCase();
    const specialOk=
      !f.view||
      (f.view==='pending-review'&&pendingReview(x))||
      (f.view==='validated'&&validated(x))||
      (f.view==='unverified'&&(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED')||
      (f.view==='jurisdiction-unresolved'&&x.jurisdiction_confirmed!==true)||
      (f.view==='triage-pending'&&triagePending(x));
    return specialOk&&
      (!f.search||text.includes(f.search.toLowerCase()))&&
      (!f.date||x.created_date?.slice(0,10)===f.date)&&
      Object.keys(options).every(k=>!f[k]||(
        k==='entity'?x.related_entities?.includes(f[k]):
        k==='reviewer'?x.assigned_reviewer===f[k]:
        k==='supervision_signal'?x.supervision_screening?.supervision_signal===f[k]:
        k==='evidence_type'?(x.evidence_type||(['OBSERVED','INFERRED'].includes(x.evidence_state)?x.evidence_state:''))===f[k]:
        k==='verification_status'?(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))===f[k]:
        ['province','regency_city'].includes(k)?(x.geographic_assignments||[]).some(a=>a[k]===f[k]):
        x[k]===f[k]
      ));
  }),[items,f]);

  const sorted=useMemo(()=>[...filtered].sort((a,b)=>{
    if(sort==='updated-desc')return new Date(b.updated_date||b.created_date||0)-new Date(a.updated_date||a.created_date||0);
    if(sort==='created-desc')return new Date(b.created_date||0)-new Date(a.created_date||0);
    if(sort==='created-asc')return new Date(a.created_date||0)-new Date(b.created_date||0);
    if(sort==='priority'){
      const rank={Critical:4,High:3,Medium:2,Low:1};
      return (rank[b.priority]||0)-(rank[a.priority]||0);
    }
    if(sort==='id')return String(a.intelligence_id||'').localeCompare(String(b.intelligence_id||''));
    return 0;
  }),[filtered,sort]);

  const counts=useMemo(()=>({
    '':items.length,
    'pending-review':items.filter(pendingReview).length,
    validated:items.filter(validated).length,
    unverified:items.filter(x=>(x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED'))==='UNVERIFIED').length,
    'jurisdiction-unresolved':items.filter(x=>x.jurisdiction_confirmed!==true).length,
    'triage-pending':items.filter(triagePending).length
  }),[items]);

  const activeFilters=Object.entries(f).filter(([k,v])=>k!=='view'&&v);
  const clearOne=key=>setF(v=>({...v,[key]:''}));
  const currentView=quickViews.find(([value])=>value===(f.view||''))?.[1]||'All intelligence';

  return <div className="space-y-6">
    <div>
      <p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">Collection / Triage</p>
      <h1 className="intel-heading">Intelligence Inbox</h1>
      <p className="text-sm text-[#77899b] mt-2">{currentView} · {sorted.length} match{sorted.length===1?'':'es'} · {items.length} record{items.length===1?'':'s'} in authorized scope</p>
    </div>

    <Notice error={error}/>

    <div className="intel-card p-4">
      <div className="flex flex-wrap gap-2">
        {quickViews.map(([value,label])=><button key={value||'all'} type="button" className={(f.view||'')===value?'intel-button':'intel-ghost'} onClick={()=>pick('view',value)}>
          {label} <span className="opacity-70">({counts[value]||0})</span>
        </button>)}
      </div>
    </div>

    <div className="intel-card p-5 space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-3">
        <input className="intel-input sm:col-span-2" placeholder="Search keywords, ID, entity or location..." aria-label="Search intelligence" value={f.search||''} onChange={e=>pick('search',e.target.value)}/>
        <input className="intel-input" type="date" aria-label="Filter by date" value={f.date||''} onChange={e=>pick('date',e.target.value)}/>
        {Object.entries(options).map(([key,values])=><select key={key} className="intel-input" aria-label={'Filter by '+key.replace('_',' ')} value={f[key]||''} onChange={e=>pick(key,e.target.value)}><option value="">All {key.replace(/_/g,' ')}</option>{values.map(v=><option key={v} value={v}>{v}</option>)}</select>)}
        <select className="intel-input" aria-label="Sort intelligence" value={sort} onChange={e=>setSort(e.target.value)}>
          <option value="updated-desc">Recently updated</option>
          <option value="created-desc">Newest created</option>
          <option value="created-asc">Oldest created</option>
          <option value="priority">Highest priority</option>
          <option value="id">Intelligence ID</option>
        </select>
      </div>

      {(activeFilters.length>0||f.view)&&<div className="flex flex-wrap items-center gap-2">
        {f.view&&<span className="rounded-full bg-[#eaf4f7] px-3 py-1 text-xs font-semibold text-[#176e8e]">View: {currentView}</span>}
        {activeFilters.map(([key,value])=><button key={key} type="button" onClick={()=>clearOne(key)} className="rounded-full bg-[#f5f7f9] px-3 py-1 text-xs text-[#536d80] hover:bg-[#edf2f5]">
          {labelForKey[key]||key}: {value} ×
        </button>)}
        <button className="text-xs font-semibold text-[#126b8b]" onClick={()=>setF({})}>Clear all filters</button>
      </div>}
    </div>

    {new URLSearchParams(window.location.search).get('jurisdiction')==='pending'&&<p role="status" className="text-sm">Submitted for national jurisdiction resolution. Regional users cannot access the record until it is confirmed.</p>}

    {loading?<p className="text-sm text-[#77899b]">Loading intelligence...</p>:error?null:<IntelligenceTable items={sorted}/>}
  </div>;
}
