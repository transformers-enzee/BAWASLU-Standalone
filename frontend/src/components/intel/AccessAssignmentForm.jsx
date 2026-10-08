import { useState } from 'react';
import { Field } from '@/components/intel/Fields';
import AccessJurisdiction from '@/components/intel/AccessJurisdiction';
import AccessPermissions from '@/components/intel/AccessPermissions';
import UserAccessHistory from '@/components/intel/UserAccessHistory';
import { bawasluRoles, scopeForRole, sensitivePermissions } from '@/components/intel/accessRoles';
import { useLanguage } from '@/lib/LanguageContext';
export default function AccessAssignmentForm({edit,setEdit,adminRole,adminProvince,users=[],roles={},labels={},busy,onSave,onCancel}){
 const {t}=useLanguage();
 const [error,setError]=useState('');
 function roleChange(value){const geographic_scope=scopeForRole(value);setEdit(prev=>({...prev,access_role:value,geographic_scope,province:geographic_scope==='Nationwide'?'':adminRole==='Provincial Administrator'?adminProvince:prev.province,regency_city:'',permissions:Object.fromEntries(Object.keys(labels).map(k=>[k,!sensitivePermissions.includes(k)&&!!roles[value]?.permissions?.includes(k)]))}));setError('');}
 function submit(e){
  e.preventDefault();const values=new FormData(e.currentTarget),access_role=String(values.get('access_role')||'');
  if(!bawasluRoles.includes(access_role)){setError(t('choose_role'));return;}
  const geographic_scope=access_role==='Viewer'?String(values.get('geographic_scope')||''):scopeForRole(access_role);
  if(!['Nationwide','Province','Regency/City'].includes(geographic_scope)){setError(t('choose_geographic_scope'));return;}
  const province=geographic_scope==='Nationwide'?'':adminRole==='Provincial Administrator'?adminProvince:String(values.get('province')||'').trim();
  const regency_city=geographic_scope==='Nationwide'?'':String(values.get('regency_city')||'').trim();
  if(geographic_scope!=='Nationwide'&&!province){setError(t('province_required'));return;}
  if(geographic_scope==='Regency/City'&&!regency_city){setError(t('regency_city_required'));return;}
  setError('');onSave({id:edit.id,access_role,geographic_scope,province,regency_city,permissions:edit.permissions,status:String(values.get('status')||'Active')});
 }
 return <form onSubmit={submit} className="intel-card p-6 space-y-5" noValidate>
  <div><h2 className="font-semibold text-lg">{t('access_assignment')} · {edit.full_name||edit.email}</h2><p className="text-sm text-muted-foreground">{edit.email}</p></div>
  {edit.platform_admin&&<p className="text-xs text-muted-foreground">{t('platform_admin_note')}</p>}
  <Field name="access_role" label={t('table_bawaslu_role')} options={bawasluRoles} value={edit.access_role} onChange={roleChange}/>
  <AccessJurisdiction edit={edit} setEdit={setEdit} adminRole={adminRole} adminProvince={adminProvince} users={users} errors={error} clear={()=>setError('')}/>
  <AccessPermissions labels={labels} permissions={edit.permissions} onChange={(key,value)=>setEdit(prev=>({...prev,permissions:{...prev.permissions,[key]:value}}))}/>
  <Field name="status" label={t('bawaslu_account_status')} options={['Active','Inactive']} value={edit.status} onChange={value=>setEdit(prev=>({...prev,status:value}))}/>
  <div className="flex gap-2"><button className="intel-button" disabled={busy}>{busy?t('saving'):t('save_assignment')}</button><button type="button" className="intel-ghost" onClick={onCancel}>{t('cancel')}</button></div>
  <UserAccessHistory userId={edit.id}/>
 </form>;
}