import { Field } from './Fields';
import { useLanguage } from '@/lib/LanguageContext';
const platform=url=>{try{const host=new URL(url).hostname.toLowerCase();if(host.endsWith('instagram.com'))return 'Instagram';if(host.endsWith('tiktok.com'))return 'TikTok';if(host.endsWith('facebook.com'))return 'Facebook';if(host.endsWith('youtube.com')||host==='youtu.be')return 'YouTube';if(host==='x.com'||host.endsWith('.x.com')||host.endsWith('twitter.com'))return 'X';return '';}catch{return '';}};
export default function OwnedChannelSource({form,setForm,entities,accounts}){
  const {t}=useLanguage();
  const candidates=entities.filter(e=>e.type==='Candidate');
  const owned=accounts.filter(a=>a.watchlist_id===form.owned_candidate_id);
  const chosen=owned.find(a=>a.id===form.owned_account_id);
  return <div className="space-y-4 rounded-lg border border-[#dce3ec] p-4">
    <p className="text-sm font-semibold">{t('registered_owned_channel_lower')}</p>
    <label className="block"><span className="intel-label">{t('candidate_watchlist_entity')}</span><select className="intel-input" required value={form.owned_candidate_id||''} onChange={e=>setForm(f=>({...f,owned_candidate_id:e.target.value,owned_account_id:''}))}><option value="">{t('select_candidate')}</option>{candidates.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
    <label className="block"><span className="intel-label">{t('registered_account')}</span><select className="intel-input" required value={form.owned_account_id||''} disabled={!form.owned_candidate_id} onChange={e=>setForm(f=>({...f,owned_account_id:e.target.value}))}><option value="">{t('select_account')}</option>{owned.map(a=><option key={a.id} value={a.id}>{a.platform||platform(a.url)||'Web'} · {a.handle||a.url}</option>)}</select></label>
    {chosen&&<p className="text-xs break-all text-[#617789]">KNOWN · Registered platform: {chosen.platform||platform(chosen.url)||'Web'} · Registered account: {chosen.handle?`${chosen.handle} · `:''}{chosen.url}. Source identity is validated by the server on submission.</p>}
    <Field label={t('individual_post_url')} type="url" required value={form.source_url} onChange={value=>setForm(f=>({...f,source_url:value}))} placeholder="https://..."/>
    <p className="text-xs text-[#617789]">{t('registered_post_confirm_note')}</p>
  </div>;
}