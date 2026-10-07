import { useEffect, useState } from 'react';
import { intel } from './useIntel';
import { Field, Notice, err } from './Fields';
import PublicationFields from './PublicationFields';
import LanguagePicker from './LanguagePicker';

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

export default function SourceCorrection({item,onSaved,onRecordAction,canTriage}){
 const [source,setSource]=useState(item),[status,setStatus]=useState(''),[recovered,setRecovered]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>setSource(item),[item.updated_date]);

 async function retrieve(){
  setBusy(true);setError('');setRecovered([]);
  try{
   const r=await onRecordAction('recoverSource',{automatic:true},item.id);
   setSource(r.item||item);
   setRecovered(r.recovered_fields||[]);
   setStatus((r.recovered_fields||[]).length?'Missing source fields recovered. Review them below.':'Source retrieved, but no missing fields required changes.');
   await onSaved();
  }catch(e){
   setStatus('SOURCE RETRIEVAL UNAVAILABLE');
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
    publication_time:source.publication_datetime?.includes('T')?source.publication_datetime.split('T')[1]?.slice(0,8):'',
    original_language_code:source.original_language_code
   },item.id);
   setSource(r.item||source);
   setRecovered(r.recovered_fields||[]);
   setStatus((r.recovered_fields||[]).length?'Missing source fields saved.':'No missing source fields were changed.');
   await onSaved();
  }catch(e){setError(err(e))}finally{setBusy(false)}
 }

 return <div className="space-y-4">
  <section className="intel-card p-5 space-y-4">
   <h3 className="font-semibold">URL source recovery · {item.intelligence_id}</h3>
   <p className="text-sm break-all">{item.source_url}</p>
   <Notice error={error}/>
   <button type="button" className="intel-ghost" disabled={busy} onClick={retrieve}>{busy?'Retrieving...':'Retrieve source'}</button>
   {status&&<p role="status" className="text-sm font-semibold text-[#a04724]">{status}</p>}
   {recovered.length>0&&<div className="rounded-lg border border-[#d9e6ec] bg-[#f7fbfc] p-3 text-xs text-[#526b7c]"><span className="font-semibold">Recovered:</span> {recovered.map(x=>fieldLabels[x]||x).join(' · ')}</div>}
   <p className="text-xs">Automatic recovery only fills missing source fields. Existing original evidence is preserved and never silently replaced.</p>

   <form onSubmit={save} className="space-y-4">
    <div className="grid md:grid-cols-2 gap-3">
     <Field label="Original headline" value={source.title} onChange={v=>setSource(x=>({...x,title:v}))}/>
     <Field label="Source / Publisher" value={source.source_name} onChange={v=>setSource(x=>({...x,source_name:v}))}/>
     <Field label="Platform" value={source.platform} onChange={v=>setSource(x=>({...x,platform:v}))}/>
     <Field label="Author / account" value={source.author} onChange={v=>setSource(x=>({...x,author:v}))}/>
     <PublicationFields value={source} onChange={setSource}/>
     <LanguagePicker value={source.original_language_code||''} onChange={v=>setSource(x=>({...x,original_language_code:v}))} content={source.original_content||''}/>
    </div>
    <Field label="Original content / extract" as="textarea" value={source.original_content} onChange={v=>setSource(x=>({...x,original_content:v}))}/>
    <button disabled={busy} className="intel-button">Save missing source fields</button>
   </form>
  </section>
  {canTriage&&source.original_content?.trim().length>=80&&<a href="#ai-triage-review" className="text-sm font-semibold text-[#126d91]">Review AI suggestions in the AI Triage section below</a>}
 </div>;
}
