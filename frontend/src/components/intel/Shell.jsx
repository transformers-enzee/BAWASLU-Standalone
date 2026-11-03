import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { LogOut, Menu, Plus } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AccessNavigation from '@/components/intel/AccessNavigation';
import { useLanguage } from '@/lib/LanguageContext';
import InterfaceLanguageBridge from '@/components/intel/InterfaceLanguageBridge';
import DemoGuide from '@/demo/DemoGuide.jsx';
import DemoAccessNavigation from '@/demo/DemoAccessNavigation.jsx';

export default function Shell(){
 const [open,setOpen]=useState(false),[deniedView,setDeniedView]=useState(false),[user,setUser]=useState(null),[access,setAccess]=useState(null),[error,setError]=useState('');
 const location=useLocation(),{language,setLanguage,t}=useLanguage();
 const logout=()=>{if(window.__BAWASLU_DEMO_REPLICA__){sessionStorage.removeItem('bawaslu_demo_training_session');window.location.assign('/demo');return;}return base44.auth.logout(true)};
 useEffect(()=>{base44.auth.me().then(setUser).catch(()=>{});base44.functions.invoke('getMyEffectiveAccess',{}).then(r=>setAccess(r.data.access)).catch(e=>setError(e.response?.data?.error||'Unable to load BAWASLU access. Please reload.'))},[]);
 useEffect(()=>{setOpen(false);setDeniedView(false)},[location.pathname]);
 if(error)return <div role="alert" className="p-6">{error}</div>;
 if(!access)return <div className="p-6 text-sm">{t('loading_access')}</div>;
 if(access.status!=='Active')return <div role="alert" className="p-6">{t('inactive_access')}</div>;
 const nav=window.__BAWASLU_DEMO_REPLICA__?<DemoAccessNavigation access={access} user={user}/>:<AccessNavigation access={access} user={user}/>;
 return <><InterfaceLanguageBridge language={language}/><div data-intel-shell className={deniedView?'min-h-screen':'min-h-screen flex'}>
  {!deniedView&&<aside className="hidden lg:flex lg:flex-col w-[250px] shrink-0 bg-[#801b24] text-white min-h-screen sticky top-0 h-screen overflow-y-auto">{nav}</aside>}
  {!deniedView&&open&&<div className="fixed inset-0 z-40 lg:hidden"><button aria-label={t('close_menu')} onClick={()=>setOpen(false)} className="absolute inset-0 bg-black/50"/><aside className="relative h-full w-[260px] flex flex-col bg-[#801b24] text-white overflow-y-auto">{nav}</aside></div>}
  <div className={deniedView?'min-h-screen':'min-w-0 flex-1'}>
   {!deniedView&&<header className="h-[76px] bg-white border-b border-[#eadde0] flex items-center justify-between px-5 md:px-9"><div className="flex items-center gap-3"><button onClick={()=>setOpen(true)} className="lg:hidden" aria-label={t('open_menu')}><Menu size={22}/></button><span className="text-[11px] font-bold uppercase tracking-[.18em] text-[#9d5357]">{t('election_supervision_intelligence')}</span></div><div className="flex items-center gap-2"><div className="inline-flex rounded-lg border border-[#d9e2e8] bg-[#f7fafb] p-1"><button type="button" onClick={()=>setLanguage('en')} aria-pressed={language==='en'} aria-label="English" title="English" className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='en'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>EN</button><button type="button" onClick={()=>setLanguage('id')} aria-pressed={language==='id'} aria-label="Bahasa Indonesia" title="Bahasa Indonesia" className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='id'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>ID</button></div>{access.permissions?.add_intelligence===true&&<Link to="/add" className="intel-button"><Plus size={16}/><span className="hidden sm:inline">{t('add_intelligence')}</span><span className="sm:hidden">{t('add')}</span></Link>}<button type="button" onClick={logout} className="intel-ghost" aria-label={t('log_out')}><LogOut size={16}/><span className="hidden md:inline">{t('log_out')}</span></button></div></header>}
   <div className="sr-only" data-build-version="127.7">BAWASLU build v127.7</div>
   <main className={deniedView?'min-h-screen flex items-center justify-center p-5 md:p-9':location.pathname==='/'?'max-w-[1600px] mx-auto p-4 md:px-6 md:py-4':'max-w-[1530px] mx-auto p-5 md:p-9'}><Outlet context={{access,setDeniedView}}/></main>
   <footer className="px-5 pb-2 text-[10px] text-slate-400 text-right" aria-label="Build version">v127.7</footer>
  </div>
 </div>{window.__BAWASLU_DEMO_REPLICA__&&<DemoGuide/>}</>;
}