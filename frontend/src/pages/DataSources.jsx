import { useState } from 'react';
import { useRegistry, registry } from '@/components/intel/useIntel';
import { Field, Notice, err } from '@/components/intel/Fields';
import Status from '@/components/intel/Status';
import { useLanguage } from '@/lib/LanguageContext';

const types=['MANUAL_LINK','MANUAL_ENTRY','FILE_UPLOAD','INTERNAL_BAWASLU','OFFICIAL_SOURCE'];

export default function DataSources(){
 const {t,label}=useLanguage();
 const {sources,loading,error,refresh}=useRegistry();
 const [form,setForm]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 const set=(k,v)=>setForm(f=>({...f,[k]:v}));
 async function submit(e){e.preventDefault();setBusy(true);try{await registry('addSource',form);setForm(null);await refresh()}catch(e){setMessage(err(e))}finally{setBusy(false)}}
 return <div className="space-y-6">
  <div className="flex justify-between items-end">
   <div>
    <p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('collection_registry')}</p>
    <h1 className="intel-heading">{t('data_sources')}</h1>
    <p className="text-sm text-[#77899b] mt-2">{t('data_sources_intro')}</p>
   </div>
   <button onClick={()=>setForm({})} className="intel-button">{t('register_source')}</button>
  </div>
  <Notice error={message||error}/>
  {form&&<form className="intel-card p-6 space-y-4" onSubmit={submit}>
   <h2 className="font-semibold">{t('register_data_source')}</h2>
   <div className="grid md:grid-cols-3 gap-4">
    <Field label={t('name')} required value={form.name} onChange={v=>set('name',v)}/>
    <Field label={t('source_type')} required options={types} value={form.source_type} onChange={v=>set('source_type',v)}/>
    <Field label={t('province')} value={form.province} onChange={v=>set('province',v)}/>
    <Field label={t('regency_city')} value={form.regency_city} onChange={v=>set('regency_city',v)}/>
   </div>
   <Field label={t('description')} as="textarea" value={form.description} onChange={v=>set('description',v)}/>
   <button disabled={busy} className="intel-button">{t('save_source')}</button> <button type="button" onClick={()=>setForm(null)} className="intel-ghost">{t('cancel')}</button>
  </form>}
  <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
   {types.map(type=><div key={type} className="intel-card p-5"><div className="flex justify-between"><span className="font-semibold text-sm">{label(type)}</span><Status value="Available"/></div><p className="text-xs text-[#8192a3] mt-3">{t('collection_method_note')}</p></div>)}
   <div className="intel-card p-5"><div className="flex justify-between"><span className="font-semibold text-sm">SOCIALCRAWL</span><Status value="Available"/></div><p className="text-xs text-[#8192a3] mt-3">{t('socialcrawl_provider_note')}</p></div>
   <div className="intel-card p-5 opacity-60"><div className="flex justify-between"><span className="font-semibold text-sm">NEWS API</span><Status value="Disabled"/></div><p className="text-xs text-[#8192a3] mt-3">{t('no_provider_connected')}</p></div>
  </div>
  <h2 className="font-semibold">{t('registered_sources')}</h2>
  {loading?<p>{t('loading_generic')}</p>:sources.length?<div className="intel-card divide-y">{sources.map(s=><div key={s.id} className="p-4 flex justify-between text-sm"><span>{s.name} <span className="text-[#8293a4]">· {label(s.source_type)} · {label(s.province||'National')}</span></span><Status value={s.status}/></div>)}</div>:<div className="intel-card p-6 text-sm text-[#8192a3]">{t('no_custom_sources')}</div>}
 </div>;
}