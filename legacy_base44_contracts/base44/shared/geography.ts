import regions from './regions.json' with { type: 'json' };

export const jurisdictionTypes=['National','Province','Regency / City','Multi-Region','Unresolved'];
const provinces=regions.provinces;
const regencies=regions.regencies;
export const provinceByName=name=>provinces.find(x=>x.name===name);
export const provinceByCode=code=>provinces.find(x=>x.code===code);
export const regencyByName=(name,provinceCode)=>regencies.find(x=>x.name===name&&x.province_code===provinceCode);
export const regencyByCode=(code,provinceCode)=>regencies.find(x=>x.code===code&&x.province_code===provinceCode);
export function canonicalAssignment(value){
 const province=provinceByCode(value?.province_code);
 if(!province)throw Error('Choose a valid Indonesian province');
 if(value?.regency_city_code){const city=regencyByCode(value.regency_city_code,province.code);if(!city)throw Error('Choose a Regency / City in the selected Province');return {province_code:province.code,province:province.name,regency_city_code:city.code,regency_city:city.name};}
 return {province_code:province.code,province:province.name,regency_city_code:'',regency_city:''};
}
export function parseJurisdiction(data){
 const type=data?.jurisdiction_type;
 if(!jurisdictionTypes.includes(type))throw Error('Choose a jurisdiction classification');
 if(type==='National'||type==='Unresolved')return {jurisdiction_type:type,province:'',regency_city:'',province_code:'',regency_city_code:'',geographic_assignments:[]};
 const values=type==='Multi-Region'?data.geographic_assignments:[{province_code:data.province_code,regency_city_code:data.regency_city_code}];
 if(!Array.isArray(values)||values.length>(type==='Multi-Region'?30:1))throw Error('Choose valid geographic assignments');
 const assignments=values.map(canonicalAssignment);
 if(type==='Multi-Region'&&assignments.length<2)throw Error('Choose at least two distinct geographic assignments');
 if(type==='Regency / City'&&!assignments[0]?.regency_city_code)throw Error('Regency / City is required');
 if(type==='Multi-Region'&&new Set(assignments.map(x=>`${x.province_code}:${x.regency_city_code}`)).size!==assignments.length)throw Error('Remove duplicate geographic assignments');
 return {jurisdiction_type:type,province:assignments.length===1?assignments[0].province:'',regency_city:assignments.length===1?assignments[0].regency_city:'',province_code:assignments.length===1?assignments[0].province_code:'',regency_city_code:assignments.length===1?assignments[0].regency_city_code:'',geographic_assignments:assignments};
}
export function canAssignJurisdiction(profile,geo){
 if(profile.geographic_scope==='Nationwide')return true;
 if(['Unresolved','National'].includes(geo.jurisdiction_type))return false;
 const assignments=geo.jurisdiction_type==='Multi-Region'?geo.geographic_assignments:[{province_code:geo.province_code,regency_city_code:geo.regency_city_code}];
 const profileProvince=provinceByName(profile.province),profileCity=profileProvince&&regencyByName(profile.regency_city,profileProvince.code);
 return assignments.length>0&&assignments.every(x=>{
  if(profile.geographic_scope==='Regency/City'||profile.regency_city){if(!profileCity||x.regency_city_code!==profileCity.code)return false;}
  return geographicAllowed(profile,{intelligence_id:'assignment',jurisdiction_confirmed:true,jurisdiction_type:x.regency_city_code?'Regency / City':'Province',province_code:x.province_code,regency_city_code:x.regency_city_code});
 });
}
export function geographicAllowed(profile,record){
 if(profile.status!=='Active')return false;
 const nationwide=profile.geographic_scope==='Nationwide';
 if(!record.jurisdiction_confirmed||!jurisdictionTypes.includes(record.jurisdiction_type)||record.jurisdiction_type==='Unresolved')return nationwide&&(profile.role==='National Administrator'||profile.permissions?.human_validation===true);
 if(nationwide)return true;
 if(record.jurisdiction_type==='National')return false;
 const province=provinceByCode(profile.province_code)||provinceByName(profile.province);
 if(!province)return false;
 const city=profile.regency_city_code?regencyByCode(profile.regency_city_code,province.code):regencyByName(profile.regency_city,province.code);
 if(profile.geographic_scope==='Regency/City'&&!city)return false;
 const assignments=record.jurisdiction_type==='Multi-Region'?record.geographic_assignments:[{province_code:record.province_code,regency_city_code:record.regency_city_code}];
 return Array.isArray(assignments)&&assignments.some(x=>{
  if(x.province_code!==province.code||!provinceByCode(x.province_code))return false;
  if(x.regency_city_code&&!regencyByCode(x.regency_city_code,province.code))return false;
  if(profile.geographic_scope==='Regency/City')return !x.regency_city_code||x.regency_city_code===city.code;
  if(profile.regency_city)return !!city&&(!x.regency_city_code||x.regency_city_code===city.code);
  return true;
 });
}