import { useMemo, useRef, useState } from 'react';
import { Plus, Link2, Pencil, Trash2, ArrowRightLeft } from 'lucide-react';
import { Link, useOutletContext } from 'react-router-dom';
import { useRegistry, registry } from '@/components/intel/useIntel';
import { Field, Notice, TYPES, PRIORITIES, err } from '@/components/intel/Fields';
import Status from '@/components/intel/Status';

const STATUSES=['Active','Under Review','Inactive'];
const RELATIONSHIP_TYPES=['Associated with','Member of','Campaign relationship','Publicly linked to','Other observed relationship'];
const blankItem=()=>({priority:'Medium',status:'Active',related_topics:''});
const topicText=v=>Array.isArray(v)?v.join(', '):(v||'');

export default function Watchlist(){
  const {access}=useOutletContext();
  const canManage=access.permissions?.manage_watchlist===true;
  const {items,accounts,relationships,loading,error,refresh}=useRegistry();
  const [form,setForm]=useState(null),[account,setAccount]=useState(null),[relation,setRelation]=useState(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const [q,setQ]=useState(''),[statusFilter,setStatusFilter]=useState(''),[typeFilter,setTypeFilter]=useState(''),[priorityFilter,setPriorityFilter]=useState(''),[geoFilter,setGeoFilter]=useState('');
  const formRef=useRef(null);

  const set=(k,v)=>setForm(f=>({...f,[k]:v}));
  const revealForm=()=>setTimeout(()=>formRef.current?.scrollIntoView({behavior:'smooth',block:'start'}),0);
  const startCreate=()=>{setForm(blankItem());setMessage('');revealForm()};
  const startEdit=x=>{setForm({...x,mode:'edit',related_topics:topicText(x.related_topics)});setMessage('');revealForm()};

  async function submit(e){
    e.preventDefault();setBusy(true);setMessage('');
    const payload={...form,related_topics:String(form.related_topics||'').split(',').map(x=>x.trim()).filter(Boolean)};
    try{
      const editedId=form.mode==='edit'?form.id:null;
      if(form.mode==='edit') await registry('updateWatchlist',payload,form.id);
      else await registry('createWatchlist',payload);
      setForm(null);await refresh();
      if(editedId) setTimeout(()=>document.getElementById('watchlist-card-'+editedId)?.scrollIntoView({behavior:'smooth',block:'center'}),0);
    }catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  async function saveAccount(e){
    e.preventDefault();setBusy(true);setMessage('');
    try{
      if(account.account_id) await registry('updateAccount',account,account.account_id);
      else await registry('addAccount',account,account.watchlist_id);
      setAccount(null);await refresh();
    }catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  async function removeAccount(a){
    if(!window.confirm('Remove this public account / URL from the watchlist?'))return;
    setBusy(true);setMessage('');
    try{await registry('removeAccount',{},a.id);await refresh()}catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  async function saveRelation(e){
    e.preventDefault();setBusy(true);setMessage('');
    try{await registry('addRelationship',relation,relation.from_id);setRelation(null);await refresh()}catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  async function removeRelation(r){
    if(!window.confirm('Remove this relationship?'))return;
    setBusy(true);setMessage('');
    try{await registry('removeRelationship',{},r.id);await refresh()}catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  async function setStatus(x,status){
    setBusy(true);setMessage('');
    try{await registry('updateWatchlist',{status},x.id);await refresh()}catch(e){setMessage(err(e))}finally{setBusy(false)}
  }

  const types=useMemo(()=>Array.from(new Set(items.map(x=>x.type).filter(Boolean))).sort(),[items]);
  const geos=useMemo(()=>Array.from(new Set(items.map(x=>[x.regency_city,x.province].filter(Boolean).join(', ')||'Nationwide'))).sort(),[items]);
  const list=useMemo(()=>items.filter(x=>{
    const geo=[x.regency_city,x.province].filter(Boolean).join(', ')||'Nationwide';
    const text=(x.name+' '+x.type+' '+x.province+' '+x.regency_city+' '+(x.related_topics||[]).join(' ')).toLowerCase();
    return text.includes(q.toLowerCase())&&(!statusFilter||x.status===statusFilter)&&(!typeFilter||x.type===typeFilter)&&(!priorityFilter||x.priority===priorityFilter)&&(!geoFilter||geo===geoFilter);
  }),[items,q,statusFilter,typeFilter,priorityFilter,geoFilter]);

  const relationsFor=x=>relationships.filter(r=>r.from_id===x.id||r.to_id===x.id);

  return <div className="space-y-6">
    <div className="flex justify-between gap-3 items-end">
      <div><p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">Monitoring registry</p><h1 className="intel-heading">Watchlist</h1><p className="text-sm text-[#77899b] mt-2">Human-managed entities, issues, locations, relationships and public source accounts used across the workspace.</p></div>
      {canManage&&<button onClick={startCreate} className="intel-button"><Plus size={16}/>Add Watchlist Item</button>}
    </div>
    <Notice error={message||error}/>

    {form&&<form ref={formRef} onSubmit={submit} className={`intel-card p-6 space-y-5 scroll-mt-6 ${form.mode==='edit'?'ring-2 ring-[#b9d8e5]':''}`}>
      <div><p className="text-[11px] uppercase tracking-[.14em] font-bold text-[#9a7e49]">{form.mode==='edit'?'Editing existing watchlist item':'Create watchlist item'}</p><h2 className="font-semibold text-lg mt-1">{form.mode==='edit'?`Edit: ${form.name||'Watchlist item'}`:'New watchlist item'}</h2>{form.mode==='edit'&&<p className="text-xs text-[#718398] mt-1">Save changes to update this existing record. Cancel returns to the watchlist without changing it.</p>}</div>
      <div className="grid md:grid-cols-3 gap-4">
        <Field label="Name" value={form.name} onChange={v=>set('name',v)} required/>
        <Field label="Type" options={TYPES} value={form.type} onChange={v=>set('type',v)} required/>
        <Field label="Monitoring Priority" options={PRIORITIES} value={form.priority} onChange={v=>set('priority',v)}/>
        <Field label="Province" value={form.province} onChange={v=>set('province',v)}/>
        <Field label="Regency / City" value={form.regency_city} onChange={v=>set('regency_city',v)}/>
        <Field label="Related Election" value={form.related_election} onChange={v=>set('related_election',v)}/>
        <Field label="Related Entity" value={form.related_entity} onChange={v=>set('related_entity',v)}/>
        <Field label="Related Topics (comma-separated)" value={form.related_topics} onChange={v=>set('related_topics',v)}/>
        <Field label="Monitoring Status" options={STATUSES} value={form.status} onChange={v=>set('status',v)}/>
      </div>
      <Field label="Description" as="textarea" value={form.description} onChange={v=>set('description',v)}/>
      <Field label="Notes" as="textarea" value={form.notes} onChange={v=>set('notes',v)}/>
      <div className="flex gap-2"><button disabled={busy} className="intel-button">{busy?'Saving...':form.mode==='edit'?'Save changes':'Create item'}</button><button type="button" onClick={()=>setForm(null)} className="intel-ghost">Cancel</button></div>
    </form>}

    <div className="intel-card p-4 grid sm:grid-cols-2 xl:grid-cols-5 gap-3">
      <input className="intel-input" placeholder="Search name, type, topic or geography..." aria-label="Search watchlist" value={q} onChange={e=>setQ(e.target.value)}/>
      <select className="intel-input" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="">All statuses</option>{STATUSES.map(x=><option key={x}>{x}</option>)}</select>
      <select className="intel-input" value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}><option value="">All types</option>{types.map(x=><option key={x}>{x}</option>)}</select>
      <select className="intel-input" value={priorityFilter} onChange={e=>setPriorityFilter(e.target.value)}><option value="">All priorities</option>{PRIORITIES.map(x=><option key={x}>{x}</option>)}</select>
      <select className="intel-input" value={geoFilter} onChange={e=>setGeoFilter(e.target.value)}><option value="">All geographies</option>{geos.map(x=><option key={x}>{x}</option>)}</select>
    </div>

    {loading?<p>Loading watchlist...</p>:<div className="grid xl:grid-cols-2 gap-4">
      {list.map(x=><div id={'watchlist-card-'+x.id} className="intel-card p-6 scroll-mt-6" key={x.id}>
        <div className="flex justify-between gap-3">
          <div><p className="text-[11px] uppercase text-[#6b8ca0] font-bold tracking-wider">{x.type}</p><h2 className="font-semibold text-lg mt-1">{x.name}</h2></div>
          <div className="flex items-start gap-2"><Status value={x.priority}/><Status value={x.status}/></div>
        </div>
        <p className="text-sm text-[#718398] mt-3">{x.description||'No description provided.'}</p>
        {!!x.related_topics?.length&&<div className="flex flex-wrap gap-1.5 mt-3">{x.related_topics.map(t=><span key={t} className="rounded-full bg-[#f2f6f8] px-2 py-1 text-[11px] text-[#536d80]">{t}</span>)}</div>}
        <div className="text-xs text-[#7f91a1] mt-3">{[x.regency_city,x.province].filter(Boolean).join(', ')||'Nationwide'} · {x.related_election||'Election not specified'}</div>
        <div className="text-xs text-[#7f91a1] mt-2">Created {new Date(x.created_date).toLocaleDateString('en-GB')} · Updated {new Date(x.updated_date).toLocaleDateString('en-GB')}</div>
        <div className="flex flex-wrap gap-3 mt-4">
          <Link to={'/inbox?entity='+encodeURIComponent(x.name)} className="text-xs font-semibold text-[#126b8b]">View related intelligence →</Link>
          {canManage&&<button className="text-xs font-semibold text-[#126b8b]" onClick={()=>startEdit(x)}><Pencil size={13} className="inline mr-1"/>Edit</button>}
          {canManage&&x.status!=='Active'&&<button className="text-xs font-semibold text-[#126b8b]" disabled={busy} onClick={()=>setStatus(x,'Active')}>Activate</button>}
          {canManage&&x.status!=='Under Review'&&<button className="text-xs font-semibold text-[#126b8b]" disabled={busy} onClick={()=>setStatus(x,'Under Review')}>Set Under Review</button>}
          {canManage&&x.status!=='Inactive'&&<button className="text-xs font-semibold text-[#7a5960]" disabled={busy} onClick={()=>setStatus(x,'Inactive')}>Deactivate</button>}
        </div>

        <div className="border-t border-[#edf1f5] mt-5 pt-4">
          <div className="text-xs font-bold text-[#536d80] mb-2">PUBLIC ACCOUNTS & URLS</div>
          {accounts.filter(a=>a.watchlist_id===x.id).map(a=><div key={a.id} className="flex items-center justify-between gap-3 py-1.5">
            <a className="flex min-w-0 gap-2 items-center text-sm text-[#157396] break-all hover:underline" href={a.url} target="_blank" rel="noreferrer"><Link2 size={14} className="shrink-0"/><span>{a.platform||'Web'} · {a.handle||a.url}</span></a>
            {canManage&&<span className="flex gap-2 shrink-0"><button className="text-xs text-[#126b8b]" onClick={()=>setAccount({account_id:a.id,watchlist_id:x.id,platform:a.platform,url:a.url,handle:a.handle})}>Edit</button><button className="text-xs text-red-700" onClick={()=>removeAccount(a)}><Trash2 size={13}/></button></span>}
          </div>)}
          {!accounts.some(a=>a.watchlist_id===x.id)&&<p className="text-xs text-[#8192a3]">No registered public account / URL.</p>}
          {account?.watchlist_id===x.id?<form onSubmit={saveAccount} className="grid sm:grid-cols-3 gap-2 mt-3">
            <Field label="Platform" value={account.platform} onChange={v=>setAccount({...account,platform:v})}/>
            <Field label="Public URL" type="url" value={account.url} onChange={v=>setAccount({...account,url:v})} required/>
            <Field label="Handle" value={account.handle} onChange={v=>setAccount({...account,handle:v})}/>
            <button disabled={busy} className="intel-button">{account.account_id?'Save account':'Add account'}</button>
            <button type="button" className="intel-ghost" onClick={()=>setAccount(null)}>Cancel</button>
          </form>:canManage&&<button className="text-xs font-semibold text-[#126b8b] mt-2" onClick={()=>setAccount({watchlist_id:x.id})}>+ Add public URL / account</button>}
        </div>

        <div className="border-t border-[#edf1f5] mt-4 pt-4">
          <div className="text-xs font-bold text-[#536d80] mb-2 flex items-center gap-2"><ArrowRightLeft size={13}/>RELATED WATCHLIST ITEMS</div>
          <div className="space-y-1.5">
            {relationsFor(x).map(r=>{
              const outgoing=r.from_id===x.id;
              const otherId=outgoing?r.to_id:r.from_id;
              const other=items.find(i=>i.id===otherId);
              return <div key={r.id} className="flex items-center justify-between gap-3 text-xs"><span>{outgoing?'→':'←'} <strong>{r.relationship_type}</strong> · {other?.name||'Entity'}{other?.type?' · '+other.type:''}</span>{canManage&&<button className="text-red-700" onClick={()=>removeRelation(r)}><Trash2 size={13}/></button>}</div>
            })}
            {!relationsFor(x).length&&<p className="text-xs text-[#8192a3]">No recorded relationship.</p>}
          </div>
          {relation?.from_id===x.id?<form onSubmit={saveRelation} className="grid sm:grid-cols-2 gap-2 mt-3">
            <select className="intel-input" value={relation.to_id||''} onChange={e=>setRelation({...relation,to_id:e.target.value})} required><option value="">Select watchlist item</option>{items.filter(i=>i.id!==x.id).map(i=><option key={i.id} value={i.id}>{i.name} · {i.type}{(i.regency_city||i.province)?' · '+[i.regency_city,i.province].filter(Boolean).join(', '):''}</option>)}</select>
            <select className="intel-input" value={relation.relationship_type||''} onChange={e=>setRelation({...relation,relationship_type:e.target.value})} required><option value="">Select relationship type</option>{RELATIONSHIP_TYPES.map(v=><option key={v}>{v}</option>)}</select>
            <button disabled={busy} className="intel-button">Link items</button>
            <button type="button" className="intel-ghost" onClick={()=>setRelation(null)}>Cancel</button>
          </form>:canManage&&<button className="text-xs font-semibold text-[#126b8b] mt-2" onClick={()=>setRelation({from_id:x.id})}>+ Link watchlist item</button>}
        </div>
      </div>)}
      {!list.length&&<div className="intel-card p-10 text-sm text-[#73869a]">No watchlist items match the current filters.</div>}
    </div>}
  </div>;
}
