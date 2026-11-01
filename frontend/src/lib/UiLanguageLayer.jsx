import {useEffect} from 'react';
import {useLanguage,translateInterfaceLiteral} from '@/lib/LanguageContext';
import {radarText} from '@/lib/smartRadarI18n';

/**
 * UI-label coverage for older modules still containing literal English copy.
 * Strict dictionary-only translation: no AI calls and no rewriting evidence.
 * Text created by React after a fetch is localized as well.
 */
const sourceSelectors=[
 '[data-i18n-exempt]','[data-original-content]','pre','code','textarea',
 '[contenteditable]','[data-issue-content]','.issue-source-description',
 '.whitespace-pre-wrap','.source-post-text','[data-source-body]',
 '[data-assistant-message]','[data-user-message]'
].join(',');
const ignoredTags=new Set(['SCRIPT','STYLE','NOSCRIPT','CODE','PRE','TEXTAREA','SVG','PATH']);
const attributes=['placeholder','title','aria-label','aria-description','aria-placeholder','data-placeholder','alt'];
// Preserve the English originals across locale toggles and React rerenders.
const originalText=new WeakMap(),lastRenderedText=new WeakMap();
const originalAttributes=new WeakMap(),lastRenderedAttributes=new WeakMap();

export default function UiLanguageLayer(){
 const {language}=useLanguage();
 useEffect(()=>{
  let frame=0;
  const isExempt=element=>!element || element.closest?.(sourceSelectors);
  const translate=value=>{
   const a=translateInterfaceLiteral(value,language);
   if(a!==value)return a;
   if(language!=='id')return value;
   const trimmed=value.trim();
   const b=radarText(language,trimmed);
   if(b!==trimmed){
    return value.slice(0,value.indexOf(trimmed))+b+value.slice(value.indexOf(trimmed)+trimmed.length);
   }
   return value;
  };
  function textNode(node){
   const element=node.parentElement;
   if(!element||ignoredTags.has(element.tagName)||isExempt(element))return;
   const current=node.nodeValue||'';
   if(!originalText.has(node)||current!==lastRenderedText.get(node)){
    originalText.set(node,current);
   }
   const english=originalText.get(node)||'';
   if(!english.trim()||english.length>350)return;
   const intended=translate(english);
   if(current!==intended)node.nodeValue=intended;
   lastRenderedText.set(node,intended);
  }
  function elementAttributes(el){
   if(ignoredTags.has(el.tagName)||isExempt(el))return;
   let originalsForEl=originalAttributes.get(el);
   let lastForEl=lastRenderedAttributes.get(el);
   if(!originalsForEl){originalsForEl={};originalAttributes.set(el,originalsForEl);}
   if(!lastForEl){lastForEl={};lastRenderedAttributes.set(el,lastForEl);}
   for(const name of attributes){
    if(!el.hasAttribute(name))continue;
    const current=el.getAttribute(name)||'';
    if(!(name in originalsForEl)||current!==lastForEl[name])originalsForEl[name]=current;
    const intended=translate(originalsForEl[name]);
    if(current!==intended)el.setAttribute(name,intended);
    lastForEl[name]=intended;
   }
   // UI-only input button text. Never translate typed values or source evidence.
   if(el.tagName==='INPUT'&&['button','submit','reset'].includes(el.type)){
    const current=el.value;
    if(!('buttonValue' in originalsForEl)||current!==lastForEl.buttonValue)originalsForEl.buttonValue=current;
    const next=translate(originalsForEl.buttonValue);
    if(current!==next)el.value=next;
    lastForEl.buttonValue=next;
   }
  }
  function scan(root){
   if(root.nodeType===3){textNode(root);return;}
   if(root.nodeType!==1)return;
   if(ignoredTags.has(root.tagName)||isExempt(root))return;
   elementAttributes(root);
   const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
   let node;
   while((node=walker.nextNode())){
    if(node.nodeType===3)textNode(node);
    else if(node.nodeType===1)elementAttributes(node);
   }
  }
  function refresh(){
   frame=0;
   scan(document.body);
  }
  function schedule(){
   if(!frame)frame=requestAnimationFrame(refresh);
  }
  schedule();
  const observer=new MutationObserver(mutations=>{
   if(mutations.some(m=>m.type==='characterData'||m.type==='childList'||m.type==='attributes'))schedule();
  });
  observer.observe(document.body,{subtree:true,childList:true,characterData:true,
   attributes:true,attributeFilter:attributes});
  return()=>{observer.disconnect();if(frame)cancelAnimationFrame(frame);};
 },[language]);
 return null;
}
