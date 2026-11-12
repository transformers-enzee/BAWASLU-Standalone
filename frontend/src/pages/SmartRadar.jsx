import {useEffect,useRef,useState} from 'react';
import ManagementBriefings from '@/components/intel/ManagementBriefings';
import {useLanguage} from '@/lib/LanguageContext';
/** Approved Smart Radar V6.2 design, mounted without restyling.
 * The same-origin frame reads authorised staging APIs, so no synthetic
 * prototype data or officer decisions are stored in the browser.
 * The global Shell owns login, navigation and responsive workspace layout.
 */
export default function SmartRadar(){
 const {language}=useLanguage();
 const frameRef=useRef(null);
 const [mode,setMode]=useState('radar');
 const sendLocale=()=>frameRef.current?.contentWindow?.postMessage(
    {type:'BAWASLU_UI_LANGUAGE',language},window.location.origin);
 useEffect(()=>{sendLocale();},[language]);
 return <section aria-label="Command Centre" className="-mx-5 -my-5 md:-mx-9 md:-my-9 bg-[#faf9f8]">
  <div data-i18n-exempt="true" className="briefing-no-print flex gap-2 border-b bg-white px-5 py-3" role="group" aria-label="Command Centre workspace">
  <button type="button" aria-pressed={mode==='radar'} onClick={()=>setMode('radar')} className={'rounded-lg px-3 py-2 text-sm font-semibold '+(mode==='radar'?'bg-[#801b24] text-white':'text-[#516477] hover:bg-[#f2f5f7]')}>Command Centre</button>
  <button type="button" aria-pressed={mode==='reports'} onClick={()=>setMode('reports')} className={'rounded-lg px-3 py-2 text-sm font-semibold '+(mode==='reports'?'bg-[#801b24] text-white':'text-[#516477] hover:bg-[#f2f5f7]')}>{language==='id'?'Laporan & Ringkasan':'Reports & Briefings'}</button>
 </div>
 {mode==='reports'?<ManagementBriefings/>:<iframe ref={frameRef} onLoad={sendLocale} title="BAWASLU Command Centre" src={/^\/demo(?:\/|$)/.test(window.location.pathname)?"/demo/smart-radar.html?build=130.0":"/ui-freeze/smart-radar-v6_2.html?build=128.4"}
   className="block w-full border-0 bg-[#faf9f8]"
   style={{height:'calc(100vh - 76px)',minHeight:640}}/>}
 </section>;
}
