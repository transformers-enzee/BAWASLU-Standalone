import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { LogOut, Menu, Plus } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AccessNavigation from '@/components/intel/AccessNavigation';
import { useLanguage } from '@/lib/LanguageContext';

export default function Shell(){
 const [open,setOpen]=useState(false),[deniedView,setDeniedView]=useState(false),[user,setUser]=useState(null),[access,setAccess]=useState(null),[error,setError]=useState('');
 const location=useLocation(),{language,setLanguage,t}=useLanguage();
 const logout=()=>base44.auth.logout(true);
 useEffect(()=>{base44.auth.me().then(setUser).catch(()=>{});base44.functions.invoke('getMyEffectiveAccess',{}).then(r=>setAccess(r.data.access)).catch(e=>setError(e.response?.data?.error||'Unable to load BAWASLU access. Please reload.'))},[]);
 useEffect(()=>{setOpen(false);setDeniedView(false)},[location.pathname]);
 if(error)return <div role="alert" className="p-6">{error}</div>;
 if(!access)return <div className="p-6 text-sm">{t('loading_access')}</div>;
 if(access.status!=='Active')return <div role="alert" className="p-6">{t('inactive_access')}</div>;
 const nav=<AccessNavigation access={access} user={user}/>;
 return <div className={deniedView?'min-h-screen':'min-h-screen flex'}>
  {!deniedView&&<aside className="hidden lg:flex lg:flex-col w-[250px] shrink-0 bg-[#122f46] text-white min-h-screen sticky top-0 h-screen overflow-y-auto">{nav}</aside>}
  {!deniedView&&open&&<div className="fixed inset-0 z-40 lg:hidden"><button aria-label={t('close_menu')} onClick={()=>setOpen(false)} className="absolute inset-0 bg-black/50"/><aside className="relative h-full w-[260px] flex flex-col bg-[#122f46] text-white overflow-y-auto">{nav}</aside></div>}
  <div className={deniedView?'min-h-screen':'min-w-0 flex-1'}>
   {!deniedView&&<header className="h-[76px] bg-white border-b border-[#e4e9ef] flex items-center justify-between px-5 md:px-9"><div className="flex items-center gap-3"><button onClick={()=>setOpen(true)} className="lg:hidden" aria-label={t('open_menu')}><Menu size={22}/></button><span className="text-[11px] font-bold uppercase tracking-[.18em] text-[#7790a2]">{t('election_supervision_intelligence')}</span></div><div className="flex items-center gap-2"><div className="inline-flex rounded-lg border border-[#d9e2e8] bg-[#f7fafb] p-1"><button type="button" onClick={()=>setLanguage('en')} className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='en'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>EN</button><button type="button" onClick={()=>setLanguage('id')} className={'px-2.5 py-1.5 rounded-md text-xs font-semibold '+(language==='id'?'bg-white text-[#163750] shadow-sm':'text-[#718398]')}>ID</button></div>{access.permissions?.add_intelligence===true&&<Link to="/add" className="intel-button"><Plus size={16}/><span className="hidden sm:inline">{t('add_intelligence')}</span><span className="sm:hidden">{t('add')}</span></Link>}<button type="button" onClick={logout} className="intel-ghost" aria-label={t('log_out')}><LogOut size={16}/><span className="hidden md:inline">{t('log_out')}</span></button></div></header>}
   <main className={deniedView?'min-h-screen flex items-center justify-center p-5 md:p-9':'max-w-[1530px] mx-auto p-5 md:p-9'}><Outlet context={{access,setDeniedView}}/></main>
  </div>
 </div>;
}