import { useEffect, useState } from 'react';
import { intel } from './useIntel';
import { Field, Notice, err } from './Fields';
import PublicationFields from './PublicationFields';
import LanguagePicker from './LanguagePicker';
import { useLanguage } from '@/lib/LanguageContext';

const fieldLabels={
 title:'headline',
 original_content:'original content',
 source_name:'source / publisher',
 platform:'platform',
 author:'author / account',
 publication_date:'publication date',
 publication_time_precision:'publication precision',
 publication_datetime:'publication time',
 original_language_code:'original language'
};

const hydrateSource=x=>({...x,publication_time:x?.publication_time||(x?.publication_datetime?.includes('T')?x.publication_datetime.split('T')[1]?.slice(0,5):'')});
const flashKey=id=>`bawaslu-source-recovery-${id}`;

export default function SourceCorrection({item,onSaved,onRecordAction,canTriage}){
 const {t}=useLanguage();
 const initialFlash=(()=>{try{return JSON.parse(sessionStorage.getItem(flashKey(item.id))||'null')}catch{return null}})();
 const [source,setSource]=useState(()=>hydrateSource(item)),[status,setStatus]=useState(initialFlash?.status||''),[recovered,setRecovered]=useState(initialFlash?.recovered||[]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>setSource(hydrateSource(item)),[item.updated_date]);

 async function retrieve(){
  setBusy(true);setError('');setRecovered([]);
  try{
   const r=await onRecordAction('recoverSource',{automatic:true},item.id);
   const recoveredFields=r.recovered_fields||[];
   const message=recoveredFields.length?t('recovered')+': '+recoveredFields.map(x=>fieldLabels[x]||x).join(' · '):t('retrieve_source');
   setSource(hydrateSource(r.item||item));
   setRecovered(recoveredFields);
   setStatus(message);
   try{sessionStorage.setItem(flashKey(item.id),JSON.stringify({status:message,recovered:recoveredFields}))}catch{}
   await onSaved();
  }catch(e){
   setStatus(t('source_retrieval_unavailable'));
   setError(err(e));
  }finally{setBusy(false)}
 }

 async function save(e){
  e.preventDefault();setBusy(true);setError('');setRecovered([]);
  try{
   const r=await onRecordAction('recoverSource',{
    title:source.title,
    original_content:source.original_content,
    source_name:source.source_name,
    platform:source.platform,
    author:source.author,
    publication_date:source.publication_date,
    publication_time_precision:source.publication_time_precision,
    publication_time:source.publication_time||'',
    original_language_code:source.original_language_code
   },item.id);
   const recoveredFields=r.recovered_fields||[];
   const message=recoveredFields.length?t('save_missing_source_fields'):t('retrieve_source');
   setSource(hydrateSource(r.item||source));
   setRecovered(recoveredFields);
   setStatus(message);
   try{sessionStorage.setItem(flashKey(item.id),JSON.stringify({status:message,recovered:recoveredFields}))}catch{}
   await onSaved();
  }catch(e){setError(err(e))}finally{setBusy(false)}
 }

 return <div className="space-y-4">
  <section className="intel-card p-5 space-y-4">
   <h3 className="font-semibold">{t('source_recovery')} · {item.intelligence_id}</h3>
   <p className="text-sm break-all">{item.source_url}</p>
   <Notice error={error}/>
   <button type="button" className="intel-ghost" disabled={busy} onClick={retrieve}>{busy?t('retrieving'):t('retrieve_source')}</button>
   {status&&<p role="status" className="text-sm font-semibold text-[#a04724]">{status}</p>}
   {recovered.length>0&&<div className="rounded-lg border border-[#d9e6ec] bg-[#f7fbfc] p-3 text-xs text-[#526b7c]"><span className="font-semibold">{t('recovered')}:</span> {recovered.map(x=>fieldLabels[x]||x).join(' · ')}</div>}
   <p className="text-xs">{t('recovery_note')}</p>

   <form onSubmit={save} className="space-y-4">
    <div className="grid md:grid-cols-2 gap-3">
     <Field label={t('original_headline')} value={source.title} onChange={v=>setSource(x=>({...x,title:v}))}/>
     <Field label={t('source_publisher')} value={source.source_name} onChange={v=>setSource(x=>({...x,source_name:v}))}/>
     <Field label={t('platform')} value={source.platform} onChange={v=>setSource(x=>({...x,platform:v}))}/>
     <Field label={t('author_account_lower')} value={source.author} onChange={v=>setSource(x=>({...x,author:v}))}/>
     <PublicationFields value={source} onChange={setSource}/>
     <LanguagePicker value={source.original_language_code||''} onChange={v=>setSource(x=>({...x,original_language_code:v}))} content={source.original_content||''}/>
    </div>
    <Field label={t('original_content_extract')} as="textarea" value={source.original_content} onChange={v=>setSource(x=>({...x,original_content:v}))}/>
    <button disabled={busy} className="intel-button">{t('save_missing_source_fields')}</button>
   </form>
  </section>
  {canTriage&&source.original_content?.trim().length>=80&&<a href="#ai-triage-review" className="text-sm font-semibold text-[#126d91]">{t('review_ai_below')}</a>}
 </div>;
}
