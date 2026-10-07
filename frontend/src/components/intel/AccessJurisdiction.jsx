import { Field } from '@/components/intel/Fields';
import regions from '@/components/intel/regions.json';
export default function AccessJurisdiction({edit,setEdit,adminRole,adminProvince,users,errors,clear}){
 const viewer=edit.access_role==='Viewer',scope=edit.geographic_scope;
 const provinceOptions=[...new Set([...regions.provinces.map(p=>p.name),...users.map(u=>u.province),edit.province].filter(Boolean))].sort();
 const province=adminRole==='Provincial Administrator'?adminProvince:edit.province;
 const code=regions.provinces.find(p=>p.name===province)?.code;
 const cityOptions=[...new Set([...regions.regencies.filter(r=>r.province_code===code).map(r=>r.name),...users.filter(u=>u.province===province).map(u=>u.regency_city),edit.regency_city].filter(Boolean))].sort();
 const change=(patch)=>{setEdit(prev=>({...prev,...patch}));clear()};
 return <div className="grid md:grid-cols-3 gap-4">
  {viewer?<Field name="geographic_scope" label="Geographic scope" options={adminRole==='Provincial Administrator'?['Province','Regency/City']:['Nationwide','Province','Regency/City']} value={scope} onChange={v=>change({geographic_scope:v,province:v==='Nationwide'?'':province,regency_city:''})}/>:<div><span className="intel-label">Geographic scope</span><p className="intel-input">{scope==='Nationwide'?'National':scope}</p></div>}
  {scope&&scope!=='Nationwide'&&(adminRole==='Provincial Administrator'?<div><span className="intel-label">Province *</span><p className="intel-input">{adminProvince}</p></div>:<Field name="province" label="Province *" options={provinceOptions} value={edit.province} onChange={v=>change({province:v,regency_city:''})}/>)}
  {scope&&scope!=='Nationwide'&&<Field name="regency_city" label={`Regency / City${scope==='Regency/City'?' *':' (optional)'}`} options={cityOptions} value={edit.regency_city} onChange={v=>change({regency_city:v})}/>}
  {errors&&<p role="alert" className="text-sm text-destructive md:col-span-3">{errors}</p>}
  {scope==='Province'&&!edit.regency_city&&<p className="text-xs text-muted-foreground md:col-span-3">Blank Regency/City means all Regency/Cities in the assigned Province.</p>}
 </div>;
}