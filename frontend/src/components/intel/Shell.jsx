import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Menu, Plus } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AccessNavigation from '@/components/intel/AccessNavigation';
import { useLanguage } from '@/lib/LanguageContext';
import InterfaceLanguageBridge from '@/components/intel/InterfaceLanguageBridge';
import DemoFeedbackWidget from '@/demo/DemoFeedbackWidget.jsx';
import DemoAccessNavigation from '@/demo/DemoAccessNavigation.jsx';

export default function Shell(){
 const [open,setOpen]=useState(false),[deniedView,setDeniedView]=useState(false),[user,setUser]=useState(null),[access,setAccess]=useState(null),[error,setError]=useState('');
 const location=useLocation(),navigate=useNavigate(),{language,setLanguage,t}=useLanguage();
 const demo=Boolean(window.__BAWASLU_DEMO_REPLICA__);
 const changeLanguage=next=>{
  setLanguage(next);
  if(demo){const params=new URLSearchParams(location.search);params.set('lang',next);
   navigate({pathname:location.pathname,search:'?'+params.toString(),hash:location.hash},{replace:true});}
 };
 const logout=()=>base44.auth.logout(true);
 useEffect(()=>{base44.auth.me().then(setUser).catch(()=>{});base44.functions.invoke('getMyEffectiveAccess',{}).then(r=>setAccess(r.data.access)).catch(e=>setError(e.response?.data?.error||'Unable to load BAWASLU access. Please reload.'))},[]);
 useEffect(()=>{setOpen(false);setDeniedView(false)},[location.pathname]);
 // Allow direct links to different demo modules to carry the language.
 useEffect(()=>{if(!demo)return;const requested=new URLSearchParams(location.search).get('lang');
  if((requested==='id'||requested==='en')&&requested!==language)setLanguage(requested);
 },[demo,location.search]);
 if(error)return <div role="alert" className="p-6">{error}</div>;
 if(!access)return <div className="p-6 text-sm">{t('loading_access')}</div>;
 if(access.status!=='Active')return <div role="alert" className="p-6">{t('inactive_access')}</div>;
 const nav=window.__BAWASLU_DEMO_REPLICA__?<DemoAccessNavigation access={access} user={user}/>:<AccessNavigation access={access} user={user}/>;
 return <><style>{`.intel-sidebar-scroll{scrollbar-width:none;-ms-overflow-style:none}.intel-sidebar-scroll::-webkit-scrollbar{display:none;width:0;height:0}`}</style><InterfaceLanguageBridge language={language}/><div data-intel-shell className={deniedView?'min-h-screen':'min-h-screen flex'}>
  {!deniedView&&<aside className="intel-sidebar-scroll hidden lg:flex lg:flex-col w-[250px] shrink-0 bg-[#801b24] text-white min-h-screen sticky top-0 h-screen overflow-y-auto">{nav}</aside>}
  {!deniedView&&open&&<div className="fixed inset-0 z-40 lg:hidden"><button aria-label={t('close_menu')} onClick={()=>setOpen(false)} className="absolute inset-0 bg-black/50"/><aside className="relative h-full w-[260px] flex flex-col bg-[#801b24] text-white overflow-y-auto">{nav}</aside></div>}
  <div className={deniedView?'min-h-screen':'min-w-0 flex-1'}>
   {!deniedView&&<header data-demo-locale-owned={window.__BAWASLU_DEMO_REPLICA__?"true":undefined} className="h-[76px] bg-white border-b border-[#eadde0] flex items-center justify-between px-5 md:px-9"><div className="flex items-center gap-3"><button onClick={()=>setOpen(true)} className="lg:hidden" aria-label={t('open_menu')}><Menu size={22}/></button><span className="text-[11px] font-bold uppercase tracking-[.18em] text-[#9d5357]">{t('election_supervision_intelligence')}</span></div><div className="flex items-center gap-2"><div className="inline-flex rounded-lg border border-[#d9e2e8] bg-[#f7fafb] p-1"><button type="button" onClick={()=>changeLanguage('en')} aria-pressed={language==='en'} aria-label="English" title="English" className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='en'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>EN</button><button type="button" onClick={()=>changeLanguage('id')} aria-pressed={language==='id'} aria-label="Bahasa Indonesia" title="Bahasa Indonesia" className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='id'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>ID</button></div>{access.permissions?.add_intelligence===true&&<Link to="/add" className="intel-button"><Plus size={16}/><span className="hidden sm:inline">{t('add_intelligence')}</span><span className="sm:hidden">{t('add')}</span></Link>}{!window.__BAWASLU_DEMO_REPLICA__&&<button type="button" onClick={logout} className="intel-ghost" aria-label={t('log_out')}><LogOut size={16}/><span className="hidden md:inline">{t('log_out')}</span></button>}</div></header>}
   <div className="sr-only" data-build-version="146.3">BAWASLU build v146.3</div>
   <main className={deniedView?'min-h-screen flex items-center justify-center p-5 md:p-9':location.pathname==='/'?'max-w-[1600px] mx-auto p-4 md:px-6 md:py-4':'max-w-[1530px] mx-auto p-5 md:p-9'}><Outlet context={{access,setDeniedView}}/></main>
   <footer className="px-5 pb-2 text-[10px] text-slate-400 text-right" aria-label="Build version">v146.3</footer>
  </div>
 </div>{window.__BAWASLU_DEMO_REPLICA__&&<DemoFeedbackWidget/>}</>;
}