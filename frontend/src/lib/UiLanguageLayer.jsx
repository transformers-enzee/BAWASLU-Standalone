import {useEffect} from 'react';
import {useLanguage,translateInterfaceLiteral} from '@/lib/LanguageContext';
import {radarText} from '@/lib/smartRadarI18n';

// Translate presentation labels; never mutate source posts, evidence or editable notes.
const excluded=[
 '[data-i18n-exempt]','[data-original-content]','pre','code','textarea','[contenteditable]',
 '[data-issue-content]','.issue-source-description','.whitespace-pre-wrap',
 '.source-post-text','[data-source-body]','[data-user-message]',
 '[data-post-text]','[data-evidence-text]','.original-post-body'
].join(',');
const ignoredTags=new Set(['SCRIPT','STYLE','NOSCRIPT','CODE','PRE','TEXTAREA','PATH','DEFS','CLIPPATH']);
const attributes=['placeholder','title','aria-label','aria-description','aria-placeholder','data-placeholder','alt'];
const originals=new WeakMap(),lastRendered=new WeakMap(),savedAttributes=new WeakMap(),lastAttributes=new WeakMap();
const requested=new WeakMap();
export default function UiLanguageLayer(){
 const {language}=useLanguage();
 useEffect(()=>{
  let frame=0,active=true;
  const fallback=window.BAWASLUUiTranslator;
  if(language==='id')fallback?.resetFailures();
  const skip=el=>!el||el.closest?.(excluded)||(window.__BAWASLU_DEMO_REPLICA__&&Boolean(el.closest?.('[data-demo-locale-owned]')));
  function literal(value){
   const translated=translateInterfaceLiteral(value,language);
   if(translated!==value||language!=='id')return translated;
   const trimmed=value.trim(),fromRadar=radarText('id',trimmed);
   return fromRadar===trimmed?value:value.replace(trimmed,fromRadar);
  }
  function textNode(node){
   const parent=node.parentElement;
   if(!parent||ignoredTags.has(parent.tagName)||skip(parent))return;
   const now=node.nodeValue||'';
   if(!originals.has(node)||now!==lastRendered.get(node))originals.set(node,now);
   const source=originals.get(node)||'';
   if(!source.trim()||source.length>1800)return;
   const next=literal(source);
   if(now!==next)node.nodeValue=next;
   lastRendered.set(node,next);
   if(language!=='id'){requested.delete(node);return;}
   if(next!==source||!fallback?.suitable(source))return;
   if(requested.get(node)===source)return;
   requested.set(node,source);
   fallback.request(source,value=>{
    if(!active||!node.isConnected||originals.get(node)!==source||!value)return;
    node.nodeValue=value;lastRendered.set(node,value);
   });
  }
  function element(el){
   if(ignoredTags.has(el.tagName)||skip(el))return;
   let saved=savedAttributes.get(el),last=lastAttributes.get(el);
   if(!saved){saved={};savedAttributes.set(el,saved);}
   if(!last){last={};lastAttributes.set(el,last);}
   for(const name of attributes){
    if(!el.hasAttribute(name))continue;
    const now=el.getAttribute(name)||'';
    if(!(name in saved)||now!==last[name])saved[name]=now;
    const source=saved[name],next=literal(source);
    if(now!==next)el.setAttribute(name,next);
    last[name]=next;
    if(language!=='id'||next!==source||!fallback?.suitable(source))continue;
    const key=name+':requested';
    if(last[key]===source)continue;
    last[key]=source;
    fallback.request(source,value=>{
     if(!active||!el.isConnected||saved[name]!==source||!value)return;
     el.setAttribute(name,value);last[name]=value;
    });
   }
   if(el.tagName==='INPUT'&&['button','submit','reset'].includes(el.type)){
    const now=el.value;
    if(!('buttonValue' in saved)||now!==last.buttonValue)saved.buttonValue=now;
    const next=literal(saved.buttonValue);
    if(now!==next)el.value=next;
    last.buttonValue=next;
   }
  }
  function sendLocale(iframe){
   try{iframe.contentWindow?.postMessage({type:'BAWASLU_UI_LANGUAGE',language},location.origin)}catch(_){}
  }
  function scan(){
   frame=0;if(!document.body)return;
   const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
   let node;
   while((node=walker.nextNode())){
    if(node.nodeType===3)textNode(node);
    else if(node.nodeType===1)element(node);
   }
   document.querySelectorAll('iframe[src*="/ui-freeze/"],iframe[src*="/demo/"]').forEach(sendLocale);
  }
  function schedule(){if(active&&!frame)frame=requestAnimationFrame(scan);}
  const oldAlert=window.alert,oldConfirm=window.confirm;
  window.alert=message=>oldAlert.call(window,literal(String(message??'')));
  window.confirm=message=>oldConfirm.call(window,literal(String(message??'')));
  const iframeLoad=event=>{if(event.target?.tagName==='IFRAME')sendLocale(event.target)};
  document.addEventListener('load',iframeLoad,true);
  const observer=new MutationObserver(schedule);
  observer.observe(document.body,{subtree:true,characterData:true,childList:true,attributes:true,attributeFilter:attributes});
  schedule();
  return()=>{
   active=false;observer.disconnect();document.removeEventListener('load',iframeLoad,true);
   window.alert=oldAlert;window.confirm=oldConfirm;
   if(frame)cancelAnimationFrame(frame);
  };
 },[language]);
 return null;
}
