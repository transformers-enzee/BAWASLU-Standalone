import { useMemo, useState } from 'react';
import { useRegistry, registry } from '@/components/intel/useIntel';
import { Field, Notice, err } from '@/components/intel/Fields';
import Status from '@/components/intel/Status';
import { useLanguage } from '@/lib/LanguageContext';
import regions from '@/components/intel/regions.json';

const types=['MANUAL_LINK','MANUAL_ENTRY','FILE_UPLOAD','INTERNAL_BAWASLU','OFFICIAL_SOURCE'];
const statuses=['Active','Inactive'];

const emptyForm=()=>({name:'',source_type:'',description:'',status:'Active',province:'',regency_city:''});

export default function DataSources(){
 const {t,label}=useLanguage();
 const {sources,loading,error,refresh}=useRegistry();
 const [form,setForm]=useState(null);
 const [editingId,setEditingId]=useState('');
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const [search,setSearch]=useState('');
 const [typeFilter,setTypeFilter]=useState('');
 const [statusFilter,setStatusFilter]=useState('');

 const set=(k,v)=>setForm(f=>({...f,[k]:v}));
 const selectedProvince=regions.provinces.find(p=>p.name===form?.province);
 const regencyOptions=selectedProvince?regions.regencies.filter(r=>r.province_code===selectedProvince.code):[];
 const setProvince=v=>setForm(f=>({...f,province:v,regency_city:''}));

 const activeCount=sources.filter(x=>x.status==='Active').length;
 const inactiveCount=sources.filter(x=>x.status==='Inactive').length;
 const geographicCount=sources.filter(x=>x.province||x.regency_city).length;

 const filtered=useMemo(()=>sources.filter(s=>{
   const hay=[s.name,s.source_type,s.province,s.regency_city,s.description].filter(Boolean).join(' ').toLowerCase();
   if(search&&!hay.includes(search.toLowerCase()))return false;
   if(typeFilter&&s.source_type!==typeFilter)return false;
   if(statusFilter&&s.status!==statusFilter)return false;
   return true;
 }),[sources,search,typeFilter,statusFilter]);

 function startCreate(){
   setEditingId('');
   setForm(emptyForm());
   setMessage('');
 }

 function startEdit(source){
   setEditingId(source.id);
   setForm({
     name:source.name||'',
     source_type:source.source_type||'',
     description:source.description||'',
     status:source.status||'Active',
     province:source.province||'',
     regency_city:source.regency_city||''
   });
   setMessage('');
 }

 async function submit(e){
   e.preventDefault();
   if(!(form?.name||'').trim()){setMessage(t('source_name_required'));return}
   if(!(form?.source_type||'').trim()){setMessage(t('source_type_required'));return}
   setBusy(true);setMessage('');
   try{
     if(editingId){
       await registry('updateSource',form,editingId);
       setMessage(t('source_updated'));
     }else{
       await registry('addSource',form);
       setMessage(t('source_saved'));
     }
     setForm(null);setEditingId('');
     await refresh();
   }catch(e){setMessage(err(e))}
   finally{setBusy(false)}
 }

 return <div className="space-y-6">
  <div className="flex flex-wrap justify-between items-end gap-4">
   <div>
    <p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('collection_registry')}</p>
    <h1 className="intel-heading">{t('data_sources')}</h1>
    <p className="text-sm text-[#77899b] mt-2">{t('data_sources_workspace')} · {t('data_sources_intro')}</p>
   </div>
   <button onClick={startCreate} className="intel-button">{t('register_source')}</button>
  </div>

  <Notice error={(message&&![t('source_saved'),t('source_updated')].includes(message)?message:'')||error}/>
  {[t('source_saved'),t('source_updated')].includes(message)&&<p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</p>}

  <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('data_sources_total')}</p><p className="text-2xl font-semibold mt-1">{sources.length}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('data_sources_active')}</p><p className="text-2xl font-semibold mt-1">{activeCount}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('data_sources_inactive')}</p><p className="text-2xl font-semibold mt-1">{inactiveCount}</p></div>
   <div className="intel-card p-4"><p className="text-xs text-[#8192a3]">{t('data_sources_geographic')}</p><p className="text-2xl font-semibold mt-1">{geographicCount}</p></div>
  </div>

  {form&&<form className="intel-card p-6 space-y-4" onSubmit={submit}>
   <h2 className="font-semibold">{editingId?t('edit_source'):t('register_data_source')}</h2>
   <div className="grid md:grid-cols-3 gap-4">
    <Field label={t('name')} required value={form.name} onChange={v=>set('name',v)}/>
    <Field label={t('source_type')} required options={types} value={form.source_type} onChange={v=>set('source_type',v)}/>
    <Field label={t('source_status')} required options={statuses} value={form.status} onChange={v=>set('status',v)}/>
    <label className="block"><span className="intel-label">{t('province')}</span><select className="intel-input" value={form.province||''} onChange={e=>setProvince(e.target.value)}><option value="">{t('select_province')}</option>{regions.provinces.map(p=><option key={p.code} value={p.name}>{p.name}</option>)}</select></label>
    <label className="block"><span className="intel-label">{t('regency_city')}</span><select className="intel-input" value={form.regency_city||''} onChange={e=>set('regency_city',e.target.value)} disabled={!form.province}><option value="">{form.province?t('entire_province'):t('select_province_first')}</option>{regencyOptions.map(r=><option key={r.code} value={r.name}>{r.name}</option>)}</select></label>
   </div>
   <Field label={t('description')} as="textarea" value={form.description} onChange={v=>set('description',v)}/>
   <button disabled={busy} className="intel-button">{busy?t('saving'):(editingId?t('update_source'):t('save_source'))}</button>
   <button type="button" onClick={()=>{setForm(null);setEditingId('')}} className="intel-ghost">{t('cancel')}</button>
  </form>}

  <section className="space-y-3">
   <h2 className="font-semibold">{t('provider_inventory')}</h2>
   <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
    {types.map(type=><div key={type} className="intel-card p-5"><div className="flex justify-between"><span className="font-semibold text-sm">{label(type)}</span><Status value="Available"/></div><p className="text-xs text-[#8192a3] mt-3">{t('collection_method_note')}</p></div>)}
    <div className="intel-card p-5"><div className="flex justify-between"><span className="font-semibold text-sm">SOCIALCRAWL</span><Status value="Available"/></div><p className="text-xs text-[#8192a3] mt-3">{t('socialcrawl_provider_note')}</p></div>
    <div className="intel-card p-5 opacity-60"><div className="flex justify-between"><span className="font-semibold text-sm">NEWS API</span><Status value="Disabled"/></div><p className="text-xs text-[#8192a3] mt-3">{t('no_provider_connected')}</p></div>
   </div>
  </section>

  <section className="space-y-3">
   <div className="flex flex-wrap justify-between gap-3 items-center"><h2 className="font-semibold">{t('custom_source_registry')}</h2></div>
   <div className="intel-card p-4 grid md:grid-cols-3 gap-3">
    <input className="intel-input" placeholder={t('data_sources_search')} value={search} onChange={e=>setSearch(e.target.value)}/>
    <select className="intel-input" value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}><option value="">{t('data_sources_all_types')}</option>{types.map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
    <select className="intel-input" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="">{t('data_sources_all_statuses')}</option>{statuses.map(x=><option key={x} value={x}>{label(x)}</option>)}</select>
   </div>

   {loading?<p>{t('loading_generic')}</p>:filtered.length?<div className="intel-card divide-y">{filtered.map(s=><div key={s.id} className="p-4 flex flex-wrap justify-between gap-4 text-sm">
    <div className="min-w-0">
     <p className="font-semibold">{s.name}</p>
     <p className="text-[#8293a4] mt-1">{label(s.source_type)} · {s.regency_city?[s.regency_city,s.province].filter(Boolean).join(', '):label(s.province||'National')}</p>
     {s.description&&<p className="text-xs text-[#718599] mt-2">{s.description}</p>}
    </div>
    <div className="flex items-center gap-3"><Status value={s.status}/><button type="button" className="text-[#146a8b] font-semibold" onClick={()=>startEdit(s)}>{t('edit_source')}</button></div>
   </div>)}</div>:<div className="intel-card p-6 text-sm text-[#8192a3]">{t('no_custom_sources')}</div>}
  </section>
 </div>;
}
