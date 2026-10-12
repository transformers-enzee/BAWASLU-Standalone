import { Link, useOutletContext } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowUpRight, BadgeCheck, Inbox, MapPin, Radio, ShieldAlert, Sparkles, ListChecks, Globe2 } from 'lucide-react';
import { useIntel } from '@/components/intel/useIntel';
import { base44 } from '@/api/base44Client';
import Status from '@/components/intel/Status';
import { Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const triagePending=x=>{const t=x.triage_review||x.triage_review_status||{};const state=typeof t==='string'?t:t.state;const generated=typeof t==='object'?t.generated:!!state;return generated&&state&&state!=='REVIEW COMPLETE';};
const mismatchPending=x=>(x.geographic_mismatch_review?.status||x.geographic_mismatch?.status)==='pending';

function scopeLabel(access,t){
  if(access?.geographic_scope==='Nationwide') return t('command_scope_nationwide');
  if(access?.geographic_scope==='Regency/City') return [access.regency_city,access.province].filter(Boolean).join(', ')||t('command_scope_regional');
  return access?.province||t('command_scope_regional');
}
function reasons(x,t){
  const out=[];
  if(mismatchPending(x)) out.push(t('geographic_mismatch'));
  if(triagePending(x)) out.push(t('ai_triage_review'));
  if(pendingReview(x)) out.push(t('pending_human_review'));
  if(x.jurisdiction_confirmed!==true) out.push(t('jurisdiction_unresolved'));
  if(x.verification_status==='UNVERIFIED') out.push(t('unverified'));
  return out;
}
function score(x){let n=0;if(mismatchPending(x))n+=70;if(triagePending(x))n+=60;if(pendingReview(x))n+=55;if(x.jurisdiction_confirmed!==true)n+=50;if(x.priority==='Critical')n+=45;else if(x.priority==='High')n+=35;return n;}

function Metric({label,value,detail,to,Icon}){
  return <Link to={to} className="intel-card p-5 group hover:border-[#abc7d5] transition-colors">
    <div className="flex items-start justify-between gap-4">
      <div><p className="text-xs font-semibold text-[#75899a]">{label}</p><strong className="block mt-2 text-3xl font-semibold text-[#163750]">{value}</strong><p className="text-xs text-[#8192a3] mt-2 leading-5">{detail}</p></div>
      <div className="rounded-lg bg-[#eef5f7] p-2.5 text-[#176e8e]"><Icon size={18}/></div>
    </div>
    <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#176e8e]">{detail ? 'Open' : ''} <ArrowUpRight size={13}/></span>
  </Link>
}

export default function CommandCenter(){
  const {access}=useOutletContext();
  const {t}=useLanguage();
  const {items,loading,error}=useIntel();
  const [socialCounts,setSocialCounts]=useState(null);
  const [socialError,setSocialError]=useState('');

  useEffect(()=>{
    base44.functions.invoke('socialListening',{action:'queue',data:{state:''}})
      .then(r=>setSocialCounts(r.data?.counts||{}))
      .catch(()=>setSocialError(t('social_queue_unavailable')));
  },[t]);

  const data=useMemo(()=>{
    const pending=items.filter(pendingReview);
    const valid=items.filter(validated);
    const unresolved=items.filter(x=>x.jurisdiction_confirmed!==true);
    const triage=items.filter(triagePending);
    const unverified=items.filter(x=>x.verification_status==='UNVERIFIED');
    const high=items.filter(x=>['Critical','High'].includes(x.priority));
    const attention=[...items].filter(x=>score(x)>0).sort((a,b)=>score(b)-score(a)||new Date(b.updated_date||b.created_date||0)-new Date(a.updated_date||a.created_date||0)).slice(0,8);
    const provinceCounts={};
    for(const x of items){
      const key=x.jurisdiction_type==='National'?t('national'):(x.province||t('jurisdiction_unresolved_short'));
      provinceCounts[key]=(provinceCounts[key]||0)+1;
    }
    const geography=Object.entries(provinceCounts).sort((a,b)=>b[1]-a[1]).slice(0,6);
    return {pending,valid,unresolved,triage,unverified,high,attention,geography};
  },[items,t]);

  const socialPending=socialCounts?['DISCOVERED','RELEVANT','MONITOR'].reduce((n,k)=>n+Number(socialCounts[k]||0),0):null;

  return <div className="space-y-8">
    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div>
        <div className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">{t('command_center_kicker')}</div>
        <h1 className="intel-heading">{t('command_center')}</h1>
        <p className="text-[#75879a] text-sm mt-2 max-w-3xl">{t('command_center_intro')}</p>
      </div>
      <div className="intel-card px-4 py-3 min-w-[240px]">
        <p className="text-[11px] uppercase tracking-wider text-[#7b8da0]">{t('command_authorized_scope')}</p>
        <p className="font-semibold text-[#173952] mt-1 flex items-center gap-2"><Globe2 size={15}/>{scopeLabel(access,t)}</p>
        <p className="text-xs text-[#8192a3] mt-1">{access?.access_role||''}</p>
      </div>
    </div>

    <Notice error={error}/>
    {loading?<p className="text-sm text-[#73869a]">{t('loading_intelligence')}</p>:error?null:<>
      <section>
        <div className="mb-4"><h2 className="text-lg font-semibold">{t('command_operational_picture')}</h2><p className="text-xs text-[#7a8b9e] mt-1">{t('command_operational_note')}</p></div>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          <Metric label={t('pending_intelligence_review')} value={data.pending.length} detail={t('pending_intelligence_detail')} to="/inbox?view=pending-review" Icon={Inbox}/>
          <Metric label={t('validated_intelligence')} value={data.valid.length} detail={t('validated_intelligence_detail')} to="/inbox?review_status=Validated%20as%20Relevant%20Intelligence" Icon={BadgeCheck}/>
          <Metric label={t('jurisdiction_unresolved')} value={data.unresolved.length} detail={t('jurisdiction_unresolved_detail')} to="/inbox?view=jurisdiction-unresolved" Icon={MapPin}/>
          <Metric label={t('ai_triage_awaiting_review')} value={data.triage.length} detail={t('ai_triage_detail')} to="/inbox?view=triage-pending" Icon={Sparkles}/>
          <Metric label={t('unverified_evidence')} value={data.unverified.length} detail={t('unverified_evidence_detail')} to="/inbox?verification_status=UNVERIFIED" Icon={ShieldAlert}/>
          <Metric label={t('social_review_queue')} value={socialPending===null?'—':socialPending} detail={t('social_review_detail')} to="/social-listening?tab=queue&pending=1" Icon={Radio}/>
        </div>
        {socialError&&<p className="text-xs text-[#8a5d27] mt-3">{socialError} {t('no_socialcrawl_search')}</p>}
      </section>

      <section className="grid xl:grid-cols-[1.7fr_1fr] gap-6">
        <div>
          <div className="flex items-end justify-between gap-4 mb-4"><div><h2 className="text-lg font-semibold">{t('command_attention_queue')}</h2><p className="text-xs text-[#7a8b9e] mt-1">{t('command_attention_note')}</p></div><Link to="/inbox" className="text-xs text-[#176e8e] font-semibold">{t('open_inbox')} →</Link></div>
          <div className="intel-card divide-y divide-[#edf1f5]">
            {data.attention.length?data.attention.map(x=><div key={x.id} className="p-4 flex flex-col lg:flex-row lg:items-center gap-3">
              <div className="min-w-0 flex-1"><Link to={'/intelligence/'+x.id} className="text-xs font-semibold text-[#146a8b]">{x.intelligence_id}</Link><Link to={'/intelligence/'+x.id} className="block font-semibold text-[#1e354b] mt-1 hover:underline line-clamp-2">{x.title||t('untitled_intelligence')}</Link><div className="flex flex-wrap gap-1.5 mt-2">{reasons(x,t).slice(0,4).map(r=><span key={r} className="rounded-full bg-[#fff5e9] px-2 py-1 text-[11px] font-semibold text-[#8a5d27]">{r}</span>)}</div></div>
              <div className="flex flex-wrap gap-1.5 lg:w-[220px]"><Status value={x.priority}/><Status value={x.review_status}/><Status value={x.verification_status}/></div>
            </div>):<div className="p-8 text-sm text-center text-[#73869a]">{t('no_immediate_attention')}</div>}
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <div className="mb-4"><h2 className="text-lg font-semibold">{t('command_priority_snapshot')}</h2><p className="text-xs text-[#7a8b9e] mt-1">{t('command_priority_note')}</p></div>
            <div className="intel-card p-5 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-[#fff7ed] p-4"><p className="text-xs text-[#8a5d27]">{t('critical_priority')}</p><strong className="text-2xl text-[#173952]">{items.filter(x=>x.priority==='Critical').length}</strong></div>
              <div className="rounded-lg bg-[#f7fafb] p-4"><p className="text-xs text-[#718398]">{t('high_priority')}</p><strong className="text-2xl text-[#173952]">{items.filter(x=>x.priority==='High').length}</strong></div>
            </div>
          </div>

          <div>
            <div className="mb-4"><h2 className="text-lg font-semibold">{t('command_geography')}</h2><p className="text-xs text-[#7a8b9e] mt-1">{t('command_geography_note')}</p></div>
            <div className="intel-card p-5 space-y-3">
              {data.geography.length?data.geography.map(([name,count])=><div key={name} className="flex items-center justify-between gap-3 text-sm"><span className="text-[#425a70] truncate">{name}</span><span className="rounded-full bg-[#eef5f7] px-2.5 py-1 text-xs font-semibold text-[#176e8e]">{count}</span></div>):<p className="text-sm text-[#73869a]">{t('command_no_geography')}</p>}
            </div>
          </div>

          <div className="intel-card p-5">
            <h3 className="font-semibold flex items-center gap-2"><ListChecks size={17}/>{t('command_next_actions')}</h3>
            <div className="mt-4 space-y-2 text-sm">
              <Link className="flex items-center justify-between rounded-lg bg-[#f7fafb] px-3 py-2" to="/validation"><span>{t('validation')}</span><ArrowUpRight size={14}/></Link>
              <Link className="flex items-center justify-between rounded-lg bg-[#f7fafb] px-3 py-2" to="/social-listening?tab=queue"><span>{t('social_review_queue')}</span><ArrowUpRight size={14}/></Link>
              <Link className="flex items-center justify-between rounded-lg bg-[#f7fafb] px-3 py-2" to="/inbox"><span>{t('intelligence_inbox')}</span><ArrowUpRight size={14}/></Link>
            </div>
          </div>
        </div>
      </section>

      <div className="intel-card p-4 flex items-start gap-3 text-xs text-[#64798c]"><AlertTriangle size={16} className="mt-0.5 shrink-0"/><p>{t('command_read_only_note')}</p></div>
    </>}
  </div>;
}
