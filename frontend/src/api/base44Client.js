const API = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_KEY = 'bawaslu_access_token';

function token(){ return window.localStorage.getItem(TOKEN_KEY) || ''; }
function apiError(status, data){
  const e = new Error(data?.detail || data?.error || `Request failed (${status})`);
  e.status = status; e.data = data; e.response = { status, data: { error: data?.detail || data?.error || e.message } };
  return e;
}
async function request(path, options={}){
  const headers = {...(options.headers||{})};
  if (token()) headers.Authorization = `Bearer ${token()}`;
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const r = await fetch(`${API}${path}`, {...options, headers});
  let data={}; try{ data=await r.json(); }catch{}
  if(!r.ok) throw apiError(r.status,data);
  return data;
}

export const base44 = {
  app:{ getPublicSettings:()=>request('/api/public-settings') },
  auth:{
    me:()=>request('/api/auth/me'),
    async loginViaEmailPassword(email,password){ const r=await request('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})}); window.localStorage.setItem(TOKEN_KEY,r.access_token); return r; },
    async register({email,password}){ sessionStorage.setItem('bawaslu_pending_email',email); sessionStorage.setItem('bawaslu_pending_password',password); return request('/api/auth/register',{method:'POST',body:JSON.stringify({email,password})}); },
    async verifyOtp({email}){ const password=sessionStorage.getItem('bawaslu_pending_password')||''; const r=await request('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})}); window.localStorage.setItem(TOKEN_KEY,r.access_token); sessionStorage.removeItem('bawaslu_pending_password'); return r; },
    resendOtp:async()=>({ok:true}),
    setToken:(v)=>window.localStorage.setItem(TOKEN_KEY,v),
    async logout(redirect){ try{await request('/api/auth/logout',{method:'POST'});}catch{} window.localStorage.removeItem(TOKEN_KEY); if(redirect) window.location.href='/login'; },
    redirectToLogin:(returnTo='/')=>{ window.location.href=`/login?returnTo=${encodeURIComponent(returnTo)}`; },
    loginWithProvider:()=>{ throw new Error('Google login is not configured in standalone v0.1. Use email/password.'); },
    resetPasswordRequest:async()=>{ throw new Error('Password reset email is not configured in standalone v0.1. Contact an administrator.'); },
    resetPassword:async()=>{ throw new Error('Password reset is not configured in standalone v0.1. Contact an administrator.'); },
  },
  externalImport:{
    async downloadCampaign(campaignId){
      const token=window.localStorage.getItem(TOKEN_KEY)||'';
      const response=await fetch(API+'/api/social-listening/campaign/'+encodeURIComponent(campaignId)+'/export.csv',{headers:{Authorization:'Bearer '+token}});
      if(!response.ok)throw apiError(response.status,await response.json().catch(()=>({})));
      const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');
      a.href=url;a.download='bawaslu_campaign_'+campaignId+'_evidence.csv';document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
    },
    async repairMetrics(campaignId){return request('/api/social-listening/campaign/'+encodeURIComponent(campaignId)+'/repair-external-metrics',{method:'POST'});},
    async start(campaignId,file){
      const form=new FormData();form.append('file',file);
      return request('/api/social-listening/external-import/start?campaign_id='+encodeURIComponent(campaignId),{method:'POST',body:form});
    },
    async status(runId){return request('/api/social-listening/external-import/status/'+encodeURIComponent(runId));},
    async preview(campaignId,file){
      const form=new FormData();form.append('file',file);
      return request('/api/social-listening/external-import/preview?campaign_id='+encodeURIComponent(campaignId),{method:'POST',body:form});
    }
  },
  functions:{
    async invoke(name,payload={}){
      const path = ['intelligence','registry'].includes(name) ? `/api/functions/${name}` : `/api/functions/${name}`;
      const data = await request(path,{method:'POST',body:JSON.stringify(payload)});
      return {data};
    }
  },
  integrations:{ Core:{
    async UploadPrivateFile({file}){ const form=new FormData(); form.append('file',file); return request('/api/upload',{method:'POST',body:form}); }
  }}
};
