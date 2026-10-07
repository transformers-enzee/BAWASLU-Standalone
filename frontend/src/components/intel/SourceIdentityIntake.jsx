import { useEffect, useState } from 'react';
import { intel } from './useIntel';
import { observedPublisherFromUrl } from './observedPublisher';

export default function SourceIdentityIntake({url,content}) {
  const [state,setState]=useState({loading:false,result:null,error:''});
  const ready=Boolean(content?.trim().length>=80);
  const observed=observedPublisherFromUrl(url).handle;
  useEffect(()=>{
    if(!url){setState({loading:false,result:null,error:''});return;}
    let active=true;
    setState({loading:true,result:null,error:''});
    const timer=setTimeout(()=>{
      intel('resolveSourceIdentity',{source_url:url,original_content:content||''})
        .then(result=>{if(active)setState({loading:false,result,error:''})})
        .catch(e=>{if(active)setState({loading:false,result:null,error:e.response?.data?.error||e.message})});
    },400);
    return ()=>{active=false;clearTimeout(timer)};
  },[url,content]);
  if(!url)return null;
  const {loading,result,error}=state;
  return <section className="rounded-lg border border-[#dce3ec] p-4 space-y-2" aria-live="polite">
    <h3 className="text-xs uppercase tracking-wider font-bold text-[#42657a]">SOURCE IDENTITY</h3>
    {(observed||result?.observed_publisher_handle)&&<p className="text-sm">Observed publisher: {observed||result.observed_publisher_handle}</p>}
    {loading?<p className="text-sm">Registered account comparison: Checking...</p>:error?<><p className="text-sm text-[#a04724]">Registered account comparison: Could not complete. Retry before relying on this comparison.</p><p className="text-sm">Identity status: UNRESOLVED</p></>:result?.matched_account?<>
      <p className="text-sm">Registered account comparison: Exact match</p>
      <p className="text-sm font-semibold">Identity status: {result.identity.status}</p>
      <p className="text-sm">{result.matched_entity.name} · {result.matched_account.handle||result.matched_account.url}</p>
      <p className="text-xs text-[#617789]">Match basis: {result.match_basis}</p>
      <p className="text-xs text-[#617789]">{result.identity.status==='REGISTERED_ACCOUNT_CONFIRMED'?'Registered-account provenance confirmed by strict server checks. This does not verify the post content.':'Registered URL match observed; strict ownership checks have not confirmed provenance. Submission can continue unresolved. '+(!ready?'Paste at least 80 characters of original post content to complete the existing strict check.':'')}</p>
    </>:<>
      <p className="text-sm">Registered account comparison: No exact match</p>
      <p className="text-sm font-semibold">Identity status: UNRESOLVED</p>
      <p className="text-xs text-[#617789]">No confirmed registered-account match was found.</p>
    </>}
  </section>;
}