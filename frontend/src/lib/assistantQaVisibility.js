/** v149.6: Display gate only. Backend authorization remains authoritative. */
export function canShowAssistantQa(access,{demo=false}={}){
 return !demo&&access?.status==='Active'&&
  access.permissions?.view_intelligence===true&&
  access.permissions?.administration===true&&
  ['National Administrator','Provincial Administrator'].includes(access.role);
}
