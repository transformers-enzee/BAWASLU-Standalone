import {useEffect,useState} from 'react';
import AssistantAnswer from './AssistantAnswer';
import {useLanguage} from '@/lib/LanguageContext';

// Cached per browser session only; source assessment and history stay untouched.
const translations=new Map();
export default function TranslatedAssistantAnswer({text}){
 const {language}=useLanguage();
 const original=String(text||'');
 const key='id:'+original;
 const [display,setDisplay]=useState(original);
 const [status,setStatus]=useState('');
 useEffect(()=>{
  let active=true;
  if(language!=='id'||!original.trim()){
   setDisplay(original);setStatus('');return()=>{active=false};
  }
  if(translations.has(key)){
   setDisplay(translations.get(key));setStatus('');return()=>{active=false};
  }
  setDisplay(original);setStatus('Menerjemahkan ringkasan tersimpan…');
  const controller=new AbortController();
  const token=window.localStorage.getItem('bawaslu_access_token')||'';
  fetch('/api/presentation/translate',{
   method:'POST',cache:'no-store',signal:controller.signal,
   headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},
   body:JSON.stringify({text:original,language:'id'})
  }).then(async response=>{
   const payload=await response.json();
   if(!response.ok)throw Error(payload.detail||'Terjemahan tidak tersedia');
   return payload.text;
  }).then(value=>{
   if(!active||!value)return;
   translations.set(key,value);setDisplay(value);setStatus('');
  }).catch(error=>{
   if(!active||error.name==='AbortError')return;
   setDisplay(original);setStatus('Terjemahan belum tersedia; teks asli ditampilkan.');
  });
  return()=>{active=false;controller.abort()};
 },[language,original,key]);
 return <div>{status&&<p role="status" className="mb-2 text-xs text-[#60768c]">{status}</p>}<AssistantAnswer text={display}/></div>;
}
