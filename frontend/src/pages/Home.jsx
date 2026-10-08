import { Link, useOutletContext } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, Plus, Inbox, BadgeCheck, ShieldAlert, MapPin, Sparkles, Radio, ListFilter } from 'lucide-react';
import { useIntel, useRegistry, intel } from '@/components/intel/useIntel';
import IntelligenceTable from '@/components/intel/IntelligenceTable';
import { auditTitle } from '@/components/intel/auditLabels';
import { Notice } from '@/components/intel/Fields';
import { base44 } from '@/api/base44Client';

const pendingReview=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const validated=x=>x.review_status==='Validated as Relevant Intelligence';
const triagePending=x=>{
  const t=x.triage_review||x.triage_review_status||{};
  const state=typeof t==='string'?t:t.state;
  const generated=typeof t==='object'?t.generated:!!state;
  return generated&&state&&state!=='REVIEW COMPLETE';
};

export default function Home(){
  const {access}=useOutletContext();
  const [activity,setActivity]=useState([]);
  const [socialCounts,setSocialCounts]=useState(null);
  const [socialError,setSocialError]=useState('');
  const {items,loading,error}=useIntel();
  const {items:watch,loading:wl,error:we}=useRegistry();

  useEffect(()=>{
    intel('activity').then(r=>setActivity(r.events||[])).catch(()=>{});
    base44.functions.invoke('socialListening',{action:'queue',data:{state:''}})
      .then(r=>setSocialCounts(r.data?.counts||{}))
      .catch(()=>setSocialError('Social Listening queue status unavailable.'));
  },[]);

  const metrics=useMemo(()=>{
    const pending=items.filter(pendingReview).length;
    const validatedCount=items.filter(validated).length;
    const unverified=items.filter(x=>x.verification_status==='UNVERIFIED').length;
    const unresolved=items.filter(x=>x.jurisdiction_confirmed!==true).length;
    const triage=items.filter(triagePending).length;
    const socialPending=socialCounts?['DISCOVERED','RELEVANT','MONITOR'].reduce((n,k)=>n+Number(socialCounts[k]||0),0):null;
    return {pending,validatedCount,unverified,unresolved,triage,socialPending};
  },[items,socialCounts]);

  const attention=useMemo(()=>items.filter(x=>
    pendingReview(x)||
    x.jurisdiction_confirmed!==true||
    x.geographic_mismatch?.status==='pending'||
    triagePending(x)||
    (['Critical','High'].includes(x.priority)&&!validated(x))
  ).slice(0,6),[items]);

  const recentValidated=useMemo(()=>items.filter(validated).sort((a,b)=>{
    const da=new Date(a.validated_at||a.updated_date||a.created_date||0).getTime();
    const db=new Date(b.validated_at||b.updated_date||b.created_date||0).getTime();
    return db-da;
  }).slice(0,5),[items]);

  const cards=[
    {label:'Pending Intelligence Review',value:metrics.pending,detail:'Needs human review / validation',to:'/validation',Icon:Inbox,permission:'human_validation'},
    {label:'Validated Intelligence',value:metrics.validatedCount,detail:'Human-validated relevant intelligence',to:'/inbox',Icon:BadgeCheck},
    {label:'UNVERIFIED Evidence',value:metrics.unverified,detail:'Independent source verification pending',to:'/inbox',Icon:ShieldAlert},
    {label:'Jurisdiction Unresolved',value:metrics.unresolved,detail:'Needs human jurisdiction confirmation',to:'/inbox',Icon:MapPin},
    {label:'AI Triage Awaiting Review',value:metrics.triage,detail:'Generated suggestions not fully decided',to:'/inbox',Icon:Sparkles},
    {label:'Social Review Queue',value:metrics.socialPending===null?'—':metrics.socialPending,detail:'Stored results awaiting disposition',to:'/social-listening',Icon:Radio}
  ];

  return <div className="space-y-8">
    <div className="flex items-end justify-between gap-4">
      <div>
        <div className="text-xs uppercase tracking-[.18em] text-[#9a7e49] font-bold mb-2">Workspace Overview</div>
        <h1 className="intel-heading">Intelligence Situation</h1>
        <p className="text-[#75879a] text-sm mt-2">Operational view of the existing BAWASLU workspace, focused on what requires attention now.</p>
      </div>
      {access.permissions?.add_intelligence===true&&<Link to="/add" className="intel-ghost hidden md:inline-flex"><Plus size={16}/>Add intelligence</Link>}
    </div>

    <Notice error={error||we}/>
    {socialError&&<p className="text-xs text-[#8192a3]">{socialError} No SocialCrawl search was triggered.</p>}

    {loading||wl?<p className="text-sm text-[#73869a]">Loading workspace overview...</p>:error||we?null:<>
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {cards.filter(c=>!c.permission||access.permissions?.[c.permission]===true).map(({label,value,detail,to,Icon})=>
          <Link to={to} key={label} className="intel-card p-5 md:p-6 group hover:border-[#abc7d5] transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-[#75899a]">{label}</p>
                <strong className="block mt-3 text-3xl font-semibold text-[#163750]">{value}</strong>
                <p className="text-xs text-[#8192a3] mt-2">{detail}</p>
              </div>
              <div className="rounded-lg bg-[#eef5f7] p-2.5 text-[#176e8e]"><Icon size={19}/></div>
            </div>
            <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#176e8e]">Open workspace <ArrowUpRight size={13}/></span>
          </Link>
        )}
      </div>

      <section>
        <div className="flex justify-between items-end gap-4 mb-4">
          <div>
            <h2 className="text-lg font-semibold">What needs attention now</h2>
            <p className="text-xs text-[#7a8b9e] mt-1">Pending review, unresolved jurisdiction, geographic mismatch, incomplete AI triage review, or elevated priority.</p>
          </div>
          <Link to="/inbox" className="text-sm text-[#176e8e] font-semibold flex items-center gap-1">Open inbox <ArrowUpRight size={15}/></Link>
        </div>
        <IntelligenceTable items={attention}/>
      </section>

      <div className="grid xl:grid-cols-[1.5fr_1fr] gap-6">
        <section>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-semibold">Latest validated intelligence</h2>
              <p className="text-xs text-[#7a8b9e] mt-1">Most recently validated records in your authorized scope.</p>
            </div>
            <Link to="/inbox" className="text-sm text-[#176e8e] font-semibold flex items-center gap-1">View intelligence <ArrowUpRight size={15}/></Link>
          </div>
          <IntelligenceTable items={recentValidated}/>
        </section>

        <section className="intel-card p-6">
          <h2 className="text-lg font-semibold">Workspace shortcuts</h2>
          <p className="text-xs text-[#7a8b9e] mt-1 mb-4">Continue work in the existing operational modules.</p>
          <div className="space-y-2">
            {[
              ['/watchlist','Review watchlist',ListFilter,'view_intelligence'],
              ['/social-listening','Open Social Listening',Radio,'view_intelligence'],
              ['/assistant','Ask Intelligence Assistant',Sparkles,'view_intelligence'],
              ['/validation','Open validation queue',BadgeCheck,'human_validation']
            ].filter(([, , ,perm])=>access.permissions?.[perm]===true).map(([to,label,Icon])=>
              <Link key={to} to={to} className="flex items-center justify-between rounded-lg border border-[#e4e9ef] px-3 py-3 text-sm font-semibold text-[#29445d] hover:bg-[#f7fafb]">
                <span className="flex items-center gap-2"><Icon size={16}/>{label}</span><ArrowUpRight size={14}/>
              </Link>
            )}
          </div>
          <div className="mt-5 border-t border-[#edf1f5] pt-4">
            <p className="text-xs text-[#8192a3]">Active watchlist items</p>
            <strong className="text-2xl text-[#163750]">{watch.filter(x=>x.status==='Active').length}</strong>
          </div>
        </section>
      </div>

      <section className="intel-card p-6">
        <h2 className="text-lg font-semibold mb-4">Recent activity</h2>
        {activity.length?activity.slice(0,6).map(x=><div key={x.id} className="py-3 border-t border-[#edf1f5] text-sm">
          <span className="font-semibold">{auditTitle(x)}</span> · {x.subject_type}
          <span className="block text-xs text-[#8293a4] mt-1">{x.actor_name} · {new Date(x.occurred_at||x.created_date).toLocaleString('en-GB')}</span>
        </div>):<p className="text-sm text-[#8293a4]">No recent activity yet.</p>}
      </section>
    </>}
  </div>;
}
