import { Field } from './Fields';
const platform=url=>{try{const host=new URL(url).hostname.toLowerCase();if(host.endsWith('instagram.com'))return 'Instagram';if(host.endsWith('tiktok.com'))return 'TikTok';if(host.endsWith('facebook.com'))return 'Facebook';if(host.endsWith('youtube.com')||host==='youtu.be')return 'YouTube';if(host==='x.com'||host.endsWith('.x.com')||host.endsWith('twitter.com'))return 'X';return '';}catch{return '';}};
export default function OwnedChannelSource({form,setForm,entities,accounts}){
  const candidates=entities.filter(e=>e.type==='Candidate');
  const owned=accounts.filter(a=>a.watchlist_id===form.owned_candidate_id);
  const chosen=owned.find(a=>a.id===form.owned_account_id);
  return <div className="space-y-4 rounded-lg border border-[#dce3ec] p-4">
    <p className="text-sm font-semibold">Registered owned channel</p>
    <label className="block"><span className="intel-label">Candidate / Watchlist Entity</span><select className="intel-input" required value={form.owned_candidate_id||''} onChange={e=>setForm(f=>({...f,owned_candidate_id:e.target.value,owned_account_id:''}))}><option value="">Select candidate</option>{candidates.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
    <label className="block"><span className="intel-label">Registered Account</span><select className="intel-input" required value={form.owned_account_id||''} disabled={!form.owned_candidate_id} onChange={e=>setForm(f=>({...f,owned_account_id:e.target.value}))}><option value="">Select account</option>{owned.map(a=><option key={a.id} value={a.id}>{a.platform||platform(a.url)||'Web'} · {a.handle||a.url}</option>)}</select></label>
    {chosen&&<p className="text-xs break-all text-[#617789]">KNOWN · Registered platform: {chosen.platform||platform(chosen.url)||'Web'} · Registered account: {chosen.handle?`${chosen.handle} · `:''}{chosen.url}. Source identity is validated by the server on submission.</p>}
    <Field label="Individual Post URL" type="url" required value={form.source_url} onChange={value=>setForm(f=>({...f,source_url:value}))} placeholder="https://..."/>
    <p className="text-xs text-[#617789]">Confirm that this post is from the selected registered account. Account ownership cannot be verified from every post URL alone.</p>
  </div>;
}