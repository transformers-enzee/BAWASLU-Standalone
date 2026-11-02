import {useEffect,useState} from 'react';
import {useLanguage} from '@/lib/LanguageContext';

// A display-only translation cache. No saved AI assessment or source record is modified.
const translated=new Map();
const pending=new Map();
const indonesiaWords=/\b(yang|dengan|untuk|tidak|dari|pada|dalam|terkait|sebagai|tersebut|menurut|telah|menunjukkan|adalah|berdasarkan|terhadap)\b/gi;
const englishWords=/\b(the|and|that|with|from|about|this|their|reported|evidence|should|however|there|were|review|because|following)\b/gi;
function probablyIndonesian(text){
 const id=(String(text).match(indonesiaWords)||[]).length;
 const en=(String(text).match(englishWords)||[]).length;
 return id>=2&&id>en;
}
function requestTranslation(original,language){
 const key=language+'\u0000'+original;
 if(translated.has(key))return Promise.resolve(translated.get(key));
 if(pending.has(key))return pending.get(key);
 const token=window.localStorage.getItem('bawaslu_access_token')||'';
 const job=fetch('/api/presentation/translate',{
  method:'POST',cache:'no-store',
  headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
  body:JSON.stringify({text:original,language})
 }).then(async response=>{
   const payload=await response.json().catch(()=>({}));
   if(!response.ok||typeof payload.text!=='string'||!payload.text.trim())throw Error('Translation not available');
   translated.set(key,payload.text);
   if(translated.size>300)translated.delete(translated.keys().next().value);
   return payload.text;
 }).finally(()=>pending.delete(key));
 pending.set(key,job);
 return job;
}
export default function useTranslatedPresentationText(text){
 const {language}=useLanguage();
 const original=String(text||'');
 const needs=Boolean(original.trim())&&original.length<=18000&&
   (language==='id'?!probablyIndonesian(original):probablyIndonesian(original));
 const key=language+'\u0000'+original;
 const [result,setResult]=useState({key:'',value:'',status:''});
 useEffect(()=>{
  if(!needs)return;
  let active=true;
  if(translated.has(key)){setResult({key,value:translated.get(key),status:''});return()=>{active=false};}
  setResult({key,value:original,status:language==='id'?'Menerjemahkan teks AI tersimpan…':'Translating saved AI text…'});
  requestTranslation(original,language).then(value=>{
    if(active)setResult({key,value,status:''});
  }).catch(()=>{
    if(active)setResult({key,value:original,status:language==='id'?'Terjemahan tidak tersedia; teks asli ditampilkan.':'Translation unavailable; displaying original text.'});
  });
  return()=>{active=false};
 },[language,original,needs,key]);
 return {display:!needs?original:result.key===key?result.value:original,
         status:needs&&result.key===key?result.status:''};
}
