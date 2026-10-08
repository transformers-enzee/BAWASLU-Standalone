import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ListFilter, Inbox, Plus, Database, BadgeCheck, Settings, Shield, LockKeyhole, Sparkles, Radio } from 'lucide-react';
const links=[
 ['/', 'Home', LayoutDashboard, 'view_intelligence'],
 ['/watchlist', 'Watchlist', ListFilter, 'view_intelligence'],
 ['/social-listening', 'Social Listening', Radio, 'view_intelligence'],
 ['/inbox', 'Intelligence Inbox', Inbox, 'view_intelligence'],
 ['/assistant', 'BAWASLU Intelligence Assistant', Sparkles, 'view_intelligence'],
 ['/add', 'Add Intelligence', Plus, 'add_intelligence'],
 ['/sources', 'Data Sources', Database, 'view_intelligence'],
 ['/validation', 'Validation', BadgeCheck, 'human_validation'],
 ['/administration', 'Administration', Settings, 'administration']
];
const future=['Command Center','Risk & Early Warning','Action Center','Intelligence & Reporting'];
export default function AccessNavigation({access,user}){
 return <><div className="flex items-center gap-3 px-5 h-[76px] border-b border-white/10"><div className="w-9 h-9 bg-[#bd9d5c] rounded-lg flex items-center justify-center text-[#10293f]"><Shield size={21}/></div><div><div className="font-bold text-[15px] leading-tight tracking-wide">BAWASLU</div><div className="text-[10px] uppercase tracking-[.19em] text-[#9fb6c8]">Intelligence Command</div></div></div>
 <div className="px-4 pt-7 pb-2 text-[10px] font-bold text-[#7793a8] tracking-[.18em] uppercase">Workspace</div>
 <nav className="px-3 space-y-1">{links.filter(([, , ,permission])=>access.permissions?.[permission]===true).map(([path,label,Icon])=><NavLink key={path} to={path} end={path==='/'} className={({isActive})=>`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-[13px] transition-colors ${isActive?'bg-[#27536d] text-white font-semibold':'text-[#b8cad7] hover:bg-white/10 hover:text-white'}`}><Icon size={17}/>{label}</NavLink>)}</nav>
 <div className="px-4 pt-8 pb-2 text-[10px] font-bold text-[#7793a8] tracking-[.18em] uppercase">Future modules</div><div className="px-3 space-y-1">{future.map(x=><div key={x} className="flex items-center justify-between px-3.5 py-2.5 text-[12px] text-[#7793a8]" title="Coming Soon"><span className="flex gap-3 items-center"><LockKeyhole size={15}/>{x}</span><span className="text-[9px]">SOON</span></div>)}</div>
 <div className="mt-auto border-t border-white/10 p-5 text-xs text-[#b8cad7]"><div className="font-semibold text-white truncate">{user?.full_name||user?.email||'Authorized user'}</div><div className="mt-1">Secure workspace · Build 38</div></div></>;
}