import { useCallback, useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';

const ROOT='/api/assistant-evaluation/acceptance-submissions';
const TRACKS=[
  ['SOURCE_LINKED_AI_REVIEW','AI answer evidence review'],
  ['LEGAL_REFERENCE_SIGNOFF','Legal reference review evidence'],
  ['LEGAL_SOURCE_ELECTION_SCOPE','Election scope applicability review'],
  ['NEGATIVE_CONTROL_REVIEW','Missing-source negative control'],
  ['FORMAL_CLIENT_ACCEPTANCE','Client acceptance evidence'],
  ['EVALUATION_SAMPLE_SHORTFALL','Evaluation sample shortfall']
];
const REFERENCE=/^[A-Za-z0-9][A-Za-z0-9._:/-]{7,159}$/;
const STATUS={
  SUBMITTED_UNVERIFIED:'Submitted — awaiting independent review',
  REVIEWED:'Evidence reviewed — not formal approval',
  REVISION_REQUESTED:'Revision requested'
};
function allowed(access){
  return !window.__BAWASLU_DEMO_REPLICA__ &&
    access?.status==='Active' &&
    access?.role==='National Administrator' &&
    access?.geographic_scope==='Nationwide' &&
    access?.permissions?.administration===true &&
    access?.permissions?.view_intelligence===true;
}
async function api(path,options={}){
  const auth=window.localStorage.getItem('bawaslu_access_token');
  if(!auth)throw new Error('Sign in with an authorized National Administrator account.');
  const reply=await fetch(path,{
    ...options,cache:'no-store',
    headers:{Authorization:'Bearer '+auth,...(options.body?{'Content-Type':'application/json'}:{})}
  });
  const body=await reply.json().catch(()=>({}));
  if(!reply.ok)throw new Error(
    typeof body.detail==='string'?body.detail:
    reply.status===403?'National Administrator access required.':
    'Acceptance review request failed ('+reply.status+').');
  return body;
}
const pill={SUBMITTED_UNVERIFIED:'bg-amber-50 text-amber-800',
  REVIEWED:'bg-blue-50 text-blue-800',REVISION_REQUESTED:'bg-rose-50 text-rose-800'};
const button='rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50';
export default function AcceptanceReview(){
  const {access}=useOutletContext();
  const permitted=allowed(access);
  const [result,setResult]=useState(null);
  const [track,setTrack]=useState(TRACKS[0][0]);
  const [reference,setReference]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [expanded,setExpanded]=useState({});
  const [confirm,setConfirm]=useState(null);
  const [currentUserId,setCurrentUserId]=useState(null);
  const refresh=useCallback(async()=>{
    setBusy(true);setError('');
    try{
      const data=await api(ROOT);
      setResult(data);
    }catch(e){setResult(null);setError(e.message);}
    finally{setBusy(false);}
  },[]);
  useEffect(()=>{
    if(!permitted)return;
    let active=true;
    api('/api/auth/me').then(u=>{
      if(active)setCurrentUserId(u.id);
    }).catch(()=>{if(active)setError('Unable to verify your reviewer identity. Review actions are unavailable.');});
    refresh();
    return()=>{active=false;};
  },[permitted,refresh]);
  if(!permitted)return <div role="alert" className="intel-card p-6 text-sm">
    National Administrator access is required for Acceptance Review.
  </div>;
  const valid=REFERENCE.test(reference.trim())&&!reference.includes('://')&&!reference.includes('..');
  const entries=result?.entries||[];
  async function submit(e){
    e.preventDefault();
    if(!valid||busy)return;
    setBusy(true);setError('');setMessage('');
    try{
      await api(ROOT,{method:'POST',body:JSON.stringify({track,reference:reference.trim()})});
      setReference('');setMessage('Evidence reference submitted. Independent review is still required.');
      const data=await api(ROOT);setResult(data);
    }catch(ex){setError(ex.message);}finally{setBusy(false);}
  }
  async function review(){
    if(!confirm||busy)return;
    setBusy(true);setError('');setMessage('');
    try{
      await api(ROOT+'/'+encodeURIComponent(confirm.id)+'/review',{
        method:'POST',body:JSON.stringify({action:confirm.action})
      });
      const data=await api(ROOT);
      setResult(data);setMessage('Review action recorded. This is not legal or client acceptance.');
      setConfirm(null);
    }catch(ex){setError(ex.message);setConfirm(null);}finally{setBusy(false);}
  }
  return <div data-acceptance-review="v159.3" className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-xs font-bold uppercase tracking-widest text-[#9a7e49]">Administration / Governance</p>
        <h1 className="intel-heading mt-2">Acceptance Review</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">Register opaque evidence references, record independent review outcomes and inspect an append-only audit history. This workspace does not grant legal-reference sign-off or formal BAWASLU client acceptance.</p>
      </div>
      <Link className={button} to="/administration">Back to Administration</Link>
    </div>
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" role="note">
      <strong>Human acceptance pending.</strong> “Evidence reviewed” means an independent administrator acknowledged the submitted reference. It does not verify the underlying legal claim, AI accuracy, legal currentness or formal client approval.
    </div>
    {error&&<p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {message&&<p role="status" className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">{message}</p>}
    <section className="intel-card p-5 space-y-4">
      <h2 className="font-semibold">Submit evidence reference</h2>
      <p className="text-xs text-slate-600">Enter only a reference ID from an approved evidence repository. Do not paste evidence contents, personal data, public URLs or legal conclusions.</p>
      <form onSubmit={submit} className="grid gap-3 md:grid-cols-[1fr_1.3fr_auto] md:items-end">
        <label className="space-y-1 text-sm"><span className="font-medium">Acceptance requirement</span>
          <select className="intel-input w-full" value={track} onChange={e=>setTrack(e.target.value)} disabled={busy}>
            {TRACKS.map(([value,label])=><option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-sm"><span className="font-medium">Opaque evidence reference</span>
          <input className="intel-input w-full" value={reference} onChange={e=>setReference(e.target.value)} minLength={8} maxLength={160}
            placeholder="qa:review-batch-001" autoComplete="off" disabled={busy} aria-describedby="ref-help"/>
        </label>
        <button className="intel-button" type="submit" disabled={!valid||busy}>Submit reference</button>
      </form>
      <p id="ref-help" className="text-xs text-slate-500">Allowed: 8–160 characters (letters, numbers, period, underscore, colon, slash, hyphen). References cannot contain URLs or parent-directory traversal.</p>
    </section>
    <section className="intel-card overflow-hidden">
      <div className="flex flex-wrap justify-between items-center gap-2 p-5 border-b">
        <div><h2 className="font-semibold">Submitted evidence and review history</h2>
          <p className="text-xs text-slate-500 mt-1">Most recent 100 submissions. Pending and reviewed entries may require further external approval.</p>
        </div>
        <button className={button} onClick={refresh} disabled={busy}>{busy?'Loading…':'Refresh'}</button>
      </div>
      {result&&<section className="mx-5 mt-4 rounded-xl border border-slate-200 p-4 space-y-3" aria-label="Acceptance requirements by track">
        <div><h3 className="font-semibold text-sm">Acceptance requirements — evidence coverage only</h3>
          <p className="text-xs text-slate-500 mt-1">Reviewed submissions are not formal acceptance. Counts reflect the most recent 100 entries, not an approval or a full historical audit.</p>
        </div>
        {result.historical_records_may_be_excluded&&<p role="status" className="text-xs text-amber-800">Older submissions are outside the 100-record window. Do not interpret these counts as all-time totals.</p>}
        <div className="grid gap-2 sm:grid-cols-2">
          {TRACKS.map(([code,label])=>{const item=result.track_progress?.[code]||{};
            return <div key={code} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs font-semibold">{label}</p>
              <p className="mt-1 text-xs text-slate-600">{item.awaiting_review||0} awaiting review · {item.evidence_reviewed_not_formally_approved||0} evidence reviewed · {item.revision_requested||0} revisions requested</p>
              <p className="mt-1 text-xs font-medium text-amber-800">Formal sign-off: not verified</p>
            </div>;
          })}
        </div>
      </section>}
      {result&&<div className="grid grid-cols-1 sm:grid-cols-3 gap-3 px-5 pt-4">
        {[['SUBMITTED_UNVERIFIED','Awaiting review'],['REVIEWED','Evidence reviewed'],['REVISION_REQUESTED','Revisions requested']].map(([value,label])=><div className="rounded-lg bg-slate-50 p-3" key={value}>
          <div className="text-xs text-slate-600">{label}</div><div className="text-2xl font-semibold">{result.status_counts?.[value]||0}</div>
        </div>)}
      </div>}
      {result&&!entries.length&&<p className="p-5 text-sm text-slate-600">No acceptance evidence submitted yet.</p>}
      <div className="divide-y">
        {entries.map(entry=>{
          const self=String(entry.submitted_by_user_id)===String(currentUserId);
          const canReview=entry.status==='SUBMITTED_UNVERIFIED'&&currentUserId!=null&&!self;
          return <article className="p-5 space-y-3" key={entry.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0"><p className="text-sm font-semibold">{TRACKS.find(t=>t[0]===entry.track)?.[1]||entry.track}</p>
                <p className="text-xs text-slate-600 mt-1">Submission #{entry.id} · User {entry.submitted_by_user_id} · {entry.submitted_at?new Date(entry.submitted_at).toLocaleString():'Unknown date'}</p>
              </div>
              <span className={'rounded-full px-2.5 py-1 text-xs font-semibold '+(pill[entry.status]||'bg-slate-100 text-slate-700')}>{STATUS[entry.status]||entry.status}</span>
            </div>
            <p className="break-all rounded bg-slate-50 px-3 py-2 font-mono text-xs">{entry.reference}</p>
            <div className="flex flex-wrap gap-2 items-center">
              <button className={button} type="button" onClick={()=>setExpanded(x=>({...x,[entry.id]:!x[entry.id]}))}>
                {expanded[entry.id]?'Hide audit history':'View audit history'} ({entry.history?.length||0})
              </button>
              {canReview&&<><button className={button} disabled={busy} type="button" onClick={()=>setConfirm({id:entry.id,action:'EVIDENCE_REVIEWED'})}>Mark evidence reviewed</button>
                <button className={button} disabled={busy} type="button" onClick={()=>setConfirm({id:entry.id,action:'REVISION_REQUESTED'})}>Request revision</button></>}
              {self&&entry.status==='SUBMITTED_UNVERIFIED'&&<span className="text-xs text-slate-500">Independent administrator required</span>}
            </div>
            {expanded[entry.id]&&<ol className="space-y-2 rounded-lg border bg-slate-50 p-3 text-xs">
              {(entry.history||[]).map((event,i)=><li key={i}>
                <span className="font-semibold">{event.action}</span> · User {event.actor_user_id} · {event.at?new Date(event.at).toLocaleString():'Unknown date'}
              </li>)}
            </ol>}
          </article>;
        })}
      </div>
    </section>
    {confirm&&<div role="dialog" aria-modal="true" aria-labelledby="acceptance-confirm-title" className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 space-y-4 shadow-xl">
        <h2 id="acceptance-confirm-title" className="font-semibold">Confirm independent evidence review</h2>
        <p className="text-sm text-slate-700">Record <strong>{confirm.action==='EVIDENCE_REVIEWED'?'Evidence Reviewed':'Revision Requested'}</strong> for submission #{confirm.id}? This action is audited and cannot be undone. It is not formal legal or client sign-off.</p>
        <div className="flex justify-end gap-2"><button className={button} disabled={busy} onClick={()=>setConfirm(null)}>Cancel</button>
          <button className="intel-button" disabled={busy} onClick={review}>Confirm action</button></div>
      </div>
    </div>}
  </div>;
}
