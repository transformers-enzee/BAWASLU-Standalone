import { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { registry, useRegistry } from '@/components/intel/useIntel';
import { Notice, err } from '@/components/intel/Fields';
import CategoryManager from '@/components/intel/CategoryManager';
import AccessAssignmentForm from '@/components/intel/AccessAssignmentForm';
import { useLanguage } from '@/lib/LanguageContext';

export default function Administration(){
 const {t,label}=useLanguage();
 const {access}=useOutletContext();const mayManage=access.permissions?.manage_users===true;
 const [users,setUsers]=useState([]),[denied,setDenied]=useState(false),[loading,setLoading]=useState(true),[edit,setEdit]=useState(null);
 const [adminRole,setAdminRole]=useState(''),[adminProvince,setAdminProvince]=useState(''),[roles,setRoles]=useState({}),[labels,setLabels]=useState({});
 const [search,setSearch]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('');const {categories,refresh}=useRegistry();
 useEffect(()=>{if(!mayManage){setLoading(false);return}registry('users').then(r=>{setUsers(r.users);setAdminRole(r.administrator_role);setAdminProvince(r.administrator_province);setRoles(r.roles);setLabels(r.permission_labels)}).catch(()=>setDenied(true)).finally(()=>setLoading(false))},[mayManage]);
 async function save(assignment){setBusy(true);setMessage('');try{const result=await registry('setUser',assignment,assignment.id);setUsers(prev=>prev.map(u=>u.id===assignment.id?result.user:u));setEdit(null);setMessage(t('assignment_saved'))}catch(e){setMessage(err(e))}finally{setBusy(false)}}
 const visible=users.filter(u=>`${u.full_name||''} ${u.email} ${u.access_role} ${u.province} ${u.regency_city}`.toLowerCase().includes(search.toLowerCase()));
 const location=u=>u.geographic_scope==='Nationwide'?t('nationwide'):`${u.province||t('unassigned')}${u.regency_city?' / '+u.regency_city:u.geographic_scope==='Province'?' / '+t('all_regencies_cities'):''}`;
 return <div className="space-y-7">
  <div><p className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('governance')}</p><h1 className="intel-heading">{t('user_access_management')}</h1><p className="text-sm text-[#77899b] mt-2">{t('user_access_intro')}</p></div>
  <Notice error={message&&message!==t('assignment_saved')?message:''}/>{message===t('assignment_saved')&&<p role="status" className="text-sm text-green-700">{message}</p>}
  {!mayManage?<p className="intel-card p-6 text-sm">{t('manage_users_required')}</p>:loading?<p className="text-sm text-muted-foreground">{t('loading_generic')}</p>:denied?<p className="intel-card p-6 text-sm">{t('manage_admin_required')}</p>:<section className="intel-card overflow-x-auto">
   <div className="p-5 flex flex-wrap gap-3 justify-between items-center"><h2 className="font-semibold">{t('user_access')}</h2><input className="intel-input max-w-xs" aria-label={t('search_users')} placeholder={t('search_users')} value={search} onChange={e=>setSearch(e.target.value)}/></div>
   <table className="intel-table min-w-[900px]"><thead><tr>{[t('name'),'Email',t('table_bawaslu_role'),t('table_geographic_scope'),t('table_reviewer_authority'),t('table_status'),t('table_last_updated'),t('table_actions')].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{visible.map(u=><tr key={u.id}>
    <td>{u.full_name||'—'}</td><td>{u.email}</td><td>{label(u.access_role)}</td><td>{location(u)}</td><td>{u.permissions?.human_validation?t('yes'):t('no')}</td><td>{label(u.status)}</td><td>{u.updated_date?new Date(u.updated_date).toLocaleDateString('en-GB'):'—'}</td><td><button className="text-[#146a8b] font-semibold" onClick={()=>{setEdit({...u});setMessage('')}}>{t('assign')}</button></td>
   </tr>)}</tbody></table>{!visible.length&&<p className="p-5 text-sm text-muted-foreground">{t('no_users_found')}</p>}
  </section>}
  {mayManage&&edit&&<AccessAssignmentForm key={edit.id} edit={edit} setEdit={setEdit} adminRole={adminRole} adminProvince={adminProvince} users={users} roles={roles} labels={labels} busy={busy} onSave={save} onCancel={()=>setEdit(null)}/>}
  <CategoryManager categories={categories} refresh={refresh} authorized={access.role==='National Administrator'&&access.permissions?.administration===true}/>
 </div>;
}