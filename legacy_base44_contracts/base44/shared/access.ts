import { geographicAllowed, provinceByName, regencyByName } from './geography.ts';
export const permissionLabels = {
 view_intelligence:'View Intelligence', add_intelligence:'Add Intelligence', edit_intelligence:'Edit Intelligence',
 review_ai_suggestions:'Review AI Suggestions', human_validation:'Human Validation', verify_evidence:'Verify Evidence',
 manage_watchlist:'Manage Watchlist', upload_evidence:'Upload Supporting Evidence', manage_users:'Manage Users & Access', administration:'Administration'
};
// Role definitions are centralized here so default authority and jurisdiction can be refined independently.
const view=['view_intelligence'];
const analyst=[...view,'add_intelligence','edit_intelligence','review_ai_suggestions','upload_evidence'];
const manager=[...analyst,'human_validation','verify_evidence','manage_watchlist','manage_users','administration'];
export const roleDefinitions={
 'National Administrator':{scope:'Nationwide',permissions:Object.keys(permissionLabels)},
 'National Leadership':{scope:'Nationwide',permissions:view},
 'National Analyst':{scope:'Nationwide',permissions:[...analyst,'human_validation','verify_evidence','manage_watchlist']},
 'Provincial Administrator':{scope:'Province',permissions:manager},
 'Provincial Analyst':{scope:'Province',permissions:analyst},
 'Regency/City Officer':{scope:'Regency/City',permissions:analyst},
 'Regency/City Analyst':{scope:'Regency/City',permissions:analyst},
 Viewer:{scope:'Selectable',permissions:view}
};
export const national=['National Administrator','National Leadership','National Analyst'];
export function defaultPermissions(role){return Object.fromEntries(Object.keys(permissionLabels).map(k=>[k,(roleDefinitions[role]?.permissions||[]).includes(k)]));}
export function profile(user,grant){const role=grant?.access_role||'Viewer';return {id:user.id,name:user.full_name||user.email,role,province:grant?.province||'',regency_city:grant?.regency_city||'',province_code:provinceByName(grant?.province)?.code||'',regency_city_code:regencyByName(grant?.regency_city,provinceByName(grant?.province)?.code)?.code||'',geographic_scope:grant?.geographic_scope||(role==='Viewer'?(grant?.regency_city?'Regency/City':'Province'):roleDefinitions[role]?.scope)||'Province',status:grant?.status||(grant?'Active':'Inactive'),permissions:grant?.permissions&&Object.keys(grant.permissions).length?grant.permissions:defaultPermissions(role)};}
export class AccessResolutionError extends Error { code='ACCESS_RESOLUTION_ERROR'; }
export async function loadProfile(b,user){
 if(!user?.id){console.error('BAWASLU_ACCESS_SCOPE',{state:'assignment_resolution_error',reason:'missing_authenticated_user_id'});throw new AccessResolutionError('Authenticated user ID is missing');}
 let grants;
 try{grants=await b.asServiceRole.entities.AccessGrant.filter({user_id:user.id});}
 catch(e){console.error('BAWASLU_ACCESS_SCOPE',{state:'assignment_resolution_error',user_id:user.id,reason:String(e?.message||e)});throw new AccessResolutionError('BAWASLU assignment could not be resolved');}
 if(grants.length>1){console.error('BAWASLU_ACCESS_SCOPE',{state:'assignment_resolution_error',user_id:user.id,reason:'multiple_assignments'});throw new AccessResolutionError('BAWASLU assignment is ambiguous');}
 const grant=grants[0];
 if(!grant||grant.status==='Inactive'){
  console.info('BAWASLU_ACCESS_SCOPE',{state:'no_active_assignment',user_id:user.id,grant_id:grant?.id||null});
  return profile(user,grant?{...grant,status:'Inactive'}:null);
 }
 if(grant.status!==undefined&&grant.status!=='Active'){
  console.error('BAWASLU_ACCESS_SCOPE',{state:'assignment_resolution_error',user_id:user.id,grant_id:grant.id,reason:'invalid_status'});
  throw new AccessResolutionError('BAWASLU assignment status could not be resolved');
 }
 const p=profile(user,grant);
 if(!['Nationwide','Province','Regency/City'].includes(p.geographic_scope)||p.geographic_scope!=='Nationwide'&&(!p.province_code||p.regency_city&&!p.regency_city_code||p.geographic_scope==='Regency/City'&&!p.regency_city_code)){
  console.error('BAWASLU_ACCESS_SCOPE',{state:'assignment_resolution_error',user_id:user.id,grant_id:grant.id,reason:'invalid_canonical_geography'});
  throw new AccessResolutionError('BAWASLU assignment geography could not be resolved');
 }
 console.info('BAWASLU_ACCESS_SCOPE',{state:'resolved',user_id:user.id,grant_id:grant.id,role:p.role,scope:p.geographic_scope,province_code:p.province_code||null});
 return p;
}
export function has(p,key){return p.status==='Active'&&p.permissions?.[key]===true;}
export function allowed(p,record){if(record?.intelligence_id)return geographicAllowed(p,record);if(p.status!=='Active')return false;if(p.geographic_scope==='Nationwide')return true;if(!p.province||p.province!==record.province)return false;return p.geographic_scope==='Regency/City'?!!p.regency_city&&p.regency_city===record.regency_city:!p.regency_city||p.regency_city===record.regency_city;}
export function canSubmit(p){return has(p,'add_intelligence');}
export function canReview(p){return has(p,'human_validation');}
export function canAdmin(p){return has(p,'manage_users')&&has(p,'administration');}
export function scope(p,records){return records.filter(x=>allowed(p,x));}
export function clean(v,n=5000){return typeof v==='string'?v.trim().slice(0,n):'';}
export function audit(base44,p,subject_type,subject_id,action,changes={}){return base44.asServiceRole.entities.AuditEvent.create({subject_type,subject_id,action,actor_id:p.id,actor_name:p.name,changes,occurred_at:new Date().toISOString()});}