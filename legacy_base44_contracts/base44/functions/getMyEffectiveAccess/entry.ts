import { createClientFromRequest } from 'npm:@base44/sdk@0.8.49';
import { loadProfile } from '../../shared/access.ts';

export default async function(req: Request): Promise<Response> {
 try {
  const b=createClientFromRequest(req);
  const user=await b.auth.me();
  if(!user?.id)return Response.json({error:'Unauthorized'},{status:401});
  const access=await loadProfile(b,user);
  if(access.status!=='Active')return Response.json({error:'BAWASLU access is not active'},{status:403});
  return Response.json({access:{role:access.role,status:access.status,geographic_scope:access.geographic_scope,province:access.province,province_code:access.province_code,regency_city:access.regency_city,regency_city_code:access.regency_city_code,permissions:access.permissions}});
 } catch(e) {
  if(e.code==='ACCESS_RESOLUTION_ERROR')return Response.json({error:'BAWASLU access could not be resolved. Please retry.',code:e.code},{status:503});
   return Response.json({error:e.message},{status:500});
 }
}